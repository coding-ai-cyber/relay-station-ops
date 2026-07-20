import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from sqlalchemy.dialects import postgresql

from app.models.shop_monitor import ShopMonitor
from app.services.shop_monitor_sync import (
    build_due_shop_monitor_statement,
    is_shop_monitor_due_for_auto_sync,
    sync_enabled_shop_monitors,
)


class ShopMonitorAutoSyncThrottleTests(unittest.TestCase):
    def test_never_synced_monitor_is_due(self):
        monitor = ShopMonitor(enabled=True, last_synced_at=None, last_sync_status="pending")

        self.assertTrue(
            is_shop_monitor_due_for_auto_sync(
                monitor,
                now=datetime(2026, 7, 16, tzinfo=UTC),
                success_interval_seconds=3600,
                failure_cooldown_seconds=3600,
            )
        )

    def test_recent_success_is_not_due_until_success_interval_passes(self):
        now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
        monitor = ShopMonitor(
            enabled=True,
            last_synced_at=now - timedelta(minutes=30),
            last_sync_status="success",
        )

        self.assertFalse(
            is_shop_monitor_due_for_auto_sync(
                monitor,
                now=now,
                success_interval_seconds=3600,
                failure_cooldown_seconds=3600,
            )
        )

    def test_recent_failure_is_not_due_until_failure_cooldown_passes(self):
        now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
        monitor = ShopMonitor(
            enabled=True,
            last_synced_at=now - timedelta(minutes=10),
            last_sync_status="failed",
        )

        self.assertFalse(
            is_shop_monitor_due_for_auto_sync(
                monitor,
                now=now,
                success_interval_seconds=3600,
                failure_cooldown_seconds=3600,
            )
        )

    def test_old_failure_is_due_after_cooldown(self):
        now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
        monitor = ShopMonitor(
            enabled=True,
            last_synced_at=now - timedelta(hours=2),
            last_sync_status="failed",
        )

        self.assertTrue(
            is_shop_monitor_due_for_auto_sync(
                monitor,
                now=now,
                success_interval_seconds=3600,
                failure_cooldown_seconds=3600,
            )
        )

    def test_due_query_uses_skip_locked_to_avoid_duplicate_auto_sync(self):
        statement = build_due_shop_monitor_statement(
            now=datetime(2026, 7, 16, 12, 0, tzinfo=UTC),
            success_interval_seconds=3600,
            failure_cooldown_seconds=3600,
        )

        compiled = str(statement.compile(dialect=postgresql.dialect()))
        self.assertIn("FOR UPDATE SKIP LOCKED", compiled)

    def test_auto_sync_only_runs_due_monitors_returned_by_query(self):
        db = MagicMock()
        due = ShopMonitor(enabled=True, last_synced_at=None, last_sync_status="pending")
        db.scalars.return_value.all.return_value = [due]

        with patch("app.services.shop_monitor_sync.sync_monitor", return_value="ok") as sync_monitor:
            result = sync_enabled_shop_monitors(
                db,
                now=datetime(2026, 7, 16, 12, 0, tzinfo=UTC),
                success_interval_seconds=3600,
                failure_cooldown_seconds=3600,
            )

        self.assertEqual(result, ["ok"])
        sync_monitor.assert_called_once_with(db, due)

    def test_auto_sync_limits_monitors_per_batch(self):
        db = MagicMock()
        due_monitors = [
            ShopMonitor(enabled=True, last_synced_at=None, last_sync_status="pending"),
            ShopMonitor(enabled=True, last_synced_at=None, last_sync_status="pending"),
            ShopMonitor(enabled=True, last_synced_at=None, last_sync_status="pending"),
        ]
        db.scalars.return_value.all.return_value = due_monitors

        with patch("app.services.shop_monitor_sync.sync_monitor", side_effect=["one", "two"]) as sync_monitor:
            result = sync_enabled_shop_monitors(
                db,
                now=datetime(2026, 7, 16, 12, 0, tzinfo=UTC),
                success_interval_seconds=3600,
                failure_cooldown_seconds=3600,
                max_monitors=2,
            )

        self.assertEqual(result, ["one", "two"])
        self.assertEqual(sync_monitor.call_count, 2)


if __name__ == "__main__":
    unittest.main()
