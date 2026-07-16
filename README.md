# OEE Estrazione Acquosa - Comber ed EV200 - Versione 1.3.0

## Avvio

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

La cartella `data` viene creata automaticamente al primo avvio.

## Asset

- Comber: estrazione acquosa
- EV200: concentrazione

Le due macchine hanno schermate operative separate: `Turno Comber` e `Turno EV200`.
Ogni turno inserito dispone di una timeline indipendente di 8 ore. Se una macchina
non è prevista in funzione, il relativo turno non deve essere compilato.

L'interfaccia utilizza un tema chiaro predefinito, ottimizzato per inserimento dati,
tablet e monitor industriali.

La pagina `Production vs Target` confronta Yesterday, Month-to-Date, Year-to-Date
e Last Year-to-Date su droga fisica, puro ottenuto, resa media aritmetica ed
equivalente standard al 15% di mass yield.

## Assunzioni iniziali modificabili

- Comber: 25 kg droga/h
- EV200: 200 kg acqua evaporata/h
- Qualita standard: 95%

Le capacita nominali devono essere validate e possono essere modificate nella
pagina Configurazione.
