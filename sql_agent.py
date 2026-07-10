import os
import sqlite3
from dataclasses import dataclass, field
from typing import TypedDict, Optional

import pandas as pd
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

load_dotenv()

FORBIDDEN_KEYWORDS = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE")

def _get_model():
    if os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o-mini", temperature=0)
    raise RuntimeError("No LLM API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env")

class AgentState(TypedDict, total=False):
    question: str
    schema: str
    sql: str
    rows: list
    columns: list
    summary: str
    error: Optional[str]

@dataclass
class AskResult:
    question: str
    sql: str
    rows: list = field(default_factory=list)
    columns: list = field(default_factory=list)
    summary: str = ""
    error: Optional[str] = None

    @property
    def dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=self.columns)

class SQLAgent:
    def __init__(self, db_path: str = "sales.db"):
        self.db_path = db_path
        self.model = _get_model()
        self.graph = self._build_graph()

    def _node_inspect_schema(self, state: AgentState) -> AgentState:
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]
        schema_parts = []
        for table in tables:
            cur.execute(f"PRAGMA table_info({table})")
            cols = ", ".join(f"{c[1]} {c[2]}" for c in cur.fetchall())
            schema_parts.append(f"{table}({cols})")
        con.close()
        return {**state, "schema": "\n".join(schema_parts)}

    def _node_generate_sql(self, state: AgentState) -> AgentState:
        prompt = (
            "You are a SQL expert working with a SQLite database.\n"
            f"Schema:\n{state['schema']}\n\n"
            f"Question: {state['question']}\n\n"
            "Write ONE syntactically correct SQLite SELECT query that answers "
            "the question. Only return the raw SQL, no explanation, no markdown "
            "fences. Never modify data - SELECT statements only. Limit results "
            "to 100 rows unless the question implies otherwise."
        )
        response = self.model.invoke(prompt)
        sql = response.content.strip().strip("```sql").strip("```").strip()
        return {**state, "sql": sql}

    def _node_execute_sql(self, state: AgentState) -> AgentState:
        sql = state["sql"]
        if any(word in sql.upper() for word in FORBIDDEN_KEYWORDS):
            return {**state, "error": "Blocked: query contains a write/DDL statement."}
        try:
            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            columns = [d[0] for d in cur.description] if cur.description else []
            con.close()
            return {**state, "rows": rows, "columns": columns, "error": None}
        except Exception as exc:
            return {**state, "error": str(exc)}

    def _node_summarize(self, state: AgentState) -> AgentState:
        if state.get("error"):
            return {**state, "summary": f"Query failed: {state['error']}"}
        preview = state["rows"][:20]
        prompt = (
            f"Question: {state['question']}\n"
            f"SQL used: {state['sql']}\n"
            f"Columns: {state['columns']}\n"
            f"Result rows (up to 20 shown): {preview}\n\n"
            "Answer the original question in 1-3 plain-English sentences, "
            "citing specific numbers from the result."
        )
        response = self.model.invoke(prompt)
        return {**state, "summary": response.content.strip()}

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("inspect_schema", self._node_inspect_schema)
        builder.add_node("generate_sql", self._node_generate_sql)
        builder.add_node("execute_sql", self._node_execute_sql)
        builder.add_node("summarize", self._node_summarize)
        builder.set_entry_point("inspect_schema")
        builder.add_edge("inspect_schema", "generate_sql")
        builder.add_edge("generate_sql", "execute_sql")
        builder.add_edge("execute_sql", "summarize")
        builder.add_edge("summarize", END)
        return builder.compile()

    def ask(self, question: str) -> AskResult:
        final_state = self.graph.invoke({"question": question})
        return AskResult(
            question=question,
            sql=final_state.get("sql", ""),
            rows=final_state.get("rows", []),
            columns=final_state.get("columns", []),
            summary=final_state.get("summary", ""),
            error=final_state.get("error"),
        )

if __name__ == "__main__":
    agent = SQLAgent()
    result = agent.ask("What were the top 5 products by total revenue?")
    print("SQL:", result.sql)
    print("Summary:", result.summary)
    print(result.dataframe)
