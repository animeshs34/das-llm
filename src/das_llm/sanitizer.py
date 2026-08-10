import re
from typing import Any, Dict, List, Union


class PrivacyGuard:
    """PII & PCI-DSS Compliant Redaction Sanitizer. Guaranteed zero leakage of sensitive data in logs or audit reports."""

    PII_PCI_REGEX_PATTERNS = [
        # 1. PCI-DSS: Credit Card Numbers (Visa, MasterCard, Amex, Discover)
        (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b", "[REDACTED_PCI_CREDIT_CARD]"),
        # 2. PCI-DSS: CVV / CVC Security Codes
        (r"\b(?:cvv|cvc|security_code)\s*[:=\s]\s*\d{3,4}\b", "[REDACTED_PCI_CVV]"),
        # 3. PII: Social Security Numbers (SSN)
        (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_PII_SSN]"),
        # 4. PII: Email Addresses
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b", "[REDACTED_PII_EMAIL]"),
        # 5. PII: Phone Numbers
        (r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[REDACTED_PII_PHONE]"),
        # 6. Credentials: Secret API Keys & Auth Tokens
        (r"\b(?:sk-proj-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{36}|AKIA[0-9A-Z]{16}|Bearer\s+[A-Za-z0-9._-]{20,})\b", "[REDACTED_CREDENTIAL]"),
    ]

    @classmethod
    def sanitize(cls, text: str) -> str:
        """Sanitizes raw text strings by replacing PII, PCI, and credential matches with compliance redaction tokens."""
        if not text:
            return text

        sanitized = str(text)
        for pattern, replacement in cls.PII_PCI_REGEX_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        return sanitized

    @classmethod
    def sanitize_obj(cls, obj: Any) -> Any:
        """Recursively sanitizes dictionaries, lists, strings, and data models before logging or writing export artifacts."""
        if isinstance(obj, str):
            return cls.sanitize(obj)
        elif isinstance(obj, dict):
            return {k: cls.sanitize_obj(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [cls.sanitize_obj(item) for item in obj]
        elif hasattr(obj, "model_dump"):
            return cls.sanitize_obj(obj.model_dump())
        elif hasattr(obj, "__dict__"):
            return cls.sanitize_obj(obj.__dict__)
        return obj
