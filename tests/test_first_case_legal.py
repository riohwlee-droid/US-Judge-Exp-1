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
