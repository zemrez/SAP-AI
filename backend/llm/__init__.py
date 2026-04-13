"""Shared LLM abstraction layer -- used by all feature modules."""

from .prompts import (
    ANOMALY_BATCH_SUMMARY,
    ANOMALY_EXPLANATION_SYSTEM,
    ANOMALY_EXPLANATION_USER,
)
from .provider import LLMProvider, LLMProviderError

__all__ = [
    "LLMProvider",
    "LLMProviderError",
    "ANOMALY_EXPLANATION_SYSTEM",
    "ANOMALY_EXPLANATION_USER",
    "ANOMALY_BATCH_SUMMARY",
]
