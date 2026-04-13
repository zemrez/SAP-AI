"! Domain: Risk score (0-100)
"! NUMC(3), value range 0 to 100
DOMAIN zanm_d_risk_score.

  @EndUserText.label : 'Risk Score (0-100)'
  FORMAT          : NUMC(3)
  OUTPUT_LENGTH   : 3
  VALUE_TABLE     : ' '

  VALUE_RANGE:
    LOW  : '000',
    HIGH : '100'.

ENDDOMAIN.
