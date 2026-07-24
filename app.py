import html
import hmac
import os
from datetime import date, datetime, time, timedelta
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from event_workflow import COL_EVENTI, EVENTI_FILE, _create_production, _validate, render_machine_workflow

# RELEASE OEE LAURIA 3.9.2 — semaforo settimanale per prodotto Comber

st.set_page_config(page_title="OEE Produzione Lauria", page_icon="🏭", layout="wide")

VERSIONE = "3.9.2"
QUALITA = 0.95
PROCESS_MACHINES = ["Comber", "EV200", "Spray Dryer"]
MACCHINE = PROCESS_MACHINES + ["Mescole"]
DEFAULT_TARGET = {
    "Comber": {"fisico": 150.0, "equivalente": 150.0},
    "EV200": {"fisico": 168.75, "equivalente": 168.75},
    "Spray Dryer": {"fisico": 321.6, "equivalente": 128.64},
}
TURNI = {"1": (time(6), time(14)), "2": (time(14), time(22)), "3": (time(22), time(6))}
DATA = Path("data")
TURNI_FILE = DATA / "turni.csv"
LOTTI_FILE = DATA / "produzioni.csv"
PRODOTTI_FILE = DATA / "anagrafica_prodotti.csv"
CAUSALI_FILE = DATA / "causali.csv"
TARGET_FILE = DATA / "target.csv"
PLANNING_FILE = DATA / "pianificazione_comber.csv"
MESCOLE_PLANNING_FILE = DATA / "pianificazione_mescole.csv"
MESCOLE_TARGET_FILE = DATA / "target_mescole.csv"
LOGO_FILE = Path("assets") / "evra_logo.svg"

COL_TURNI = ["id_turno", "data_turno", "turno", "macchina", "ore_pianificate", "ore_produzione", "ore_fermo", "note"]
COL_LOTTI = [
    "id", "id_turno", "data_turno", "turno", "macchina", "lotto", "codice_droga",
    "codice_semilavorato", "descrizione", "kg_droga", "kg_liquido", "residuo_secco_pct",
    "kg_puro", "kg_semilavorato", "pct_puro_semilavorato", "kg_puro_equivalente", "lotti_comber", "piano_id", "note",
]
COL_PRODOTTI = ["tipo", "codice", "descrizione", "pct_puro_standard", "attivo"]
COL_CAUSALI = ["causale", "categoria", "esclusa_pianificato", "perdita_tecnica", "attiva"]
COL_TARGET = ["macchina", "target_fisico_giorno", "target_equivalente_giorno", "giorni_produttivi_anno"]
COL_PLANNING = ["piano_id","settimana","data_inizio","data_fine","ora_inizio","ora_fine","prodotto","lotto_droga","estrazioni_pianificate","kg_per_estrazione","kg_pianificati","impianto","caricato_il"]
COL_MESCOLE_PLANNING = ["piano_id","settimana","data_inizio_settimana","data_fine_settimana","data_documento","data_prevista","riferimento","codice","descrizione","quantita_pianificata","quantita_evasa","stato_origine","caricato_il"]
COL_MESCOLE_TARGET = ["target_kg_giorno","target_kg_ora_uomo"]


def require_password():
    """Protegge l'app senza salvare credenziali nel repository pubblico."""
    try:
        expected=str(st.secrets.get("APP_PASSWORD", "")).strip()
    except Exception:
        expected=str(os.environ.get("APP_PASSWORD", "")).strip()
    if not expected:
        st.error("Password applicazione non configurata. Inserisci APP_PASSWORD nei Secrets di Streamlit.")
        st.stop()
    if st.session_state.get("authenticated"):
        return
    st.title("Accesso OEE Produzione Lauria")
    st.caption("Inserisci la password aziendale per accedere all’applicazione.")
    entered=st.text_input("Password",type="password",key="login_password")
    if st.button("Accedi",type="primary"):
        if hmac.compare_digest(entered,expected):
            st.session_state["authenticated"]=True
            st.rerun()
        else:
            st.error("Password non corretta.")
    st.stop()


require_password()


st.markdown("""
<style>
:root{--navy:#0B4F87;--blue:#2F73B5;--green:#238B73;--ink:#24313A;--line:#D9E1E8}
.stApp{background:#F7F9FB;color:var(--ink)}
[data-testid="stSidebar"]{background:#FFFFFF;border-right:1px solid var(--line)}
[data-testid="stAppViewContainer"] p,[data-testid="stAppViewContainer"] label,
[data-testid="stSidebar"] p,[data-testid="stSidebar"] label{color:var(--ink)!important}
h1,h2,h3,h4{color:#17324D!important}.block-container{padding-top:1.4rem;max-width:1800px}
[data-testid="stMetric"]{background:#FFF;border:1px solid var(--line);border-radius:10px;padding:12px 15px}
[data-testid="stMetricLabel"],[data-testid="stMetricValue"]{color:var(--ink)!important}
[data-baseweb="input"]>div,[data-baseweb="select"]>div,[data-baseweb="textarea"]>div{background:#FFF!important}
[data-baseweb="input"] *,[data-baseweb="select"] *,[data-baseweb="textarea"] *{color:var(--ink)!important}
.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"]{background:#238B73;color:#FFF;border:0;font-weight:700}
.report-head{background:#FFF;border:1px solid var(--line);border-radius:10px 10px 0 0;padding:18px 22px}
.report-title{font-size:30px;font-weight:800;color:#2D3339}.report-sub{color:#5C6770}
.summary{display:grid;grid-template-columns:2fr repeat(6,1fr);color:#FFF;padding:11px 16px;align-items:center}
.summary.navy{background:#0B4F87}.summary.blue{background:#2F73B5}.summary.green{background:#238B73}
.summary .name{font-size:21px;font-weight:800}.summary .basis{font-size:12px;font-weight:600;opacity:.92;margin-top:4px;line-height:1.25}.summary .value{font-size:18px;font-weight:800}.summary .label{font-size:13px;opacity:.95}
.table-wrap{overflow-x:auto;background:#FFF;border:1px solid var(--line);border-radius:10px;margin-top:18px;padding:18px}
.prod-table{border-collapse:collapse;width:100%;min-width:1500px;font-size:13px}
.prod-table th{padding:10px 7px;border-bottom:2px solid #3892E5;text-align:center;color:#27323A;background:#FFF}
.prod-table td{padding:9px 7px;border-bottom:1px solid #E5E9ED;text-align:right;color:#263238}
.prod-table td:first-child{text-align:left;font-weight:700;border-right:2px solid #3892E5}
.prod-table tr:nth-child(even){background:#F0F2F4}.prod-table tr.group{font-weight:800;background:#E7EEF5}
.ach-good{color:#16815D!important;font-weight:800}.ach-mid{color:#C27700!important;font-weight:800}.ach-low{color:#C43D3D!important;font-weight:800}
.hint{background:#EAF4FB;border-left:5px solid #2F73B5;padding:12px;border-radius:5px;color:#254A64}
.machine-head{padding:16px 20px;border-radius:10px;color:#FFF;margin:8px 0 18px;font-size:24px;font-weight:800}
.machine-head.comber{background:#0B4F87}.machine-head.ev200{background:#2F73B5}.machine-head.spray{background:#238B73}.machine-head.mix{background:#6F4E8C}
.machine-note{font-size:14px;font-weight:400;opacity:.95;margin-top:3px}
@media(max-width:900px){.summary{grid-template-columns:1.5fr repeat(3,1fr);row-gap:8px}.report-title{font-size:23px}}
</style>
""", unsafe_allow_html=True)


def init_data():
    DATA.mkdir(exist_ok=True)
    if not TURNI_FILE.exists():
        pd.DataFrame(columns=COL_TURNI).to_csv(TURNI_FILE, index=False)
    if not LOTTI_FILE.exists():
        pd.DataFrame(columns=COL_LOTTI).to_csv(LOTTI_FILE, index=False)
    if not PRODOTTI_FILE.exists():
        pd.DataFrame([
            {"tipo":"Droga", "codice":"INSERIRE", "descrizione":"Nuovo codice droga", "pct_puro_standard":15, "attivo":"SI"},
            {"tipo":"Semilavorato", "codice":"INSERIRE", "descrizione":"Nuovo codice semilavorato", "pct_puro_standard":40, "attivo":"SI"},
        ]).to_csv(PRODOTTI_FILE, index=False)
    if not CAUSALI_FILE.exists():
        pd.DataFrame([
            ["Attesa prodotto","Organizzativa","NO","NO","SI"], ["Attesa analisi","Organizzativa","NO","NO","SI"],
            ["Carico/Scarico","Operativa","NO","NO","SI"], ["Lavaggio","Pianificata","SI","NO","SI"],
            ["Pulizia","Pianificata","SI","NO","SI"], ["Guasto","Tecnica","NO","SI","SI"],
            ["Manutenzione programmata","Pianificata","SI","NO","SI"],
            ["Manutenzione straordinaria","Tecnica","NO","SI","SI"], ["Altro","Operativa","NO","NO","SI"],
        ], columns=COL_CAUSALI).to_csv(CAUSALI_FILE, index=False)
    if not TARGET_FILE.exists():
        pd.DataFrame([
            {"macchina":m,"target_fisico_giorno":v["fisico"],"target_equivalente_giorno":v["equivalente"],"giorni_produttivi_anno":220}
            for m,v in DEFAULT_TARGET.items()
        ]).to_csv(TARGET_FILE,index=False)
    if not PLANNING_FILE.exists():
        pd.DataFrame(columns=COL_PLANNING).to_csv(PLANNING_FILE,index=False)
    if not MESCOLE_PLANNING_FILE.exists():
        pd.DataFrame(columns=COL_MESCOLE_PLANNING).to_csv(MESCOLE_PLANNING_FILE,index=False)
    if not MESCOLE_TARGET_FILE.exists():
        pd.DataFrame([{"target_kg_giorno":0,"target_kg_ora_uomo":0}]).to_csv(MESCOLE_TARGET_FILE,index=False)


def read_csv(path, columns):
    init_data()
    df = pd.read_csv(path, dtype=str).fillna("")
    for c in columns:
        if c not in df.columns: df[c] = ""
    return df[columns]


def save_csv(df, path, columns):
    for c in columns:
        if c not in df.columns: df[c] = ""
    df[columns].to_csv(path, index=False)


def parse_comber_plan(upload):
    raw=pd.read_excel(upload,sheet_name=0,header=None)
    if raw.shape[1]<11: raise ValueError("Formato non riconosciuto: sono attese almeno 11 colonne.")
    week=str(raw.iloc[1,2]).replace(".0","").strip()
    dates=pd.to_datetime(raw.iloc[:,1],errors="coerce").ffill()
    starts=[i for i in range(3,len(raw)) if str(raw.iloc[i,5]).strip() not in ["","nan"] and str(raw.iloc[i,10]).strip().lower()=="comber"]
    plans=[]
    for pos,i in enumerate(starts):
        stop=starts[pos+1] if pos+1<len(starts) else len(raw)
        block=raw.iloc[i:stop].copy()
        extraction_no=pd.to_numeric(block.iloc[:,3],errors="coerce")
        valid=block[extraction_no.notna()]
        if valid.empty: continue
        first_i=valid.index[0]; last_i=valid.index[-1]
        product=str(raw.iloc[i,5]).strip(); drug_lot=str(raw.iloc[i,7]).strip()
        planned=pd.to_numeric(raw.iloc[i,6],errors="coerce")
        per_ext=pd.to_numeric(valid.iloc[:,4],errors="coerce").dropna()
        year=int(dates.iloc[first_i].year)
        plan_id=f"{year}-W{int(float(week)):02d}-{drug_lot or pos+1}"
        plans.append({
            "piano_id":plan_id,"settimana":week,"data_inizio":dates.iloc[first_i].date().isoformat(),"data_fine":dates.iloc[last_i].date().isoformat(),
            "ora_inizio":str(raw.iloc[first_i,2]).strip(),"ora_fine":str(raw.iloc[last_i,2]).strip().split("-")[-1],
            "prodotto":product,"lotto_droga":drug_lot,"estrazioni_pianificate":int(extraction_no.notna().sum()),
            "kg_per_estrazione":float(per_ext.mean()) if not per_ext.empty else 0,"kg_pianificati":float(planned) if pd.notna(planned) else float(per_ext.sum()),
            "impianto":"Comber","caricato_il":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
    if not plans: raise ValueError("Nessuna campagna Comber trovata nel file.")
    return pd.DataFrame(plans,columns=COL_PLANNING)


def _clock(value, fallback, use_end=False):
    parts=str(value).strip().split("-")
    text=(parts[-1] if use_end else parts[0]).strip().replace("24:00","00:00")
    try: return datetime.strptime(text,"%H:%M").time()
    except Exception: return fallback


def _comber_extractions(events):
    """Una sola riga logica per estrazione, anche quando attraversa più turni."""
    if events.empty:
        return pd.DataFrame(columns=["lotto","numero_estrazione","kg_droga","completata"])
    work=events.copy()
    work["kg_num"]=pd.to_numeric(work["kg_droga"],errors="coerce").fillna(0)
    work["estrazione"]=pd.to_numeric(work["numero_estrazione"],errors="coerce").fillna(0).astype(int)
    work["_key"]=work["lotto"].astype(str).str.strip()+"|"+work["estrazione"].astype(str)
    rows=[]
    for _,grp in work.groupby("_key",sort=False):
        rows.append({
            "lotto":str(grp.iloc[0]["lotto"]).strip(),
            "numero_estrazione":int(grp.iloc[0]["estrazione"]),
            "kg_droga":float(grp["kg_num"].max()),
            "completata":bool((grp["stato_estrazione"]=="Completata").any()),
        })
    return pd.DataFrame(rows)


def comber_daily_status(plans, selected_day, as_of=None):
    selected_day=pd.Timestamp(selected_day).date()
    as_of=as_of or datetime.now()
    work=plans.copy()
    starts=pd.to_datetime(work["data_inizio"],errors="coerce").dt.date
    ends=pd.to_datetime(work["data_fine"],errors="coerce").dt.date
    active=work[(starts<=selected_day)&(ends>=selected_day)].copy()

    # Se una campagna copre più giorni, il carico viene ripartito sui giorni del piano.
    if not active.empty:
        active["_giorni"]=[
            max(((pd.Timestamp(r["data_fine"])-pd.Timestamp(r["data_inizio"])).days+1),1)
            for _,r in active.iterrows()
        ]
        active["kg_giorno"]=pd.to_numeric(active["kg_pianificati"],errors="coerce").fillna(0)/active["_giorni"]
        active["estrazioni_giorno"]=pd.to_numeric(active["estrazioni_pianificate"],errors="coerce").fillna(0)/active["_giorni"]
    else:
        active["kg_giorno"]=pd.Series(dtype=float)
        active["estrazioni_giorno"]=pd.Series(dtype=float)

    events=read_csv(EVENTI_FILE,COL_EVENTI)
    comber=events[
        (events["macchina"]=="Comber")&
        (events["tipo_evento"]=="Produzione")&
        (events["data_turno"].astype(str)==selected_day.isoformat())
    ].copy()
    extractions=_comber_extractions(comber)
    completed=extractions[extractions["completata"]] if not extractions.empty else extractions
    actual_kg=float(completed["kg_droga"].sum()) if not completed.empty else 0.0
    completed_count=int(len(completed))
    in_progress_count=int((~extractions["completata"]).sum()) if not extractions.empty else 0
    planned_kg=float(active["kg_giorno"].sum()) if not active.empty else 0.0
    planned_count=float(active["estrazioni_giorno"].sum()) if not active.empty else 0.0

    expected=0.0
    if selected_day<as_of.date(): expected=100.0
    elif selected_day==as_of.date() and not active.empty:
        start=min(_clock(v,time(6)) for v in active["ora_inizio"])
        end=max(_clock(v,time(22)) for v in active["ora_fine"])
        start_dt=datetime.combine(selected_day,start)
        end_dt=datetime.combine(selected_day,end)
        if end_dt<=start_dt: end_dt+=timedelta(days=1)
        expected=max(0.0,min(100.0,(as_of-start_dt).total_seconds()/(end_dt-start_dt).total_seconds()*100))

    kg_pct=pct(actual_kg,planned_kg)
    count_pct=pct(completed_count,planned_count)
    actual_pct=max(kg_pct,count_pct)
    if selected_day>as_of.date():
        light,label="🔵","PROGRAMMATO"
    elif planned_kg<=0 and planned_count<=0:
        light,label="⚪","NESSUN PIANO"
    elif actual_pct>=100:
        light,label="🟢","COMPLETATO"
    elif selected_day<as_of.date():
        light,label="🔴","IN RITARDO"
    elif actual_pct+10>=expected:
        light,label="🟢","IN LINEA"
    else:
        light,label="🟡","SOTTO IL RITMO ATTESO"

    plan_ids=set(active["piano_id"].astype(str).str.strip()) if not active.empty else set()
    linked=comber["piano_id"].astype(str).str.strip().isin(plan_ids) if plan_ids else pd.Series(False,index=comber.index)
    # Con un solo piano giornaliero, le registrazioni storiche senza piano_id sono
    # considerate riconciliate; con più piani restano evidenziate per verifica.
    if len(active)==1:
        linked=linked | (comber["piano_id"].astype(str).str.strip()=="")
    unplanned=comber[~linked].copy()
    unplanned_lots=sorted({str(x).strip() for x in unplanned["lotto"] if str(x).strip()})
    return {
        "piani":active,"estrazioni":extractions,"eventi_fuori_piano":unplanned,
        "kg_pianificati":planned_kg,"kg_effettivi":actual_kg,
        "estrazioni_pianificate":planned_count,"estrazioni_completate":completed_count,
        "estrazioni_in_corso":in_progress_count,"atteso_pct":expected,
        "avanzamento_pct":actual_pct,"semaforo":light,"stato":label,
        "lotti_fuori_piano":unplanned_lots,
    }


def comber_weekly_status(plans, as_of=None):
    """Stato di ogni prodotto/campagna della settimana, senza selezione del giorno."""
    as_of=as_of or datetime.now()
    events=read_csv(EVENTI_FILE,COL_EVENTI)
    comber=events[(events["macchina"]=="Comber")&(events["tipo_evento"]=="Produzione")].copy()
    comber["_data"]=pd.to_datetime(comber["data_turno"],errors="coerce").dt.date
    rows=[]; assigned=set()
    plan_records=plans.to_dict("records")
    for p in plan_records:
        start_day=pd.to_datetime(p["data_inizio"],errors="coerce").date()
        end_day=pd.to_datetime(p["data_fine"],errors="coerce").date()
        plan_id=str(p["piano_id"]).strip()
        explicit=comber[comber["piano_id"].astype(str).str.strip()==plan_id]
        candidates=comber[
            (comber["_data"]>=start_day)&(comber["_data"]<=end_day)&
            (comber["piano_id"].astype(str).str.strip()=="")
        ]
        # Le registrazioni precedenti prive di piano_id vengono riconciliate solo
        # quando in quella data esiste una sola campagna Comber.
        inferred_indexes=[]
        for idx,event in candidates.iterrows():
            active_count=sum(
                pd.to_datetime(q["data_inizio"],errors="coerce").date()<=event["_data"]<=pd.to_datetime(q["data_fine"],errors="coerce").date()
                for q in plan_records
            )
            if active_count==1: inferred_indexes.append(idx)
        linked=pd.concat([explicit,comber.loc[inferred_indexes]],ignore_index=False).drop_duplicates()
        assigned.update(linked.index.tolist())
        extractions=_comber_extractions(linked)
        completed=extractions[extractions["completata"]] if not extractions.empty else extractions
        actual_kg=float(completed["kg_droga"].sum()) if not completed.empty else 0.0
        completed_count=int(len(completed))
        in_progress=int((~extractions["completata"]).sum()) if not extractions.empty else 0
        planned_kg=float(pd.to_numeric(pd.Series([p["kg_pianificati"]]),errors="coerce").fillna(0).iloc[0])
        planned_count=float(pd.to_numeric(pd.Series([p["estrazioni_pianificate"]]),errors="coerce").fillna(0).iloc[0])
        actual_pct=max(pct(actual_kg,planned_kg),pct(completed_count,planned_count))
        start_dt=datetime.combine(start_day,_clock(p["ora_inizio"],time(6)))
        end_dt=datetime.combine(end_day,_clock(p["ora_fine"],time(22),use_end=True))
        if end_dt<=start_dt: end_dt+=timedelta(days=1)
        if as_of<start_dt:
            expected=0.0; light="🔵"; label="PROGRAMMATO"
        else:
            expected=max(0.0,min(100.0,(as_of-start_dt).total_seconds()/(end_dt-start_dt).total_seconds()*100))
            if actual_pct>=100:
                light="🟢"; label="COMPLETATO"
            elif as_of>end_dt:
                light="🔴"; label="IN RITARDO"
            elif actual_pct+10>=expected:
                light="🟢"; label="IN LINEA"
            else:
                light="🟡"; label="SOTTO IL RITMO"
        rows.append({
            **p,"semaforo":light,"stato":label,"avanzamento_pct":actual_pct,
            "avanzamento_atteso_pct":expected,"kg_effettivi":actual_kg,
            "estrazioni_completate":completed_count,"estrazioni_in_corso":in_progress,
            "lotti_produzione":"; ".join(dict.fromkeys(linked["lotto"].astype(str))) if not linked.empty else "",
        })
    result=pd.DataFrame(rows)
    if plans.empty:
        return result,comber.iloc[0:0]
    week_start=pd.to_datetime(plans["data_inizio"],errors="coerce").min().date()
    week_end=pd.to_datetime(plans["data_fine"],errors="coerce").max().date()
    in_week=comber[(comber["_data"]>=week_start)&(comber["_data"]<=week_end)]
    unplanned=in_week[~in_week.index.isin(assigned)].copy()
    return result,unplanned


def parse_mescole_plan(upload):
    raw=pd.read_excel(upload,sheet_name=0,dtype=str).fillna("")
    raw.columns=[str(c).strip().upper() for c in raw.columns]
    aliases={"CODICE":"CODART","DESCRIZIONE":"DESART","QUANTITÀ":"QUANTITA","DATA PREVISTA":"DATEVA"}
    raw=raw.rename(columns={k:v for k,v in aliases.items() if k in raw.columns and v not in raw.columns})
    missing=[c for c in ["CODART","DESART","QUANTITA","DATEVA"] if c not in raw.columns]
    if missing: raise ValueError("Colonne mancanti: "+", ".join(missing)+". Servono CODART, DESART, QUANTITA e DATEVA.")
    def plan_date(value):
        text=str(value).strip()
        return pd.to_datetime(text,errors="coerce",dayfirst=not (len(text)>=10 and text[4:5]=="-" and text[7:8]=="-"))

    rows=[]
    for i,r in raw.iterrows():
        code=str(r.get("CODART","")).strip(); desc=str(r.get("DESART","")).strip()
        if not code: continue
        ref="-".join(str(r.get(c,"")).strip() for c in ["TIPDOC","NUMDOC","SERIE"] if str(r.get(c,"")).strip())
        planned=num(r.get("QUANTITA",0)); due=plan_date(r.get("DATEVA",""))
        doc=plan_date(r.get("DATDOC",""))
        plan_id=f"MIX-{ref or 'PIANO'}-{i+1}-{code}"
        monday=(due-timedelta(days=due.weekday())).date() if pd.notna(due) else None
        iso=due.isocalendar() if pd.notna(due) else None
        rows.append({
            "piano_id":plan_id,"settimana":f"{iso.year}-W{iso.week:02d}" if iso else "",
            "data_inizio_settimana":monday.isoformat() if monday else "",
            "data_fine_settimana":(monday+timedelta(days=6)).isoformat() if monday else "",
            "data_documento":doc.date().isoformat() if pd.notna(doc) else "",
            "data_prevista":due.date().isoformat() if pd.notna(due) else "","riferimento":ref,
            "codice":code,"descrizione":desc,"quantita_pianificata":planned,
            "quantita_evasa":num(r.get("QTAEVA",0)),"stato_origine":str(r.get("EFFETTIVA","")).strip(),
            "caricato_il":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
    if not rows: raise ValueError("Nessuna riga di pianificazione Mescole valida trovata.")
    return pd.DataFrame(rows,columns=COL_MESCOLE_PLANNING)


def normalize_mescole_plans(plans):
    plans=plans.copy()
    due=pd.to_datetime(plans["data_prevista"],errors="coerce")
    for idx,value in due.items():
        if pd.isna(value): continue
        monday=(value-timedelta(days=value.weekday())).date()
        iso=value.isocalendar()
        plans.loc[idx,"settimana"]=f"{iso.year}-W{iso.week:02d}"
        plans.loc[idx,"data_inizio_settimana"]=monday.isoformat()
        plans.loc[idx,"data_fine_settimana"]=(monday+timedelta(days=6)).isoformat()
    return plans


def mescole_planning_status(plans,as_of=None):
    plans=normalize_mescole_plans(plans)
    events=read_csv(EVENTI_FILE,COL_EVENTI)
    events=events[(events["macchina"]=="Mescole")&(events["tipo_evento"]=="Produzione")].copy()
    events["data_evento"]=pd.to_datetime(events["data_turno"],errors="coerce")
    events["quantita_finale_num"]=pd.to_numeric(events["quantita_finale"],errors="coerce").fillna(0)
    today=as_of or date.today(); rows=[]
    grouped=plans.groupby(["settimana","data_inizio_settimana","data_fine_settimana","codice","descrizione"],dropna=False,sort=True)
    for keys,group in grouped:
        week,start_txt,end_txt,code,description=keys
        start=pd.to_datetime(start_txt,errors="coerce"); end=pd.to_datetime(end_txt,errors="coerce")
        planned=pd.to_numeric(group["quantita_pianificata"],errors="coerce").fillna(0).sum()
        linked=events[(events["codice"]==str(code))]
        if pd.notna(start) and pd.notna(end):
            linked=linked[(linked["data_evento"].dt.date>=start.date())&(linked["data_evento"].dt.date<=end.date())]
        closed=linked[linked["tipo_produzione"]=="Chiusura lotto"]
        produced=float(closed["quantita_finale_num"].sum())
        actual_pct=pct(produced,planned)
        if pd.isna(start) or pd.isna(end) or today<start.date(): expected_pct=0.0
        elif today>end.date(): expected_pct=100.0
        else: expected_pct=min(max(today.weekday()+1,0),5)/5*100
        if planned>0 and produced>=planned:
            status="Completato"; pace="Completato"
        elif pd.notna(end) and today>end.date():
            status="In ritardo"; pace="In ritardo"
        elif pd.notna(start) and today<start.date():
            status="Da avviare"; pace="Non iniziata"
        else:
            status="In corso" if produced>0 or not linked.empty else "Da avviare"
            delta=actual_pct-expected_pct
            pace="In anticipo" if delta>10 else ("In ritardo" if delta<-10 else "In linea")
        lots="; ".join(dict.fromkeys(x for x in linked["lotto"].astype(str) if x.strip()))
        rows.append({
            "settimana":week,"data_inizio_settimana":start_txt,"data_fine_settimana":end_txt,
            "codice":code,"descrizione":description,"quantita_pianificata":float(planned),
            "quantita_prodotta":produced,"avanzamento_pct":actual_pct,"avanzamento_atteso_pct":expected_pct,
            "stato":status,"ritmo":pace,"lotti_produzione":lots,
        })
    return pd.DataFrame(rows)


def mescole_unplanned_lots(plans,week):
    plans=normalize_mescole_plans(plans)
    selected=plans[plans["settimana"]==week]
    if selected.empty: return pd.DataFrame()
    start=pd.to_datetime(selected["data_inizio_settimana"],errors="coerce").min()
    end=pd.to_datetime(selected["data_fine_settimana"],errors="coerce").max()
    planned_codes=set(selected["codice"].astype(str))
    events=read_csv(EVENTI_FILE,COL_EVENTI)
    events=events[(events["macchina"]=="Mescole")&(events["tipo_evento"]=="Produzione")].copy()
    events["data_evento"]=pd.to_datetime(events["data_turno"],errors="coerce")
    events=events[(events["data_evento"].dt.date>=start.date())&(events["data_evento"].dt.date<=end.date())]
    events=events[~events["codice"].astype(str).isin(planned_codes)]
    rows=[]
    for lot,group in events.groupby("lotto",sort=False):
        if not str(lot).strip(): continue
        closed=group[group["tipo_produzione"]=="Chiusura lotto"]
        rows.append({
            "lotto":lot,"codice":group.iloc[-1]["codice"],"descrizione":group.iloc[-1]["descrizione"],
            "data":group.iloc[0]["data_turno"],"stato":"Completato" if not closed.empty else "In corso",
            "quantita":pd.to_numeric(closed["quantita_finale"],errors="coerce").fillna(0).sum(),
        })
    return pd.DataFrame(rows)


def update_mescole_products(plans):
    products=read_csv(PRODOTTI_FILE,COL_PRODOTTI)
    for r in plans[["codice","descrizione"]].drop_duplicates().itertuples(index=False):
        mask=(products["tipo"]=="Mescola")&(products["codice"]==str(r.codice))
        products=products[~mask]
        products=pd.concat([products,pd.DataFrame([{"tipo":"Mescola","codice":str(r.codice),"descrizione":str(r.descrizione),"pct_puro_standard":0,"attivo":"SI"}])],ignore_index=True)
    save_csv(products,PRODOTTI_FILE,COL_PRODOTTI)


def mescole_target_config():
    config=read_csv(MESCOLE_TARGET_FILE,COL_MESCOLE_TARGET)
    if config.empty:
        return {"target_kg_giorno":0.0,"target_kg_ora_uomo":0.0}
    return {
        "target_kg_giorno":num(config.iloc[0]["target_kg_giorno"]),
        "target_kg_ora_uomo":num(config.iloc[0]["target_kg_ora_uomo"]),
    }


def num(v):
    x = pd.to_numeric(str(v).replace(",", "."), errors="coerce")
    return 0.0 if pd.isna(x) else float(x)


def pct(n, d): return n / d * 100 if d else 0.0


def workdays(start, end):
    if end < start: return 0
    return sum(1 for x in pd.date_range(start, end) if x.weekday() < 5)


def previous_workday(day):
    previous=day-timedelta(days=1)
    while previous.weekday()>=5:
        previous-=timedelta(days=1)
    return previous


def target_config():
    df=read_csv(TARGET_FILE,COL_TARGET)
    for c in ["target_fisico_giorno","target_equivalente_giorno","giorni_produttivi_anno"]:
        df[c]=pd.to_numeric(df[c],errors="coerce").fillna(0)
    return df


def annual_day_target(machine, metric):
    df=target_config(); row=df[df["macchina"]==machine]
    col="target_equivalente_giorno" if metric=="equivalente" else "target_fisico_giorno"
    return float(row.iloc[0][col]) if not row.empty else DEFAULT_TARGET[machine][metric]


def annual_workdays(machine):
    df=target_config(); row=df[df["macchina"]==machine]
    return float(row.iloc[0]["giorni_produttivi_anno"]) if not row.empty else 220


def target_period(machine, metric, start, end, annual=False):
    if annual: return annual_day_target(machine, metric) * annual_workdays(machine)
    return annual_day_target(machine, metric) * workdays(start, end)


def equivalent_comber(kg_drug, kg_pure):
    # Regola aziendale: minimo convenzionale 15%; rese migliori restano reali.
    return max(kg_drug * 0.15, kg_pure)


def equivalent_spray(kg_semi, kg_pure):
    # Kg di puro riferiti allo standard 60/40: minimo 40% del semilavorato;
    # se il taglio è inferiore al 60%, si mantiene il puro reale più alto.
    if kg_semi <= 0: return 0.0
    return max(kg_pure, kg_semi * 0.40)


def sync_completed_comber_extractions():
    """Ricostruisce il consuntivo anche per estrazioni salvate in precedenza."""
    events=read_csv(EVENTI_FILE,COL_EVENTI)
    completed=events[
        (events["macchina"]=="Comber")&
        (events["tipo_evento"]=="Produzione")&
        (events["stato_estrazione"]=="Completata")
    ]
    if completed.empty:
        return
    productions=read_csv(LOTTI_FILE,COL_LOTTI)
    changed=False
    for lot,group in completed.groupby("lotto",sort=False):
        if not str(lot).strip():
            continue
        last=group.iloc[-1]
        prod=_create_production(
            "Comber",str(lot),str(last["id_turno"]),str(last["data_turno"]),str(last["turno"]),[]
        )
        productions=productions[~((productions["macchina"]=="Comber")&(productions["lotto"]==str(lot)))]
        productions=pd.concat([productions,pd.DataFrame([prod])],ignore_index=True)
        changed=True
    if changed:
        save_csv(productions,LOTTI_FILE,COL_LOTTI)


def prep_production():
    sync_completed_comber_extractions()
    df = read_csv(LOTTI_FILE, COL_LOTTI)
    if df.empty: return df
    df["data_turno"] = pd.to_datetime(df["data_turno"], errors="coerce")
    for c in ["kg_droga","kg_liquido","residuo_secco_pct","kg_puro","kg_semilavorato","pct_puro_semilavorato","kg_puro_equivalente"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    # Ricalcolo difensivo dei KPI: alcuni record storici riportavano per
    # Comber il solo minimo del 15% anche quando il puro reale era maggiore.
    comber=df["macchina"].eq("Comber")
    df.loc[comber,"kg_puro_equivalente"] = pd.concat(
        [df.loc[comber,"kg_droga"].mul(0.15),df.loc[comber,"kg_puro"]],axis=1
    ).max(axis=1)
    ev200=df["macchina"].eq("EV200")
    df.loc[ev200,"kg_puro_equivalente"] = df.loc[ev200,"kg_puro"]
    spray=df["macchina"].eq("Spray Dryer")
    df.loc[spray,"kg_puro_equivalente"] = pd.concat(
        [df.loc[spray,"kg_puro"],df.loc[spray,"kg_semilavorato"].mul(0.40)],axis=1
    ).max(axis=1)
    return df


def save_history_event_edits(original,edited):
    """Salva le correzioni dello Storico e riallinea consuntivi e turni."""
    all_events=read_csv(EVENTI_FILE,COL_EVENTI)
    updated=all_events.copy()
    for row in edited.to_dict("records"):
        idx=updated["id_evento"]==str(row["id_evento"])
        if idx.any():
            for column in COL_EVENTI:
                updated.loc[idx,column]=row.get(column,"")
    affected_shifts=set(original["id_turno"].astype(str))|set(edited["id_turno"].astype(str))
    for shift_id in affected_shifts:
        group=updated[updated["id_turno"].astype(str)==shift_id]
        if group.empty: continue
        ok,message=_validate(group.to_dict("records"),str(group.iloc[0]["turno"]),True)
        if not ok:
            return False,f"Turno {shift_id}: {message}"
    save_csv(updated,EVENTI_FILE,COL_EVENTI)

    productions=read_csv(LOTTI_FILE,COL_LOTTI)
    affected_pairs=set()
    for frame in [original,edited]:
        affected_pairs.update(
            (str(r.macchina),str(r.lotto)) for r in frame.itertuples()
            if str(r.lotto).strip()
        )
    for machine,lot in affected_pairs:
        productions=productions[~((productions["macchina"]==machine)&(productions["lotto"]==lot))]
        lot_events=updated[
            (updated["macchina"]==machine)&(updated["lotto"]==lot)&
            (updated["tipo_evento"]=="Produzione")
        ]
        eligible=lot_events[
            (lot_events["tipo_produzione"]=="Chiusura lotto")|
            ((lot_events["macchina"]=="Comber")&(lot_events["stato_estrazione"]=="Completata"))
        ]
        if not eligible.empty:
            last=eligible.iloc[-1]
            production=_create_production(machine,lot,last["id_turno"],last["data_turno"],str(last["turno"]),[])
            productions=pd.concat([productions,pd.DataFrame([production])],ignore_index=True)
    save_csv(productions,LOTTI_FILE,COL_LOTTI)

    turns=read_csv(TURNI_FILE,COL_TURNI)
    for shift_id in affected_shifts:
        shift_events=updated[updated["id_turno"].astype(str)==shift_id]
        if shift_events.empty: continue
        production_hours=pd.to_numeric(
            shift_events.loc[shift_events["tipo_evento"]=="Produzione","durata_h"],errors="coerce"
        ).fillna(0).sum()
        idx=turns["id_turno"].astype(str)==shift_id
        if idx.any():
            turns.loc[idx,"ore_produzione"]=float(production_hours)
            turns.loc[idx,"ore_fermo"]=max(8-float(production_hours),0)
    save_csv(turns,TURNI_FILE,COL_TURNI)
    return True,"Eventi, produzioni, dashboard e ore turno aggiornati."


def delete_history_events(event_ids):
    """Elimina gli eventi selezionati e ricostruisce tutti i dati derivati."""
    all_events=read_csv(EVENTI_FILE,COL_EVENTI)
    removed=all_events[all_events["id_evento"].isin(event_ids)].copy()
    if removed.empty:
        return False,"Nessun evento selezionato."
    updated=all_events[~all_events["id_evento"].isin(event_ids)].copy()
    save_csv(updated,EVENTI_FILE,COL_EVENTI)

    productions=read_csv(LOTTI_FILE,COL_LOTTI)
    affected_pairs={
        (str(r.macchina),str(r.lotto)) for r in removed.itertuples()
        if str(r.lotto).strip()
    }
    for machine,lot in affected_pairs:
        productions=productions[~((productions["macchina"]==machine)&(productions["lotto"]==lot))]
        lot_events=updated[
            (updated["macchina"]==machine)&(updated["lotto"]==lot)&
            (updated["tipo_evento"]=="Produzione")
        ]
        eligible=lot_events[
            (lot_events["tipo_produzione"]=="Chiusura lotto")|
            ((lot_events["macchina"]=="Comber")&(lot_events["stato_estrazione"]=="Completata"))
        ]
        if not eligible.empty:
            last=eligible.iloc[-1]
            production=_create_production(machine,lot,last["id_turno"],last["data_turno"],str(last["turno"]),[])
            productions=pd.concat([productions,pd.DataFrame([production])],ignore_index=True)
    save_csv(productions,LOTTI_FILE,COL_LOTTI)

    turns=read_csv(TURNI_FILE,COL_TURNI)
    for shift_id in removed["id_turno"].astype(str).unique():
        remaining=updated[updated["id_turno"].astype(str)==shift_id]
        if remaining.empty:
            turns=turns[turns["id_turno"].astype(str)!=shift_id]
            continue
        production_hours=pd.to_numeric(
            remaining.loc[remaining["tipo_evento"]=="Produzione","durata_h"],errors="coerce"
        ).fillna(0).sum()
        idx=turns["id_turno"].astype(str)==shift_id
        if idx.any():
            turns.loc[idx,"ore_produzione"]=float(production_hours)
            turns.loc[idx,"ore_fermo"]=max(8-float(production_hours),0)
    save_csv(turns,TURNI_FILE,COL_TURNI)
    return True,f"Eliminati {len(removed)} eventi. Dashboard e consuntivi ricalcolati."


def period_value(df, machine, metric, start, end):
    if df.empty: return 0.0
    x = df[(df["macchina"] == machine) & (df["data_turno"].dt.date >= start) & (df["data_turno"].dt.date <= end)]
    col = "kg_puro_equivalente" if metric == "equivalente" else ("kg_semilavorato" if machine == "Spray Dryer" else "kg_puro")
    return float(x[col].sum())


def fmt(v): return f"{v:,.0f}".replace(",", ".")


def fmt_it(v,decimals=1):
    return f"{v:,.{decimals}f}".replace(",","_").replace(".",",").replace("_",".")


def summary_band(name, basis, css, df, machine, metric, periods):
    cells = [f'<div><div class="name">{html.escape(name)} (kg)</div><div class="basis">{html.escape(basis)}</div></div>']
    for label, (start, end) in periods.items():
        cells.append(f'<div><div class="value">{fmt(period_value(df,machine,metric,start,end))}</div><div class="label">{label}</div></div>')
    st.markdown(f'<div class="summary {css}">{"".join(cells)}</div>', unsafe_allow_html=True)


def ach_class(v): return "ach-good" if v >= 100 else ("ach-mid" if v >= 75 else "ach-low")


def dashboard_table(df, today):
    yesterday = previous_workday(today)
    week_start = today - timedelta(days=today.weekday()); week_end = week_start + timedelta(days=6)
    month_start = today.replace(day=1); month_end = (pd.Timestamp(month_start) + pd.offsets.MonthEnd()).date()
    year_start = today.replace(month=1, day=1); year_end = today.replace(month=12, day=31)
    try: ly_end = today.replace(year=today.year - 1)
    except ValueError: ly_end = today.replace(year=today.year - 1, day=28)
    ly_start = ly_end.replace(month=1, day=1)
    # La dashboard produttiva riporta soltanto i due output industriali:
    # estrazione acquosa e prodotto essiccato. EV200 resta nella dashboard OEE.
    rows = [
        ("Comber – Pure extract", "Comber", "fisico"), ("Comber – Pure equivalent 15%", "Comber", "equivalente"),
        ("Spray Dryer – Semi-finished product", "Spray Dryer", "fisico"), ("Spray Dryer – Pure equivalent 40%", "Spray Dryer", "equivalente"),
    ]
    heads = ["Production", "Yesterday", "Yesterday Target", "Achievement", "Week to Date", "Week Target", "Achievement", "Month to Date", "Month Target", "Achievement", "Year to Date", "Year Target", "Achievement", "Last Year YTD"]
    body = []
    for label, machine, metric in rows:
        ya = period_value(df,machine,metric,yesterday,yesterday); yt=target_period(machine,metric,yesterday,yesterday)
        wa = period_value(df,machine,metric,week_start,today); wt=target_period(machine,metric,week_start,week_end)
        ma = period_value(df,machine,metric,month_start,today); mt=target_period(machine,metric,month_start,month_end)
        aa = period_value(df,machine,metric,year_start,today); at=target_period(machine,metric,year_start,year_end,True)
        ly = period_value(df,machine,metric,ly_start,ly_end)
        vals=[ya,yt,pct(ya,yt),wa,wt,pct(wa,wt),ma,mt,pct(ma,mt),aa,at,pct(aa,at),ly]
        tds=[f"<td>{html.escape(label)}</td>"]
        for i,v in enumerate(vals):
            is_ach=i in (2,5,8,11); cls=f' class="{ach_class(v)}"' if is_ach else ""
            tds.append(f"<td{cls}>{v:.0f}%</td>" if is_ach else f"<td>{fmt(v)}</td>")
        body.append("<tr>"+"".join(tds)+"</tr>")
    return '<div class="table-wrap"><h3>Production (kg) by line</h3><table class="prod-table"><thead><tr>'+"".join(f"<th>{h}</th>" for h in heads)+"</tr></thead><tbody>"+"".join(body)+"</tbody></table></div>"


def gauge(value, title):
    fig=go.Figure(go.Indicator(mode="gauge+number",value=value*100,number={"suffix":"%"},title={"text":title},gauge={"axis":{"range":[0,100]},"bar":{"color":"#238B73"},"steps":[{"range":[0,60],"color":"#F3B5B5"},{"range":[60,80],"color":"#F7D98A"},{"range":[80,100],"color":"#8DDBBE"}]}))
    fig.update_layout(height=290,margin=dict(l=25,r=25,t=55,b=15),paper_bgcolor="white",font_color="#24313A")
    return fig


def xlsx_export(machine=None):
    out=BytesIO()
    with pd.ExcelWriter(out,engine="openpyxl") as w:
        turns=read_csv(TURNI_FILE,COL_TURNI)
        productions=read_csv(LOTTI_FILE,COL_LOTTI)
        events=read_csv(EVENTI_FILE,COL_EVENTI)
        if machine:
            turns=turns[turns["macchina"]==machine]
            productions=productions[productions["macchina"]==machine]
            events=events[events["macchina"]==machine]
        turns.to_excel(w,"Turni",index=False)
        productions.to_excel(w,"Produzioni",index=False)
        events.to_excel(w,"Eventi",index=False)
        read_csv(PRODOTTI_FILE,COL_PRODOTTI).to_excel(w,"Anagrafica prodotti",index=False)
        read_csv(CAUSALI_FILE,COL_CAUSALI).to_excel(w,"Causali",index=False)
    out.seek(0); return out


def oee_results(turns, prod):
    results=[]
    for machine in PROCESS_MACHINES:
        x=turns[turns["macchina"]==machine].copy() if not turns.empty else pd.DataFrame(columns=COL_TURNI)
        for c in ["ore_pianificate","ore_produzione","ore_fermo"]:
            x[c]=pd.to_numeric(x[c],errors="coerce").fillna(0)
        planned=float(x["ore_pianificate"].sum()); production=float(x["ore_produzione"].sum())
        raw_availability=production/planned if planned else 0
        availability=min(raw_availability,1.0)
        registered_ids=set(x["id_turno"].astype(str))
        machine_prod=prod[(prod["macchina"]==machine)&(prod["id_turno"].astype(str).isin(registered_ids))].copy() if not prod.empty else pd.DataFrame()
        output=float(machine_prod["kg_puro_equivalente"].sum()) if not machine_prod.empty else 0
        # I target configurati sono giornalieri su 24 ore: vengono rapportati
        # alle ore pianificate effettivamente registrate.
        target=annual_day_target(machine,"equivalente")*(planned/24) if planned else 0
        raw_performance=output/target if target else 0
        performance=min(raw_performance,1.0)
        oee=min(availability*performance*QUALITA,1.0)
        results.append({"Macchina":machine,"Disponibilità":availability,"Performance":performance,"Performance grezza":raw_performance,"Qualità":QUALITA,"OEE":oee,"Peso":planned})
    return results


def process_indicator(prod,machine,turns=None):
    if prod.empty: return None if machine=="EV200" else 0.0
    x=prod[prod["macchina"]==machine].copy()
    if turns is not None and not turns.empty:
        ids=set(turns[turns["macchina"]==machine]["id_turno"].astype(str))
        x=x[x["id_turno"].astype(str).isin(ids)]
    if x.empty: return None if machine=="EV200" else 0.0
    if machine=="Comber":
        valid=x[x["kg_droga"]>0]
        if valid.empty: return 0.0
        # Media aritmetica delle rese dei singoli lotti.
        return float((valid["kg_puro"]/valid["kg_droga"]*100).mean())
    if machine=="Spray Dryer":
        valid=x[x["kg_semilavorato"]>0]
        if valid.empty: return 0.0
        # Taglio = quota non pura del semilavorato; media aritmetica dei lotti.
        return float((100-valid["pct_puro_semilavorato"]).mean())
    return None


def render_oee_unified(turns, prod):
    results=oee_results(turns,prod)
    cols=st.columns(3)
    for col,r in zip(cols,results):
        with col:
            st.plotly_chart(gauge(r["OEE"],f'OEE {r["Macchina"]}'),use_container_width=True)
            indicator=process_indicator(prod,r["Macchina"],turns)
            metric_cols=st.columns(3 if indicator is not None else 2)
            a,b=metric_cols[0],metric_cols[1]
            a.metric("Availability",f'{r["Disponibilità"]:.1%}')
            b.metric("Performance",f'{r["Performance"]:.1%}')
            if r["Macchina"]=="Comber": metric_cols[2].metric("Average mass yield",f"{indicator:.1f}%")
            elif r["Macchina"]=="Spray Dryer": metric_cols[2].metric("Average cut",f"{indicator:.1f}%")
            if r["Performance grezza"]>1.05:
                st.warning(f'Output superiore allo standard teorico ({r["Performance grezza"]:.1%}). Verificare dati e target; ai fini OEE la performance è limitata al 100%.')
    overall_num=sum(r["OEE"]*r["Peso"] for r in results); overall_den=sum(r["Peso"] for r in results)
    overall=overall_num/overall_den if overall_den else 0
    st.metric("Overall weighted OEE",f"{overall:.1%}")
    if turns.empty:
        st.info("I cruscotti sono a zero finché non vengono salvate le ore dei turni nelle sezioni macchina.")


init_data()
if LOGO_FILE.exists(): st.sidebar.image(str(LOGO_FILE),width=170)
st.sidebar.markdown("### Produzione Lauria")
area=st.sidebar.radio("Area",[
    "Comber","Pianificazione Comber","EV200","Spray Dryer","Mescole","Pianificazione Mescole","Dashboard Mescole",
    "Dashboard OEE","Production vs Target",
    "Excel","Storico","Target","Anagrafiche e causali",
])
page=f"Turno {area}" if area in MACCHINE else area
st.sidebar.caption(f"Versione {VERSIONE} · Qualità standard {QUALITA:.0%}")

if page=="Pianificazione Comber":
    st.title("Pianificazione Comber")
    st.caption("Carica il piano settimanale e controlla giorno per giorno avanzamento, ritmo e lavorazioni fuori piano.")
    uploaded_plan=st.file_uploader("Pianificazione settimanale estrazione",type=["xls","xlsx"],key="comber_plan_upload")
    preview=None
    if uploaded_plan:
        try:
            preview=parse_comber_plan(uploaded_plan)
            st.success(f"Rilevate {len(preview)} campagne Comber · {int(pd.to_numeric(preview['estrazioni_pianificate']).sum())} estrazioni · {pd.to_numeric(preview['kg_pianificati']).sum():,.0f} kg pianificati".replace(",","."))
            st.dataframe(preview[["settimana","data_inizio","data_fine","prodotto","lotto_droga","estrazioni_pianificate","kg_per_estrazione","kg_pianificati"]],use_container_width=True,hide_index=True)
            confirm_plan=st.checkbox("Confermo l’importazione del piano Comber")
            if st.button("Importa pianificazione",type="primary",disabled=not confirm_plan):
                existing=read_csv(PLANNING_FILE,COL_PLANNING)
                existing=existing[~existing["piano_id"].isin(preview["piano_id"])]
                save_csv(pd.concat([existing,preview],ignore_index=True),PLANNING_FILE,COL_PLANNING)
                st.success("Pianificazione importata e resa disponibile nella sezione Comber."); st.rerun()
        except Exception as exc:
            st.error(f"Impossibile leggere la pianificazione: {exc}")
    plans=read_csv(PLANNING_FILE,COL_PLANNING)
    st.divider(); st.subheader("Avanzamento pianificazione")
    if plans.empty:
        st.info("Nessuna pianificazione Comber ancora caricata.")
    else:
        weeks=sorted([x for x in plans["settimana"].unique() if str(x).strip()],reverse=True)
        current_iso=date.today().isocalendar()
        current_week=str(current_iso.week)
        selected_week=st.selectbox("Settimana",weeks,index=weeks.index(current_week) if current_week in weeks else 0)
        current=plans[plans["settimana"]==selected_week]
        progress,unplanned=comber_weekly_status(current)
        k1,k2,k3,k4,k5=st.columns(5)
        k1.metric("Prodotti pianificati",len(progress))
        k2.metric("Completati",int((progress["stato"]=="COMPLETATO").sum()))
        k3.metric("In linea",int((progress["stato"]=="IN LINEA").sum()))
        k4.metric("Sotto ritmo",int((progress["stato"]=="SOTTO IL RITMO").sum()))
        k5.metric("In ritardo",int((progress["stato"]=="IN RITARDO").sum()))

        progress["stato_visuale"]=progress["semaforo"]+" "+progress["stato"]
        view=progress[["stato_visuale","data_inizio","prodotto","lotto_droga","ora_inizio","ora_fine","kg_pianificati","kg_effettivi","estrazioni_pianificate","estrazioni_completate","estrazioni_in_corso","avanzamento_pct","avanzamento_atteso_pct"]]
        st.dataframe(view,use_container_width=True,hide_index=True,column_config={
            "stato_visuale":"Stato","data_inizio":"Giorno previsto","prodotto":"Prodotto",
            "lotto_droga":"Lotto droga","ora_inizio":"Inizio previsto","ora_fine":"Fine prevista",
            "kg_pianificati":st.column_config.NumberColumn("Kg pianificati",format="%.1f"),
            "kg_effettivi":st.column_config.NumberColumn("Kg completati",format="%.1f"),
            "estrazioni_pianificate":"Estrazioni pianificate",
            "estrazioni_completate":"Estrazioni completate","estrazioni_in_corso":"In corso",
            "avanzamento_pct":st.column_config.ProgressColumn("Avanzamento reale",min_value=0,max_value=100,format="%.0f%%"),
            "avanzamento_atteso_pct":st.column_config.ProgressColumn("Avanzamento atteso",min_value=0,max_value=100,format="%.0f%%"),
        })
        legend="🔵 Programmato  ·  🟢 In linea/Completato  ·  🟡 Sotto il ritmo  ·  🔴 In ritardo"
        st.caption(legend)
        unplanned_lots=sorted({str(x).strip() for x in unplanned["lotto"] if str(x).strip()})
        if unplanned_lots:
            st.error("🔴 Lotti inseriti fuori pianificazione: "+", ".join(unplanned_lots))
            extra=unplanned[["data_turno","lotto","numero_estrazione","descrizione","ora_inizio","ora_fine","stato_estrazione"]].copy()
            st.dataframe(extra,use_container_width=True,hide_index=True)
        else:
            st.success("Nessun lotto fuori pianificazione nella settimana selezionata.")

elif page=="Pianificazione Mescole":
    st.title("Pianificazione Mescole")
    st.caption("Carica il piano del reparto e controlla quantità pianificate, prodotte, lotti aperti e avanzamento.")
    uploaded=st.file_uploader("Pianificazione reparto Mescole",type=["xls","xlsx"],key="mescole_plan_upload")
    if uploaded:
        try:
            preview=parse_mescole_plan(uploaded)
            st.success(f"Rilevate {len(preview)} righe · {preview['settimana'].nunique()} settimane · {pd.to_numeric(preview['quantita_pianificata']).sum():,.1f} kg pianificati")
            st.dataframe(preview[["settimana","data_inizio_settimana","data_fine_settimana","riferimento","codice","descrizione","quantita_pianificata"]],use_container_width=True,hide_index=True)
            confirm=st.checkbox("Confermo l’importazione del piano Mescole")
            if st.button("Importa pianificazione Mescole",type="primary",disabled=not confirm):
                existing=read_csv(MESCOLE_PLANNING_FILE,COL_MESCOLE_PLANNING)
                existing=existing[~existing["piano_id"].isin(preview["piano_id"])]
                save_csv(pd.concat([existing,preview],ignore_index=True),MESCOLE_PLANNING_FILE,COL_MESCOLE_PLANNING)
                update_mescole_products(preview)
                st.success("Piano importato. I codici sono disponibili anche nella sezione Mescole."); st.rerun()
        except Exception as exc: st.error(f"Impossibile leggere la pianificazione Mescole: {exc}")
    plans=normalize_mescole_plans(read_csv(MESCOLE_PLANNING_FILE,COL_MESCOLE_PLANNING))
    st.divider(); st.subheader("Avanzamento settimanale")
    if plans.empty: st.info("Nessuna pianificazione Mescole ancora caricata.")
    else:
        weeks=sorted([x for x in plans["settimana"].unique() if str(x).strip()],reverse=True)
        current_iso=date.today().isocalendar(); current_week=f"{current_iso.year}-W{current_iso.week:02d}"
        selected_week=st.selectbox("Settimana",weeks,index=weeks.index(current_week) if current_week in weeks else 0)
        weekly_plans=plans[plans["settimana"]==selected_week]
        progress=mescole_planning_status(weekly_plans)
        unplanned=mescole_unplanned_lots(plans,selected_week)
        total_planned=float(progress["quantita_pianificata"].sum()) if not progress.empty else 0
        total_produced=float(progress["quantita_prodotta"].sum()) if not progress.empty else 0
        actual_pct=pct(total_produced,total_planned)
        expected_pct=float(progress["avanzamento_atteso_pct"].max()) if not progress.empty else 0
        pace_delta=actual_pct-expected_pct
        week_start=pd.to_datetime(weekly_plans["data_inizio_settimana"],errors="coerce").min()
        if total_planned and total_produced>=total_planned:
            st.success(f"✅ SETTIMANA COMPLETATA · {fmt_it(total_produced)} kg prodotti su {fmt_it(total_planned)} kg pianificati")
        elif pd.notna(week_start) and date.today()<week_start.date():
            st.info(f"ℹ️ SETTIMANA NON ANCORA INIZIATA · {fmt_it(total_planned)} kg pianificati")
        elif pace_delta>10:
            st.success(f"✅ IN ANTICIPO · avanzamento reale {actual_pct:.1f}% · atteso {expected_pct:.1f}%")
        elif pace_delta>=-10:
            st.success(f"✅ IN LINEA · avanzamento reale {actual_pct:.1f}% · atteso {expected_pct:.1f}%")
        else:
            st.error(f"⚠️ IN RITARDO · avanzamento reale {actual_pct:.1f}% · atteso {expected_pct:.1f}% · scostamento {pace_delta:.1f} punti")
        if not unplanned.empty:
            st.warning(f"⚠️ {len(unplanned)} lotti fuori pianificazione rilevati nella settimana")
        k1,k2,k3,k4=st.columns(4)
        k1.metric("Kg pianificati",fmt_it(total_planned))
        k2.metric("Kg prodotti",fmt_it(total_produced),delta=f"{actual_pct:.1f}%")
        k3.metric("Avanzamento atteso",f"{expected_pct:.1f}%")
        k4.metric("Lotti fuori piano",len(unplanned))
        st.dataframe(progress[["ritmo","stato","codice","descrizione","quantita_pianificata","quantita_prodotta","avanzamento_pct","avanzamento_atteso_pct","lotti_produzione"]],use_container_width=True,hide_index=True,column_config={
            "ritmo":"Rispetto ai tempi","stato":"Stato","codice":"Codice","descrizione":"Prodotto",
            "quantita_pianificata":st.column_config.NumberColumn("Pianificato kg",format="%.1f"),
            "quantita_prodotta":st.column_config.NumberColumn("Prodotto kg",format="%.1f"),
            "avanzamento_pct":st.column_config.ProgressColumn("Avanzamento",min_value=0,max_value=100,format="%.1f%%"),
            "avanzamento_atteso_pct":st.column_config.NumberColumn("Atteso",format="%.1f%%"),
            "lotti_produzione":"Lotti registrati",
        })
        if not unplanned.empty:
            st.subheader("Lotti fuori pianificazione")
            st.dataframe(unplanned,use_container_width=True,hide_index=True,column_config={
                "lotto":"Lotto","codice":"Codice","descrizione":"Prodotto","data":"Data","stato":"Stato",
                "quantita":st.column_config.NumberColumn("Quantità kg",format="%.1f"),
            })

elif page=="Dashboard Mescole":
    st.title("Dashboard Mescole")
    st.caption("Produttività, avanzamento e utilizzo delle risorse del reparto Mescole. Gli indicatori non sono classificati come OEE.")
    today=date.today(); default_start=today.replace(day=1)
    f1,f2=st.columns(2)
    with f1: start=st.date_input("Dal",value=default_start,format="DD/MM/YYYY",key="mix_dash_start")
    with f2: end=st.date_input("Al",value=today,format="DD/MM/YYYY",key="mix_dash_end")
    if end<start:
        st.error("La data finale deve essere successiva alla data iniziale.")
        st.stop()
    target_cfg=mescole_target_config()
    with st.expander("Imposta target Mescole"):
        t1,t2=st.columns(2)
        with t1:
            target_day=st.number_input(
                "Target produzione (kg/giorno)",min_value=0.0,value=float(target_cfg["target_kg_giorno"]),step=10.0,
                help="Target giornaliero utilizzato per calcolare l'obiettivo del periodo selezionato.",
            )
        with t2:
            target_productivity=st.number_input(
                "Target produttività (kg/ora-uomo)",min_value=0.0,value=float(target_cfg["target_kg_ora_uomo"]),step=1.0,
            )
        if st.button("Salva target Mescole",type="primary"):
            save_csv(pd.DataFrame([{
                "target_kg_giorno":target_day,"target_kg_ora_uomo":target_productivity,
            }]),MESCOLE_TARGET_FILE,COL_MESCOLE_TARGET)
            st.success("Target Mescole aggiornati."); st.rerun()

    all_mix=read_csv(EVENTI_FILE,COL_EVENTI)
    all_mix=all_mix[(all_mix["macchina"]=="Mescole")&(all_mix["tipo_evento"]=="Produzione")].copy()
    all_mix["data_evento"]=pd.to_datetime(all_mix["data_turno"],errors="coerce")
    for column in ["durata_h","numero_operatori","quantita_finale","ore_uomo"]:
        all_mix[column]=pd.to_numeric(all_mix[column],errors="coerce").fillna(0)
    all_mix.loc[all_mix["ore_uomo"]<=0,"ore_uomo"]=all_mix["durata_h"]*all_mix["numero_operatori"]
    period=all_mix[(all_mix["data_evento"].dt.date>=start)&(all_mix["data_evento"].dt.date<=end)].copy()
    closures=period[period["tipo_produzione"]=="Chiusura lotto"].copy()

    produced=float(closures["quantita_finale"].sum())
    completed_lots=int(closures["lotto"].astype(str).replace("",pd.NA).dropna().nunique())
    production_hours=float(period["durata_h"].sum())
    person_hours=float(period["ore_uomo"].sum())
    kg_hour=produced/production_hours if production_hours else 0
    kg_person_hour=produced/person_hours if person_hours else 0

    open_lots=[]
    history=all_mix[all_mix["data_evento"].dt.date<=end].sort_values(["data_evento","ora_inizio","id_evento"])
    for row in history.itertuples():
        lot=str(row.lotto).strip()
        if not lot: continue
        if row.tipo_produzione=="Apertura lotto" and lot not in open_lots: open_lots.append(lot)
        elif row.tipo_produzione=="Chiusura lotto" and lot in open_lots: open_lots.remove(lot)

    plans=read_csv(MESCOLE_PLANNING_FILE,COL_MESCOLE_PLANNING)
    plans["data_piano"]=pd.to_datetime(plans["data_prevista"],errors="coerce")
    plans["quantita_pianificata_num"]=pd.to_numeric(plans["quantita_pianificata"],errors="coerce").fillna(0)
    plan_period=plans[(plans["data_piano"].dt.date>=start)&(plans["data_piano"].dt.date<=end)].copy()
    planned=float(plan_period["quantita_pianificata_num"].sum())
    plan_achievement=pct(produced,planned)
    target_period=float(target_cfg["target_kg_giorno"])*workdays(start,end)
    target_achievement=pct(produced,target_period)
    productivity_achievement=pct(kg_person_hour,float(target_cfg["target_kg_ora_uomo"]))

    k1,k2,k3,k4=st.columns(4)
    k1.metric("Kg prodotti",fmt_it(produced))
    k2.metric("Kg pianificati",fmt_it(planned),delta=f"{plan_achievement:.1f}% del piano" if planned else None)
    k3.metric("Target del periodo",fmt_it(target_period) if target_period else "–")
    k4.metric("Target raggiunto",f"{target_achievement:.1f}%" if target_period else "–")
    k5,k6,k7,k8=st.columns(4)
    k5.metric("Lotti completati",completed_lots)
    k6.metric("Lotti in corso",len(open_lots))
    k7.metric("Ore lavorazione",f"{production_hours:.2f}")
    k8.metric("Ore-uomo",f"{person_hours:.2f}")
    k9,k10,k11=st.columns(3)
    k9.metric("Produttività di processo",f"{kg_hour:.1f} kg/ora")
    k10.metric("Produttività ore-uomo",f"{kg_person_hour:.1f} kg/ora-uomo")
    k11.metric(
        "Target produttività",f'{target_cfg["target_kg_ora_uomo"]:.1f} kg/ora-uomo' if target_cfg["target_kg_ora_uomo"] else "–",
        delta=f"{productivity_achievement:.1f}% raggiunto" if target_cfg["target_kg_ora_uomo"] else None,
    )

    left,right=st.columns(2)
    with left:
        st.subheader("Produzione giornaliera")
        if closures.empty: st.info("Nessuna mescola completata nel periodo selezionato.")
        else:
            daily=closures.groupby(closures["data_evento"].dt.date)["quantita_finale"].sum().reset_index()
            fig=go.Figure(go.Bar(x=daily["data_evento"],y=daily["quantita_finale"],marker_color="#6F4E8C"))
            fig.update_layout(height=330,margin=dict(l=20,r=20,t=20,b=20),xaxis_title="Data",yaxis_title="Kg prodotti",paper_bgcolor="white",plot_bgcolor="white")
            st.plotly_chart(fig,use_container_width=True)
    with right:
        st.subheader("Produzione per prodotto")
        if closures.empty: st.info("Nessun prodotto disponibile nel periodo selezionato.")
        else:
            by_product=closures.groupby("descrizione",dropna=False)["quantita_finale"].sum().sort_values(ascending=True).tail(10)
            fig=go.Figure(go.Bar(x=by_product.values,y=by_product.index,orientation="h",marker_color="#238B73"))
            fig.update_layout(height=330,margin=dict(l=20,r=20,t=20,b=20),xaxis_title="Kg prodotti",yaxis_title="",paper_bgcolor="white",plot_bgcolor="white")
            st.plotly_chart(fig,use_container_width=True)

    st.subheader("Dettaglio lotti completati")
    if closures.empty: st.info("Nessun lotto completato nel periodo.")
    else:
        detail=closures[["data_turno","turno","lotto","codice","descrizione","numero_operatori","quantita_finale","piano_id"]].copy()
        st.dataframe(detail.iloc[::-1],use_container_width=True,hide_index=True,column_config={
            "data_turno":"Data","turno":"Turno","lotto":"Lotto","codice":"Codice","descrizione":"Prodotto",
            "numero_operatori":"Operatori","quantita_finale":st.column_config.NumberColumn("Quantità kg",format="%.1f"),"piano_id":"Riferimento piano",
        })
    if open_lots:
        st.info("Lotti attualmente in corso: "+" · ".join(open_lots))

elif page=="Dashboard OEE":
    st.title("Dashboard OEE")
    st.caption("Combined OEE dashboard for Comber, EV200 and Spray Dryer. The 95% standard quality factor remains included in the OEE calculation.")
    all_turns=read_csv(TURNI_FILE,COL_TURNI); all_prod=prep_production()
    render_oee_unified(all_turns,all_prod)

elif page=="Production vs Target":
    st.title("Production vs Target")
    st.caption("Physical and equivalent output for Comber extraction and Spray Dryer production.")
    wide_report=st.toggle("Pagina intera",value=False,help="Nasconde il menu laterale e usa tutta la larghezza dello schermo. Disattiva il comando per tornare alla vista normale.")
    if wide_report:
        st.markdown("""
        <style>
        [data-testid="stSidebar"]{display:none!important}
        [data-testid="stAppViewContainer"] .block-container{
            max-width:none!important;width:100%!important;padding-left:1.2rem!important;padding-right:1.2rem!important
        }
        .table-wrap{padding:12px!important}.prod-table{min-width:1450px!important}
        </style>
        """,unsafe_allow_html=True)
    today=st.date_input("Report date",value=date.today(),format="DD/MM/YYYY")
    week_start=today-timedelta(days=today.weekday()); month_start=today.replace(day=1)
    st.markdown(f'<div class="report-head"><div class="report-title">Production vs. Target Report ({today:%d/%m/%Y})</div><div class="report-sub">Daily, Weekly, Monthly, Year-to-Date &nbsp; · &nbsp; Month {month_start:%d/%m/%Y}–{(pd.Timestamp(month_start)+pd.offsets.MonthEnd()).date():%d/%m/%Y} &nbsp; · &nbsp; Week {week_start:%d/%m/%Y}–{week_start+timedelta(days=6):%d/%m/%Y}</div></div>',unsafe_allow_html=True)
    df=prep_production(); yesterday=previous_workday(today); prev_end=month_start-timedelta(days=1); prev_start=prev_end.replace(day=1)
    try: ly=today.replace(year=today.year-1)
    except ValueError: ly=today.replace(year=today.year-1,day=28)
    periods={"Yesterday":(yesterday,yesterday),"Week":(week_start,today),"Month":(month_start,today),"Previous Month":(prev_start,prev_end),"YTD Production":(today.replace(month=1,day=1),today),"Last year YTD":(ly.replace(month=1,day=1),ly)}
    # Base KPI esplicita: estrazione in puro equivalente, essiccazione in
    # semilavorato fisico totale. La tabella distingue entrambe le letture.
    summary_band("Comber – Aqueous extraction","Pure equivalent output (15% minimum basis)","navy",df,"Comber","equivalente",periods)
    summary_band("Spray Dryer – Drying","Total semi-finished product output","green",df,"Spray Dryer","fisico",periods)
    st.markdown(dashboard_table(df,today),unsafe_allow_html=True)
    cfg=target_config()
    target_txt=" · ".join(
        f"{r.macchina}: {r.target_fisico_giorno:g} physical kg/day, {r.target_equivalente_giorno:g} equivalent kg/day, {r.giorni_produttivi_anno:g} working days/year"
        for r in cfg.itertuples()
    )
    st.caption("Active targets — "+target_txt)

elif page in ["Turno Comber", "Turno EV200", "Turno Spray Dryer", "Turno Mescole"]:
    machine={"Turno Comber":"Comber", "Turno EV200":"EV200", "Turno Spray Dryer":"Spray Dryer", "Turno Mescole":"Mescole"}[page]
    render_machine_workflow(machine)
    st.stop()
    machine_css={"Comber":"comber", "EV200":"ev200", "Spray Dryer":"spray"}[machine]
    machine_desc={
        "Comber":"Estrazione acquosa · droga, liquido estratto, residuo secco e resa",
        "EV200":"Concentrazione · liquido alimentato, residui secchi e concentrato",
        "Spray Dryer":"Essiccazione · codice semilavorato, polvere ottenuta e puro equivalente",
    }[machine]
    st.markdown(f'<div class="machine-head {machine_css}">{machine}<div class="machine-note">{machine_desc}</div></div>',unsafe_allow_html=True)
    st.caption("Maschera dedicata: i campi visualizzati appartengono esclusivamente alla macchina selezionata.")
    c1,c2=st.columns(2)
    with c1: d=st.date_input("Data di inizio turno",value=date.today(),format="DD/MM/YYYY")
    with c2: shift=st.selectbox("Turno",["1","2","3"])
    shift_id=f"{d:%Y%m%d}-{shift}-{machine.replace(' ','_')}"
    products=read_csv(PRODOTTI_FILE,COL_PRODOTTI); active=products[products["attivo"].str.upper()=="SI"]
    drug=active[active["tipo"]=="Droga"]; semi=active[active["tipo"]=="Semilavorato"]
    with st.form("production"):
        st.markdown(f"### Produzione {machine}")
        lot=st.text_input("Lotto *",placeholder="Campo obbligatorio")
        descr=st.text_input("Descrizione prodotto/estratto *",placeholder="Campo obbligatorio")
        code_drug=""; code_semi=""; kg_drug=kg_liquid=rs=kg_pure=kg_semi=0.0; pure_pct=40.0
        if machine=="Comber":
            opts=[f"{r.codice} — {r.descrizione}" for r in drug.itertuples()]
            sel=st.selectbox("Codice droga *",opts,index=None,placeholder="Seleziona un codice dall’anagrafica")
            code_drug=sel.split(" — ")[0] if sel else ""
            a,b,c=st.columns(3)
            with a: kg_drug=st.number_input("Droga lavorata (kg)",min_value=0.0)
            with b: kg_liquid=st.number_input("Liquido estratto (kg)",min_value=0.0)
            with c: rs=st.number_input("Residuo secco liquido (%)",min_value=0.0,max_value=100.0)
            kg_pure=kg_liquid*rs/100
            st.info(f"Puro ottenuto: {kg_pure:.1f} kg · Resa: {pct(kg_pure,kg_drug):.1f}% · Equivalente 15%: {equivalent_comber(kg_drug,kg_pure):.1f} kg")
        elif machine=="EV200":
            a,b,c=st.columns(3)
            with a: kg_liquid=st.number_input("Liquido alimentato (kg)",min_value=0.0)
            with b: rs_in=st.number_input("Residuo secco iniziale (%)",min_value=0.0,max_value=100.0)
            with c: kg_conc=st.number_input("Concentrato ottenuto (kg)",min_value=0.0)
            rs=st.number_input("Residuo secco finale (%)",min_value=0.0,max_value=100.0)
            kg_pure=kg_conc*rs/100
            st.info(f"Puro concentrato ottenuto: {kg_pure:.1f} kg · Puro teorico in ingresso: {kg_liquid*rs_in/100:.1f} kg")
        else:
            opts=[f"{r.codice} — {r.descrizione}" for r in semi.itertuples()]
            sel=st.selectbox("Codice semilavorato *",opts,index=None,placeholder="Seleziona un codice dall’anagrafica")
            code_semi=sel.split(" — ")[0] if sel else ""
            if sel and not descr:
                st.caption("La descrizione associata al codice è visibile nel menu; riportala nel campo descrizione per confermare il prodotto.")
            a,b=st.columns(2)
            with a: kg_semi=st.number_input("Semilavorato totale ottenuto (kg)",min_value=0.0)
            with b: pure_pct=st.number_input("Percentuale puro (%)",min_value=0.0,max_value=100.0,value=40.0)
            kg_pure=kg_semi*pure_pct/100
            st.info(f"Puro ottenuto: {kg_pure:.1f} kg · Puro equivalente standard 60/40: {equivalent_spray(kg_semi,kg_pure):.1f} kg")
        notes=st.text_area("Note")
        submit=st.form_submit_button("Salva produzione",type="primary")
    if submit:
        if not lot.strip(): st.error("Inserisci il lotto: il salvataggio è bloccato per evitare produzioni senza tracciabilità.")
        elif not descr.strip(): st.error("Inserisci la descrizione del prodotto/estratto.")
        elif machine=="Comber" and (not code_drug or kg_drug<=0): st.error("Seleziona la droga e inserisci i kg lavorati.")
        elif machine=="Comber" and (kg_liquid<=0 or rs<=0): st.error("Inserisci liquido estratto e residuo secco: servono per calcolare il puro.")
        elif machine=="EV200" and (kg_liquid<=0 or kg_conc<=0 or rs<=0): st.error("Inserisci alimentazione, concentrato ottenuto e residuo secco finale.")
        elif machine=="Spray Dryer" and (not code_semi or kg_semi<=0): st.error("Seleziona il semilavorato e inserisci la quantità.")
        else:
            eq=equivalent_comber(kg_drug,kg_pure) if machine=="Comber" else (equivalent_spray(kg_semi,kg_pure) if machine=="Spray Dryer" else kg_pure)
            row={"id":datetime.now().strftime("%Y%m%d%H%M%S%f"),"id_turno":shift_id,"data_turno":d,"turno":shift,"macchina":machine,"lotto":lot.strip(),"codice_droga":code_drug,"codice_semilavorato":code_semi,"descrizione":descr,"kg_droga":kg_drug,"kg_liquido":kg_liquid,"residuo_secco_pct":rs,"kg_puro":kg_pure,"kg_semilavorato":kg_semi,"pct_puro_semilavorato":pure_pct,"kg_puro_equivalente":eq,"note":notes}
            save_csv(pd.concat([read_csv(LOTTI_FILE,COL_LOTTI),pd.DataFrame([row])],ignore_index=True),LOTTI_FILE,COL_LOTTI); st.success("Produzione salvata.")
    st.divider(); st.markdown("### Consuntivo ore del turno")
    with st.form("hours"):
        a,b=st.columns(2)
        with a: prod_h=st.number_input("Ore di produzione",0.0,8.0,8.0,0.25)
        with b: stop_h=st.number_input("Ore di fermo",0.0,8.0,0.0,0.25)
        caus=read_csv(CAUSALI_FILE,COL_CAUSALI); opts=caus[caus["attiva"].str.upper()=="SI"]["causale"].tolist()
        cause=st.selectbox("Causale principale",[""]+opts); shift_note=st.text_input("Note turno / causale",value=cause)
        save_hours=st.form_submit_button("Salva consuntivo turno")
    if save_hours:
        turns=read_csv(TURNI_FILE,COL_TURNI); turns=turns[turns["id_turno"]!=shift_id]
        row={"id_turno":shift_id,"data_turno":d,"turno":shift,"macchina":machine,"ore_pianificate":8,"ore_produzione":prod_h,"ore_fermo":stop_h,"note":shift_note}
        save_csv(pd.concat([turns,pd.DataFrame([row])],ignore_index=True),TURNI_FILE,COL_TURNI); st.success("Consuntivo salvato.")
    st.divider(); st.markdown(f"### Ultimi dati caricati — {machine}")
    st.caption("Puoi correggere direttamente le celle. ID e macchina sono bloccati per evitare di spostare accidentalmente un dato su un’altra linea.")
    all_rows=read_csv(LOTTI_FILE,COL_LOTTI)
    recent=all_rows[all_rows["macchina"]==machine].tail(20).copy()
    if recent.empty:
        st.info("Nessuna produzione caricata per questa macchina.")
    else:
        edited_recent=st.data_editor(
            recent,use_container_width=True,hide_index=True,num_rows="fixed",
            disabled=["id","macchina"],key=f"recent_{machine}",
        )
        if st.button("Salva correzioni agli ultimi dati",type="primary",key=f"save_recent_{machine}"):
            base=all_rows[~all_rows["id"].isin(recent["id"])]
            save_csv(pd.concat([base,edited_recent],ignore_index=True),LOTTI_FILE,COL_LOTTI)
            st.success("Correzioni salvate."); st.rerun()
        labels={str(r.id):f"{r.data_turno} · {r.lotto} · {r.descrizione}" for r in recent.itertuples()}
        delete_id=st.selectbox("Dato da eliminare",[""]+list(labels),format_func=lambda x:"-- Seleziona --" if not x else labels[x],key=f"delete_{machine}")
        confirm_delete=st.checkbox("Confermo l’eliminazione del dato selezionato",key=f"confirm_delete_{machine}")
        if st.button("Elimina dato",disabled=not(delete_id and confirm_delete),key=f"delete_btn_{machine}"):
            save_csv(all_rows[all_rows["id"]!=delete_id],LOTTI_FILE,COL_LOTTI)
            st.success("Dato eliminato."); st.rerun()

elif page=="Storico":
    st.title("Storico generale")
    df=prep_production()
    f1,f2=st.columns(2)
    with f1: machine_filter=st.selectbox("Macchina",["Tutte"]+MACCHINE)
    with f2: text_filter=st.text_input("Cerca lotto, codice o descrizione")
    if not df.empty:
        if machine_filter!="Tutte": df=df[df["macchina"]==machine_filter]
        if text_filter.strip():
            needle=text_filter.strip().lower()
            mask=df[["lotto","codice_droga","codice_semilavorato","descrizione"]].astype(str).apply(lambda c:c.str.lower().str.contains(needle,regex=False)).any(axis=1)
            df=df[mask]
        df=df.sort_values(["data_turno","id"],ascending=False)
    tab_prod,tab_events=st.tabs(["Produzioni chiuse","Eventi di turno"])
    with tab_prod: st.dataframe(df,use_container_width=True,hide_index=True)
    with tab_events:
        events=read_csv(EVENTI_FILE,COL_EVENTI)
        filtered_events=events.copy()
        if machine_filter!="Tutte": filtered_events=filtered_events[filtered_events["macchina"]==machine_filter]
        if text_filter.strip() and not filtered_events.empty:
            needle=text_filter.strip().lower()
            emask=filtered_events[["lotto","codice","descrizione","tipo_evento"]].astype(str).apply(lambda c:c.str.lower().str.contains(needle,regex=False)).any(axis=1)
            filtered_events=filtered_events[emask]
        if filtered_events.empty:
            st.info("Nessun evento corrispondente ai filtri selezionati.")
        else:
            original=filtered_events.iloc[::-1].copy()
            st.caption("Correggi direttamente le celle. ID evento, ID turno e macchina restano protetti.")
            edited_history=st.data_editor(
                original,use_container_width=True,hide_index=True,num_rows="fixed",
                disabled=["id_evento","id_turno","macchina"],key="history_event_editor",
            )
            confirm_history=st.checkbox("Confermo le modifiche agli eventi selezionati",key="confirm_history_events")
            if st.button("Salva modifiche eventi",type="primary",disabled=not confirm_history,key="save_history_events"):
                ok,message=save_history_event_edits(original,edited_history)
                if ok:
                    st.success(message); st.rerun()
                else:
                    st.error(message)
            st.divider(); st.markdown("#### Elimina eventi")
            event_labels={
                str(r.id_evento):f"{r.data_turno} · Turno {r.turno} · {r.macchina} · {r.ora_inizio}–{r.ora_fine} · {r.tipo_evento} · {r.lotto}"
                for r in original.itertuples()
            }
            delete_ids=st.multiselect(
                "Eventi da eliminare",list(event_labels),format_func=lambda value:event_labels[value],
                placeholder="Seleziona uno o più eventi",key="history_delete_events",
            )
            confirm_delete=st.checkbox(
                "Confermo l’eliminazione definitiva degli eventi selezionati",
                key="confirm_history_delete",
            )
            if st.button(
                "Elimina eventi selezionati",disabled=not(delete_ids and confirm_delete),
                key="delete_history_events_btn",
            ):
                ok,message=delete_history_events(delete_ids)
                if ok:
                    st.success(message); st.rerun()
                else:
                    st.error(message)

elif page=="Target":
    st.title("Configurazione target")
    st.caption("I valori salvati aggiornano immediatamente dashboard, percentuali di raggiungimento e performance OEE.")
    targets=target_config()
    edited_targets=st.data_editor(
        targets,use_container_width=True,hide_index=True,num_rows="fixed",disabled=["macchina"],
        column_config={
            "target_fisico_giorno":st.column_config.NumberColumn("Target fisico kg/giorno",min_value=0.0,format="%.2f"),
            "target_equivalente_giorno":st.column_config.NumberColumn("Target equivalente kg/giorno",min_value=0.0,format="%.2f"),
            "giorni_produttivi_anno":st.column_config.NumberColumn("Giorni produttivi/anno",min_value=1,max_value=366,step=1),
        },key="target_editor",
    )
    if st.button("Salva target",type="primary"):
        numeric=edited_targets[["target_fisico_giorno","target_equivalente_giorno","giorni_produttivi_anno"]].apply(pd.to_numeric,errors="coerce")
        if numeric.isna().any().any() or (numeric<=0).any().any(): st.error("Tutti i target e i giorni produttivi devono essere maggiori di zero.")
        else: save_csv(edited_targets,TARGET_FILE,COL_TARGET); st.success("Target aggiornati."); st.rerun()
    st.info("Valori iniziali: Comber 150 kg/giorno; EV200 168,75 kg/giorno; Spray Dryer 321,6 kg fisici e 128,64 kg equivalenti; 220 giorni/anno.")

elif page=="Anagrafiche e causali":
    st.title("Anagrafiche e causali")
    tab1,tab2=st.tabs(["Codici prodotto","Causali"])
    with tab1:
        with st.form("new_product"):
            a,b=st.columns(2)
            with a: typ=st.selectbox("Tipo",["Droga","Semilavorato","Mescola"]); code=st.text_input("Codice")
            with b: desc=st.text_input("Descrizione"); std=st.number_input("% puro standard",0.0,100.0,15.0)
            add=st.form_submit_button("Aggiungi / aggiorna codice",type="primary")
        if add and code.strip():
            p=read_csv(PRODOTTI_FILE,COL_PRODOTTI); p=p[~((p["tipo"]==typ)&(p["codice"]==code.strip()))]
            p=pd.concat([p,pd.DataFrame([{"tipo":typ,"codice":code.strip(),"descrizione":desc,"pct_puro_standard":std,"attivo":"SI"}])],ignore_index=True); save_csv(p,PRODOTTI_FILE,COL_PRODOTTI); st.success("Codice salvato.")
        edited=st.data_editor(read_csv(PRODOTTI_FILE,COL_PRODOTTI),use_container_width=True,num_rows="dynamic",key="products")
        if st.button("Salva modifiche codici"): save_csv(edited,PRODOTTI_FILE,COL_PRODOTTI); st.success("Anagrafica aggiornata.")
    with tab2:
        with st.form("new_cause"):
            a,b=st.columns(2)
            with a: cause=st.text_input("Nuova causale"); cat=st.selectbox("Categoria",["Operativa","Organizzativa","Tecnica","Pianificata"])
            with b: excluded=st.checkbox("Escludi dal tempo pianificato"); technical=st.checkbox("Perdita tecnica")
            addc=st.form_submit_button("Aggiungi causale",type="primary")
        if addc and cause.strip():
            c=read_csv(CAUSALI_FILE,COL_CAUSALI); c=c[c["causale"]!=cause.strip()]
            c=pd.concat([c,pd.DataFrame([{"causale":cause.strip(),"categoria":cat,"esclusa_pianificato":"SI" if excluded else "NO","perdita_tecnica":"SI" if technical else "NO","attiva":"SI"}])],ignore_index=True); save_csv(c,CAUSALI_FILE,COL_CAUSALI); st.success("Causale salvata.")
        editedc=st.data_editor(read_csv(CAUSALI_FILE,COL_CAUSALI),use_container_width=True,num_rows="dynamic",key="causes")
        if st.button("Salva modifiche causali"): save_csv(editedc,CAUSALI_FILE,COL_CAUSALI); st.success("Causali aggiornate.")

elif page=="Excel":
    st.title("Excel per macchina")
    machine=st.selectbox("Seleziona la macchina",MACCHINE)
    safe_name=machine.lower().replace(" ","_")
    st.caption(f"Il file contiene esclusivamente turni e produzioni della macchina {machine}.")
    st.download_button(f"Scarica Excel {machine}",xlsx_export(machine),f"oee_{safe_name}.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",type="primary")
    up=st.file_uploader(f"Ricarica Excel {machine}",type=["xlsx"],key=f"upload_{safe_name}")
    replace=st.checkbox(f"Confermo la sostituzione dei soli dati {machine}")
    if up and st.button(f"Importa dati {machine}",disabled=not replace):
        try:
            xl=pd.ExcelFile(up)
            if "Turni" not in xl.sheet_names or "Produzioni" not in xl.sheet_names:
                raise ValueError("Il file deve contenere i fogli Turni e Produzioni.")
            new_t=pd.read_excel(xl,"Turni",dtype=str).fillna(""); new_p=pd.read_excel(xl,"Produzioni",dtype=str).fillna("")
            for frame in [new_t,new_p]: frame["macchina"]=machine
            old_t=read_csv(TURNI_FILE,COL_TURNI); old_p=read_csv(LOTTI_FILE,COL_LOTTI)
            old_t=old_t[old_t["macchina"]!=machine]; old_p=old_p[old_p["macchina"]!=machine]
            save_csv(pd.concat([old_t,new_t],ignore_index=True),TURNI_FILE,COL_TURNI)
            save_csv(pd.concat([old_p,new_p],ignore_index=True),LOTTI_FILE,COL_LOTTI)
            if "Eventi" in xl.sheet_names:
                new_e=pd.read_excel(xl,"Eventi",dtype=str).fillna(""); new_e["macchina"]=machine
                old_e=read_csv(EVENTI_FILE,COL_EVENTI); old_e=old_e[old_e["macchina"]!=machine]
                save_csv(pd.concat([old_e,new_e],ignore_index=True),EVENTI_FILE,COL_EVENTI)
            st.success(f"Dati {machine} sostituiti. Le altre macchine non sono state modificate.")
        except Exception as exc: st.error(f"Impossibile importare: {exc}")
    st.markdown(f'<div class="hint">Questo backup è indipendente: caricandolo vengono sostituiti soltanto i dati {machine}. I reparti non si sovrascrivono tra loro.</div>',unsafe_allow_html=True)
