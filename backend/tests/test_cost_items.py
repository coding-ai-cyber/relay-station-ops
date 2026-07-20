import re
import unittest
from datetime import date

from app.api.routes.cost_items import generate_cost_no
from app.schemas.cost_item import CostItemCreate


class CostItemInputTests(unittest.TestCase):
    def test_blank_cost_number_is_treated_as_missing(self):
        payload = CostItemCreate(
            cost_no="",
            cost_type="other",
            product_name="Early account batch",
            amount=120,
            cost_date=date(2026, 7, 15),
        )

        self.assertIsNone(payload.cost_no)
        self.assertEqual(payload.product_name, "Early account batch")
        self.assertTrue(payload.one_time)
        self.assertFalse(payload.recurring)

    def test_generates_cost_number_with_current_date_prefix(self):
        cost_no = generate_cost_no(today=date(2026, 7, 15))

        self.assertRegex(cost_no, r"^COST-20260715-[A-Z0-9]{6}$")

    def test_generates_uppercase_random_suffix(self):
        numbers = {generate_cost_no(today=date(2026, 7, 15)) for _ in range(20)}

        self.assertTrue(all(re.match(r"^COST-20260715-[A-Z0-9]{6}$", item) for item in numbers))
        self.assertGreater(len(numbers), 1)


if __name__ == "__main__":
    unittest.main()
