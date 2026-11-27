import unittest
from judgesim import ca9
from judgesim.engine import require, Invalid
class CA9Tests(unittest.TestCase):
    def setUp(self):
        self.state={"people":{j:{"id":j,"role":"judge","active":True,"court_id":"CA9","judicial_status":"active_circuit","seniority_rank":i+1} for i,j in enumerate("ABC")}}
        self.case={"assigned_judges":list("ABC"),"presiding_judge_id":"A","conflict_review_completed":True,"jurisdiction_basis":"reviewed 28 USC 1291","panel_kind":"ordinary_merits","hearings":{"H":{"status":"completed"}}}
    def test_panel(self):
        ca9.check_panel(self.state,self.case,require)
        self.case["presiding_judge_id"]="B"
        with self.assertRaises(Invalid): ca9.check_panel(self.state,self.case,require)
    def test_duplicate_judges(self):
        self.case["assigned_judges"]=list("AAB")
        with self.assertRaises(Invalid): ca9.check_panel(self.state,self.case,require)
    def test_visiting_panel(self):
        self.state["people"]["C"].update(court_id="OTHER",judicial_status="visiting")
        ca9.check_panel(self.state,self.case,require)
        self.state["people"]["B"].update(court_id="OTHER",judicial_status="visiting")
        with self.assertRaises(Invalid): ca9.check_panel(self.state,self.case,require)
    def test_no_argument(self):
        p={"briefs_and_record_reviewed":True,"no_argument_votes":dict.fromkeys("ABC",True),"no_argument_reason":"argument_not_helpful"}
        ca9.no_argument(self.case,p,require)
        p["no_argument_votes"]["C"]=False
        with self.assertRaises(Invalid): ca9.no_argument(self.case,p,require)
    def test_conference(self):
        p={"votes":{"A":"affirm","B":"affirm","C":"reverse"},"majority_disposition":"affirm","author_id":"A"}
        self.assertEqual(ca9.conference(self.case,p,require)["author_id"],"A")
        p["author_id"]="C"
        with self.assertRaises(Invalid): ca9.conference(self.case,p,require)
    def test_publication_majority(self):
        o={"author_id":"A","parts":["I","II"],"positions":{j:{"disposition":"affirm","stance":"join","joined_parts":["I","II"]} for j in "ABC"}}
        p={"opinion_kind":"majority","publication_form":"OPINION","publication_reason":"federal_rule","certified":True,"disposition":"affirm"}
        ca9.issuance(self.case,o,p,require)
        o["positions"]["B"]["joined_parts"]=["I"]
        o["positions"]["C"]["stance"]="concur"
        with self.assertRaises(Invalid): ca9.issuance(self.case,o,p,require)
    def test_missing_certification(self):
        with self.assertRaises(Invalid): ca9.issuance(self.case,{},{"opinion_kind":"order","publication_form":"ORDER"},require)
