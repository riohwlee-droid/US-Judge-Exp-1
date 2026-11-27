import unittest
from judgesim.engine import apply_batch, initial_state, Invalid
from judgesim.ca9_lifecycle import date_due
from datetime import date

PROFILES={"CA9":{"id":"CA9","status":"training_only","matter_types":["civil_appeal","criminal_appeal"],"hearing_kinds":["oral_argument","consideration_on_briefs"]}}
class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.s=initial_state();self.seq=0
        self.run_ev("campaign.configure",court_id="CA9",user_confirmed=True,player={"id":"J01"},game_time="2026-11-02T10:00:00-08:00",legal_cutoff="2026-11-02")
        for i in range(1,14):
            self.run_ev("person.register",person={"id":f"J{i:02}","role":"judge","fictional":True,"active":True,"court_id":"CA9","judicial_status":"active_circuit","seniority_rank":i,"chief_judge":i==1})
        self.run_ev("case.register",case={"id":"C","court_id":"CA9","fictional":True,"matter_type":"civil_appeal","title":"Test only","assigned_judges":[],"record_status":"complete","initial_document_ids":["REC"],"panel_kind":"ordinary_merits","origin_district":"NDCA","calendar_location":"SF","jurisdiction_basis":"28 USC 1291 test","conflict_review_completed":True})
        self.doc("REC")
        self.assign()
    @property
    def c(self):return self.s["cases"]["C"]
    def run_ev(self,k,**p):
        self.seq+=1
        self.s=apply_batch(self.s,[{"id":f"E{self.seq}","type":k,"payload":p}],PROFILES,allow_training=True)
    def ca(self,k,**p):self.run_ev("ca9."+k,case_id="C",legal_review_completed=True,rule_basis="test reviewed",**p)
    def doc(self,id):
        self.run_ev("document.register",document={"id":id,"case_id":"C","path":"records/test/"+id+".md","sha256":"a"*64,"pages":1,"access":"judge","status":"filed"})
    def assign(self):
        self.ca("assign",seed="testseed-000",calendar_review_completed=True,calendar_month="2026-11",case_weight=2,priority_review="ordinary FIFO reviewed",slots=[{"id":"S","location":"SF","month":"2026-11","judges":["J01","J02","J03"],"remaining_weight":3}])
    def submit(self):
        h="H"+str(self.c["panel_epoch"])
        self.run_ev("hearing.start",case_id="C",hearing_id=h,kind="oral_argument")
        self.run_ev("hearing.complete",case_id="C",hearing_id=h)
    def issue(self,tag="1",gov=False):
        panel=self.c["assigned_judges"];author=panel[0]; assigner=min(panel)
        self.submit()
        self.run_ev("conference.record",case_id="C",votes=dict.fromkeys(panel,"affirm"),majority_disposition="affirm",author_id=author,assigning_judge_id=assigner)
        self.run_ev("draft.start",case_id="C",author_id=author)
        self.doc("O-D"+tag)
        self.run_ev("opinion.circulate",opinion={"id":"O"+tag,"case_id":"C","document_id":"O-D"+tag,"author_id":author,"parts":["I"]})
        for j in panel:self.run_ev("opinion.position",opinion_id="O"+tag,judge_id=j,disposition="affirm",stance="join",joined_parts=["I"])
        self.run_ev("opinion.issue",opinion_id="O"+tag,opinion_kind="majority",rule_basis="test",legal_review_completed=True,publication_form="OPINION",publication_reason="federal_rule",certified=True,disposition="affirm")
        self.run_ev("precedent.register",precedent={"id":"PR"+tag,"opinion_id":"O"+tag,"origin":"simulation","source_type":"issued_simulated_opinion","issued_at":self.s["campaign"]["game_time"],"authority_status":"binding","scope":"CA9","rule_basis":"test"})
        self.doc("JUD"+tag)
        self.ca("judgment",controlling_opinion_id="O"+tag,judgment_document_id="JUD"+tag,calendar_verified=True,federal_party_civil=gov,holidays=["2026-11-26"])
    def days(self,n):self.run_ev("time.advance",minutes=n*1440,user_authorized=True)
    def test_assignment_and_recusal(self):
        self.assertEqual(self.c["assigned_judges"],["J01","J02","J03"])
        with self.assertRaises(Invalid):self.ca("panel_change",outgoing_judge_id="J03",reason="recusal",mode="quorum",remaining_votes={"J01":"affirm","J02":"affirm"})
        self.ca("panel_change",outgoing_judge_id="J03",reason="recusal",mode="same_location_switch",same_location_review=True,incoming_judge_id="J04",parties_notified=True)
        self.assertEqual(self.c["assigned_judges"],["J01","J02","J04"])
        self.assertEqual(len(self.c["panel_history"]),2)
    def test_quorum(self):
        self.submit()
        with self.assertRaises(Invalid):self.ca("panel_change",outgoing_judge_id="J03",reason="death",mode="quorum",remaining_votes={"J01":"affirm","J02":"reverse"})
        self.ca("panel_change",outgoing_judge_id="J03",reason="death",mode="quorum",remaining_votes={"J01":"affirm","J02":"affirm"})
        self.assertEqual(self.c["panel_kind"],"quorum")
        self.run_ev("conference.record",case_id="C",votes={"J01":"affirm","J02":"affirm"},majority_disposition="affirm",author_id="J01")
    def test_no_petition_mandate(self):
        self.issue();self.assertEqual(self.c["review"]["petition_due"],"2026-11-16")
        self.doc("M")
        with self.assertRaises(Invalid):self.ca("mandate",mandate_document_id="M",certified_judgment_and_costs_reviewed=True)
        self.days(21)
        self.ca("en_banc_clear",all_notice_call_periods_checked=True,same_day_call_window_closed=True)
        self.ca("mandate",mandate_document_id="M",certified_judgment_and_costs_reviewed=True)
        self.assertEqual(self.c["status"],"closed")
        self.doc("RECALL");self.ca("mandate_recall",order_document_id="RECALL",extraordinary_circumstances="test",authority_reviewed=True)
        self.assertEqual(self.c["status"],"pending")
    def test_panel_rehearing_grant(self):
        self.issue();self.doc("P");self.ca("rehearing_file",petition_document_id="P",kind="panel")
        self.doc("ORD");self.doc("RESP")
        with self.assertRaises(Invalid):self.ca("response_file",petition_document_id="P",response_document_id="RESP")
        self.ca("response_request",petition_document_id="P",order_document_id="ORD")
        self.ca("response_file",petition_document_id="P",response_document_id="RESP")
        self.ca("panel_rehearing",petition_document_id="P",votes={"J01":True,"J02":True,"J03":False},order_document_id="ORD",withdraw_prior_judgment=True)
        self.assertEqual(self.s["opinions"]["O1"]["status"],"vacated")
        self.assertEqual(self.s["precedents"]["PR1"]["authority_status"],"nonprecedential")
        self.issue("2");self.assertEqual(self.c["judgment"]["opinion_id"],"O2")
    def test_en_banc_grant_and_second_judgment(self):
        self.issue();self.doc("P");self.ca("rehearing_file",petition_document_id="P",kind="en_banc")
        self.ca("en_banc_call",judge_id="J04",ground="exceptional_importance",call_timing_reviewed=True)
        self.ca("en_banc_open",party_opportunity_completed=True,memoranda_completed=True,roster_complete=True)
        for i in range(1,8):self.ca("en_banc_vote",judge_id=f"J{i:02}",vote=True)
        self.doc("ORD")
        with self.assertRaises(Invalid):self.ca("en_banc_tally",order_document_id="ORD")
        self.days(8);self.ca("en_banc_tally",order_document_id="ORD")
        self.assertEqual(self.c["phase"],"en_banc_pending")
        self.assertEqual(self.s["opinions"]["O1"]["status"],"vacated")
        self.ca("en_banc_draw",seed="enbanc-lottery-test",clerk_draw_witnessed=True)
        self.assertEqual(len(self.c["assigned_judges"]),11)
        self.assertIn("J01",self.c["assigned_judges"])
        self.issue("2")
        self.assertEqual(self.c["judgment"]["opinion_id"],"O2")
        self.assertEqual(len(self.s["opinions"]["O1"]["panel_judges"]),3)
    def test_en_banc_missing_votes_are_no_and_stay(self):
        self.issue(gov=True);self.assertEqual(self.c["review"]["petition_due"],"2026-12-17")
        self.ca("en_banc_call",judge_id="J04",ground="circuit_conflict",call_timing_reviewed=True)
        self.ca("en_banc_open",party_opportunity_completed=True,memoranda_completed=True,roster_complete=True)
        self.ca("en_banc_vote",judge_id="J04",vote=True)
        self.days(8);self.doc("ORD");self.ca("en_banc_tally",order_document_id="ORD")
        self.assertEqual(self.c["review"]["en_banc"]["no"],12)
        self.doc("MOTION");self.ca("stay_file",motion_document_id="MOTION")
        self.ca("stay_decide",grant=True,order_document_id="ORD",substantial_question=True,good_cause=True,until="2026-12-28")
        self.days(50);self.doc("M")
        with self.assertRaises(Invalid):self.ca("mandate",mandate_document_id="M",certified_judgment_and_costs_reviewed=True)
        self.ca("stay_end",reason="expired",no_extension_or_cert_notice=True)
        self.ca("mandate",mandate_document_id="M",certified_judgment_and_costs_reviewed=True)
        self.assertEqual(self.c["status"],"closed")
    def test_holiday(self):
        self.assertEqual(date_due(date(2026,11,19),7,["2026-11-26"]),date(2026,11,27))
