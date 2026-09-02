"""
Lean file checking utilities.
"""

import re
import subprocess
from pathlib import Path
from typing import List, Tuple
from multiprocessing import Pool, cpu_count

# Match Lean diagnostic headers: path:line:col: severity: message
DIAG_RE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s*(?P<sev>error|warning|info)(?:\([^)]*\))?:\s*(?P<msg>.+)",
    re.MULTILINE,
)

# Skip Lake package / VCS trees when scanning a project root.
_SKIP_DIR_NAMES = {".lake", "lake-packages", ".git"}

# Lean sorry warnings that mean the goal is not fully proven.
_SORRY_WARNING_MARKERS = (
    "declaration uses 'sorry'",
    'declaration uses "sorry"',
    "uses 'sorry'",
    'uses "sorry"',
)


def find_lean_files(folder_path: str | Path) -> List[Path]:
    """
    Recursively find all .lean files in a folder.

    Skips `.lake/`, `lake-packages/`, and `.git/` trees so a Lake project
    root does not fan out into Mathlib / dependency sources after `lake build`.

    Args:
        folder_path: Path to the folder to search

    Returns:
        Sorted list of .lean file paths
    """
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Folder does not exist: {folder_path}")

    if not folder.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {folder_path}")

    lean_files = []
    for file_path in folder.rglob("*.lean"):
        if not file_path.is_file():
            continue
        if any(part in _SKIP_DIR_NAMES for part in file_path.parts):
            continue
        lean_files.append(file_path)

    return sorted(lean_files)


def find_lean_project_root(file_path: Path) -> Path:
    """
    Find the Lean project root (directory containing lean-toolchain).

    Args:
        file_path: Path to a file or directory

    Returns:
        Project root path, or the file's parent if not found
    """
    current = file_path.parent if file_path.is_file() else file_path
    while current != current.parent:  # Until reaching root
        lean_toolchain = current / "lean-toolchain"
        if lean_toolchain.exists():
            return current
        current = current.parent
    # If not found, return file's parent directory
    return file_path.parent if file_path.is_file() else file_path


def classify_lean_output(stdout: str, stderr: str, returncode: int) -> Tuple[bool, bool]:
    """
    Classify `lake env lean` output using diagnostic severities.

    Avoids brittle substring checks (`"error" in text`) that false-positive on
    identifiers like `errorMsg` or paths containing the word error, and that
    false-positive sorry on any mention of the tactic name outside a warning.
    """
    combined = f"{stdout}\n{stderr}"
    has_error = returncode != 0
    has_sorry_warning = False

    for match in DIAG_RE.finditer(combined):
        sev = match.group("sev")
        msg = match.group("msg").lower()
        if sev == "error":
            has_error = True
        elif sev == "warning" and any(m in msg for m in _SORRY_WARNING_MARKERS):
            has_sorry_warning = True
        elif sev == "warning" and "sorry" in msg and "declaration uses" in msg:
            has_sorry_warning = True

    # Fallback: unsolved goals are errors in Lean, but some older toolchains
    # may surface residual sorry only as a warning without the exact phrase.
    if not has_sorry_warning and "declaration uses 'sorry'" in combined.lower():
        has_sorry_warning = True

    return has_error, has_sorry_warning


def check_lean_file(file_path: Path) -> Tuple[bool, bool, str, str]:
    """
    Check a single .lean file for errors and sorry warnings.

    Args:
        file_path: Path to the .lean file

    Returns:
        (has_error, has_sorry_warning, stdout, stderr)
    """
    try:
        # Find project root containing lean-toolchain
        project_root = find_lean_project_root(file_path)

        # Use lake env lean command to check the file
        result = subprocess.run(
            ["lake", "env", "lean", str(file_path)],
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout
            cwd=str(project_root),  # Run in project root
        )

        stdout = result.stdout
        stderr = result.stderr
        has_error, has_sorry_warning = classify_lean_output(
            stdout, stderr, result.returncode
        )
        return has_error, has_sorry_warning, stdout, stderr

    except subprocess.TimeoutExpired:
        return True, False, "", "Check timed out (60s)"
    except Exception as e:
        return True, False, "", f"Execution error: {str(e)}"


def _check_wrapper(file_path: Path) -> Tuple[Path, bool, bool, str, str]:
    """
    Wrapper function for multiprocessing.

    Returns:
        (file_path, has_error, has_sorry_warning, stdout, stderr)
    """
    has_error, has_sorry_warning, stdout, stderr = check_lean_file(file_path)
    return (file_path, has_error, has_sorry_warning, stdout, stderr)


def check_lean_files_parallel(
    lean_files: List[Path], num_proc: int = None
) -> List[Tuple[Path, bool, bool, str, str]]:
    """
    Check multiple .lean files in parallel.

    Args:
        lean_files: List of .lean file paths
        num_proc: Number of parallel processes (default: CPU count)

    Returns:
        List of (file_path, has_error, has_sorry_warning, stdout, stderr)
    """
    if num_proc is None:
        num_proc = cpu_count()

    with Pool(processes=num_proc) as pool:
        results = pool.map(_check_wrapper, lean_files)

    return results


def check_folder(
    folder_path: str | Path, num_proc: int = None
) -> Tuple[bool, List[Path], List[Path]]:
    """
    Check all .lean files in a folder.

    Args:
        folder_path: Path to the folder
        num_proc: Number of parallel processes

    Returns:
        (all_passed, error_files, sorry_files)
    """
    lean_files = find_lean_files(folder_path)
    if not lean_files:
        return True, [], []

    results = check_lean_files_parallel(lean_files, num_proc)

    error_files = []
    sorry_files = []

    for file_path, has_error, has_sorry_warning, _, _ in results:
        if has_error:
            error_files.append(file_path)
        elif has_sorry_warning:
            sorry_files.append(file_path)

    all_passed = len(error_files) == 0 and len(sorry_files) == 0
    return all_passed, error_files, sorry_files
