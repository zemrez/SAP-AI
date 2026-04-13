"""Pydantic models for SAP financial data structures."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class JournalEntry(BaseModel):
    """Single journal entry line item from API_JOURNALENTRYITEMBASIC_SRV."""

    company_code: str = Field(..., alias="CompanyCode")
    fiscal_year: str = Field(..., alias="FiscalYear")
    accounting_document: str = Field(..., alias="AccountingDocument")
    accounting_document_item: str = Field(..., alias="AccountingDocumentItem")
    posting_date: str = Field(..., alias="PostingDate")
    document_date: str = Field(..., alias="DocumentDate")
    gl_account: str = Field(..., alias="GLAccount")
    amount_in_company_code_currency: Decimal = Field(..., alias="AmountInCompanyCodeCurrency")
    company_code_currency: str = Field(..., alias="CompanyCodeCurrency")
    debit_credit_code: str = Field(..., alias="DebitCreditCode")
    document_type: str = Field(..., alias="AccountingDocumentType")
    reference_document: str = Field("", alias="ReferenceDocument")
    document_header_text: str = Field("", alias="DocumentHeaderText")
    created_by_user: str = Field("", alias="AccountingDocumentCreatedByUser")

    model_config = {"populate_by_name": True}


class GLAccount(BaseModel):
    """General Ledger master data from API_GLACCOUNTINCHARTOFACCOUNTS_SRV."""

    chart_of_accounts: str = Field(..., alias="ChartOfAccounts")
    gl_account: str = Field(..., alias="GLAccount")
    gl_account_name: str = Field("", alias="GLAccountName")
    gl_account_group: str = Field("", alias="GLAccountGroup")
    gl_account_type: str = Field("", alias="GLAccountType")
    is_balance_sheet_account: bool = Field(False, alias="IsBalanceSheetAccount")
    profit_loss_account_type: str = Field("", alias="ProfitLossAccountType")

    model_config = {"populate_by_name": True}


class VendorInvoice(BaseModel):
    """Vendor invoice item from API_SUPPLIERINVOICE_PROCESS_SRV."""

    supplier_invoice: str = Field(..., alias="SupplierInvoice")
    fiscal_year: str = Field(..., alias="FiscalYear")
    company_code: str = Field(..., alias="CompanyCode")
    supplier: str = Field("", alias="InvoicingParty")
    document_date: str = Field("", alias="DocumentDate")
    posting_date: str = Field("", alias="PostingDate")
    invoice_gross_amount: Decimal = Field(..., alias="InvoiceGrossAmount")
    document_currency: str = Field(..., alias="DocumentCurrency")
    payment_terms: str = Field("", alias="PaymentTerms")
    is_cleared: bool = Field(False, alias="IsCleared")
    reference_document: str = Field("", alias="SupplierInvoiceIDByInvoicingParty")

    model_config = {"populate_by_name": True}
