"""No official saves mutated: actual sealed first release plus isolated lifecycle tests."""
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from judgesim.supply import *
from judgesim.engine import initial_state, apply_batch, digest, Invalid
from judgesim.storage import profiles
ROOT=Path(__file__).resolve().parents[1]
POL=read_json(ROOT/"supply/policy.json")
ROSTER=read_json(ROOT/"courts/ca9/roster-v1.json")
RELEASE=POL["legacy_release"]
def ev(i,k,**p):return {"id":i,"type":k,"payload":p}
class QueueTests(unittest.TestCase):
    def setUp(self):
        self.t=TemporaryDirectory();self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name);self.state=initial_state();self.ledger=new_ledger()
        write_json(self.root/"supply/policy.json",POL)
    def test_replenishment_idempotent_and_capacity(self):
        policy_check(POL)
        replenish(self.ledger,self.state,POL,0)
        self.assertEqual(len(self.ledger["jobs"]),3)
        before=deepcopy(self.ledger);replenish(self.ledger,self.state,POL,0)
        self.assertEqual(before,self.ledger)
        with self.assertRaisesRegex(ValueError,"capacity"):process_command(self.root,self.ledger,POL,self.state,{"schema_version":1,"action":"request"},0)
    def test_real_first_release_inventory(self):
        import_seals(ROOT,self.ledger,POL,0);replenish(self.ledger,self.state,POL,0)
        self.assertEqual(inventory(self.ledger,self.state,POL)["ready"],1)
        self.assertEqual(inventory(self.ledger,self.state,POL)["queued"],2)
        self.assertEqual(self.ledger["jobs"]["CA9-26-001"]["release_digest"],canonical(check_release(ROOT,RELEASE)))
        before=deepcopy(self.ledger);import_seals(ROOT,self.ledger,POL,0);replenish(self.ledger,self.state,POL,0)
        self.assertEqual(before,self.ledger)
    def test_stage_failure_and_retry(self):
        j=make_job(self.ledger,POL,POL["provisional_cutoff"],0)
        def command(action,expected,**p):
            return process_command(self.root,self.ledger,POL,self.state,{"schema_version":1,"action":action,"job_id":j["id"],"expected_status":expected,**p},0)
        command("start","queued")
        with self.assertRaisesRegex(ValueError,"unexpected validation stage"):command("advance","working",stage="briefs")
        command("advance","working",stage="world")
        self.assertEqual(j["status"],"rework")
        self.assertEqual(j["stage_index"],-1)
        self.assertEqual(j["history"][-1]["action"],"validation_failed")
        command("retry","rework")
        self.assertEqual(j["attempt"],2)
        write_json(self.root/j["blueprint_path"],{"case_id":j["id"],"version":"v1","track":j["track"],"origin_district":j["origin_district"],"legal_cutoff":j["legal_cutoff"]})
        with patch("judgesim.supply.compile_package",return_value={"stage":"world"}):
            command("advance","working",stage="world")
        self.assertEqual(j["stage_index"],0)
        self.assertEqual(j["status"],"working")
        with self.assertRaisesRegex(ValueError,"wrong stage"):command("seal","working",stage="review")
    def test_bad_seal_not_published(self):
        j=make_job(self.ledger,POL,POL["provisional_cutoff"],0)
        j.update(status="reviewed",stage_index=5)
        write_json(self.root/j["blueprint_path"],{"case_id":j["id"],"version":"v1","track":j["track"],"origin_district":j["origin_district"],"legal_cutoff":j["legal_cutoff"]})
        r={"case_id":j["id"],"version":"v1","legal_cutoff":j["legal_cutoff"],"blueprint_path":j["blueprint_path"],"record_as_of":"2026-11-27T10:00:00-08:00"}
        with patch("judgesim.supply.compile_package",return_value=r),patch("judgesim.supply.check_release",side_effect=ValueError("seal mismatch")):
            process_command(self.root,self.ledger,POL,self.state,{"schema_version":1,"action":"seal","job_id":j["id"],"expected_status":"reviewed","stage":"review"},0)
        self.assertEqual(j["status"],"rework")
        self.assertFalse((self.root/j["blueprint_path"]).with_name("release.json").exists())
        self.assertEqual(j["stage_index"],4)
    def test_receipts_and_rework_sync(self):
        write_json(self.root/"CURRENT.json",{"checkpoint":"S0","revision":0})
        with patch("judgesim.supply.verify",return_value=self.state):
            sync(self.root);l=read_json(self.root/"supply/STATE.json")
            j=next(iter(l["jobs"]))
            for rid,action,status,extra in [("REQ-01","start","queued",{}),("REQ-02","advance","working",{"stage":"world"})]:
                write_json(self.root/"supply/requests"/(rid+".json"),{"schema_version":1,"request_id":rid,"action":action,"job_id":j,"expected_status":status,**extra})
                sync(self.root)
            receipt=read_json(self.root/"supply/receipts/REQ-02.json")
            self.assertEqual(receipt["status"],"rework")
            before=read_json(self.root/"supply/STATE.json");sync(self.root)
            self.assertEqual(before,read_json(self.root/"supply/STATE.json"))
            (self.root/"supply/requests/REQ-01.json").unlink()
            with self.assertRaisesRegex(ValueError,"missing or modified"):sync(self.root)
    def test_future_and_cutoff_and_consumed(self):
        import_seals(ROOT,self.ledger,POL,0);j=self.ledger["jobs"]["CA9-26-001"]
        self.state["campaign"].update(game_time="2026-11-27T09:59:00-08:00",legal_cutoff="2026-11-27")
        self.assertFalse(eligible(j,self.state,"2026-11-27"))
        self.state["campaign"]["game_time"]="2026-11-27T10:00:00-08:00"
        self.assertTrue(eligible(j,self.state,"2026-11-27"))
        self.assertFalse(eligible(j,self.state,"2026-11-28"))
        self.state["cases"][j["id"]]={"phase":"unassigned","status":"pending","factory_release":{"digest":j["release_digest"]}}
        self.assertFalse(eligible(j,self.state,"2026-11-27"))
        self.assertEqual(inventory(self.ledger,self.state,POL)["registered_unassigned"],1)
        self.state["cases"][j["id"]]["phase"]="merits"
        replenish(self.ledger,self.state,POL,0)
        self.assertEqual(inventory(self.ledger,self.state,POL)["queued"],3)
class CalendarTests(unittest.TestCase):
    def setUp(self):
        self.profiles=deepcopy(profiles(ROOT));self.profiles["CA9"]["status"]="ready" # test only, no profile mutation
        self.player="J-CA9-PLAYER"
        player={"id":self.player,"name":"Supply Test Judge","birth_date":"1980-05-01","commission_date":"2026-11-27","chambers_city":"San Francisco"}
        self.s=apply_batch(initial_state(),[ev("C","campaign.configure",user_confirmed=True,court_id="CA9",player=player,game_time="2026-11-27T10:00:00-08:00",legal_cutoff="2026-11-27"),ev("O","ca9.organization_install",roster=ROSTER,roster_digest=digest(ROSTER),user_confirmed=True)],self.profiles)
        r=check_release(ROOT,RELEASE)
        self.r=r
        for i,cid in enumerate([r["case_id"],"SIM-TEST-SECOND"]):
            case=dict(r["case_fields"],id=cid,fictional=True,record_status="complete",initial_document_ids=["DOC"+str(i)],assigned_judges=[],panel_kind="ordinary_merits",conflict_review_completed=True,factory_record_as_of=r["record_as_of"],factory_release={"path":RELEASE,"digest":canonical(r)})
            self.s=apply_batch(self.s,[ev("R"+str(i),"case.register",case=case)],self.profiles)
    def review(self,judges,capacity=1,conflicts=None):
        return {"calendar_review_completed":True,"legal_review_completed":True,"rule_basis":"simulated reviewed input","priority_review":"FIFO reviewed","calendar_month":"2026-12","case_weight":1,"slots":[{"id":"SLOT1","location":"San Francisco","month":"2026-12","judges":judges,"conflicts":conflicts or [],"total_weight":capacity}]}
    def test_assignment_capacity_notice_and_replay(self):
        r=self.review([self.player,"J-CA9-01","J-CA9-02"])
        req=ev("CAL","ca9.clerk_calendar",limit=2,reviews={c:r for c in self.s["cases"]})
        with patch("judgesim.storage.profiles",return_value=self.profiles):
            events,result=calendar_events(ROOT,self.s,req)
        self.assertEqual(len(events),1)
        self.assertEqual(result,apply_batch(self.s,events,self.profiles))
        self.assertEqual(len(notices(result)),1)
        self.assertEqual(notices(result)[0]["case_id"],self.r["case_id"])
        self.assertEqual(result["cases"]["SIM-TEST-SECOND"]["phase"],"unassigned")
        with patch("judgesim.storage.profiles",return_value=self.profiles):
            with self.assertRaisesRegex(ValueError,"no reviewed eligible"):calendar_events(ROOT,result,ev("CAL2","ca9.clerk_calendar",limit=2,reviews={c:r for c in result["cases"]}))
    def test_nonplayer_and_conflict(self):
        r=self.review(["J-CA9-01","J-CA9-02","J-CA9-03"],2)
        with patch("judgesim.storage.profiles",return_value=self.profiles):
            events,result=calendar_events(ROOT,self.s,ev("CAL","ca9.clerk_calendar",limit=2,reviews={c:r for c in self.s["cases"]}))
            self.assertEqual(len(events),2)
            self.assertFalse(notices(result))
            conflict=self.review([self.player,"J-CA9-01","J-CA9-02"],2,[self.player])
            with self.assertRaises(Invalid):calendar_events(ROOT,self.s,ev("BAD","ca9.clerk_calendar",limit=1,reviews={self.r["case_id"]:conflict}))
    def test_actual_intake_plan_uses_verified_release(self):
        # Supply ledger supplied by actual workflow; use independent copy in memory if official state changed.
        ledger=new_ledger();import_seals(ROOT,ledger,POL,0)
        self.s["cases"]={}
        with patch("judgesim.supply.read_json",side_effect=lambda p:ledger if str(p).endswith("supply/STATE.json") else read_json(p)):
            self.assertFalse(intake_plan(ROOT,self.s,{"reviews":{}}))
            with self.assertRaisesRegex(ValueError,"review incomplete"):intake_plan(ROOT,self.s,{"reviews":{self.r["case_id"]:{"conflict_review_completed":True}}})
            jobs=intake_plan(ROOT,self.s,{"reviews":{self.r["case_id"]:{"conflict_review_completed":True,"jurisdiction_review_completed":True,"review_note":"test reviewed"}}})
        self.assertEqual([j["id"] for j in jobs],[self.r["case_id"]])
