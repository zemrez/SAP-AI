"! Authorization check helper for Anomaly Detective
"! Checks ZANM_AUTH object with ACTVT + BUKRS fields
CLASS zcl_anm_auth DEFINITION
  PUBLIC
  FINAL
  CREATE PUBLIC.

  PUBLIC SECTION.

    "! Activity constants
    CONSTANTS:
      gc_actvt_create  TYPE activ_auth VALUE '01',
      gc_actvt_change  TYPE activ_auth VALUE '02',
      gc_actvt_display TYPE activ_auth VALUE '03',
      gc_actvt_execute TYPE activ_auth VALUE '16'.

    "! Check if user is authorized for an activity on a company code
    "! @parameter iv_actvt  | Activity (01/02/03/16)
    "! @parameter iv_bukrs  | Company code
    "! @raising zcx_anm_exception | Raised when user lacks authorization
    CLASS-METHODS check_authority
      IMPORTING
        iv_actvt TYPE activ_auth
        iv_bukrs TYPE bukrs
      RAISING
        zcx_anm_exception.

    "! Check authorization and return boolean (no exception)
    "! @parameter iv_actvt  | Activity (01/02/03/16)
    "! @parameter iv_bukrs  | Company code
    "! @parameter rv_authorized | ABAP_TRUE if authorized
    CLASS-METHODS is_authorized
      IMPORTING
        iv_actvt            TYPE activ_auth
        iv_bukrs            TYPE bukrs
      RETURNING
        VALUE(rv_authorized) TYPE abap_bool.

  PROTECTED SECTION.
  PRIVATE SECTION.
ENDCLASS.


CLASS zcl_anm_auth IMPLEMENTATION.

  METHOD check_authority.
    AUTHORITY-CHECK OBJECT 'ZANM_AUTH'
      ID 'ACTVT' FIELD iv_actvt
      ID 'BUKRS' FIELD iv_bukrs.

    IF sy-subrc <> 0.
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_scan_failed
          details = |Authorization check failed for activity { iv_actvt } company code { iv_bukrs }|.
    ENDIF.
  ENDMETHOD.

  METHOD is_authorized.
    AUTHORITY-CHECK OBJECT 'ZANM_AUTH'
      ID 'ACTVT' FIELD iv_actvt
      ID 'BUKRS' FIELD iv_bukrs.

    rv_authorized = COND #( WHEN sy-subrc = 0 THEN abap_true
                            ELSE abap_false ).
  ENDMETHOD.

ENDCLASS.
