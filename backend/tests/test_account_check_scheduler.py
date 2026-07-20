import unittest

from app.services.account_check_scheduler import run_account_check_scheduler


class AccountCheckSchedulerTests(unittest.IsolatedAsyncioTestCase):
    async def test_scheduler_checks_immediately_then_waits_for_interval(self):
        calls: list[str] = []
        sleeps: list[float] = []

        async def check_once() -> None:
            calls.append("check")

        async def sleep(interval: float) -> None:
            sleeps.append(interval)

        await run_account_check_scheduler(
            check_once=check_once,
            sleep=sleep,
            interval_seconds=600,
            iterations=2,
        )

        self.assertEqual(calls, ["check", "check"])
        self.assertEqual(sleeps, [600])


if __name__ == "__main__":
    unittest.main()
