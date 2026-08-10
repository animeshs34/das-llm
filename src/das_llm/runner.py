import asyncio
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from das_llm.schemas import (
    SimulationConfig,
    SimulationReport,
    Message,
    ToolExecutionAttempt,
)
from das_llm.seeding import SimulationSeeder
from das_llm.proxy import BoundaryEvaluator
from das_llm.adapter import AgentAdapter
from das_llm.shrinker import DeltaDebugger
from das_llm.drift import ModelDriftTracker
from das_llm.semantic import SemanticEvaluator

logger = logging.getLogger(__name__)


def parse_tool_call(tool_call: Dict[str, Any]) -> Tuple[str, Any]:
    """Helper to extract tool name and arguments from a tool call dictionary."""
    function_data = tool_call.get("function", {})
    tool_name = function_data.get("name", tool_call.get("name", "unknown"))
    raw_args = function_data.get("arguments", tool_call.get("arguments", {}))

    if isinstance(raw_args, str):
        try:
            parsed_args = json.loads(raw_args)
        except Exception:
            parsed_args = raw_args
    else:
        parsed_args = raw_args

    return tool_name, parsed_args


def estimate_tokens(text: str) -> int:
    """Fast approximation of token count based on whitespace and character length."""
    if not text:
        return 0
    return max(1, len(text) // 4)


class SimulationRunner:
    """Async Monte Carlo execution engine for evaluating LLM agent security invariants."""

    MODEL_PRICING_PER_1K = {
        "gpt-4o": 0.005,
        "claude-3-5-sonnet": 0.003,
        "gemma4:latest": 0.0,
        "gemma4:e2b": 0.0,
    }

    def __init__(
        self,
        config: SimulationConfig,
        adapter: AgentAdapter,
        custom_conditions: Optional[Dict[str, Any]] = None,
        expected_fingerprint: Optional[str] = None,
    ):
        self.config = config
        self.adapter = adapter
        self.custom_conditions = custom_conditions
        self.drift_tracker = ModelDriftTracker(expected_fingerprint=expected_fingerprint)
        self.semantic_evaluator = SemanticEvaluator()

    async def run(
        self, prompt: str = "Execute instructions.", das_mock_tools: Optional[Dict[str, Any]] = None
    ) -> SimulationReport:
        """Runs N concurrent simulation iterations, isolating state per worker task."""
        tasks = [
            self._worker_task(iteration_index=i, prompt=prompt, das_mock_tools=das_mock_tools)
            for i in range(self.config.iterations)
        ]
        results = await asyncio.gather(*tasks)

        violations_count = 0
        minimized_traces: List[List[Message]] = []
        violated_invariant_id: Optional[str] = None
        attempted_call_summary: Optional[str] = None
        minimal_failing_payload: Optional[str] = None
        raw_traces: List[Dict[str, Any]] = []

        total_suite_tokens = 0
        drift_warning = False

        for iteration_index, has_violation, trajectory, minimized_trace, first_failed_attempt, attempts, run_tokens in results:
            total_suite_tokens += run_tokens

            trace_entry = {
                "iteration": iteration_index,
                "has_violation": has_violation,
                "tokens_used": run_tokens,
                "trajectory": [
                    item.model_dump() if hasattr(item, "model_dump") else item for item in trajectory
                ],
                "attempts": [a.model_dump() for a in attempts],
            }
            raw_traces.append(trace_entry)

            if has_violation:
                violations_count += 1
                if minimized_trace:
                    minimized_traces.append(minimized_trace)

                if first_failed_attempt and not violated_invariant_id:
                    violated_invariant_id = first_failed_attempt.violated_invariant_id
                    attempted_call_summary = (
                        f"{first_failed_attempt.tool_name}({json.dumps(first_failed_attempt.arguments)})"
                    )

                if not minimal_failing_payload:
                    search_list = (minimized_trace or []) + trajectory
                    for msg in search_list:
                        role = msg.role if isinstance(msg, Message) else (msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", ""))
                        content = msg.content if isinstance(msg, Message) else (msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", ""))
                        if role in ("tool", "user") and content:
                            minimal_failing_payload = str(content)
                            break

        total_runs = self.config.iterations
        violation_rate = violations_count / total_runs if total_runs > 0 else 0.0
        passed = violation_rate <= self.config.max_violation_rate

        return SimulationReport(
            suite_name=self.config.suite_name,
            seed=self.config.seed,
            total_runs=total_runs,
            violations=violations_count,
            violation_rate=violation_rate,
            passed=passed,
            total_tokens_used=total_suite_tokens,
            fingerprint_changed_warning=drift_warning,
            model_fingerprint=self.drift_tracker.last_seen_fingerprint or "fp_gemma4_local",
            model_tested=self.config.model,
            minimized_failing_traces=minimized_traces,
            violated_invariant_id=violated_invariant_id,
            attempted_call_summary=attempted_call_summary,
            minimal_failing_payload=minimal_failing_payload,
            raw_traces=raw_traces,
        )

    async def _worker_task(
        self, iteration_index: int, prompt: str, das_mock_tools: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, bool, List[Any], Optional[List[Message]], Optional[ToolExecutionAttempt], List[ToolExecutionAttempt], int]:
        """Single isolated async worker execution task with token accounting, timeout shielding, and semantic checks."""
        worker_seed = self.config.seed + iteration_index
        seeder = SimulationSeeder(seed=worker_seed)
        evaluator = BoundaryEvaluator(self.config, custom_handlers=self.custom_conditions)

        trajectory: List[Any] = []
        has_violation = False
        first_failed_attempt: Optional[ToolExecutionAttempt] = None
        run_tokens = 0

        # Invoke agent adapter wrapped with timeout shielding
        try:
            async def _invoke():
                try:
                    return await self.adapter.invoke(prompt, das_mock_tools=das_mock_tools)
                except TypeError:
                    return await self.adapter.invoke(prompt)

            trajectory = await asyncio.wait_for(_invoke(), timeout=self.config.timeout_seconds)

        except asyncio.TimeoutError:
            logger.error(f"Worker task iteration {iteration_index} timed out after {self.config.timeout_seconds}s!")
            has_violation = True
            first_failed_attempt = ToolExecutionAttempt(
                tool_name="system_timeout",
                arguments={"timeout_seconds": self.config.timeout_seconds},
                allowed=False,
                violated_invariant_id="TIMEOUT_EXCEEDED",
            )
            trajectory = [
                Message(role="system", content="System timeout handler."),
                Message(role="user", content=prompt),
                Message(role="assistant", content=f"Execution timed out after {self.config.timeout_seconds}s."),
            ]

        except Exception as e:
            logger.error(f"Worker task iteration {iteration_index} caught unhandled exception: {e}")
            has_violation = True
            first_failed_attempt = ToolExecutionAttempt(
                tool_name="agent_unhandled_exception",
                arguments={"error": str(e)},
                allowed=False,
                violated_invariant_id="AGENT_UNHANDLED_EXCEPTION",
            )
            trajectory = [
                Message(role="system", content="System exception handler."),
                Message(role="user", content=prompt),
                Message(role="assistant", content=f"Agent raised unhandled exception: {e}"),
            ]

        # Calculate token consumption
        for item in trajectory:
            content = item.content if isinstance(item, Message) else (item.get("content") if isinstance(item, dict) else getattr(item, "content", ""))
            run_tokens += estimate_tokens(str(content))

        # Enforce max_tokens_per_iteration cap
        if self.config.max_tokens_per_iteration and run_tokens > self.config.max_tokens_per_iteration:
            logger.error(
                f"Token budget ({run_tokens}) exceeded max limit ({self.config.max_tokens_per_iteration})!"
            )
            has_violation = True
            first_failed_attempt = ToolExecutionAttempt(
                tool_name="resource_token_cap",
                arguments={"tokens_used": run_tokens, "max_allowed": self.config.max_tokens_per_iteration},
                allowed=False,
                violated_invariant_id="TOKEN_BUDGET_EXCEEDED",
            )

        # Check for agent trajectory loop
        if len(trajectory) > self.config.max_trajectory_length:
            has_violation = True
            if not first_failed_attempt:
                first_failed_attempt = ToolExecutionAttempt(
                    tool_name="agent_loop_protection",
                    arguments={
                        "trajectory_length": len(trajectory),
                        "max_allowed": self.config.max_trajectory_length,
                    },
                    allowed=False,
                    violated_invariant_id="MAX_TRAJECTORY_LENGTH_EXCEEDED",
                )

        # Check trajectory for invariant violations (passing history trajectory)
        eval_has_violation, attempts = self._evaluate_trajectory(trajectory, evaluator)
        if eval_has_violation:
            has_violation = True

        # Check semantic soft invariants on final assistant output
        for inv in self.config.invariants:
            if inv.condition_type == "semantic_distance_threshold" and trajectory:
                last_msg = trajectory[-1]
                text_out = last_msg.content if isinstance(last_msg, Message) else (last_msg.get("content") if isinstance(last_msg, dict) else str(last_msg))
                sem_attempt = self.semantic_evaluator.evaluate_text_output(str(text_out), inv)
                attempts.append(sem_attempt)
                if not sem_attempt.allowed:
                    has_violation = True
                    if not first_failed_attempt:
                        first_failed_attempt = sem_attempt

        if not first_failed_attempt:
            first_failed_attempt = next((a for a in attempts if not a.allowed), None)

        minimized_trace: Optional[List[Message]] = None
        if has_violation and trajectory:
            def predicate(msgs: List[Message]) -> bool:
                v, _ = self._evaluate_trajectory(msgs, evaluator)
                return v

            try:
                shrinker = DeltaDebugger(predicate=predicate)
                minimized_trace = shrinker.shrink(trajectory)
            except Exception as e:
                logger.warning(f"Shrinker encountered error: {e}")

        return iteration_index, has_violation, trajectory, minimized_trace, first_failed_attempt, attempts, run_tokens

    @staticmethod
    def _evaluate_trajectory(
        trajectory: List[Any], evaluator: BoundaryEvaluator
    ) -> Tuple[bool, List[ToolExecutionAttempt]]:
        """Evaluates all tool calls in a trajectory against the evaluator."""
        attempts = []
        has_violation = False

        for idx, item in enumerate(trajectory):
            history_so_far = trajectory[:idx]
            if isinstance(item, Message):
                tool_calls = item.tool_calls
            elif isinstance(item, dict):
                tool_calls = item.get("tool_calls")
            else:
                tool_calls = getattr(item, "tool_calls", None)

            if tool_calls:
                for tc in tool_calls:
                    tool_name, args = parse_tool_call(tc)
                    attempt = evaluator.evaluate_call(tool_name, args, history_trajectory=history_so_far)
                    attempts.append(attempt)
                    if not attempt.allowed:
                        has_violation = True

        return has_violation, attempts
