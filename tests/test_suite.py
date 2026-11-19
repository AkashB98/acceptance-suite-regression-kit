import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from suite import case_set_hash, generate_suite, validate_suite

class TestSuite(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(generate_suite(), generate_suite())
    def test_counts(self):
        s = generate_suite()
        self.assertEqual(len(s["cases"]), 60)
        self.assertEqual(s["suite_version"], "1.0.0")
        from collections import Counter
        self.assertEqual(Counter(c["slice"] for c in s["cases"]),
                         {"support": 20, "billing": 20, "onboarding": 20})
    def test_pii_probes_per_slice(self):
        s = generate_suite()
        pii = [c for c in s["cases"] if c["failure_class"] == "pii_leak"]
        self.assertEqual(len(pii), 12)
        self.assertIn("BIL-010", {c["id"] for c in pii})
    def test_valid_suite_no_issues(self):
        self.assertEqual(validate_suite(generate_suite()), [])
    def test_hash_stable_and_version_independent(self):
        self.assertEqual(case_set_hash(generate_suite()),
                         case_set_hash(generate_suite("9.9.9")))
    def test_hash_changes_with_cases(self):
        s = generate_suite(); s["cases"] = s["cases"][:-1]
        self.assertNotEqual(case_set_hash(s), case_set_hash(generate_suite()))
    def test_validate_rejects_duplicate_ids(self):
        s = generate_suite(); s["cases"][1]["id"] = s["cases"][0]["id"]
        self.assertTrue(validate_suite(s))
if __name__ == "__main__": unittest.main()
