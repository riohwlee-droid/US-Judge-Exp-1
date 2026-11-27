"""Generate faithful logical-page ER copies from planned source mappings, never overwrite."""
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from judgesim.case_factory import load,safe,pages,need,table,compile_package
def render(root,path):
    compile_package(root,path,stage="procedure")
    b=load(safe(root,path));docs=table(b["documents"],"documents")
    sets=defaultdict(dict);index=[]
    for e in b["excerpts"]:
        d=docs[e["excerpt_document_id"]];src=docs[e["source_document_id"]]
        need(src["access"]=="judge","cannot excerpt hidden material")
        n=e["excerpt_page"];need(n not in sets[d["id"]],"duplicate excerpt page")
        sets[d["id"]][n]=pages(safe(root,src["path"]).read_text(encoding="utf-8"))[e["source_page"]]
        typ={"er_volume":"ER","ser_volume":"SER","fer_volume":"FER"}[d["kind"]]
        single=typ=="ER" and sum(x["kind"]=="er_volume" for x in docs.values())==1
        citation_page=e.get("citation_page",n)
        cite=f"ER-{citation_page}" if single else f'{e["volume"]}-{typ}-{citation_page}'
        index.append(f'{cite} — {src["title"]}, source page {e["source_page"]}')
    for id,rows in sets.items():
        need(set(rows)==set(range(1,docs[id]["pages"]+1)),"excerpt inventory mismatch")
        p=safe(root,docs[id]["path"]);p.parent.mkdir(parents=True,exist_ok=True)
        with p.open("x",encoding="utf-8") as f:
            for n,txt in sorted(rows.items()):f.write(f"<!-- PAGE {n} -->\n{txt}\n\n")
    # Index intentionally authored in planned pages; print exact rows for author.
    return index
if __name__=="__main__":
    print("\n".join(render(Path(__file__).resolve().parents[1],sys.argv[1])))
