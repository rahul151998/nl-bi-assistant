import os
import requests
import msal
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

AUTHORITY_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}"
SCOPE = ["https://analysis.windows.net/powerbi/api/.default"]
PUSH_URL_TEMPLATE = (
    "https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"
    "/datasets/{dataset_id}/tables/{table_name}/rows"
)

def get_access_token() -> str:
    tenant_id = os.environ["POWERBI_TENANT_ID"]
    client_id = os.environ["POWERBI_CLIENT_ID"]
    client_secret = os.environ["POWERBI_CLIENT_SECRET"]
    app = msal.ConfidentialClientApplication(
        client_id=client_id, client_credential=client_secret,
        authority=AUTHORITY_TEMPLATE.format(tenant_id=tenant_id),
    )
    result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in result:
        raise RuntimeError(f"Auth failed: {result.get('error_description', result)}")
    return result["access_token"]

def push_dataframe(df: pd.DataFrame, table_name=None) -> None:
    workspace_id = os.environ["POWERBI_WORKSPACE_ID"]
    dataset_id = os.environ["POWERBI_DATASET_ID"]
    table_name = table_name or os.environ.get("POWERBI_TABLE_NAME", "QueryResults")
    token = get_access_token()
    url = PUSH_URL_TEMPLATE.format(workspace_id=workspace_id, dataset_id=dataset_id, table_name=table_name)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    rows = df.astype(object).where(pd.notnull(df), None).to_dict(orient="records")
    payload = {"rows": rows}
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code >= 300:
        raise RuntimeError(f"Power BI push failed ({response.status_code}): {response.text}")

if __name__ == "__main__":
    sample = pd.DataFrame([{"Category": "Test", "Revenue": 123.45}])
    push_dataframe(sample)
    print("Pushed sample row to Power BI.")
