"! Domain: Scan execution status
"! Fixed values: PENDING, RUNNING, DONE, FAILED
DOMAIN zanm_d_scan_status.

  @EndUserText.label : 'Scan Status'
  FORMAT          : CHAR(10)
  OUTPUT_LENGTH   : 10
  VALUE_TABLE     : ' '

  FIXED_VALUES:
    'PENDING'   : 'Scan is queued',
    'RUNNING'   : 'Scan in progress',
    'DONE'      : 'Scan completed',
    'FAILED'    : 'Scan failed'.

ENDDOMAIN.
