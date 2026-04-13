"""Base detector interface and shared result model."""

from abc import ABC, abstractmethod
from decimal import Decimal

from pydantic import BaseModel, Field


class DetectionResult(BaseModel):
    """A single anomaly finding from a detector."""

    detector_name: str
    anomaly_type: str  # human-readable category
    confidence: float = Field(..., ge=0.0, le=1.0)
    document_number: str | None = None
    company_code: str | None = None
    fiscal_year: int | None = None
    posting_date: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    details: dict = Field(default_factory=dict)
    description: str = ""


class BaseDetector(ABC):
    """Abstract base for all anomaly detectors.

    Subclasses must implement ``detect`` and ``get_default_config``.
    """

    name: str = "base"
    description: str = ""

    @abstractmethod
    async def detect(self, entries: list[dict]) -> list[DetectionResult]:
        """Run detection on a list of journal entry dicts.

        Each dict contains SAP journal entry fields with Python-style keys
        (e.g. ``company_code``, ``posting_date``, ``amount_in_company_code_currency``).
        """
        ...

    @abstractmethod
    def get_default_config(self) -> dict:
        """Return the default configuration dict for this detector."""
        ...
