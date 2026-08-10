import logging
from typing import Dict, Any, List, Callable, Optional
from das_llm.schemas import SimulationConfig, SecurityInvariant, ToolExecutionAttempt, Message

logger = logging.getLogger(__name__)

ConditionHandler = Callable[[SecurityInvariant, Dict[str, Any]], bool]


class BoundaryEvaluator:
    """Strategy permission proxy evaluating LLM tool call attempts against security invariants."""

    _global_custom_handlers: Dict[str, ConditionHandler] = {}

    def __init__(
        self,
        config: SimulationConfig,
        custom_handlers: Optional[Dict[str, ConditionHandler]] = None,
    ):
        self.config = config
        self.invariants_by_tool: Dict[str, List[SecurityInvariant]] = {}
        self.instance_custom_handlers: Dict[str, ConditionHandler] = custom_handlers or {}

        for inv in config.invariants:
            self.invariants_by_tool.setdefault(inv.target_tool, []).append(inv)

    @classmethod
    def register_condition_type(cls, name: str, handler: ConditionHandler) -> None:
        """Globally registers a custom condition type evaluation strategy."""
        cls._global_custom_handlers[name] = handler
        logger.info(f"Registered custom condition type handler: '{name}'")

    def register_instance_condition_type(self, name: str, handler: ConditionHandler) -> None:
        """Registers a custom condition type evaluation strategy on this evaluator instance."""
        self.instance_custom_handlers[name] = handler

    def evaluate_call(
        self, tool_name: str, args: Any, history_trajectory: Optional[List[Any]] = None
    ) -> ToolExecutionAttempt:
        """Evaluates a tool execution attempt against registered security invariants."""
        if not isinstance(args, dict):
            logger.error(f"Fail closed: malformed tool arguments type {type(args)} for tool '{tool_name}'")
            return ToolExecutionAttempt(
                tool_name=tool_name,
                arguments={"_raw_args": str(args)},
                allowed=False,
                violated_invariant_id="MALFORMED_ARGS",
            )

        invariants = self.invariants_by_tool.get(tool_name, []) + self.invariants_by_tool.get("global", [])

        for inv in invariants:
            try:
                allowed = self._dispatch_evaluation(inv, args, history_trajectory=history_trajectory)
            except Exception as e:
                logger.exception(f"Fail closed due to evaluation exception: {e}")
                return ToolExecutionAttempt(
                    tool_name=tool_name,
                    arguments=args,
                    allowed=False,
                    violated_invariant_id=inv.invariant_id,
                )

            if not allowed:
                return ToolExecutionAttempt(
                    tool_name=tool_name,
                    arguments=args,
                    allowed=False,
                    violated_invariant_id=inv.invariant_id,
                )

        return ToolExecutionAttempt(
            tool_name=tool_name,
            arguments=args,
            allowed=True,
            violated_invariant_id=None,
        )

    def _dispatch_evaluation(
        self, invariant: SecurityInvariant, args: Dict[str, Any], history_trajectory: Optional[List[Any]] = None
    ) -> bool:
        """Routes evaluation to built-in or developer-registered custom condition handlers."""
        ctype = invariant.condition_type

        if ctype in self.instance_custom_handlers:
            return self.instance_custom_handlers[ctype](invariant, args)

        if ctype in self._global_custom_handlers:
            return self._global_custom_handlers[ctype](invariant, args)

        if ctype == "blocked":
            return self._evaluate_blocked(invariant, args)
        elif ctype == "requires_flag":
            return self._evaluate_requires_flag(invariant, args)
        elif ctype == "data_exclusion":
            return self._evaluate_data_exclusion(invariant, args)
        elif ctype == "state_machine_violation":
            return self._evaluate_state_machine_violation(invariant, args, history_trajectory)
        elif ctype in ("trace_exclusion", "cross_agent_contagion"):
            return self._evaluate_trace_exclusion(invariant, args, history_trajectory)
        else:
            logger.error(f"Unknown condition_type: '{ctype}'. Failing closed.")
            return False

    def _evaluate_blocked(self, invariant: SecurityInvariant, args: Dict[str, Any]) -> bool:
        if not invariant.required_params:
            return False

        for k, v in invariant.required_params.items():
            if args.get(k) == v:
                return False

        return True

    def _evaluate_requires_flag(self, invariant: SecurityInvariant, args: Dict[str, Any]) -> bool:
        if not invariant.required_params:
            return False

        for flag_name, expected_val in invariant.required_params.items():
            if args.get(flag_name) != expected_val:
                return False

        return True

    def _evaluate_data_exclusion(self, invariant: SecurityInvariant, args: Dict[str, Any]) -> bool:
        if not invariant.required_params:
            return False

        for param_key, forbidden_pattern in invariant.required_params.items():
            arg_val = args.get(param_key)
            if arg_val is not None:
                arg_str = str(arg_val).lower()
                forbidden_str = str(forbidden_pattern).lower()
                if forbidden_str in arg_str:
                    return False

        return True

    def _evaluate_state_machine_violation(
        self, invariant: SecurityInvariant, args: Dict[str, Any], history_trajectory: Optional[List[Any]]
    ) -> bool:
        """Evaluates stateful kill-chain invariants (forbidden prior tools in session history)."""
        forbidden_priors = invariant.required_params.get("forbidden_prior_tools", [])
        if not forbidden_priors or not history_trajectory:
            return True

        # Extract names of all prior tools executed in trajectory history
        prior_tools_called = set()
        for item in history_trajectory:
            tool_calls = item.tool_calls if isinstance(item, Message) else item.get("tool_calls") if isinstance(item, dict) else getattr(item, "tool_calls", None)
            if tool_calls:
                for tc in tool_calls:
                    name = tc.get("function", {}).get("name") or tc.get("name")
                    if name:
                        prior_tools_called.add(name)

        for forbidden in forbidden_priors:
            if forbidden in prior_tools_called:
                logger.warning(
                    f"State Machine Violation: Tool '{invariant.target_tool}' blocked because forbidden prior tool '{forbidden}' was invoked in session history!"
                )
                return False  # Stateful violation caught

        return True

    def _evaluate_trace_exclusion(
        self, invariant: SecurityInvariant, args: Dict[str, Any], history_trajectory: Optional[List[Any]]
    ) -> bool:
        """Evaluates multi-agent cascading contagion topology rules."""
        untrusted_agent = invariant.required_params.get("untrusted_source_agent")
        if not untrusted_agent or not history_trajectory:
            return True

        for item in history_trajectory:
            source = getattr(item, "source_agent", None) if isinstance(item, Message) else (item.get("source_agent") if isinstance(item, dict) else None)
            if source == untrusted_agent:
                logger.warning(
                    f"Multi-Agent Contagion Violation: Tool '{invariant.target_tool}' blocked due to infected context from '{untrusted_agent}'!"
                )
                return False

        return True
