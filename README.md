# OEE Estrazione Acquosa - Comber ed EV200

## Avvio

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

La cartella `data` viene creata automaticamente al primo avvio.

## Asset

- Comber: estrazione acquosa
- EV200: concentrazione

Ogni asset dispone di una timeline indipendente di 8 ore per turno. Un asset non
pianificato non contribuisce al denominatore OEE.

## Assunzioni iniziali modificabili

- Comber: 25 kg droga/h
- EV200: 200 kg acqua evaporata/h
- Qualita standard: 95%

Le capacita nominali devono essere validate e possono essere modificate nella
pagina Configurazione.
