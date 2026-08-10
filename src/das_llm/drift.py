import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ModelDriftTracker:
    """Tracks LLM model fingerprints and HTTP response headers across simulation runs to detect silent provider model updates."""

    def __init__(self, expected_fingerprint: Optional[str] = None):
        self.expected_fingerprint = expected_fingerprint
        self.recorded_fingerprints: Dict[str, int] = {}
        self.last_seen_fingerprint: Optional[str] = None

    def record_response(self, headers_or_meta: Dict[str, Any]) -> Tuple[str, bool]:
        """Records fingerprint from response headers or OpenAI choices metadata."""
        fingerprint = (
            headers_or_meta.get("system_fingerprint")
            or headers_or_meta.get("x-request-id")
            or headers_or_meta.get("ollama-model")
            or headers_or_meta.get("model_version", "default_model_fp")
        )

        self.last_seen_fingerprint = fingerprint
        self.recorded_fingerprints[fingerprint] = self.recorded_fingerprints.get(fingerprint, 0) + 1

        drift_detected = False
        if self.expected_fingerprint and fingerprint != self.expected_fingerprint:
            logger.warning(
                f"Model Drift Alert: Expected fingerprint '{self.expected_fingerprint}', but provider returned '{fingerprint}'!"
            )
            drift_detected = True
        elif len(self.recorded_fingerprints) > 1:
            logger.warning(f"Model Drift Alert: Multiple fingerprints observed in single test run: {list(self.recorded_fingerprints.keys())}")
            drift_detected = True

        return fingerprint, drift_detected
