"""Persistenza Supabase per l'app OEE EVRA Lauria.

I CSV restano il dataset iniziale e un formato di esportazione. Quando Supabase
è configurato, tutte le letture e scritture operative passano da app_records.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st


KEY_COLUMNS = {
    "eventi": ["id_evento"],
    "turni": ["id_turno"],
    "produzioni": ["id"],
    "pianificazione_comber": ["piano_id"],
    "pianificazione_mescole": ["piano_id"],
    "anagrafica_prodotti": ["tipo", "codice"],
    "causali": ["causale"],
    "target": ["macchina"],
    "target_mescole": [],
}


def _secret(name: str) -> str:
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return str(value or os.environ.get(name, "")).strip()


def configured() -> bool:
    return bool(_secret("SUPABASE_URL") and _secret("SUPABASE_SERVICE_ROLE_KEY"))


@st.cache_resource
def client():
    from supabase import create_client

    url = _secret("SUPABASE_URL")
    key = _secret("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Connessione al database persistente non configurata.")
    return create_client(url, key)


def verify_connection() -> None:
    """Fallisce in modo esplicito se il database non è raggiungibile."""
    client().table("app_records").select("dataset", count="exact").limit(1).execute()


def audit_dataframe() -> pd.DataFrame:
    rows: list[dict] = []
    start = 0
    page_size = 1000
    while True:
        page = (
            client()
            .table("app_audit_log")
            .select(
                "audit_id,dataset,record_id,operation,old_payload,"
                "new_payload,changed_at,database_role"
            )
            .order("audit_id")
            .range(start, start + page_size - 1)
            .execute()
            .data
            or []
        )
        rows.extend(page)
        if len(page) < page_size:
            break
        start += page_size
    frame = pd.DataFrame(rows)
    for column in ["old_payload", "new_payload"]:
        if column in frame.columns:
            frame[column] = frame[column].map(
                lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True)
                if isinstance(value, (dict, list))
                else value
            )
    return frame


def _dataset(path: Path | str) -> str:
    name = Path(path).stem
    if name not in KEY_COLUMNS:
        raise ValueError(f"Dataset non configurato per la persistenza: {name}")
    return name


def _fetch_all(dataset: str, include_deleted: bool = False) -> list[dict]:
    rows: list[dict] = []
    start = 0
    page_size = 1000
    while True:
        query = (
            client()
            .table("app_records")
            .select("record_id,payload,deleted_at")
            .eq("dataset", dataset)
            .order("record_id")
            .range(start, start + page_size - 1)
        )
        if not include_deleted:
            query = query.is_("deleted_at", "null")
        page = query.execute().data or []
        rows.extend(page)
        if len(page) < page_size:
            break
        start += page_size
    return rows


def _clean_payload(row: pd.Series, columns: list[str]) -> dict[str, str]:
    payload = {}
    for column in columns:
        value = row.get(column, "")
        payload[column] = "" if pd.isna(value) else str(value)
    return payload


def _record_id(dataset: str, payload: dict[str, str], position: int) -> str:
    keys = KEY_COLUMNS[dataset]
    values = [payload.get(column, "").strip() for column in keys]
    if keys and all(values):
        return "|".join(values)
    if dataset == "target_mescole":
        return "config"
    raw = f"{dataset}|{position}|" + "|".join(f"{k}={payload[k]}" for k in sorted(payload))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _chunks(rows: list[dict], size: int = 200):
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def write_dataframe(path: Path | str, frame: pd.DataFrame, columns: list[str]) -> None:
    dataset = _dataset(path)
    work = frame.copy()
    for column in columns:
        if column not in work.columns:
            work[column] = ""
    desired: dict[str, dict[str, str]] = {}
    for position, (_, row) in enumerate(work[columns].iterrows()):
        payload = _clean_payload(row, columns)
        desired[_record_id(dataset, payload, position)] = payload

    existing_rows = _fetch_all(dataset, include_deleted=True)
    existing = {row["record_id"]: row for row in existing_rows}
    upserts = []
    for record_id, payload in desired.items():
        old = existing.get(record_id)
        if old is None or old.get("payload") != payload or old.get("deleted_at") is not None:
            upserts.append(
                {
                    "dataset": dataset,
                    "record_id": record_id,
                    "payload": payload,
                    "deleted_at": None,
                }
            )
    for batch in _chunks(upserts):
        client().table("app_records").upsert(
            batch, on_conflict="dataset,record_id"
        ).execute()


def soft_delete_ids(path: Path | str, record_ids) -> None:
    """Eliminazione recuperabile di record esplicitamente selezionati."""
    dataset = _dataset(path)
    deleted_at = datetime.now(timezone.utc).isoformat()
    for record_id in dict.fromkeys(str(value) for value in record_ids if str(value).strip()):
        (
            client()
            .table("app_records")
            .update({"deleted_at": deleted_at})
            .eq("dataset", dataset)
            .eq("record_id", record_id)
            .execute()
        )


def read_dataframe(path: Path | str, columns: list[str]) -> pd.DataFrame:
    dataset = _dataset(path)
    active = _fetch_all(dataset)
    if not active:
        # Importazione iniziale una sola volta. Se esistono record eliminati,
        # non si ripristina automaticamente il CSV di base.
        all_rows = _fetch_all(dataset, include_deleted=True)
        local_path = Path(path)
        if not all_rows and local_path.exists():
            local = pd.read_csv(local_path, dtype=str).fillna("")
            for column in columns:
                if column not in local.columns:
                    local[column] = ""
            if not local.empty:
                write_dataframe(local_path, local[columns], columns)
                active = _fetch_all(dataset)
    rows = [record.get("payload") or {} for record in active]
    frame = pd.DataFrame(rows)
    for column in columns:
        if column not in frame.columns:
            frame[column] = ""
    return frame[columns].fillna("")
