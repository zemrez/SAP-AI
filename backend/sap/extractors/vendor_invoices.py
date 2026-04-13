"""Extractor for SAP Vendor (Supplier) Invoice data."""

from __future__ import annotations

import logging
from typing import Any

from sap.client import SAPClient
from sap.odata import ODataQueryBuilder
from sap.schemas import VendorInvoice

logger = logging.getLogger(__name__)

SERVICE = "API_SUPPLIERINVOICE_PROCESS_SRV"
ENTITY_SET = "A_SupplierInvoice"


class VendorInvoiceExtractor:
    """Fetches vendor / supplier invoices from SAP."""

    def __init__(self, client: SAPClient) -> None:
        self.client = client

    async def get_invoices(
        self,
        company_code: str,
        fiscal_year: str,
        *,
        top: int = 5000,
        skip: int = 0,
        supplier: str | None = None,
    ) -> list[VendorInvoice]:
        """Fetch vendor invoices for a company code and fiscal year."""
        qb = (
            ODataQueryBuilder()
            .select(
                "SupplierInvoice",
                "FiscalYear",
                "CompanyCode",
                "InvoicingParty",
                "DocumentDate",
                "PostingDate",
                "InvoiceGrossAmount",
                "DocumentCurrency",
                "PaymentTerms",
                "IsCleared",
                "SupplierInvoiceIDByInvoicingParty",
            )
            .filter(f"CompanyCode eq '{company_code}'")
            .filter(f"FiscalYear eq '{fiscal_year}'")
            .top(top)
            .skip(skip)
        )

        if supplier:
            qb.filter(f"InvoicingParty eq '{supplier}'")

        path = f"{SERVICE}/{ENTITY_SET}?{qb.build()}&$format=json"
        data = await self.client.get(path)
        results = self._extract_results(data)

        return [VendorInvoice.model_validate(r) for r in results]

    async def get_invoice(self, supplier_invoice: str, fiscal_year: str) -> VendorInvoice:
        """Fetch a single vendor invoice by key."""
        key = f"SupplierInvoice='{supplier_invoice}',FiscalYear='{fiscal_year}'"
        path = f"{SERVICE}/{ENTITY_SET}({key})?$format=json"
        data = await self.client.get(path)
        result = data.get("d", data)
        return VendorInvoice.model_validate(result)

    @staticmethod
    def _extract_results(data: dict[str, Any]) -> list[dict]:
        if "d" in data:
            return data["d"].get("results", [])
        return data.get("value", [])
