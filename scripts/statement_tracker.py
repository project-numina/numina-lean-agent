"""
Statement tracking utilities for detecting changes in theorem/lemma statements.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Literal, Optional

from .extract_sublemmas import LeanCodeParser


@dataclass
class StatementSnapshot:
    """Snapshot of a single statement."""
    file_path: Path
    name: str
    statement: str  # Statement without proof


@dataclass
class StatementChange:
    """Record of a statement change."""
    file_path: Path
    name: str
    original: str
    current: str
    change_type: Literal["modified", "added", "removed"]

    def __str__(self) -> str:
        return f"[{self.change_type}] {self.file_path}:{self.name}"


def extract_statements_from_file(file_path: Path) -> Dict[str, str]:
    """
    Extract all theorem/lemma statements from a Lean file.
    Returns a dict mapping theorem/lemma names to their statements (without proofs).
    """
    try:
        if not file_path.exists():
            return {}
        code = file_path.read_text(encoding="utf-8")
        parser = LeanCodeParser(code)
        blocks = parser.extract_all_blocks(keys=["theorem", "lemma"], allow_overlap=False)

        statements = {}
        for block in blocks:
            name = block["info"]["name"]
            statement = block["info"]["statement"]
            if name:
                statements[name] = statement

        return statements
    except Exception as e:
        print(f"[warn] Failed to extract statements from {file_path}: {e}")
        return {}


def normalize_statement(statement: str) -> str:
    """Normalize whitespace for comparison."""
    return " ".join(statement.split())


class StatementTracker:
    """
    Track statement changes across Claude runs.

    Usage:
        tracker = StatementTracker(files=[Path("file.lean")])
        # ... run claude ...
        changes = tracker.check()
        if changes:
            for c in changes:
                print(f"  {c}")
    """

    def __init__(self, files: List[Path]):
        """
        Initialize tracker with files to monitor.

        Args:
            files: List of .lean files to track
        """
        self.files = [Path(f).resolve() for f in files]
        self.initial_snapshots: Dict[Path, Dict[str, str]] = {}  # {file_path: {statement_name: statement}}
        self.initial_file_contents: Dict[Path, str] = {}  # {file_path: full_file_content}
        self._capture_initial()

    def _capture_initial(self) -> None:
        """Capture initial state of all statements and full file contents."""
        for f in self.files:
            # Store full file content for restoration
            if f.exists():
                self.initial_file_contents[f] = f.read_text(encoding="utf-8")
            # Store statements
            self.initial_snapshots[f] = extract_statements_from_file(f)

    def check(self) -> List[StatementChange]:
        """
        Check current state against initial state.

        Returns:
            List of statement changes (compared to initial state)
        """
        changes = []

        for f in self.files:
            initial = self.initial_snapshots.get(f, {})
            current = extract_statements_from_file(f)

            all_names = set(initial.keys()) | set(current.keys())

            for name in all_names:
                orig = initial.get(name, "")
                curr = current.get(name, "")

                orig_norm = normalize_statement(orig)
                curr_norm = normalize_statement(curr)

                if orig_norm != curr_norm:
                    if not orig:
                        change_type = "added"
                    elif not curr:
                        change_type = "removed"
                    else:
                        change_type = "modified"

                    changes.append(StatementChange(
                        file_path=f,
                        name=name,
                        original=orig,
                        current=curr,
                        change_type=change_type,
                    ))

        return changes
    
    def check_initial_statements(self) -> tuple[bool, List[StatementChange]]:
        """
        Using the check function, check if any initial statements are modified or removed.
        
        Returns:
            Tuple of (is_valid, changes):
            - is_valid: True if all initial statements are unchanged, False if any were modified or removed
            - changes: List of all StatementChange objects (modified or removed), empty if all valid
        """
        changes = self.check()
        # Filter to only modified or removed changes (not added)
        relevant_changes = [c for c in changes if c.change_type in ["modified", "removed"]]
        is_valid = len(relevant_changes) == 0
        return is_valid, relevant_changes

    def get_initial_statements(self) -> Dict[Path, Dict[str, str]]:
        """Get the initial snapshots."""
        return self.initial_snapshots.copy()

    def restore_initial_statements(self, changes: Optional[List[StatementChange]] = None) -> None:
        """
        Restore all files to their initial statement state.
        This replaces the current theorem/lemma statements with the original ones.
        If a file was deleted, restore it from the stored initial content.
        
        Args:
            changes: Optional list of StatementChange objects to restore. If provided, only restore these changes.
                    If not provided, check all files for changes.
        """
        # If no changes provided, check for them
        if changes is None:
            _, changes = self.check_initial_statements()
        
        if not changes:
            print("[info] No statement changes to restore")
            return
        
        # Group changes by file
        changes_by_file: Dict[Path, List[StatementChange]] = {}
        for change in changes:
            if change.file_path not in changes_by_file:
                changes_by_file[change.file_path] = []
            changes_by_file[change.file_path].append(change)
        
        # First, check if any files were deleted and restore them
        # Also track which files were restored so we skip processing them again
        restored_files = set()
        for f in self.files:
            initial_content = self.initial_file_contents.get(f)
            if not initial_content:
                continue
            
            if not f.exists():
                # File was deleted, restore from initial content
                print(f"[info] File {f} was deleted, restoring from initial content...")
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(initial_content, encoding="utf-8")
                print(f"[info] Restored file {f}")
                restored_files.add(f)
        
        # Restore modified/removed statements by rewriting the file from the
        # captured original bytes. Replacing LeanCodeParser "cleaned" block
        # text into the on-disk file is a silent no-op whenever comments,
        # blank lines, or `:=` spacing differ from the cleaned form — which
        # is the common MiniF2f / agent-edited case. Full-file restore is
        # already used for deleted files above; use it for integrity too.
        for f, file_changes in changes_by_file.items():
            if f in restored_files:
                continue

            initial_content = self.initial_file_contents.get(f)
            if not initial_content:
                continue

            relevant = [c for c in file_changes if c.change_type in ("modified", "removed")]
            if not relevant:
                continue

            current_content = f.read_text(encoding="utf-8") if f.exists() else ""
            if current_content == initial_content:
                print(f"[info] {f} already matches initial content; nothing to restore")
                continue

            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(initial_content, encoding="utf-8")
            names = ", ".join(c.name for c in relevant)
            print(f"[info] Restored {f} to initial content (statements: {names})")


def extract_claude_usage(claude_result: Optional[dict]) -> Optional[dict]:
    """Extract usage/cost info from a parsed type:'result' JSON dict."""
    if not claude_result or claude_result.get("type") != "result":
        return None
    usage = claude_result.get("usage", {})
    return {
        "total_cost_usd": claude_result.get("total_cost_usd"),
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
        "num_turns": claude_result.get("num_turns"),
        "duration_api_ms": claude_result.get("duration_api_ms"),
        "session_id": claude_result.get("session_id"),
    }


@dataclass
class RoundResult:
    """Result of a single run_claude_once call."""
    round_number: int
    end_reason: Optional[str]  # COMPLETE / LIMIT / None
    returncode: int
    statement_changes: List[StatementChange] = field(default_factory=list)
    duration_seconds: float = 0.0
    line_counts: dict = field(default_factory=dict)  # {filename: line_count}
    claude_usage: Optional[dict] = None  # Token/cost info from stream-json result

    def has_statement_changes(self) -> bool:
        """Check if any statements were changed in this round."""
        return len(self.statement_changes) > 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "round_number": self.round_number,
            "end_reason": self.end_reason,
            "returncode": self.returncode,
            "duration_seconds": self.duration_seconds,
            "statement_changes": [
                {
                    "file_path": str(c.file_path),
                    "name": c.name,
                    "original": c.original,
                    "current": c.current,
                    "change_type": c.change_type,
                }
                for c in self.statement_changes
            ],
            "line_counts": self.line_counts,
            "claude_usage": self.claude_usage,
        }
