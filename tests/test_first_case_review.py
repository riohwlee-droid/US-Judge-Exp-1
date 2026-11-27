import unittest
from scripts.audit_first_case import ROOT,BP
from judgesim.case_factory import load
from scripts.audit_first_case import audit
class FullPageAudit(unittest.TestCase):
    def test_all_actual_pages_and_citation_anchors(self):
        a=audit()
        self.assertEqual(a["total_pages"],430)
        self.assertEqual(a["original_pages"],233)
        self.assertEqual(a["excerpt_pages"],190)
        self.assertEqual(a["record_cite_page_occurrences"],92)
        self.assertGreater(a["legal_occurrences"],30)
        self.assertFalse(a["unmapped_common_reporter_or_short_citations"])
        self.assertEqual(a["release_ready"],not load(ROOT/BP)["unresolved_blockers"])
        b=load(ROOT/BP)
        self.assertEqual({f['id'] for f in b['facts']},{x['fact_id'] for x in b['assertions']})
        self.assertEqual(len(b['timeline']),42)
        self.assertEqual(sum(t['time_precision']=='recorded' for t in b['timeline']),18)
        print("Full-page review summary:",{k:v for k,v in a.items() if k not in {"file_sha256","material_blockers"}})
