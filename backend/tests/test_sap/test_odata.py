"""Tests for ODataQueryBuilder."""

import sys
from pathlib import Path

# Ensure backend root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sap.odata import ODataQueryBuilder


class TestODataQueryBuilder:
    def test_empty_build(self):
        query = ODataQueryBuilder().build()
        assert query == ""

    def test_select_single(self):
        query = ODataQueryBuilder().select("CompanyCode").build()
        assert query == "$select=CompanyCode"

    def test_select_multiple(self):
        query = ODataQueryBuilder().select("CompanyCode", "FiscalYear", "Amount").build()
        assert query == "$select=CompanyCode,FiscalYear,Amount"

    def test_filter_single(self):
        query = ODataQueryBuilder().filter("CompanyCode eq '1000'").build()
        assert query == "$filter=CompanyCode eq '1000'"

    def test_filter_multiple_joined_with_and(self):
        query = (
            ODataQueryBuilder()
            .filter("CompanyCode eq '1000'")
            .filter("FiscalYear eq '2024'")
            .build()
        )
        assert query == "$filter=CompanyCode eq '1000' and FiscalYear eq '2024'"

    def test_expand(self):
        query = ODataQueryBuilder().expand("to_Items", "to_Partner").build()
        assert query == "$expand=to_Items,to_Partner"

    def test_orderby_ascending(self):
        query = ODataQueryBuilder().orderby("Amount").build()
        assert query == "$orderby=Amount asc"

    def test_orderby_descending(self):
        query = ODataQueryBuilder().orderby("Amount", descending=True).build()
        assert query == "$orderby=Amount desc"

    def test_top(self):
        query = ODataQueryBuilder().top(100).build()
        assert query == "$top=100"

    def test_skip(self):
        query = ODataQueryBuilder().skip(50).build()
        assert query == "$skip=50"

    def test_inlinecount(self):
        query = ODataQueryBuilder().inlinecount().build()
        assert query == "$inlinecount=allpages"

    def test_full_query(self):
        query = (
            ODataQueryBuilder()
            .select("CompanyCode", "Amount")
            .filter("CompanyCode eq '1000'")
            .filter("Amount gt 1000")
            .expand("to_Items")
            .orderby("Amount", descending=True)
            .top(50)
            .skip(10)
            .build()
        )
        assert "$select=CompanyCode,Amount" in query
        assert "$filter=CompanyCode eq '1000' and Amount gt 1000" in query
        assert "$expand=to_Items" in query
        assert "$orderby=Amount desc" in query
        assert "$top=50" in query
        assert "$skip=10" in query

    def test_build_path(self):
        path = (
            ODataQueryBuilder()
            .select("CompanyCode")
            .top(10)
            .build_path("A_JournalEntryItemBasic")
        )
        assert path.startswith("A_JournalEntryItemBasic?")
        assert "$select=CompanyCode" in path
        assert "$top=10" in path

    def test_build_path_no_query(self):
        path = ODataQueryBuilder().build_path("A_JournalEntryItemBasic")
        assert path == "A_JournalEntryItemBasic"

    def test_chaining_returns_same_instance(self):
        builder = ODataQueryBuilder()
        result = builder.select("A").filter("B eq 'C'").top(10)
        assert result is builder

    def test_filter_operators(self):
        """Ensure SAP OData filter operators are passed through correctly."""
        for op in ("eq", "ne", "gt", "lt", "ge", "le"):
            query = ODataQueryBuilder().filter(f"Amount {op} 100").build()
            assert f"Amount {op} 100" in query
