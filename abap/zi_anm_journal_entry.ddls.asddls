@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Interface View - Journal Entry'

define view entity ZI_ANM_JOURNAL_ENTRY
  as select from bkpf
  inner join bseg on  bseg.bukrs = bkpf.bukrs
                   and bseg.belnr = bkpf.belnr
                   and bseg.gjahr = bkpf.gjahr
{
  key bkpf.bukrs    as CompanyCode,
  key bkpf.belnr    as DocumentNumber,
  key bkpf.gjahr    as FiscalYear,
  key bseg.buzei    as LineItem,

      // Header fields
      bkpf.blart    as DocumentType,
      bkpf.budat    as PostingDate,
      bkpf.bldat    as DocumentDate,
      bkpf.monat    as FiscalPeriod,
      bkpf.cpudt    as EntryDate,
      bkpf.cputm    as EntryTime,
      bkpf.usnam    as EnteredBy,
      bkpf.tcode    as TransactionCode,
      bkpf.bstat    as DocumentStatus,
      bkpf.waers    as CurrencyKey,
      bkpf.kursf    as ExchangeRate,
      bkpf.bktxt    as HeaderText,
      bkpf.stblg    as ReversalDocument,
      bkpf.stjah    as ReversalYear,

      // Line item fields
      bseg.koart    as AccountType,
      bseg.hkont    as GLAccount,
      bseg.shkzg    as DebitCreditIndicator,
      @Semantics.amount.currencyCode: 'CurrencyKey'
      bseg.dmbtr    as AmountInLocalCurrency,
      @Semantics.amount.currencyCode: 'CurrencyKey'
      bseg.wrbtr    as AmountInDocCurrency,
      bseg.mwskz    as TaxCode,
      bseg.kostl    as CostCenter,
      bseg.aufnr    as InternalOrder,
      bseg.prctr    as ProfitCenter,
      bseg.lifnr    as Vendor,
      bseg.kunnr    as Customer,
      bseg.sgtxt    as ItemText,
      bseg.zuonr    as AssignmentNumber
}
