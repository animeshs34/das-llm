import json
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Union


class SimulationSeeder:
    """PRNG state manager and corpus loader supporting plain and structured payload selection."""

    def __init__(
        self,
        seed: int,
        corpus_path: Optional[str] = None,
        payloads: Optional[List[Union[str, Dict[str, Any]]]] = None,
    ):
        self.seed = seed
        self.rng = random.Random(seed)

        if payloads is not None:
            self.raw_payloads = payloads
        else:
            resolved_path = self._resolve_corpus_path(corpus_path)
            self.raw_payloads = self._load_corpus(resolved_path)

        self.structured_payloads: List[Dict[str, Any]] = []
        self.string_payloads: List[str] = []

        for p in self.raw_payloads:
            if isinstance(p, dict) and "payload" in p:
                self.structured_payloads.append(p)
                self.string_payloads.append(p["payload"])
            elif isinstance(p, str):
                self.string_payloads.append(p)

    def _resolve_corpus_path(self, corpus_path: Optional[str]) -> Path:
        if corpus_path:
            p = Path(corpus_path)
            if p.exists():
                return p

        cwd_corpus = Path.cwd() / "corpus" / "payloads.json"
        if cwd_corpus.exists():
            return cwd_corpus

        pkg_corpus = Path(__file__).parents[2] / "corpus" / "payloads.json"
        if pkg_corpus.exists():
            return pkg_corpus

        raise FileNotFoundError(
            f"Could not locate corpus payloads file. Searched: {corpus_path}, {cwd_corpus}, {pkg_corpus}"
        )

    def _load_corpus(self, path: Path) -> List[Any]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list) or not data:
                raise ValueError(f"Corpus at {path} must be a non-empty list.")
            return data

    def get_payload(
        self,
        condition_type: Optional[str] = None,
        target_tool: Optional[str] = None,
    ) -> str:
        """Deterministically selects a payload, optionally filtering by target condition_type or tool."""
        candidates = []

        if condition_type or target_tool:
            for item in self.structured_payloads:
                ctype_match = (
                    condition_type is None
                    or item.get("target_condition_type") == condition_type
                )
                tool_match = (
                    target_tool is None
                    or item.get("target_tool") == target_tool
                )
                if ctype_match and tool_match:
                    candidates.append(item["payload"])

        if not candidates:
            # Fall back to full string payloads
            candidates = self.string_payloads

        return self.rng.choice(candidates)
