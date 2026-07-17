import html
from datetime import date, datetime, time, timedelta
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(page_title="OEE Produzione Lauria", page_icon="🏭", layout="wide")

VERSIONE = "2.0.0"
QUALITA = 0.95
GIORNI_ANNO = 220
TARGET = {
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

COL_TURNI = ["id_turno", "data_turno", "turno", "macchina", "ore_pianificate", "ore_produzione", "ore_fermo", "note"]
COL_LOTTI = [
    "id", "id_turno", "data_turno", "turno", "macchina", "lotto", "codice_droga",
    "codice_semilavorato", "descrizione", "kg_droga", "kg_liquido", "residuo_secco_pct",
    "kg_puro", "kg_semilavorato", "pct_puro_semilavorato", "kg_puro_equivalente", "note",
]
COL_PRODOTTI = ["tipo", "codice", "descrizione", "pct_puro_standard", "attivo"]
COL_CAUSALI = ["causale", "categoria", "esclusa_pianificato", "perdita_tecnica", "attiva"]


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
.summary .name{font-size:21px;font-weight:800}.summary .value{font-size:18px;font-weight:800}.summary .label{font-size:13px;opacity:.95}
.table-wrap{overflow-x:auto;background:#FFF;border:1px solid var(--line);border-radius:10px;margin-top:18px;padding:18px}
.prod-table{border-collapse:collapse;width:100%;min-width:1500px;font-size:13px}
.prod-table th{padding:10px 7px;border-bottom:2px solid #3892E5;text-align:center;color:#27323A;background:#FFF}
.prod-table td{padding:9px 7px;border-bottom:1px solid #E5E9ED;text-align:right;color:#263238}
.prod-table td:first-child{text-align:left;font-weight:700;border-right:2px solid #3892E5}
.prod-table tr:nth-child(even){background:#F0F2F4}.prod-table tr.group{font-weight:800;background:#E7EEF5}
.ach-good{color:#16815D!important;font-weight:800}.ach-mid{color:#C27700!important;font-weight:800}.ach-low{color:#C43D3D!important;font-weight:800}
.hint{background:#EAF4FB;border-left:5px solid #2F73B5;padding:12px;border-radius:5px;color:#254A64}
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


def num(v):
    x = pd.to_numeric(str(v).replace(",", "."), errors="coerce")
    return 0.0 if pd.isna(x) else float(x)


def pct(n, d): return n / d * 100 if d else 0.0


def workdays(start, end):
    if end < start: return 0
    return sum(1 for x in pd.date_range(start, end) if x.weekday() < 5)


def annual_day_target(machine, metric): return TARGET[machine][metric]


def target_period(machine, metric, start, end, annual=False):
    if annual: return annual_day_target(machine, metric) * GIORNI_ANNO
    return annual_day_target(machine, metric) * workdays(start, end)


def equivalent_comber(kg_drug, kg_pure):
    # Regola aziendale: minimo convenzionale 15%; rese migliori restano reali.
    return max(kg_drug * 0.15, kg_pure)


def prep_production():
    df = read_csv(LOTTI_FILE, COL_LOTTI)
    if df.empty: return df
    df["data_turno"] = pd.to_datetime(df["data_turno"], errors="coerce")
    for c in ["kg_droga","kg_liquido","residuo_secco_pct","kg_puro","kg_semilavorato","pct_puro_semilavorato","kg_puro_equivalente"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


def period_value(df, machine, metric, start, end):
    if df.empty: return 0.0
    x = df[(df["macchina"] == machine) & (df["data_turno"].dt.date >= start) & (df["data_turno"].dt.date <= end)]
    col = "kg_puro_equivalente" if metric == "equivalente" else ("kg_semilavorato" if machine == "Spray Dryer" else "kg_puro")
    return float(x[col].sum())


def fmt(v): return f"{v:,.0f}".replace(",", ".")


def summary_band(name, css, df, machine, metric, periods):
    cells = [f'<div class="name">{html.escape(name)} (kg)</div>']
    for label, (start, end) in periods.items():
        cells.append(f'<div><div class="value">{fmt(period_value(df,machine,metric,start,end))}</div><div class="label">{label}</div></div>')
    st.markdown(f'<div class="summary {css}">{"".join(cells)}</div>', unsafe_allow_html=True)


def ach_class(v): return "ach-good" if v >= 100 else ("ach-mid" if v >= 75 else "ach-low")


def dashboard_table(df, today):
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=today.weekday()); week_end = week_start + timedelta(days=6)
    month_start = today.replace(day=1); month_end = (pd.Timestamp(month_start) + pd.offsets.MonthEnd()).date()
    year_start = today.replace(month=1, day=1); year_end = today.replace(month=12, day=31)
    try: ly_end = today.replace(year=today.year - 1)
    except ValueError: ly_end = today.replace(year=today.year - 1, day=28)
    ly_start = ly_end.replace(month=1, day=1)
    rows = [
        ("Comber – Estratto puro", "Comber", "fisico"), ("Comber – Puro equivalente 15%", "Comber", "equivalente"),
        ("EV200 – Concentrato puro", "EV200", "fisico"), ("EV200 – Puro equivalente", "EV200", "equivalente"),
        ("Spray Dryer – Semilavorato", "Spray Dryer", "fisico"), ("Spray Dryer – Puro equivalente 40%", "Spray Dryer", "equivalente"),
    ]
    heads = ["Produzione", "Yesterday", "Yesterday Target", "Achievement", "Week to Date", "Week Target", "Achievement", "Month to Date", "Month Target", "Achievement", "Year to Date", "Year Target", "Achievement", "Last Year YTD"]
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


def xlsx_export():
    out=BytesIO()
    with pd.ExcelWriter(out,engine="openpyxl") as w:
        read_csv(TURNI_FILE,COL_TURNI).to_excel(w,"Turni",index=False)
        read_csv(LOTTI_FILE,COL_LOTTI).to_excel(w,"Produzioni",index=False)
        read_csv(PRODOTTI_FILE,COL_PRODOTTI).to_excel(w,"Anagrafica prodotti",index=False)
        read_csv(CAUSALI_FILE,COL_CAUSALI).to_excel(w,"Causali",index=False)
    out.seek(0); return out


init_data()
st.sidebar.title("🏭 Produzione Lauria")
page=st.sidebar.radio("Sezione",["Dashboard unica","Inserimento turno","OEE per macchina","Storico","Anagrafiche e causali","Import / Export"])
st.sidebar.caption(f"Versione {VERSIONE} · Qualità standard {QUALITA:.0%}")

if page=="Dashboard unica":
    today=st.date_input("Data report",value=date.today(),format="DD/MM/YYYY")
    week_start=today-timedelta(days=today.weekday()); month_start=today.replace(day=1)
    st.markdown(f'<div class="report-head"><div class="report-title">Production vs. Target Report ({today:%d/%m/%Y})</div><div class="report-sub">Daily, Weekly, Monthly, Year-to-Date &nbsp; · &nbsp; Month {month_start:%d/%m/%Y}–{(pd.Timestamp(month_start)+pd.offsets.MonthEnd()).date():%d/%m/%Y} &nbsp; · &nbsp; Week {week_start:%d/%m/%Y}–{week_start+timedelta(days=6):%d/%m/%Y}</div></div>',unsafe_allow_html=True)
    df=prep_production(); yesterday=today-timedelta(days=1); prev_end=month_start-timedelta(days=1); prev_start=prev_end.replace(day=1)
    try: ly=today.replace(year=today.year-1)
    except ValueError: ly=today.replace(year=today.year-1,day=28)
    periods={"Yesterday":(yesterday,yesterday),"Week":(week_start,today),"Month":(month_start,today),"Previous Month":(prev_start,prev_end),"YTD Production":(today.replace(month=1,day=1),today),"Last year YTD":(ly.replace(month=1,day=1),ly)}
    summary_band("Comber – Puro equivalente 15%","navy",df,"Comber","equivalente",periods)
    summary_band("EV200 – Concentrato puro","blue",df,"EV200","fisico",periods)
    summary_band("Spray Dryer – Puro equivalente 40%","green",df,"Spray Dryer","equivalente",periods)
    st.markdown(dashboard_table(df,today),unsafe_allow_html=True)
    st.caption("Target: Comber 150 kg/giorno; EV200 168,75 kg/giorno; Spray Dryer 321,6 kg semilavorato e 128,64 kg equivalente; 220 giorni/anno.")

elif page=="Inserimento turno":
    st.title("Inserimento turno")
    machine=st.selectbox("Macchina",["Comber","EV200","Spray Dryer"])
    c1,c2=st.columns(2)
    with c1: d=st.date_input("Data di inizio turno",value=date.today(),format="DD/MM/YYYY")
    with c2: shift=st.selectbox("Turno",["1","2","3"])
    shift_id=f"{d:%Y%m%d}-{shift}-{machine.replace(' ','_')}"
    products=read_csv(PRODOTTI_FILE,COL_PRODOTTI); active=products[products["attivo"].str.upper()=="SI"]
    drug=active[active["tipo"]=="Droga"]; semi=active[active["tipo"]=="Semilavorato"]
    with st.form("production"):
        st.markdown(f"### Produzione {machine}")
        lot=st.text_input("Lotto")
        descr=st.text_input("Descrizione prodotto/estratto")
        code_drug=""; code_semi=""; kg_drug=kg_liquid=rs=kg_pure=kg_semi=0.0; pure_pct=40.0
        if machine=="Comber":
            opts=[f"{r.codice} — {r.descrizione}" for r in drug.itertuples()]
            sel=st.selectbox("Codice droga",opts,index=None,placeholder="Seleziona codice")
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
            sel=st.selectbox("Codice semilavorato",opts,index=None,placeholder="Seleziona codice")
            code_semi=sel.split(" — ")[0] if sel else ""
            a,b=st.columns(2)
            with a: kg_semi=st.number_input("Semilavorato totale ottenuto (kg)",min_value=0.0)
            with b: pure_pct=st.number_input("Percentuale puro (%)",min_value=0.0,max_value=100.0,value=40.0)
            kg_pure=kg_semi*pure_pct/100
            st.info(f"Puro equivalente: {kg_pure:.1f} kg")
        notes=st.text_area("Note")
        submit=st.form_submit_button("Salva produzione",type="primary")
    if submit:
        if not lot.strip(): st.error("Inserisci il lotto.")
        elif machine=="Comber" and (not code_drug or kg_drug<=0): st.error("Seleziona la droga e inserisci i kg lavorati.")
        elif machine=="Spray Dryer" and (not code_semi or kg_semi<=0): st.error("Seleziona il semilavorato e inserisci la quantità.")
        else:
            eq=equivalent_comber(kg_drug,kg_pure) if machine=="Comber" else kg_pure
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

elif page=="OEE per macchina":
    st.title("OEE per macchina")
    machine=st.selectbox("Macchina",list(TARGET)); turns=read_csv(TURNI_FILE,COL_TURNI)
    if turns.empty: st.info("Nessun turno consuntivato.")
    else:
        x=turns[turns["macchina"]==machine].copy()
        for c in ["ore_pianificate","ore_produzione","ore_fermo"]: x[c]=pd.to_numeric(x[c],errors="coerce").fillna(0)
        availability=x["ore_produzione"].sum()/x["ore_pianificate"].sum() if x["ore_pianificate"].sum() else 0
        prod=prep_production(); output=period_value(prod,machine,"equivalente",date(2000,1,1),date(2100,1,1)); target=TARGET[machine]["equivalente"]*len(x)
        performance=output/target if target else 0; oee=availability*performance*QUALITA
        a,b=st.columns([1.4,1]);
        with a: st.plotly_chart(gauge(oee,f"OEE {machine}"),use_container_width=True)
        with b: st.metric("Disponibilità",f"{availability:.1%}"); st.metric("Performance",f"{performance:.1%}"); st.metric("Qualità",f"{QUALITA:.1%}")

elif page=="Storico":
    st.title("Storico produzioni")
    df=prep_production(); machine=st.selectbox("Filtra macchina",["Tutte"]+list(TARGET))
    if machine!="Tutte" and not df.empty: df=df[df["macchina"]==machine]
    st.dataframe(df,use_container_width=True,hide_index=True)

elif page=="Anagrafiche e causali":
    st.title("Anagrafiche e causali")
    tab1,tab2=st.tabs(["Codici prodotto","Causali"])
    with tab1:
        with st.form("new_product"):
            a,b=st.columns(2)
            with a: typ=st.selectbox("Tipo",["Droga","Semilavorato"]); code=st.text_input("Codice")
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

elif page=="Import / Export":
    st.title("Importazione ed esportazione")
    st.download_button("Scarica backup Excel completo",xlsx_export(),"oee_produzione_lauria_backup.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",type="primary")
    up=st.file_uploader("Importa un backup creato da questa app",type=["xlsx"])
    if up and st.button("Importa e sostituisci i dati"):
        try:
            xl=pd.ExcelFile(up)
            mapping={"Turni":(TURNI_FILE,COL_TURNI),"Produzioni":(LOTTI_FILE,COL_LOTTI),"Anagrafica prodotti":(PRODOTTI_FILE,COL_PRODOTTI),"Causali":(CAUSALI_FILE,COL_CAUSALI)}
            for sheet,(path,cols) in mapping.items():
                if sheet in xl.sheet_names: save_csv(pd.read_excel(xl,sheet,dtype=str).fillna(""),path,cols)
            st.success("Importazione completata. Ricarica la pagina.")
        except Exception as exc: st.error(f"Impossibile importare: {exc}")
    st.markdown('<div class="hint">Per non perdere i dati su Streamlit Cloud, scarica periodicamente il backup Excel. Il file può essere ricaricato integralmente in questa pagina.</div>',unsafe_allow_html=True)
