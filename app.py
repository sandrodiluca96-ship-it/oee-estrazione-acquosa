import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, time, timedelta
from io import BytesIO


st.set_page_config(page_title="OEE Estrazione Acquosa", layout="wide")

st.markdown("""
<style>
.stApp {background-color:#F5F7F6;color:#263238}
[data-testid="stSidebar"] {background-color:#EEF3F0;border-right:1px solid #D9E0DC}
[data-testid="stMetric"] {
    background-color:#FFFFFF;border:1px solid #D9E0DC;border-radius:10px;
    padding:14px 16px;box-shadow:0 1px 3px rgba(38,50,56,.06)
}
[data-testid="stDataFrame"] {background-color:#FFFFFF;border-radius:8px}
[data-baseweb="input"], [data-baseweb="select"] {background-color:#FFFFFF}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
    background-color: #2E7D32 !important; color: white !important;
    border-color: #2E7D32 !important; font-weight: 700 !important;
}
.stButton > button[kind="secondary"] {background-color:#FFFFFF;border-color:#9EAAA4;color:#263238}
.ok {background:#E8F5E9;border-left:6px solid #2E7D32;padding:12px;border-radius:6px;color:#1B5E20;font-weight:600}
.warn {background:#FFF3CD;border-left:6px solid #FF9800;padding:12px;border-radius:6px;color:#4E342E;font-weight:600}
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# CONFIGURAZIONE
# -----------------------------------------------------------------------------

VERSIONE = "1.3.0"
QUALITA_STANDARD = 0.95
TURNO_H = 8

ASSET = {
    "Comber": {"tipo": "Estrazione", "capacita": 25.0, "unita": "kg droga/h"},
    "EV200": {"tipo": "Concentrazione", "capacita": 200.0, "unita": "kg acqua evaporata/h"},
}

TURNI = {
    "1": {"inizio": time(6, 0), "fine": time(14, 0)},
    "2": {"inizio": time(14, 0), "fine": time(22, 0)},
    "3": {"inizio": time(22, 0), "fine": time(6, 0)},
}

CAUSALI = [
    "Produzione", "Attesa prodotto", "Attesa analisi", "Carico/Scarico",
    "Lavaggio", "Guasto", "Manutenzione programmata",
    "Manutenzione straordinaria", "Pulizia", "Altro",
]

TIPI_LAVORAZIONE = ["Apertura lavorazione", "Prosecuzione lavorazione", "Chiusura lavorazione"]
FERMI_ESCLUSI = ["Lavaggio", "Manutenzione programmata", "Pulizia"]
FERMI_TECNICI = ["Guasto", "Manutenzione straordinaria"]

DATA_DIR = Path("data")
EVENTI_FILE = DATA_DIR / "eventi_turno.csv"
CONFIG_FILE = DATA_DIR / "configurazione.csv"
TARGET_FILE = DATA_DIR / "target_mensili.csv"

COL_TARGET = ["mese", "prodotto", "target_kg_equivalenti_15"]

COL_EVENTI = [
    "id_evento", "id_turno_asset", "data_turno", "turno", "asset", "asset_pianificato",
    "tipo_evento", "tipo_lavorazione", "lotto", "prodotto", "ora_inizio", "ora_fine",
    "data_ora_inizio", "data_ora_fine", "durata_h", "kg_droga", "kg_acqua",
    "kg_liquido_estratto", "rs_liquido_pct", "kg_puro_estratto", "resa_estrattiva_pct",
    "kg_liquido_alimentato", "rs_iniziale_pct", "kg_concentrato", "rs_finale_pct",
    "kg_puro_ingresso", "kg_puro_concentrato", "recupero_concentrazione_pct",
    "kg_acqua_evaporata", "note",
]


# -----------------------------------------------------------------------------
# DATI E UTILITA'
# -----------------------------------------------------------------------------

def inizializza():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not EVENTI_FILE.exists():
        pd.DataFrame(columns=COL_EVENTI).to_csv(EVENTI_FILE, index=False)
    if not CONFIG_FILE.exists():
        pd.DataFrame([
            {"asset": k, "capacita_nominale": v["capacita"], "unita": v["unita"]}
            for k, v in ASSET.items()
        ]).to_csv(CONFIG_FILE, index=False)
    if not TARGET_FILE.exists():
        pd.DataFrame(columns=COL_TARGET).to_csv(TARGET_FILE, index=False)


def leggi_eventi():
    inizializza()
    df = pd.read_csv(EVENTI_FILE, dtype=str).fillna("")
    for col in COL_EVENTI:
        if col not in df.columns:
            df[col] = ""
    return df[COL_EVENTI]


def salva_eventi(df):
    for col in COL_EVENTI:
        if col not in df.columns:
            df[col] = ""
    df[COL_EVENTI].to_csv(EVENTI_FILE, index=False)


def leggi_config():
    inizializza()
    df = pd.read_csv(CONFIG_FILE, dtype=str).fillna("")
    df["capacita_nominale"] = pd.to_numeric(df["capacita_nominale"], errors="coerce").fillna(0)
    return df


def leggi_target():
    inizializza()
    df = pd.read_csv(TARGET_FILE, dtype=str).fillna("")
    for col in COL_TARGET:
        if col not in df.columns:
            df[col] = ""
    df["target_kg_equivalenti_15"] = pd.to_numeric(
        df["target_kg_equivalenti_15"], errors="coerce"
    ).fillna(0)
    return df[COL_TARGET]


def salva_target(df):
    for col in COL_TARGET:
        if col not in df.columns:
            df[col] = ""
    df[COL_TARGET].to_csv(TARGET_FILE, index=False)


def safe_float(v, default=0.0):
    x = pd.to_numeric(str(v).replace(",", "."), errors="coerce")
    return default if pd.isna(x) else float(x)


def safe_div(n, d):
    return n / d if d not in (0, None) and not pd.isna(d) else 0


def parse_time(v):
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(str(v)[:8], fmt).time()
        except Exception:
            pass
    return None


def ore(oi, of):
    if oi is None or of is None:
        return 0
    a = datetime.combine(datetime.today(), oi)
    b = datetime.combine(datetime.today(), of)
    if b <= a:
        b += timedelta(days=1)
    return (b - a).total_seconds() / 3600


def minuto_turno(t, turno):
    if t is None or turno not in TURNI:
        return None
    start = TURNI[turno]["inizio"].hour * 60 + TURNI[turno]["inizio"].minute
    value = t.hour * 60 + t.minute
    return value + 1440 if value < start else value


def dentro_turno(oi, of, turno):
    if turno not in TURNI or oi is None or of is None:
        return False
    start = minuto_turno(TURNI[turno]["inizio"], turno)
    end = TURNI[turno]["fine"].hour * 60 + TURNI[turno]["fine"].minute
    if end <= start:
        end += 1440
    a, b = minuto_turno(oi, turno), minuto_turno(of, turno)
    if b <= a:
        b += 1440
    return a >= start and b <= end


def timestamp_evento(data_turno, turno, oi, of):
    di = data_turno + timedelta(days=1) if turno == "3" and oi < TURNI[turno]["inizio"] else data_turno
    df = data_turno + timedelta(days=1) if turno == "3" and of <= TURNI[turno]["fine"] else data_turno
    a, b = datetime.combine(di, oi), datetime.combine(df, of)
    if b <= a:
        b += timedelta(days=1)
    return a, b


def orari_turno(turno):
    if turno not in TURNI:
        return []
    start = TURNI[turno]["inizio"].hour * 60 + TURNI[turno]["inizio"].minute
    end = TURNI[turno]["fine"].hour * 60 + TURNI[turno]["fine"].minute
    if end <= start:
        end += 1440
    out = []
    for m in range(start, end + 1, 15):
        x = m % 1440
        out.append(f"{x // 60:02d}:{x % 60:02d}")
    return out


def valida_timeline(rows, turno, completa=False):
    if not rows:
        return False, "Nessun evento inserito."
    intervals = []
    for i, row in enumerate(rows, 1):
        oi, of = parse_time(row.get("ora_inizio")), parse_time(row.get("ora_fine"))
        if not dentro_turno(oi, of, turno):
            return False, f"Evento {i} esterno al turno."
        a, b = minuto_turno(oi, turno), minuto_turno(of, turno)
        if b <= a:
            b += 1440
        intervals.append((a, b, i))
    intervals.sort()
    start = minuto_turno(TURNI[turno]["inizio"], turno)
    end = TURNI[turno]["fine"].hour * 60 + TURNI[turno]["fine"].minute
    if end <= start:
        end += 1440
    cursor = start
    for a, b, i in intervals:
        if a < cursor:
            return False, f"L'evento {i} si sovrappone al precedente."
        if completa and a > cursor:
            return False, "La timeline contiene un intervallo non coperto."
        cursor = b
    if completa and cursor != end:
        return False, "La timeline non copre esattamente le 8 ore."
    return True, "Timeline valida."


def nuovo_id():
    return datetime.now().strftime("%Y%m%d%H%M%S%f")


def prepara_eventi(df):
    if df.empty:
        return df
    numeriche = [c for c in COL_EVENTI if c.startswith("kg_") or c.endswith("_pct") or c == "durata_h"]
    for c in numeriche:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["data_turno"] = pd.to_datetime(df["data_turno"], errors="coerce")
    return df


def lotti_aperti(asset):
    df = leggi_eventi()
    if df.empty:
        return []
    df = df[(df["asset"] == asset) & (df["tipo_evento"] == "Produzione")]
    aperture = df[df["tipo_lavorazione"] == "Apertura lavorazione"]["lotto"].tolist()
    chiusure = set(df[df["tipo_lavorazione"] == "Chiusura lavorazione"]["lotto"].tolist())
    buffer = st.session_state.get("buffer", [])
    aperture += [r["lotto"] for r in buffer if r.get("asset") == asset and r.get("tipo_lavorazione") == "Apertura lavorazione"]
    return list(dict.fromkeys([x for x in aperture if x and x not in chiusure]))


def dati_lotto(asset, lotto):
    rows = list(st.session_state.get("buffer", []))
    df = leggi_eventi()
    if not df.empty:
        rows += df.to_dict("records")
    matches = [r for r in rows if r.get("asset") == asset and str(r.get("lotto")) == str(lotto) and r.get("tipo_lavorazione") == "Apertura lavorazione"]
    return matches[-1] if matches else None


def calcola_kpi(df, asset):
    df = prepara_eventi(df.copy())
    df = df[(df["asset"] == asset) & (df["asset_pianificato"].str.upper() == "SI")]
    if df.empty:
        return {k: 0 for k in ["availability", "technical", "performance", "quality", "oee", "ore_prod", "ore_fermo", "output1", "output2", "indice"]}
    turni = df[["data_turno", "turno", "asset"]].drop_duplicates().shape[0]
    lordo = turni * TURNO_H
    fermi = df[df["tipo_evento"] != "Produzione"]
    esclusi = fermi[fermi["tipo_evento"].isin(FERMI_ESCLUSI)]["durata_h"].sum()
    perdite = fermi[~fermi["tipo_evento"].isin(FERMI_ESCLUSI)]["durata_h"].sum()
    pianificato = max(lordo - esclusi, 0)
    availability = safe_div(pianificato - perdite, pianificato)
    tecnici = fermi[fermi["tipo_evento"].isin(FERMI_TECNICI)]["durata_h"].sum()
    technical = safe_div(lordo - tecnici, lordo)
    prod = df[df["tipo_evento"] == "Produzione"]
    ore_prod = prod["durata_h"].sum()
    chiusure = prod[prod["tipo_lavorazione"] == "Chiusura lavorazione"]
    cap_df = leggi_config()
    cap = float(cap_df.loc[cap_df["asset"] == asset, "capacita_nominale"].iloc[0])
    if asset == "Comber":
        output_perf = chiusure["kg_droga"].sum()
        output1 = chiusure["kg_puro_estratto"].sum()
        output2 = chiusure["kg_liquido_estratto"].sum()
        indice = safe_div(chiusure["kg_puro_estratto"].sum(), chiusure["kg_droga"].sum()) * 100
    else:
        output_perf = chiusure["kg_acqua_evaporata"].sum()
        output1 = chiusure["kg_puro_concentrato"].sum()
        output2 = chiusure["kg_concentrato"].sum()
        indice = safe_div(chiusure["kg_puro_concentrato"].sum(), chiusure["kg_puro_ingresso"].sum()) * 100
    performance = safe_div(output_perf, cap * ore_prod)
    quality = QUALITA_STANDARD if not chiusure.empty else 0
    return {
        "availability": max(availability, 0), "technical": max(technical, 0),
        "performance": max(performance, 0), "quality": quality,
        "oee": max(availability, 0) * max(performance, 0) * quality,
        "ore_prod": ore_prod, "ore_fermo": fermi["durata_h"].sum(),
        "output1": output1, "output2": output2, "indice": indice,
    }


def gauge(value, title):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value * 100, number={"suffix": "%"}, title={"text": title},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#2E7D32"},
               "steps": [{"range": [0, 50], "color": "#ff4b4b"}, {"range": [50, 75], "color": "#ffd966"}, {"range": [75, 100], "color": "#9be564"}]}
    ))
    fig.update_layout(height=300, margin=dict(l=30, r=30, t=60, b=20))
    return fig


def chiusure_comber(df):
    """Prepara i batch Comber chiusi e l'equivalente standard al 15% di mass yield."""
    df = prepara_eventi(df.copy())
    if df.empty:
        return df
    out = df[
        (df["asset"] == "Comber")
        & (df["tipo_evento"] == "Produzione")
        & (df["tipo_lavorazione"] == "Chiusura lavorazione")
    ].copy()
    if out.empty:
        return out
    out["kg_equivalenti_15"] = (
        out["kg_puro_estratto"] / 0.15
    ).clip(upper=out["kg_droga"])
    return out


def indicatori_periodo(df, dal, al):
    if df.empty:
        return {"kg_droga": 0.0, "kg_puro": 0.0, "resa_media": 0.0, "kg_equivalenti_15": 0.0, "batch": 0}
    x = df[(df["data_turno"].dt.date >= dal) & (df["data_turno"].dt.date <= al)]
    return {
        "kg_droga": float(x["kg_droga"].sum()),
        "kg_puro": float(x["kg_puro_estratto"].sum()),
        "resa_media": float(x["resa_estrattiva_pct"].mean()) if not x.empty else 0.0,
        "kg_equivalenti_15": float(x["kg_equivalenti_15"].sum()),
        "batch": int(len(x)),
    }


def giorni_lavorativi(inizio, fine):
    if fine < inizio:
        return 0
    return sum(1 for d in pd.date_range(inizio, fine) if d.weekday() < 5)


def target_maturato(target_df, prodotto, inizio, fine):
    """Prorata i target mensili sui giorni lavorativi compresi nel periodo."""
    if target_df.empty or fine < inizio:
        return 0.0
    t = target_df.copy()
    if prodotto != "Tutti":
        t = t[t["prodotto"].astype(str) == prodotto]
    totale = 0.0
    for mese in pd.period_range(inizio, fine, freq="M"):
        mese_txt = str(mese)
        target_mese = t[t["mese"].astype(str) == mese_txt]["target_kg_equivalenti_15"].sum()
        primo = max(inizio, mese.start_time.date())
        ultimo = min(fine, mese.end_time.date())
        giorni_mese = giorni_lavorativi(mese.start_time.date(), mese.end_time.date())
        giorni_periodo = giorni_lavorativi(primo, ultimo)
        totale += target_mese * safe_div(giorni_periodo, giorni_mese)
    return float(totale)


def export_excel():
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        leggi_eventi().to_excel(writer, sheet_name="Eventi turno", index=False)
        leggi_config().to_excel(writer, sheet_name="Configurazione", index=False)
        leggi_target().to_excel(writer, sheet_name="Target mensili", index=False)
    out.seek(0)
    return out


# -----------------------------------------------------------------------------
# SESSIONE E NAVIGAZIONE
# -----------------------------------------------------------------------------

inizializza()
for key, value in {"buffer": [], "locked_header": None, "flash": ""}.items():
    if key not in st.session_state:
        st.session_state[key] = value

st.title("🌿 OEE Estrazione Acquosa")
st.caption(f"Versione {VERSIONE} | Estrattore Comber e concentratore EV200 | Qualità standard 95%")

pagina = st.sidebar.radio(
    "Sezione",
    [
        "Turno Comber",
        "Turno EV200",
        "Dashboard Comber",
        "Dashboard EV200",
        "Performance complessiva",
        "Production vs Target",
        "Storico",
        "Configurazione",
        "Gestione dati",
    ],
)

if st.session_state["flash"]:
    st.success(st.session_state["flash"])
    st.session_state["flash"] = ""


# -----------------------------------------------------------------------------
# TURNO
# -----------------------------------------------------------------------------

if pagina in ["Turno Comber", "Turno EV200"]:
    asset = "Comber" if pagina == "Turno Comber" else "EV200"
    st.subheader(f"Compilazione turno {asset}")
    locked = bool(st.session_state["buffer"])
    locked_info = st.session_state.get("locked_header")
    if locked and locked_info and asset != locked_info[2]:
        st.error(
            f"Esiste un turno {locked_info[2]} non ancora salvato. "
            f"Torna a 'Turno {locked_info[2]}' e salvalo oppure svuotalo prima di passare all'altra macchina."
        )
        st.stop()
    data_default = datetime.strptime(locked_info[0], "%Y-%m-%d").date() if locked and locked_info else None
    turno_default = locked_info[1] if locked and locked_info else "-- Seleziona --"
    c1, c2 = st.columns(2)
    with c1:
        data_turno = st.date_input("Data turno", value=data_default, format="DD/MM/YYYY", disabled=locked)
    with c2:
        turno_options = ["-- Seleziona --", "1", "2", "3"]
        turno = st.selectbox("Turno", turno_options, index=turno_options.index(turno_default), disabled=locked)
    if turno != "-- Seleziona --":
        st.caption(f"{asset} | Turno {turno}: {TURNI[turno]['inizio'].strftime('%H:%M')} - {TURNI[turno]['fine'].strftime('%H:%M')}")

    if True:
        st.divider()
        st.markdown("### Aggiungi evento")
        tipo_evento = st.selectbox("Tipo evento", CAUSALI, index=None, placeholder="Seleziona evento")
        opts = orari_turno(turno) if turno != "-- Seleziona --" else []
        ultimo = st.session_state["buffer"][-1]["ora_fine"][:5] if st.session_state["buffer"] else (TURNI[turno]["inizio"].strftime("%H:%M") if turno in TURNI else "")
        a1, a2 = st.columns(2)
        with a1:
            oi_txt = st.selectbox("Ora inizio", ["--"] + opts, index=(["--"] + opts).index(ultimo) if ultimo in opts else 0)
        with a2:
            of_txt = st.selectbox("Ora fine", ["--"] + opts)
        oi, of = parse_time(oi_txt), parse_time(of_txt)
        durata = ore(oi, of)
        if durata:
            st.metric("Durata evento", f"{durata:.2f} h")

        row = {c: "" for c in COL_EVENTI}
        row.update({"asset": asset, "asset_pianificato": "SI", "tipo_evento": tipo_evento or "",
                    "ora_inizio": str(oi) if oi else "", "ora_fine": str(of) if of else "", "durata_h": durata})

        if tipo_evento == "Produzione":
            aperti = lotti_aperti(asset)
            default_tipo = "Prosecuzione lavorazione" if aperti else "Apertura lavorazione"
            tipo_lav = st.selectbox("Tipo lavorazione", TIPI_LAVORAZIONE, index=TIPI_LAVORAZIONE.index(default_tipo))
            row["tipo_lavorazione"] = tipo_lav
            if tipo_lav == "Apertura lavorazione":
                lotto = st.text_input("Lotto lavorazione")
                prodotto = st.text_input("Prodotto")
                row.update({"lotto": lotto.strip(), "prodotto": prodotto.strip()})
                if asset == "Comber":
                    x1, x2 = st.columns(2)
                    with x1: row["kg_droga"] = st.number_input("Kg droga caricata", min_value=0.0, step=10.0)
                    with x2: row["kg_acqua"] = st.number_input("Kg acqua caricata", min_value=0.0, step=10.0)
                else:
                    x1, x2 = st.columns(2)
                    with x1: row["kg_liquido_alimentato"] = st.number_input("Kg liquido alimentato", min_value=0.0, step=10.0)
                    with x2: row["rs_iniziale_pct"] = st.number_input("Residuo secco iniziale %", min_value=0.0, max_value=100.0, step=0.1)
                    row["kg_puro_ingresso"] = safe_float(row["kg_liquido_alimentato"]) * safe_float(row["rs_iniziale_pct"]) / 100
            else:
                lotto = st.selectbox("Lotto aperto", ["-- Seleziona --"] + aperti)
                base = dati_lotto(asset, lotto)
                if base:
                    for c in ["lotto", "prodotto", "kg_droga", "kg_acqua", "kg_liquido_alimentato", "rs_iniziale_pct", "kg_puro_ingresso"]:
                        row[c] = base.get(c, "")
                if tipo_lav == "Chiusura lavorazione":
                    if asset == "Comber":
                        x1, x2 = st.columns(2)
                        with x1: row["kg_liquido_estratto"] = st.number_input("Kg liquido estratto", min_value=0.0, step=10.0)
                        with x2: row["rs_liquido_pct"] = st.number_input("Residuo secco liquido %", min_value=0.0, max_value=100.0, step=0.1)
                        puro = safe_float(row["kg_liquido_estratto"]) * safe_float(row["rs_liquido_pct"]) / 100
                        row["kg_puro_estratto"] = puro
                        row["resa_estrattiva_pct"] = safe_div(puro, safe_float(row["kg_droga"])) * 100
                        st.info(f"Puro estratto: {puro:.1f} kg | Resa estrattiva: {safe_float(row['resa_estrattiva_pct']):.1f}%")
                    else:
                        x1, x2 = st.columns(2)
                        with x1: row["kg_concentrato"] = st.number_input("Kg concentrato ottenuto", min_value=0.0, step=10.0)
                        with x2: row["rs_finale_pct"] = st.number_input("Residuo secco finale %", min_value=0.0, max_value=100.0, step=0.1)
                        puro = safe_float(row["kg_concentrato"]) * safe_float(row["rs_finale_pct"]) / 100
                        row["kg_puro_concentrato"] = puro
                        row["recupero_concentrazione_pct"] = safe_div(puro, safe_float(row["kg_puro_ingresso"])) * 100
                        row["kg_acqua_evaporata"] = max(safe_float(row["kg_liquido_alimentato"]) - safe_float(row["kg_concentrato"]), 0)
                        st.info(f"Puro nel concentrato: {puro:.1f} kg | Recupero: {safe_float(row['recupero_concentrazione_pct']):.1f}% | Acqua evaporata: {safe_float(row['kg_acqua_evaporata']):.1f} kg")
        elif tipo_evento:
            row["note"] = st.text_area("Note")

        copertura = sum(safe_float(x.get("durata_h")) for x in st.session_state["buffer"])
        disabled_add = copertura >= TURNO_H - 0.01
        if st.button("Aggiungi evento", type="primary", disabled=disabled_add):
            if not data_turno or turno == "-- Seleziona --" or not tipo_evento or durata <= 0:
                st.error("Compila data, turno, evento e orari.")
            elif not dentro_turno(oi, of, turno):
                st.error("L'evento non rientra nel turno.")
            elif tipo_evento == "Produzione" and not row.get("lotto"):
                st.error("Seleziona o inserisci il lotto.")
            else:
                prova = st.session_state["buffer"] + [row]
                if sum(safe_float(x["durata_h"]) for x in prova) > TURNO_H + 0.01:
                    st.error("L'evento porterebbe la copertura oltre 8 ore.")
                else:
                    ok, msg = valida_timeline(prova, turno)
                    if not ok: st.error(msg)
                    else:
                        st.session_state["buffer"] = prova
                        st.session_state["locked_header"] = (str(data_turno), turno, asset)
                        st.rerun()

        st.divider()
        st.markdown("### Eventi del turno asset")
        if st.session_state["buffer"]:
            bdf = pd.DataFrame(st.session_state["buffer"])
            st.dataframe(bdf[["tipo_evento", "tipo_lavorazione", "lotto", "ora_inizio", "ora_fine", "durata_h", "note"]], use_container_width=True)
            copertura = pd.to_numeric(bdf["durata_h"], errors="coerce").sum()
            p1, p2, p3 = st.columns(3)
            p1.metric("Ore produzione", f"{pd.to_numeric(bdf.loc[bdf['tipo_evento']=='Produzione','durata_h'], errors='coerce').sum():.2f}")
            p2.metric("Ore fermo", f"{pd.to_numeric(bdf.loc[bdf['tipo_evento']!='Produzione','durata_h'], errors='coerce').sum():.2f}")
            p3.metric("Copertura", f"{copertura / TURNO_H:.1%}")
            st.markdown("<div class='ok'>Copertura completa.</div>" if abs(copertura-8)<0.01 else f"<div class='warn'>Mancano {8-copertura:.2f} ore.</div>", unsafe_allow_html=True)
            selected = st.selectbox("Evento da eliminare", range(len(bdf)), format_func=lambda i: f"{i+1} - {bdf.iloc[i]['tipo_evento']} {bdf.iloc[i]['ora_inizio'][:5]}-{bdf.iloc[i]['ora_fine'][:5]}")
            e1, e2, e3 = st.columns(3)
            with e1:
                if st.button("Elimina evento"):
                    st.session_state["buffer"].pop(selected); st.rerun()
            with e2:
                if st.button("Svuota turno"):
                    st.session_state["buffer"] = []; st.session_state["locked_header"] = None; st.rerun()
            with e3:
                if st.button("Salva turno asset", type="primary"):
                    ok, msg = valida_timeline(st.session_state["buffer"], turno, completa=True)
                    if not ok: st.error(msg)
                    else:
                        idta = nuovo_id(); rows = []
                        for i, x in enumerate(st.session_state["buffer"], 1):
                            oi2, of2 = parse_time(x["ora_inizio"]), parse_time(x["ora_fine"])
                            dti, dtf = timestamp_evento(data_turno, turno, oi2, of2)
                            y = {c: x.get(c, "") for c in COL_EVENTI}
                            y.update({"id_evento": f"{idta}-E{i}", "id_turno_asset": idta, "data_turno": str(data_turno),
                                      "turno": turno, "asset": asset, "asset_pianificato": "SI",
                                      "data_ora_inizio": str(dti), "data_ora_fine": str(dtf)})
                            rows.append(y)
                        salva_eventi(pd.concat([leggi_eventi(), pd.DataFrame(rows)], ignore_index=True))
                        st.session_state["buffer"] = []; st.session_state["locked_header"] = None
                        st.session_state["flash"] = f"Turno {turno} - {asset} salvato."; st.rerun()
        else:
            st.info("Nessun evento inserito.")


# -----------------------------------------------------------------------------
# DASHBOARD E STORICO
# -----------------------------------------------------------------------------

if pagina in ["Dashboard Comber", "Dashboard EV200", "Performance complessiva"]:
    df = prepara_eventi(leggi_eventi())
    if not df.empty:
        f1, f2 = st.columns(2)
        with f1: da = st.date_input("Dal", value=df["data_turno"].min().date())
        with f2: a = st.date_input("Al", value=df["data_turno"].max().date())
        df = df[(df["data_turno"].dt.date >= da) & (df["data_turno"].dt.date <= a)]
    if pagina == "Performance complessiva":
        st.subheader("Performance complessiva della linea acquosa")
        kc, ke = calcola_kpi(df, "Comber"), calcola_kpi(df, "EV200")
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(gauge(kc["oee"], "OEE Comber"), use_container_width=True)
        with c2: st.plotly_chart(gauge(ke["oee"], "OEE EV200"), use_container_width=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Puro estratto Comber", f"{kc['output1']:.1f} kg")
        m2.metric("Puro recuperato EV200", f"{ke['output1']:.1f} kg")
        m3.metric("Resa estrattiva", f"{kc['indice']:.1f}%")
        m4.metric("Recupero concentrazione", f"{ke['indice']:.1f}%")
    else:
        asset_name = "Comber" if pagina == "Dashboard Comber" else "EV200"
        st.subheader(f"Dashboard OEE {asset_name}")
        k = calcola_kpi(df, asset_name)
        c1, c2 = st.columns([1.2, 1])
        with c1: st.plotly_chart(gauge(k["oee"], f"OEE {asset_name}"), use_container_width=True)
        with c2:
            st.metric("Disponibilità operativa", f"{k['availability']:.1%}")
            st.metric("Disponibilità tecnica", f"{k['technical']:.1%}")
            st.metric("Performance", f"{k['performance']:.1%}")
            st.metric("Qualità standard", f"{k['quality']:.1%}")
        x1, x2, x3, x4 = st.columns(4)
        if asset_name == "Comber":
            x1.metric("Liquido estratto", f"{k['output2']:.1f} kg")
            x2.metric("Puro estratto", f"{k['output1']:.1f} kg")
            x3.metric("Resa estrattiva", f"{k['indice']:.1f}%")
        else:
            x1.metric("Concentrato", f"{k['output2']:.1f} kg")
            x2.metric("Puro recuperato", f"{k['output1']:.1f} kg")
            x3.metric("Recupero", f"{k['indice']:.1f}%")
        x4.metric("Ore produttive", f"{k['ore_prod']:.1f} h")
        fermi = df[(df["asset"] == asset_name) & (df["tipo_evento"] != "Produzione")]
        if not fermi.empty:
            fg = fermi.groupby("tipo_evento", as_index=False)["durata_h"].sum()
            st.plotly_chart(px.bar(fg, x="tipo_evento", y="durata_h", title="Fermi per causale"), use_container_width=True)

if pagina == "Production vs Target":
    st.subheader("Production vs Target - Comber")
    st.caption("Droga fisica, puro ottenuto, resa media aritmetica ed equivalente standard al 15% di mass yield.")
    chiusure = chiusure_comber(leggi_eventi())
    prodotti = sorted([x for x in chiusure["prodotto"].dropna().astype(str).unique().tolist() if x]) if not chiusure.empty else []
    prodotto_sel = st.selectbox("Prodotto", ["Tutti"] + prodotti)
    if prodotto_sel != "Tutti" and not chiusure.empty:
        chiusure = chiusure[chiusure["prodotto"].astype(str) == prodotto_sel]

    oggi = datetime.today().date()
    ieri = oggi - timedelta(days=1)
    inizio_mese = oggi.replace(day=1)
    inizio_anno = oggi.replace(month=1, day=1)
    try:
        fine_lytd = oggi.replace(year=oggi.year - 1)
    except ValueError:
        fine_lytd = oggi.replace(year=oggi.year - 1, day=28)
    inizio_lytd = fine_lytd.replace(month=1, day=1)
    target_df = leggi_target()

    periodi = [
        ("Yesterday", ieri, ieri),
        ("Month-to-Date", inizio_mese, oggi),
        ("Year-to-Date", inizio_anno, oggi),
        ("Last Year-to-Date", inizio_lytd, fine_lytd),
    ]
    rows = []
    for nome, dal, al in periodi:
        valori = indicatori_periodo(chiusure, dal, al)
        target = target_maturato(target_df, prodotto_sel, dal, al)
        delta = valori["kg_equivalenti_15"] - target if target > 0 else 0
        rows.append({
            "Periodo": nome,
            "Droga fisica lavorata (kg)": valori["kg_droga"],
            "Puro ottenuto (kg)": valori["kg_puro"],
            "Resa media aritmetica (%)": valori["resa_media"],
            "Equivalente 15% (kg eq.)": valori["kg_equivalenti_15"],
            "Target maturato (kg eq.)": target,
            "Scostamento (kg eq.)": delta,
            "Scostamento (%)": safe_div(delta, target) * 100 if target > 0 else 0,
            "Batch chiusi": valori["batch"],
        })

    r = pd.DataFrame(rows)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Yesterday - Eq. 15%", f"{r.iloc[0]['Equivalente 15% (kg eq.)']:.1f} kg")
    k2.metric("Month-to-Date - Eq. 15%", f"{r.iloc[1]['Equivalente 15% (kg eq.)']:.1f} kg")
    k3.metric("Year-to-Date - Eq. 15%", f"{r.iloc[2]['Equivalente 15% (kg eq.)']:.1f} kg")
    k4.metric("Last Year-to-Date - Eq. 15%", f"{r.iloc[3]['Equivalente 15% (kg eq.)']:.1f} kg")
    st.dataframe(r, use_container_width=True, hide_index=True)

    if not chiusure.empty:
        trend = chiusure.copy()
        trend["mese"] = trend["data_turno"].dt.to_period("M").astype(str)
        tg = trend.groupby("mese", as_index=False).agg(
            droga_fisica=("kg_droga", "sum"),
            puro_ottenuto=("kg_puro_estratto", "sum"),
            equivalente_15=("kg_equivalenti_15", "sum"),
            resa_media=("resa_estrattiva_pct", "mean"),
        )
        fig = px.bar(tg, x="mese", y="equivalente_15", text_auto=".1f", title="Produzione mensile equivalente al 15%")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("### Target mensili per prodotto")
    st.caption("Il target è espresso in kg equivalenti al 15% e viene maturato sui giorni lavorativi del periodo.")
    with st.form("target_mensile"):
        t1, t2, t3 = st.columns(3)
        with t1: mese_target = st.date_input("Mese target", value=oggi.replace(day=1), format="DD/MM/YYYY")
        with t2: prodotto_target = st.text_input("Prodotto", value=prodotto_sel if prodotto_sel != "Tutti" else "")
        with t3: valore_target = st.number_input("Target mensile kg eq. 15%", min_value=0.0, step=100.0)
        salva_t = st.form_submit_button("Salva target", type="primary")
    if salva_t:
        if not prodotto_target.strip() or valore_target <= 0:
            st.error("Inserisci prodotto e target maggiore di zero.")
        else:
            nuovo = pd.DataFrame([{"mese": mese_target.strftime("%Y-%m"), "prodotto": prodotto_target.strip(), "target_kg_equivalenti_15": valore_target}])
            tdf = pd.concat([leggi_target(), nuovo], ignore_index=True)
            tdf = tdf.drop_duplicates(subset=["mese", "prodotto"], keep="last")
            salva_target(tdf)
            st.success("Target mensile salvato.")
            st.rerun()
    st.dataframe(leggi_target(), use_container_width=True, hide_index=True)

if pagina == "Storico":
    st.subheader("Storico eventi")
    df = prepara_eventi(leggi_eventi())
    if df.empty: st.info("Nessun dato disponibile.")
    else:
        c1, c2 = st.columns(2)
        with c1: fa = st.selectbox("Asset", ["Tutti", "Comber", "EV200"])
        with c2: ft = st.selectbox("Turno", ["Tutti", "1", "2", "3"])
        if fa != "Tutti": df = df[df["asset"] == fa]
        if ft != "Tutti": df = df[df["turno"] == ft]
        st.dataframe(df, use_container_width=True)


# -----------------------------------------------------------------------------
# CONFIGURAZIONE E GESTIONE DATI
# -----------------------------------------------------------------------------

if pagina == "Configurazione":
    st.subheader("Configurazione capacità nominali")
    cfg = leggi_config()
    with st.form("cfg"):
        comber = st.number_input("Comber - capacità kg droga/h", min_value=0.1, value=float(cfg.loc[cfg['asset']=='Comber','capacita_nominale'].iloc[0]))
        ev200 = st.number_input("EV200 - capacità evaporativa kg acqua/h", min_value=0.1, value=float(cfg.loc[cfg['asset']=='EV200','capacita_nominale'].iloc[0]))
        if st.form_submit_button("Salva configurazione", type="primary"):
            cfg.loc[cfg["asset"] == "Comber", "capacita_nominale"] = comber
            cfg.loc[cfg["asset"] == "EV200", "capacita_nominale"] = ev200
            cfg.to_csv(CONFIG_FILE, index=False); st.success("Configurazione salvata.")
    st.info("Le capacità nominali determinano la Performance OEE. Confermarle con dati tecnici o storico validato.")

if pagina == "Gestione dati":
    st.subheader("Export, import e cancellazione")
    st.download_button("Scarica Excel completo", export_excel(), "oee_estrazione_acquosa_export.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
    up = st.file_uploader("Ripristina da Excel", type=["xlsx"])
    if up is not None:
        try:
            xls = pd.ExcelFile(up)
            if "Eventi turno" in xls.sheet_names and st.button("Importa e sostituisci eventi"):
                salva_eventi(pd.read_excel(xls, "Eventi turno", dtype=str).fillna(""))
                if "Configurazione" in xls.sheet_names:
                    pd.read_excel(xls, "Configurazione").to_csv(CONFIG_FILE, index=False)
                if "Target mensili" in xls.sheet_names:
                    salva_target(pd.read_excel(xls, "Target mensili", dtype=str).fillna(""))
                st.success("Dati importati."); st.rerun()
        except Exception as exc: st.error(f"Errore import: {exc}")
    st.divider()
    conferma = st.checkbox("Confermo la cancellazione di tutti gli eventi")
    if st.button("Cancella storico", disabled=not conferma):
        salva_eventi(pd.DataFrame(columns=COL_EVENTI)); st.success("Storico cancellato."); st.rerun()
