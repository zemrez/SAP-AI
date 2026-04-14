"! Background job scheduler for Anomaly Detective
"! Manages SM36 jobs for scheduled anomaly scans
CLASS zcl_anm_job_scheduler DEFINITION
  PUBLIC
  FINAL
  CREATE PUBLIC.

  PUBLIC SECTION.

    "! Schedule a background scan job via SM36
    "! @parameter iv_bukrs      | Company code
    "! @parameter iv_date_from  | Start date (optional — defaults to today minus SCAN_DEFAULT_DAYS)
    "! @parameter iv_date_to    | End date (optional — defaults to today)
    "! @parameter iv_scan_type  | FULL or INCREMENTAL
    "! @parameter iv_start_time | Scheduled start timestamp (optional — immediate if omitted)
    "! @parameter rv_jobcount   | SAP job count identifier
    "! @raising zcx_anm_exception | SCAN_FAILED on scheduling errors
    CLASS-METHODS schedule_scan
      IMPORTING
        iv_bukrs           TYPE bukrs
        iv_date_from       TYPE budat OPTIONAL
        iv_date_to         TYPE budat OPTIONAL
        iv_scan_type       TYPE char12 DEFAULT 'FULL'
        iv_start_time      TYPE timestamp OPTIONAL
      RETURNING
        VALUE(rv_jobcount) TYPE btcjobcnt
      RAISING
        zcx_anm_exception.

    "! Cancel a scheduled or running job
    "! @parameter iv_jobname  | Job name
    "! @parameter iv_jobcount | Job count
    "! @raising zcx_anm_exception | SCAN_FAILED on cancellation errors
    CLASS-METHODS cancel_job
      IMPORTING
        iv_jobname  TYPE btcjob
        iv_jobcount TYPE btcjobcnt
      RAISING
        zcx_anm_exception.

    "! Check the status of a scheduled job
    "! @parameter iv_jobname  | Job name
    "! @parameter iv_jobcount | Job count
    "! @parameter rv_status   | Job status character (S=scheduled, R=released, F=finished, A=aborted)
    CLASS-METHODS get_job_status
      IMPORTING
        iv_jobname        TYPE btcjob
        iv_jobcount       TYPE btcjobcnt
      RETURNING
        VALUE(rv_status)  TYPE btcstatus.

  PROTECTED SECTION.
  PRIVATE SECTION.

    CONSTANTS gc_job_prefix TYPE btcjob VALUE 'ZANM_SCAN_'.

ENDCLASS.


CLASS zcl_anm_job_scheduler IMPLEMENTATION.

  METHOD schedule_scan.
    DATA lv_jobname  TYPE btcjob.
    DATA lv_jobcount TYPE btcjobcnt.
    DATA lv_start_date TYPE sy-datum.
    DATA lv_start_time TYPE sy-uzeit.

    " Build job name with company code for identification
    lv_jobname = gc_job_prefix && iv_bukrs.

    " Step 1: Open job definition
    CALL FUNCTION 'JOB_OPEN'
      EXPORTING
        jobname          = lv_jobname
      IMPORTING
        jobcount         = lv_jobcount
      EXCEPTIONS
        cant_create_job  = 1
        invalid_job_data = 2
        jobname_missing  = 3
        OTHERS           = 4.

    IF sy-subrc <> 0.
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_scan_failed
          details = |Failed to open background job: { lv_jobname }|.
    ENDIF.

    " Step 2: Submit the report as a job step
    DATA lv_variant TYPE raldb_vari VALUE 'DEFAULT'.

    SUBMIT zanm_scheduled_scan
      WITH p_bukrs  = iv_bukrs
      WITH p_dfrom  = iv_date_from
      WITH p_dto    = iv_date_to
      WITH p_stype  = iv_scan_type
      VIA JOB lv_jobname NUMBER lv_jobcount
      AND RETURN.

    " Step 3: Schedule (release) the job
    IF iv_start_time IS NOT INITIAL.
      " Convert timestamp to date and time
      CONVERT TIME STAMP iv_start_time TIME ZONE sy-zonlo
        INTO DATE lv_start_date TIME lv_start_time.
    ELSE.
      " Immediate execution
      lv_start_date = sy-datum.
      lv_start_time = sy-uzeit.
    ENDIF.

    CALL FUNCTION 'JOB_CLOSE'
      EXPORTING
        jobcount             = lv_jobcount
        jobname              = lv_jobname
        sdlstrtdt            = lv_start_date
        sdlstrttm            = lv_start_time
      EXCEPTIONS
        cant_start_immediate = 1
        invalid_startdate    = 2
        jobname_missing      = 3
        job_close_failed     = 4
        job_nosteps          = 5
        job_notex            = 6
        lock_failed          = 7
        invalid_target       = 8
        OTHERS               = 9.

    IF sy-subrc <> 0.
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_scan_failed
          details = |Failed to schedule background job: { lv_jobname }|.
    ENDIF.

    rv_jobcount = lv_jobcount.
  ENDMETHOD.


  METHOD cancel_job.
    CALL FUNCTION 'BP_JOB_DELETE'
      EXPORTING
        jobcount = iv_jobcount
        jobname  = iv_jobname
      EXCEPTIONS
        cant_delete_job       = 1
        cant_enq_job          = 2
        cant_read_job         = 3
        invalid_input         = 4
        job_does_not_exist    = 5
        OTHERS                = 6.

    IF sy-subrc <> 0.
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_scan_failed
          details = |Failed to cancel job { iv_jobname } / { iv_jobcount }|.
    ENDIF.
  ENDMETHOD.


  METHOD get_job_status.
    DATA lt_joblist TYPE STANDARD TABLE OF tbtcjob.

    CALL FUNCTION 'BP_JOB_READ'
      EXPORTING
        job_read_jobcount = iv_jobcount
        job_read_jobname  = iv_jobname
        job_read_opcode   = '20'  " Read single job
      TABLES
        job_read_joblist  = lt_joblist
      EXCEPTIONS
        invalid_opcode    = 1
        job_doesnt_exist  = 2
        job_doesnt_have_steps = 3
        OTHERS            = 4.

    IF sy-subrc = 0 AND lt_joblist IS NOT INITIAL.
      READ TABLE lt_joblist INDEX 1 INTO DATA(ls_job).
      rv_status = ls_job-status.
    ELSE.
      rv_status = 'U'. " Unknown
    ENDIF.
  ENDMETHOD.

ENDCLASS.
