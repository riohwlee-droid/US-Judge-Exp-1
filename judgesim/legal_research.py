"""CA9 proposition-specific research verification; offline validation of reviewed evidence."""
from datetime import date
import re
from .case_factory import need,nonblank,table,norm,safe,load,hash_bytes,canonical,approved_url,pages,LEGAL,key

REPORTER=re.compile(r"\b\d+\s+(?:U\.S\.|S\. Ct\.|F\.(?:2d|3d|4th| Supp\.(?: 2d| 3d)?)|F\.\s+App['’]x|L\. Ed\. 2d)\s+\d+\b")
SHORT=re.compile(r"\b(?:Id\.|id\.|supra\b)")
# These are audit aids, not a comprehensive legal citation parser.
NEG={"overruled","vacated","superseded","abrogated"}
CASES={"scotus","ca9","other_federal","district","state_highest","state_other"}
USE={"support","distinguish","adverse","history","preclusion","factual","conflict_rehearing"}

def day(x):return date.fromisoformat(x)
def required_text(o,keys):
    need(all(nonblank(o.get(k)) for k in keys),"missing research field: "+str(keys))
def source(root,ref,prefix,hashes):
    need(ref["path"].startswith(prefix) and approved_url(ref["url"]),"unapproved research source")
    raw=safe(root,ref["path"]).read_bytes()
    need(ref["sha256"] in {"server_computed",hash_bytes(raw)},"research source hash mismatch")
    hashes[ref["path"]]=hash_bytes(raw)
    return raw.decode("utf-8")
def segment(text,locator,quote):
    # Explicit locator-delimited excerpts; location is checked against source by researcher.
    marker="@@ LOC "+locator
    blocks=re.split(r"(?m)^@@ LOC ",text)
    found=[b.split("\n",1)[1] for b in blocks[1:] if "\n" in b and b.split("\n",1)[0]==locator]
    need(nonblank(locator) and len(found)==1 and nonblank(quote) and norm(quote) in norm(found[0]),"quote not at reviewed locator "+locator)
def validate_authority(root,a,r,cutoff,prefix,hashes):
    need(r["authority_id"]==a["id"],"authority review mismatch")
    need(a["origin"]=="real" and a["authority_type"] in {"case","statute","rule","regulation","constitution"} and approved_url(a["url"]) and nonblank(a["court"]) and nonblank(a["citation"]),"real authority metadata required")
    need(day(a["decided_at"])<=cutoff and day(a["verified_at"])>=day(a["decided_at"]) and a["source_reviewed"] is True,"unreviewed authority date/source")
    required_text(r,["reviewer","identity_basis","scope_note"])
    need(r["cutoff"]==cutoff.isoformat() and day(r["reviewed_at"])>=cutoff,"review cutoff/date mismatch")
    need(r["identity_status"]=="verified","unverified or ambiguous authority")
    need(r["citation"]==a["citation"] and r["decision_date"]==a["decided_at"],"authority identity mismatch")
    ref=r["original"];need(ref["path"]==a["source_path"] and ref["sha256"]==a["source_sha256"] and ref["url"]==a["url"],"source identity mismatch")
    txt=source(root,ref,prefix,hashes)
    need(r["source_kind"] in {"official","courtlistener","other_reviewed"} and r["opinion_text_reviewed"] is True,"original text review required")
    iscase=a["authority_type"]=="case"
    if iscase:
        need(r["court_level"] in CASES and r["opinion_kind"] in {"majority","per_curiam","plurality","concurrence","dissent","order","combined_reviewed"},"opinion identity missing")
        need(r["publication"] in {"published","unpublished","unknown"} and r["panel_kind"] in {"panel","en_banc","full_court","not_applicable","unknown"},"publication/panel missing")
        court=a["court"].lower()
        if court in {"ca9","scotus"}:need(r["court_level"]==court,"court level inconsistent with authority")
        if r["court_level"] in {"ca9","scotus"}:need(court==r["court_level"],"controlling court code required")
        ids=r["identity_lookup"]
        need(ids["provider"] in {"courtlistener","official"} and ids["status"]=="found","citation lookup not verified")
        required_text(ids,["basis","canonical_name","matched_citation"])
        need(ids["matched_citation"] in a["citation"],"matched reporter citation not present")
        if ids["provider"]=="courtlistener":
            need(type(ids["cluster_id"]) is int and ids["cluster_id"]>0 and type(ids["opinion_id"]) is int and ids["opinion_id"]>0,"CourtListener cluster/opinion identity required")
            need(all(type(i) is int and i>0 for i in ids.get("alternate_clusters",[])),"bad duplicate cluster IDs")
        else:need(approved_url(ids["official_url"]),"official lookup URL required")
        need(day(a["decided_at"])<=cutoff,"post-cutoff case")
    else:
        required_text(r,["version_basis","jurisdiction_basis"])
        start=day(r["effective_from"]);end=day(r["effective_to"]) if r.get("effective_to") else None
        need(start<=cutoff and (end is None or cutoff<end),"law version not effective at cutoff")
    pins=table(a["pins"],"authority pins");reviews=table(r["pin_reviews"],"pin reviews")
    need(pins,"authority requires at least one proposition")
    need(set(pins)==set(reviews),"missing proposition review")
    for pid,pin in pins.items():
        pr=reviews[pid]
        need(pr["locator"]==pin["locator"] and pr["proposition"]==pin["proposition"],"pin identity mismatch")
        segment(txt,pin["locator"],pin["quote"])
        required_text(pr,["reasoning","applicability","limitation"])
        need(pr["character"] in {"holding","dictum","separate","plurality","procedural","text","unresolved"},"invalid proposition character")
        need(pr["status"] in {"usable_limited","limited","overruled","vacated","superseded","abrogated","unresolved"},"unknown treatment status")
        need(pr["status"]!="unresolved" and pr["character"]!="unresolved","unresolved proposition")
        need(pr["weight"] in {"binding","persuasive","nonprecedential","historical","text","case_specific"},"invalid claimed legal weight")
        if iscase:
            if pr["weight"]=="binding":
                need(r["court_level"] in {"scotus","ca9","state_highest"} and r["publication"]=="published" and r["opinion_kind"] in {"majority","per_curiam","combined_reviewed"} and pr["character"]=="holding","invalid binding precedent")
                if r["court_level"]=="state_highest":need(pr.get("controlling_state_law_reviewed") is True,"state-law scope review required")
            if r["opinion_kind"] in {"concurrence","dissent","plurality"}:need(pr["weight"]!="binding","separate/plurality not binding automatically")
            if r["publication"]!="published":need(pr["weight"]!="binding","unpublished not binding precedent")
        else:need(pr["weight"] in {"text","historical"} and pr["character"]=="text","noncase authority weight")
        if pr["status"] in NEG:need(pr["weight"]=="historical","invalid operative weight for displaced proposition")
    searches=table(r["searches"],"treatment searches")
    required={"direct_history","negative_treatment","later_citing"} if iscase else {"version_history","amendments"}
    need(required<={s["kind"] for s in searches.values()},"missing treatment research lanes")
    for s in searches.values():
        required_text(s,["provider","query","scope","limitations"])
        need(day(s["searched_at"])>=cutoff and s["through"]==cutoff.isoformat(),"search cutoff not recorded")
        need(type(s["hits_reviewed"]) is int and s["hits_reviewed"]>=0,"invalid reviewed result count")
        need(s["coverage"] in {"bounded","partial","complete_returned_set"},"invalid coverage")
        need(s["unresolved_material_candidates"]==[],"material treatment candidates unresolved")
    for t in r["treatments"]:
        need(t["search_id"] in searches and t["pin_id"] in pins,"unmapped treatment")
        need(day(a["decided_at"])<=day(t["date"])<=cutoff,"treatment outside temporal scope")
        required_text(t,["citation","court","locator","quote","analysis"])
        need(t["relation"] in NEG|{"followed","distinguished","limited","criticized","mentioned","amended","cert_denied"},"invalid treatment relation")
        segment(source(root,t["source"],prefix,hashes),t["locator"],t["quote"])
        pr=reviews[t["pin_id"]]
        if t["relation"] in NEG and t["operative"] is True:need(pr["status"]==t["relation"],"operative adverse treatment inconsistent with pin status")
        if t["relation"]=="limited" and t["operative"] is True:need(pr["status"] in {"limited"}|NEG,"limitation not reflected")
    return reviews

def validate_use(a,r,pr,u):
    purpose=u.get("purpose",u.get("use"))
    need(not (u.get("use")=="support" and purpose!="support"),"support cannot be disguised as historical use")
    need(purpose in USE and nonblank(u.get("analysis")),"unreviewed authority use")
    weight=u.get("claimed_weight")
    need(weight==pr["weight"],"citation misstates reviewed weight")
    if pr["status"] in NEG:need(purpose in {"adverse","history","distinguish"},"displaced proposition used as operative support")
    if pr["status"]=="limited" and purpose=="support":need(nonblank(u.get("limitation_application")),"limited proposition application missing")
    if a["authority_type"]=="case" and r["publication"]=="unpublished":
        if r["court_level"]=="ca9" and day(a["decided_at"])<date(2007,1,1):
            need(purpose in {"preclusion","factual","conflict_rehearing"} and nonblank(u.get("exception_basis")),"pre-2007 CA9 unpublished citation restricted")
        if purpose in {"preclusion","factual","conflict_rehearing"}:need(nonblank(u.get("exception_basis")),"exception needs reviewed rule basis")
    if purpose=="support":need(weight not in {"historical","case_specific"},"historical/case-specific authority not general support")

def audit_document(page_map, audit, authorities, reviews, uses):
    required_text(audit,["reviewer","method","scope"])
    need(audit["status"]=="passed" and audit["unresolved"]==[],"citation audit unresolved")
    refs=table(audit["occurrences"],"citation occurrences")
    need(len({(r["page"],r["offset"]) for r in refs.values()})==len(refs),"duplicate citation occurrence offset")
    tagged={(n,x,y) for n,t in page_map.items() for x,y in LEGAL.findall(t)}
    mapped={(u["page"],u["authority_id"],u["pin_id"]) for u in uses}
    need(tagged==mapped,"page-level authority annotations mismatch")
    used=set()
    for ref in refs.values():
        n=ref["page"];txt=page_map[n];a=authorities[ref["authority_id"]];r=reviews[a["id"]]
        need(ref["pin_id"] in {p["id"] for p in a["pins"]},"audit pin unknown")
        if ref["form"]=="full" and a["authority_type"]=="case":need(r["identity_lookup"]["matched_citation"] in ref["text"],"full case citation does not match verified reporter")
        need(nonblank(ref["text"]) and ref["text"] in txt and ref["form"] in {"full","short","id","supra","statute","rule","other"},"audit occurrence absent")
        need((n,a["id"],ref["pin_id"]) in mapped,"occurrence lacks page use")
        if ref["form"] in {"id","short","supra"}:
            prev=refs.get(ref.get("antecedent_id"))
            need(prev and prev["authority_id"]==ref["authority_id"] and (prev["page"],prev["offset"])<(n,ref["offset"]),"unresolved short citation antecedent")
        need(type(ref["offset"]) is int and txt[ref["offset"]:ref["offset"]+len(ref["text"])]==ref["text"],"citation offset mismatch")
        used.add((n,a["id"],ref["pin_id"]))
    need(used==mapped,"authority use lacks occurrence audit")
    for n,txt in page_map.items():
        for m in list(REPORTER.finditer(txt))+list(SHORT.finditer(txt)):
            need(any(x["page"]==n and x["offset"]<=m.start() and x["offset"]+len(x["text"])>=m.end() for x in refs.values()),"unreviewed reporter/short cite on page "+str(n))

def validate_research(root,research,authorities,page_maps,uses,cutoff,prefix,hashes):
    need(research["schema_version"]==1 and research["cutoff"]==cutoff.isoformat(),"research packet version/cutoff")
    reviews=table(research["authority_reviews"],"authority reviews")
    need(set(reviews)==set(authorities),"authority review inventory mismatch")
    pin_reviews={i:validate_authority(root,a,reviews[i],cutoff,prefix,hashes) for i,a in authorities.items()}
    for u in uses:
        a=authorities[u["authority_id"]];r=reviews[a["id"]]
        validate_use(a,r,pin_reviews[a["id"]][u["pin_id"]],u)
    audits=table(research["document_audits"],"document audits")
    need(set(audits)==set(page_maps),"document citation audit inventory mismatch")
    for d,m in page_maps.items():audit_document(m,audits[d],authorities,reviews,[u for u in uses if u["document_id"]==d])
    return {"authorities":len(authorities),"audited_documents":len(audits),"uses":len(uses)}

def validate_packet(root,path,digest,doc,cutoff,expected_hashes=None):
    p=load(safe(root,path))
    prefix=f'law/research/{key(doc["case_id"])}/{key(doc["id"])}/'
    need(p["schema_version"]==1 and path==prefix+"packet.json" and p["case_id"]==doc["case_id"] and p["document_id"]==doc["id"],"research packet scope mismatch")
    need(canonical(p)==digest and p["document_sha256"] in {"server_computed",doc["sha256"]},"research packet/document changed")
    txt=safe(root,doc["path"]).read_text(encoding="utf-8")
    auth=table(p["authorities"],"packet authorities")
    hashes={}
    validate_research(root,p["research"],auth,{doc["id"]:pages(txt)},p["uses"],day(cutoff),prefix,hashes)
    need(auth or nonblank(p.get("no_authority_reason")) and not p["uses"],"empty packet needs reviewed reason")
    if expected_hashes is not None:need(hashes==expected_hashes,"research source inventory/hash changed")
    return hashes
