import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class LogToTestIngester:
    """Ingests production observability logs (Datadog, LangSmith, Arize), strips PII, and generates permanent test seed manifests."""

    PII_REGEX_LIST = [
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", "ANONYMIZED_EMAIL@domain.com"),
        (r"\b\d{3}-\d{2}-\d{4}\b", "000-00-0000"),
        (r"sk-proj-[A-Za-z0-9_-]{20,}", "sk-proj-ANONYMIZED_KEY"),
    ]

    def sanitize_text(self, text: str) -> str:
        """Strips real user PII and credentials from log text."""
        sanitized = text
        for pattern, replacement in self.PII_REGEX_LIST:
            sanitized = re.sub(pattern, replacement, sanitized)
        return sanitized

    def ingest_log_file(self, log_path: str | Path, output_corpus: str | Path) -> Path:
        """Reads production log JSON file, sanitizes entries, and appends payloads to test corpus."""
        in_path = Path(log_path)
        out_path = Path(output_corpus)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not in_path.exists():
            raise FileNotFoundError(f"Production log file not found: {in_path}")

        raw_content = in_path.read_text(encoding="utf-8")
        try:
            log_entries = json.loads(raw_content)
        except Exception:
            # Handle NDJSON
            log_entries = [json.loads(line) for line in raw_content.splitlines() if line.strip()]

        existing_payloads: List[Dict[str, Any]] = []
        if out_path.exists():
            try:
                existing_payloads = json.loads(out_path.read_text(encoding="utf-8"))
            except Exception:
                existing_payloads = []

        new_count = 0
        for i, entry in enumerate(log_entries):
            prompt = entry.get("prompt") or entry.get("input") or entry.get("message")
            if prompt:
                sanitized_prompt = self.sanitize_text(str(prompt))
                payload_entry = {
                    "id": f"REPLAY-PROD-{i+1:03d}",
                    "target_condition_type": entry.get("target_condition_type", "requires_flag"),
                    "target_tool": entry.get("target_tool", "issue_refund"),
                    "payload": sanitized_prompt,
                }
                existing_payloads.append(payload_entry)
                new_count += 1

        out_path.write_text(json.dumps(existing_payloads, indent=4), encoding="utf-8")
        logger.info(f"Ingested {new_count} production log anomalies into {out_path}")
        return out_path
