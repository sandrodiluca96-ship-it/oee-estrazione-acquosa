"""Traduzione dell'interfaccia senza modificare i valori tecnici salvati."""

from __future__ import annotations

from functools import wraps

LANGUAGE_KEY = "ui_language"

MACHINE_NAMES = {
    "Italiano": {"Comber": "Estrazione acquosa", "Spray Dryer": "Essiccazione Spray Dryer", "EV200": "EV200", "Mescole": "Mescole"},
    "English": {"Comber": "Aqueous Extraction", "Spray Dryer": "Spray Dryer Drying", "EV200": "EV200", "Mescole": "Blending"},
}

IT = {
    "Production vs Target": "Produzione vs obiettivo",
    "Production vs. Target Report": "Report produzione vs obiettivo",
    "Production (kg) by line": "Produzione (kg) per linea",
    "Production": "Produzione",
    "Yesterday": "Ieri",
    "Yesterday Target": "Target di ieri",
    "Achievement": "Raggiungimento",
    "Week to Date": "Settimana a oggi",
    "Week Target": "Target settimanale",
    "Month to Date": "Mese a oggi",
    "Month Target": "Target mensile",
    "Year to Date": "Anno a oggi",
    "Year Target": "Target annuale",
    "Last Year YTD": "Anno precedente a oggi",
    "Previous Month": "Mese precedente",
    "YTD Production": "Produzione da inizio anno",
    "Last year YTD": "Anno precedente a oggi",
    "Report date": "Data report",
    "Daily, Weekly, Monthly, Year-to-Date": "Giornaliero, settimanale, mensile, anno a oggi",
    "Month": "Mese",
    "Week": "Settimana",
    "Active targets": "Target attivi",
    "physical kg/day": "kg fisici/giorno",
    "equivalent kg/day": "kg equivalenti/giorno",
    "working days/year": "giorni lavorativi/anno",
    "Pure extract": "Estratto puro",
    "Pure equivalent 15%": "Puro equivalente 15%",
    "Semi-finished product": "Semilavorato",
    "Pure equivalent 40%": "Puro equivalente 40%",
    "Aqueous extraction": "Estrazione acquosa",
    "Drying": "Essiccazione",
    "Pure equivalent output (15% minimum basis)": "Output puro equivalente (base minima 15%)",
    "Total semi-finished product output": "Output totale di semilavorato",
    "Overall weighted OEE": "OEE complessivo ponderato",
}

EN = {
    "Produzione Lauria": "Lauria Production", "Pianificazione Comber": "Aqueous Extraction Planning",
    "Pianificazione Mescole": "Blending Planning", "Dashboard Mescole": "Blending Dashboard",
    "Dashboard OEE e OOE": "OEE and OOE Dashboard", "Dashboard OEE/OOE": "OEE/OOE Dashboard",
    "Excel per macchina": "Excel by machine", "Storico generale": "General history",
    "Configurazione target": "Target configuration", "Anagrafiche e causali": "Master data and causes",
    "Anagrafiche": "Master data", "Target": "Targets", "Storico": "History", "Versione": "Version",
    "Qualità standard": "Standard Quality", "Pagina intera": "Full screen", "Indicatore": "Indicator",
    "Confronto": "Comparison", "Accesso OEE Produzione Lauria": "Lauria Production OEE Login",
    "Inserisci la password aziendale per accedere all’applicazione.": "Enter the company password to access the application.",
    "Password applicazione non configurata. Inserisci APP_PASSWORD nei Secrets di Streamlit.": "Application password is not configured. Add APP_PASSWORD to Streamlit Secrets.",
    "Password non corretta.": "Incorrect password.", "Accedi": "Log in",
    "Database persistente non configurato. L’app è bloccata per evitare salvataggi temporanei e perdita di dati.": "Persistent database is not configured. The application is blocked to prevent temporary saves and data loss.",
    "Database persistente non raggiungibile. Nessun dato è stato salvato. Verifica i Secrets di Streamlit e riprova.": "Persistent database cannot be reached. No data was saved. Check Streamlit Secrets and try again.",
    "Data turno": "Shift date", "Data di inizio turno": "Shift start date", "Turno": "Shift",
    "Seleziona data e turno per iniziare.": "Select a date and shift to begin.",
    "gli eventi devono coprire 8 ore": "events must cover 8 hours", "Aggiungi evento": "Add event",
    "Modifica / duplica evento": "Edit / duplicate event", "Tipo evento": "Event type",
    "Seleziona evento": "Select an event", "Ora inizio": "Start time", "Ora fine": "End time",
    "Durata evento": "Event duration", "Produzione": "Production", "Lavorazione": "Operation",
    "Nuovo lotto": "New batch", "Riprendi lotto in corso": "Resume active batch",
    "Fase di produzione": "Production stage", "Tipo produzione": "Production type",
    "Apertura lotto": "Open batch", "Prosecuzione lotto": "Continue batch", "Chiusura lotto": "Close batch",
    "Scarico estrattore": "Extractor discharge", "Origine del liquido da concentrare": "Source of liquid to concentrate",
    "Da Comber": "From Aqueous Extraction", "Altro lotto": "Other batch",
    "Lotti Comber da concentrare *": "Aqueous Extraction batches to concentrate *",
    "Puoi unire più lotti soltanto se appartengono allo stesso prodotto.": "You can combine batches only when they belong to the same product.",
    "I lotti selezionati appartengono a prodotti differenti.": "The selected batches belong to different products.",
    "Lotto da concentrare *": "Batch to concentrate *", "Lotto aperto *": "Open batch *",
    "Nessun lotto aperto": "No open batch", "Numero estrazione *": "Extraction number *",
    "Droga caricata nella singola estrazione (kg) *": "Raw material loaded in this extraction (kg) *",
    "Se l'estrazione prosegue dal turno precedente, la quantità viene ereditata e non sarà conteggiata due volte.": "If the extraction continues from the previous shift, the quantity is inherited and is not counted twice.",
    "Estratto liquido ottenuto (kg)": "Liquid extract obtained (kg)",
    "Residuo secco estrazione (%)": "Extraction dry matter (%)",
    "Lascia 0 se lo scarico non è ancora avvenuto.": "Leave 0 if discharge has not yet occurred.",
    "Lascia 0 finché il dato non è disponibile.": "Leave 0 until the value is available.",
    "Concentrato finale (kg) *": "Final concentrate (kg) *", "Residuo secco finale (%) *": "Final dry matter (%) *",
    "Kg molle *": "Liquid concentrate kg *", "Residuo secco molle (%) *": "Liquid concentrate dry matter (%) *",
    "Maltodestrina (kg)": "Maltodextrin (kg)", "Polvere finale ottenuta (kg) *": "Final powder obtained (kg) *",
    "Numero operatori *": "Number of operators *", "Quantità finale ottenuta (kg)": "Final quantity obtained (kg)",
    "Note": "Notes", "Aggiorna evento": "Update event", "Annulla modifica": "Cancel edit",
    "Eventi inseriti nel turno": "Events entered for the shift", "Evento da gestire": "Event to manage",
    "Modifica": "Edit", "Duplica": "Duplicate", "Elimina": "Delete", "Ore coperte": "Hours covered",
    "Salva turno": "Save shift", "Turno completo e pronto per il salvataggio.": "Shift complete and ready to save.",
    "Turno salvato correttamente.": "Shift saved successfully.", "Nessun evento inserito.": "No events entered.",
    "Ultimi eventi salvati": "Latest saved events", "Nessun evento definitivo ancora salvato.": "No final event has been saved yet.",
    "Per correggere un evento vai in Storico → Eventi di turno.": "To correct an event, go to History → Shift events.",
    "Estrazione acquosa per singola estrazione": "Aqueous extraction by individual extraction",
    "Concentrazione dei lotti estratti": "Concentration of extracted batches",
    "Essiccazione semilavorati": "Semi-finished product drying",
    "Produzione e produttività dei lotti di mescola": "Blending batch production and productivity",
    "Estrazione acquosa": "Aqueous Extraction", "Essiccazione Spray Dryer": "Spray Dryer Drying",
    "Concentrazione": "Concentration", "Mescole": "Blending", "Avanzamento pianificazione": "Planning progress",
    "Piano della settimana": "Weekly plan", "Pianificazione settimanale estrazione": "Weekly extraction plan",
    "Importa pianificazione": "Import plan", "Settimana": "Week", "Inizio previsto": "Planned start",
    "Droga": "Raw material", "Lotto attualmente in lavorazione": "Batch currently being processed",
    "Lotto (informativo)": "Batch (informational)", "Piano kg": "Plan kg", "Completati kg": "Completed kg",
    "Residuo kg": "Remaining kg", "Scostamento kg": "Variance kg", "Estrazioni previste": "Planned extractions",
    "Estrazioni completate": "Completed extractions", "Avanzamento kg": "Kg progress",
    "Avanzamento atteso": "Expected progress", "DA INIZIARE": "TO START", "IN LAVORAZIONE": "IN PROGRESS",
    "IN LINEA": "ON TRACK", "SOTTO IL RITMO": "BEHIND PACE", "IN RITARDO": "LATE",
    "COMPLETATO CON EXTRA": "COMPLETED WITH EXTRA", "COMPLETATO": "COMPLETED",
    "Produzioni non attribuite o eccedenti il piano selezionato": "Production not assigned to or exceeding the selected plan",
    "Tutte le produzioni completate risultano attribuite alla pianificazione.": "All completed production is assigned to the plan.",
    "Fuori piano/extra": "Outside plan/extra", "Attribuiti al piano": "Assigned to plan",
    "Residuo della settimana": "Weekly remaining quantity",
    "Lavorazione attuale / ultima registrata": "Current / latest recorded operation",
    "Per ogni macchina è mostrato l'evento produttivo più recente salvato.": "The latest saved production event is shown for each machine.",
    "Nessuna lavorazione registrata": "No operation recorded", "Dettaglio del calcolo": "Calculation details",
    "Ore complessive": "Total hours", "Attività escluse dall'OEE": "Activities excluded from OEE",
    "Fermi inclusi nell'OEE": "Stops included in OEE", "Tempo operativo": "Operating time",
    "Output equivalente": "Equivalent output", "Output teorico nel tempo operativo": "Theoretical output during operating time",
    "Quality usata nel calcolo": "Quality used in the calculation", "Principali perdite": "Main losses",
    "Nessuna perdita registrata nel periodo.": "No loss recorded in the selected period.",
    "Come vengono calcolati OEE e OOE": "How OEE and OOE are calculated", "Dal": "From", "Al": "To",
    "La data finale deve essere successiva alla data iniziale.": "The end date must be after the start date.",
    "qualità standard temporanea": "temporary standard quality", "classificazione causali retroattiva": "retroactive cause classification",
    "Macchina": "Machine", "Tutte": "All", "Cerca lotto, codice o descrizione": "Search batch, code or description",
    "Produzioni chiuse": "Closed production", "Eventi di turno": "Shift events",
    "Nessun evento corrispondente ai filtri selezionati.": "No event matches the selected filters.",
    "Correggi direttamente le celle. ID evento, ID turno e macchina restano protetti.": "Edit cells directly. Event ID, shift ID and machine remain protected.",
    "Confermo le modifiche agli eventi selezionati": "I confirm the changes to the selected events",
    "Salva modifiche eventi": "Save event changes", "Elimina eventi": "Delete events",
    "Backup completo database": "Full database backup", "Backup per macchina": "Backup by machine",
    "Scarica backup completo": "Download full backup", "Seleziona la macchina": "Select machine",
    "Scarica Excel": "Download Excel", "Ricarica Excel": "Upload Excel", "Importa dati": "Import data",
    "Codici prodotto": "Product codes", "Causali": "Causes", "Tipo": "Type",
    "Semilavorato": "Semi-finished product", "Mescola": "Blend", "Codice": "Code", "Descrizione": "Description",
    "% puro standard": "Standard pure %", "Aggiungi / aggiorna codice": "Add / update code",
    "Salva modifiche codici": "Save code changes", "Nuova causale": "New cause", "Categoria": "Category",
    "Fuori dal tempo pianificato OEE": "Outside OEE planned time", "Perdita tecnica": "Technical loss",
    "Nota obbligatoria": "Mandatory note", "Aggiungi causale": "Add cause", "Salva modifiche causali": "Save cause changes",
    "Salva target": "Save targets", "Target aggiornati.": "Targets updated.",
    "Target fisico kg/giorno": "Physical target kg/day", "Target equivalente kg/giorno": "Equivalent target kg/day",
    "Giorni produttivi/anno": "Production days/year", "Attesa prodotto": "Waiting for product",
    "Attesa analisi": "Waiting for analysis", "Cambio lotto": "Batch change", "Inventario": "Inventory",
    "Lavaggio": "Washing", "Pulizia": "Cleaning", "Manutenzione programmata": "Planned maintenance",
    "Manutenzione straordinaria": "Unplanned maintenance", "Guasto": "Breakdown", "Altro": "Other",
    "In corso": "In progress", "Completata": "Completed", "Completato": "Completed", "Stato": "Status",
    "Fase": "Stage", "Ultimo aggiornamento": "Last update", "Dettaglio": "Details", "Operatori": "Operators",
    "Quantità kg": "Quantity kg", "Riferimento piano": "Plan reference",
    "Comber – Pure extract": "Aqueous Extraction – Pure extract",
    "Comber – Pure equivalent 15%": "Aqueous Extraction – Pure equivalent 15%",
    "Spray Dryer – Semi-finished product": "Spray Dryer Drying – Semi-finished product",
    "Spray Dryer – Pure equivalent 40%": "Spray Dryer Drying – Pure equivalent 40%",
    "I cruscotti sono a zero finché non vengono salvate le ore dei turni nelle sezioni macchina.": "Dashboards remain at zero until shift hours are saved in the machine sections.",
    "Carica il piano del reparto e controlla quantità pianificate, prodotte, lotti aperti e avanzamento.": "Upload the department plan and review planned quantities, production, open batches and progress.",
    "Pianificazione reparto Mescole": "Blending department plan",
    "Avanzamento settimanale": "Weekly progress", "Kg pianificati": "Planned kg", "Kg prodotti": "Produced kg",
    "Lotti fuori piano": "Batches outside plan", "Lotti fuori pianificazione": "Batches outside plan",
    "Produttività, avanzamento e utilizzo delle risorse del reparto Mescole. Gli indicatori non sono classificati come OEE.": "Productivity, progress and resource utilization for Blending. These indicators are not classified as OEE.",
    "Target del periodo": "Period target", "Target raggiunto": "Target achievement",
    "Ore": "Hours", "Data": "Date",
    "Lotti completati": "Completed batches", "Lotti in corso": "Open batches", "Ore lavorazione": "Operating hours",
    "Ore-uomo": "Labour hours", "Produttività di processo": "Process productivity",
    "Produttività ore-uomo": "Labour productivity", "Target produttività": "Productivity target",
    "Average mass yield": "Average mass yield", "Average cut": "Average cut", "Mass Yield media": "Average mass yield",
    "Pianificazione importata e resa disponibile nella sezione Comber.": "Plan imported and available in the Aqueous Extraction section.",
    "Piano per droga e quantità: il lotto resta informativo. I residui vengono riportati e recuperati con priorità FIFO.": "Plan by raw material and quantity. The batch is informational. Residual quantities are carried forward and recovered using FIFO priority.",
    "Impossibile leggere la pianificazione": "Unable to read the plan", "Confermo l’importazione del piano Mescole": "I confirm the Blending plan import",
    "Importa pianificazione Mescole": "Import Blending plan", "Piano importato. I codici sono disponibili anche nella sezione Mescole.": "Plan imported. Codes are also available in the Blending section.",
    "Imposta target Mescole": "Set Blending targets", "Target produzione (kg/giorno)": "Production target (kg/day)",
    "Target produttività (kg/ora-uomo)": "Productivity target (kg/labour hour)", "Salva target Mescole": "Save Blending targets",
    "Target Mescole aggiornati.": "Blending targets updated.", "Produzione giornaliera": "Daily production",
    "Produzione per prodotto": "Production by product", "Nessuna mescola completata nel periodo selezionato.": "No blend was completed in the selected period.",
    "Nessun prodotto disponibile nel periodo selezionato.": "No product is available in the selected period.",
    "Nessun lotto completato nel periodo.": "No batch was completed in the selected period.",
    "L'Availability OEE usa come denominatore soltanto produzione e fermi avvenuti mentre era pianificato produrre.": "OEE Availability uses only production time and stops occurring during planned production in the denominator.",
    "L'Availability OOE usa tutte le ore operative registrate, includendo attesa prodotto, lavaggi, cambi lotto e manutenzioni programmate.": "OOE Availability uses all recorded operating hours, including waiting for product, washing, batch changes and planned maintenance.",
    "La Performance confronta l'output equivalente con quello teorico nel solo tempo effettivo di produzione; in questo modo i fermi non vengono penalizzati due volte.": "Performance compares equivalent output with theoretical output during actual production time, so stops are not penalized twice.",
    "Physical and equivalent output for Comber extraction and Spray Dryer production.": "Physical and equivalent output for Aqueous Extraction and Spray Dryer Drying.",
    "Maschera dedicata: i campi visualizzati appartengono esclusivamente alla macchina selezionata.": "Dedicated form: displayed fields belong only to the selected machine.",
    "Consuntivo ore del turno": "Shift hours summary", "Ultimi dati caricati": "Latest loaded data",
    "Puoi correggere direttamente le celle. ID e macchina sono bloccati per evitare di spostare accidentalmente un dato su un’altra linea.": "You can edit cells directly. ID and machine are locked to prevent moving data to another line accidentally.",
    "Lotto *": "Batch *", "Descrizione prodotto/estratto *": "Product/extract description *", "Campo obbligatorio": "Required field",
    "Codice droga *": "Raw material code *", "Droga lavorata (kg)": "Processed raw material (kg)",
    "Liquido estratto (kg)": "Extracted liquid (kg)", "Residuo secco liquido (%)": "Liquid dry matter (%)",
    "Liquido alimentato (kg)": "Fed liquid (kg)", "Residuo secco iniziale (%)": "Initial dry matter (%)",
    "Residuo secco finale (%)": "Final dry matter (%)", "Concentrato ottenuto (kg)": "Concentrate obtained (kg)", "Codice semilavorato *": "Semi-finished product code *",
    "Semilavorato totale ottenuto (kg)": "Total semi-finished product obtained (kg)", "Percentuale puro (%)": "Pure percentage (%)",
    "Salva produzione": "Save production", "Ore di produzione": "Production hours", "Ore di fermo": "Stop hours",
    "Causale principale": "Main cause", "Note turno / causale": "Shift / cause notes", "Salva consuntivo turno": "Save shift summary",
    "Consuntivo salvato.": "Shift summary saved.", "Nessuna produzione caricata per questa macchina.": "No production has been loaded for this machine.",
    "Salva correzioni agli ultimi dati": "Save corrections to latest data", "Dato da eliminare": "Record to delete",
    "Confermo l’eliminazione del dato selezionato": "I confirm deletion of the selected record", "Elimina dato": "Delete record",
    "Correzioni salvate.": "Corrections saved.", "Dato eliminato.": "Record deleted.",
    "I valori salvati aggiornano immediatamente dashboard, percentuali di raggiungimento e performance OEE.": "Saved values immediately update dashboards, achievement percentages and OEE performance.",
    "Eventi da eliminare": "Events to delete", "Confermo l’eliminazione definitiva degli eventi selezionati": "I confirm permanent deletion of the selected events",
    "Elimina eventi selezionati": "Delete selected events", "Codice salvato.": "Code saved.", "Anagrafica aggiornata.": "Master data updated.",
    "Causale salvata.": "Cause saved.", "Confermo la riclassificazione retroattiva delle causali": "I confirm retroactive reclassification of causes",
    "La modifica ricalcolerà retroattivamente gli indicatori. Anteprima sull'intero storico:": "The change will recalculate indicators retroactively. Preview over the full history:",
    "Contiene tutti i reparti, le pianificazioni, i target, le anagrafiche e il registro delle modifiche.": "Includes all departments, plans, targets, master data and the change log.",
    "Il file contiene esclusivamente turni e produzioni della macchina": "The file contains only shifts and production for the machine",
    "Confermo la sostituzione dei soli dati": "I confirm replacement of data only for",
    "Importa storico gestionale": "Import ERP history", "File Carico Produzione": "Production Loading file",
    "File Esplosione commessa": "Work order explosion file", "Lotti Spray Dryer": "Spray Dryer batches",
    "Kg essiccati": "Dried kg", "Lotti Comber": "Aqueous Extraction batches", "Puro Estrazione": "Extraction pure output",
    "Confermo l'aggiornamento dello storico gestionale": "I confirm the ERP history update",
    "Il nuovo prodotto sarà salvato nell’anagrafica del reparto insieme all’evento.": "The new product will be saved in department master data with the event.",
    "Seleziona evento e orari validi.": "Select an event and valid times.", "Lotto, codice e descrizione sono obbligatori.": "Batch, code and description are required.",
    "Per completare l'estrazione devono essere valorizzati sia il liquido sia il residuo secco.": "Both liquid quantity and dry matter are required to complete the extraction.",
    "La quantità chiude automaticamente il lotto. Sarà contabilizzata una sola volta.": "The quantity automatically closes the batch. It will be counted once.",
    "Il lotto sarà disponibile nel turno successivo tra le lavorazioni da riprendere.": "The batch will be available to resume in the next shift.",
    "Per questa causale è obbligatorio inserire una nota.": "A note is required for this cause.",
    "Nuovo codice *": "New code *", "Nuova descrizione *": "New description *",
    "Inserisci il lotto: il salvataggio è bloccato per evitare produzioni senza tracciabilità.": "Enter the batch. Saving is blocked to prevent untraceable production records.",
    "Inserisci la descrizione del prodotto/estratto.": "Enter the product/extract description.",
    "La descrizione associata al codice è visibile nel menu; riportala nel campo descrizione per confermare il prodotto.": "The description linked to the code is shown in the menu. Enter it in the description field to confirm the product.",
    "Seleziona la droga e inserisci i kg lavorati.": "Select the raw material and enter the processed kg.",
    "Inserisci liquido estratto e residuo secco: servono per calcolare il puro.": "Enter extracted liquid and dry matter to calculate pure output.",
    "Inserisci alimentazione, concentrato ottenuto e residuo secco finale.": "Enter feed, concentrate obtained and final dry matter.",
    "Seleziona il semilavorato e inserisci la quantità.": "Select the semi-finished product and enter the quantity.",
    "Inserisci il numero dell'estrazione e la droga caricata nella singola estrazione.": "Enter the extraction number and raw material loaded in the individual extraction.",
    "Scarico registrato come in corso. Potrà essere ripreso nel turno successivo e completato inserendo estratto liquido ottenuto e residuo secco.": "Discharge saved as in progress. It can be resumed in the next shift and completed by entering liquid extract and dry matter.",
    "Inserisci sia la quantità di liquido sia il residuo secco, oppure lascia entrambi a zero per registrare la lavorazione in corso.": "Enter both liquid quantity and dry matter, or leave both at zero to record the operation as in progress.",
    "Puoi chiudere il lotto soltanto dopo aver completato l'estrazione.": "You can close the batch only after completing the extraction.",
    "Inserisci concentrato finale e residuo secco finale.": "Enter final concentrate and final dry matter.",
    "Indica se la mescola è stata eseguita da 1 o 2 operatori.": "Specify whether the blend was produced by 1 or 2 operators.",
}


def get_language(st=None):
    if st is None:
        try:
            import streamlit as st
        except Exception:
            return "Italiano"
    return st.session_state.get(LANGUAGE_KEY, "Italiano")


def machine_name(machine, language=None):
    language = language or get_language()
    return MACHINE_NAMES.get(language, MACHINE_NAMES["Italiano"]).get(machine, machine)


def translate(text, language=None):
    if not isinstance(text, str):
        return text
    language = language or get_language()
    if language == "Italiano":
        if text in IT:
            return IT[text]
        result = text
        replacements = {**MACHINE_NAMES["Italiano"], **IT}
        for source, target in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
            if target not in result:
                result = result.replace(source, target)
        return result
    if text in EN:
        return EN[text]
    result = text
    replacements = {**MACHINE_NAMES["English"], **EN}
    for source, target in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        if target not in result:
            result = result.replace(source, target)
    return result


def language_selector(st):
    labels = {"Italiano": "🇮🇹 Italiano", "English": "🇬🇧 English"}
    current = st.session_state.get(LANGUAGE_KEY, "Italiano")
    st.sidebar.selectbox("Lingua / Language", ["Italiano", "English"], index=0 if current == "Italiano" else 1,
                         format_func=lambda value: labels[value], key=LANGUAGE_KEY)


_PATCHED = False


def _translate_kwargs(kwargs):
    for key in ("help", "placeholder", "label"):
        if isinstance(kwargs.get(key), str):
            kwargs[key] = translate(kwargs[key])
    return kwargs


def _translate_column_config(config):
    if not isinstance(config, dict):
        return config
    translated = {}
    for key, value in config.items():
        if isinstance(value, str):
            translated[key] = translate(value)
        elif isinstance(value, dict):
            copy = value.copy()
            for field in ("label", "help", "title"):
                if isinstance(copy.get(field), str):
                    copy[field] = translate(copy[field])
            translated[key] = copy
        else:
            translated[key] = value
    return translated


def configure_streamlit_translation(st):
    global _PATCHED
    if _PATCHED:
        return
    from streamlit.delta_generator import DeltaGenerator

    text_methods = ["title", "header", "subheader", "caption", "info", "success", "warning", "error", "markdown",
                    "write", "text", "button", "form_submit_button", "download_button", "file_uploader", "text_input",
                    "text_area", "number_input", "date_input", "checkbox", "toggle", "expander", "metric"]
    for method_name in text_methods:
        original = getattr(DeltaGenerator, method_name, None)
        if original is None:
            continue
        @wraps(original)
        def wrapped(self, *args, __original=original, **kwargs):
            args = list(args)
            if args and isinstance(args[0], str):
                args[0] = translate(args[0])
            return __original(self, *args, **_translate_kwargs(dict(kwargs)))
        setattr(DeltaGenerator, method_name, wrapped)

    for method_name in ("selectbox", "radio", "multiselect", "select_slider"):
        original = getattr(DeltaGenerator, method_name, None)
        if original is None:
            continue
        @wraps(original)
        def wrapped_choice(self, *args, __original=original, **kwargs):
            args = list(args)
            if args and isinstance(args[0], str):
                args[0] = translate(args[0])
            old_format = kwargs.get("format_func", str)
            kwargs["format_func"] = lambda value: translate(old_format(value))
            return __original(self, *args, **_translate_kwargs(dict(kwargs)))
        setattr(DeltaGenerator, method_name, wrapped_choice)

    original_tabs = getattr(DeltaGenerator, "tabs", None)
    if original_tabs:
        @wraps(original_tabs)
        def wrapped_tabs(self, tabs, *args, **kwargs):
            return original_tabs(self, [translate(value) for value in tabs], *args, **kwargs)
        DeltaGenerator.tabs = wrapped_tabs

    for method_name in ("dataframe", "data_editor"):
        original = getattr(DeltaGenerator, method_name, None)
        if original is None:
            continue
        @wraps(original)
        def wrapped_table(self, data=None, *args, __original=original, __method=method_name, **kwargs):
            reverse_names = {}
            try:
                config = dict(kwargs.get("column_config") or {})
                for column in list(data.columns):
                    config.setdefault(column, translate(str(column)))
                kwargs["column_config"] = _translate_column_config(config)
                if __method == "dataframe":
                    data = data.copy()
                    for column in data.select_dtypes(include=["object", "string"]).columns:
                        data[column] = data[column].map(lambda value: translate(value) if isinstance(value, str) else value)
                elif __method == "data_editor" and "macchina" in data.columns:
                    language = get_language(st)
                    reverse_names = {display: internal for internal, display in MACHINE_NAMES[language].items()}
                    data = data.copy()
                    data["macchina"] = data["macchina"].map(lambda value: machine_name(value, language))
            except Exception:
                pass
            result = __original(self, data, *args, **kwargs)
            if __method == "data_editor" and "macchina" in getattr(result, "columns", []):
                result = result.copy()
                result["macchina"] = result["macchina"].map(lambda value: reverse_names.get(value, value))
            return result
        setattr(DeltaGenerator, method_name, wrapped_table)
    _PATCHED = True
