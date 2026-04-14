"! OData DPC extension handler for Anomaly Detective
"! Provides CRUD operations for all Z table entities exposed via OData V4
CLASS zcl_anm_odata_handler DEFINITION
  PUBLIC
  FINAL
  CREATE PUBLIC.

  PUBLIC SECTION.

    "! Anomaly list filter structure
    TYPES:
      BEGIN OF ty_anomaly_filter,
        bukrs    TYPE bukrs,
        severity TYPE char10,
        status   TYPE char15,
        detector TYPE char30,
        scan_id  TYPE sysuuid_x16,
      END OF ty_anomaly_filter.

    "! Pagination parameters
    TYPES:
      BEGIN OF ty_paging,
        top  TYPE i,
        skip TYPE i,
      END OF ty_paging.

    " --- Scan Run operations ---

    "! Create a new scan run (called from Python sidecar or Fiori UI)
    "! @parameter iv_bukrs     | Company code
    "! @parameter iv_date_from | Start date
    "! @parameter iv_date_to   | End date
    "! @parameter iv_scan_type | FULL or INCREMENTAL
    "! @parameter rv_scan_id   | Created scan UUID
    "! @raising zcx_anm_exception | On creation errors
    "! @raising cx_no_authority   | When user lacks authorization
    CLASS-METHODS create_scan
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

    "! Read a single scan run by ID
    "! @parameter iv_scan_id | Scan UUID
    "! @parameter rs_scan    | Scan run record
    "! @raising zcx_anm_exception | SCAN_FAILED if not found
    CLASS-METHODS read_scan
      IMPORTING
        iv_scan_id     TYPE sysuuid_x16
      RETURNING
        VALUE(rs_scan) TYPE zanm_scan_run
      RAISING
        zcx_anm_exception.

    "! Read all scan runs for a company code
    "! @parameter iv_bukrs | Company code (optional — returns all if empty)
    "! @parameter is_paging | Pagination (optional)
    "! @parameter rt_scans | Scan run records
    CLASS-METHODS read_scan_list
      IMPORTING
        iv_bukrs         TYPE bukrs OPTIONAL
        is_paging        TYPE ty_paging OPTIONAL
      RETURNING
        VALUE(rt_scans)  TYPE STANDARD TABLE OF zanm_scan_run WITH DEFAULT KEY.

    " --- Anomaly operations ---

    "! Update anomaly status (investigate, resolve, mark as false positive)
    "! @parameter iv_anomaly_id | Anomaly UUID
    "! @parameter iv_status     | New status
    "! @parameter iv_assigned_to | Assigned user (optional)
    "! @parameter iv_resolution | Resolution note (optional)
    "! @raising zcx_anm_exception | ODATA_ERROR if anomaly not found
    CLASS-METHODS update_anomaly
      IMPORTING
        iv_anomaly_id  TYPE sysuuid_x16
        iv_status      TYPE char15
        iv_assigned_to TYPE syuname OPTIONAL
        iv_resolution  TYPE string OPTIONAL
      RAISING
        zcx_anm_exception.

    "! Read anomaly list with filters, sorting, and pagination
    "! @parameter is_filter    | Filter criteria
    "! @parameter is_paging    | Pagination (top/skip)
    "! @parameter iv_order_by  | Sort field (default: risk_score)
    "! @parameter iv_order_dir | Sort direction (ASC/DESC, default: DESC)
    "! @parameter rt_anomalies | Anomaly records
    CLASS-METHODS get_anomaly_list
      IMPORTING
        is_filter           TYPE ty_anomaly_filter OPTIONAL
        is_paging           TYPE ty_paging OPTIONAL
        iv_order_by         TYPE string DEFAULT 'RISK_SCORE'
        iv_order_dir        TYPE string DEFAULT 'DESC'
      RETURNING
        VALUE(rt_anomalies) TYPE STANDARD TABLE OF zanm_anomaly WITH DEFAULT KEY.

    "! Read a single anomaly by ID
    "! @parameter iv_anomaly_id | Anomaly UUID
    "! @parameter rs_anomaly    | Anomaly record
    "! @raising zcx_anm_exception | ODATA_ERROR if not found
    CLASS-METHODS read_anomaly
      IMPORTING
        iv_anomaly_id     TYPE sysuuid_x16
      RETURNING
        VALUE(rs_anomaly) TYPE zanm_anomaly
      RAISING
        zcx_anm_exception.

    "! Deep entity read: get all anomalies for a given scan
    "! @parameter iv_scan_id   | Parent scan UUID
    "! @parameter rt_anomalies | Anomaly records for this scan
    CLASS-METHODS get_anomalies_for_scan
      IMPORTING
        iv_scan_id          TYPE sysuuid_x16
      RETURNING
        VALUE(rt_anomalies) TYPE STANDARD TABLE OF zanm_anomaly WITH DEFAULT KEY.

    "! Delete an anomaly (admin operation)
    "! @parameter iv_anomaly_id | Anomaly UUID
    "! @raising zcx_anm_exception | ODATA_ERROR if not found
    CLASS-METHODS delete_anomaly
      IMPORTING
        iv_anomaly_id TYPE sysuuid_x16
      RAISING
        zcx_anm_exception.

  PROTECTED SECTION.
  PRIVATE SECTION.
ENDCLASS.


CLASS zcl_anm_odata_handler IMPLEMENTATION.

  METHOD create_scan.
    " Delegate to orchestrator which handles auth, record creation, and sidecar call
    rv_scan_id = zcl_anm_orchestrator=>trigger_scan(
      iv_bukrs     = iv_bukrs
      iv_date_from = iv_date_from
      iv_date_to   = iv_date_to
      iv_scan_type = iv_scan_type ).
  ENDMETHOD.


  METHOD read_scan.
    SELECT SINGLE * FROM zanm_scan_run
      INTO rs_scan
      WHERE scan_id = iv_scan_id.

    IF sy-subrc <> 0.
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_odata_error
          details = |Scan run not found|.
    ENDIF.
  ENDMETHOD.


  METHOD read_scan_list.
    IF iv_bukrs IS NOT INITIAL.
      SELECT * FROM zanm_scan_run
        INTO TABLE rt_scans
        WHERE bukrs = iv_bukrs
        ORDER BY created_at DESCENDING.
    ELSE.
      SELECT * FROM zanm_scan_run
        INTO TABLE rt_scans
        ORDER BY created_at DESCENDING.
    ENDIF.

    " Apply pagination
    IF is_paging-top > 0.
      DATA(lv_end) = is_paging-skip + is_paging-top.
      DATA(lv_count) = lines( rt_scans ).

      IF is_paging-skip > 0 AND is_paging-skip < lv_count.
        DELETE rt_scans FROM 1 TO is_paging-skip.
      ENDIF.

      IF is_paging-top < lines( rt_scans ).
        DELETE rt_scans FROM ( is_paging-top + 1 ).
      ENDIF.
    ENDIF.
  ENDMETHOD.


  METHOD update_anomaly.
    DATA ls_anomaly TYPE zanm_anomaly.

    SELECT SINGLE * FROM zanm_anomaly
      INTO ls_anomaly
      WHERE anomaly_id = iv_anomaly_id.

    IF sy-subrc <> 0.
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_odata_error
          details = |Anomaly not found for update|.
    ENDIF.

    ls_anomaly-status = iv_status.

    IF iv_assigned_to IS NOT INITIAL.
      ls_anomaly-assigned_to = iv_assigned_to.
    ENDIF.

    IF iv_resolution IS NOT INITIAL.
      ls_anomaly-resolution = iv_resolution.
    ENDIF.

    " Set resolved timestamp when status changes to RESOLVED or FALSE_POS
    IF iv_status = 'RESOLVED' OR iv_status = 'FALSE_POS'.
      GET TIME STAMP FIELD ls_anomaly-resolved_at.
    ENDIF.

    UPDATE zanm_anomaly FROM ls_anomaly.
    COMMIT WORK AND WAIT.
  ENDMETHOD.


  METHOD get_anomaly_list.
    " Build dynamic WHERE clause based on filters
    DATA lv_where TYPE string.
    DATA lt_where_parts TYPE STANDARD TABLE OF string.

    IF is_filter-bukrs IS NOT INITIAL.
      APPEND |bukrs = '{ is_filter-bukrs }'| TO lt_where_parts.
    ENDIF.
    IF is_filter-severity IS NOT INITIAL.
      APPEND |severity = '{ is_filter-severity }'| TO lt_where_parts.
    ENDIF.
    IF is_filter-status IS NOT INITIAL.
      APPEND |status = '{ is_filter-status }'| TO lt_where_parts.
    ENDIF.
    IF is_filter-detector IS NOT INITIAL.
      APPEND |detector = '{ is_filter-detector }'| TO lt_where_parts.
    ENDIF.
    IF is_filter-scan_id IS NOT INITIAL.
      APPEND |scan_id = @is_filter-scan_id| TO lt_where_parts.
    ENDIF.

    " Concatenate WHERE parts
    IF lt_where_parts IS NOT INITIAL.
      lv_where = concat_lines_of( table = lt_where_parts sep = ` AND ` ).
    ELSE.
      lv_where = '1 = 1'.
    ENDIF.

    " Execute dynamic select
    TRY.
        SELECT * FROM zanm_anomaly
          WHERE (lv_where)
          INTO TABLE @rt_anomalies
          ORDER BY risk_score DESCENDING, created_at DESCENDING.
      CATCH cx_root.
        " Fallback: select all
        SELECT * FROM zanm_anomaly
          INTO TABLE @rt_anomalies
          ORDER BY risk_score DESCENDING.
    ENDTRY.

    " Apply pagination
    IF is_paging-top > 0.
      IF is_paging-skip > 0 AND is_paging-skip < lines( rt_anomalies ).
        DELETE rt_anomalies FROM 1 TO is_paging-skip.
      ENDIF.
      IF is_paging-top < lines( rt_anomalies ).
        DELETE rt_anomalies FROM ( is_paging-top + 1 ).
      ENDIF.
    ENDIF.
  ENDMETHOD.


  METHOD read_anomaly.
    SELECT SINGLE * FROM zanm_anomaly
      INTO rs_anomaly
      WHERE anomaly_id = iv_anomaly_id.

    IF sy-subrc <> 0.
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_odata_error
          details = |Anomaly not found|.
    ENDIF.
  ENDMETHOD.


  METHOD get_anomalies_for_scan.
    SELECT * FROM zanm_anomaly
      INTO TABLE rt_anomalies
      WHERE scan_id = iv_scan_id
      ORDER BY risk_score DESCENDING.
  ENDMETHOD.


  METHOD delete_anomaly.
    DELETE FROM zanm_anomaly WHERE anomaly_id = iv_anomaly_id.

    IF sy-dbcnt = 0.
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_odata_error
          details = |Anomaly not found for deletion|.
    ENDIF.

    COMMIT WORK.
  ENDMETHOD.

ENDCLASS.
