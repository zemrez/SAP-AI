"! Data Element: Anomaly investigation status
"! Based on domain ZANM_D_ANOM_STATUS
DATA_ELEMENT zanm_anom_status.

  @EndUserText.label       : 'Anomaly Status'
  @EndUserText.quickInfo   : 'Anomaly Investigation Status'
  DOMAIN                   : zanm_d_anom_status

  FIELD_LABELS:
    SHORT   : 'Anom.Stat',
    MEDIUM  : 'Anomaly Status',
    LONG    : 'Anomaly Investigation Status',
    HEADING : 'Anom Status'.

ENDDATA_ELEMENT.
