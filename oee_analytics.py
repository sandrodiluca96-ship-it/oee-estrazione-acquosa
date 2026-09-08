"""Calcoli puri per pianificazione Comber e indicatori OEE/OOE.

Il modulo non dipende da Streamlit o Supabase: questo rende le regole
aziendali verificabili con test automatici e utilizzabili sullo storico.
"""

from __future__ import annotations

import re
import unicodedata
import hashlib
from datetime import date, datetime, time, timedelta

import pandas as pd


PROCESS_MACHINES = ["Comber", "EV200", "Spray Dryer"]


def _event_timestamp(row) -> pd.Timestamp:
    """Ordina gli eventi rispettando anche il turno notturno."""
    day = pd.to_datetime(row.get("data_turno"), errors="coerce")
    if pd.isna(day):
        return pd.Timestamp.min
    try:
        hour, minute = [int(part) for part in str(row.get("ora_inizio", ""))[:5].split(":")]
    except (TypeError, ValueError):
        hour, minute = 0, 0
    if str(row.get("turno", "")) == "3" and hour < 6:
        day += pd.Timedelta(days=1)
    return day.normalize() + pd.Timedelta(hours=hour, minutes=minute)


def open_productions(events: pd.DataFrame, as_of: datetime | None = None) -> pd.DataFrame:
    """Ricostruisce i lotti di processo aperti dagli eventi salvati.

    Un lotto resta aperto tra turni diversi finché non viene registrata una
    chiusura. La data dell'ultimo segmento non chiude né nasconde il lotto.
    """
    columns = [
        "Macchina", "Stato", "Lotto", "Codice", "Descrizione", "Fase",
        "Ultimo aggiornamento", "Turno", "Dettaglio",
    ]
    if events.empty:
        return pd.DataFrame(columns=columns)
    work = events.copy()
    for column in ["macchina", "tipo_evento", "lotto", "tipo_produzione", "stato_lotto"]:
        if column not in work:
            work[column] = ""
    work = work[
        work["macchina"].isin(PROCESS_MACHINES)
        & (work["tipo_evento"] == "Produzione")
        & work["lotto"].astype(str).str.strip().ne("")
    ].copy()
    if work.empty:
        return pd.DataFrame(columns=columns)
    work["_timestamp"] = work.apply(_event_timestamp, axis=1)
    work = work.sort_values(["_timestamp", "id_evento"] if "id_evento" in work else ["_timestamp"])
    active: dict[tuple[str, str], dict] = {}
    for row in work.to_dict("records"):
        machine, lot = str(row.get("macchina", "")).strip(), str(row.get("lotto", "")).strip()
        key = (machine, lot)
        stage = str(row.get("tipo_produzione", "")).strip()
        closed = stage == "Chiusura lotto" or str(row.get("stato_lotto", "")).strip() == "Completato"
        if closed:
            active.pop(key, None)
            continue
        current = active.setdefault(key, {"events": [], "opened": row.get("_timestamp")})
        current["events"].append(row)
        current["last"] = row

    rows = []
    for (machine, lot), current in active.items():
        history, last = current["events"], current["last"]
        last_at = last["_timestamp"]
        # Lo stato dipende dal workflow, non dall'età del record: il lotto
        # resta in lavorazione finché non viene salvata una chiusura.
        status = "🟢 IN LAVORAZIONE"

        def latest_text(field):
            for item in reversed(history):
                value = str(item.get(field, "")).strip()
                if value and value.lower() != "nan":
                    return value
            return ""

        phase = latest_text("fase_lavorazione") or latest_text("tipo_produzione") or "Lavorazione in corso"
        if machine == "Comber":
            completed = {
                str(item.get("numero_estrazione", "")).strip()
                for item in history if str(item.get("stato_estrazione", "")).strip() == "Completata"
            } - {"", "nan"}
            extraction = latest_text("numero_estrazione")
            detail = f"Estrazione {extraction or '-'} · {len(completed)} completate"
        elif machine == "EV200":
            detail = f"Lotti Comber: {latest_text('lotti_comber') or '-'}"
        else:
            detail = "Essiccazione / atomizzazione"
        updated = "—" if last_at == pd.Timestamp.min else last_at.strftime("%d/%m/%Y %H:%M")
        rows.append({
            "Macchina": machine, "Stato": status, "Lotto": lot,
            "Codice": latest_text("codice"), "Descrizione": latest_text("descrizione"),
            "Fase": phase, "Ultimo aggiornamento": updated,
            "Turno": latest_text("turno"), "Dettaglio": detail,
        })
    return pd.DataFrame(rows, columns=columns).sort_values(
        ["Macchina", "Ultimo aggiornamento", "Lotto"], ascending=[True, False, True]
    ).reset_index(drop=True) if rows else pd.DataFrame(columns=columns)


def number(value) -> float:
    parsed = pd.to_numeric(str(value).replace(",", "."), errors="coerce")
    return 0.0 if pd.isna(parsed) else float(parsed)


def normalize_text(value) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()


def cause_id_for_name(value) -> str:
    normalized = normalize_text(value) or "CAUSALE"
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:10].upper()
    return f"CAU-{digest}"


def same_drug(planned_name, actual_name) -> bool:
    """Confronto tollerante tra nome gestionale e descrizione anagrafica.

    Accetta uguaglianza e descrizioni estese (es. TIMO / TIMO FOGLIE), ma non
    usa il lotto. Le associazioni non riconosciute restano visibili fuori piano.
    """
    planned = normalize_text(planned_name)
    actual = normalize_text(actual_name)
    if not planned or not actual:
        return False
    if planned == actual:
        return True
    if len(planned) >= 4 and (planned in actual or actual in planned):
        return True
    p_words = {word for word in planned.split() if len(word) >= 4}
    a_words = {word for word in actual.split() if len(word) >= 4}
    return bool(p_words and a_words and p_words.intersection(a_words))


def completed_comber_extractions(events: pd.DataFrame) -> pd.DataFrame:
    """Restituisce una riga per estrazione completata senza doppi conteggi."""
    columns = ["extraction_key", "data", "lotto", "numero_estrazione", "codice", "descrizione", "kg_droga"]
    if events.empty:
        return pd.DataFrame(columns=columns)
    work = events.copy()
    work = work[(work["macchina"] == "Comber") & (work["tipo_evento"] == "Produzione")]
    if work.empty:
        return pd.DataFrame(columns=columns)
    work["_date"] = pd.to_datetime(work["data_turno"], errors="coerce")
    work["_kg"] = pd.to_numeric(work["kg_droga"], errors="coerce").fillna(0)
    work["_number"] = pd.to_numeric(work["numero_estrazione"], errors="coerce").fillna(0).astype(int)
    work["_key"] = work["lotto"].astype(str).str.strip() + "|" + work["_number"].astype(str)
    rows = []
    for key, group in work.groupby("_key", sort=False):
        completed = group[group["stato_estrazione"] == "Completata"]
        if completed.empty:
            continue
        final = completed.sort_values(["_date", "ora_fine", "id_evento"]).iloc[-1]
        rows.append({
            "extraction_key": key,
            "data": final["_date"].date() if pd.notna(final["_date"]) else None,
            "lotto": str(final.get("lotto", "")).strip(),
            "numero_estrazione": int(final["_number"]),
            "codice": str(final.get("codice", "")).strip(),
            "descrizione": str(final.get("descrizione", "")).strip(),
            "kg_droga": float(group["_kg"].max()),
        })
    return pd.DataFrame(rows, columns=columns).sort_values(["data", "extraction_key"], na_position="last")


def _allocate_comber(plans: pd.DataFrame, events: pd.DataFrame, cutoff: date):
    """Alloca i kg completati al piano più vecchio aperto della stessa droga."""
    work = plans.copy().reset_index(drop=True)
    work["_start"] = pd.to_datetime(work["data_inizio"], errors="coerce").dt.date
    work["_end"] = pd.to_datetime(work["data_fine"], errors="coerce").dt.date
    work["_planned"] = pd.to_numeric(work["kg_pianificati"], errors="coerce").fillna(0).clip(lower=0)
    work["_allocated"] = 0.0
    work["_completed_extractions"] = 0
    extractions = completed_comber_extractions(events)
    extractions = extractions[extractions["data"].notna() & (extractions["data"] <= cutoff)].copy()
    allocation_rows = []
    unmatched_rows = []
    order = sorted(work.index, key=lambda i: (work.at[i, "_start"] or date.max, str(work.at[i, "piano_id"])))
    for extraction in extractions.itertuples(index=False):
        remaining = float(extraction.kg_droga)
        matched_any = False
        for idx in order:
            if remaining <= 1e-9:
                break
            start = work.at[idx, "_start"]
            if start is None or pd.isna(start) or start > extraction.data:
                continue
            if not same_drug(work.at[idx, "prodotto"], extraction.descrizione):
                continue
            capacity = max(float(work.at[idx, "_planned"] - work.at[idx, "_allocated"]), 0.0)
            if capacity <= 1e-9:
                continue
            assigned = min(remaining, capacity)
            work.at[idx, "_allocated"] += assigned
            work.at[idx, "_completed_extractions"] += 1
            allocation_rows.append({"piano_id": work.at[idx, "piano_id"], "extraction_key": extraction.extraction_key, "kg_allocati": assigned})
            remaining -= assigned
            matched_any = True
        if remaining > 1e-9:
            unmatched_rows.append({
                "data_turno": extraction.data,
                "lotto": extraction.lotto,
                "numero_estrazione": extraction.numero_estrazione,
                "codice": extraction.codice,
                "descrizione": extraction.descrizione,
                "kg_droga": remaining,
                "motivo": "Nessun piano aperto compatibile" if not matched_any else "Quantità oltre il piano",
            })
    return work, pd.DataFrame(allocation_rows), pd.DataFrame(unmatched_rows)


def comber_planning_view(plans: pd.DataFrame, events: pd.DataFrame, selected_week_plans: pd.DataFrame, as_of=None):
    """Costruisce il piano della sola settimana selezionata e i fuori piano."""
    as_of = as_of or datetime.now()
    empty = pd.DataFrame()
    if selected_week_plans.empty:
        return empty, empty, empty
    week_start = pd.to_datetime(selected_week_plans["data_inizio"], errors="coerce").min().date()
    week_end = pd.to_datetime(selected_week_plans["data_fine"], errors="coerce").max().date()
    cutoff = min(as_of.date(), week_end)
    # Ogni settimana è indipendente: i residui dei piani precedenti non sono
    # riportati né assorbono la produzione della settimana selezionata.
    current, allocations, unmatched = _allocate_comber(selected_week_plans, events, cutoff)
    rows = []
    for _, row in current.iterrows():
        plan_id = str(row["piano_id"])
        planned = float(row["_planned"])
        allocated = float(row["_allocated"])
        residual = max(planned - allocated, 0.0)
        start = row["_start"]
        end = row["_end"]
        if as_of.date() < start:
            expected = 0.0
        elif as_of.date() > end:
            expected = 100.0
        else:
            span = max((end - start).days + 1, 1)
            expected = min(max(((as_of.date() - start).days + 1) / span * 100, 0.0), 100.0)
        progress = allocated / planned * 100 if planned else 0.0
        if residual <= 1e-6:
            status = "COMPLETATO CON EXTRA" if progress > 100.01 else "COMPLETATO"
            light = "🟢"
        elif as_of.date() > end:
            status, light = "IN RITARDO", "🔴"
        elif allocated <= 1e-9:
            status, light = "DA INIZIARE", "🔵"
        elif progress + 10 >= expected:
            status, light = "IN LINEA", "🟢"
        else:
            status, light = "SOTTO IL RITMO", "🟡"
        rows.append({
            **{column: row[column] for column in plans.columns},
            "kg_effettivi": allocated,
            "kg_residui": residual,
            "kg_residui_inizio_settimana": planned,
            "kg_recuperati_settimana": 0.0,
            "estrazioni_completate": int(row["_completed_extractions"]),
            "avanzamento_pct": progress,
            "avanzamento_grafico_pct": min(progress, 100.0),
            "avanzamento_atteso_pct": expected,
            "stato": status,
            "semaforo": light,
        })
    status = pd.DataFrame(rows)
    current_rows = status.copy()
    if not unmatched.empty:
        unmatched = unmatched[(unmatched["data_turno"] >= week_start) & (unmatched["data_turno"] <= cutoff)]
    return current_rows, empty, unmatched


def calculate_effectiveness(events: pd.DataFrame, productions: pd.DataFrame, causes: pd.DataFrame,
                            targets: dict[str, float], quality: float = 0.95,
                            start: date | None = None, end: date | None = None):
    """Calcola OEE e OOE con classificazione causali letta in tempo reale.

    OEE: solo produzione programmata e perdite non escluse.
    OOE: tutte le ore registrate nel turno operativo.
    La performance usa il tempo realmente operativo, evitando di penalizzare
    due volte le fermate.
    """
    event_work = events.copy()
    if event_work.empty:
        event_work = pd.DataFrame(columns=["id_turno", "data_turno", "macchina", "tipo_evento", "cause_id", "durata_h"])
    event_work["_date"] = pd.to_datetime(event_work["data_turno"], errors="coerce").dt.date
    event_work["_hours"] = pd.to_numeric(event_work["durata_h"], errors="coerce").fillna(0).clip(lower=0)
    if start:
        event_work = event_work[event_work["_date"] >= start]
    if end:
        event_work = event_work[event_work["_date"] <= end]

    cause_rows = causes.copy()
    by_id = {str(r.cause_id).strip(): r for r in cause_rows.itertuples() if str(getattr(r, "cause_id", "")).strip()}
    by_name = {normalize_text(r.causale): r for r in cause_rows.itertuples()}
    results = []
    for machine in PROCESS_MACHINES:
        machine_events = event_work[event_work["macchina"] == machine]
        operating = float(machine_events.loc[machine_events["tipo_evento"] == "Produzione", "_hours"].sum())
        oee_losses = 0.0
        scheduled_excluded = 0.0
        ooe_losses = 0.0
        unknown_losses = 0.0
        for _, event in machine_events[machine_events["tipo_evento"] != "Produzione"].iterrows():
            cause = by_id.get(str(event.get("cause_id", "")).strip()) or by_name.get(normalize_text(event["tipo_evento"]))
            excluded = str(getattr(cause, "esclusa_pianificato", "NO")).upper() == "SI" if cause else False
            penalizes_ooe = str(getattr(cause, "penalizza_ooe", "SI")).upper() == "SI" if cause else True
            if penalizes_ooe:
                ooe_losses += float(event["_hours"])
            if excluded:
                scheduled_excluded += float(event["_hours"])
            else:
                oee_losses += float(event["_hours"])
                if cause is None:
                    unknown_losses += float(event["_hours"])
        oee_planned = operating + oee_losses
        ooe_planned = operating + ooe_losses
        availability_oee = operating / oee_planned if oee_planned else 0.0
        availability_ooe = operating / ooe_planned if ooe_planned else 0.0
        turn_ids = set(machine_events["id_turno"].astype(str))
        machine_prod = productions[
            (productions["macchina"] == machine) & productions["id_turno"].astype(str).isin(turn_ids)
        ] if not productions.empty else pd.DataFrame()
        output = float(pd.to_numeric(machine_prod.get("kg_puro_equivalente", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
        theoretical = float(targets.get(machine, 0.0)) * operating / 24.0
        raw_performance = output / theoretical if theoretical else 0.0
        performance = min(max(raw_performance, 0.0), 1.0)
        q = min(max(float(quality), 0.0), 1.0)
        oee = min(availability_oee * performance * q, 1.0)
        ooe = min(availability_ooe * performance * q, 1.0)
        results.append({
            "Macchina": machine,
            "Ore totali": ooe_planned,
            "Ore escluse OEE": scheduled_excluded,
            "Perdite OEE": oee_losses,
            "Tempo operativo": operating,
            "Availability OEE": availability_oee,
            "Availability OOE": availability_ooe,
            "Performance": performance,
            "Performance grezza": raw_performance,
            "Qualità": q,
            "OEE": oee,
            "OOE": ooe,
            "Output equivalente": output,
            "Output teorico": theoretical,
            "Ore causali non riconosciute": unknown_losses,
        })
    return results
