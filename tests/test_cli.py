import io, json, os, sys, tempfile, unittest
from contextlib import redirect_stdout
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cli import main

class TestCli(unittest.TestCase):
    def test_demo_exit_zero_and_deterministic(self):
        outs = []
        for _ in range(2):
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(["demo"])
            self.assertEqual(code, 0); outs.append(buf.getvalue())
        self.assertEqual(outs[0], outs[1])
        self.assertIn("REJECTED", outs[0])
    def test_run_and_compare_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = os.path.join(tmp, "v1.json"), os.path.join(tmp, "v2.json")
            md = os.path.join(tmp, "diff.md")
            self.assertEqual(main(["run", "--version", "v1", "--out", a]), 0)
            self.assertEqual(main(["run", "--version", "v2", "--out", b]), 0)
            self.assertEqual(main(["compare", "--from-report", a, "--to-report", b, "--markdown", md]), 0)
            with open(md, encoding="utf-8") as fh: text = fh.read()
            self.assertIn("BIL-010", text)
            with open(a, encoding="utf-8") as fh: report = json.load(fh)
            self.assertEqual(report["verdict"], "ACCEPTED")
    def test_run_missing_suite_is_error_exit_2(self):
        self.assertEqual(main(["run", "--version", "v1", "--suite", "/tmp/no-such-suite-xyz.json"]), 2)
if __name__ == "__main__": unittest.main()
