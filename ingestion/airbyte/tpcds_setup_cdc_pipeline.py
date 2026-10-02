import requests, yaml
from requests.auth import HTTPBasicAuth

AUTH = HTTPBasicAuth('airbyte', 'password')
BASE_URL = 'http://localhost:8000/api/v1'

# 1. Obtener workspace ID
ws_res = requests.post(f'{BASE_URL}/workspaces/list', json={}, auth=AUTH).json()
workspace_id = ws_res['workspaces'][0]['workspaceId']

# 2. Registrar Source TPC-DS (CDC)
with open('sources/postgres_cdc_tpcds.yaml') as f:
    s_cfg = yaml.safe_load(f)

sources = requests.post(f'{BASE_URL}/sources/list', json={'workspaceId': workspace_id}, auth=AUTH).json().get('sources', [])
src = next((s for s in sources if s['name'] == s_cfg['name']), None)
if not src:
    res = requests.post(f'{BASE_URL}/sources/create', json={
        'workspaceId': workspace_id,
        'name': s_cfg['name'],
        'sourceDefinitionId': s_cfg['sourceDefinitionId'],
        'connectionConfiguration': s_cfg['connectionConfiguration']
    }, auth=AUTH).json()
    src_id = res['sourceId']
    print(f'Source CDC creado: {src_id}')
else:
    src_id = src['sourceId']
    print(f'Source CDC existente: {src_id}')

# 3. Obtener Destination Postgres DW existente
dests = requests.post(f'{BASE_URL}/destinations/list', json={'workspaceId': workspace_id}, auth=AUTH).json().get('destinations', [])
dst = next(d for d in dests if d['name'] == 'Postgres DW Destination')
dest_id = dst['destinationId']
print(f'Destination DW: {dest_id}')

# 4. Descubrir catálogo de TPC-DS
print('Descubriendo catálogo...')
cat_res = requests.post(f'{BASE_URL}/sources/discover_schema', json={'sourceId': src_id, 'disable_cache': True}, auth=AUTH).json()
configured = []
target_tables = {'date_dim', 'item', 'store_sales'}

for s in cat_res.get('catalog', {}).get('streams', []):
    name = s['stream']['name']
    if name in target_tables:
        configured.append({
            'stream': s['stream'],
            'config': {
                'syncMode': 'full_refresh',
                'destinationSyncMode': 'overwrite',
                'cursorField': [],
                'primaryKey': [],
                'selected': True
            }
        })

# 5. Crear Conexión
conns = requests.post(f'{BASE_URL}/connections/list', json={'workspaceId': workspace_id}, auth=AUTH).json().get('connections', [])
conn = next((c for c in conns if c['name'] == 'Postgres TPC-DS (CDC) -> Postgres DW'), None)
if not conn:
    conn = requests.post(f'{BASE_URL}/connections/create', json={
        'name': 'Postgres TPC-DS (CDC) -> Postgres DW',
        'sourceId': src_id,
        'destinationId': dest_id,
        'prefix': 'tpcds_',
        'namespaceDefinition': 'source',
        'status': 'active',
        'syncCatalog': {'streams': configured}
    }, auth=AUTH).json()
    conn_id = conn['connectionId']
    print(f'Conexión creada: {conn_id}')
else:
    conn_id = conn['connectionId']
    print(f'Conexión existente: {conn_id}')

# 6. Disparar sincronización
sync = requests.post(f'{BASE_URL}/connections/sync', json={'connectionId': conn_id}, auth=AUTH).json()
job_id = sync.get("job", {}).get("id")
print(f"Job de replicación disparado con éxito. Job ID: {job_id}")