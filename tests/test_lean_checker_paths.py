import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("lean_checker", Path(__file__).resolve().parents[1] / "scripts/lean_checker.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class LeanCheckerPathTests(unittest.TestCase):
    def test_relative_source_remains_valid_after_changing_to_project_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            project = root / "project"
            source = project / "Proofs" / "Main.lean"
            source.parent.mkdir(parents=True)
            source.write_text("example : True := by trivial\n")
            (project / "lean-toolchain").write_text("leanprover/lean4:v4.27.0\n")
            previous = Path.cwd()
            try:
                os.chdir(root)
                def compile_file(command, **kwargs):
                    cwd = Path(kwargs["cwd"])
                    actual = cwd / command[-1]
                    self.assertEqual(cwd, project)
                    self.assertEqual(actual.resolve(), source)
                    self.assertTrue(actual.is_file())
                    return subprocess.CompletedProcess(command, 0, "", "")
                with patch.object(checker.subprocess, "run", side_effect=compile_file):
                    self.assertEqual(checker.check_lean_file(Path("project/Proofs/Main.lean")), (False, False, "", ""))
            finally:
                os.chdir(previous)

    def test_relative_directory_finds_ancestor_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            (project / "lean-toolchain").touch()
            (project / "Proofs").mkdir()
            previous = Path.cwd()
            try:
                os.chdir(project / "Proofs")
                self.assertEqual(checker.find_lean_project_root(Path(".")), project)
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
