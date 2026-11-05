# EVRA 4.3.0 – Guanzate Blending

Sostituire app.py e persistence.py; aggiungere guanzate_blending.py e data/guanzate_blending.csv. Conservare tutti gli altri CSV, asset e Secrets esistenti. Gli altri moduli inclusi sono invariati. Non sostituire l’intera cartella data.

La voce Guanzate – Blending mostra ottobre dal CSV allegato e consente importazione del foglio Dati OEE. Il caricamento è una anteprima; Salva rende persistenti i dati. Verificare che app_records consenta il dataset guanzate_blending. Nessuna modifica al database online è stata eseguita.

Ogni importazione sostituisce i mesi e le macchine presenti nel file: usare file completi per quei mesi. Reimportazioni identiche mantengono gli stessi ID. In caso di errore parziale ripetere il salvataggio: scrittura e cancellazione non sono transazionali.

OOE secondo la convenzione Guanzate: Q = buoni/totale, A = netto/durata, P = ideale/netto; OOE = Q*A*P. Rapporti delle somme. Nessun limite al 100% e nessun fattore qualità convenzionale di Lauria. La denominazione OEE del sorgente viene trattata come OOE secondo l’indicazione aziendale. Unità quantità non assunta come kg. Ore e intervalli condivisi restano quelli del sorgente, con avviso. Il calendario non viene ricostruito.

Verificati sintassi, 296 righe, esclusione totale, OOE ottobre 54,7281%, ID univoci/stabili alla reimportazione e periodo vuoto N/D. Interfaccia e Supabase non verificati in esecuzione. La schermata Guanzate aggiunta è in italiano.
