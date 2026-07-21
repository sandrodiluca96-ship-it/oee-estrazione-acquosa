from datetime import datetime, time, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st


DATA = Path("data")
EVENTI_FILE = DATA / "eventi.csv"
PRODUZIONI_FILE = DATA / "produzioni.csv"
TURNI_FILE = DATA / "turni.csv"
PRODOTTI_FILE = DATA / "anagrafica_prodotti.csv"
CAUSALI_FILE = DATA / "causali.csv"
PLANNING_FILE = DATA / "pianificazione_comber.csv"

TURNI = {"1": (time(6), time(14)), "2": (time(14), time(22)), "3": (time(22), time(6))}
TIPI_PRODUZIONE = ["Apertura lotto", "Prosecuzione lotto", "Chiusura lotto"]

COL_EVENTI = [
    "id_evento", "id_turno", "data_turno", "turno", "macchina", "tipo_evento",
    "tipo_produzione", "lotto", "codice", "descrizione", "ora_inizio", "ora_fine",
    "durata_h", "kg_droga", "kg_liquido", "rs_liquido_pct", "kg_liquido_alimentato",
    "rs_iniziale_pct", "kg_concentrato", "rs_finale_pct", "kg_molle", "rs_molle_pct",
    "kg_maltodestrina", "kg_polvere_finale", "lotti_comber", "piano_id", "note",
]
COL_PRODUZIONI = [
    "id", "id_turno", "data_turno", "turno", "macchina", "lotto", "codice_droga",
    "codice_semilavorato", "descrizione", "kg_droga", "kg_liquido", "residuo_secco_pct",
    "kg_puro", "kg_semilavorato", "pct_puro_semilavorato", "kg_puro_equivalente", "lotti_comber", "piano_id", "note",
]
COL_TURNI = ["id_turno", "data_turno", "turno", "macchina", "ore_pianificate", "ore_produzione", "ore_fermo", "note"]
COL_PRODOTTI = ["tipo", "codice", "descrizione", "pct_puro_standard", "attivo"]
COL_CAUSALI = ["causale", "categoria", "esclusa_pianificato", "perdita_tecnica", "attiva"]
COL_PLANNING = ["piano_id","settimana","data_inizio","data_fine","ora_inizio","ora_fine","prodotto","lotto_droga","estrazioni_pianificate","kg_per_estrazione","kg_pianificati","impianto","caricato_il"]


def _read(path, columns):
    DATA.mkdir(exist_ok=True)
    if not path.exists(): pd.DataFrame(columns=columns).to_csv(path, index=False)
    df = pd.read_csv(path, dtype=str).fillna("")
    for c in columns:
        if c not in df.columns: df[c] = ""
    return df[columns]


def _save(df, path, columns):
    for c in columns:
        if c not in df.columns: df[c] = ""
    df[columns].to_csv(path, index=False)


def _number(v):
    x = pd.to_numeric(str(v).replace(",", "."), errors="coerce")
    return 0.0 if pd.isna(x) else float(x)


def _parse_time(v):
    try: return datetime.strptime(str(v)[:5], "%H:%M").time()
    except Exception: return None


def _duration(start, end):
    if not start or not end: return 0.0
    a = datetime.combine(datetime.today(), start); b = datetime.combine(datetime.today(), end)
    if b <= a: b += timedelta(days=1)
    return (b-a).total_seconds()/3600


def _shift_minute(t, shift):
    if not t: return None
    start = TURNI[shift][0].hour*60
    value = t.hour*60+t.minute
    return value+1440 if value < start else value


def _times(shift):
    if shift not in TURNI: return []
    start=TURNI[shift][0].hour*60; end=TURNI[shift][1].hour*60
    if end <= start: end += 1440
    return [f"{(m%1440)//60:02d}:{(m%1440)%60:02d}" for m in range(start,end+1,15)]


def _validate(rows, shift, complete=False):
    if not rows: return False, "Inserisci almeno un evento."
    intervals=[]
    for i,r in enumerate(rows,1):
        a=_shift_minute(_parse_time(r.get("ora_inizio")),shift)
        b=_shift_minute(_parse_time(r.get("ora_fine")),shift)
        if a is None or b is None: return False,f"Evento {i}: orari non validi."
        if b <= a: b += 1440
        start=TURNI[shift][0].hour*60; end=TURNI[shift][1].hour*60
        if end <= start: end += 1440
        if a < start or b > end: return False,f"Evento {i}: orario esterno al turno."
        intervals.append((a,b,i))
    intervals.sort(); cursor=TURNI[shift][0].hour*60
    end=TURNI[shift][1].hour*60
    if end <= cursor: end += 1440
    for a,b,i in intervals:
        if a < cursor: return False,f"Evento {i}: sovrapposto al precedente."
        if complete and a > cursor: return False,"Esiste un intervallo del turno non coperto."
        cursor=b
    if complete and cursor != end: return False,"Gli eventi non coprono esattamente le 8 ore."
    return True,"Timeline valida."


def _saved_open_lots(machine):
    ev=_read(EVENTI_FILE,COL_EVENTI)
    ev=ev[(ev["macchina"]==machine)&(ev["tipo_evento"]=="Produzione")]
    opened=[]
    for r in ev.itertuples():
        if r.tipo_produzione=="Apertura lotto" and r.lotto: opened.append(r.lotto)
        elif r.tipo_produzione=="Chiusura lotto" and r.lotto in opened: opened.remove(r.lotto)
    return opened


def _lot_source(machine,lot,buffer):
    rows=[]
    saved=_read(EVENTI_FILE,COL_EVENTI)
    if not saved.empty: rows += saved[(saved["macchina"]==machine)&(saved["lotto"]==lot)].to_dict("records")
    rows += [r for r in buffer if r.get("lotto")==lot]
    return rows


def _first(rows,key):
    for r in rows:
        if str(r.get(key,"")).strip() and _number(r.get(key))!=0: return _number(r.get(key))
    return 0.0


def _first_text(rows,key):
    for r in rows:
        if str(r.get(key,"")).strip(): return str(r.get(key))
    return ""


def _create_production(machine,lot,shift_id,data_turno,shift,buffer):
    rows=[r for r in _lot_source(machine,lot,buffer) if r.get("tipo_evento")=="Produzione"]
    code=_first_text(rows,"codice"); desc=_first_text(rows,"descrizione")
    out={c:"" for c in COL_PRODUZIONI}
    out.update({"id":f"LOT-{machine}-{lot}","id_turno":shift_id,"data_turno":str(data_turno),"turno":shift,"macchina":machine,"lotto":lot,"descrizione":desc,"note":"Generato dalla chiusura lotto"})
    if machine=="Comber":
        drug=_first(rows,"kg_droga")
        liquid=sum(_number(r.get("kg_liquido")) for r in rows)
        pure=sum(_number(r.get("kg_liquido"))*_number(r.get("rs_liquido_pct"))/100 for r in rows)
        out.update({"codice_droga":code,"kg_droga":drug,"kg_liquido":liquid,"residuo_secco_pct":pure/liquid*100 if liquid else 0,"kg_puro":pure,"kg_puro_equivalente":max(drug*.15,pure)})
    elif machine=="EV200":
        feed=sum(_number(r.get("kg_liquido_alimentato")) for r in rows)
        concentrate=max([_number(r.get("kg_concentrato")) for r in rows]+[0])
        rs_final=max([_number(r.get("rs_finale_pct")) for r in rows]+[0])
        pure=concentrate*rs_final/100
        out.update({"codice_droga":code,"kg_liquido":feed,"residuo_secco_pct":rs_final,"kg_puro":pure,"kg_puro_equivalente":pure,"lotti_comber":_first_text(rows,"lotti_comber")})
    else:
        molle=_first(rows,"kg_molle"); rs=_first(rows,"rs_molle_pct"); malto=_first(rows,"kg_maltodestrina")
        final=max([_number(r.get("kg_polvere_finale")) for r in rows]+[0]); pure=max(final-malto,0)
        equivalent=max(pure,final*.40) if final else 0
        out.update({"codice_semilavorato":code,"kg_liquido":molle,"residuo_secco_pct":rs,"kg_puro":pure,"kg_semilavorato":final,"pct_puro_semilavorato":pure/final*100 if final else 0,"kg_puro_equivalente":equivalent,"note":f"Maltodestrina: {malto:.1f} kg"})
    return out


def _product_options(machine):
    products=_read(PRODOTTI_FILE,COL_PRODOTTI)
    products=products[products["attivo"].str.upper()=="SI"]
    # Comber ed EV200 condividono la stessa anagrafica della droga.
    # Lo Spray Dryer continua invece a usare i codici semilavorato.
    kind="Semilavorato" if machine=="Spray Dryer" else "Droga"
    return products[products["tipo"]==kind].copy()


def _comber_lots_for_ev200():
    """Lotti Comber disponibili, inclusi quelli ancora aperti."""
    events=_read(EVENTI_FILE,COL_EVENTI)
    events=events[(events["macchina"]=="Comber")&(events["tipo_evento"]=="Produzione")]
    rows=[]
    for lot,group in events.groupby("lotto",sort=False):
        if not str(lot).strip(): continue
        last=group.iloc[-1]
        rows.append({"lotto":str(lot),"codice":str(last.get("codice","") or ""),"descrizione":str(last.get("descrizione","") or "")})
    productions=_read(PRODUZIONI_FILE,COL_PRODUZIONI)
    productions=productions[productions["macchina"]=="Comber"]
    for r in productions.itertuples():
        rows.append({"lotto":str(r.lotto),"codice":str(r.codice_droga or r.codice_semilavorato or ""),"descrizione":str(r.descrizione or "")})
    unique={r["lotto"]:r for r in rows if r["lotto"]}
    return list(unique.values())


def _open_comber_plans():
    plans=_read(PLANNING_FILE,COL_PLANNING)
    if plans.empty: return []
    events=_read(EVENTI_FILE,COL_EVENTI)
    completed=set(events[(events["macchina"]=="Comber")&(events["tipo_produzione"]=="Chiusura lotto")]["piano_id"])
    return plans[~plans["piano_id"].isin(completed)].to_dict("records")


def _product_selector(machine,state,reset,current_code="",key_suffix=""):
    products=_product_options(machine)
    products["label"]=products["codice"].astype(str)+" — "+products["descrizione"].astype(str)
    labels=products["label"].tolist()
    old_label=next((x for x in labels if x.startswith(str(current_code)+" — ")),None)
    field_label={"Comber":"Codice droga e descrizione *","EV200":"Codice prodotto e descrizione *","Spray Dryer":"Codice semilavorato e descrizione *"}[machine]
    options=["-- Seleziona --"]+labels
    selected=st.selectbox(
        field_label,options,index=options.index(old_label) if old_label else 0,
        help="Digita una parte del codice o della descrizione per cercare il prodotto.",
        key=f"product_lookup_{state}_{reset}_{key_suffix}",
    )
    if selected=="-- Seleziona --": return "",""
    code=selected.split(" — ")[0]
    description=str(products[products["codice"]==code].iloc[0]["descrizione"])
    st.success(f"Selected: {code} — {description}")
    return code,description


def render_machine_workflow(machine):
    state=f"wf_{machine.replace(' ','_')}"
    if state not in st.session_state:
        st.session_state[state]={"buffer":[],"edit":None,"draft":None,"next":"","reset":0,"header":None}
    s=st.session_state[state]; buffer=s["buffer"]
    css={"Comber":"comber","EV200":"ev200","Spray Dryer":"spray"}[machine]
    desc={"Comber":"Estrazione acquosa per singola estrazione","EV200":"Concentrazione dei lotti estratti","Spray Dryer":"Essiccazione semilavorati"}[machine]
    st.markdown(f'<div class="machine-head {css}">{machine}<div class="machine-note">{desc}</div></div>',unsafe_allow_html=True)
    locked=bool(buffer); header=s.get("header")
    c1,c2=st.columns(2)
    with c1: day=st.date_input("Data turno",value=datetime.strptime(header[0],"%Y-%m-%d").date() if header else None,format="DD/MM/YYYY",disabled=locked,key=f"day_{state}_{s['reset']}")
    with c2:
        choices=["-- Seleziona turno --","1","2","3"]
        shift=st.selectbox("Turno",choices,index=choices.index(header[1]) if header else 0,disabled=locked,key=f"shift_{state}_{s['reset']}")
    if shift=="-- Seleziona turno --":
        st.info("Seleziona data e turno per iniziare."); return
    st.caption(f"Turno {shift}: {TURNI[shift][0]:%H:%M}–{TURNI[shift][1]:%H:%M} · gli eventi devono coprire 8 ore.")
    edit=s.get("edit"); current=buffer[edit] if edit is not None and edit<len(buffer) else s.get("draft")
    st.markdown("### Aggiungi evento" if current is None else "### Modifica / duplica evento")
    causes=_read(CAUSALI_FILE,COL_CAUSALI); active_causes=causes[causes["attiva"].str.upper()=="SI"]["causale"].tolist()
    event_types=["Produzione"]+active_causes
    default_type=current.get("tipo_evento") if current else None
    event_type=st.selectbox("Tipo evento",event_types,index=event_types.index(default_type) if default_type in event_types else None,placeholder="Seleziona evento",key=f"etype_{state}_{s['reset']}")
    times=_times(shift); last_end=buffer[-1]["ora_fine"][:5] if buffer else TURNI[shift][0].strftime("%H:%M")
    start_default=(current.get("ora_inizio","")[:5] if current else s.get("next") or last_end)
    end_default=(current.get("ora_fine","")[:5] if current else "")
    a,b=st.columns(2)
    with a: start_txt=st.selectbox("Ora inizio",["--"]+times,index=(["--"]+times).index(start_default) if start_default in times else 0,key=f"start_{state}_{s['reset']}")
    with b: end_txt=st.selectbox("Ora fine",["--"]+times,index=(["--"]+times).index(end_default) if end_default in times else 0,key=f"end_{state}_{s['reset']}")
    start=_parse_time(start_txt); end=_parse_time(end_txt); hours=_duration(start,end)
    if start and end: st.metric("Durata evento",f"{hours:.2f} h")
    row={c:"" for c in COL_EVENTI}; row.update({"tipo_evento":event_type or "","ora_inizio":start_txt if start else "","ora_fine":end_txt if end else "","durata_h":hours,"macchina":machine})
    if event_type=="Produzione":
        open_lots=list(dict.fromkeys(_saved_open_lots(machine)+[r.get("lotto","") for r in buffer if r.get("tipo_produzione")=="Apertura lotto"]))
        closed={r.get("lotto") for r in buffer if r.get("tipo_produzione")=="Chiusura lotto"}; open_lots=[x for x in open_lots if x and x not in closed]
        default_stage=current.get("tipo_produzione") if current else ("Prosecuzione lotto" if open_lots else "Apertura lotto")
        stage=st.selectbox("Tipo produzione",TIPI_PRODUZIONE,index=TIPI_PRODUZIONE.index(default_stage),key=f"stage_{state}_{s['reset']}"); row["tipo_produzione"]=stage
        if stage=="Apertura lotto":
            lot=st.text_input("Lotto *",value=current.get("lotto","") if current else "",key=f"lot_{state}_{s['reset']}")
            if machine=="EV200":
                sources=_comber_lots_for_ev200()
                labels=[f'{r["lotto"]} — {r["codice"]} — {r["descrizione"]}' for r in sources]
                previous=set(str(current.get("lotti_comber","")).split(";")) if current else set()
                defaults=[x for x in labels if x.split(" — ")[0] in previous]
                linked=st.multiselect("Lotti Comber da concentrare *",labels,default=defaults,help="Puoi unire più lotti soltanto se appartengono allo stesso prodotto.",key=f"link_{state}_{s['reset']}")
                selected=[next(r for r in sources if r["lotto"]==x.split(" — ")[0]) for x in linked]
                codes={r["codice"] for r in selected if r["codice"]}
                descriptions={r["descrizione"] for r in selected if r["descrizione"]}
                same_product=len(codes)<=1 and len(descriptions)<=1
                if selected and same_product:
                    code=selected[0]["codice"]; description=selected[0]["descrizione"]
                    row["lotti_comber"]=";".join(r["lotto"] for r in selected)
                    st.success(f"Prodotto ereditato: {code} — {description}")
                else:
                    code=description=""
                    if selected: st.error("I lotti selezionati appartengono a prodotti differenti.")
            else:
                old_code=current.get("codice","") if current else ""
                code,description=_product_selector(machine,state,s["reset"],old_code,"opening")
            row.update({"lotto":lot,"codice":code,"descrizione":description})
        else:
            options=open_lots
            old_lot=current.get("lotto","") if current else ""
            lot=st.selectbox("Lotto aperto *",options,index=options.index(old_lot) if old_lot in options else 0 if options else None,placeholder="Nessun lotto aperto",key=f"openlot_{state}_{s['reset']}")
            src=_lot_source(machine,lot,buffer) if lot else []
            row.update({"lotto":lot or "","codice":_first_text(src,"codice"),"descrizione":_first_text(src,"descrizione"),"lotti_comber":_first_text(src,"lotti_comber"),"piano_id":_first_text(src,"piano_id")})
            if lot: st.success(f"Lotto ripreso: {lot} · {_first_text(src,'codice')} · {_first_text(src,'descrizione')}")
        if machine=="Comber":
            if stage=="Apertura lotto": row["kg_droga"]=st.number_input("Droga caricata totale (kg) *",min_value=0.0,value=_number(current.get("kg_droga")) if current else 0.0,key=f"drug_{state}_{s['reset']}")
            x,y=st.columns(2)
            with x: row["kg_liquido"]=st.number_input("Liquido di questa estrazione (kg) *",min_value=0.0,value=_number(current.get("kg_liquido")) if current else 0.0,key=f"liq_{state}_{s['reset']}")
            with y: row["rs_liquido_pct"]=st.number_input("Residuo secco estrazione (%) *",min_value=0.0,max_value=100.0,value=_number(current.get("rs_liquido_pct")) if current else 0.0,key=f"rs_{state}_{s['reset']}")
            st.info(f"Puro di questa estrazione: {_number(row['kg_liquido'])*_number(row['rs_liquido_pct'])/100:.1f} kg")
        elif machine=="EV200":
            if stage=="Chiusura lotto":
                x,y=st.columns(2)
                with x: row["kg_concentrato"]=st.number_input("Concentrato finale (kg) *",min_value=0.0,value=_number(current.get("kg_concentrato")) if current else 0.0,key=f"conc_{state}_{s['reset']}")
                with y: row["rs_finale_pct"]=st.number_input("Residuo secco finale (%) *",min_value=0.0,max_value=100.0,value=_number(current.get("rs_finale_pct")) if current else 0.0,key=f"rsf_{state}_{s['reset']}")
                st.info(f"Puro concentrato ottenuto: {_number(row['kg_concentrato'])*_number(row['rs_finale_pct'])/100:.1f} kg")
        else:
            if stage=="Apertura lotto":
                x,y,z=st.columns(3)
                with x: row["kg_molle"]=st.number_input("Kg molle *",min_value=0.0,value=_number(current.get("kg_molle")) if current else 0.0,key=f"molle_{state}_{s['reset']}")
                with y: row["rs_molle_pct"]=st.number_input("Residuo secco molle (%) *",min_value=0.0,max_value=100.0,value=_number(current.get("rs_molle_pct")) if current else 0.0,key=f"rsm_{state}_{s['reset']}")
                with z: row["kg_maltodestrina"]=st.number_input("Maltodestrina (kg)",min_value=0.0,value=_number(current.get("kg_maltodestrina")) if current else 0.0,key=f"malto_{state}_{s['reset']}")
            if stage=="Chiusura lotto": row["kg_polvere_finale"]=st.number_input("Polvere finale ottenuta (kg) *",min_value=0.0,value=_number(current.get("kg_polvere_finale")) if current else 0.0,key=f"powder_{state}_{s['reset']}")
    row["note"]=st.text_area("Note",value=current.get("note","") if current else "",key=f"note_{state}_{s['reset']}")
    cadd,ccancel=st.columns(2)
    with cadd: add=st.button("Aggiorna evento" if edit is not None else "Aggiungi evento",type="primary",key=f"add_{state}_{s['reset']}")
    with ccancel: cancel=st.button("Annulla modifica",disabled=current is None,key=f"cancel_{state}_{s['reset']}")
    if cancel:
        s.update({"edit":None,"draft":None}); s["reset"]+=1; st.rerun()
    if add:
        if not event_type or not start or not end or hours<=0: st.error("Seleziona evento e orari validi.")
        elif event_type=="Produzione" and (not row["lotto"] or not row["codice"] or not row["descrizione"]): st.error("Lotto, codice e descrizione sono obbligatori.")
        elif machine=="Comber" and event_type=="Produzione" and (_number(row["kg_liquido"])<=0 or _number(row["rs_liquido_pct"])<=0): st.error("Inserisci quantità e residuo secco della singola estrazione.")
        elif machine=="EV200" and event_type=="Produzione" and stage=="Apertura lotto" and not row.get("lotti_comber"): st.error("Seleziona almeno un lotto Comber da concentrare.")
        elif machine=="EV200" and event_type=="Produzione" and stage=="Chiusura lotto" and (_number(row["kg_concentrato"])<=0 or _number(row["rs_finale_pct"])<=0): st.error("Inserisci concentrato finale e residuo secco finale.")
        else:
            candidate=buffer.copy()
            if edit is not None: candidate[edit]=row
            else: candidate.append(row)
            valid,msg=_validate(candidate,shift,False)
            if not valid: st.error(msg)
            else:
                if edit is not None: buffer[edit]=row
                else: buffer.append(row)
                s.update({"edit":None,"draft":None,"next":row["ora_fine"][:5],"header":(str(day),shift)}); s["reset"]+=1; st.rerun()
    st.divider(); st.markdown("### Eventi inseriti nel turno")
    if buffer:
        view=pd.DataFrame(buffer)[["tipo_evento","tipo_produzione","lotto","codice","descrizione","ora_inizio","ora_fine","durata_h"]]
        st.dataframe(view,use_container_width=True,hide_index=True)
        selected=st.selectbox("Evento da gestire",range(len(buffer)),format_func=lambda i:f"{i+1} · {buffer[i]['tipo_evento']} · {buffer[i]['ora_inizio'][:5]}–{buffer[i]['ora_fine'][:5]}",key=f"manage_{state}")
        m1,m2,m3=st.columns(3)
        if m1.button("Modifica",key=f"edit_{state}"): s["edit"]=selected; s["draft"]=None; s["reset"]+=1; st.rerun()
        if m2.button("Duplica",key=f"dup_{state}"):
            draft=buffer[selected].copy(); draft["ora_inizio"]=buffer[-1]["ora_fine"][:5]; draft["ora_fine"]=""; draft["durata_h"]=0
            s["draft"]=draft; s["edit"]=None; s["reset"]+=1; st.rerun()
        if m3.button("Elimina",key=f"del_{state}"):
            buffer.pop(selected); s["edit"]=None; s["draft"]=None; s["next"]=buffer[-1]["ora_fine"][:5] if buffer else ""; st.rerun()
        total=sum(_number(r.get("durata_h")) for r in buffer); st.metric("Ore coperte",f"{total:.2f} / 8.00 h")
        valid,msg=_validate(buffer,shift,True)
        if valid: st.success("Turno completo e pronto per il salvataggio.")
        else: st.warning(msg)
        confirm=st.checkbox("Confermo il salvataggio definitivo del turno",key=f"confirm_{state}")
        if st.button("Salva turno",type="primary",disabled=not(valid and confirm),key=f"save_{state}"):
            shift_id=f"{day:%Y%m%d}-{shift}-{machine.replace(' ','_')}"; stamp=datetime.now().strftime("%Y%m%d%H%M%S")
            saved=[]
            for i,r in enumerate(buffer,1):
                x={c:r.get(c,"") for c in COL_EVENTI}; x.update({"id_evento":f"{stamp}-{i}","id_turno":shift_id,"data_turno":str(day),"turno":shift,"macchina":machine}); saved.append(x)
            all_events=_read(EVENTI_FILE,COL_EVENTI); _save(pd.concat([all_events,pd.DataFrame(saved)],ignore_index=True),EVENTI_FILE,COL_EVENTI)
            productions=_read(PRODUZIONI_FILE,COL_PRODUZIONI)
            for r in buffer:
                if r.get("tipo_evento")=="Produzione" and r.get("tipo_produzione")=="Chiusura lotto":
                    prod=_create_production(machine,r["lotto"],shift_id,day,shift,buffer)
                    productions=productions[~((productions["macchina"]==machine)&(productions["lotto"]==r["lotto"]))]
                    productions=pd.concat([productions,pd.DataFrame([prod])],ignore_index=True)
            _save(productions,PRODUZIONI_FILE,COL_PRODUZIONI)
            prod_h=sum(_number(r["durata_h"]) for r in buffer if r.get("tipo_evento")=="Produzione"); stop_h=8-prod_h
            turns=_read(TURNI_FILE,COL_TURNI); turns=turns[turns["id_turno"]!=shift_id]
            turn={"id_turno":shift_id,"data_turno":str(day),"turno":shift,"macchina":machine,"ore_pianificate":8,"ore_produzione":prod_h,"ore_fermo":stop_h,"note":"Salvato da timeline eventi"}
            _save(pd.concat([turns,pd.DataFrame([turn])],ignore_index=True),TURNI_FILE,COL_TURNI)
            s.update({"buffer":[],"edit":None,"draft":None,"next":"","header":None}); s["reset"]+=1
            st.success("Turno salvato correttamente."); st.rerun()
    else: st.info("Nessun evento inserito.")
    st.divider(); st.markdown(f"### Ultimi eventi salvati — {machine}")
    saved_all=_read(EVENTI_FILE,COL_EVENTI); recent=saved_all[saved_all["macchina"]==machine].tail(30).copy()
    if recent.empty:
        st.caption("Nessun evento definitivo ancora salvato.")
    else:
        st.caption("Gli eventi definitivi restano correggibili. ID, turno e macchina sono protetti.")
        edited=st.data_editor(
            recent,use_container_width=True,hide_index=True,num_rows="fixed",
            disabled=["id_evento","id_turno","macchina"],key=f"saved_editor_{state}",
        )
        confirm_edit=st.checkbox("Confermo la correzione degli eventi definitivi",key=f"confirm_saved_{state}")
        if st.button("Salva correzioni eventi",disabled=not confirm_edit,key=f"save_saved_{state}"):
            valid_all=True; error=""
            for shift_id,grp in edited.groupby("id_turno"):
                shift_value=str(grp.iloc[0]["turno"])
                ok,msg=_validate(grp.to_dict("records"),shift_value,True)
                if not ok: valid_all=False; error=f"Turno {shift_id}: {msg}"; break
            if not valid_all: st.error(error)
            else:
                base=saved_all[~saved_all["id_evento"].isin(recent["id_evento"])]
                updated=pd.concat([base,edited],ignore_index=True); _save(updated,EVENTI_FILE,COL_EVENTI)
                productions=_read(PRODUZIONI_FILE,COL_PRODUZIONI)
                for lot in edited[edited["tipo_produzione"]=="Chiusura lotto"]["lotto"].unique():
                    closure=edited[(edited["lotto"]==lot)&(edited["tipo_produzione"]=="Chiusura lotto")].iloc[-1]
                    prod=_create_production(machine,lot,closure["id_turno"],closure["data_turno"],str(closure["turno"]),[])
                    productions=productions[~((productions["macchina"]==machine)&(productions["lotto"]==lot))]
                    productions=pd.concat([productions,pd.DataFrame([prod])],ignore_index=True)
                _save(productions,PRODUZIONI_FILE,COL_PRODUZIONI)
                st.success("Eventi e quantità di lotto ricalcolati."); st.rerun()
