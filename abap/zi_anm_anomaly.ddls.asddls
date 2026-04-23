@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Interface View - Anomaly'

define view entity ZI_ANM_ANOMALY
  as select from zanm_anomaly
  association [1..1] to ZI_ANM_SCAN_RUN as _ScanRun
    on $projection.ScanId = _ScanRun.ScanId
{
  key anomaly_id    as AnomalyId,
      scan_id       as ScanId,
      detector      as Detector,
      anomaly_type  as AnomalyType,
      risk_score    as RiskScore,
      severity      as Severity,
      belnr         as DocumentNumber,
      bukrs         as CompanyCode,
      gjahr         as FiscalYear,
      budat         as PostingDate,
      @Semantics.amount.currencyCode: 'Currency'
      dmbtr         as AmountInLocalCurrency,
      waers         as Currency,
      description   as Description,
      details_json  as DetailsJson,
      status        as Status,
      assigned_to   as AssignedTo,
      resolution    as Resolution,
      resolved_at   as ResolvedAt,
      created_at    as CreatedAt,

      /* Virtual elements for UI criticality */
      case Severity
        when 'CRITICAL' then 1
        when 'HIGH'     then 1
        when 'MEDIUM'   then 2
        when 'LOW'      then 3
        else 0
      end as SeverityCriticality,

      case Status
        when 'OPEN'          then 1
        when 'INVESTIGATING' then 2
        when 'RESOLVED'      then 3
        when 'FALSE_POS'     then 0
        else 0
      end as StatusCriticality,

      /* Associations */
      _ScanRun
}
