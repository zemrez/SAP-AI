"""Shared fixtures for anomaly detective tests."""

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _make_entry(
    *,
    doc: str = "5000000001",
    item: str = "001",
    company_code: str = "1000",
    fiscal_year: str = "2025",
    posting_date: str = "2025-06-15",
    gl_account: str = "400000",
    amount: float = 1500.00,
    currency: str = "EUR",
    dc_code: str = "S",
    doc_type: str = "SA",
    reference: str = "INV-001",
    created_by: str = "TESTUSER",
) -> dict:
    """Create a realistic journal entry dict with Python-style keys."""
    return {
        "accounting_document": doc,
        "accounting_document_item": item,
        "company_code": company_code,
        "fiscal_year": fiscal_year,
        "posting_date": posting_date,
        "document_date": posting_date,
        "gl_account": gl_account,
        "amount_in_company_code_currency": amount,
        "company_code_currency": currency,
        "debit_credit_code": dc_code,
        "document_type": doc_type,
        "reference_document": reference,
        "document_header_text": "",
        "created_by_user": created_by,
    }


@pytest.fixture
def make_entry():
    """Factory fixture for creating journal entry dicts."""
    return _make_entry


@pytest.fixture
def normal_entries():
    """A set of 20 normal journal entries for GL 400000."""
    entries = []
    for i in range(20):
        entries.append(
            _make_entry(
                doc=f"500000{i:04d}",
                amount=1000.0 + i * 50,  # range: 1000 - 1950
                posting_date=f"2025-06-{(i % 28) + 1:02d}",
                gl_account="400000",
            )
        )
    return entries


@pytest.fixture
def document_pair_entries():
    """Journal entries forming debit/credit pairs for combination detection."""
    entries = []
    # Common pair: 400000 (D) -> 200000 (C), repeated 20 times
    for i in range(20):
        entries.append(
            _make_entry(
                doc=f"600000{i:04d}",
                item="001",
                gl_account="400000",
                amount=1000.0 + i * 10,
                dc_code="S",
                posting_date=f"2025-06-{(i % 28) + 1:02d}",
            )
        )
        entries.append(
            _make_entry(
                doc=f"600000{i:04d}",
                item="002",
                gl_account="200000",
                amount=-(1000.0 + i * 10),
                dc_code="H",
                posting_date=f"2025-06-{(i % 28) + 1:02d}",
            )
        )
    # Rare pair: 400000 (D) -> 999999 (C), just once
    entries.append(
        _make_entry(
            doc="6000009999",
            item="001",
            gl_account="400000",
            amount=5000.0,
            dc_code="S",
        )
    )
    entries.append(
        _make_entry(
            doc="6000009999",
            item="002",
            gl_account="999999",
            amount=-5000.0,
            dc_code="H",
        )
    )
    return entries
