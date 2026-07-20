import re
import unittest
from datetime import date

from app.api.routes.revenues import generate_revenue_no
from app.schemas.revenue import RevenueCreate


class RevenueInputTests(unittest.TestCase):
    def test_blank_revenue_number_is_treated_as_missing(self):
        payload = RevenueCreate(
            revenue_no="",
            source="manual_payment",
            amount=30,
            currency="USD",
            revenue_date=date(2026, 7, 16),
        )

        self.assertIsNone(payload.revenue_no)

    def test_generates_revenue_number_with_current_date_prefix(self):
        revenue_no = generate_revenue_no(today=date(2026, 7, 16))

        self.assertRegex(revenue_no, r"^REV-20260716-[A-Z0-9]{6}$")

    def test_generates_uppercase_random_suffix(self):
        numbers = {generate_revenue_no(today=date(2026, 7, 16)) for _ in range(20)}

        self.assertTrue(all(re.match(r"^REV-20260716-[A-Z0-9]{6}$", item) for item in numbers))
        self.assertGreater(len(numbers), 1)


if __name__ == "__main__":
    unittest.main()
