@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Interface View - Scan Run'

define view entity ZI_ANM_SCAN_RUN
  as select from zanm_scan_run
{
  key scan_id       as ScanId,
      bukrs         as CompanyCode,
      scan_type     as ScanType,
      status        as Status,
      date_from     as DateFrom,
      date_to       as DateTo,
      records_scand as RecordsScanned,
      anomaly_count as AnomalyCount,
      error_msg     as ErrorMessage,
      started_at    as StartedAt,
      finished_at   as FinishedAt,
      created_by    as CreatedBy,
      created_at    as CreatedAt
}
