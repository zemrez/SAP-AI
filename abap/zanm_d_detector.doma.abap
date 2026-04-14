"! Domain: Detector type identifier
"! Fixed values: AMOUNT, DUPLICATE, TIMING, COMBO, ROUND, ML
DOMAIN zanm_d_detector.

  @EndUserText.label : 'Detector Type'
  FORMAT          : CHAR(30)
  OUTPUT_LENGTH   : 30
  VALUE_TABLE     : ' '

  FIXED_VALUES:
    'AMOUNT'    : 'Amount threshold detector',
    'DUPLICATE' : 'Duplicate entry detector',
    'TIMING'    : 'Off-hours timing detector',
    'COMBO'     : 'Unusual combination detector',
    'ROUND'     : 'Round amount detector',
    'ML'        : 'Machine learning detector'.

ENDDOMAIN.
