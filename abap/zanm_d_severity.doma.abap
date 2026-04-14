"! Domain: Anomaly severity level
"! Fixed values: LOW, MEDIUM, HIGH, CRITICAL
DOMAIN zanm_d_severity.

  @EndUserText.label : 'Anomaly Severity'
  FORMAT          : CHAR(10)
  OUTPUT_LENGTH   : 10
  VALUE_TABLE     : ' '

  FIXED_VALUES:
    'LOW'       : 'Low severity',
    'MEDIUM'    : 'Medium severity',
    'HIGH'      : 'High severity',
    'CRITICAL'  : 'Critical severity'.

ENDDOMAIN.
