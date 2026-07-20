import unittest

from app.api.routes.reports import build_ai_pricing_recommendations
from app.schemas.dashboard import AccountTypeProfitRow


class ReportAIRecommendationTests(unittest.TestCase):
    def test_recommends_multiplier_and_projected_profit_from_real_cost(self):
        rows = [
            AccountTypeProfitRow(
                account_type="openai",
                batch_count=3,
                purchase_quantity=100,
                effective_account_count=80,
                effective_rate=80,
                all_cost=100,
                effective_cost=80,
                test_loss=20,
                real_effective_unit_cost=1.25,
                avg_score=88,
            )
        ]

        result = build_ai_pricing_recommendations(rows, target_margin=40)

        self.assertEqual(len(result), 1)
        recommendation = result[0]
        self.assertEqual(recommendation.account_type, "openai")
        self.assertEqual(recommendation.risk_level, "stable")
        self.assertEqual(recommendation.recommended_multiplier, 1.87)
        self.assertEqual(recommendation.suggested_sale_price, 2.34)
        self.assertEqual(recommendation.projected_revenue, 187.0)
        self.assertEqual(recommendation.projected_profit, 87.0)
        self.assertEqual(recommendation.projected_margin, 46.52)
        self.assertIn("有效率 80.0%", recommendation.reason)

    def test_marks_low_effective_rate_as_high_risk(self):
        rows = [
            AccountTypeProfitRow(
                account_type="gemini",
                batch_count=1,
                purchase_quantity=100,
                effective_account_count=35,
                effective_rate=35,
                all_cost=100,
                effective_cost=35,
                test_loss=65,
                real_effective_unit_cost=2.86,
                avg_score=55,
            )
        ]

        result = build_ai_pricing_recommendations(rows, target_margin=35)

        self.assertEqual(result[0].risk_level, "high_risk")
        self.assertGreater(result[0].recommended_multiplier, 2.0)
        self.assertIn("高风险", result[0].reason)


if __name__ == "__main__":
    unittest.main()
