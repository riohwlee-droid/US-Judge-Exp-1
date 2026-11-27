"""Compile staged case or freeze a validated release (no LLM/network)."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from judgesim.case_factory import compile_package,release_path,check_release,safe,canonical,STAGES
def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=["check","seal","verify"])
    p.add_argument("path")
    p.add_argument("--stage",choices=STAGES,default="review")
    p.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    p.add_argument("--training",action="store_true")
    a=p.parse_args()
    if a.command=="verify":
        r=check_release(a.root,a.path,training=a.training)
    else:
        r=compile_package(a.root,a.path,stage=a.stage if a.command=="check" else "review",training=a.training)
        if a.command=="seal":
            dest=safe(a.root,release_path(r["case_id"],r["version"]))
            with dest.open("x",encoding="utf-8") as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write("\n")
    print(json.dumps({"result":r.get("summary",r),"release_digest":canonical(r) if "files" in r else None},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
