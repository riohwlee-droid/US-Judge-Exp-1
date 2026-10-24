"""Run by GitHub Actions: validate chat-authored JSON requests and publish receipts.

No network, AI call, secret, dynamic import or executable field in a request.
Git commit/push is handled by the workflow after this script succeeds.
"""
from copy import deepcopy
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from judgesim.engine import Invalid, apply_batch, require, identifier
from judgesim.storage import read_json, write_json, verify, profiles, safe, sha, write_checkpoint


def process(root):
    root = Path(root)
    verify(root)
    results = []
    for path in sorted((root / "requests").glob("*.json")):
        request_id = identifier(path.stem)
        receipt_path = root / "receipts" / f"{request_id}.json"
        if receipt_path.exists():
            require(read_json(receipt_path)["request_sha256"] == sha(path), "processed request was modified")
            continue
        receipt = {"schema_version": 1, "request_id": request_id, "request_sha256": sha(path)}
        try:
            packet = read_json(path)
            require(packet["schema_version"] == 1 and packet["request_id"] == request_id, "request ID/version mismatch")
            identifier(packet["checkpoint"])
            state = verify(root)
            pointer = read_json(root / "CURRENT.json")
            require(packet["base_checkpoint"] == pointer["checkpoint"] and
                    packet["base_revision"] == state["revision"], "stale base: reload CURRENT and rebase events")
            require(isinstance(packet["events"], list) and packet["events"], "empty or invalid event batch")
            events = deepcopy(packet["events"])
            for event in events:
                if event["type"] == "document.register":
                    doc = event["payload"]["document"]
                    if doc["sha256"] == "server_computed":
                        doc["sha256"] = sha(safe(root, doc["path"]))
            result = apply_batch(state, events, profiles(root))
            # Document/inventory checks happen before a production pointer is written.
            import shutil
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                shutil.copytree(root, tmp, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".git", "__pycache__"))
                write_checkpoint(tmp, packet["checkpoint"], result, events, pointer["checkpoint"], state)
                verify(tmp)
            write_checkpoint(root, packet["checkpoint"], result, events, pointer["checkpoint"], state)
            verify(root)
            receipt.update(status="accepted", checkpoint=packet["checkpoint"], revision=result["revision"])
        except (Invalid, ValueError, KeyError, TypeError, OSError) as exc:
            receipt.update(status="rejected", reason=str(exc))
        write_json(receipt_path, receipt)
        results.append({"request_id": request_id, "status": receipt["status"]})
    verify(root)
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(process(Path(__file__).resolve().parents[1]), ensure_ascii=False))
