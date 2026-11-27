"""Detect mutation/deletion of prior history, except the explicitly authorized one-time campaign reset."""
import subprocess
import sys

MIGRATION_PARENT = "83f43a479856238c014c07984344a08cdc775c80"
MIGRATION_DELETIONS = ["D\treceipts/REQ-20261024-maine-start-01.json","D\trequests/REQ-20261024-maine-start-01.json","D\tsaves/S0002-maine-start-civil01/events.json","D\tsaves/S0002-maine-start-civil01/manifest.json","D\tsaves/S0002-maine-start-civil01/state.json"]
def audit(base):
    result = subprocess.run(["git", "diff", "--name-status", "--no-renames", base, "HEAD", "--",
                             "saves/", "receipts/", "requests/"], text=True, capture_output=True, check=True)
    bad = [line for line in result.stdout.splitlines() if not line.startswith("A\t")]
    audit_factory(base)
    base_sha = subprocess.check_output(["git", "rev-parse", base], text=True).strip()
    # Exact prior SHA and exact deletion set only; not a general history rewrite exemption.
    if base_sha == MIGRATION_PARENT and sorted(bad) == sorted(MIGRATION_DELETIONS):
        print("Authorized federal-only campaign reset; old campaign archived")
        return
    if bad:
        raise ValueError("Immutable history modified: " + ", ".join(bad))

def audit_factory(base):
    import json
    prior=subprocess.check_output(["git","ls-tree","-r","--name-only",base,"--","factory/"],text=True).splitlines()
    for path in prior:
        if not path.endswith("/release.json"):continue
        raw=subprocess.check_output(["git","show",f"{base}:{path}"])
        release=json.loads(raw)
        paths=[path,*release["files"]]
        for p in paths:
            before=subprocess.check_output(["git","show",f"{base}:{p}"])
            after=subprocess.check_output(["git","show",f"HEAD:{p}"])
            if before!=after:raise ValueError("Sealed factory file changed: "+p)

if __name__ == "__main__":
    audit(sys.argv[1])
    print("PASS: history audit")

