from datetime import date, datetime
import unittest

import pandas as pd

from oee_analytics import calculate_effectiveness, comber_planning_view, open_productions


def _event(event_id, day, kind, hours, description="", lot="", extraction=0, kg=0, completed="", cause_id=""):
    return {
        "id_evento":event_id,"id_turno":f"{day}-1-Comber","data_turno":day,"turno":"1","macchina":"Comber",
        "tipo_evento":kind,"cause_id":cause_id,"ora_inizio":"06:00","ora_fine":"08:00","durata_h":hours,
        "lotto":lot,"numero_estrazione":extraction,"codice":"MDR","descrizione":description,"kg_droga":kg,
        "stato_estrazione":completed,
    }


class AnalyticsTests(unittest.TestCase):
 def test_open_productions_are_carried_until_closure(self):
    rows=[
        {**_event("1","2026-09-07","Produzione",2,"TIMO","C-01",1,100,"Completata"),"tipo_produzione":"Apertura lotto","stato_lotto":"In corso","fase_lavorazione":"Scarico estrattore completato"},
        {**_event("2","2026-09-08","Produzione",2,"TIMO","C-01",2,80,"In corso"),"tipo_produzione":"Prosecuzione lotto","stato_lotto":"In corso","fase_lavorazione":"Estrazione in corso"},
        {**_event("3","2026-09-07","Produzione",2,"MELISSA","E-01"),"macchina":"EV200","tipo_produzione":"Apertura lotto","stato_lotto":"In corso","lotti_comber":"C-77"},
        {**_event("4","2026-09-08","Produzione",2,"MELISSA","E-01"),"macchina":"EV200","tipo_produzione":"Chiusura lotto","stato_lotto":"Completato"},
        {**_event("5","2026-09-07","",2,"TIMO","S-01"),"macchina":" spray dryer ","tipo_produzione":"Prosecuzione lotto","stato_lotto":"In corso"},
    ]
    result=open_productions(pd.DataFrame(rows),datetime(2026,9,8,12))
    self.assertEqual(set(result["Lotto"]),{"C-01","S-01"})
    comber=result[result["Lotto"]=="C-01"].iloc[0]
    self.assertEqual(comber["Stato"],"🟢 IN LAVORAZIONE")
    self.assertIn("Estrazione 2",comber["Dettaglio"])
    spray=result[result["Lotto"]=="S-01"].iloc[0]
    self.assertEqual(spray["Stato"],"🟢 IN LAVORAZIONE")

 def test_oee_excludes_waiting_product_but_ooe_includes_it(self):
    events = pd.DataFrame([
        _event("1","2026-09-07","Produzione",4,"TIMO","L1",1,100,"Completata"),
        _event("2","2026-09-07","Guasto",1,cause_id="C-GUASTO"),
        _event("3","2026-09-07","Attesa prodotto",3,cause_id="C-ATTESA"),
    ])
    causes=pd.DataFrame([
        {"cause_id":"C-GUASTO","causale":"Guasto","esclusa_pianificato":"NO"},
        {"cause_id":"C-ATTESA","causale":"Attesa prodotto","esclusa_pianificato":"SI"},
    ])
    productions=pd.DataFrame([{"id_turno":"2026-09-07-1-Comber","macchina":"Comber","kg_puro_equivalente":20}])
    result=calculate_effectiveness(events,productions,causes,{"Comber":120,"EV200":0,"Spray Dryer":0},1.0,date(2026,9,7),date(2026,9,7))[0]
    self.assertEqual(result["Availability OEE"],4/5)
    self.assertEqual(result["Availability OOE"],4/8)
    self.assertEqual(result["Performance"],1.0)
    self.assertEqual(result["OEE"],0.8)
    self.assertEqual(result["OOE"],0.5)


 def test_comber_week_is_independent_and_does_not_carry_backlog(self):
    plans=pd.DataFrame([
        {"piano_id":"P36","settimana":"36","data_inizio":"2026-08-31","data_fine":"2026-09-05","ora_inizio":"06:00","ora_fine":"22:00","prodotto":"TIMO","lotto_droga":"","estrazioni_pianificate":2,"kg_per_estrazione":100,"kg_pianificati":200,"impianto":"Comber","caricato_il":""},
        {"piano_id":"P37","settimana":"37","data_inizio":"2026-09-07","data_fine":"2026-09-12","ora_inizio":"06:00","ora_fine":"22:00","prodotto":"TIMO","lotto_droga":"","estrazioni_pianificate":2,"kg_per_estrazione":100,"kg_pianificati":200,"impianto":"Comber","caricato_il":""},
    ])
    events=pd.DataFrame([
        _event("1","2026-09-04","Produzione",2,"Timo foglie","L1",1,100,"Completata"),
        _event("2","2026-09-07","Produzione",2,"Timo foglie","L2",1,150,"Completata"),
    ])
    current=plans[plans["settimana"]=="37"]
    progress,backlog,unplanned=comber_planning_view(plans,events,current,datetime(2026,9,8,12))
    self.assertTrue(backlog.empty)
    self.assertEqual(progress.iloc[0]["kg_effettivi"],150)
    self.assertEqual(progress.iloc[0]["kg_residui"],50)
    self.assertTrue(unplanned.empty)

 def test_comber_matches_same_week_even_before_planned_product_day(self):
    plans=pd.DataFrame([{
        "piano_id":"P37-F","settimana":"37","data_inizio":"2026-09-08","data_fine":"2026-09-12",
        "ora_inizio":"06:00","ora_fine":"22:00","prodotto":"FINOCCHIO","lotto_droga":"26E0240D0409",
        "estrazioni_pianificate":10,"kg_per_estrazione":199,"kg_pianificati":1990,"impianto":"Comber","caricato_il":"",
    }])
    events=pd.DataFrame([
        {**_event("F1","2026-09-07","Produzione",3,"Finocchio","M26/0137",1,199,"Completata"),
         "tipo_produzione":"Apertura lotto","stato_lotto":"In corso"},
    ])
    progress,backlog,unplanned=comber_planning_view(plans,events,plans,datetime(2026,9,9,12))
    self.assertEqual(progress.iloc[0]["kg_effettivi"],199)
    self.assertEqual(progress.iloc[0]["stato"],"IN LAVORAZIONE")
    self.assertEqual(progress.iloc[0]["lotto_in_lavorazione"],"M26/0137")
    self.assertTrue(unplanned.empty)


if __name__ == "__main__":
    unittest.main()
