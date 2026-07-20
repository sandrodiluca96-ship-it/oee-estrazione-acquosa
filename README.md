# OEE Produzione Lauria – applicazione unificata

Unica applicazione Streamlit Poka-Yoke per:

- Comber – estrazione acquosa;
- EV200 – concentrazione;
- Spray Dryer – essiccazione;
- navigazione laterale separata per Comber, EV200 e Spray Dryer;
- ultimi dati visibili e correggibili dentro ogni macchina;
- gestione completa a eventi: apertura, prosecuzione e chiusura lotto, modifica, duplicazione ed eliminazione;
- copertura obbligatoria delle otto ore e corretta gestione del terzo turno;
- sezioni centralizzate Excel e Storico con filtro per macchina;
- target giornalieri e giorni produttivi modificabili dall'app;
- dashboard Production vs Target per Comber e Spray Dryer;
- dashboard OEE separata con i tre cruscotti;
- indicatori di processo OEE: mass yield media Comber e taglio medio Spray Dryer;
- sezione Production vs Target separata, posizionata dopo le tre macchine;
- modalità ingrandita per visualizzare il report produttivo a tutta pagina;
- logo EVRA nella barra laterale;
- anagrafiche modificabili di codici droga, semilavorati e causali;
- backup e ripristino Excel.
- pianificazione settimanale Comber da file `.xls`/`.xlsx`, con stati Planned, In progress, Completed, Delayed e Unplanned;
- EV200 collegato a uno o più lotti Comber dello stesso prodotto, con inserimento del solo concentrato finale e residuo secco finale.

## Pubblicazione su Streamlit Community Cloud

1. Creare o aprire un repository GitHub.
2. Caricare **il contenuto della cartella**, mantenendo anche `.streamlit/config.toml`.
3. In Streamlit Cloud selezionare il repository, il ramo `main` e `app.py`.
4. Fare clic su Deploy.

## Formule principali

- Comber: se la resa è inferiore al 15%, equivalente = kg droga × 15%; altrimenti equivalente = puro reale.
- Spray Dryer: equivalente 40% = minore tra semilavorato fisico e puro/40%; con tagli inferiori al 60% resta il dato fisico reale.
- Qualità OEE standard temporanea: 95%.

## Target

- Comber: 150 kg/giorno, 220 giorni/anno.
- EV200: 168,75 kg/giorno, 220 giorni/anno.
- Spray Dryer: 321,6 kg semilavorato/giorno e 128,64 kg equivalenti/giorno.

Scaricare regolarmente il backup Excel dalla pagina **Import / Export**.
