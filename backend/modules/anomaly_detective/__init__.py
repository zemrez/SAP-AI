"""Anomaly Detective module — AI-powered financial anomaly detection."""

from .router import router

MODULE_META = {
    "name": "Anomaly Detective",
    "version": "1.0.0",
    "prefix": "anomaly-detective",
}

__all__ = ["router", "MODULE_META"]
