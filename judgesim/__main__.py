import argparse
import json
import sys
from .engine import Invalid, apply_batch, require, view
from .storage import profiles, read_json, verify, write_checkpoint


def main():
    parser = argparse.ArgumentParser(description="US Judge Experience: storage checks without an AI API")
    parser.add_argument("command", choices=["verify", "resume", "apply"])
    parser.add_argument("--root", default=".")
    parser.add_argument("--pointer", default="CURRENT.json")
    parser.add_argument("--packet")
    args = parser.parse_args()
    try:
        state = verify(args.root, args.pointer)
        if args.command == "verify":
            print(f"PASS: revision={state['revision']} status={state['campaign']['status']}")
        elif args.command == "resume":
            print(json.dumps(view(state), ensure_ascii=False, indent=2))
        else:
            require(args.packet, "--packet is required")
            packet = read_json(args.packet)
            current = read_json(f"{args.root}/{args.pointer}")
            require(packet["base_checkpoint"] == current["checkpoint"] and
                    packet["base_revision"] == state["revision"], "stale packet: reload latest save")
            result = apply_batch(state, packet["events"], profiles(args.root))
            # Preflight the entire candidate in a temporary copy before touching live files.
            import shutil
            import tempfile
            with tempfile.TemporaryDirectory() as temp:
                shutil.copytree(args.root, temp, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git", "__pycache__"))
                write_checkpoint(temp, packet["checkpoint"], result, packet["events"],
                    current["checkpoint"], state, args.pointer)
                verify(temp, args.pointer)
            write_checkpoint(args.root, packet["checkpoint"], result, packet["events"],
                current["checkpoint"], state, args.pointer)
            verify(args.root, args.pointer)
            print(f"LOCAL CANDIDATE READY: revision={result['revision']}; publish and read back on GitHub")
        return 0
    except (Invalid, KeyError, TypeError, ValueError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
