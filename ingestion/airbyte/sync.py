import os
import sys
import argparse
import yaml
import requests
from requests.auth import HTTPBasicAuth

AIRBYTE_URL = os.getenv("AIRBYTE_URL", "http://localhost:8000/api/v1")
AUTH = HTTPBasicAuth("airbyte", "password")

def get_workspace_id() -> str:
    res = requests.post(f"{AIRBYTE_URL}/workspaces/list", json={}, auth=AUTH)
    if res.status_code == 200:
        workspaces = res.json().get("workspaces", [])
        if workspaces:
            return workspaces[0]["workspaceId"]
    return "1a41e3a7-68c7-46e0-8f74-2bb84eca01ce"

def get_or_create_source(workspace_id: str, cfg_path: str) -> str:
    with open(cfg_path, "r") as f:
        cfg = yaml.safe_load(f)

    res = requests.post(f"{AIRBYTE_URL}/sources/list", json={"workspaceId": workspace_id}, auth=AUTH)
    if res.status_code == 200:
        for src in res.json().get("sources", []):
            if src["name"] == cfg["name"]:
                requests.post(f"{AIRBYTE_URL}/sources/update", json={
                    "sourceId": src["sourceId"],
                    "name": cfg["name"],
                    "connectionConfiguration": cfg["connectionConfiguration"]
                }, auth=AUTH)
                return src["sourceId"]

    payload = {
        "workspaceId": workspace_id,
        "name": cfg["name"],
        "sourceDefinitionId": cfg["sourceDefinitionId"],
        "connectionConfiguration": cfg["connectionConfiguration"]
    }
    create_res = requests.post(f"{AIRBYTE_URL}/sources/create", json=payload, auth=AUTH)
    if create_res.status_code != 200:
        print(f"Error creando Source: {create_res.text}")
        sys.exit(1)
    return create_res.json()["sourceId"]

def get_or_create_destination(workspace_id: str, cfg_path: str) -> str:
    with open(cfg_path, "r") as f:
        cfg = yaml.safe_load(f)

    res = requests.post(f"{AIRBYTE_URL}/destinations/list", json={"workspaceId": workspace_id}, auth=AUTH)
    if res.status_code == 200:
        dests = res.json().get("destinations", [])
        for dest in dests:
            if dest["name"] == cfg["name"] or "Local Storage" in dest["name"]:
                return dest["destinationId"]

    defs_res = requests.post(f"{AIRBYTE_URL}/destination_definitions/list", json={}, auth=AUTH)
    dest_def_id = None
    if defs_res.status_code == 200:
        for d in defs_res.json().get("destinationDefinitions", []):
            if "Local JSON" in d["name"]:
                dest_def_id = d["destinationDefinitionId"]
                break

    if not dest_def_id:
        dest_def_id = cfg.get("destinationDefinitionId")

    payload = {
        "workspaceId": workspace_id,
        "name": cfg["name"],
        "destinationDefinitionId": dest_def_id,
        "connectionConfiguration": cfg["connectionConfiguration"]
    }
    create_res = requests.post(f"{AIRBYTE_URL}/destinations/create", json=payload, auth=AUTH)
    if create_res.status_code != 200:
        print(f"Error creando Destination: {create_res.text}")
        sys.exit(1)
    return create_res.json()["destinationId"]

def sync_connection(workspace_id: str, conn_cfg_path: str):
    with open(conn_cfg_path, "r") as f:
        conn_cfg = yaml.safe_load(f)

    source_id = get_or_create_source(workspace_id, conn_cfg["sourceConfig"])
    dest_id = get_or_create_destination(workspace_id, conn_cfg["destinationConfig"])

    cat_res = requests.post(f"{AIRBYTE_URL}/sources/discover_schema", json={"sourceId": source_id, "disable_cache": True}, auth=AUTH)
    if cat_res.status_code != 200:
        print(f"Error descubriendo esquema: {cat_res.text}")
        sys.exit(1)

    discovered = cat_res.json().get("catalog", {}).get("streams", [])
    desired = {s["name"]: s for s in conn_cfg.get("streams", [])}

    configured_streams = []
    for s_obj in discovered:
        s = s_obj["stream"]
        stream_name = s["name"]
        if stream_name in desired:
            d_cfg = desired[stream_name]
            configured_streams.append({
                "stream": s,
                "config": {
                    "syncMode": d_cfg.get("syncMode", "full_refresh"),
                    "destinationSyncMode": d_cfg.get("destinationSyncMode", "overwrite"),
                    "cursorField": d_cfg.get("cursorField", []),
                    "primaryKey": d_cfg.get("primaryKey", []),
                    "selected": True
                }
            })

    res = requests.post(f"{AIRBYTE_URL}/connections/list", json={"workspaceId": workspace_id}, auth=AUTH)
    existing_conn = None
    if res.status_code == 200:
        for c in res.json().get("connections", []):
            if c["name"] == conn_cfg["name"] or conn_cfg["name"] in c["name"]:
                existing_conn = c
                break

    if existing_conn:
        conn_id = existing_conn["connectionId"]
        requests.post(f"{AIRBYTE_URL}/connections/update", json={
            "connectionId": conn_id,
            "status": "active",
            "syncCatalog": {"streams": configured_streams}
        }, auth=AUTH)
    else:
        payload = {
            "name": conn_cfg["name"],
            "sourceId": source_id,
            "destinationId": dest_id,
            "prefix": conn_cfg.get("prefix", ""),
            "status": "active",
            "syncCatalog": {"streams": configured_streams}
        }
        create_res = requests.post(f"{AIRBYTE_URL}/connections/create", json=payload, auth=AUTH)
        if create_res.status_code != 200:
            print(f"Error creando Connection: {create_res.text}")
            sys.exit(1)
        conn_id = create_res.json()["connectionId"]

    print(f"Iniciando replicación para '{conn_cfg['name']}' (ID: {conn_id})...")
    sync_res = requests.post(f"{AIRBYTE_URL}/connections/sync", json={"connectionId": conn_id}, auth=AUTH)
    if sync_res.status_code == 200:
        job_id = sync_res.json().get("job", {}).get("id")
        print(f"Job disparado exitosamente. ID: {job_id}")
    else:
        print(f"Error al disparar: {sync_res.status_code} - {sync_res.text}")

def main():
    parser = argparse.ArgumentParser(description="Airbyte Declarative Pipeline Sync")
    parser.add_argument("target", choices=["tpch", "tpcds", "all"], help="Base de datos a replicar")
    args = parser.parse_args()

    workspace_id = get_workspace_id()

    if args.target in ["tpch", "all"]:
        sync_connection(workspace_id, "connections/postgres_tpch_to_local.yaml")
    if args.target in ["tpcds", "all"]:
        sync_connection(workspace_id, "connections/postgres_tpcds_to_local.yaml")

if __name__ == "__main__":
    main()