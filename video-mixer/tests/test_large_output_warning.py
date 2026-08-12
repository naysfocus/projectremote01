import unittest

from services.calculator import calculate_estimates
from services.output_safety import LARGE_OUTPUT_WARNING_THRESHOLD, render_output_warning


class LargeOutputWarningTests(unittest.TestCase):
    @staticmethod
    def payload(h=8, v=7):
        return {
            "h": h,
            "v": v,
            "modes": {
                "horizontal": True,
                "mixHorizontal": False,
                "mixHorizontalLinear": False,
                "mixHorizontalLinearUnique": False,
            },
            "batch": {"enabled": False, "size": None},
            "grid": [[{"label": f"T{r+1}C{c+1}", "path": f"/tmp/{r}_{c}.mp4"} for c in range(v)] for r in range(h)],
        }

    def test_large_unlimited_job_requires_warning(self):
        total, per_mode, token = render_output_warning(self.payload(), calculate_estimates)
        self.assertGreater(total, LARGE_OUTPUT_WARNING_THRESHOLD)
        self.assertEqual(per_mode["horizontal"], total)
        self.assertEqual(len(token), 64)

    def test_limit_30000_does_not_cross_warning_threshold(self):
        payload = self.payload()
        payload["batch"] = {"enabled": True, "size": 30000}
        total, _, _ = render_output_warning(payload, calculate_estimates)
        self.assertEqual(total, 30000)
        self.assertFalse(total > LARGE_OUTPUT_WARNING_THRESHOLD)

    def test_configuration_change_invalidates_confirmation(self):
        payload = self.payload()
        _, _, first_token = render_output_warning(payload, calculate_estimates)
        payload["modes"]["mixHorizontal"] = True
        _, _, changed_token = render_output_warning(payload, calculate_estimates)
        self.assertNotEqual(first_token, changed_token)

    def test_no_hard_maximum_is_applied(self):
        payload = self.payload(10, 10)
        payload["modes"] = {
            "horizontal": False,
            "mixHorizontal": True,
            "mixHorizontalLinear": False,
            "mixHorizontalLinearUnique": False,
        }
        total, _, _ = render_output_warning(payload, calculate_estimates)
        self.assertGreater(total, 30_000)
        self.assertGreater(total, 30_000_000)


if __name__ == "__main__":
    unittest.main()
