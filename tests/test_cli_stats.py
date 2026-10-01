import json
import tempfile
import unittest
from pathlib import Path
from scripts.cli_stats import analyze_cli_log


class CliStatsTests(unittest.TestCase):
    def test_query_words_are_not_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / "cli.log"
            log.write_text("2026-04-17 01:52:08,119 __main__ INFO "
                           "loogle.search called: query='called succeeded failed exhausted'\n"
                           "2026-04-17 01:52:09,119 __main__ INFO "
                           "loogle.search succeeded: 3 hits\n"
                           "2026-04-17 01:52:10,119 __main__ WARNING "
                           "leansearch.search attempt 1/3 failed; retrying\n")
            result = analyze_cli_log(log, root)
            self.assertEqual(result["by_tool"]["loogle"],
                             {"called": 1, "ok": 1, "fail": 0})
            self.assertEqual(result["by_tool"]["leansearch"]["fail"], 1)
            self.assertEqual(json.loads((root / "cli_stats.json").read_text()), result)


if __name__ == "__main__":
    unittest.main()
