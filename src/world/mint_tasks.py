"""Task-based mint system (Plan #269).

Provides objective, verifiable task completion as an alternative to LLM-based
quality scoring. Tasks have public tests (agents can see/run) and hidden tests
(kernel runs secretly to prevent gaming).

Flow:
1. Agent queries mint_tasks to see available tasks
2. Agent reads task details including public tests
3. Agent builds artifact with run() function
4. Agent submits via submit_to_task action
5. Kernel runs public tests (detailed results)
6. Kernel runs hidden tests (pass/fail only)
7. All pass -> reward distributed, task closed
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .ledger import Ledger
    from .artifacts import Artifact, ArtifactStore
    from .executor import SafeExecutor
    from .logger import EventLogger


@dataclass
class TaskTest:
    """A single test case for a task."""

    test_id: str
    description: str
    invoke_args: list[Any]  # Args to pass to run()
    expected_result: Any
    assertion_type: str = "equals"  # equals, contains, type_is, truthy

    def to_dict(self, include_expected: bool = True) -> dict[str, Any]:
        """Convert to dict for API responses.

        Args:
            include_expected: If False, hide expected_result (for hidden tests)
        """
        result = {
            "test_id": self.test_id,
            "description": self.description,
            "invoke_args": self.invoke_args,
            "assertion_type": self.assertion_type,
        }
        if include_expected:
            result["expected_result"] = self.expected_result
        return result


@dataclass
class TaskTestResult:
    """Result from running a single test."""

    test_id: str
    passed: bool
    expected: Any | None = None  # Only shown for public tests
    actual: Any | None = None  # Only shown for public tests
    error: str | None = None

    def to_dict(self, is_public: bool = True) -> dict[str, Any]:
        """Convert to dict for API responses."""
        result = {
            "test_id": self.test_id,
            "passed": self.passed,
        }
        if is_public:
            result["expected"] = self.expected
            result["actual"] = self.actual
            if self.error:
                result["error"] = self.error
        return result


@dataclass
class MintTask:
    """A task that agents can complete to earn scrip."""

    task_id: str
    description: str
    reward: int  # Scrip reward for completion
    public_tests: list[TaskTest] = field(default_factory=list)
    hidden_tests: list[TaskTest] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    completed_by: str | None = None  # Principal ID who completed it
    completed_at: float | None = None

    @property
    def is_open(self) -> bool:
        """Check if task is still available for completion."""
        if self.completed_by is not None:
            return False
        if self.expires_at is not None and time.time() > self.expires_at:
            return False
        return True

    def to_dict(self, include_hidden: bool = False) -> dict[str, Any]:
        """Convert to dict for API responses.

        Args:
            include_hidden: If True, include hidden tests (NEVER do this for agents)
        """
        result = {
            "task_id": self.task_id,
            "description": self.description,
            "reward": self.reward,
            "public_tests": [t.to_dict() for t in self.public_tests],
            "is_open": self.is_open,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "completed_by": self.completed_by,
            "completed_at": self.completed_at,
        }
        if include_hidden:
            result["hidden_tests"] = [t.to_dict() for t in self.hidden_tests]
        return result


@dataclass
class TaskSubmissionResult:
    """Result from submitting an artifact for a task."""

    success: bool
    task_id: str
    artifact_id: str
    public_results: list[TaskTestResult] = field(default_factory=list)
    hidden_passed: bool | None = None  # None if public tests failed
    reward_earned: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for API responses."""
        return {
            "success": self.success,
            "task_id": self.task_id,
            "artifact_id": self.artifact_id,
            "public_tests": {
                "passed": sum(1 for r in self.public_results if r.passed),
                "total": len(self.public_results),
                "results": [r.to_dict(is_public=True) for r in self.public_results],
            },
            "hidden_tests": {
                "passed": self.hidden_passed,
            } if self.hidden_passed is not None else None,
            "reward_earned": self.reward_earned,
            "message": self.message,
        }


class MintTaskManager:
    """Manages task-based mint system.

    Provides objective, verifiable task completion as an alternative to
    LLM-based quality scoring.
    """

    def __init__(
        self,
        ledger: Ledger,
        artifacts: ArtifactStore,
        executor: SafeExecutor,
        logger: EventLogger,
    ) -> None:
        """Initialize MintTaskManager.

        Args:
            ledger: For scrip operations
            artifacts: For artifact access
            executor: For running tests
            logger: For event logging
        """
        self._ledger = ledger
        self._artifacts = artifacts
        self._executor = executor
        self._logger = logger
        self._tasks: dict[str, MintTask] = {}

    def seed_from_config(self, seed_tasks: list[dict[str, Any]]) -> None:
        """Load tasks from configuration.

        Args:
            seed_tasks: List of task configs from config.yaml
        """
        for task_config in seed_tasks:
            task_id = task_config["task_id"]

            # Parse public tests
            public_tests = []
            for i, test_cfg in enumerate(task_config.get("public_tests", [])):
                public_tests.append(TaskTest(
                    test_id=f"{task_id}_public_{i}",
                    description=test_cfg.get("description", f"Test {i}"),
                    invoke_args=test_cfg["args"],
                    expected_result=test_cfg["expected"],
                    assertion_type=test_cfg.get("assertion", "equals"),
                ))

            # Parse hidden tests
            hidden_tests = []
            for i, test_cfg in enumerate(task_config.get("hidden_tests", [])):
                hidden_tests.append(TaskTest(
                    test_id=f"{task_id}_hidden_{i}",
                    description=test_cfg.get("description", f"Hidden test {i}"),
                    invoke_args=test_cfg["args"],
                    expected_result=test_cfg["expected"],
                    assertion_type=test_cfg.get("assertion", "equals"),
                ))

            # Calculate expiration if specified
            expires_at = None
            if "expires_after_seconds" in task_config:
                expires_at = time.time() + task_config["expires_after_seconds"]

            task = MintTask(
                task_id=task_id,
                description=task_config["description"],
                reward=task_config["reward"],
                public_tests=public_tests,
                hidden_tests=hidden_tests,
                expires_at=expires_at,
            )
            self._tasks[task_id] = task

            self._logger.log("mint_task_created", {
                "task_id": task_id,
                "description": task_config["description"],
                "reward": task_config["reward"],
                "public_tests_count": len(public_tests),
                "hidden_tests_count": len(hidden_tests),
            })

    def get_available_tasks(self, limit: int = 20) -> list[MintTask]:
        """Get list of open tasks.

        Args:
            limit: Max tasks to return

        Returns:
            List of open tasks (hidden tests excluded)
        """
        return [
            task for task in list(self._tasks.values())[:limit]
            if task.is_open
        ]

    def get_task(self, task_id: str) -> MintTask | None:
        """Get a specific task.

        Args:
            task_id: Task ID to look up

        Returns:
            Task if found, None otherwise (hidden tests excluded from to_dict)
        """
        return self._tasks.get(task_id)

    def _run_test(
        self,
        artifact: Artifact,
        test: TaskTest,
    ) -> TaskTestResult:
        """Run a single test against an artifact.

        Args:
            artifact: Artifact to test
            test: Test to run

        Returns:
            Test result
        """
        try:
            # Execute artifact's run() with test args
            exec_result = self._executor.execute(
                code=artifact.code,
                args=test.invoke_args,
            )

            if not exec_result.get("success", False):
                return TaskTestResult(
                    test_id=test.test_id,
                    passed=False,
                    expected=test.expected_result,
                    actual=None,
                    error=exec_result.get("error", "Execution failed"),
                )

            actual = exec_result.get("result")

            # Check assertion
            passed = self._check_assertion(
                actual,
                test.expected_result,
                test.assertion_type,
            )

            return TaskTestResult(
                test_id=test.test_id,
                passed=passed,
                expected=test.expected_result,
                actual=actual,
                error=None,
            )

        except Exception as e:
            return TaskTestResult(
                test_id=test.test_id,
                passed=False,
                expected=test.expected_result,
                actual=None,
                error=str(e),
            )

    def _check_assertion(
        self,
        actual: Any,
        expected: Any,
        assertion_type: str,
    ) -> bool:
        """Check if actual value matches expected based on assertion type.

        Args:
            actual: Actual result from execution
            expected: Expected result
            assertion_type: Type of assertion

        Returns:
            True if assertion passes
        """
        if assertion_type == "equals":
            return bool(actual == expected)
        elif assertion_type == "contains":
            return bool(expected in actual)
        elif assertion_type == "type_is":
            return bool(type(actual).__name__ == expected)
        elif assertion_type == "truthy":
            return bool(actual)
        else:
            # Unknown assertion type - fail safe
            return False

    def submit_solution(
        self,
        principal_id: str,
        artifact_id: str,
        task_id: str,
    ) -> TaskSubmissionResult:
        """Submit an artifact as solution to a task.

        Args:
            principal_id: Who is submitting
            artifact_id: Artifact to test
            task_id: Task to solve

        Returns:
            Submission result with test results and reward info
        """
        # Validate task exists and is open
        task = self._tasks.get(task_id)
        if task is None:
            return TaskSubmissionResult(
                success=False,
                task_id=task_id,
                artifact_id=artifact_id,
                message=f"Task '{task_id}' not found",
            )

        if not task.is_open:
            return TaskSubmissionResult(
                success=False,
                task_id=task_id,
                artifact_id=artifact_id,
                message=f"Task '{task_id}' is no longer open",
            )

        # Validate artifact exists
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            return TaskSubmissionResult(
                success=False,
                task_id=task_id,
                artifact_id=artifact_id,
                message=f"Artifact '{artifact_id}' not found",
            )

        # Validate caller has write permission (ADR-0028: no hardcoded created_by checks)
        authorized_writer = (artifact.metadata or {}).get("authorized_writer")
        authorized_principal = (artifact.metadata or {}).get("authorized_principal")
        if principal_id not in (authorized_writer, authorized_principal):
            return TaskSubmissionResult(
                success=False,
                task_id=task_id,
                artifact_id=artifact_id,
                message=f"Not authorized to submit artifact '{artifact_id}'",
            )

        # Validate artifact has code
        if not artifact.code:
            return TaskSubmissionResult(
                success=False,
                task_id=task_id,
                artifact_id=artifact_id,
                message=f"Artifact '{artifact_id}' has no executable code",
            )

        # Run public tests
        public_results = [
            self._run_test(artifact, test)
            for test in task.public_tests
        ]
        public_passed = all(r.passed for r in public_results)

        # Log submission attempt
        self._logger.log("mint_task_submission", {
            "principal_id": principal_id,
            "artifact_id": artifact_id,
            "task_id": task_id,
            "public_tests_passed": sum(1 for r in public_results if r.passed),
            "public_tests_total": len(public_results),
        })

        # If public tests failed, don't run hidden tests
        if not public_passed:
            return TaskSubmissionResult(
                success=False,
                task_id=task_id,
                artifact_id=artifact_id,
                public_results=public_results,
                hidden_passed=None,  # Didn't run
                message="Public tests failed. Fix issues and try again.",
            )

        # Run hidden tests
        hidden_results = [
            self._run_test(artifact, test)
            for test in task.hidden_tests
        ]
        hidden_passed = all(r.passed for r in hidden_results)

        if not hidden_passed:
            return TaskSubmissionResult(
                success=False,
                task_id=task_id,
                artifact_id=artifact_id,
                public_results=public_results,
                hidden_passed=False,  # Failed but no details
                message="Public tests passed, but hidden tests failed.",
            )

        # All tests passed! Award reward and mark complete
        self._ledger.credit_scrip(principal_id, task.reward)
        task.completed_by = principal_id
        task.completed_at = time.time()

        # Log completion
        self._logger.log("mint_task_completed", {
            "principal_id": principal_id,
            "artifact_id": artifact_id,
            "task_id": task_id,
            "reward": task.reward,
        })

        return TaskSubmissionResult(
            success=True,
            task_id=task_id,
            artifact_id=artifact_id,
            public_results=public_results,
            hidden_passed=True,
            reward_earned=task.reward,
            message=f"All tests passed! Earned {task.reward} scrip.",
        )
