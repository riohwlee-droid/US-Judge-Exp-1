"""Detect mutation/deletion of previously committed checkpoints and receipts."""
import subprocess
import sys


def audit(base):
    result = subprocess.run(["git", "diff", "--name-status", "--no-renames", base, "HEAD", "--",
                             "saves/", "receipts/", "requests/"], text=True, capture_output=True, check=True)
    bad = [line for line in result.stdout.splitlines() if not line.startswith("A\t")]
    if bad:
        raise ValueError("Immutable history modified: " + ", ".join(bad))


if __name__ == "__main__":
    audit(sys.argv[1])
    print("PASS: prior checkpoints, processed/unprocessed requests and receipts are append-only")
