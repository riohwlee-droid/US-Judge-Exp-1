"""Inspect a research packet independently of gameplay."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from judgesim.legal_research import validate_packet
from judgesim.case_factory import canonical,load
root=Path(__file__).resolve().parents[1]
if __name__=="__main__":
    path,docpath,cutoff=sys.argv[1:4]
    p=load(root/path);d=load(root/docpath)
    hashes=validate_packet(root,path,canonical(p),d,cutoff)
    print(json.dumps({"status":"structurally_valid","digest":canonical(p),"source_hashes":hashes,"authority_count":len(p["authorities"])}))
