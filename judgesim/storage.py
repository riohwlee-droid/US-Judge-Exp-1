"""Immutable checkpoints plus a small publication pointer; standard library only."""
from pathlib import Path
import hashlib
import json
import re
from .engine import Invalid, apply_batch, digest, initial_state, require, validate_state, reference


def no_duplicates(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, f"duplicate JSON key: {key}")
        obj[key] = value
    return obj


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=no_duplicates,
                      parse_constant=lambda x: (_ for _ in ()).throw(Invalid(f"invalid JSON number: {x}")))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe(root, relative):
    require(isinstance(relative, str) and not Path(relative).is_absolute(), "unsafe repository path")
    require(".." not in Path(relative).parts, "path traversal")
    result = (Path(root) / relative).resolve()
    require(result.is_relative_to(Path(root).resolve()), "path escapes repository")
    return result


def profiles(root):
    return read_json(Path(root) / "courts/profiles.json")["profiles"]


def check_documents(root, state):
    paths = set()
    for doc in state["documents"].values():
        require(doc["path"] not in paths, "documents must have unique immutable paths")
        paths.add(doc["path"])
        path = safe(root, doc["path"])
        require(path.is_file(), f"missing original: {doc['path']}")
        require(sha(path) == doc["sha256"], f"original content changed: {doc['id']}")
        markers = re.findall(r"^<!-- PAGE ([1-9][0-9]*) -->$", path.read_text(encoding="utf-8"), re.M)
        require(markers == [str(n) for n in range(1, doc["pages"] + 1)], "invalid stable page markers")
        if doc.get("supersedes"):
            require(doc["supersedes"] in state["documents"], "missing original correction target")
        for citation in doc.get("citations", []):
            reference(state, citation)
    for case in state["cases"].values():
        require(case.get("initial_document_ids"), "complete case lacks initial record inventory")
        for key in case["initial_document_ids"]:
            require(key in state["documents"] and state["documents"][key]["case_id"] == case["id"],
                    "initial record is incomplete")


def verify(root, pointer_path="CURRENT.json", allow_training=False):
    root = Path(root)
    pointer = read_json(safe(root, pointer_path))
    profile_map = profiles(root)
    source_map = {s["id"]: s for s in read_json(root / "law/sources.json")["sources"]}
    for profile in profile_map.values():
        if profile["status"] == "ready":
            for source_id in profile["source_ids"]:
                require(source_id in source_map, "court cites missing source")
                require(source_map[source_id]["review_depth"] == "court_specific",
                        "overview sources cannot make a court ready")
    chain = []
    seen = set()
    checkpoint = pointer["checkpoint"]
    while checkpoint:
        require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", checkpoint) is not None, "bad checkpoint ID")
        require(checkpoint not in seen, "checkpoint cycle")
        seen.add(checkpoint)
        base = f"saves/{checkpoint}"
        manifest_path = safe(root, f"{base}/manifest.json")
        manifest = read_json(manifest_path)
        require(manifest["id"] == checkpoint and manifest["schema_version"] == 1, "bad checkpoint manifest")
        require(manifest["state_path"] == f"{base}/state.json" and manifest["events_path"] == f"{base}/events.json",
                "checkpoint paths must stay in their own directory")
        if not chain:
            require(sha(manifest_path) == pointer["manifest_sha256"], "pointer/manifest hash mismatch")
        if manifest["parent"]:
            parent_path = safe(root, f"saves/{manifest['parent']}/manifest.json")
            require(sha(parent_path) == manifest["parent_manifest_sha256"], "parent manifest changed")
        state = read_json(safe(root, manifest["state_path"]))
        events = read_json(safe(root, manifest["events_path"]))
        require(isinstance(events, list), "events must be a list")
        require(digest(state) == manifest["state_digest"] and digest(events) == manifest["events_digest"],
                "checkpoint digest mismatch")
        require(state["revision"] == manifest["revision"], "revision mismatch")
        chain.append((manifest, state, events))
        checkpoint = manifest["parent"]
    require(chain, "empty save chain")
    previous = initial_state()
    previous_id = None
    for manifest, state, events in reversed(chain):
        require(manifest["parent"] == previous_id, "broken parent chain")
        require(manifest["base_revision"] == previous["revision"], "stale base revision")
        replayed = apply_batch(previous, events, profile_map, allow_training)
        require(replayed == state, "saved state differs from event replay")
        validate_state(state, profile_map, allow_training)
        check_documents(root, state)
        for key, old in previous["documents"].items():
            require(state["documents"].get(key) == old, "existing document registration was modified")
        previous, previous_id = state, manifest["id"]
    require(previous["revision"] == pointer["revision"], "pointer revision mismatch")
    return previous


def write_checkpoint(root, checkpoint_id, state, events, parent=None, parent_state=None,
                     pointer_path="CURRENT.json"):
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", checkpoint_id) is not None, "bad checkpoint ID")
    root = Path(root)
    base = f"saves/{checkpoint_id}"
    require(not safe(root, base).exists(), "checkpoint is immutable; use a new identifier")
    manifest = {"schema_version": 1, "id": checkpoint_id, "parent": parent,
        "parent_manifest_sha256": sha(safe(root, f"saves/{parent}/manifest.json")) if parent else None,
        "base_revision": parent_state["revision"] if parent_state else 0,
        "revision": state["revision"], "state_path": f"{base}/state.json",
        "events_path": f"{base}/events.json", "state_digest": digest(state), "events_digest": digest(events)}
    write_json(safe(root, manifest["state_path"]), state)
    write_json(safe(root, manifest["events_path"]), events)
    write_json(safe(root, f"{base}/manifest.json"), manifest)
    pointer = {"schema_version": 1, "checkpoint": checkpoint_id, "revision": state["revision"],
               "manifest_sha256": sha(safe(root, f"{base}/manifest.json"))}
    write_json(safe(root, pointer_path), pointer)
    return pointer
