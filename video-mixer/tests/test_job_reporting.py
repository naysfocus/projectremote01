import tempfile
import time
import unittest
from pathlib import Path

from services import job_manager


class JobReportTests(unittest.TestCase):
    def test_completed_job_reports_actual_mp4_count(self):
        reports = []
        job_manager.configure_reporter(lambda event, summary: reports.append((event, summary)))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a").mkdir()
            (root / "a" / "video_0001.mp4").write_bytes(b"x")
            (root / "a" / "video_0002.mp4").write_bytes(b"x")
            jid = "testjob"
            job_manager.JOBS[jid] = {
                "status": "done",
                "startedAt": time.time() - 5,
                "finishedAt": time.time(),
                "done": 2,
                "perMode": {"horizontal": {"total": 2, "done": 2}},
                "meta": {
                    "outputDir": str(root),
                    "runTag": "20260805_100000",
                    "clientTimeZone": "Asia/Jakarta",
                    "clientUtcOffsetMinutes": -420,
                    "clientLocalStartedAt": "2026-08-05T10:00:00",
                },
            }
            job_manager._report_completed_job(jid)
        self.assertEqual(len(reports), 1)
        event, summary = reports[0]
        self.assertEqual(event, "generate_completed")
        self.assertEqual(summary["video_count"], 2)
        self.assertEqual(summary["mode"], "horizontal")
        self.assertEqual(summary["client_timezone"], "Asia/Jakarta")
        self.assertEqual(summary["client_utc_offset_minutes"], -420)


if __name__ == "__main__":
    unittest.main()
