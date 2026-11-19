import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from compare import compare_reports, render_markdown_diff
from runner import run_version
from suite import generate_suite

class TestCompare(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suite = generate_suite()
        cls.v1 = run_version(cls.suite, "v1")
        cls.v2 = run_version(cls.suite, "v2")
        cls.v1b = run_version(cls.suite, "v1b")
    def test_v1_to_v2_single_zero_tolerance_flip(self):
        d = compare_reports(self.v1, self.v2)
        self.assertEqual(d["status"], "COMPARED")
        self.assertEqual(len(d["flips"]), 1)
        flip = d["flips"][0]
        self.assertEqual(flip["criterion"], "zero_tolerance")
        self.assertEqual((flip["from"], flip["to"]), ("pass", "fail"))
        self.assertEqual([e["id"] for e in flip["evidence"]], ["BIL-010"])
    def test_v1_to_v1b_zero_flips(self):
        d = compare_reports(self.v1, self.v1b)
        self.assertEqual(d["flips"], [])
        self.assertEqual(d["verdict_from"], d["verdict_to"])
    def test_version_mismatch_refused(self):
        other = run_version(generate_suite("1.1.0"), "v1")
        d = compare_reports(self.v1, other)
        self.assertEqual(d["status"], "REFUSED")
        self.assertEqual(d["reason"], "suite drift, not agent drift")
    def test_hash_mismatch_refused(self):
        s2 = generate_suite(); s2["cases"] = s2["cases"][:-1] + [dict(s2["cases"][-1], id="ONB-099")]
        other = run_version(s2, "v1")
        self.assertEqual(compare_reports(self.v1, other)["status"], "REFUSED")
    def test_markdown_diff_mentions_flip_and_evidence(self):
        md = render_markdown_diff(compare_reports(self.v1, self.v2))
        self.assertIn("zero_tolerance", md); self.assertIn("BIL-010", md)
        self.assertIn("REJECTED", md)
    def test_markdown_refusal(self):
        other = run_version(generate_suite("2.0.0"), "v1")
        md = render_markdown_diff(compare_reports(self.v1, other))
        self.assertIn("suite drift, not agent drift", md)
if __name__ == "__main__": unittest.main()
