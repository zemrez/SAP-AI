"! Domain: Scan type
"! Fixed values: FULL, INCREMENTAL
DOMAIN zanm_d_scan_type.

  @EndUserText.label : 'Scan Type'
  FORMAT          : CHAR(12)
  OUTPUT_LENGTH   : 12
  VALUE_TABLE     : ' '

  FIXED_VALUES:
    'FULL'        : 'Full scan of date range',
    'INCREMENTAL' : 'Incremental since last scan'.

ENDDOMAIN.
