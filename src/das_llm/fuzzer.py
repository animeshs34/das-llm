import base64
import random
from typing import List, Callable


class MutationalFuzzer:
    """Deterministic mutational fuzzer for adversarial prompt payload transformations."""

    HOMOGLYPH_MAP = {
        "e": "е",  # Cyrillic small letter ie
        "a": "а",  # Cyrillic small letter a
        "o": "о",  # Cyrillic small letter o
        "p": "р",  # Cyrillic small letter er
        "c": "с",  # Cyrillic small letter es
        "i": "і",  # Cyrillic small letter byelorussian-ukrainian i
    }

    def __init__(self, seed: int):
        self.seed = seed
        self.rng = random.Random(seed)

    def mutate(self, raw_payload: str, operator_name: str | None = None) -> str:
        """Deterministically transforms raw_payload using a selected mutation operator."""
        operators: List[Callable[[str], str]] = [
            self._insert_zero_width_spaces,
            self._apply_homoglyphs,
            self._wrap_base64,
            self._wrap_markdown_comments,
            self._noop,
        ]

        if operator_name:
            named_op = getattr(self, f"_{operator_name}", None)
            if named_op and callable(named_op):
                return named_op(raw_payload)

        chosen_op = self.rng.choice(operators)
        return chosen_op(raw_payload)

    def _insert_zero_width_spaces(self, text: str) -> str:
        """Inserts zero-width spaces (\u200B) inside key instruction words."""
        words = text.split(" ")
        mutated_words = []
        for word in words:
            if len(word) > 4 and self.rng.random() > 0.5:
                mid = len(word) // 2
                word = word[:mid] + "\u200B" + word[mid:]
            mutated_words.append(word)
        return " ".join(mutated_words)

    def _apply_homoglyphs(self, text: str) -> str:
        """Replaces standard Latin characters with visual homoglyphs."""
        chars = []
        for char in text:
            if char in self.HOMOGLYPH_MAP and self.rng.random() > 0.4:
                chars.append(self.HOMOGLYPH_MAP[char])
            else:
                chars.append(char)
        return "".join(chars)

    def _wrap_base64(self, text: str) -> str:
        """Encodes injection directive in Base64 wrapper."""
        encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        return f"[DECODE_BASE64_INSTRUCTION]: {encoded}"

    def _wrap_markdown_comments(self, text: str) -> str:
        """Encapsulates payload inside Markdown comment tags."""
        return f"<!-- SYSTEM_INSTRUCTION_OVERRIDE: {text} -->"

    def _noop(self, text: str) -> str:
        """Returns unmodified raw payload."""
        return text
