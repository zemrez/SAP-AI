"! Data Element: Scan type (FULL / INCREMENTAL)
"! Based on domain ZANM_D_SCAN_TYPE
DATA_ELEMENT zanm_scan_type.

  @EndUserText.label       : 'Scan Type'
  @EndUserText.quickInfo   : 'Anomaly Scan Type'
  DOMAIN                   : zanm_d_scan_type

  FIELD_LABELS:
    SHORT   : 'ScanType',
    MEDIUM  : 'Scan Type',
    LONG    : 'Anomaly Scan Type',
    HEADING : 'Scan Type'.

ENDDATA_ELEMENT.
