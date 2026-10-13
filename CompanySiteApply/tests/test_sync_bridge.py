# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [TEST_SYNC_BRIDGE_INIT]
# Timestamp: 2026-10-13 18:00:00 +05:30
# Issue / Context: Sync Playwright calls crash inside --autonomous's event
#                  loop (task-644 class). Bridge must work in both contexts.
# ==============================================================================

import asyncio
import unittest

from CompanySiteApply.utils.sync_bridge import call_sync_offloaded


class TestSyncBridge(unittest.TestCase):
    def test_inline_without_loop(self):
        self.assertEqual(call_sync_offloaded(lambda x: x * 2, 21), 42)

    def test_offloaded_inside_running_loop(self):
        async def _run():
            return call_sync_offloaded(lambda: "threaded-ok")

        self.assertEqual(asyncio.run(_run()), "threaded-ok")

    def test_exceptions_propagate(self):
        def _boom():
            raise ValueError("bridge-proof")

        with self.assertRaises(ValueError):
            call_sync_offloaded(_boom)


if __name__ == "__main__":
    unittest.main()
