"! Data Element: Anomaly severity level
"! Based on domain ZANM_D_SEVERITY
DATA_ELEMENT zanm_severity.

  @EndUserText.label       : 'Severity'
  @EndUserText.quickInfo   : 'Anomaly Severity Level'
  DOMAIN                   : zanm_d_severity

  FIELD_LABELS:
    SHORT   : 'Severity',
    MEDIUM  : 'Severity',
    LONG    : 'Anomaly Severity Level',
    HEADING : 'Severity'.

ENDDATA_ELEMENT.
