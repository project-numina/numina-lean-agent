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
    mcp_log_dir: Optional[str | Path] = None  # MCP log directory (sets $MCP_LOG_DIR)
    mcp_log_name: Optional[str] = None  # MCP log name (sets $MCP_LOG_NAME before claude command)

    # Optional fields - Claude parameters
    permission_mode: str = "bypassPermissions"  # Permission mode
    output_format: Optional[str] = None  # Output format (json / None)

    # Optional fields - Statement tracking
    track_statements: bool = True  # Whether to track statement changes
    on_statement_change: Literal["error", "warn"] = "warn"  # Action on statement change

    # Optional fields - Git integration
    git_commit: bool = False  # Whether to create git commits after each round

    # Optional fields - Parallel execution
    isolate: bool = False  # Enable MCP session isolation (sets LEAN_PROJECT_PATH)

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
        if self.mcp_log_dir:
            self.mcp_log_dir = Path(self.mcp_log_dir).resolve()

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

    def _find_lean_project_root(self) -> Optional[Path]:
        """Walk up from target_path to find the Lean project root (contains lean-toolchain)."""
        search = self.target_path if self.target_path.is_dir() else self.target_path.parent
        while search != search.parent:
            if (search / "lean-toolchain").is_file():
                return search
            search = search.parent
        return None

    def build_env(self) -> dict:
        """Build environment variables (including MCP_LOG_DIR, MCP_LOG_NAME, LEAN_PROJECT_PATH)."""
        env = os.environ.copy()
        if self.mcp_log_dir:
            # Ensure directory exists
            Path(self.mcp_log_dir).mkdir(parents=True, exist_ok=True)
            env["MCP_LOG_DIR"] = str(self.mcp_log_dir)
        if self.mcp_log_name:
            env["MCP_LOG_NAME"] = self.mcp_log_name
        if self.isolate:
            project_root = self._find_lean_project_root()
            if project_root:
                env["LEAN_PROJECT_PATH"] = str(project_root)
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
            "mcp_log_dir": str(self.mcp_log_dir) if self.mcp_log_dir else None,
            "mcp_log_name": self.mcp_log_name,
            "permission_mode": self.permission_mode,
            "output_format": self.output_format,
            "track_statements": self.track_statements,
            "on_statement_change": self.on_statement_change,
            "git_commit": self.git_commit,
            "isolate": self.isolate,
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
            mcp_log_dir=data.get("mcp_log_dir"),
            mcp_log_name=data.get("mcp_log_name"),
            permission_mode=data.get("permission_mode", "bypassPermissions"),
            output_format=data.get("output_format"),
            track_statements=data.get("track_statements", True),
            on_statement_change=data.get("on_statement_change", "warn"),
            git_commit=data.get("git_commit", False),
            isolate=data.get("isolate", False),
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
    mcp_stats: Optional[dict] = None  # MCP tool call statistics
    round_results: List["RoundResult"] = field(default_factory=list)  # Per-round results
    statement_changed: bool = False  # Whether any statement was changed

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
            "mcp_stats": self.mcp_stats,
            "round_results": [rr.to_dict() for rr in self.round_results],
            "statement_changed": self.statement_changed,
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
            mcp_stats=data.get("mcp_stats"),
            round_results=[],  # Not deserializing round_results for simplicity
            statement_changed=data.get("statement_changed", False),
        )
