"""Pre-admission compiler for fictional appeals. Structural checks != legal truth."""
from collections import Counter, defaultdict
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
import json
import re
from urllib.parse import urlparse

VERSION=1
TRACKS={
 "civil_summary_judgment":{"complaint","answer","motion_summary_judgment","opposition","trial_order","judgment"},
 "civil_trial":{"complaint","answer","trial_transcript","trial_order","judgment"},
 "criminal_trial":{"indictment","trial_transcript","verdict","sentencing_transcript","judgment"},
 "criminal_suppression":{"indictment","motion_suppress","opposition","suppression_transcript","trial_order","judgment"}
}
COMMON={"trial_docket","notice_appeal","appellate_docket","opening_brief","answering_brief","er_index","er_volume"}
BRIEFS={"opening_brief","answering_brief","reply_brief"}
LOWER={"trial_docket","complaint","answer","indictment","motion_summary_judgment","motion_suppress","opposition","reply_motion","trial_order","judgment","trial_transcript","suppression_transcript","sentencing_transcript","verdict","exhibit","deposition","affidavit","discovery_filing","notice_appeal","other_lower"}
STAGES=("world","procedure","record","excerpts","briefs","review")
REVIEW={"chronology","identity_amounts_units","knowledge_and_access","docket_and_evidence","jurisdiction_and_timeliness","preservation_and_review_standard","record_pinpoints","legal_pinpoints_and_treatment","adversarial_balance","no_predetermined_appellate_result","length_and_originality","local_rule_compliance"}
FORBIDDEN={"expected_winner","correct_disposition","canonical_appellate_result","target_verdict","answer_key","winning_party","preferred_appellate_outcome"}
ID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,119}$")
MARK=re.compile(r"^<!-- PAGE ([1-9][0-9]*) -->\s*$",re.M)
ER=re.compile(r"\b([1-9][0-9]*)-(ER|SER|FER)-([1-9][0-9]*)\b")
LEGAL=re.compile(r"\[\[AUTH:([A-Za-z0-9_.-]+):([A-Za-z0-9_.-]+)\]\]")
DISTRICTS={"AK","AZ","CDCA","EDCA","NDCA","SDCA","HI","ID","MT","NV","OR","EDWA","WDWA","GU","NMI"}
def need(v,msg):
    if not v:raise ValueError(msg)
def nonblank(v):return isinstance(v,str) and bool(v.strip())
def key(v):
    need(isinstance(v,str) and ID.fullmatch(v),"invalid ID")
    return v
def at(v):
    d=datetime.fromisoformat(v.replace("Z","+00:00"));need(d.tzinfo is not None,"timestamp requires offset")
    return d
def norm(s):return " ".join(s.split())
def words(s):return len(re.findall(r"\b[\w]+(?:[-’'][\w]+)*\b",s))
def hash_bytes(b):return sha256(b).hexdigest()
def canonical(obj):return hash_bytes(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode())
def load(path):
    def unique(pairs):
        d={}
        for k,v in pairs:
            need(k not in d,"duplicate JSON key "+k);d[k]=v
        return d
    return json.loads(Path(path).read_text(encoding="utf-8"),object_pairs_hook=unique,parse_constant=lambda x:(_ for _ in ()).throw(ValueError("nonfinite number")))
def safe(root,path):
    need(isinstance(path,str) and not Path(path).is_absolute() and ".." not in Path(path).parts,"unsafe path")
    p=(Path(root)/path).resolve()
    need(p.is_relative_to(Path(root).resolve()),"path escape")
    return p
def table(rows,label):
    need(isinstance(rows,list),label+" must be list")
    out={}
    for row in rows:
        i=key(row["id"]);need(i not in out,"duplicate "+label+" "+i);out[i]=row
    return out
def no_answers(obj):
    if isinstance(obj,dict):
        need(not FORBIDDEN.intersection(obj),"predetermined appellate outcome field forbidden")
        for x in obj.values():no_answers(x)
    elif isinstance(obj,list):
        for x in obj:no_answers(x)
def pages(text):
    m=list(MARK.finditer(text));need(m and not text[:m[0].start()].strip(),"missing initial page marker")
    need([int(x[1]) for x in m]==list(range(1,len(m)+1)),"nonconsecutive logical pages")
    result={i+1:text[x.end():m[i+1].start() if i+1<len(m) else len(text)].strip() for i,x in enumerate(m)}
    need(all(result.values()),"empty page")
    return result
def source_pin(pin,source_text):
    need(nonblank(pin["locator"]) and nonblank(pin["quote"]) and norm(pin["quote"]) in norm(source_text),"authority source quote missing")
    need(nonblank(pin["proposition"]),"authority proposition missing")
def approved_url(url):
    u=urlparse(url);h=u.hostname or ""
    return u.scheme=="https" and not u.username and not u.password and (h in {"courtlistener.com","www.courtlistener.com","govinfo.gov","www.govinfo.gov","uscode.house.gov","law.cornell.edu","www.law.cornell.edu","supremecourt.gov","www.supremecourt.gov","loc.gov","www.loc.gov"} or h=="uscourts.gov" or h.endswith(".uscourts.gov"))

def compile_package(root, blueprint_path, stage="review", training=False):
    need(stage in STAGES,"unknown stage")
    b=load(safe(root,blueprint_path));no_answers(b)
    need(b["schema_version"]==VERSION and b["fictional"] is True,"factory schema/fictional required")
    cid=key(b["case_id"]); rev=key(b["version"]); prefix=f"factory/{cid}/{rev}/"
    need(blueprint_path==prefix+"blueprint.json","blueprint path mismatch")
    need(b["court_id"]=="CA9" and b["track"] in TRACKS and b["origin_district"] in DISTRICTS,"unsupported court/track/district")
    need(b["purpose"]==("training" if training else "production"),"training material cannot enter live record")
    cutoff=date.fromisoformat(b["legal_cutoff"]);ready=at(b["record_as_of"])
    need(cutoff<=ready.date(),"future legal cutoff")
    need(nonblank(b["title"]) and nonblank(b["jurisdiction_basis"]) and nonblank(b["calendar_location"]),"case metadata missing")
    actors=table(b["actors"],"actors");facts=table(b["facts"],"facts");timeline=table(b["timeline"],"timeline")
    need(actors and facts and timeline,"world ledger incomplete")
    need(all(x["fictional"] is True and nonblank(x["name"]) and nonblank(x["role"]) for x in actors.values()),"invalid fictional actors")
    need(len({x["name"] for x in actors.values()})==len(actors),"duplicate actor names")
    for e in timeline.values():
        need(at(e["at"])<=ready and nonblank(e["description"]) and e["actor_ids"] and set(e["actor_ids"])<=actors.keys(),"invalid world event")
    tuples=set()
    for f in facts.values():
        need(f["subject_id"] in actors and f["event_id"] in timeline and nonblank(f["field"]) and nonblank(f["value"]) and nonblank(f["unit"]),"invalid canonical fact")
        t=(f["subject_id"],f["event_id"],f["field"]);need(t not in tuples,"conflicting canonical fact key");tuples.add(t)
        need(f["visibility"] in {"record_possible","world_only"} and set(f["known_by"])<=actors.keys(),"fact access invalid")
    summary={"case_id":cid,"version":rev,"stage":stage,"facts":len(facts),"actors":len(actors)}
    if stage=="world":return summary
    issues=table(b["issues"],"issues")
    need(issues,"no appellate issues")
    for i in issues.values():
        need(all(nonblank(i.get(k)) for k in ("question","standard_of_review","preservation_status","appellant_theory","appellee_theory","appellant_relief","appellee_relief")),"incomplete adversarial issue")
        need(norm(i["appellant_theory"])!=norm(i["appellee_theory"]),"both sides need distinct theories")
    docs=table(b["documents"],"documents")
    need(docs and len({d["path"] for d in docs.values()})==len(docs),"document inventory/path collision")
    kinds={d["kind"] for d in docs.values()}
    need(TRACKS[b["track"]]|COMMON <= kinds,"mandatory record category missing")
    for d in docs.values():
        need(d["kind"] in LOWER|BRIEFS|{"appellate_docket","er_index","er_volume","ser_volume","fer_volume","amicus","order_appeal","other_appeal","world_evidence"},"unknown document kind")
        need(d["path"].startswith(f"records/{cid}/{rev}/") and d["path"].endswith(".md"),"record path not version-scoped")
        need(d["actor_id"] in actors and at(d["created_at"])<=at(d["filed_at"])<=ready,"document chronology")
        need(d["access"] in {"judge","world_only"} and d["status"]==("filed" if d["access"]=="judge" else "unfiled"),"initial record visibility mismatch")
        need((d["kind"]=="world_evidence")== (d["access"]=="world_only"),"world-only must not enter filed record")
        need(type(d["pages"]) is int and d["pages"]>=1 and nonblank(d["title"]),"invalid document plan")
        need(set(d.get("depends_on",[]))<=docs.keys() and d["id"] not in d.get("depends_on",[]),"invalid dependency")
        for dep in d.get("depends_on",[]):need(at(docs[dep]["filed_at"])<=at(d["filed_at"]),"future document dependency")
    visiting=set();done=set()
    def visit(i):
        need(i not in visiting,"dependency cycle")
        if i in done:return
        visiting.add(i)
        for x in docs[i].get("depends_on",[]):visit(x)
        visiting.remove(i);done.add(i)
    for i in docs:visit(i)
    docket=table(b["docket"],"docket")
    docketed={}
    for e in docket.values():
        d=docs[e["document_id"]]
        need(d["access"]=="judge" and d["id"] not in docketed,"bad/duplicate docket entry")
        need(e["court"] in {"district","appeals"} and at(e["filed_at"])==at(d["filed_at"]),"docket date mismatch")
        need((e["court"]=="district")==(d["kind"] in LOWER),"docket court mismatch")
        docketed[d["id"]]=e
    need(set(docketed)=={d["id"] for d in docs.values() if d["access"]=="judge" and d["kind"] not in {"trial_docket","appellate_docket"}},"filed inventory/docket mismatch")
    def one(kind):
        ds=[d for d in docs.values() if d["kind"]==kind];need(len(ds)==1,"exactly one "+kind+" required");return ds[0]
    judgment=one("judgment");notice=one("notice_appeal");opening=one("opening_brief");answer=one("answering_brief")
    need(at(judgment["filed_at"])<=at(notice["filed_at"])<=at(opening["filed_at"])<=at(answer["filed_at"]),"appeal chronology")
    for d in docs.values():
        if d["kind"]=="reply_brief":need(at(d["filed_at"])>=at(answer["filed_at"]),"reply before answer")
    for i in issues.values():
        for k in ("ruling_document_id","preservation_document_id"):
            d=docs[i[k]];need(d["kind"] in LOWER and d["access"]=="judge","issue needs lower record")
    need(b["timeliness_review"]["reviewed"] is True and nonblank(b["timeliness_review"]["basis"]),"jurisdiction/timeliness review required")
    summary.update(documents=len(docs),issues=len(issues))
    if stage=="procedure":return summary
    pmap={};hashes={};counts={};seen={}
    for d in docs.values():
        if stage=="record" and d["kind"] not in LOWER|{"world_evidence"}:continue
        if stage=="excerpts" and d["kind"] in BRIEFS|{"amicus"}:continue
        raw=safe(root,d["path"]).read_bytes();pmap[d["id"]]=pages(raw.decode("utf-8"));hashes[d["path"]]=hash_bytes(raw)
        need(len(pmap[d["id"]])==d["pages"],"page count mismatch "+d["id"])
        counts[d["id"]]=sum(words(p) for p in pmap[d["id"]].values())
        if d["kind"] not in {"er_volume","ser_volume","fer_volume","er_index","trial_docket","appellate_docket"}:
            for n,txt in pmap[d["id"]].items():
                if words(txt)>=60:
                    h=hash_bytes(norm(txt).encode());need(h not in seen,"duplicate substantive page "+d["id"]);seen[h]=(d["id"],n)
                need(not re.search(r"\b(?:TODO|TBD|PLACEHOLDER|continued verbatim|pages omitted)\b",txt,re.I),"unfinished original "+d["id"])
        if not training and d["kind"] in {"trial_transcript","suppression_transcript","sentencing_transcript","deposition","opening_brief","answering_brief","reply_brief"}:
            need(counts[d["id"]]>=70*d["pages"],"thin substantive document "+d["id"])
    def anchor(ref, allowed=None):
        d=docs[ref["document_id"]];n=ref["page"];need(type(n) is int and n in pmap[d["id"]],"missing cited page")
        if allowed:need(d["kind"] in allowed and d["access"]=="judge","citation outside filed lower record")
        need(nonblank(ref["quote"]) and norm(ref["quote"]) in norm(pmap[d["id"]][n]),"anchor text not on cited page "+d["id"])
        return d
    assertions=table(b["assertions"],"assertions")
    for a in assertions.values():
        d=docs[a["document_id"]]
        if d["id"] not in pmap:continue
        anchor({"document_id":d["id"],"page":a["page"],"quote":a["quote"]})
        f=facts[a["fact_id"]]
        need(a["speaker_id"] in actors and nonblank(a["asserted_value"]) and a["unit"]==f["unit"],"assertion actor/value/unit invalid")
        need(a["mode"] in {"canonical","testimony","allegation","inference","finding"},"invalid assertion mode")
        if a["mode"]=="canonical":need(a["asserted_value"]==f["value"],"canonical fact contradiction "+a["id"])
        if d["access"]=="judge":
            need(f["visibility"]!="world_only","world-only truth leaked")
            if a["mode"] in {"canonical","testimony"}:need(a["speaker_id"] in f["known_by"],"speaker lacks knowledge")
        if a["asserted_value"]!=f["value"]:
            need(a["mode"]!="canonical" and nonblank(a.get("dispute_basis")),"unexplained contradiction")
    for e in docket.values():
        d=docs[e["document_id"]]
        if d["kind"] in LOWER:
            docket_doc=one("trial_docket")
        else:docket_doc=one("appellate_docket")
        if docket_doc["id"] in pmap:
            need(nonblank(e["entry_text"]) and norm(e["entry_text"]) in norm(pmap[docket_doc["id"]][e["docket_page"]]),"docket entry missing from original")
    for i in issues.values():
        for k in ("ruling","preservation"):
            if i[k+"_document_id"] in pmap:
                anchor({"document_id":i[k+"_document_id"],"page":i[k+"_page"],"quote":i[k+"_quote"]},LOWER)
    if stage=="record":return dict(summary,originals_checked=len(pmap))
    ermap={}
    for e in b["excerpts"]:
        d=docs[e["excerpt_document_id"]];src=docs[e["source_document_id"]]
        need(d["kind"] in {"er_volume","ser_volume","fer_volume"} and src["kind"] in LOWER and src["access"]=="judge","invalid excerpt source")
        n=e["excerpt_page"];sn=e["source_page"];need(type(n) is int and type(sn) is int,"bad excerpt page")
        typ={"er_volume":"ER","ser_volume":"SER","fer_volume":"FER"}[d["kind"]]
        need(type(e["volume"]) is int and e["volume"]>=1 and e["volume"]==d["volume"],"volume mismatch")
        cite=f'{e["volume"]}-{typ}-{n}';need(cite not in ermap,"duplicate excerpt citation")
        need(norm(pmap[d["id"]][n])==norm(pmap[src["id"]][sn]),"excerpt differs from original "+cite)
        ermap[cite]=e
    for d in docs.values():
        if d["kind"] in {"er_volume","ser_volume","fer_volume"}:
            need({e["excerpt_page"] for e in ermap.values() if e["excerpt_document_id"]==d["id"]}==set(pmap[d["id"]]),"unmapped excerpt pages")
    need(any(e["source_document_id"]==judgment["id"] for e in ermap.values()) and any(e["source_document_id"]==notice["id"] for e in ermap.values()) and any(docs[e["source_document_id"]]["kind"]=="trial_docket" for e in ermap.values()),"missing judgment/notice/docket in excerpts")
    index=one("er_index")
    for cite in ermap:need(cite in " ".join(pmap[index["id"]].values()),"missing excerpt index entry "+cite)
    if stage=="excerpts":return dict(summary,excerpt_pages=len(ermap))
    auth=table(b["authorities"],"authorities")
    need(auth,"no authorities")
    for a in auth.values():
        need(a["origin"]=="real" and approved_url(a["url"]) and nonblank(a["citation"]) and nonblank(a["court"]),"unverified authority identity/source")
        need(date.fromisoformat(a["decided_at"])<=cutoff and date.fromisoformat(a["verified_at"])>=date.fromisoformat(a["decided_at"]),"authority date invalid")
        need(a["source_path"].startswith(prefix+"law/"),"source snapshot path")
        raw=safe(root,a["source_path"]).read_bytes()
        need(hash_bytes(raw)==a["source_sha256"],"authority snapshot changed")
        hashes[a["source_path"]]=hash_bytes(raw)
        need(a["source_reviewed"] is True and nonblank(a["source_review_note"]),"authority original review required")
        t=a["subsequent_treatment"]
        need(t["status"] in {"checked_no_negative_found","limited_check","negative","not_checked"} and nonblank(t["scope"]),"treatment review required")
        need(t["status"]!="not_checked" and nonblank(t["checked_at"]) and nonblank(t["method"]),"unchecked subsequent treatment")
        for pin in table(a["pins"],"pins").values():source_pin(pin,raw.decode("utf-8"))
    arguments=table(b["arguments"],"arguments")
    for d in docs.values():
        if d["kind"] not in BRIEFS:continue
        required={"table_of_contents","table_of_authorities","argument","conclusion","certificate"}
        if d["kind"]=="opening_brief":required|={"jurisdiction","issues","statement_of_case","summary","standard_of_review"}
        need(required<=set(d["sections"]),"missing brief sections "+d["id"])
        whole="\n".join(pmap[d["id"]].values())
        limit=6500 if d["kind"]=="reply_brief" else 13000
        need(type(d["body_words_reviewed"]) is int and 0<d["body_words_reviewed"]<=counts[d["id"]],"invalid reviewed body words")
        need(d["body_words_reviewed"]<=limit or nonblank(d.get("length_order_basis")),"brief exceeds ordinary word limit")
        visible={f"{v}-{t}-{n}" for v,t,n in ER.findall(whole)}
        annotated=set()
        for a in assertions.values():
            if a["document_id"]!=d["id"]:continue
            need(a.get("record_cites"),"brief factual assertion lacks record cite")
            for ref in a["record_cites"]:
                cite=ref["cite"];need(cite in ermap and cite in pmap[d["id"]][a["page"]],"brief record cite missing")
                e=ermap[cite];anchor({"document_id":e["source_document_id"],"page":e["source_page"],"quote":ref["quote"]},LOWER)
                annotated.add(cite)
        for a in arguments.values():
            if a["document_id"]!=d["id"]:continue
            need(a["issue_id"] in issues and a["side"]==("appellee" if d["kind"]=="answering_brief" else "appellant"),"argument side/issue mismatch")
            anchor({"document_id":d["id"],"page":a["page"],"quote":a["quote"]})
            need(a["authorities"],"argument lacks legal authority")
            for r in a.get("record_cites",[]):
                cite=r["cite"];need(cite in ermap and cite in pmap[d["id"]][a["page"]],"argument cite missing")
                e=ermap[cite];anchor({"document_id":e["source_document_id"],"page":e["source_page"],"quote":r["quote"]},LOWER);annotated.add(cite)
            for ref in a["authorities"]:
                authority=auth[ref["authority_id"]];pin=table(authority["pins"],"pins")[ref["pin_id"]]
                tag=f'[[AUTH:{authority["id"]}:{pin["id"]}]]'
                need(tag in pmap[d["id"]][a["page"]] and authority["citation"] in pmap[d["id"]][a["page"]],"legal citation/annotation missing")
                need(ref["use"] in {"support","distinguish","adverse"} and nonblank(ref["analysis"]),"unreviewed legal application")
                if authority["subsequent_treatment"]["status"]=="negative":need(ref["use"]!="support","negative authority relied upon as support")
        need(visible==annotated,"unmapped record citation in "+d["id"])
        actual=set(LEGAL.findall(whole));mapped={(r["authority_id"],r["pin_id"]) for a in arguments.values() if a["document_id"]==d["id"] for r in a["authorities"]}
        need(actual==mapped and actual,"unmapped legal citation")
    for i in issues:
        for side,d in (("appellant",opening),("appellee",answer)):
            need(any(a["issue_id"]==i and a["side"]==side and a["document_id"]==d["id"] for a in arguments.values()),"issue not argued by both parties")
    original=[d for d in docs.values() if d["kind"] not in {"er_volume","ser_volume","fer_volume","er_index"} and d["access"]=="judge"]
    total=sum(d["pages"] for d in original);total_words=sum(counts[d["id"]] for d in original)
    if not training:need(total>=200 and total_words>=24000,"production requires 200 original logical pages and 24,000 original words")
    summary.update(original_pages=total,original_words=total_words,excerpt_pages=len(ermap),authorities=len(auth))
    if stage=="briefs":return summary
    reviews=table(b["reviews"],"reviews")
    need(set(reviews)==REVIEW,"review checklist incomplete")
    for r in reviews.values():need(r["status"]=="passed" and nonblank(r["reviewer"]) and nonblank(r["basis"]) and nonblank(r["checked_at"]),"review not passed")
    need(b["unresolved_blockers"]==[],"unresolved blockers")
    hashes[blueprint_path]=hash_bytes(safe(root,blueprint_path).read_bytes())
    registrations=[]
    for d in docs.values():
        registrations.append({"id":d["id"],"case_id":cid,"title":d["title"],"path":d["path"],"sha256":hashes[d["path"]],"pages":d["pages"],"page_system":"stable_logical_pages","access":d["access"],"status":d["status"],"filed_at":d["filed_at"] if d["status"]=="filed" else None,"supersedes":None,"citations":[],"kind":d["kind"]})
    return {"schema_version":VERSION,"purpose":b["purpose"],"case_id":cid,"version":rev,"blueprint_path":blueprint_path,"legal_cutoff":b["legal_cutoff"],"record_as_of":b["record_as_of"],"case_fields":{"title":b["title"],"court_id":"CA9","matter_type":"civil_appeal" if b["track"].startswith("civil") else "criminal_appeal","origin_district":b["origin_district"],"calendar_location":b["calendar_location"],"jurisdiction_basis":b["jurisdiction_basis"]},"files":hashes,"documents":registrations,"summary":summary}

def release_path(cid,rev):return f"factory/{key(cid)}/{key(rev)}/release.json"
def check_release(root,path,expected=None,training=False):
    r=load(safe(root,path));need(path==release_path(r["case_id"],r["version"]),"release path mismatch")
    need(r==compile_package(root,r["blueprint_path"],training=training),"release differs from compiled originals")
    if expected is not None:need(canonical(r)==expected,"release digest mismatch")
    return r
