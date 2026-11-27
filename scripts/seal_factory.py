"""Server-only declaration processor for pre-admission releases."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from judgesim.case_factory import load, compile_package, check_release, release_path, safe, canonical, need
def process(root):
    root=Path(root);out=[]
    for q in sorted((root/"factory").glob("*/*/seal-request.json")):
        request=load(q)
        expected=str(q.parent.relative_to(root)/"blueprint.json")
        need(request=={"schema_version":1,"blueprint_path":expected,"action":"seal"},"invalid seal declaration")
        dest=q.parent/"release.json"
        if dest.exists():
            check_release(root,str(dest.relative_to(root)))
            continue
        r=compile_package(root,expected)
        with dest.open("x",encoding="utf-8") as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write("\n")
        out.append({"path":str(dest.relative_to(root)),"digest":canonical(r),"summary":r["summary"]})
    return out
if __name__=="__main__":print(json.dumps(process(Path(__file__).resolve().parents[1]),indent=2))
