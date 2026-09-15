"""Couverture du frais ajouté uniquement au premier versement."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FinancingInitialFeeArchitectureTests(unittest.TestCase):
    def test_schema_adds_first_installment_fee_automatically(self):
        source = (ROOT / "finances_data_part_14.pyfrag").read_text(encoding="utf-8")
        self.assertIn("ADD COLUMN IF NOT EXISTS first_installment_fee", source)
        self.assertIn("CHECK (first_installment_fee >= 0)", source)

    def test_restore_preserves_first_installment_fee(self):
        source = (ROOT / "finances_data_part_16.pyfrag").read_text(encoding="utf-8")
        self.assertIn(
            'first_installment_fee=raw.get("first_installment_fee") or 0',
            source,
        )

    def test_ui_explains_that_fee_does_not_increase_principal(self):
        source = (ROOT / "finances_financing.py").read_text(encoding="utf-8")
        self.assertIn("Frais au premier versement", source)
        self.assertIn("il n’augmente pas le capital financé", source)


if __name__ == "__main__":
    unittest.main()
