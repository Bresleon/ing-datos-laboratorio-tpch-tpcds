import requests
from requests.auth import HTTPBasicAuth

AUTH = HTTPBasicAuth("airbyte", "password")
BASE_URL = "http://localhost:8000/api/v1"

# 1. Obtener Workspace
ws_res = requests.post(f"{BASE_URL}/workspaces/list", json={}, auth=AUTH).json()
workspace_id = ws_res["workspaces"][0]["workspaceId"]

# 2. Registrar Source CDC si no existe
sources = requests.post(f"{BASE_URL}/sources/list", json={"workspaceId": workspace_id}, auth=AUTH).json().get("sources", [])
src = next((s for s in sources if s["name"] == "Postgres TPC-H (CDC)"), None)
if not src:
    defs = requests.post(f"{BASE_URL}/source_definitions/list", json={}, auth=AUTH).json()
    src_def_id = next(d["sourceDefinitionId"] for d in defs["sourceDefinitions"] if d["name"].lower() == "postgres")
    src = requests.post(f"{BASE_URL}/sources/create", json={
        "workspaceId": workspace_id,
        "name": "Postgres TPC-H (CDC)",
        "sourceDefinitionId": src_def_id,
        "connectionConfiguration": {
            "host": "172.17.0.1",
            "port": 5432,
            "database": "tpch",
            "username": "airbyte_user",
            "password": "airbyte",
            "schemas": ["public"],
            "ssl_mode": {"mode": "disable"},
            "replication_method": {
                "method": "CDC",
                "replication_slot": "airbyte_slot",
                "publication": "airbyte_publication",
                "initial_waiting_seconds": 300
            }
        }
    }, auth=AUTH).json()
source_id = src["sourceId"]

# 3. Registrar Destination Postgres si no existe
dests = requests.post(f"{BASE_URL}/destinations/list", json={"workspaceId": workspace_id}, auth=AUTH).json().get("destinations", [])
dst = next((d for d in dests if d["name"] == "Postgres DW Destination"), None)
if not dst:
    defs = requests.post(f"{BASE_URL}/destination_definitions/list", json={}, auth=AUTH).json()
    dst_def_id = next(d["destinationDefinitionId"] for d in defs["destinationDefinitions"] if d["name"].lower() == "postgres")
    dst = requests.post(f"{BASE_URL}/destinations/create", json={
        "workspaceId": workspace_id,
        "name": "Postgres DW Destination",
        "destinationDefinitionId": dst_def_id,
        "connectionConfiguration": {
            "host": "172.17.0.1",
            "port": 5435,
            "database": "dw_destination",
            "username": "postgres",
            "password": "password123",
            "schema": "public",
            "ssl_mode": {"mode": "disable"}
        }
    }, auth=AUTH).json()
dest_id = dst["destinationId"]

# 4. Descubrir catálogo de tablas
cat = requests.post(f"{BASE_URL}/sources/discover_schema", json={"sourceId": source_id, "disable_cache": True}, auth=AUTH).json()
configured_streams = []
for s in cat.get("catalog", {}).get("streams", []):
    name = s["stream"]["name"]
    if name in {"nation", "region", "orders"}:
        is_orders = (name == "orders")
        configured_streams.append({
            "stream": s["stream"],
            "config": {
                "syncMode": "incremental" if is_orders else "full_refresh",
                "destinationSyncMode": "append_dedup" if is_orders else "overwrite",
                "cursorField": [],
                "primaryKey": [["o_orderkey"]] if is_orders else [],
                "selected": True
            }
        })

# 5. Crear Conexión y Disparar Sincronización
conns = requests.post(f"{BASE_URL}/connections/list", json={"workspaceId": workspace_id}, auth=AUTH).json().get("connections", [])
conn = next((c for c in conns if c["name"] == "Postgres TPC-H (CDC) -> Postgres DW"), None)
if not conn:
    conn = requests.post(f"{BASE_URL}/connections/create", json={
        "name": "Postgres TPC-H (CDC) -> Postgres DW",
        "sourceId": source_id,
        "destinationId": dest_id,
        "prefix": "",
        "namespaceDefinition": "source",
        "status": "active",
        "syncCatalog": {"streams": configured_streams}
    }, auth=AUTH).json()

conn_id = conn["connectionId"]
sync = requests.post(f'{BASE_URL}/connections/sync', json={'connectionId': conn_id}, auth=AUTH).json()
job_id = sync.get("job", {}).get("id")
print(f"Job de replicación disparado con éxito. Job ID: {job_id}")