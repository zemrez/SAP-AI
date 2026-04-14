"! Main orchestrator for Anomaly Detective scan execution
"! Coordinates scan lifecycle: create run, call Python sidecar, store results
CLASS zcl_anm_orchestrator DEFINITION
  PUBLIC
  FINAL
  CREATE PUBLIC.

  PUBLIC SECTION.

    "! Anomaly record structure matching Python sidecar response
    TYPES:
      BEGIN OF ty_anomaly_input,
        detector     TYPE char30,
        anomaly_type TYPE char50,
        risk_score   TYPE i,
        severity     TYPE char10,
        belnr        TYPE belnr_d,
        bukrs        TYPE bukrs,
        gjahr        TYPE gjahr,
        budat        TYPE budat,
        dmbtr        TYPE dmbtr,
        waers        TYPE waers,
        description  TYPE string,
        details_json TYPE string,
      END OF ty_anomaly_input,
      tt_anomaly_input TYPE STANDARD TABLE OF ty_anomaly_input WITH DEFAULT KEY.

    "! Trigger a new anomaly detection scan
    "! Creates ZANM_SCAN_RUN entry and calls Python sidecar via HTTP
    "! @parameter iv_bukrs     | Company code
    "! @parameter iv_date_from | Start date for scan
    "! @parameter iv_date_to   | End date for scan
    "! @parameter iv_scan_type | FULL or INCREMENTAL
    "! @parameter rv_scan_id   | Generated scan UUID
    "! @raising zcx_anm_exception | SCAN_FAILED on errors
    "! @raising cx_no_authority   | When user lacks authorization
    CLASS-METHODS trigger_scan
      IMPORTING
        iv_bukrs          TYPE bukrs
        iv_date_from      TYPE budat
        iv_date_to        TYPE budat
        iv_scan_type      TYPE char12 DEFAULT 'FULL'
      RETURNING
        VALUE(rv_scan_id) TYPE sysuuid_x16
      RAISING
        zcx_anm_exception
        cx_no_authority.

    "! Get current status of a scan run
    "! @parameter iv_scan_id | Scan UUID
    "! @parameter rv_status  | Current status (PENDING/RUNNING/DONE/FAILED)
    "! @raising zcx_anm_exception | SCAN_FAILED if scan not found
    CLASS-METHODS get_scan_status
      IMPORTING
        iv_scan_id        TYPE sysuuid_x16
      RETURNING
        VALUE(rv_status)  TYPE char10
      RAISING
        zcx_anm_exception.

    "! Callback when Python sidecar finishes — updates scan run record
    "! @parameter iv_scan_id      | Scan UUID
    "! @parameter iv_status       | Final status (DONE or FAILED)
    "! @parameter iv_anomaly_count | Number of anomalies found
    "! @parameter iv_records_scand | Number of records scanned
    "! @parameter iv_error_msg    | Error message (if FAILED)
    CLASS-METHODS on_scan_complete
      IMPORTING
        iv_scan_id       TYPE sysuuid_x16
        iv_status        TYPE char10
        iv_anomaly_count TYPE i DEFAULT 0
        iv_records_scand TYPE i DEFAULT 0
        iv_error_msg     TYPE string OPTIONAL.

    "! Write anomalies received from Python sidecar into ZANM_ANOMALY
    "! @parameter iv_scan_id   | Parent scan UUID
    "! @parameter it_anomalies | Anomaly records from Python
    "! @raising zcx_anm_exception | On write errors
    CLASS-METHODS write_anomalies
      IMPORTING
        iv_scan_id   TYPE sysuuid_x16
        it_anomalies TYPE tt_anomaly_input
      RAISING
        zcx_anm_exception.

  PROTECTED SECTION.
  PRIVATE SECTION.

    "! Build HTTP request body for Python sidecar
    CLASS-METHODS build_sidecar_payload
      IMPORTING
        iv_scan_id   TYPE sysuuid_x16
        iv_bukrs     TYPE bukrs
        iv_date_from TYPE budat
        iv_date_to   TYPE budat
        iv_scan_type TYPE char12
      RETURNING
        VALUE(rv_json) TYPE string.

    "! Call Python sidecar /api/v1/scans/trigger endpoint via HTTP
    CLASS-METHODS call_sidecar
      IMPORTING
        iv_json TYPE string
      RAISING
        zcx_anm_exception.

ENDCLASS.


CLASS zcl_anm_orchestrator IMPLEMENTATION.

  METHOD trigger_scan.
    " Authorization check — user needs EXECUTE on this company code
    zcl_anm_auth=>check_authority(
      iv_actvt = zcl_anm_auth=>gc_actvt_execute
      iv_bukrs = iv_bukrs ).

    " Generate scan ID
    rv_scan_id = zcl_anm_uuid=>generate( ).

    " Create scan run record with PENDING status
    DATA ls_scan TYPE zanm_scan_run.
    GET TIME STAMP FIELD DATA(lv_timestamp).

    ls_scan-scan_id    = rv_scan_id.
    ls_scan-bukrs      = iv_bukrs.
    ls_scan-scan_type  = iv_scan_type.
    ls_scan-status     = 'PENDING'.
    ls_scan-date_from  = iv_date_from.
    ls_scan-date_to    = iv_date_to.
    ls_scan-created_by = sy-uname.
    ls_scan-created_at = lv_timestamp.
    ls_scan-started_at = lv_timestamp.

    INSERT zanm_scan_run FROM ls_scan.
    IF sy-subrc <> 0.
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_scan_failed
          details = |Failed to create scan run record|.
    ENDIF.

    COMMIT WORK AND WAIT.

    " Update status to RUNNING
    UPDATE zanm_scan_run SET status = 'RUNNING'
      WHERE scan_id = rv_scan_id.
    COMMIT WORK AND WAIT.

    " Call Python sidecar asynchronously via HTTP
    DATA(lv_json) = build_sidecar_payload(
      iv_scan_id   = rv_scan_id
      iv_bukrs     = iv_bukrs
      iv_date_from = iv_date_from
      iv_date_to   = iv_date_to
      iv_scan_type = iv_scan_type ).

    TRY.
        call_sidecar( lv_json ).
      CATCH zcx_anm_exception INTO DATA(lx_err).
        " Mark scan as failed if sidecar call fails
        on_scan_complete(
          iv_scan_id  = rv_scan_id
          iv_status   = 'FAILED'
          iv_error_msg = lx_err->mv_details ).
        RAISE EXCEPTION lx_err.
    ENDTRY.
  ENDMETHOD.


  METHOD get_scan_status.
    SELECT SINGLE status FROM zanm_scan_run
      INTO rv_status
      WHERE scan_id = iv_scan_id.

    IF sy-subrc <> 0.
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_scan_failed
          details = |Scan run not found|.
    ENDIF.
  ENDMETHOD.


  METHOD on_scan_complete.
    GET TIME STAMP FIELD DATA(lv_timestamp).

    UPDATE zanm_scan_run
      SET status        = iv_status
          anomaly_count = iv_anomaly_count
          records_scand = iv_records_scand
          error_msg     = iv_error_msg
          finished_at   = lv_timestamp
      WHERE scan_id = iv_scan_id.

    COMMIT WORK AND WAIT.
  ENDMETHOD.


  METHOD write_anomalies.
    DATA lt_anomalies TYPE STANDARD TABLE OF zanm_anomaly.
    DATA ls_anomaly TYPE zanm_anomaly.

    GET TIME STAMP FIELD DATA(lv_timestamp).

    LOOP AT it_anomalies INTO DATA(ls_input).
      CLEAR ls_anomaly.

      ls_anomaly-anomaly_id   = zcl_anm_uuid=>generate( ).
      ls_anomaly-scan_id      = iv_scan_id.
      ls_anomaly-detector     = ls_input-detector.
      ls_anomaly-anomaly_type = ls_input-anomaly_type.
      ls_anomaly-risk_score   = ls_input-risk_score.
      ls_anomaly-severity     = ls_input-severity.
      ls_anomaly-belnr        = ls_input-belnr.
      ls_anomaly-bukrs        = ls_input-bukrs.
      ls_anomaly-gjahr        = ls_input-gjahr.
      ls_anomaly-budat        = ls_input-budat.
      ls_anomaly-dmbtr        = ls_input-dmbtr.
      ls_anomaly-waers        = ls_input-waers.
      ls_anomaly-description  = ls_input-description.
      ls_anomaly-details_json = ls_input-details_json.
      ls_anomaly-status       = 'OPEN'.
      ls_anomaly-created_at   = lv_timestamp.

      APPEND ls_anomaly TO lt_anomalies.
    ENDLOOP.

    IF lt_anomalies IS NOT INITIAL.
      INSERT zanm_anomaly FROM TABLE lt_anomalies.
      IF sy-subrc <> 0.
        RAISE EXCEPTION TYPE zcx_anm_exception
          EXPORTING
            textid  = zcx_anm_exception=>gc_scan_failed
            details = |Failed to write anomaly records|.
      ENDIF.
      COMMIT WORK AND WAIT.
    ENDIF.
  ENDMETHOD.


  METHOD build_sidecar_payload.
    " Build JSON payload for POST /api/v1/scans/trigger
    DATA(lv_scan_id_str) = zcl_anm_uuid=>generate_as_string( ).
    " Use the actual scan_id passed in
    lv_scan_id_str = iv_scan_id.

    rv_json = |\{| &&
              |"scan_id":"{ lv_scan_id_str }",| &&
              |"bukrs":"{ iv_bukrs }",| &&
              |"date_from":"{ iv_date_from }",| &&
              |"date_to":"{ iv_date_to }",| &&
              |"scan_type":"{ iv_scan_type }"| &&
              |\}|.
  ENDMETHOD.


  METHOD call_sidecar.
    " Read sidecar URL from configuration
    DATA lv_url TYPE string.
    TRY.
        lv_url = zcl_anm_config_manager=>get_config( zcl_anm_config_manager=>gc_key_sidecar_url ).
      CATCH zcx_anm_exception.
        lv_url = 'http://localhost:8011'.
    ENDTRY.

    lv_url = lv_url && '/api/v1/scans/trigger'.

    " Create HTTP client
    DATA lo_http_client TYPE REF TO if_http_client.

    cl_http_client=>create_by_url(
      EXPORTING
        url                = lv_url
      IMPORTING
        client             = lo_http_client
      EXCEPTIONS
        argument_not_found = 1
        plugin_not_active  = 2
        internal_error     = 3
        OTHERS             = 4 ).

    IF sy-subrc <> 0.
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_scan_failed
          details = |HTTP client creation failed for URL: { lv_url }|.
    ENDIF.

    " Configure request
    lo_http_client->request->set_method( if_http_request=>co_request_method_post ).
    lo_http_client->request->set_content_type( 'application/json' ).
    lo_http_client->request->set_cdata( iv_json ).

    " Send request (asynchronous — fire and forget)
    lo_http_client->send(
      EXCEPTIONS
        http_communication_failure = 1
        http_invalid_state         = 2
        http_processing_failed     = 3
        OTHERS                     = 4 ).

    IF sy-subrc <> 0.
      DATA(lv_error) = lo_http_client->get_last_error( ).
      lo_http_client->close( ).
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_scan_failed
          details = |HTTP send failed: { lv_error }|.
    ENDIF.

    " Receive response to complete the request cycle
    lo_http_client->receive(
      EXCEPTIONS
        http_communication_failure = 1
        http_invalid_state         = 2
        http_processing_failed     = 3
        OTHERS                     = 4 ).

    IF sy-subrc <> 0.
      DATA(lv_recv_err) = lo_http_client->get_last_error( ).
      lo_http_client->close( ).
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_scan_failed
          details = |HTTP receive failed: { lv_recv_err }|.
    ENDIF.

    " Check HTTP status
    DATA(lv_status) = lo_http_client->response->get_header_field( '~status_code' ).
    lo_http_client->close( ).

    IF lv_status < '200' OR lv_status >= '300'.
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_scan_failed
          details = |Sidecar returned HTTP { lv_status }|.
    ENDIF.
  ENDMETHOD.

ENDCLASS.
