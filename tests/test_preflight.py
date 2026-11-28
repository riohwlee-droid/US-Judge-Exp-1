"""Production-path preflight; all test outcomes and documents are isolated fixtures.
No actual campaign, sealed original, or player merits decision is modified."""
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from judgesim.storage import read_json, write_json, verify
from judgesim.case_factory import check_release, canonical
from judgesim.supply import sync, candidates, notices
from scripts.process_requests import process

ROOT=Path(__file__).resolve().parents[1]
PLAYER="J-CA9-PLAYER"
CUTOFF="2026-11-27"
def event(i,event_type,**p):
    return {"id":i,"type":event_type,"payload":p}

class Preflight(unittest.TestCase):
    def test_production_end_to_end(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            # The test publishes its own requests. Keep live requests and receipts out of the fixture.
            for folder in ("courts","law","factory","records","supply","saves"):
                if (ROOT/folder).exists():shutil.copytree(ROOT/folder,root/folder)
            shutil.copy2(ROOT/"CURRENT.json",root/"CURRENT.json")
            baseline=read_json(root/"CURRENT.json")
            # Profile readiness override is solely in the disposable test copy.
            profiles=read_json(root/"courts/profiles.json")
            profiles["profiles"]["CA9"]["status"]="ready"
            write_json(root/"courts/profiles.json",profiles)
            seq=0
            def publish(events,expected="accepted"):
                nonlocal seq
                seq+=1; rid=f"ZZ-PREFLIGHT-{seq:03d}"; p=read_json(root/"CURRENT.json")
                write_json(root/"requests"/(rid+".json"),{"schema_version":1,"request_id":rid,"checkpoint":rid,"base_checkpoint":p["checkpoint"],"base_revision":p["revision"],"events":events})
                result=process(root)
                self.assertEqual(result,[{"request_id":rid,"status":expected}],read_json(root/"receipts"/(rid+".json")))
                if expected=="rejected":self.assertEqual(read_json(root/"CURRENT.json"),p)
                return verify(root)
            s=verify(root)
            # This launch-specific test remains safe after launch; ongoing lifecycle has other tests.
            if s["campaign"]["status"]!="setup_required":
                self.skipTest("initial campaign already launched; launch fixture no longer applies")
            self.assertEqual(sync(root)["inventory"]["ready"],3)
            player=read_json(ROOT/"planning/ca9-start.json")["player_proposal"]
            s=publish([event("PF-C","campaign.configure",court_id="CA9",player=player,user_confirmed=True,game_time="2026-11-30T08:30:00-08:00",legal_cutoff=CUTOFF),event("PF-O","ca9.organization_install",roster_id="CA9-ROSTER-V1",roster_digest="server_computed",user_confirmed=True)])
            self.assertEqual(len(s["people"]),201)
            self.assertEqual(s["people"][PLAYER]["seniority_rank"],29)
            self.assertEqual(s["people"][PLAYER]["career_history"],player["career_history"])
            self.assertEqual(len([p for p in s["people"].values() if p.get("judicial_status")=="active_circuit"]),29)
            sync(root)
            jobs=candidates(root,s); self.assertEqual(len(jobs),3)
            expected_docs=sum(len(check_release(root,j["release_path"],j["release_digest"])["documents"]) for j in jobs)
            review={j["id"]:{"conflict_review_completed":True,"jurisdiction_review_completed":True,"review_note":"TEST fixture only, not actual clerk clearance"} for j in jobs}
            s=publish([event("PF-I1","ca9.supply_intake",limit=2,reviews=review)])
            sync(root)
            s=publish([event("PF-I2","ca9.supply_intake",limit=1,reviews=review)])
            self.assertEqual(len(s["cases"]),3)
            self.assertEqual(len(s["documents"]),expected_docs)
            self.assertEqual(expected_docs,90)
            self.assertEqual(sync(root)["inventory"]["registered_unassigned"],3)
            # Deterministic test slot deliberately includes fixture player; not a real assignment.
            c=sorted(s["cases"].values(),key=lambda x:(x["factory_record_as_of"],x["id"]))[0]
            cid=c["id"];panel=[PLAYER,"J-CA9-01","J-CA9-02"]
            review={cid:{"calendar_review_completed":True,"legal_review_completed":True,"rule_basis":"TEST GO 3.2/3.3","priority_review":"TEST FIFO","calendar_month":"2026-12","case_weight":1,"slots":[{"id":"PF-SLOT","location":c["calendar_location"],"month":"2026-12","judges":panel,"total_weight":2,"conflicts":[]}]}}
            s=publish([event("PF-A","ca9.clerk_calendar",limit=1,reviews=review)])
            self.assertEqual(set(s["cases"][cid]["assigned_judges"]),set(panel))
            self.assertEqual(len(notices(s)),1)
            self.assertEqual(sync(root)["inventory"]["queued"],1)
            # Real reviewed citation packet copied into a new immutable test document.
            def doc(did,body,access="judge",status="internal",research=False):
                path=f"records/preflight/{did}.md";dest=root/path;dest.parent.mkdir(parents=True,exist_ok=True)
                obj={"id":did,"case_id":cid,"path":path,"sha256":"server_computed","pages":1,"access":access,"status":status}
                if research:
                    # Use a sealed authority from this same case; no fabricated authority or search.
                    rel=check_release(root,s["cases"][cid]["factory_release"]["path"])
                    b=read_json(root/rel["blueprint_path"])
                    a=deepcopy(b["authorities"][0]);r=deepcopy(next(x for x in b["research"]["authority_reviews"] if x["authority_id"]==a["id"]))
                    pref=f"law/research/{cid}/{did}/"
                    def copy_source(ref):
                        old=ref["path"];new=pref+Path(old).name
                        out=root/new;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/old,out)
                        ref["path"]=new
                    source={"path":a["source_path"]};copy_source(source);a["source_path"]=source["path"]
                    r["original"]["path"]=a["source_path"]
                    for t in r["treatments"]:copy_source(t["source"])
                    pin=a["pins"][0];pr=r["pin_reviews"][0]
                    body=body+"\n"+a["citation"]+" [[AUTH:"+a["id"]+":"+pin["id"]+"]]\n"+pin["proposition"]
                    use={"id":"PF-USE","document_id":did,"page":1,"quote":a["citation"],"authority_id":a["id"],"pin_id":pin["id"],"use":"support","claimed_weight":pr["weight"],"analysis":"TEST reproduces a previously reviewed proposition only, not a merits conclusion."}
                    if pr["status"]=="limited":use["limitation_application"]="TEST proposition only; no application to merits."
                    audit={"id":did,"reviewer":"TEST fixture","method":"Exact copied citation and offset","scope":"One page test","status":"passed","unresolved":[],"occurrences":[{"id":"C1","page":1,"offset":body.index(a["citation"]),"text":a["citation"],"authority_id":a["id"],"pin_id":pin["id"],"form":"full" if a["authority_type"]=="case" else a["authority_type"]}]}
                    packet={"schema_version":1,"case_id":cid,"document_id":did,"document_sha256":"server_computed","authorities":[a],"uses":[use],"research":{"schema_version":1,"cutoff":CUTOFF,"authority_reviews":[r],"document_audits":[audit]}}
                    write_json(root/(pref+"packet.json"),packet)
                    obj["research_packet"]={"path":pref+"packet.json","digest":"server_computed"}
                dest.write_text("<!-- PAGE 1 -->\n"+body+"\n",encoding="utf-8")
                return event("PF-D-"+did,"document.register",document=obj)
            ca=lambda i,k,**p:event(i,"ca9."+k,case_id=cid,legal_review_completed=True,rule_basis="TEST reviewed procedure",**p)
            s=publish([event("PF-T","task.assign",task_id="PF-TASK",case_id=cid,assigning_judge_id=PLAYER,assignee_id="CH-J-CA9-PLAYER-LC1",task_kind="research",instructions="TEST source review",due_at="2026-12-02T17:00:00-08:00")])
            s=publish([doc("PF-MEMO","TEST research memorandum.",research=True),event("PF-TC","task.complete",task_id="PF-TASK",output_document_id="PF-MEMO")])
            self.assertEqual(s["tasks"]["PF-TASK"]["status"],"completed")
            s=publish([event("PF-TIME","time.advance",minutes=3*1440,user_authorized=True),event("PF-H","hearing.start",case_id=cid,hearing_id="PF-HR",kind="oral_argument"),event("PF-HC","hearing.complete",case_id=cid,hearing_id="PF-HR")])
            panel=s["cases"][cid]["assigned_judges"];others=[j for j in panel if j!=PLAYER]
            votes={PLAYER:"affirm",others[0]:"affirm",others[1]:"reverse"}
            author=PLAYER
            conf=event("PF-CONF","conference.record",case_id=cid,votes=votes,majority_disposition="affirm",author_id=author)
            publish([conf],"rejected")
            s=publish([doc("PF-V1","TEST independent preliminary view one.",access="npc_private"),doc("PF-V2","TEST independent preliminary view two.",access="npc_private"),event("PF-IV1","ca9.independent_view",case_id=cid,judge_id=others[0],document_id="PF-V1",disposition="affirm"),event("PF-IV2","ca9.independent_view",case_id=cid,judge_id=others[1],document_id="PF-V2",disposition="reverse"),event("PF-CONF2","conference.record",case_id=cid,votes=votes,majority_disposition="affirm",author_id=author),event("PF-DR","draft.start",case_id=cid,author_id=author)])
            def circulate(did,oid,**extra):
                return [doc(did,"TEST opinion mechanics only; no actual disposition.",research=True),event("PF-C-"+oid,"opinion.circulate",opinion={"id":oid,"case_id":cid,"document_id":did,"author_id":author,"parts":["I","II"],**extra})]
            s=publish(circulate("PF-OP1","PF-O1"))
            s=publish([event("PF-P1","opinion.position",opinion_id="PF-O1",judge_id=others[0],disposition="affirm",stance="concur",joined_parts=["I"],comment="TEST narrow reasoning"),*circulate("PF-OP2","PF-O2",supersedes="PF-O1")])
            self.assertEqual(s["opinions"]["PF-O1"]["status"],"superseded")
            self.assertEqual(s["opinions"]["PF-O2"]["positions"],{})
            s=publish([event("PF-P2-"+str(i),"opinion.position",opinion_id="PF-O2",judge_id=j,disposition=votes[j],stance="join" if votes[j]=="affirm" else "dissent",joined_parts=["I","II"] if votes[j]=="affirm" else []) for i,j in enumerate(panel)])
            s=publish([event("PF-ISSUE","opinion.issue",opinion_id="PF-O2",opinion_kind="majority",rule_basis="TEST",legal_review_completed=True,publication_form="MEMORANDUM",certified=True,disposition="affirm"),doc("PF-JUD","TEST judgment.",status="filed"),ca("PF-J","judgment",controlling_opinion_id="PF-O2",judgment_document_id="PF-JUD",calendar_verified=True,federal_party_civil=False,holidays=["2026-12-25","2027-01-01"])])
            self.assertEqual(s["cases"][cid]["review"]["petition_due"],"2026-12-17")
            publish([doc("PF-MAND","TEST mandate.",status="filed"),ca("PF-M0","mandate",mandate_document_id="PF-MAND",certified_judgment_and_costs_reviewed=True)],"rejected")
            s=publish([event("PF-TIME2","time.advance",minutes=25*1440,user_authorized=True),ca("PF-CLEAR","en_banc_clear",all_notice_call_periods_checked=True,same_day_call_window_closed=True),doc("PF-MAND2","TEST mandate.",status="filed"),ca("PF-M","mandate",mandate_document_id="PF-MAND2",certified_judgment_and_costs_reviewed=True)])
            self.assertEqual(s["cases"][cid]["status"],"closed")
            self.assertEqual(verify(root),s)
            self.assertEqual(sync(root)["inventory"]["closed"],1)
            self.assertEqual(read_json(ROOT/"CURRENT.json"),baseline)
