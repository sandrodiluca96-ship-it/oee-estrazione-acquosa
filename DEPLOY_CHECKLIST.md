# Checklist di rilascio

1. Verificare di avere i backup di `app_records`, `app_audit_log` e il backup Excel dell'app.
2. Conservare una copia o un branch della versione 3.11.0.
3. Caricare tutti i file di questo pacchetto nel repository, inclusi `oee_analytics.py`, `assets/` e `.streamlit/config.toml`.
4. Non modificare `APP_PASSWORD`, `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` nei Secrets.
5. Verificare che il file di avvio configurato su Streamlit sia `app.py`.
6. Avviare l'app in una finestra senza inserimenti operatori in corso.
7. Aprire **Anagrafiche e causali** e controllare la classificazione migrata.
8. Confrontare un periodo noto nelle viste OEE, OOE e Confronto.
9. Importare un piano Comber di prova e verificare kg, backlog e fuori piano.
10. Riaprire l'utilizzo agli operatori soltanto dopo i controlli.

In caso di anomalia, ripubblicare la versione precedente. Il pacchetto non cancella produzioni o eventi storici durante il normale avvio.
