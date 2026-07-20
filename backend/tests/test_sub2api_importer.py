import unittest
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from app.core.security import field_cipher
from app.models.account import Account
from app.models.account_item import AccountItem
from app.services.sub2api_importer import (
    Sub2APIAdminClient,
    Sub2APIImportError,
    Sub2APIImportValidationError,
    build_sub2api_account_payload,
    _bind_account_to_sub2api_instance,
    _find_remote,
    _import_targets_for_accounts,
    _lock_batch_for_execution,
    _remote_index,
    _response_message,
    _safe_error_message,
    recover_stale_import_batch,
)


def account(**overrides):
    values = {
        "account_no": "ACC-001",
        "name": "Primary account",
        "account_type": "OpenAI",
        "remark": "stable",
        "expired_at": None,
        "raw_payload": None,
        "raw_credentials_encrypted": None,
        "sub2api_account_id": None,
        "login_account": None,
        "authorized_email": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class Sub2APIInstanceBindingTests(unittest.TestCase):
    def test_records_target_instance_and_remote_id_on_imported_account(self):
        instance_id = uuid.uuid4()
        local = SimpleNamespace(sub2api_instance_id=None, sub2api_account_id=None)
        item = SimpleNamespace(remote_account_id=None)

        _bind_account_to_sub2api_instance(local, item, instance_id, "remote-1001")

        self.assertEqual(local.sub2api_instance_id, instance_id)
        self.assertEqual(local.sub2api_account_id, "remote-1001")
        self.assertEqual(item.remote_account_id, "remote-1001")

    def test_records_target_instance_even_when_remote_id_is_missing(self):
        instance_id = uuid.uuid4()
        local = SimpleNamespace(sub2api_instance_id=None, sub2api_account_id="old-id")
        item = SimpleNamespace(remote_account_id="old-id")

        _bind_account_to_sub2api_instance(local, item, instance_id, "")

        self.assertEqual(local.sub2api_instance_id, instance_id)
        self.assertEqual(local.sub2api_account_id, "old-id")
        self.assertIsNone(item.remote_account_id)


class BuildSub2APIAccountPayloadTests(unittest.TestCase):
    def test_uses_raw_oauth_credentials_and_matching_groups(self):
        local = account(
            raw_payload={
                "platform": "openai",
                "type": "oauth",
                "credentials": "[REDACTED]",
            },
            raw_credentials_encrypted=field_cipher.encrypt(
                '{"access_token":"access","refresh_token":"refresh"}'
            ),
        )
        groups = [
            {"id": 11, "name": "OpenAI stable", "platform": "openai"},
            {"id": 22, "name": "Claude stable", "platform": "anthropic"},
        ]

        payload = build_sub2api_account_payload(local, groups, sub2api_key=None)

        self.assertEqual(payload["platform"], "openai")
        self.assertEqual(payload["name"], "ACC-001")
        self.assertEqual(payload["type"], "oauth")
        self.assertEqual(payload["credentials"]["refresh_token"], "refresh")
        self.assertEqual(payload["group_ids"], [11])
        self.assertEqual(payload["concurrency"], 10)
        self.assertEqual(payload["priority"], 1)

    def test_uses_original_email_as_remote_account_name(self):
        payload = build_sub2api_account_payload(
            account(
                login_account="buyer@example.com",
                authorized_email="other@example.com",
                raw_payload={"platform": "openai", "type": "oauth", "credentials": "[REDACTED]"},
                raw_credentials_encrypted=field_cipher.encrypt(
                    '{"access_token":"access","email":"credential@example.com"}'
                ),
            ),
            [{"id": 14, "name": "OpenAI", "platform": "openai"}],
            sub2api_key=None,
        )

        self.assertEqual(payload["name"], "buyer@example.com")

    def test_uses_credential_email_as_remote_account_name_when_account_email_missing(self):
        payload = build_sub2api_account_payload(
            account(
                raw_payload={"platform": "openai", "type": "oauth", "credentials": "[REDACTED]"},
                raw_credentials_encrypted=field_cipher.encrypt(
                    '{"access_token":"access","email":"credential@example.com"}'
                ),
            ),
            [{"id": 14, "name": "OpenAI", "platform": "openai"}],
            sub2api_key=None,
        )

        self.assertEqual(payload["name"], "credential@example.com")

    def test_maps_saved_key_to_apikey_credentials(self):
        payload = build_sub2api_account_payload(
            account(account_type="Claude"),
            [{"id": 7, "name": "Claude", "platform": "anthropic"}],
            sub2api_key="sk-live",
        )

        self.assertEqual(payload["platform"], "anthropic")
        self.assertEqual(payload["type"], "apikey")
        self.assertEqual(payload["credentials"], {"api_key": "sk-live"})
        self.assertEqual(payload["group_ids"], [7])

    def test_rejects_groups_for_other_platforms(self):
        with self.assertRaisesRegex(Sub2APIImportValidationError, "匹配.*分组"):
            build_sub2api_account_payload(
                account(
                    raw_payload={"type": "apikey", "credentials": "[REDACTED]"},
                    raw_credentials_encrypted=field_cipher.encrypt('{"api_key":"key"}'),
                ),
                [{"id": 9, "name": "Gemini", "platform": "gemini"}],
                sub2api_key=None,
            )

    def test_rejects_account_without_importable_credentials(self):
        with self.assertRaisesRegex(Sub2APIImportValidationError, "凭证"):
            build_sub2api_account_payload(
                account(),
                [{"id": 11, "name": "OpenAI stable", "platform": "openai"}],
                sub2api_key=None,
            )

    def test_omits_chatgpt_account_metadata_from_credentials(self):
        payload = build_sub2api_account_payload(
            account(
                raw_payload={"platform": "openai", "type": "oauth", "credentials": "[REDACTED]"},
                raw_credentials_encrypted=field_cipher.encrypt(
                    '{"access_token":"access","account_id":"chatgpt-id","chatgpt_account_id":"chatgpt-id","plan_type":"free"}'
                ),
            ),
            [{"id": 14, "name": "OpenAI", "platform": "openai"}],
            sub2api_key=None,
        )

        self.assertEqual(payload["credentials"]["access_token"], "access")
        self.assertNotIn("account_id", payload["credentials"])
        self.assertNotIn("chatgpt_account_id", payload["credentials"])
        self.assertNotIn("plan_type", payload["credentials"])

    def test_includes_selected_proxy_id_when_importing(self):
        payload = build_sub2api_account_payload(
            account(
                raw_payload={"platform": "openai", "type": "oauth", "credentials": "[REDACTED]"},
                raw_credentials_encrypted=field_cipher.encrypt('{"access_token":"access"}'),
            ),
            [{"id": 14, "name": "OpenAI", "platform": "openai"}],
            sub2api_key=None,
            proxy_id=33,
        )

        self.assertEqual(payload["proxy_id"], 33)


class Sub2APIImportTargetTests(unittest.TestCase):
    def test_expands_account_details_into_individual_import_targets(self):
        parent = Account(
            id=uuid.uuid4(),
            account_no="PO-1-A001",
            account_type="OpenAI",
            raw_credentials_encrypted=field_cipher.encrypt('{"access_token":"parent"}'),
        )
        first = AccountItem(
            id=uuid.uuid4(),
            account_id=parent.id,
            item_no="PO-1-A001-D001",
            item_index=1,
            email="first@example.com",
            platform="openai",
            raw_credentials_encrypted=field_cipher.encrypt('{"access_token":"first","email":"first@example.com"}'),
        )
        second = AccountItem(
            id=uuid.uuid4(),
            account_id=parent.id,
            item_no="PO-1-A001-D002",
            item_index=2,
            email="second@example.com",
            platform="openai",
            raw_credentials_encrypted=field_cipher.encrypt('{"access_token":"second","email":"second@example.com"}'),
        )
        parent.items = [second, first]

        targets = _import_targets_for_accounts([parent])

        self.assertEqual([target.display_no for target in targets], ["PO-1-A001-D001", "PO-1-A001-D002"])
        payloads = [
            build_sub2api_account_payload(
                target.payload_account,
                [{"id": 14, "name": "OpenAI", "platform": "openai"}],
                sub2api_key=None,
            )
            for target in targets
        ]
        self.assertEqual([payload["name"] for payload in payloads], ["first@example.com", "second@example.com"])
        self.assertEqual([payload["credentials"]["access_token"] for payload in payloads], ["first", "second"])

    def test_imports_parent_account_when_no_details_exist(self):
        parent = Account(
            id=uuid.uuid4(),
            account_no="ACC-001",
            account_type="OpenAI",
            raw_credentials_encrypted=field_cipher.encrypt('{"access_token":"parent"}'),
        )

        targets = _import_targets_for_accounts([parent])

        self.assertEqual(len(targets), 1)
        self.assertIs(targets[0].source_account, parent)
        self.assertIsNone(targets[0].source_item)
        self.assertEqual(targets[0].display_no, "ACC-001")


class Sub2APIAdminClientTests(unittest.TestCase):
    def test_wraps_connection_errors(self):
        instance = SimpleNamespace(
            admin_key_encrypted=field_cipher.encrypt("admin-key"),
            base_url="http://127.0.0.1:9",
            detected_accounts_path=None,
        )
        client = Sub2APIAdminClient(instance)

        with patch.object(httpx.Client, "get", side_effect=httpx.ConnectError("offline")):
            with self.assertRaisesRegex(Sub2APIImportError, "offline"):
                client.list_groups()

    def test_paginates_remote_accounts(self):
        instance = SimpleNamespace(
            admin_key_encrypted=field_cipher.encrypt("admin-key"),
            base_url="http://127.0.0.1:9",
            detected_accounts_path="/api/v1/admin/accounts",
        )
        client = Sub2APIAdminClient(instance)
        pages = [
            ({"data": {"items": [{"id": 1}], "total": 2}}, "/api/v1/admin"),
            ({"data": {"items": [{"id": 2}], "total": 2}}, "/api/v1/admin"),
        ]

        with patch.object(client, "_get_with_prefix_fallback", side_effect=pages) as request:
            items = client.list_accounts(page_size=1)

        self.assertEqual([item["id"] for item in items], [1, 2])
        self.assertEqual(request.call_count, 2)

    def test_lists_remote_proxies(self):
        instance = SimpleNamespace(
            admin_key_encrypted=field_cipher.encrypt("admin-key"),
            base_url="http://127.0.0.1:9",
            detected_accounts_path="/api/v1/admin/accounts",
        )
        client = Sub2APIAdminClient(instance)

        with patch.object(
            client,
            "_get_with_prefix_fallback",
            return_value=({"data": {"items": [{"id": 33, "name": "Proxy 33"}]}}, "/api/v1/admin"),
        ) as request:
            items = client.list_proxies()

        self.assertEqual(items, [{"id": 33, "name": "Proxy 33"}])
        request.assert_called_once_with("proxies?page=1&page_size=1000")

    def test_paginates_when_server_caps_the_page_size(self):
        instance = SimpleNamespace(
            admin_key_encrypted=field_cipher.encrypt("admin-key"),
            base_url="http://127.0.0.1:9",
            detected_accounts_path="/api/v1/admin/accounts",
        )
        client = Sub2APIAdminClient(instance)
        pages = [
            ({"data": {"items": [{"id": index} for index in range(100)], "total": 150}}, "/api/v1/admin"),
            ({"data": {"items": [{"id": index} for index in range(100, 150)], "total": 150}}, "/api/v1/admin"),
        ]

        with patch.object(client, "_get_with_prefix_fallback", side_effect=pages) as request:
            items = client.list_accounts(page_size=1000)

        self.assertEqual(len(items), 150)
        self.assertEqual(request.call_count, 2)

    def test_rejects_pagination_that_repeats_the_same_page(self):
        instance = SimpleNamespace(
            admin_key_encrypted=field_cipher.encrypt("admin-key"),
            base_url="http://127.0.0.1:9",
            detected_accounts_path="/api/v1/admin/accounts",
        )
        client = Sub2APIAdminClient(instance)
        repeated_page = ({"data": {"items": [{"id": 1}], "total": 3}}, "/api/v1/admin")

        with patch.object(
            client,
            "_get_with_prefix_fallback",
            side_effect=[repeated_page, repeated_page],
        ):
            with self.assertRaisesRegex(Sub2APIImportError, "pagination|分页"):
                client.list_accounts(page_size=1)

    def test_redacts_credentials_from_remote_error_message(self):
        response = httpx.Response(
            422,
            json={"detail": {"credentials": {"access_token": "secret-token"}}},
        )

        message = _response_message(response)

        self.assertNotIn("secret-token", message)
        self.assertIn("[REDACTED]", message)

    def test_redacts_credentials_from_plain_text_error_message(self):
        message = _safe_error_message("request failed: access_token=secret-token")

        self.assertNotIn("secret-token", message)
        self.assertIn("[REDACTED]", message)

    def test_falls_back_to_single_create_when_batch_route_is_misrouted(self):
        instance = SimpleNamespace(
            admin_key_encrypted=field_cipher.encrypt("admin-key"),
            base_url="https://sub2api.example",
            detected_accounts_path="/api/v1/admin/accounts",
        )
        client = Sub2APIAdminClient(instance)
        http_client = unittest.mock.MagicMock()
        http_client.request.side_effect = [
            httpx.Response(400, json={"message": "Invalid account ID"}),
            httpx.Response(200, json={"data": {"id": 88, "name": "ACC-001"}}),
        ]
        client_factory = unittest.mock.MagicMock()
        client_factory.return_value.__enter__.return_value = http_client

        with patch.object(httpx, "Client", client_factory):
            results = client.batch_create(
                [{"name": "ACC-001", "platform": "openai", "type": "oauth", "credentials": {}}],
                "batch-key",
            )

        self.assertEqual(results[0]["id"], "88")
        self.assertTrue(results[0]["success"])
        self.assertEqual(http_client.request.call_args_list[0].kwargs["json"], {"accounts": [unittest.mock.ANY]})
        self.assertEqual(http_client.request.call_args_list[1].kwargs["json"]["name"], "ACC-001")
        self.assertEqual(http_client.request.call_args_list[1].args[0], "POST")
        self.assertTrue(http_client.request.call_args_list[1].args[1].endswith("/api/v1/admin/accounts"))

    def test_preserves_write_method_across_redirects(self):
        instance = SimpleNamespace(
            admin_key_encrypted=field_cipher.encrypt("admin-key"),
            base_url="https://sub2api.example",
            detected_accounts_path="/api/v1/admin/accounts",
        )
        client = Sub2APIAdminClient(instance)
        http_client = unittest.mock.MagicMock()
        http_client.request.side_effect = [
            httpx.Response(
                301,
                headers={"location": "https://api.sub2api.example/api/v1/admin/accounts/batch"},
                request=httpx.Request("POST", "https://sub2api.example/api/v1/admin/accounts/batch"),
            ),
            httpx.Response(200, json={"data": {"results": [{"success": True, "id": 88}]}}),
        ]
        client_factory = unittest.mock.MagicMock()
        client_factory.return_value.__enter__.return_value = http_client

        with patch.object(httpx, "Client", client_factory):
            results = client.batch_create(
                [{"name": "ACC-001", "platform": "openai", "type": "oauth", "credentials": {}}],
                "batch-key",
            )

        self.assertEqual(results, [{"success": True, "id": 88}])
        self.assertEqual(http_client.request.call_args_list[0].args[0], "POST")
        self.assertEqual(http_client.request.call_args_list[1].args[0], "POST")
        self.assertEqual(
            http_client.request.call_args_list[1].args[1],
            "https://api.sub2api.example/api/v1/admin/accounts/batch",
        )


class RemoteAccountMatchingTests(unittest.TestCase):
    def test_account_number_does_not_match_remote_id_namespace(self):
        index = _remote_index([
            {"id": "123", "name": "different", "platform": "openai"},
        ])

        self.assertIsNone(_find_remote(account(account_no="123"), index, "openai"))

    def test_does_not_match_same_name_from_other_platform(self):
        index = _remote_index([
            {"id": "88", "name": "ACC-001", "platform": "anthropic"},
        ])

        self.assertIsNone(_find_remote(account(), index, "openai"))

    def test_matches_saved_remote_id_only_in_id_namespace(self):
        remote = {"id": "88", "name": "different", "platform": "openai"}
        index = _remote_index([remote])

        self.assertIs(
            _find_remote(account(sub2api_account_id="88"), index, "openai", known_remote_id="88"),
            remote,
        )

    def test_does_not_trust_global_remote_id_without_instance_binding(self):
        index = _remote_index([
            {"id": "88", "name": "different", "platform": "openai"},
        ])

        self.assertIsNone(
            _find_remote(account(sub2api_account_id="88"), index, "openai")
        )

    def test_does_not_match_account_number_against_remote_email(self):
        index = _remote_index([
            {"id": "88", "name": "different", "email": "ACC-001", "platform": "openai"},
        ])

        self.assertIsNone(_find_remote(account(), index, "openai"))

    def test_rejects_ambiguous_matches(self):
        index = _remote_index([
            {"id": "88", "name": "ACC-001", "platform": "openai"},
            {"id": "99", "email": "owner@example.com", "platform": "openai"},
        ])

        with self.assertRaisesRegex(Sub2APIImportValidationError, "multiple|多个"):
            _find_remote(
                account(authorized_email="owner@example.com"),
                index,
                "openai",
            )

    def test_matches_email_nested_in_remote_credentials(self):
        remote = {
            "id": "88",
            "name": "different",
            "platform": "openai",
            "credentials": {"email": "owner@example.com"},
        }
        index = _remote_index([remote])

        self.assertIs(
            _find_remote(
                account(authorized_email="owner@example.com"),
                index,
                "openai",
            ),
            remote,
        )


class StaleImportRecoveryTests(unittest.TestCase):
    def test_marks_pending_items_failed_when_running_batch_is_stale(self):
        now = datetime.now(UTC)
        pending = SimpleNamespace(status="pending", error_message=None)
        succeeded = SimpleNamespace(status="success", error_message=None)
        batch = SimpleNamespace(
            status="running",
            started_at=now - timedelta(minutes=20),
            items=[pending, succeeded],
            success_count=0,
            failed_count=0,
            skipped_count=0,
            finished_at=None,
        )

        recovered = recover_stale_import_batch(batch, now=now, stale_after=timedelta(minutes=15))

        self.assertTrue(recovered)
        self.assertEqual(pending.status, "failed")
        self.assertIn("中断", pending.error_message)
        self.assertEqual(batch.status, "partial")

    def test_keeps_recent_running_batch_unchanged(self):
        now = datetime.now(UTC)
        pending = SimpleNamespace(status="pending", error_message=None)
        batch = SimpleNamespace(
            status="running",
            started_at=now - timedelta(minutes=5),
            items=[pending],
        )

        self.assertFalse(
            recover_stale_import_batch(batch, now=now, stale_after=timedelta(minutes=15))
        )
        self.assertEqual(pending.status, "pending")

    def test_execution_lock_is_held_on_the_batch_row(self):
        db = unittest.mock.MagicMock()
        batch = SimpleNamespace()

        _lock_batch_for_execution(db, batch)

        db.refresh.assert_called_once_with(batch, with_for_update=True)

if __name__ == "__main__":
    unittest.main()
