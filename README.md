# OEE Produzione Lauria – applicazione unificata

Unica applicazione Streamlit per:

- Comber – estrazione acquosa;
- EV200 – concentrazione;
- Spray Dryer – essiccazione;
- dashboard Production vs Target;
- OEE per macchina;
- anagrafiche modificabili di codici droga, semilavorati e causali;
- backup e ripristino Excel.

## Pubblicazione su Streamlit Community Cloud

1. Creare o aprire un repository GitHub.
2. Caricare **il contenuto della cartella**, mantenendo anche `.streamlit/config.toml`.
3. In Streamlit Cloud selezionare il repository, il ramo `main` e `app.py`.
4. Fare clic su Deploy.

## Formule principali

- Comber: se la resa è inferiore al 15%, equivalente = kg droga × 15%; altrimenti equivalente = puro reale.
- Spray Dryer: puro equivalente = semilavorato × percentuale puro (predefinita 40%).
- Qualità OEE standard temporanea: 95%.

## Target

- Comber: 150 kg/giorno, 220 giorni/anno.
- EV200: 168,75 kg/giorno, 220 giorni/anno.
- Spray Dryer: 321,6 kg semilavorato/giorno e 128,64 kg equivalenti/giorno.

Scaricare regolarmente il backup Excel dalla pagina **Import / Export**.
