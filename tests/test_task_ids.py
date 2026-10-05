import importlib.util
from datetime import datetime
from pathlib import Path
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("numina_task", Path(__file__).resolve().parents[1] / "scripts/task.py")
task = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = task
spec.loader.exec_module(task)


class TaskIdTests(unittest.TestCase):
    def test_parallel_same_stem_tasks_have_separate_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = datetime(2026, 1, 1, 12, 0, 0)
            first = task.TaskMetadata("file", root / "A/Main.lean", created_at=created, result_dir=root / "results")
            second = task.TaskMetadata("file", root / "B/Main.lean", created_at=created, result_dir=root / "results")
            self.assertNotEqual(first.task_id, second.task_id)
            self.assertNotEqual(first.build_env()["CLI_LOG_PATH"], second.build_env()["CLI_LOG_PATH"])
            self.assertEqual(task.TaskMetadata.from_dict(first.to_dict()).task_id, first.task_id)

    def test_explicit_id_is_preserved(self):
        metadata = task.TaskMetadata("file", "Main.lean", task_id="resume-this-task")
        self.assertEqual(metadata.task_id, "resume-this-task")
        self.assertEqual(task.TaskMetadata.from_dict(metadata.to_dict()).task_id, "resume-this-task")


if __name__ == "__main__":
    unittest.main()
