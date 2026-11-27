import unittest
from pathlib import Path
from judgesim.case_factory import compile_package
ROOT=Path(__file__).resolve().parents[1]
BP="factory/CA9-26-001/v1/blueprint.json"
class ActualLegalReview(unittest.TestCase):
    def test_full_production_briefs(self):
        result=compile_package(ROOT,BP,stage="briefs")
        self.assertEqual(result["research"]["authorities"],13)
        print("Production legal review:",result["research"])
    def test_full_review_and_seal_if_present(self):
        from judgesim.case_factory import check_release
        result=compile_package(ROOT,BP)
        self.assertEqual(result["case_id"],"CA9-26-001")
        self.assertEqual(len(result["documents"]),33)
        rp=str(Path(BP).with_name("release.json"))
        if (ROOT/rp).exists():self.assertEqual(check_release(ROOT,rp),result)
