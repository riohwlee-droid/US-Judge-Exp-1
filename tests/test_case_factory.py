import tempfile,unittest,json
from pathlib import Path
from copy import deepcopy
from judgesim.case_factory import compile_package,check_release,canonical,hash_bytes,REVIEW,pages
from scripts.seal_factory import process
from scripts.render_excerpts import render

class FactoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.prefix="factory/TEST-CA9/v1/";self.path=self.prefix+"blueprint.json"
        self.rec="records/TEST-CA9/v1/"
        self.t="2026-01-01T12:00:00-08:00";self.later="2026-02-01T12:00:00-08:00"
        self.b={"schema_version":1,"case_id":"TEST-CA9","version":"v1","purpose":"training","fictional":True,"court_id":"CA9","track":"civil_summary_judgment","appeal_shape":"single_represented_appeal","origin_district":"NDCA","title":"Training only — no playable case","calendar_location":"SF","jurisdiction_basis":"training 28 USC 1291","legal_cutoff":"2026-01-01","record_as_of":self.later,
            "actors":[{"id":x,"name":n,"role":r,"fictional":True} for x,n,r in [("P","Fictional Plaintiff","party"),("D","Fictional Defendant","party"),("C","Fictional Clerk","staff")]],
            "timeline":[{"id":"T1","at":self.t,"description":"Invented delivery","actor_ids":["P","D"]}],
            "facts":[{"id":"F1","subject_id":"P","event_id":"T1","field":"boxes","value":"2","unit":"boxes","visibility":"record_possible","known_by":["P","D","C"]}],
            "issues":[{"id":"I1","question":"Is the record disputed?","standard_of_review":"de novo","preservation_status":"preserved","appellant_theory":"genuine dispute","appellee_theory":"immaterial disagreement","appellant_relief":"vacate","appellee_relief":"affirm","ruling_document_id":"ORDER","ruling_page":1,"ruling_quote":"Motion granted.","preservation_document_id":"OPP","preservation_page":1,"preservation_quote":"Disputed."}],
            "documents":[],"docket":[],"assertions":[],"evidence":[],"excerpts":[],"arguments":[],"authorities":[],"reviews":[{"id":i,"status":"passed","reviewer":"training reviewer","basis":"fixture only","checked_at":"2026-02-01"} for i in sorted(REVIEW)],"unresolved_blockers":[],"timeliness_review":{"reviewed":True,"basis":"training only"}}
        for id,kind,text in [
            ("TD","trial_docket",""),("COM","complaint","Complaint."),("ANS","answer","Answer."),
            ("MSJ","motion_summary_judgment","Motion."),("OPP","opposition","Disputed."),("ORDER","trial_order","Motion granted."),
            ("J","judgment","Judgment entered."),("N","notice_appeal","Notice of appeal."),
            ("EX","exhibit","Two boxes were delivered."),("AD","appellate_docket",""),
            ("ER","er_volume",""),("IDX","er_index",""),("B1","opening_brief",""),("B2","answering_brief","")]:
            self.doc(id,kind,text)
        self.b["documents"][-4]["volume"]=1;self.b["documents"][-4]["pages"]=4
        for i,src in enumerate(["J","N","TD","EX"],1):
            self.b["excerpts"].append({"excerpt_document_id":"ER","excerpt_page":i,"volume":1,"source_document_id":src,"source_page":1})
        for x in self.b["documents"]:
            if x["kind"] in {"trial_docket","appellate_docket"}:continue
            court="district" if x["kind"] in {"complaint","answer","motion_summary_judgment","opposition","trial_order","judgment","notice_appeal","exhibit"} else "appeals"
            self.b["docket"].append({"id":"DK-"+x["id"],"document_id":x["id"],"court":court,"filed_at":self.t,"docket_page":1,"entry_text":x["id"]+" filed."})
        for k,doc in [("district","TD"),("appeals","AD")]:
            self.put(self.rec+doc+".md","<!-- PAGE 1 -->\n"+"\n".join(e["entry_text"] for e in self.b["docket"] if e["court"]==k)+"\n")
        self.put(self.rec+"ER.md","".join(f"<!-- PAGE {i} -->\n"+pages((self.root/(self.rec+src+".md")).read_text())[1]+"\n" for i,src in enumerate(["J","N","TD","EX"],1)))
        self.put(self.rec+"IDX.md","<!-- PAGE 1 -->\nER-1 Judgment\nER-2 Notice\nER-3 Docket\nER-4 Exhibit\n")
        self.b["assertions"].append({"id":"A-EX","document_id":"EX","page":1,"quote":"Two boxes were delivered.","fact_id":"F1","speaker_id":"P","asserted_value":"2","unit":"boxes","mode":"canonical"})
        self.b["evidence"].append({"id":"EV","document_id":"EX","event_id":"T1","custodian_id":"P","fact_ids":["F1"],"record_status":"filed","admission_status":"submitted_not_admitted","provenance":"training only","page":1,"quote":"Two boxes were delivered."})
        # Actual opinion excerpt, not an assertion of exhaustive subsequent treatment.
        quote="courts may not resolve genuine disputes of fact in favor of the party seeking summary judgment."
        source=quote+"\n";sp=self.prefix+"law/TOLAN.txt";self.put(sp,source)
        self.b["authorities"]=[{"id":"TOLAN","origin":"real","authority_type":"case","citation":"Tolan v. Cotton, 572 U.S. 650 (2014)","url":"https://www.law.cornell.edu/supremecourt/text/13-551","court":"SCOTUS","decided_at":"2014-05-05","verified_at":"2026-11-27","source_path":sp,"source_sha256":hash_bytes(source.encode()),"source_reviewed":True,"source_review_note":"training excerpt from part II.A, Cornell opinion; no exhaustive citator claim","subsequent_treatment":{"status":"limited_check","scope":"training only, not cleared for production","checked_at":"2026-11-27","method":"limited source review"},"pins":[{"id":"IIA","locator":"part II.A","quote":quote,"proposition":"No resolving genuine factual disputes in movant's favor."}]}]
        for id,side in [("B1","appellant"),("B2","appellee")]:
            d=next(x for x in self.b["documents"] if x["id"]==id)
            sections=["table_of_contents","table_of_authorities","argument","conclusion","certificate"]
            if id=="B1":sections+=["jurisdiction","issues","statement_of_case","summary","standard_of_review"]
            headings={s:s.replace("_"," ").title() for s in sections}
            d["sections"]={s:{"page":1,"heading":h} for s,h in headings.items()};d["body_words_reviewed"]=20
            text="\n".join(headings.values())+"\nTwo boxes were delivered. ER-4\n"+("Dispute matters." if id=="B1" else "Dispute is immaterial.")+"\nTolan v. Cotton, 572 U.S. 650 (2014) [[AUTH:TOLAN:IIA]]"
            self.put(d["path"],"<!-- PAGE 1 -->\n"+text+"\n")
            self.b["assertions"].append({"id":"A-"+id,"document_id":id,"page":1,"quote":"Two boxes were delivered.","fact_id":"F1","speaker_id":"P" if id=="B1" else "D","asserted_value":"2","unit":"boxes","mode":"allegation","record_cites":[{"cite":"ER-4","quote":"Two boxes were delivered."}]})
            self.b["arguments"].append({"id":"ARG-"+id,"document_id":id,"page":1,"quote":"Dispute matters." if id=="B1" else "Dispute is immaterial.","issue_id":"I1","side":side,"record_cites":[],"authorities":[{"authority_id":"TOLAN","pin_id":"IIA","use":"support" if id=="B1" else "distinguish","analysis":"training only"}]})
        self.save()
    def put(self,p,s):
        p=self.root/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding="utf-8")
    def doc(self,id,kind,text):
        path=self.rec+id+".md"
        self.b["documents"].append({"id":id,"kind":kind,"title":id,"path":path,"actor_id":"P","created_at":self.t,"filed_at":self.t,"access":"judge","status":"filed","pages":1,"depends_on":[]})
        self.put(path,"<!-- PAGE 1 -->\n"+text+"\n")
    def save(self):self.put(self.path,json.dumps(self.b))
    def compile(self,stage="review"):self.save();return compile_package(self.root,self.path,stage,training=True)
    def test_stages_and_release(self):
        for stage in ["world","procedure","record","excerpts","briefs"]:self.assertEqual(self.compile(stage)["stage"],stage)
        r=self.compile();p=self.prefix+"release.json";self.put(p,json.dumps(r))
        self.assertEqual(check_release(self.root,p,canonical(r),True),r)
        with self.assertRaises(ValueError):check_release(self.root,p,training=False)
    def test_conflicting_fact(self):
        self.b["assertions"][0]["asserted_value"]="3"
        with self.assertRaisesRegex(ValueError,"canonical fact contradiction"):self.compile()
    def test_unexplained_dispute(self):
        self.b["assertions"][1]["asserted_value"]="3"
        with self.assertRaisesRegex(ValueError,"unexplained contradiction"):self.compile()
        self.b["assertions"][1]["dispute_basis"]="party disputes meaning";self.compile()
    def test_hidden_fact(self):
        self.b["facts"][0]["visibility"]="world_only"
        with self.assertRaisesRegex(ValueError,"world-only"):self.compile()
    def test_bad_excerpt(self):
        self.put(self.rec+"ER.md",(self.root/(self.rec+"ER.md")).read_text().replace("Two boxes","Three boxes"))
        with self.assertRaisesRegex(ValueError,"excerpt differs"):self.compile()
    def test_bad_pin(self):
        self.b["authorities"][0]["pins"][0]["quote"]="not in opinion"
        with self.assertRaisesRegex(ValueError,"authority source quote"):self.compile()
    def test_negative_authority(self):
        self.b["authorities"][0]["subsequent_treatment"]["status"]="negative"
        with self.assertRaisesRegex(ValueError,"negative authority"):self.compile()
    def test_missing_argument(self):
        self.b["arguments"].pop()
        with self.assertRaises(ValueError):self.compile()
    def test_predetermined_winner(self):
        self.b["expected_winner"]="appellant"
        with self.assertRaisesRegex(ValueError,"predetermined"):self.compile()
    def test_tampered_release(self):
        r=self.compile();p=self.prefix+"release.json";self.put(p,json.dumps(r))
        self.put(self.rec+"COM.md","<!-- PAGE 1 -->\nAmended without permission.\n")
        with self.assertRaisesRegex(ValueError,"release differs"):check_release(self.root,p,training=True)
    def test_training_cannot_seal_on_server(self):
        self.put(self.prefix+"seal-request.json",json.dumps({"schema_version":1,"blueprint_path":self.path,"action":"seal"}))
        with self.assertRaisesRegex(ValueError,"training material"):process(self.root)
    def test_large_page_index_training_stress(self):
        # Structural stress only. No fabricated substantive case delivered.
        d=next(x for x in self.b["documents"] if x["id"]=="COM");d["pages"]=225
        self.put(d["path"],"".join(f"<!-- PAGE {i} -->\nTraining segment {i}.\n" for i in range(1,226)))
        r=self.compile();self.assertGreater(r["summary"]["original_pages"],200)
    def test_production_floor(self):
        self.b["purpose"]="production";self.save()
        with self.assertRaises(ValueError):compile_package(self.root,self.path)
