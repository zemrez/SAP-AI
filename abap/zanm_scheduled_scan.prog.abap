*&---------------------------------------------------------------------*
*& Report ZANM_SCHEDULED_SCAN
*&---------------------------------------------------------------------*
*& Background job program for scheduled anomaly detection scans.
*& Designed for SM36 scheduling. Creates a scan run via the orchestrator
*& and logs results to the application log (BAL).
*&---------------------------------------------------------------------*
REPORT zanm_scheduled_scan.

* Selection screen
SELECTION-SCREEN BEGIN OF BLOCK b01 WITH FRAME TITLE TEXT-b01.
  PARAMETERS:     p_bukrs  TYPE bukrs     OBLIGATORY.
  PARAMETERS:     p_dfrom  TYPE budat.
  PARAMETERS:     p_dto    TYPE budat.
  PARAMETERS:     p_stype  TYPE char12     DEFAULT 'FULL'.
SELECTION-SCREEN END OF BLOCK b01.

* Initialization: set default date range
INITIALIZATION.
  " Default: last 30 days (configurable via ZANM_CONFIG)
  DATA lv_default_days TYPE i VALUE 30.
  TRY.
      DATA(lv_days_str) = zcl_anm_config_manager=>get_config(
        zcl_anm_config_manager=>gc_key_scan_days ).
      lv_default_days = lv_days_str.
    CATCH zcx_anm_exception.
      " Use hardcoded default
  ENDTRY.

  p_dto   = sy-datum.
  p_dfrom = sy-datum - lv_default_days.


* Main processing
START-OF-SELECTION.

  DATA lv_scan_id TYPE sysuuid_x16.
  DATA lv_log_handle TYPE balloghndl.

  " --- Initialize application log ---
  DATA ls_log TYPE bal_s_log.
  ls_log-extnumber = |ZANM_SCAN_{ p_bukrs }_{ sy-datum }|.
  ls_log-object    = 'ZANM'.
  ls_log-subobject = 'SCAN'.
  ls_log-aluser    = sy-uname.
  ls_log-alprog    = sy-repid.

  CALL FUNCTION 'BAL_LOG_CREATE'
    EXPORTING
      i_s_log                 = ls_log
    IMPORTING
      e_log_handle            = lv_log_handle
    EXCEPTIONS
      log_header_inconsistent = 1
      OTHERS                  = 2.

  IF sy-subrc <> 0.
    WRITE: / 'WARNING: Could not create application log.'.
  ENDIF.

  " --- Log start message ---
  DATA ls_msg TYPE bal_s_msg.
  ls_msg-msgty = 'I'.
  ls_msg-msgid = 'ZANM_MSG'.
  ls_msg-msgno = '010'.
  ls_msg-msgv1 = p_bukrs.
  ls_msg-msgv2 = p_dfrom.
  ls_msg-msgv3 = p_dto.
  ls_msg-msgv4 = p_stype.

  CALL FUNCTION 'BAL_LOG_MSG_ADD'
    EXPORTING
      i_log_handle = lv_log_handle
      i_s_msg      = ls_msg
    EXCEPTIONS
      OTHERS       = 1.

  WRITE: / |Starting anomaly scan for { p_bukrs }: { p_dfrom } to { p_dto } ({ p_stype })|.

  " --- Trigger scan via orchestrator ---
  TRY.
      lv_scan_id = zcl_anm_orchestrator=>trigger_scan(
        iv_bukrs     = p_bukrs
        iv_date_from = p_dfrom
        iv_date_to   = p_dto
        iv_scan_type = p_stype ).

      " Log success
      CLEAR ls_msg.
      ls_msg-msgty = 'S'.
      ls_msg-msgid = 'ZANM_MSG'.
      ls_msg-msgno = '011'.
      ls_msg-msgv1 = lv_scan_id.

      CALL FUNCTION 'BAL_LOG_MSG_ADD'
        EXPORTING
          i_log_handle = lv_log_handle
          i_s_msg      = ls_msg
        EXCEPTIONS
          OTHERS       = 1.

      WRITE: / |Scan triggered successfully. Scan ID: { lv_scan_id }|.

    CATCH zcx_anm_exception INTO DATA(lx_anm).
      " Log application error
      CLEAR ls_msg.
      ls_msg-msgty = 'E'.
      ls_msg-msgid = 'ZANM_MSG'.
      ls_msg-msgno = '012'.
      ls_msg-msgv1 = lx_anm->mv_details.

      CALL FUNCTION 'BAL_LOG_MSG_ADD'
        EXPORTING
          i_log_handle = lv_log_handle
          i_s_msg      = ls_msg
        EXCEPTIONS
          OTHERS       = 1.

      WRITE: / |ERROR: Scan failed — { lx_anm->mv_details }|.

    CATCH cx_no_authority INTO DATA(lx_auth).
      " Log authorization error
      CLEAR ls_msg.
      ls_msg-msgty = 'E'.
      ls_msg-msgid = 'ZANM_MSG'.
      ls_msg-msgno = '013'.
      ls_msg-msgv1 = p_bukrs.
      ls_msg-msgv2 = sy-uname.

      CALL FUNCTION 'BAL_LOG_MSG_ADD'
        EXPORTING
          i_log_handle = lv_log_handle
          i_s_msg      = ls_msg
        EXCEPTIONS
          OTHERS       = 1.

      WRITE: / |ERROR: No authorization for company code { p_bukrs }|.

    CATCH cx_root INTO DATA(lx_root).
      " Log unexpected error
      CLEAR ls_msg.
      ls_msg-msgty = 'A'.
      ls_msg-msgid = 'ZANM_MSG'.
      ls_msg-msgno = '014'.
      ls_msg-msgv1 = lx_root->get_text( ).

      CALL FUNCTION 'BAL_LOG_MSG_ADD'
        EXPORTING
          i_log_handle = lv_log_handle
          i_s_msg      = ls_msg
        EXCEPTIONS
          OTHERS       = 1.

      WRITE: / |ERROR: Unexpected error — { lx_root->get_text( ) }|.
  ENDTRY.

  " --- Save application log ---
  CALL FUNCTION 'BAL_DB_SAVE'
    EXCEPTIONS
      log_not_found       = 1
      save_not_allowed    = 2
      numbering_error     = 3
      OTHERS              = 4.

  IF sy-subrc = 0.
    WRITE: / 'Application log saved successfully.'.
  ELSE.
    WRITE: / 'WARNING: Failed to save application log.'.
  ENDIF.
