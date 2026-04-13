"! Data Element: Scan execution status
"! Based on domain ZANM_D_SCAN_STATUS
DATA_ELEMENT zanm_scan_status.

  @EndUserText.label       : 'Scan Status'
  @EndUserText.quickInfo   : 'Anomaly Scan Execution Status'
  DOMAIN                   : zanm_d_scan_status

  FIELD_LABELS:
    SHORT   : 'Status',
    MEDIUM  : 'Scan Status',
    LONG    : 'Scan Execution Status',
    HEADING : 'Scan Status'.

ENDDATA_ELEMENT.
