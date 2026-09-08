# Versione 4.0.1

## Produzioni in corso

- Nella dashboard OEE/OOE sono visibili i lotti aperti di Comber, EV200 e Spray Dryer.
- Ogni riga mostra lotto, codice, descrizione, fase, turno, ultimo aggiornamento e dettaglio macchina.
- Un lotto rimane visibile tra turni differenti e scompare solo dopo la chiusura salvata.
- Il semaforo distingue lavorazioni aggiornate oggi, da riprendere entro 48 ore e da verificare oltre 48 ore.
- Nessuna nuova tabella o colonna Supabase richiesta.

# Versione 4.0.0

## Pianificazione Comber

- Il lotto non è più usato per riconciliare piano e produzione.
- Le produzioni vengono associate per nome normalizzato della droga.
- La campagna si chiude sui kg pianificati; le estrazioni restano informative.
- I residui passano alle settimane successive e sono recuperati con logica FIFO.
- La pagina separa backlog, piano corrente, residui ed extra/fuori piano.
- L'importazione controlla la coerenza tra settimana dichiarata e date.
- La reimportazione sostituisce in modo esplicito il piano dello stesso anno/settimana.

## OEE e OOE

- Nuove viste OEE, OOE e Confronto per Comber, EV200 e Spray Dryer.
- Filtro per intervallo temporale.
- Performance calcolata sul tempo operativo per non penalizzare due volte i fermi.
- Qualità standard 95% mostrata esplicitamente.
- Dettaglio delle ore e Pareto delle perdite.
- Spiegazione visuale integrata.

## Causali

- Aggiunto un `cause_id` stabile ai nuovi eventi.
- Migrazione compatibile delle causali e degli eventi storici.
- Attesa prodotto e altre attività fuori dal piano produttivo non penalizzano l'OEE, ma penalizzano l'OOE.
- Riclassificazione retroattiva con anteprima dell'impatto.
- Nota obbligatoria configurabile.

## Compatibilità

- Nessuna nuova tabella Supabase richiesta.
- I nuovi campi sono memorizzati nei payload JSON già presenti in `app_records`.
- I record storici senza i nuovi campi restano leggibili.
