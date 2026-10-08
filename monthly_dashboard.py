"""Monthly/weekly reporting and late Spray Dryer batch completion."""
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import unicodedata
import re
import math
import html
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from persistence import read_dataframe, read_optional_dataframe, write_dataframe
from oee_analytics import calculate_effectiveness

REF_PATH=Path('data/yield_references.csv')
REF_COLS=['materia_prima','yield_pct']
MAP_PATH=Path('data/yield_mapping.csv')
MAP_COLS=['codice','materia_prima']
HIST_PATH=Path('data/ooe_monthly_history.csv')
HIST_COLS=['anno','mese','macchina','ooe_pct','ore_riferimento']

def tr(it,en):
    return en if st.session_state.get('ui_language')=='English' else it

def normalize(value):
    value=unicodedata.normalize('NFKD',str(value)).encode('ascii','ignore').decode().upper()
    return re.sub(r'\s+',' ',value.replace('_X000D_',' ')).strip()

def prepare_lots(frame):
    d=frame.copy()
    d['date']=pd.to_datetime(d['data_turno'],errors='coerce')
    for c in ['kg_droga','kg_puro','kg_puro_equivalente','kg_semilavorato','pct_puro_semilavorato']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    d['yield_pct']=d.kg_puro.div(d.kg_droga.where(d.kg_droga>0))*100
    d['equivalent_yield_pct']=d.kg_puro_equivalente.div(d.kg_droga.where(d.kg_droga>0))*100
    valid=(d.kg_semilavorato>0)&d.pct_puro_semilavorato.between(0,100)
    d['cut_pct']=(100-d.pct_puro_semilavorato).where(valid)
    d['semi_equivalent']=d.kg_puro_equivalente/.4
    return d

def attach_references(lots,refs,mapping):
    d=lots.copy(); by_name={normalize(r.materia_prima):float(r.yield_pct) for r in refs.itertuples() if pd.notna(r.yield_pct)}
    codes=dict(zip(mapping.codice.astype(str),mapping.materia_prima.astype(str)))
    d['reference_name']=[codes.get(str(c),str(desc)) for c,desc in zip(d.codice_droga,d.descrizione)]
    d['reference_pct']=d.reference_name.map(lambda s:by_name.get(normalize(s),float('nan')))
    d['delta_pp']=d.yield_pct-d.reference_pct
    return d

def metrics(d):
    def total(c):return d[c].sum(min_count=1)
    matched=d[d.yield_pct.notna()&d.reference_pct.notna()]
    return {'kg_droga':total('kg_droga'),'kg_puro':total('kg_puro'),'kg_puro_equivalente':total('kg_puro_equivalente'),
            'yield_pct':d.yield_pct.mean(),'equivalent_yield_pct':d.equivalent_yield_pct.mean(),
            'kg_semilavorato':total('kg_semilavorato'),'semi_equivalent':total('semi_equivalent'),'cut_pct':d.cut_pct.mean(),
            'reference_pct':matched.reference_pct.mean(),'delta_pp':matched.delta_pp.mean()}

def pending_lots(events,prod,start,end):
    ev=events[(events.macchina=='Spray Dryer')&(events.tipo_evento=='Produzione')].copy()
    ev['date']=pd.to_datetime(ev.data_turno,errors='coerce')
    ev['lot_key']=ev.lotto.astype(str).str.strip().str.upper()
    period=ev[(ev.date>=pd.Timestamp(start))&(ev.date<=pd.Timestamp(end))]
    result=[]
    for lot,g in period.groupby('lot_key'):
        allg=ev[ev.lot_key==lot]
        closed=allg.tipo_produzione.eq('Chiusura lotto').any() or allg.stato_lotto.eq('Completato').any()
        cons=prod[(prod.macchina=='Spray Dryer')&prod.lotto.astype(str).str.strip().str.upper().eq(lot)]
        valid=pd.to_numeric(cons.kg_semilavorato,errors='coerce').gt(0).any()
        if not closed or not valid:
            result.append({'lotto':lot,'descrizione':g.descrizione.dropna().iloc[0] if g.descrizione.notna().any() else '',
                           'ultima_data':allg.date.max().date(),'chiuso':closed,'quantita_presente':valid})
    return pd.DataFrame(result)

def close_lot(events,productions,lot,event_id,kg,pure_pct):
    """Pure transformation: one production row per machine/batch; event hours unchanged."""
    from event_workflow import COL_PRODUZIONI
    if not math.isfinite(kg) or not math.isfinite(pure_pct) or not kg>0 or not 0<=pure_pct<=100:raise ValueError('Invalid quantity/composition')
    ev=events.copy(); mask=(ev.macchina=='Spray Dryer')&ev.lotto.astype(str).str.strip().str.upper().eq(str(lot).strip().upper())
    selected=ev[mask&ev.id_evento.eq(event_id)]
    if len(selected)!=1:raise ValueError('Select one existing event')
    row=selected.iloc[0]
    # Clear previous closing quantities; corrections must permit lower totals too.
    ev.loc[mask,'kg_polvere_finale']=float('nan')
    previous=mask&ev.tipo_produzione.eq('Chiusura lotto')
    ev.loc[previous,'tipo_produzione']='Prosecuzione lotto'
    ev.loc[mask,'stato_lotto']='In corso'
    ev.loc[selected.index,'tipo_produzione']='Chiusura lotto'
    ev.loc[selected.index,'stato_lotto']='Completato'
    ev.loc[selected.index,'kg_polvere_finale']=kg
    pure=kg*pure_pct/100
    ev.loc[selected.index,'note']=str(row.get('note','') or '')+' | Consuntivo a valle: puro confermato '+str(pure_pct)+'%'
    out={c:'' for c in COL_PRODUZIONI}
    out.update(id=f'LOT-Spray Dryer-{lot}',id_turno=row.id_turno,data_turno=row.data_turno,turno=row.turno,macchina='Spray Dryer',lotto=lot,
               codice_semilavorato=row.codice,descrizione=row.descrizione,kg_semilavorato=kg,kg_puro=pure,
               pct_puro_semilavorato=pure_pct,kg_puro_equivalente=max(pure,kg*.4),note='Consuntivo a valle; composizione confermata')
    keep=~((productions.macchina=='Spray Dryer')&productions.lotto.astype(str).str.strip().str.upper().eq(str(lot).strip().upper()))
    return ev,pd.concat([productions[keep],pd.DataFrame([out])],ignore_index=True)

def render_late_completion():
    from event_workflow import EVENTI_FILE,COL_EVENTI,PRODUZIONI_FILE,COL_PRODUZIONI
    st.title(tr('Consuntivo e chiusura lotti','Batch completion and final quantity'))
    events=read_dataframe(EVENTI_FILE,COL_EVENTI);productions=read_dataframe(PRODUZIONI_FILE,COL_PRODUZIONI)
    ev=events[(events.macchina=='Spray Dryer')&(events.tipo_evento=='Produzione')&events.lotto.fillna('').ne('')].copy()
    if ev.empty:st.info(tr('Nessun lotto disponibile.','No batches available.'));return
    st.caption(tr('Aggiorna un solo consuntivo del lotto. Ore e turni restano invariati. La data deriva dall’evento di fine produzione selezionato.','Update one batch total. Hours and shifts remain unchanged. The production date comes from the selected final event.'))
    show_closed=st.checkbox(tr('Mostra anche i lotti chiusi','Also show closed batches'),key='late_show_closed')
    dates=pd.to_datetime(ev.data_turno,errors='coerce').dropna()
    pending=pending_lots(events,productions,dates.min().date(),dates.max().date())
    if not pending.empty:st.dataframe(pending,hide_index=True,use_container_width=True)
    allowed=set(pending.lotto.astype(str)) if not pending.empty else set()
    options=sorted(ev.lotto.unique()) if show_closed else sorted(v for v in ev.lotto.unique() if str(v).strip().upper() in allowed)
    if not options:
        st.success(tr('Nessun lotto aperto da completare.','No open batches to complete.'))
        return
    if st.session_state.get('late_lot') not in options:st.session_state['late_lot']=options[0]
    lot=st.selectbox(tr('Lotto','Batch'),options,key='late_lot')
    rows=ev[ev.lotto==lot].sort_values(['data_turno','turno','ora_inizio'])
    st.dataframe(rows[['data_turno','turno','ora_inizio','ora_fine','descrizione','tipo_produzione','kg_polvere_finale']],hide_index=True)
    selected=st.selectbox(tr('Evento di fine produzione','Final production event'),rows.id_evento.tolist(),index=len(rows)-1,
        format_func=lambda v: ' · '.join(str(rows[rows.id_evento==v].iloc[0][c]) for c in ['data_turno','turno','ora_fine']),key='late_event_'+str(lot))
    current=productions[(productions.macchina=='Spray Dryer')&productions.lotto.astype(str).str.strip().str.upper().eq(str(lot).strip().upper())]
    def initial(c,default):
        v=pd.to_numeric(current[c],errors='coerce').dropna();return float(v.iloc[-1]) if not v.empty else default
    with st.form('late_form_'+str(lot)):
        kg=st.number_input(tr('Polvere totale del lotto (kg)','Total batch powder (kg)'),min_value=0.,value=initial('kg_semilavorato',0.))
        pct=st.number_input(tr('Estratto puro nel semilavorato (%)','Pure extract in semi-finished product (%)'),min_value=0.,max_value=100.,value=initial('pct_puro_semilavorato',40.))
        confirmed=st.checkbox(tr('Confermo peso, composizione e data effettiva di fine produzione','I confirm weight, composition and actual production completion date'))
        save=st.form_submit_button(tr('Salva quantità e chiudi lotto','Save quantity and close batch'))
    if save:
        if not confirmed or kg<=0:st.error(tr('Conferma i dati e inserisci una quantità positiva.','Confirm the data and enter a positive quantity.'));return
        # Re-read immediately before writing to avoid overwriting a stale page snapshot.
        fresh_e=read_dataframe(EVENTI_FILE,COL_EVENTI);fresh_p=read_dataframe(PRODUZIONI_FILE,COL_PRODUZIONI)
        new_e,new_p=close_lot(fresh_e,fresh_p,lot,selected,kg,pct)
        write_dataframe(EVENTI_FILE,new_e,COL_EVENTI)
        try:
            write_dataframe(PRODUZIONI_FILE,new_p,COL_PRODUZIONI)
            # Persistence upserts do not delete absent rows; retire superseded IDs explicitly.
            from persistence import soft_delete_ids
            retired=set(fresh_p.id.astype(str))-set(new_p.id.astype(str))
            if retired:soft_delete_ids(PRODUZIONI_FILE,retired)
        except Exception:
            st.error(tr('Chiusura evento salvata, ma consuntivo non salvato. Ripeti questa operazione per completarlo.','Event closure saved, but production total failed. Repeat this operation to complete it.'));return
        st.success(tr('Lotto chiuso e consuntivo aggiornato.','Batch closed and production total updated.'));st.rerun()

def metric_card(label, value, unit, previous, accent):
    def fmt(v):
        if pd.isna(v):return tr('N/D','N/A')
        return f"{v:,.1f}".replace(',', 'X').replace('.', ',').replace('X', '.') if st.session_state.get('ui_language')!='English' else f"{v:,.1f}"
    delta=value-previous
    change=tr('Confronto non disponibile','Comparison unavailable') if pd.isna(delta) else f"{delta:+,.1f} {'p.p.' if unit=='%' else 'kg'} · "+tr('vs stesso mese LY','vs same month LY')
    return f'<div class="evra-card" style="border-top:4px solid {accent}"><div class="evra-label">{html.escape(label)}</div><div class="evra-value">{fmt(value)} <span>{unit}</span></div><div class="evra-change">{html.escape(change)}</div></div>'


@st.cache_data(ttl=30, show_spinner=False)
def cached_effectiveness(events, productions, causes, targets, quality, start, end):
    return calculate_effectiveness(events, productions, causes, targets, quality, start, end)


def render_monthly_dashboard(productions,events,causes,targets,quality):
    st.markdown('''<style>
.evra-banner{padding:20px 24px;background:linear-gradient(110deg,#12334b,#176a79);color:white;border-radius:14px;margin-bottom:20px}
.evra-banner h1{font-size:28px;color:white;margin:0}.evra-banner p{margin:6px 0 0;color:#d9eef4}
.evra-card{background:var(--secondary-background-color);border-radius:12px;padding:18px 18px 14px;min-height:150px;margin:5px 0 16px;border:1px solid #879eaa40}
.evra-label{font-size:14px;font-weight:600;min-height:22px}.evra-value{font-size:32px;font-weight:750;margin:12px 0;line-height:1.1}.evra-value span{font-size:16px;font-weight:400}.evra-change{font-size:12px;opacity:.8}
.evra-section{font-size:23px;font-weight:700;border-left:5px solid;padding-left:12px;margin:28px 0 12px}
</style>''',unsafe_allow_html=True)
    st.markdown('<div class="evra-banner"><h1>'+tr('Produzione Lauria','Lauria production')+'</h1><p>'+tr('Risultati del mese · confronti storici · trend settimanali','Monthly results · historical comparisons · weekly trends')+'</p></div>',unsafe_allow_html=True)
    d=prepare_lots(productions)
    refs=read_optional_dataframe(REF_PATH,REF_COLS);mapping=read_optional_dataframe(MAP_PATH,MAP_COLS)
    refs.yield_pct=pd.to_numeric(refs.yield_pct,errors='coerce')
    d=attach_references(d,refs,mapping)
    today=(datetime.now(ZoneInfo('Europe/Rome'))-timedelta(hours=6)).date()
    years=sorted(set(d.date.dropna().dt.year.astype(int))|{today.year},reverse=True)
    year=st.selectbox(tr('Anno','Year'),years,key='monthly_year')
    month=st.selectbox(tr('Mese','Month'),range(1,13),index=today.month-1,key='monthly_month')
    start=date(year,month,1);end=(pd.Timestamp(start)+pd.offsets.MonthEnd()).date()
    if year==today.year and month==today.month:end=today
    last_month=month-1 if year==today.year and month==today.month else month
    ytd_end=(pd.Timestamp(date(year,last_month,1))+pd.offsets.MonthEnd()).date() if last_month else date(year-1,12,31)
    lytd_end=(pd.Timestamp(date(year-1,last_month,1))+pd.offsets.MonthEnd()).date() if last_month else date(year-2,12,31)
    prev_end=(pd.Timestamp(date(year-1,month,1))+pd.offsets.MonthEnd()).date()
    hist=read_optional_dataframe(HIST_PATH,HIST_COLS)
    for c in HIST_COLS:
        if c!='macchina':hist[c]=pd.to_numeric(hist[c],errors='coerce')
    cache={}
    report_tables=[]
    def ooe(machine,a,b):
        if a>b:return float('nan')
        he=hist[(hist.anno==a.year)&(hist.macchina==machine)&hist.mese.between(a.month,b.month)]
        if a.day==1 and b==(pd.Timestamp(b)+pd.offsets.MonthEnd()).date() and set(he.mese)==set(range(a.month,b.month+1)):
            weights=he.ore_riferimento
            if he.ooe_pct.notna().all() and weights.notna().all() and weights.sum()>0:return float((he.ooe_pct*weights).sum()/weights.sum())
        key=(a,b)
        if key not in cache:cache[key]=cached_effectiveness(events,productions,causes,targets,quality,a,b)
        result=next((r for r in cache[key] if r['Macchina']==machine),None)
        # Do not pretend that July-onward operational records cover a full YTD.
        dates=pd.to_datetime(events.loc[events.macchina==machine,'data_turno'],errors='coerce').dropna()
        if dates.empty or a<dates.min().date():return float('nan')
        return result['OOE']*100 if result and result['Ore totali']>0 else float('nan')
    st.caption(tr('Calendario lunedì 06:00–sabato 06:00. Medie yield e taglio aritmetiche per lotto. OOE sui tempi registrati; la completezza dei turni va verificata.','Calendar Monday 06:00–Saturday 06:00. Arithmetic batch averages for yield and cut. OOE uses recorded time; shift completeness must be checked.'))
    ndup=events.drop(columns=['id_evento']).duplicated().sum()
    if ndup:st.warning(tr(f'{ndup} eventi ripetuti: copie identiche escluse dal calcolo OOE, dati originali conservati.',f'{ndup} repeated events: identical copies excluded from OOE calculations; original data retained.'))
    pending=pending_lots(events,productions,start,end)
    if not pending.empty:
        st.warning(tr(f'Consuntivo incompleto: {len(pending)} lotti da verificare nel mese.',f'Incomplete totals: {len(pending)} batches to review this month.'))
        with st.expander(tr('Lotti da verificare','Batches to review')):st.dataframe(pending,hide_index=True)
    labels={'ooe_pct':'OOE (%)','kg_droga':tr('Materia prima (kg)','Raw material (kg)'), 'kg_puro':tr('Secco reale (kg)','Actual dry solids (kg)'),
      'kg_puro_equivalente':tr('Secco equivalente (kg)','Equivalent dry solids (kg)'), 'yield_pct':'Mass Yield (%)','equivalent_yield_pct':tr('Yield equivalente (%)','Equivalent yield (%)'),
      'kg_semilavorato':tr('Semilavorato reale (kg)','Actual semi-finished (kg)'), 'semi_equivalent':tr('Semilavorato equivalente (kg)','Equivalent semi-finished (kg)'), 'cut_pct':tr('Taglio medio (%)','Mean excipient cut (%)')}
    for machine in ['Comber','Spray Dryer']:
        accent='#187c92' if machine=='Comber' else '#b87523'
        section=tr('Estrazione · Comber','Extraction · Comber') if machine=='Comber' else 'Spray Dryer · Plant Lauria'
        st.markdown(f'<div class="evra-section" style="border-color:{accent}">{section}</div>',unsafe_allow_html=True)
        md=d[d.macchina==machine]
        def values(a,b):
            z=md[(md.date>=pd.Timestamp(a))&(md.date<=pd.Timestamp(b))];result=metrics(z);result['ooe_pct']=ooe(machine,a,b);return result
        periods={tr('Mese','Month'):values(start,end),tr('Mese LY','Month LY'):values(date(year-1,month,1),prev_end),
                 'YTD':values(date(year,1,1),ytd_end),'LYTD':values(date(year-1,1,1),lytd_end),'LY':values(date(year-1,1,1),date(year-1,12,31))}
        keys=['ooe_pct','kg_droga','kg_puro','kg_puro_equivalente','yield_pct','equivalent_yield_pct'] if machine=='Comber' else ['ooe_pct','kg_semilavorato','semi_equivalent','cut_pct']
        main=['ooe_pct','kg_droga','kg_puro','yield_pct'] if machine=='Comber' else ['ooe_pct','kg_semilavorato','semi_equivalent','cut_pct']
        cards=st.columns(4)
        for col,key in zip(cards,main):
            with col:
                st.markdown(metric_card(labels[key],periods[tr('Mese','Month')][key], '%' if key.endswith('_pct') else 'kg',periods[tr('Mese LY','Month LY')][key],accent),unsafe_allow_html=True)
        records=[]
        for key in keys:
            row={'KPI':labels[key],**{p:v[key] for p,v in periods.items()}}
            row['Δ YTD / LYTD']=periods['YTD'][key]-periods['LYTD'][key]
            if key.startswith('kg_') or key=='semi_equivalent':row['Δ YTD / LYTD (%)']=100*(periods['YTD'][key]/periods['LYTD'][key]-1) if periods['LYTD'][key]>0 else float('nan')
            records.append(row)
        summary=pd.DataFrame(records).set_index('KPI')
        with st.expander(tr('Confronti completi · Mese, YTD, LYTD e LY','Full comparisons · Month, YTD, LYTD and LY')):
            st.dataframe(summary.style.format(precision=2,na_rep=tr('N/D','N/A')),use_container_width=True)
        report_tables.append('<h2>'+machine+'</h2>'+summary.to_html(float_format=lambda v:f'{v:,.2f}',na_rep='N/D'))
        st.caption(tr('Δ delle percentuali in punti percentuali. YTD/LYTD fino all’ultimo mese chiuso selezionato.','Percentage differences are percentage points. YTD/LYTD end at the selected last closed month.'))
        view=st.radio(tr('Andamento','Trend'),['monthly','weekly','batch'] if machine=='Comber' else ['monthly','weekly'],format_func=lambda k:{'monthly':tr('Mensile','Monthly'),'weekly':tr('Settimanale','Weekly'),'batch':tr('Yield per lotto','Yield by batch')}[k],horizontal=True,key='trend_'+machine)
        metric=st.selectbox('KPI',keys,key='metric_'+machine,format_func=lambda k:labels[k])
        descs=sorted(md.descrizione.dropna().astype(str).unique())
        with st.expander(tr('Filtra per prodotto','Filter by product')):
            selected=st.multiselect(tr('Prodotti','Products'),descs,key='products_'+machine)
        filtered=md[md.descrizione.isin(selected)] if selected else md
        if metric=='ooe_pct' and selected:st.caption(tr('OOE resta riferito all’intero impianto.','OOE remains a whole-machine indicator.'))
        if view=='batch':
            z=filtered[(filtered.date>=pd.Timestamp(start))&(filtered.date<=pd.Timestamp(end))].sort_values('date')
            custom=z[['descrizione','lotto','reference_pct','delta_pp']].fillna(tr('N/D','N/A')).to_numpy()
            colors=['gray' if pd.isna(v) else 'green' if v>0 else 'red' if v<0 else 'gray' for v in z.delta_pp]
            fig=go.Figure(go.Scatter(x=z.date,y=z.yield_pct,mode='lines+markers',marker_color=colors,customdata=custom,name='Mass Yield',hovertemplate='%{customdata[0]}<br>%{customdata[1]}<br>%{x|%d/%m/%Y}<br>Yield: %{y:.2f}%<br>'+tr('Storico','Reference')+': %{customdata[2]}%<br>Δ: %{customdata[3]} p.p.<extra></extra>'))
            fig.add_trace(go.Scatter(x=z.date,y=z.reference_pct,mode='lines',line_dash='dash',name=tr('Riferimento storico','Historical reference'),connectgaps=False))
        else:
            stop=min(date(year,12,31),today) if year>=today.year else date(year,12,31)
            starts=list(pd.date_range(date(year,1,1),stop,freq='MS').date) if view=='monthly' else list(pd.date_range(date(year,1,1)-timedelta(days=date(year,1,1).weekday()),stop,freq='7D').date)
            points=[]
            for a in starts:
                b=min((pd.Timestamp(a)+pd.offsets.MonthEnd()).date() if view=='monthly' else a+timedelta(days=4),stop)
                a=max(a,date(year,1,1));z=filtered[(filtered.date>=pd.Timestamp(a))&(filtered.date<=pd.Timestamp(b))]
                vals=metrics(z);v=ooe(machine,a,b) if metric=='ooe_pct' else vals[metric]
                names='<br>'.join(str(n) for n in z.descrizione.dropna().unique())
                points.append((a,v,names,z.lotto.nunique(),vals['reference_pct']))
            fig=go.Figure(go.Scatter(x=[p[0] for p in points],y=[p[1] for p in points],mode='lines+markers',connectgaps=False,customdata=[[p[2],p[3]] for p in points],name=labels[metric],hovertemplate='%{x|%d/%m/%Y}<br>%{y:.2f}<br>'+tr('Lotti','Batches')+': %{customdata[1]}<br>%{customdata[0]}<extra></extra>'))
            if view=='monthly':
                prior=[]
                for a,_,_,_,_ in points:
                    pa=date(year-1,a.month,1);pb=(pd.Timestamp(pa)+pd.offsets.MonthEnd()).date()
                    old=filtered[(filtered.date>=pd.Timestamp(pa))&(filtered.date<=pd.Timestamp(pb))]
                    prior.append(ooe(machine,pa,pb) if metric=='ooe_pct' else metrics(old)[metric])
                fig.add_trace(go.Scatter(x=[p[0] for p in points],y=prior,mode='lines+markers',line_dash='dot',name=str(year-1),connectgaps=False))
            if metric=='yield_pct':fig.add_trace(go.Scatter(x=[p[0] for p in points],y=[p[4] for p in points],mode='lines',line_dash='dash',name=tr('Storico degli stessi lotti','Matched batch historical mean'),connectgaps=False))
        for index,trace in enumerate(fig.data):
            if not (view=='batch' and index==0):trace.update(line_color=accent if index==0 else '#8997a3',line_width=3 if index==0 else 2)
        fig.update_layout(title='Mass Yield (%)' if view=='batch' else labels[metric],height=380,hovermode='closest',margin=dict(l=20,r=20,t=55,b=20),legend=dict(orientation='h',y=1.12,x=0),font=dict(family='Arial',size=13))
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor='#879eaa25',zeroline=False)
        st.plotly_chart(fig,use_container_width=True)
        detail=filtered[(filtered.date>=pd.Timestamp(start))&(filtered.date<=pd.Timestamp(end))]
        with st.expander(tr('Dettaglio lotti del mese','Monthly batch details')):
            cols=['data_turno','lotto','descrizione','kg_droga','kg_puro','yield_pct','reference_pct','delta_pp'] if machine=='Comber' else ['data_turno','lotto','descrizione','kg_semilavorato','pct_puro_semilavorato','cut_pct','semi_equivalent','note']
            st.dataframe(detail[cols],hide_index=True,use_container_width=True)
        if machine=='Comber' and detail.reference_pct.isna().any():st.caption(tr('Alcuni prodotti non hanno un riferimento associato: nessun confronto automatico per questi lotti.','Some products have no mapped reference: no automatic comparison for those batches.'))
    report='<html><meta charset="utf-8"><style>body{font-family:Arial;margin:25px}table{border-collapse:collapse;font-size:12px}td,th{border:1px solid #ddd;padding:6px}@media print{button{display:none}}</style><button onclick="window.print()">Print / Stampa</button><h1>Lauria '+str(year)+'-'+str(month).zfill(2)+'</h1><p>OOE; arithmetic batch mean yield and cut. Production totals may be incomplete. Review batch warnings in the app.</p>'+''.join(report_tables)+'</html>'
    st.download_button(tr('Scarica report stampabile','Download printable report'),report.encode('utf-8'),'Lauria_monthly_report.html','text/html',key='monthly_print')
    with st.expander(tr('Riferimenti storici e associazione codici','Historical references and code mapping')):
        edited=st.data_editor(refs,num_rows='dynamic',key='reference_editor')
        mapped=st.data_editor(mapping,num_rows='dynamic',key='mapping_editor')
        st.caption(tr('Associare il codice droga alla descrizione esatta del riferimento; varianti e combinazioni restano distinte.','Map each raw-material code to the exact reference description; variants and combinations remain distinct.'))
        if st.button(tr('Salva riferimenti e associazioni','Save references and mappings'),key='save_refs'):
            edited.yield_pct=pd.to_numeric(edited.yield_pct,errors='coerce')
            if edited.materia_prima.isna().any() or edited.materia_prima.duplicated().any() or not edited.yield_pct.between(0,100).all() or mapped.codice.duplicated().any() or not mapped.materia_prima.isin(edited.materia_prima).all():st.error(tr('Verifica descrizioni, codici univoci e percentuali 0–100.','Check descriptions, unique codes and percentages 0–100.'))
            else:
                try:
                    write_dataframe(REF_PATH,edited,REF_COLS);write_dataframe(MAP_PATH,mapped,MAP_COLS)
                except Exception:
                    st.error(tr('Salvataggio configurazioni rifiutato dal database. I dati produttivi non sono stati modificati. Verifica i nuovi dataset nei log Supabase/Streamlit.', 'Database rejected configuration save. Production data were not modified. Check new datasets in Supabase/Streamlit logs.'))
                else:st.rerun()
    with st.expander(tr('OOE storico mensile','Historical monthly OOE')):
        edited=st.data_editor(hist,num_rows='dynamic',key='ooe_history')
        st.caption(tr('OOE 0–100%; ore del denominatore OOE per ponderare i cumulati. Nessuna ricostruzione OOE dai soli kg.','OOE 0–100%; denominator hours for cumulative weighting. OOE cannot be reconstructed from kg alone.'))
        if st.button(tr('Salva OOE storico','Save historical OOE'),key='save_ooe_history'):
            for c in HIST_COLS:
                if c!='macchina':edited[c]=pd.to_numeric(edited[c],errors='coerce')
            valid=not edited[HIST_COLS].isna().any().any() and not edited.duplicated(['anno','mese','macchina']).any() and edited.macchina.isin(['Comber','Spray Dryer']).all() and edited.mese.between(1,12).all() and edited.ooe_pct.between(0,100).all() and edited.ore_riferimento.gt(0).all() and (edited[['anno','mese']]%1==0).all().all()
            if valid:
                try:write_dataframe(HIST_PATH,edited,HIST_COLS)
                except Exception:st.error(tr('Salvataggio storico OOE rifiutato dal database: verifica il vincolo dataset nei log.', 'Database rejected OOE history save: check dataset constraints in logs.'))
                else:st.rerun()
            else:st.error(tr('Verifica valori e duplicati.','Check values and duplicates.'))
