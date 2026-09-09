# Versione 4.0.7

## Lotto live e pianificazione Comber

- La pianificazione indica “In lavorazione” soltanto per il prodotto dell'ultima lavorazione Comber registrata.
- I vecchi lotti rimasti formalmente aperti non alterano più lo stato del piano settimanale.
- Durante la prosecuzione viene proposto per primo il lotto lavorato più di recente, compresi i lotti aperti nello stesso turno non ancora salvato.
- Le produzioni senza un piano settimanale compatibile continuano a essere riportate correttamente tra i fuori piano.

# Versione 4.0.6

## Lavorazione live

- Sotto OEE/OOE viene mostrata una sola lavorazione per macchina: l'ultima registrata in ordine cronologico.
- Lo stato distingue il lotto ancora in corso dall'ultima lavorazione già chiusa.
- I vecchi lotti privi di chiusura non affollano più la dashboard.

# Versione 4.0.5

## Aggancio settimanale Comber e Spray Dryer

- Le estrazioni Comber sono associate al piano tramite settimana e nome droga, anche se precedono il giorno specifico previsto per il prodotto.
- La data di inizio prevista resta informativa e non blocca più l'attribuzione all'interno della stessa settimana.
- La pianificazione mostra il lotto Comber attualmente in lavorazione e lo stato dedicato.
- La ricostruzione Spray Dryer riconosce prosecuzioni anche con differenze di maiuscole, spazi o vecchi eventi con fase valorizzata.

# Versione 4.0.4

## Continuità delle lavorazioni tra turni

- I lotti Comber e Spray Dryer restano visibili tra le produzioni in corso anche nei giorni e turni successivi.
- La prosecuzione non dipende più dalla data dell'ultimo aggiornamento.
- Il lotto scompare dalla dashboard esclusivamente dopo il salvataggio della chiusura lotto.

# Versione 4.0.3

## Indicatore Comber

- Nel cruscotto Comber la Quality è sostituita visivamente dalla Mass Yield media del periodo selezionato.
- La Quality standard del 95% continua a essere applicata alla formula OEE/OOE ed è visibile nel dettaglio del calcolo.

# Versione 4.0.2

## Semplificazione dashboard e pianificazione

- Eliminato il riporto del backlog nella Pianificazione Comber: ogni settimana è indipendente.
- EV200 resta operativo nell'app, ma non compare più nella Dashboard OEE/OOE.
- La sezione sotto OEE/OOE mostra solo le produzioni aggiornate oggi e quindi realmente indicate come in lavorazione.
- Rimossi dalla vista i lotti “Da riprendere” e “Da verificare”.
- Rimossi i riquadri informativi introduttivi azzurri dalla Dashboard OEE/OOE.

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
