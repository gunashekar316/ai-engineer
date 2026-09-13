"""
End-to-End Verification Test for Salary Maintenance Automation
Spins up the mock HR portal, executes the automated bot, asserts process completion,
and validates audit trail compliance.
"""

import json
import os
import sys
import time
import unittest

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

# Reconfigure stdout for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from src.automation.mock_portal import MockPortalServer, INITIAL_PAYROLL_ITEMS
from src.automation.salary_maintenance_bot import SalaryMaintenanceBot, AUDIT_LOG_PATH


class TestSalaryMaintenanceAutomation(unittest.TestCase):
    portal_server = None
    base_url = None

    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 70)
        print(" [SETUP] Starting Mock HR Payroll Portal for E2E Verification Test")
        print("=" * 70)
        # Clear audit log at beginning of test run
        if os.path.exists(AUDIT_LOG_PATH):
            try:
                os.remove(AUDIT_LOG_PATH)
            except OSError:
                pass
        cls.portal_server = MockPortalServer()
        cls.actual_port = cls.portal_server.start()
        cls.base_url = cls.portal_server.base_url
        print(f"Mock Portal listening at: {cls.portal_server.portal_url} (Port {cls.actual_port})")
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        print("\n" + "=" * 70)
        print(" [TEARDOWN] Stopping Mock HR Payroll Portal")
        print("=" * 70)
        if cls.portal_server:
            cls.portal_server.stop()
            print("Mock Portal terminated cleanly.")

    def setUp(self):
        # Reset portal state before each test
        import requests
        requests.post(f"{self.base_url}/api/reset", timeout=5.0)

    def test_01_portal_health_and_dom_elements(self):
        """Validates that portal serves target DOM elements (#pi-table, #pi-note, #btn-pi-ok)."""
        import requests
        from bs4 import BeautifulSoup

        print("\n[TEST 01] Verifying Portal Health & Telemetry DOM Elements...")
        res = requests.get(f"{self.base_url}/health", timeout=5.0)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json().get("status"), "ok")

        html_res = requests.get(f"{self.base_url}/", timeout=5.0)
        self.assertEqual(html_res.status_code, 200)

        soup = BeautifulSoup(html_res.text, "html.parser")
        table = soup.find("table", id="pi-table")
        note = soup.find("textarea", id="pi-note")
        button = soup.find("button", id="btn-pi-ok")

        self.assertIsNotNone(table, "Target table #pi-table must exist in DOM")
        self.assertIsNotNone(note, "Target textarea #pi-note must exist in DOM")
        self.assertIsNotNone(button, "Commit button #btn-pi-ok must exist in DOM")
        print("  ✓ DOM Elements verified: #pi-table, #pi-note, #btn-pi-ok present.")

    def test_02_e2e_salary_maintenance_bot_execution(self):
        """Executes full automated maintenance bot and asserts 100% completion & accuracy."""
        import requests

        print("\n[TEST 02] Running SalaryMaintenanceBot on pending records...")
        bot = SalaryMaintenanceBot(
            base_url=self.base_url,
            timeout_sec=5.0,
            max_retries=3,
            throttle_delay=0.02
        )

        metrics = bot.run()

        # Assertions on Bot Execution
        self.assertGreater(metrics.total_records, 0, "Bot should have detected pending records")
        self.assertEqual(metrics.total_records, len(INITIAL_PAYROLL_ITEMS), "Should process all initial items")
        self.assertEqual(metrics.successful_records, metrics.total_records, "All records must succeed")
        self.assertEqual(metrics.failed_records, 0, "No records should fail")
        self.assertGreater(metrics.throughput_per_sec, 0.0, "Throughput must be positive")

        # Verify Portal Server State via API
        res = requests.get(f"{self.base_url}/api/payroll-items", timeout=5.0)
        self.assertEqual(res.status_code, 200)
        items = res.json()

        for item in items:
            self.assertEqual(item["status"], "approved", f"Item {item['id']} should be approved")
            self.assertTrue(len(item["note"]) > 0, f"Item {item['id']} should have remark note")
            self.assertIsNotNone(item["updated_at"], f"Item {item['id']} should have updated_at timestamp")

        # Verify Audit Log Trail
        self.assertTrue(os.path.exists(AUDIT_LOG_PATH), "Audit log file must be created")
        with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        self.assertEqual(len(lines), len(INITIAL_PAYROLL_ITEMS), "Audit log must contain all records")
        for entry in lines:
            self.assertEqual(entry["status"], "approved")
            self.assertEqual(entry["target_input"], "#pi-note")
            self.assertEqual(entry["commit_button"], "#btn-pi-ok")
            self.assertIn("duration_ms", entry)

        print(f"  ✓ Full batch of {metrics.total_records} records processed with 100% success rate.")
        print(f"  ✓ Average latency: {metrics.avg_latency_ms:.1f}ms | Throughput: {metrics.throughput_per_sec:.1f} rec/s")
        print(f"  ✓ Audit log verified ({len(lines)} compliant entries written).")

    def test_03_defensive_retry_and_resiliency(self):
        """Tests defensive behavior against non-existent records or invalid states."""
        print("\n[TEST 03] Testing Defensive Exception Handling & Retry Logic...")
        bot = SalaryMaintenanceBot(
            base_url=self.base_url,
            timeout_sec=2.0,
            max_retries=2,
            throttle_delay=0.01
        )

        dummy_item = {
            "id": "INVALID-ROW-99999",
            "employee_id": "E9999",
            "employee_name": "架空 太郎",
            "category": "テスト項目",
            "amount": 10000,
            "effective_month": "2026-07"
        }

        success = bot.process_single_record(dummy_item)
        self.assertFalse(success, "Invalid record should fail gracefully without throwing fatal exception")
        print("  ✓ Invalid record failed gracefully and was caught by defensive retry policy.")


def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSalaryMaintenanceAutomation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
