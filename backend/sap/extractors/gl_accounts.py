"""Extractor for SAP General Ledger account master data."""

from __future__ import annotations

import logging
from typing import Any

from sap.client import SAPClient
from sap.odata import ODataQueryBuilder
from sap.schemas import GLAccount

logger = logging.getLogger(__name__)

SERVICE = "API_GLACCOUNTINCHARTOFACCOUNTS_SRV"
ENTITY_SET = "A_GLAccountInChartOfAccounts"


class GLAccountExtractor:
    """Fetches GL account master data from SAP."""

    def __init__(self, client: SAPClient) -> None:
        self.client = client

    async def get_accounts(
        self,
        chart_of_accounts: str = "YCOA",
        *,
        top: int = 5000,
        skip: int = 0,
        account_type: str | None = None,
    ) -> list[GLAccount]:
        """Fetch GL accounts for a chart of accounts."""
        qb = (
            ODataQueryBuilder()
            .select(
                "ChartOfAccounts",
                "GLAccount",
                "GLAccountName",
                "GLAccountGroup",
                "GLAccountType",
                "IsBalanceSheetAccount",
                "ProfitLossAccountType",
            )
            .filter(f"ChartOfAccounts eq '{chart_of_accounts}'")
            .top(top)
            .skip(skip)
        )

        if account_type:
            qb.filter(f"GLAccountType eq '{account_type}'")

        path = f"{SERVICE}/{ENTITY_SET}?{qb.build()}&$format=json"
        data = await self.client.get(path)
        results = self._extract_results(data)

        return [GLAccount.model_validate(r) for r in results]

    async def get_account(self, chart_of_accounts: str, gl_account: str) -> GLAccount:
        """Fetch a single GL account by key."""
        key = f"ChartOfAccounts='{chart_of_accounts}',GLAccount='{gl_account}'"
        path = f"{SERVICE}/{ENTITY_SET}({key})?$format=json"
        data = await self.client.get(path)
        result = data.get("d", data)
        return GLAccount.model_validate(result)

    @staticmethod
    def _extract_results(data: dict[str, Any]) -> list[dict]:
        if "d" in data:
            return data["d"].get("results", [])
        return data.get("value", [])
