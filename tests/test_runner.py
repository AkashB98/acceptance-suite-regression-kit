import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import criterion, p95, run_version
from suite import generate_suite

class TestRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suite = generate_suite()
        cls.v1 = run_version(cls.suite, "v1")
        cls.v2 = run_version(cls.suite, "v2")
        cls.v1b = run_version(cls.suite, "v1b")
    def test_v1_accepted(self):
        self.assertEqual(self.v1["verdict"], "ACCEPTED")
        self.assertEqual(self.v1["average_success"], 0.933333)
    def test_v2_higher_average_but_rejected(self):
        self.assertGreater(self.v2["average_success"], self.v1["average_success"])
        self.assertEqual(self.v2["average_success"], 0.966667)
        self.assertEqual(self.v2["verdict"], "REJECTED")
    def test_v2_rejection_is_zero_tolerance_billing_pii(self):
        z = criterion(self.v2, "zero_tolerance")
        self.assertFalse(z["passed"])
        self.assertEqual(z["details"]["failed_cases"],
                         [{"id": "BIL-010", "slice": "billing", "failure_class": "pii_leak"}])
        self.assertTrue(criterion(self.v2, "per_slice_success_floor")["passed"])
        self.assertTrue(criterion(self.v2, "latency_p95")["passed"])
    def test_v1b_identical_to_v1(self):
        self.assertEqual(self.v1["cases"], self.v1b["cases"])
        self.assertEqual(self.v1["average_success"], self.v1b["average_success"])
    def test_report_records_suite_version_and_hash(self):
        self.assertEqual(self.v1["suite_version"], "1.0.0")
        self.assertEqual(len(self.v1["suite_hash"]), 64)
    def test_no_weighted_score_field(self):
        self.assertNotIn("score", self.v1)
        self.assertEqual(len(self.v1["criteria"]), 3)
    def test_p95_hand_computed(self):
        self.assertEqual(p95(list(range(1, 21))), 19)
        self.assertEqual(p95([5]), 5)
    def test_unknown_version_raises(self):
        with self.assertRaises(ValueError):
            run_version(self.suite, "v99")
    def test_deterministic_run(self):
        self.assertEqual(run_version(self.suite, "v2"), self.v2)
if __name__ == "__main__": unittest.main()
