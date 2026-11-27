"""Audit every actual first-case logical page, citation and source map without granting release."""
from pathlib import Path
import sys,json,re
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from judgesim.case_factory import compile_package,check_release,load,pages,safe,words,hash_bytes,LEGAL,ER,norm
from judgesim.legal_research import REPORTER,SHORT
ROOT=Path(__file__).resolve().parents[1]
BP="factory/CA9-26-001/v1/blueprint.json"
def audit(root=ROOT):
    b=load(root/BP);docs={d["id"]:d for d in b["documents"]};maps={};hashes={}
    for id,d in docs.items():
        raw=safe(root,d["path"]).read_bytes();maps[id]=pages(raw.decode());hashes[id]=hash_bytes(raw)
        assert len(maps[id])==d["pages"]
    for stage in ("world","procedure","record","excerpts"):
        compile_package(root,BP,stage=stage)
    ex={f'{e["volume"]}-ER-{e["citation_page"]}':e for e in b["excerpts"]}
    assert len(ex)==190
    for e in ex.values():
        assert maps[e["excerpt_document_id"]][e["excerpt_page"]]==maps[e["source_document_id"]][e["source_page"]]
    brief_ids={i for i,d in docs.items() if d["kind"] in {"opening_brief","answering_brief","reply_brief"}}
    actual={(i,n,c) for i in brief_ids for n,t in maps[i].items() for c in ER.findall(t)}
    annotated={(r["document_id"],r["page"],r["cite"]) for r in b["brief_record_refs"]}
    assert actual==annotated and len(annotated)==len(b["brief_record_refs"])
    for r in b["brief_record_refs"]:
        e=ex[r["cite"]]
        assert e["source_document_id"]==r["source_document_id"] and e["source_page"]==r["source_page"]
        assert norm(r["quote"]) in norm(maps[e["source_document_id"]][e["source_page"]])
    auth={a["id"]:a for a in b["authorities"]}
    original={i for i,d in docs.items() if d["kind"] not in {"er_volume","er_index","ser_volume","fer_volume"}}
    audits={a["id"]:a for a in b["research"]["document_audits"]}
    assert set(audits)==original
    occcount=0;unmapped=[]
    for i in original:
        tagged={(n,x,y) for n,t in maps[i].items() for x,y in LEGAL.findall(t)}
        seen=set()
        for o in audits[i]["occurrences"]:
            t=maps[i][o["page"]];a=auth[o["authority_id"]]
            assert t[o["offset"]:o["offset"]+len(o["text"])]==o["text"]==a["citation"]
            seen.add((o["page"],o["authority_id"],o["pin_id"]))
            occcount+=1
        assert tagged==seen
        for n,t in maps[i].items():
            for m in list(REPORTER.finditer(t))+list(SHORT.finditer(t)):
                if not any(o["page"]==n and o["offset"]<=m.start() and o["offset"]+len(o["text"])>=m.end() for o in audits[i]["occurrences"]):
                    unmapped.append({"document":i,"page":n,"text":m.group()})
    # Check the audit arithmetic independently of the narrative, against actual export rows.
    log=maps["CA9-26-001-LOG"]
    maren=[line for n in (4,5,6) for line in log[n].splitlines() if re.match(r"AQ-\d+ \|",line)]
    assert len(maren)==12 and len({x.split(" | ")[0] for x in maren})==12
    assert sum("resolved" in x and "open:" not in x for x in maren)==8
    assert sum("open:" in x for x in maren)==4
    assert sum("disputed authorization" in x for x in maren)==2
    bell=[x for x in log[7].splitlines() if re.match(r"AQ-\d+ \|",x)]
    assert len(bell)==4 and sum("open:" in x for x in bell)==2
    # A compiled candidate and an actual immutable release are different states.
    ready=False
    if not b["unresolved_blockers"]:
        compile_package(root,BP,stage="review")
        ready=True
    rp=str(Path(BP).with_name("release.json"))
    sealed=(root/rp).exists()
    if sealed:check_release(root,rp)
    return {"original_docs":len(original),"original_pages":sum(len(maps[i]) for i in original),"original_words":sum(words(t) for i in original for t in maps[i].values()),"excerpt_pages":len(ex),"index_pages":len(maps["CA9-26-001-IDX"]),"total_pages":sum(map(len,maps.values())),"record_cite_page_occurrences":len(actual),"legal_occurrences":occcount,"unmapped_common_reporter_or_short_citations":unmapped,"file_sha256":hashes,"material_blockers":b["unresolved_blockers"],"release_ready":ready,"sealed":sealed}
if __name__=="__main__":print(json.dumps(audit(),indent=2))
