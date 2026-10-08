# EVRA Lauria — aggiornamento 4.2.0

## Installazione
1. Conservare una copia della versione attuale e un backup del database.
2. Copiare i file del pacchetto nel progetto, mantenendo i Secrets Streamlit e gli asset già presenti. Nessuna credenziale è inclusa.
3. Caricare anche `data/yield_references.csv`, `data/yield_mapping.csv` e `data/ooe_monthly_history.csv`. I CSV del backup sono inclusi come seed: non sostituiscono dataset già esistenti in Supabase.
4. Avviare `streamlit run app.py` con le dipendenze di requirements.txt.
5. Verificare in Supabase che eventuali vincoli sul campo dataset consentano yield_references, yield_mapping e ooe_monthly_history. La tabella app_records esistente resta la fonte di persistenza.

## Nuove pagine
- Dashboard mensile Lauria: Comber e Spray Dryer; grafici mensili, settimanali e yield per lotto; confronti mese LY, YTD, LYTD, LY; report HTML stampabile.
- Consuntivo e chiusura lotti: selezionare lotto ed evento effettivo di fine produzione, inserire polvere totale e percentuale di puro verificata, confermare. Il peso corregge il consuntivo del lotto, non si aggiunge al precedente. I tempi restano invariati.

Le dashboard precedenti restano accessibili. OOE esclude copie di eventi identiche salvo ID; gli eventi originali non sono cancellati. Questo può cambiare risultati precedentemente influenzati dai duplicati.

## Regole
- Mass Yield media: media aritmetica delle rese dei lotti; resa lotto = secco reale/materia prima ×100.
- Taglio medio: media aritmetica di 100 − percentuale puro per lotto. Se il puro storico è stato stimato, anche il taglio lo è; le note fonte sono consultabili nel dettaglio.
- Equivalenti: conservate le convenzioni aziendali esistenti (minimo 15% Comber, minimo 40% puro SD); semilavorato equivalente = puro equivalente/0,40.
- Riferimenti: 126 valori forniti dall'utente, solo pulizia di spazi e artefatti. Nessun accorpamento botanico automatico. 4 codici con associazioni esatte univoche precompilate; le altre associazioni vanno completate nella pagina. Il totale complessivo 11% non è usato per giudicare le singole droghe.
- Trend settimanale: giornate produttive lunedì–venerdì (06:00–06:00), settimana fino al sabato 06:00. Sabati/domeniche con date turno anomale restano nei totali mensili e richiedono verifica; non vengono spostati automaticamente.
- OOE: resta sulla base delle ore registrate, non viene imposto automaticamente un denominatore di 120 h. Il calendario nominale non prova la completezza dei turni. Storico OOE mensile inseribile con ore del denominatore per cumulati ponderati. Prima dell'inizio dei tempi operativi, OOE cumulato = N/D se manca lo storico.
- YTD/LYTD: fino al mese selezionato; se il mese è quello attuale, fino al mese precedente chiuso.
- Rese senza riferimento: nessun giudizio sopra/sotto; grafico aggregato storico basato sui soli lotti associati. Se l'associazione è parziale, confrontare i singoli lotti prima di interpretare le due medie aggregate.

## Dati da verificare
Nel backup di settembre sono presenti otto lotti senza quantità finale/chiusura. Inoltre S26/0201 ha descrizioni diverse tra eventi e consuntivo: verificare prodotto e codice prima di confermare rettifiche. Le righe importate con puro convenzionale al 40% sono stime, non analisi di composizione.

## Verifiche effettuate
Compilazione Python; test su backup reale di chiusura a valle, correzione al ribasso, unicità consuntivo, conservazione tempi/date, media aritmetica yield, individuazione otto lotti pendenti, esclusione copie esatte dal calcolo OOE e integrità dei 126 riferimenti.

Non è stato possibile avviare l'interfaccia Streamlit o effettuare scritture reali sul vostro Supabase in questo ambiente. Le scritture di eventi e consuntivi non sono una transazione unica: in caso di errore la pagina segnala di ripetere l'operazione. Non usare una modifica manuale della data se non corrisponde alla reale fine produzione: selezionare l'evento corretto.

L'interfaccia nuova è bilingue; i valori tecnici restano interni. Eliminata la conversione dei nomi macchina nei dati degli editor. Le traduzioni preesistenti sono conservate, senza una verifica visuale completa di ogni schermata.

## 4.2.1 — Grafica
Nuova dashboard con quattro schede principali per reparto, variazione rispetto allo stesso mese LY, colori distinti Comber/SD, confronti e filtri espandibili, grafici più compatti. Formule invariate. Grafica non verificata nell’interfaccia Streamlit completa.
