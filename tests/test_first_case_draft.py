"""Real drafted originals, not synthetic stress text. No seal/admission assertions."""
import unittest
from pathlib import Path
from judgesim.case_factory import compile_package, load, pages, words, safe
ROOT=Path(__file__).resolve().parents[1]
BP="factory/CA9-26-001/v1/blueprint.json"

class FirstCaseDraft(unittest.TestCase):
    def test_world_procedure(self):
        for stage in ("world","procedure"):
            self.assertEqual(compile_package(ROOT,BP,stage)["stage"],stage)
    def test_record_and_excerpts(self):
        for stage in ("record","excerpts"):
            self.assertEqual(compile_package(ROOT,BP,stage)["stage"],stage)
    def test_original_depth_and_excerpts(self):
        b=load(ROOT/BP)
        orig=[d for d in b["documents"] if d["kind"] not in {"er_volume","ser_volume","fer_volume","er_index"}]
        total=0
        for d in b["documents"]:
            p=pages(safe(ROOT,d["path"]).read_text())
            self.assertEqual(len(p),d["pages"])
            if d in orig:total+=sum(words(t) for t in p.values())
        self.assertGreaterEqual(sum(d["pages"] for d in orig),200)
        self.assertGreaterEqual(total,24000)
        print("Draft record:",len(orig),"original documents,",sum(d["pages"] for d in orig),"original pages,",total,"words")
    def test_no_release_before_review(self):
        b=load(ROOT/BP)
        if b["unresolved_blockers"]:
            self.assertFalse((ROOT/BP).with_name("release.json").exists())
            self.assertFalse((ROOT/BP).with_name("seal-request.json").exists())
