"""Guanzate Blending: consuntivi e OOE del tracciato aziendale."""
from pathlib import Path
import hashlib
import pandas as pd

DATA_PATH = Path('data/guanzate_blending.csv')
NUMERIC = ['Quantità prodotta', 'Quantità scartata', 'Quantità totale', 'Durata Minuti',
           'Tempo Netto Minuti', 'Tempo Ideale Minuti', 'Minuti Fermi Straordinari', 'Minuti Fermi Ordinari']
COLS = ['id', 'Data', 'Ordine/riga', 'Macchina', 'Ora Inizio', 'Ora Fine'] + NUMERIC


def prepare(frame):
    d = frame.copy()
    missing = [c for c in COLS if c != 'id' and c not in d]
    if missing:
        raise ValueError('Colonne mancanti: ' + ', '.join(missing))
    dates = pd.to_datetime(d['Data'], errors='coerce')
    summary = d['Data'].astype(str).str.upper().str.contains('TOTALE', na=False)
    if (dates.isna() & ~summary).any():
        raise ValueError('Sono presenti righe con data assente o non valida.')
    d = d.loc[~summary].copy()
    d['Data'] = dates.loc[d.index].dt.strftime('%Y-%m-%d')
    for c in NUMERIC:
        d[c] = pd.to_numeric(d[c], errors='coerce')
        if d[c].isna().any() or d[c].lt(0).any():
            raise ValueError('Valori mancanti, negativi o non numerici: ' + c)
    if d['Macchina'].fillna('').astype(str).str.strip().eq('').any():
        raise ValueError('Macchina mancante.')
    for c in ['Ordine/riga', 'Macchina', 'Ora Inizio', 'Ora Fine']:
        d[c] = d[c].fillna('').astype(str).str.strip()
    # Stable identities, including occurrence number for identical source rows.
    keys = d[[c for c in COLS if c != 'id']].astype(str).agg('|'.join, axis=1)
    occurrence = keys.groupby(keys).cumcount()
    d['id'] = [hashlib.sha256((k+'|'+str(n)).encode()).hexdigest() for k,n in zip(keys,occurrence)]
    return d[COLS].reset_index(drop=True)


def indicators(d):
    totals = d[NUMERIC].sum()
    def ratio(a,b):
        return float(a/b) if b else None
    quality = ratio(totals['Quantità prodotta'], totals['Quantità totale'])
    availability = ratio(totals['Tempo Netto Minuti'], totals['Durata Minuti'])
    performance = ratio(totals['Tempo Ideale Minuti'], totals['Tempo Netto Minuti'])
    ooe = quality*availability*performance if all(v is not None for v in [quality,availability,performance]) else None
    return totals, quality, availability, performance, ooe


def render_guanzate_blending():
    import streamlit as st
    from persistence import read_optional_dataframe, write_dataframe, soft_delete_ids
    st.title('Guanzate · Blending')
    st.caption('OOE secondo il tracciato Guanzate. Quantità espresse nell’unità del file sorgente.')
    stored = read_optional_dataframe(DATA_PATH, COLS)
    uploaded = st.file_uploader('Importa registrazioni Blending', type=['xlsx'], key='guanzate_upload')
    preview = None
    if uploaded:
        try:
            preview = prepare(pd.read_excel(uploaded, sheet_name='Dati OEE'))
            st.caption(f'{len(preview)} registrazioni · {preview.Data.min()} / {preview.Data.max()}')
            st.dataframe(preview.drop(columns='id'), hide_index=True, use_container_width=True)
            st.caption('Il salvataggio sostituisce i mesi e le macchine presenti nel file. Gli altri periodi restano disponibili.')
            if st.button('Salva registrazioni Guanzate', type='primary', disabled=preview.empty):
                try:
                    # Fresh read for replacement keys; no changes to Lauria datasets.
                    from persistence import invalidate_data_cache
                    invalidate_data_cache()
                    old = read_optional_dataframe(DATA_PATH,COLS)
                    pairs = set(zip(preview.Data.str[:7], preview.Macchina))
                    replaced = pd.Series([(str(a)[:7],str(b)) in pairs for a,b in zip(old.Data,old.Macchina)], index=old.index, dtype=bool)
                    write_dataframe(DATA_PATH, preview, COLS)
                    retired = set(old.loc[replaced,'id']) - set(preview.id)
                    if retired:
                        soft_delete_ids(DATA_PATH, retired)
                    st.success('Registrazioni salvate.'); st.rerun()
                except Exception:
                    st.error('Salvataggio non completato. Verificare che Supabase consenta il dataset guanzate_blending e ripetere l’importazione.')
        except (ValueError, KeyError) as exc:
            st.error(str(exc))
    source = preview if preview is not None else (prepare(stored) if not stored.empty else None)
    if source is None or source.empty:
        st.info('Carica il file Excel delle registrazioni Blending.'); return
    if preview is not None:
        st.info('Anteprima del file caricato. I dati diventano persistenti con Salva registrazioni Guanzate.')
    source['date'] = pd.to_datetime(source.Data)
    machine = st.selectbox('Macchina Guanzate', sorted(source.Macchina.unique()), key='gz_machine')
    source = source[source.Macchina.eq(machine)]
    months = sorted(source.Data.str[:7].unique(), reverse=True)
    month = st.selectbox('Mese Guanzate', months, key='gz_month')
    mode = st.radio('Periodo', ['Mese', 'Cumulato fino al mese selezionato'], horizontal=True, key='gz_period')
    mask = source.Data.str[:7].eq(month) if mode=='Mese' else (source.Data.str[:4].eq(month[:4]) & source.Data.str[:7].le(month))
    d = source[mask].copy()
    totals,q,a,p,ooe = indicators(d)
    def pct(v): return 'N/D' if v is None else f'{v:.2%}'
    for col,label,value in zip(st.columns(4),['OOE Guanzate','Qualità','Disponibilità','Performance'],[ooe,q,a,p]):
        col.metric(label,pct(value))
    for col,label,key in zip(st.columns(3),['Quantità prodotta','Quantità scartata','Ore registrate'],['Quantità prodotta','Quantità scartata','Durata Minuti']):
        col.metric(label, f'{totals[key]/60 if key=="Durata Minuti" else totals[key]:,.1f}')
    st.caption('Quality = buoni / totale; Availability = tempo netto / durata; Performance = tempo ideale / netto; OOE = Q × A × P. Rapporti delle somme, senza limite artificiale al 100%. I fermi ordinari seguono il tempo netto del file.')
    repeated = d.duplicated(['Data','Macchina','Ora Inizio','Ora Fine'],keep=False)
    high = d['Tempo Ideale Minuti'].gt(d['Tempo Netto Minuti'])
    if repeated.any():
        st.warning(f'{int(repeated.sum())} righe condividono data, macchina e intervallo con altre righe. I tempi sono sommati come nel file sorgente; verificare la ripartizione prima di validare l’OOE.')
    if high.any(): st.warning(f'{int(high.sum())} registrazioni hanno Performance superiore al 100%.')
    st.caption(f'Copertura disponibile: {d.Data.min()} – {d.Data.max()}. La presenza di un mese non ne certifica la completezza.')
    daily=[]
    for day,g in d.groupby('Data'):
        t,quality,availability,performance,effectiveness=indicators(g)
        daily.append({'Data':day,'OOE (%)':effectiveness*100 if effectiveness is not None else None,'Quantità prodotta':t['Quantità prodotta']})
    daily=pd.DataFrame(daily).set_index('Data')
    st.subheader('Andamento giornaliero')
    st.line_chart(daily[['OOE (%)']])
    st.bar_chart(daily[['Quantità prodotta']])
    with st.expander('Dettaglio registrazioni e controlli'):
        st.dataframe(d.drop(columns=['id','date']), hide_index=True,use_container_width=True)
        if repeated.any(): st.dataframe(d.loc[repeated].drop(columns=['id','date']),hide_index=True,use_container_width=True)
    st.download_button('Esporta periodo CSV',d.drop(columns=['id','date']).to_csv(index=False).encode('utf-8-sig'),'guanzate_blending.csv','text/csv')
