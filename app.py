import streamlit as st
from sql_agent import SQLAgent

st.set_page_config(page_title="NL BI Assistant", page_icon="📊")
st.title("📊 Natural-Language BI Assistant")
st.caption("Ask a question about the sample sales database in plain English.")

if "agent" not in st.session_state:
    st.session_state.agent = SQLAgent(db_path="sales.db")

question = st.text_input("Your question", placeholder="e.g. What were the top 5 products by revenue last quarter?")

if st.button("Ask") and question:
    with st.spinner("Thinking..."):
        result = st.session_state.agent.ask(question)
    st.session_state.last_result = result

if "last_result" in st.session_state:
    result = st.session_state.last_result
    if result.error:
        st.error(result.error)
    else:
        st.subheader("Answer")
        st.write(result.summary)
        st.subheader("SQL used")
        st.code(result.sql, language="sql")
        st.subheader("Result")
        st.dataframe(result.dataframe)
        st.divider()
        if st.button("Push result to Power BI"):
            try:
                from powerbi_push import push_dataframe
                push_dataframe(result.dataframe)
                st.success("Pushed to Power BI streaming dataset.")
            except Exception as exc:
                st.error(f"Push failed: {exc}")
