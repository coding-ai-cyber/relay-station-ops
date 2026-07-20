import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.models.account import Account
from app.schemas.account import Sub2APICheckRequest
from app.services.sub2api_checker import run_sub2api_check


class FakeResponse:
    status_code = 404
    text = "not found"

    def json(self):
        return {"message": "not found"}


class FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def get(self, *args, **kwargs):
        return FakeResponse()


class Sub2APICheckSurvivalTests(unittest.TestCase):
    def test_unavailable_result_clears_survival_time(self):
        account = Account(
            id=uuid.uuid4(),
            account_no="ACC-404",
            account_type="openai",
            created_at=datetime(2026, 7, 16, tzinfo=UTC),
            available_started_at=datetime(2026, 7, 17, tzinfo=UTC),
            survival_seconds=86400,
            available_days=1,
        )
        db = MagicMock()
        records = []

        def add(item):
            if item.__class__.__name__ == "AccountCheckBatch":
                item.id = uuid.uuid4()
                item.alive_count = 0
                item.abnormal_count = 0
                item.status_401_count = 0
                item.status_403_count = 0
                item.status_429_count = 0
            records.append(item)

        db.add.side_effect = add
        payload = Sub2APICheckRequest(endpoint_url="https://example.test/{account_no}")

        with (
            patch("app.services.sub2api_checker._select_accounts", return_value=[account]),
            patch("app.services.sub2api_checker.httpx.Client", FakeClient),
        ):
            batch = run_sub2api_check(db, payload, checked_by=None)

        check_record = next(
            item for item in records if item.__class__.__name__ == "AccountCheckRecord"
        )
        self.assertEqual(batch.abnormal_count, 1)
        self.assertEqual(account.status, "unavailable")
        self.assertIsNone(account.available_started_at)
        self.assertIsNone(account.survival_seconds)
        self.assertIsNone(account.available_days)
        self.assertIsNone(check_record.survived_seconds)


if __name__ == "__main__":
    unittest.main()
