"! Domain: Anomaly investigation status
"! Fixed values: OPEN, INVESTIGATING, RESOLVED, FALSE_POS
DOMAIN zanm_d_anom_status.

  @EndUserText.label : 'Anomaly Status'
  FORMAT          : CHAR(15)
  OUTPUT_LENGTH   : 15
  VALUE_TABLE     : ' '

  FIXED_VALUES:
    'OPEN'          : 'Newly detected',
    'INVESTIGATING' : 'Under investigation',
    'RESOLVED'      : 'Resolved',
    'FALSE_POS'     : 'False positive'.

ENDDOMAIN.
