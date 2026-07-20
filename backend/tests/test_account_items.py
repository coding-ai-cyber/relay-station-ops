import unittest
import uuid
from unittest.mock import MagicMock

from app.api.routes.accounts import list_account_items
from app.models.account import Account
from app.models.account_item import AccountItem


class AccountItemRouteTests(unittest.TestCase):
    def test_list_account_items_queries_items_for_account(self):
        account_id = uuid.uuid4()
        expected = [
            AccountItem(
                id=uuid.uuid4(),
                account_id=account_id,
                purchase_id=uuid.uuid4(),
                item_no="PO-1-A001-D001",
                item_index=1,
                email="a@example.com",
                platform="openai",
                status="bound",
            )
        ]
        db = MagicMock()
        db.get.return_value = Account(id=account_id, account_no="PO-1-A001", account_type="openai")
        db.scalars.return_value.all.return_value = expected

        result = list_account_items(account_id=account_id, db=db, current_user=object())

        self.assertEqual(result, expected)
        statement = str(db.scalars.call_args.args[0])
        self.assertIn("account_items.account_id", statement)
        self.assertEqual(db.scalars.call_args.args[0].compile().params["account_id_1"], account_id)


if __name__ == "__main__":
    unittest.main()
