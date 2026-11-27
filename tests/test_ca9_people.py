import unittest
from copy import deepcopy
from pathlib import Path
from judgesim.engine import initial_state, apply_batch, require, Invalid, digest
from judgesim.storage import read_json
from judgesim.ca9_people import check_roster, task_guard, conference_guard
ROOT=Path(__file__).resolve().parents[1]
PKG=read_json(ROOT/"courts/ca9/roster-v1.json")
PROFILES={"CA9":{"status":"training_only","matter_types":["civil_appeal"],"hearing_kinds":["oral_argument"]}}
def ev(i,k,**p):return {"id":i,"type":k,"payload":p}
class OrganizationTests(unittest.TestCase):
    def install(self):
        s=initial_state()
        player={"id":"J-CA9-PLAYER","name":"Fictional Test Player","birth_date":"1980-05-01","commission_date":"2026-11-27","chambers_city":"San Francisco"}
        s=apply_batch(s,[ev("C","campaign.configure",user_confirmed=True,court_id="CA9",player=player,game_time="2026-11-27T10:00:00-08:00",legal_cutoff="2026-11-27"),ev("O","ca9.organization_install",roster=PKG,roster_digest=digest(PKG),user_confirmed=True)],PROFILES,True)
        return s
    def test_roster(self):
        check_roster(PKG,require)
        s=self.install()
        self.assertEqual(len([p for p in s["people"].values() if p.get("judicial_status")=="active_circuit"]),29)
        self.assertEqual(len(s["campaign"]["organization"]["chambers"]),37)
        self.assertTrue(all(s["people"][j]["active"] for j in next(x for x in s["campaign"]["organization"]["chambers"] if x["judge_id"]=="J-CA9-PLAYER")["staff_ids"]))
    def test_tampered_seats_and_seniority(self):
        p=deepcopy(PKG);p["seats"].pop()
        with self.assertRaises(Invalid):check_roster(p,require)
        p=deepcopy(PKG);p["people"][0]["seniority_rank"]=2
        with self.assertRaises(Invalid):check_roster(p,require)
    def test_no_extra_active_judge(self):
        s=self.install()
        with self.assertRaises(Invalid):apply_batch(s,[ev("X","person.register",person={"id":"EXTRA","role":"judge","fictional":True,"active":True})],PROFILES,True)
    def test_chambers_permissions(self):
        s=self.install();s["cases"]["C"]={"assigned_judges":["J-CA9-PLAYER","J-CA9-01","J-CA9-02"],"phase":"merits"}
        p={"case_id":"C","assigning_judge_id":"J-CA9-PLAYER","assignee_id":"CH-J-CA9-PLAYER-LC1","task_kind":"research"}
        task_guard(s,p,require)
        p["assignee_id"]="CH-J-CA9-01-LC1"
        with self.assertRaises(Invalid):task_guard(s,p,require)
        p["assignee_id"]="CH-J-CA9-PLAYER-JA"
        with self.assertRaises(Invalid):task_guard(s,p,require)
    def test_independent_views(self):
        s=self.install();c={"assigned_judges":["J-CA9-PLAYER","J-CA9-01","J-CA9-02"],"panel_epoch":1}
        with self.assertRaises(Invalid):conference_guard(s,c,require)
        c["independent_views"]={"1":{"J-CA9-01":{},"J-CA9-02":{}}}
        conference_guard(s,c,require)
