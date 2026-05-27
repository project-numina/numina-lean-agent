"""
Task metadata and result definitions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional, List, TYPE_CHECKING
import os

if TYPE_CHECKING:
    from .statement_tracker import RoundResult, StatementChange
    from .safe_verify import SafeVerifyResult


@dataclass
class TaskMetadata:
    """Task metadata for Claude Lean proving tasks."""

    # Required fields
    task_type: Literal["file", "folder"]  # Task type
    target_path: str | Path  # Target path (file or folder)

    # Optional fields - Prompt (one of these must be provided)
    prompt: Optional[str] = None  # Direct prompt content
    prompt_file: Optional[str | Path] = None  # Read prompt from file

    # Optional fields - Execution parameters
    cwd: Optional[str | Path] = None  # Claude working directory
    max_rounds: int = 20  # Maximum rounds (continue count limit)
    check_after_complete: bool = True  # Whether to check lean files after completion
    allow_sorry: bool = False  # Whether to allow sorry in lean files (default: False)
    sleep_between_rounds: float = 1.0  # Sleep between rounds (seconds)

    # Optional fields - Result output
    result_dir: Optional[str | Path] = None  # Result output directory (JSON files)

    # Optional fields - Claude parameters
    permission_mode: str = "bypassPermissions"  # Permission mode
    output_format: Optional[str] = None  # Output format (json / None)

    # Optional fields - Statement tracking
    track_statements: bool = True  # Whether to track statement changes
    on_statement_change: Literal["error", "warn"] = "warn"  # Action on statement change

    # Optional fields - Git integration
    git_commit: bool = False  # Whether to create git commits after each round

    # Optional fields - SafeVerify post-completion check
    safe_verify_path: Optional[str | Path] = None  # Path to safe_verify binary; None = skip
    safe_verify_cwd: Optional[str | Path] = None  # cwd for lake env (falls back to task.cwd)

    # Auto-generated fields
    created_at: datetime = field(default_factory=datetime.now)
    task_id: str = field(default="")  # Auto-generated unique ID

    def __post_init__(self):
        # Auto-generate task_id
        if not self.task_id:
            timestamp = self.created_at.strftime("%Y%m%d_%H%M%S")
            target_name = Path(self.target_path).stem
            self.task_id = f"{self.task_type}_{target_name}_{timestamp}"

        # Normalize paths
        self.target_path = Path(self.target_path).resolve()
        if self.cwd:
            self.cwd = Path(self.cwd).resolve()
        if self.prompt_file:
            self.prompt_file = Path(self.prompt_file).resolve()
        if self.result_dir:
            self.result_dir = Path(self.result_dir).resolve()
        if self.safe_verify_path:
            self.safe_verify_path = Path(self.safe_verify_path).resolve()
        if self.safe_verify_cwd:
            self.safe_verify_cwd = Path(self.safe_verify_cwd).resolve()

    def get_prompt(self) -> str:
        """Get prompt content (from prompt or prompt_file), with target path prepended."""
        if self.prompt:
            base_prompt = self.prompt.strip()
        elif self.prompt_file and Path(self.prompt_file).exists():
            base_prompt = Path(self.prompt_file).read_text(encoding="utf-8").strip()
        else:
            raise ValueError("Either prompt or prompt_file must be provided")

        # Prepend target path information
        target_type = "file" if self.task_type == "file" else "folder"
        target_info = f"The target {target_type} is: {self.target_path}\n\n"
        return target_info + base_prompt

    def get_check_path(self) -> Path:
        """Get the path to check for lean files."""
        return self.target_path

    def build_env(self) -> dict:
        """Build environment variables for the Claude subprocess.

        When `result_dir` is set, point `CLI_LOG_PATH` at a per-task log file so
        that `skills/cli/*.py` invocations write into an isolated file (no
        cross-task pollution). Falls through to the skill script's default
        (`<repo_root>/cli.log`) when `result_dir` is absent.
        """
        env = os.environ.copy()
        if self.result_dir:
            cli_log_path = Path(self.result_dir) / self.task_id / "cli.log"
            cli_log_path.parent.mkdir(parents=True, exist_ok=True)
            env["CLI_LOG_PATH"] = str(cli_log_path)
        return env

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "target_path": str(self.target_path),
            "prompt": self.prompt,
            "prompt_file": str(self.prompt_file) if self.prompt_file else None,
            "cwd": str(self.cwd) if self.cwd else None,
            "max_rounds": self.max_rounds,
            "check_after_complete": self.check_after_complete,
            "allow_sorry": self.allow_sorry,
            "sleep_between_rounds": self.sleep_between_rounds,
            "result_dir": str(self.result_dir) if self.result_dir else None,
            "permission_mode": self.permission_mode,
            "output_format": self.output_format,
            "track_statements": self.track_statements,
            "on_statement_change": self.on_statement_change,
            "git_commit": self.git_commit,
            "safe_verify_path": str(self.safe_verify_path) if self.safe_verify_path else None,
            "safe_verify_cwd": str(self.safe_verify_cwd) if self.safe_verify_cwd else None,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskMetadata":
        """Create TaskMetadata from dictionary."""
        # Handle created_at if present
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        return cls(
            task_type=data["task_type"],
            target_path=data["target_path"],
            prompt=data.get("prompt"),
            prompt_file=data.get("prompt_file"),
            cwd=data.get("cwd"),
            max_rounds=data.get("max_rounds", 20),
            check_after_complete=data.get("check_after_complete", True),
            allow_sorry=data.get("allow_sorry", False),
            sleep_between_rounds=data.get("sleep_between_rounds", 1.0),
            result_dir=data.get("result_dir"),
            permission_mode=data.get("permission_mode", "bypassPermissions"),
            output_format=data.get("output_format"),
            track_statements=data.get("track_statements", True),
            on_statement_change=data.get("on_statement_change", "warn"),
            git_commit=data.get("git_commit", False),
            safe_verify_path=data.get("safe_verify_path"),
            safe_verify_cwd=data.get("safe_verify_cwd"),
            created_at=created_at,
            task_id=data.get("task_id", ""),
        )


@dataclass
class TaskResult:
    """Task execution result."""

    task_id: str
    success: bool
    end_reason: Optional[str]  # COMPLETE / LIMIT / ERROR
    rounds_used: int
    start_time: datetime
    end_time: datetime
    error_message: Optional[str] = None
    cli_stats: Optional[dict] = None  # CLI skill call statistics (from cli.log slice)
    round_results: List["RoundResult"] = field(default_factory=list)  # Per-round results
    statement_changed: bool = False  # Whether any statement was changed
    safe_verify_result: Optional["SafeVerifyResult"] = None  # SafeVerify check result

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    def get_all_statement_changes(self) -> List["StatementChange"]:
        """Get all statement changes across all rounds."""
        changes = []
        for rr in self.round_results:
            changes.extend(rr.statement_changes)
        return changes

    @property
    def total_cost_usd(self) -> float:
        """Sum total_cost_usd across all rounds."""
        total = 0.0
        for rr in self.round_results:
            if rr.claude_usage and rr.claude_usage.get("total_cost_usd"):
                total += rr.claude_usage["total_cost_usd"]
        return total

    @property
    def total_usage(self) -> dict:
        """Aggregate token counts across all rounds."""
        keys = ["input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"]
        totals = {k: 0 for k in keys}
        for rr in self.round_results:
            if rr.claude_usage:
                for k in keys:
                    totals[k] += rr.claude_usage.get(k, 0)
        return totals

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "end_reason": self.end_reason,
            "rounds_used": self.rounds_used,
            "duration_seconds": self.duration_seconds,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "error_message": self.error_message,
            "cli_stats": self.cli_stats,
            "round_results": [rr.to_dict() for rr in self.round_results],
            "statement_changed": self.statement_changed,
            "total_cost_usd": self.total_cost_usd,
            "total_usage": self.total_usage,
            "safe_verify": {
                "ran": self.safe_verify_result.ran,
                "success": self.safe_verify_result.success,
                "returncode": self.safe_verify_result.returncode,
                "error_message": self.safe_verify_result.error_message,
            } if self.safe_verify_result else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskResult":
        """Create TaskResult from dictionary."""
        return cls(
            task_id=data["task_id"],
            success=data["success"],
            end_reason=data.get("end_reason"),
            rounds_used=data["rounds_used"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            error_message=data.get("error_message"),
            cli_stats=data.get("cli_stats") or data.get("mcp_stats"),
            round_results=[],  # Not deserializing round_results for simplicity
            statement_changed=data.get("statement_changed", False),
        )
