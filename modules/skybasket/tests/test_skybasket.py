from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skybasket import cli


class SkyBasketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        module_root = Path(self.temp_dir.name)
        data_dir = module_root / "data"
        log_dir = module_root / "log"
        receipts_dir = module_root / "receipts"
        data_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)
        receipts_dir.mkdir(parents=True, exist_ok=True)

        self.original_module_root = cli.MODULE_ROOT
        self.original_data_dir = cli.DATA_DIR
        self.original_log_dir = cli.LOG_DIR
        self.original_receipts_dir = cli.RECEIPTS_DIR
        self.original_pact_log_path = cli.PACT_LOG_PATH

        cli.MODULE_ROOT = module_root
        cli.DATA_DIR = data_dir
        cli.LOG_DIR = log_dir
        cli.RECEIPTS_DIR = receipts_dir
        cli.PACT_LOG_PATH = log_dir / "pact_events.jsonl"

    def tearDown(self) -> None:
        cli.MODULE_ROOT = self.original_module_root
        cli.DATA_DIR = self.original_data_dir
        cli.LOG_DIR = self.original_log_dir
        cli.RECEIPTS_DIR = self.original_receipts_dir
        cli.PACT_LOG_PATH = self.original_pact_log_path
        self.temp_dir.cleanup()

    def load_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_seed_creates_initial_avatars_and_workcards(self) -> None:
        result = cli.seed()
        self.assertEqual(result["avatars"], 4)
        self.assertEqual(result["workcards"], 2)
        avatars = self.load_json(cli.DATA_DIR / "avatars.json")
        workcards = self.load_json(cli.DATA_DIR / "workcards.json")
        self.assertEqual(len(avatars["mandate_links"]), 3)
        self.assertEqual(len(workcards["workcards"]), 2)

    def test_create_basket_creates_basket_001(self) -> None:
        cli.seed()
        basket = cli.create_basket()
        self.assertEqual(basket["basket_id"], "basket_001")
        baskets = self.load_json(cli.DATA_DIR / "baskets.json")
        self.assertEqual(baskets["baskets"][0]["basket_id"], "basket_001")

    def test_deliver_all_creates_proofpacks_for_all_items(self) -> None:
        cli.seed()
        cli.create_basket()
        basket = cli.deliver_all("basket_001")
        self.assertTrue(all("proofpack" in item for item in basket["items"]))

    def test_happy_path_checkout_returns_checked(self) -> None:
        cli.seed()
        cli.create_basket()
        cli.deliver_all("basket_001")
        receipt = cli.checkout("basket_001")
        self.assertEqual(receipt["basket_status"], "checked")
        self.assertEqual(receipt["basket_action"], "mock_basket_payment_release_allowed")

    def test_missing_mandatelink_returns_incomplete(self) -> None:
        cli.seed()
        avatars = self.load_json(cli.DATA_DIR / "avatars.json")
        avatars["mandate_links"] = [link for link in avatars["mandate_links"] if link["source_avatar"] != "summary_agent"]
        cli.write_json(cli.DATA_DIR / "avatars.json", avatars)
        cli.create_basket()
        cli.deliver_all("basket_001")
        receipt = cli.checkout("basket_001")
        self.assertEqual(receipt["basket_status"], "incomplete")

    def test_basket_total_price_above_mandate_returns_out_of_scope(self) -> None:
        cli.seed()
        cli.create_basket()
        baskets = self.load_json(cli.DATA_DIR / "baskets.json")
        baskets["baskets"][0]["buyer_mandate"]["max_total_price"]["amount"] = 0.20
        cli.write_json(cli.DATA_DIR / "baskets.json", baskets)
        cli.deliver_all("basket_001")
        receipt = cli.checkout("basket_001")
        self.assertEqual(receipt["basket_status"], "out_of_scope")

    def test_one_failed_item_delivery_makes_basket_failed(self) -> None:
        cli.seed()
        cli.create_basket()
        cli.deliver_all("basket_001")
        baskets = self.load_json(cli.DATA_DIR / "baskets.json")
        baskets["baskets"][0]["items"][1]["proofpack"]["output"]["payload"].pop("risk_label")
        cli.write_json(cli.DATA_DIR / "baskets.json", baskets)
        receipt = cli.checkout("basket_001")
        self.assertEqual(receipt["basket_status"], "failed")

    def test_replay_reconstructs_event_history(self) -> None:
        cli.seed()
        cli.create_basket()
        cli.deliver_all("basket_001")
        cli.checkout("basket_001")
        replay = cli.replay()
        self.assertEqual(replay["event_count"], 4)
        self.assertEqual(replay["latest_basket_status"], "checked")


if __name__ == "__main__":
    unittest.main()
