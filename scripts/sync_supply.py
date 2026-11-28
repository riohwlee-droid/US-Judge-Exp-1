"""Reconcile production stock after official save, seal or creator request."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from judgesim.supply import sync
if __name__=="__main__":print(json.dumps(sync(Path(__file__).resolve().parents[1]),indent=2))
