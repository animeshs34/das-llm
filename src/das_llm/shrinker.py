import logging
from typing import List, Callable, Tuple
from das_llm.schemas import Message, ToolExecutionAttempt

logger = logging.getLogger(__name__)

# Predicate signature: takes a trajectory of Messages and returns True if it triggers a violation.
ViolationPredicate = Callable[[List[Message]], bool]


class DeltaDebugger:
    """Delta debugging (ddmin) structural minimizer for conversation trajectories."""

    def __init__(self, predicate: ViolationPredicate):
        self.predicate = predicate

    def shrink(self, trajectory: List[Message]) -> List[Message]:
        """Shrinks a failing List[Message] to the minimal subset that reproduces the violation.

        Preserves system prompt at index 0 (if present).
        Never modifies internal string content. Only drops whole Message objects.
        """
        if not trajectory:
            return trajectory

        # Extract system prompt if present
        first_role = (
            trajectory[0].role
            if isinstance(trajectory[0], Message)
            else (trajectory[0].get("role") if isinstance(trajectory[0], dict) else getattr(trajectory[0], "role", ""))
        )
        if first_role == "system":
            system_msg = [trajectory[0]]
            candidates = trajectory[1:]
        else:
            system_msg = []
            candidates = trajectory


        # Verify initial full sequence triggers the predicate
        if not self.predicate(system_msg + candidates):
            logger.warning("Initial trajectory did not trigger predicate violation; returning original.")
            return trajectory

        minimal_candidates = self._ddmin(candidates, system_msg)
        return system_msg + minimal_candidates

    def _ddmin(self, S: List[Message], prefix: List[Message]) -> List[Message]:
        """Classic ddmin algorithm operating over a list of Message objects."""
        n = 2
        while len(S) > 1:
            chunks = self._split(S, n)
            some_complement_failed = False

            # 1. Try subsets
            for chunk in chunks:
                if len(chunk) < len(S) and self.predicate(prefix + chunk):
                    S = chunk
                    n = max(n - 1, 2)
                    some_complement_failed = True
                    break

            if some_complement_failed:
                continue

            # 2. Try complements
            for chunk in chunks:
                complement = [m for m in S if m not in chunk]
                if len(complement) < len(S) and complement and self.predicate(prefix + complement):
                    S = complement
                    n = max(n - 1, 2)
                    some_complement_failed = True
                    break

            if some_complement_failed:
                continue

            # 3. Increase granularity
            if n >= len(S):
                break
            n = min(len(S), 2 * n)

        return S


    @staticmethod
    def _split(seq: List[Message], n: int) -> List[List[Message]]:
        """Splits seq into n roughly equal chunks."""
        k = len(seq)
        if k == 0:
            return []
        n = min(n, k)
        chunk_size = k // n
        remainder = k % n

        chunks = []
        start = 0
        for i in range(n):
            end = start + chunk_size + (1 if i < remainder else 0)
            chunks.append(seq[start:end])
            start = end
        return chunks
