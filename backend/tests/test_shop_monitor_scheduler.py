import unittest

from app.services.shop_monitor_scheduler import run_shop_monitor_scheduler_once_for_test


class ShopMonitorSchedulerTests(unittest.IsolatedAsyncioTestCase):
    async def test_scheduler_syncs_immediately_then_waits_for_interval(self):
        calls: list[str] = []
        sleeps: list[float] = []

        async def sync_once() -> None:
            calls.append("sync")

        async def sleep(interval: float) -> None:
            sleeps.append(interval)

        await run_shop_monitor_scheduler_once_for_test(
            sync_once=sync_once,
            sleep=sleep,
            interval_seconds=300,
            iterations=2,
        )

        self.assertEqual(calls, ["sync", "sync"])
        self.assertEqual(sleeps, [300])


if __name__ == "__main__":
    unittest.main()
