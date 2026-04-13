"""Extractor for SAP Journal Entry line items."""

from __future__ import annotations

import logging
from typing import Any

from sap.client import SAPClient
from sap.odata import ODataQueryBuilder
from sap.schemas import JournalEntry

logger = logging.getLogger(__name__)

# SAP standard OData service
SERVICE = "API_JOURNALENTRYITEMBASIC_SRV"
ENTITY_SET = "A_JournalEntryItemBasic"


class JournalEntryExtractor:
    """Fetches journal entry line items from SAP."""

    def __init__(self, client: SAPClient) -> None:
        self.client = client

    async def get_entries(
        self,
        company_code: str,
        fiscal_year: str,
        *,
        top: int = 5000,
        skip: int = 0,
        gl_account: str | None = None,
        document_type: str | None = None,
    ) -> list[JournalEntry]:
        """Fetch journal entry items for a company code and fiscal year."""
        qb = (
            ODataQueryBuilder()
            .select(
                "CompanyCode",
                "FiscalYear",
                "AccountingDocument",
                "AccountingDocumentItem",
                "PostingDate",
                "DocumentDate",
                "GLAccount",
                "AmountInCompanyCodeCurrency",
                "CompanyCodeCurrency",
                "DebitCreditCode",
                "AccountingDocumentType",
                "ReferenceDocument",
                "DocumentHeaderText",
                "AccountingDocumentCreatedByUser",
            )
            .filter(f"CompanyCode eq '{company_code}'")
            .filter(f"FiscalYear eq '{fiscal_year}'")
            .top(top)
            .skip(skip)
        )

        if gl_account:
            qb.filter(f"GLAccount eq '{gl_account}'")
        if document_type:
            qb.filter(f"AccountingDocumentType eq '{document_type}'")

        path = f"{SERVICE}/{ENTITY_SET}?{qb.build()}&$format=json"
        data = await self.client.get(path)
        results = self._extract_results(data)

        return [JournalEntry.model_validate(r) for r in results]

    async def get_entry_by_key(
        self,
        company_code: str,
        fiscal_year: str,
        accounting_document: str,
        accounting_document_item: str,
    ) -> JournalEntry:
        """Fetch a single journal entry item by its composite key."""
        key = (
            f"CompanyCode='{company_code}',"
            f"FiscalYear='{fiscal_year}',"
            f"AccountingDocument='{accounting_document}',"
            f"AccountingDocumentItem='{accounting_document_item}'"
        )
        path = f"{SERVICE}/{ENTITY_SET}({key})?$format=json"
        data = await self.client.get(path)
        result = data.get("d", data)
        return JournalEntry.model_validate(result)

    @staticmethod
    def _extract_results(data: dict[str, Any]) -> list[dict]:
        """Handle both OData V2 (d.results) and V4 (value) response shapes."""
        if "d" in data:
            return data["d"].get("results", [])
        return data.get("value", [])
