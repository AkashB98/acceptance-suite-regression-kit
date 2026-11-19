import os, socket, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from compare import compare_reports
from runner import run_version
from suite import generate_suite

class TestNoNetwork(unittest.TestCase):
    def test_pipeline_works_with_sockets_blocked(self):
        orig = socket.socket
        def blocked(*a, **k): raise AssertionError("network use forbidden")
        socket.socket = blocked
        try:
            suite = generate_suite()
            d = compare_reports(run_version(suite, "v1"), run_version(suite, "v2"))
            self.assertEqual(len(d["flips"]), 1)
        finally:
            socket.socket = orig
if __name__ == "__main__": unittest.main()
