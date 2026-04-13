"! Data Element: Risk score (0-100)
"! Based on domain ZANM_D_RISK_SCORE
DATA_ELEMENT zanm_risk_score.

  @EndUserText.label       : 'Risk Score'
  @EndUserText.quickInfo   : 'Anomaly Risk Score (0-100)'
  DOMAIN                   : zanm_d_risk_score

  FIELD_LABELS:
    SHORT   : 'Risk',
    MEDIUM  : 'Risk Score',
    LONG    : 'Anomaly Risk Score',
    HEADING : 'Risk Score'.

ENDDATA_ELEMENT.
