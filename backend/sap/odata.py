"""OData query builder for SAP OData V2/V4 services."""

from __future__ import annotations

from urllib.parse import quote


class ODataQueryBuilder:
    """Fluent builder for OData system query options.

    Usage:
        query = (
            ODataQueryBuilder()
            .select("CompanyCode", "FiscalYear", "Amount")
            .filter("CompanyCode eq '1000'")
            .filter("FiscalYear eq '2024'")
            .orderby("Amount", descending=True)
            .top(100)
            .skip(0)
            .expand("to_Items")
            .build()
        )
        # => "$select=CompanyCode,FiscalYear,Amount&$filter=CompanyCode eq '1000' and FiscalYear eq '2024'&..."
    """

    def __init__(self) -> None:
        self._select: list[str] = []
        self._filter: list[str] = []
        self._expand: list[str] = []
        self._orderby: list[str] = []
        self._top: int | None = None
        self._skip: int | None = None
        self._inlinecount: bool = False

    # ------------------------------------------------------------------
    # Fluent setters
    # ------------------------------------------------------------------

    def select(self, *fields: str) -> ODataQueryBuilder:
        """Add fields to $select."""
        self._select.extend(fields)
        return self

    def filter(self, expression: str) -> ODataQueryBuilder:
        """Add a filter expression.

        Multiple calls are joined with ``and``.
        Supports SAP OData filter operators: eq, ne, gt, lt, ge, le, and, or.

        Examples:
            .filter("CompanyCode eq '1000'")
            .filter("Amount gt 1000")
            .filter("PostingDate ge datetime'2024-01-01T00:00:00'")
        """
        self._filter.append(expression)
        return self

    def expand(self, *navigations: str) -> ODataQueryBuilder:
        """Add navigation properties to $expand."""
        self._expand.extend(navigations)
        return self

    def orderby(self, field: str, *, descending: bool = False) -> ODataQueryBuilder:
        """Add an $orderby clause."""
        direction = "desc" if descending else "asc"
        self._orderby.append(f"{field} {direction}")
        return self

    def top(self, n: int) -> ODataQueryBuilder:
        """Limit the number of results ($top)."""
        self._top = n
        return self

    def skip(self, n: int) -> ODataQueryBuilder:
        """Skip the first *n* results ($skip)."""
        self._skip = n
        return self

    def inlinecount(self) -> ODataQueryBuilder:
        """Request inline count ($inlinecount=allpages for OData V2)."""
        self._inlinecount = True
        return self

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> str:
        """Build the query string (without leading '?')."""
        parts: list[str] = []

        if self._select:
            parts.append(f"$select={','.join(self._select)}")
        if self._filter:
            combined = " and ".join(self._filter)
            parts.append(f"$filter={combined}")
        if self._expand:
            parts.append(f"$expand={','.join(self._expand)}")
        if self._orderby:
            parts.append(f"$orderby={','.join(self._orderby)}")
        if self._top is not None:
            parts.append(f"$top={self._top}")
        if self._skip is not None:
            parts.append(f"$skip={self._skip}")
        if self._inlinecount:
            parts.append("$inlinecount=allpages")

        return "&".join(parts)

    def build_path(self, entity_set: str) -> str:
        """Build a full OData path: ``EntitySet?query``."""
        query = self.build()
        if query:
            return f"{entity_set}?{query}"
        return entity_set
