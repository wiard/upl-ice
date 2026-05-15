from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import sys


MODULE_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = MODULE_ROOT
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from airmarket import cli  # noqa: E402


class AirMarketTests(unittest.TestCase):
    def make_copy(self) -> Path:
        tmpdir = Path(tempfile.mkdtemp(prefix="airmarket-"))
        target = tmpdir / "airmarket"
        shutil.copytree(MODULE_ROOT, target)
        return target

    def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def patch_module_paths(self, target: Path) -> None:
        cli.MODULE_ROOT = target
        cli.DATA_DIR = target / "data"
        cli.LOG_DIR = target / "log"
        cli.RECEIPTS_DIR = target / "receipts"
        cli.PACT_LOG_PATH = target / "log" / "pact_events.jsonl"

    def test_seed_creates_data(self) -> None:
        target = self.make_copy()
        self.patch_module_paths(target)
        summary = cli.seed()
        self.assertEqual(summary["avatars"], 2)
        self.assertTrue((target / "data" / "avatars.json").exists())
        self.assertTrue((target / "data" / "workcards.json").exists())
        self.assertTrue((target / "data" / "orders.json").exists())

    def test_place_order_creates_order(self) -> None:
        target = self.make_copy()
        self.patch_module_paths(target)
        cli.seed()
        order = cli.place_order("workcard_summary_001")
        self.assertEqual(order["order_id"], "order_001")
        orders = self.read_json(target / "data" / "orders.json")
        self.assertEqual(len(orders["orders"]), 1)

    def test_deliver_creates_proofpack(self) -> None:
        target = self.make_copy()
        self.patch_module_paths(target)
        cli.seed()
        cli.place_order("workcard_summary_001")
        proofpack = cli.deliver("order_001")
        self.assertTrue(proofpack["result_declared_complete"])
        orders = self.read_json(target / "data" / "orders.json")
        self.assertIn("proofpack", orders["orders"][0])

    def test_checkout_returns_checked_on_happy_path(self) -> None:
        target = self.make_copy()
        self.patch_module_paths(target)
        cli.seed()
        cli.place_order("workcard_summary_001")
        cli.deliver("order_001")
        result = cli.checkout("order_001")
        self.assertEqual(result["status"], "checked")
        self.assertEqual(result["action"], "mock_payment_release_allowed")

    def test_missing_mandate_link_returns_incomplete(self) -> None:
        target = self.make_copy()
        self.patch_module_paths(target)
        cli.seed()
        avatars = self.read_json(target / "data" / "avatars.json")
        avatars["mandate_links"] = []
        (target / "data" / "avatars.json").write_text(json.dumps(avatars, indent=2) + "\n", encoding="utf-8")
        cli.place_order("workcard_summary_001")
        cli.deliver("order_001")
        result = cli.checkout("order_001")
        self.assertEqual(result["status"], "incomplete")

    def test_price_above_mandate_returns_out_of_scope(self) -> None:
        target = self.make_copy()
        self.patch_module_paths(target)
        cli.seed()
        workcards = self.read_json(target / "data" / "workcards.json")
        workcards["workcards"][0]["price"]["amount"] = 0.45
        (target / "data" / "workcards.json").write_text(json.dumps(workcards, indent=2) + "\n", encoding="utf-8")
        cli.place_order("workcard_summary_001")
        cli.deliver("order_001")
        result = cli.checkout("order_001")
        self.assertEqual(result["status"], "out_of_scope")

    def test_failed_delivery_check_returns_failed(self) -> None:
        target = self.make_copy()
        self.patch_module_paths(target)
        cli.seed()
        cli.place_order("workcard_summary_001")
        cli.deliver("order_001")
        orders = self.read_json(target / "data" / "orders.json")
        orders["orders"][0]["proofpack"]["output"]["word_count"] = 999
        (target / "data" / "orders.json").write_text(json.dumps(orders, indent=2) + "\n", encoding="utf-8")
        result = cli.checkout("order_001")
        self.assertEqual(result["status"], "failed")

    def test_replay_reconstructs_event_history(self) -> None:
        target = self.make_copy()
        self.patch_module_paths(target)
        cli.seed()
        cli.place_order("workcard_summary_001")
        cli.deliver("order_001")
        cli.checkout("order_001")
        history = cli.replay()
        self.assertEqual(history["event_count"], 4)
        self.assertIn("checkout_adjudicated", history["event_types"])


if __name__ == "__main__":
    unittest.main()
