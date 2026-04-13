"! Custom exception class for Anomaly Detective
"! Provides typed error handling with specific text IDs per error scenario
CLASS zcx_anm_exception DEFINITION
  PUBLIC
  INHERITING FROM cx_static_check
  FINAL
  CREATE PUBLIC.

  PUBLIC SECTION.

    INTERFACES if_t100_message.

    "! Additional error details (free text)
    DATA mv_details TYPE string READ-ONLY.

    "! Text ID: Scan execution failed
    CONSTANTS:
      BEGIN OF gc_scan_failed,
        msgid TYPE symsgid VALUE 'ZANM_MSG',
        msgno TYPE symsgno VALUE '001',
        attr1 TYPE scx_attrname VALUE 'MV_DETAILS',
        attr2 TYPE scx_attrname VALUE '',
        attr3 TYPE scx_attrname VALUE '',
        attr4 TYPE scx_attrname VALUE '',
      END OF gc_scan_failed.

    "! Text ID: No data found for selection
    CONSTANTS:
      BEGIN OF gc_no_data,
        msgid TYPE symsgid VALUE 'ZANM_MSG',
        msgno TYPE symsgno VALUE '002',
        attr1 TYPE scx_attrname VALUE 'MV_DETAILS',
        attr2 TYPE scx_attrname VALUE '',
        attr3 TYPE scx_attrname VALUE '',
        attr4 TYPE scx_attrname VALUE '',
      END OF gc_no_data.

    "! Text ID: SAP data read error
    CONSTANTS:
      BEGIN OF gc_sap_read_error,
        msgid TYPE symsgid VALUE 'ZANM_MSG',
        msgno TYPE symsgno VALUE '003',
        attr1 TYPE scx_attrname VALUE 'MV_DETAILS',
        attr2 TYPE scx_attrname VALUE '',
        attr3 TYPE scx_attrname VALUE '',
        attr4 TYPE scx_attrname VALUE '',
      END OF gc_sap_read_error.

    "! Text ID: OData processing error
    CONSTANTS:
      BEGIN OF gc_odata_error,
        msgid TYPE symsgid VALUE 'ZANM_MSG',
        msgno TYPE symsgno VALUE '004',
        attr1 TYPE scx_attrname VALUE 'MV_DETAILS',
        attr2 TYPE scx_attrname VALUE '',
        attr3 TYPE scx_attrname VALUE '',
        attr4 TYPE scx_attrname VALUE '',
      END OF gc_odata_error.

    "! Text ID: Configuration key not found
    CONSTANTS:
      BEGIN OF gc_config_not_found,
        msgid TYPE symsgid VALUE 'ZANM_MSG',
        msgno TYPE symsgno VALUE '005',
        attr1 TYPE scx_attrname VALUE 'MV_DETAILS',
        attr2 TYPE scx_attrname VALUE '',
        attr3 TYPE scx_attrname VALUE '',
        attr4 TYPE scx_attrname VALUE '',
      END OF gc_config_not_found.

    "! Text ID: Detection rule not found
    CONSTANTS:
      BEGIN OF gc_rule_not_found,
        msgid TYPE symsgid VALUE 'ZANM_MSG',
        msgno TYPE symsgno VALUE '006',
        attr1 TYPE scx_attrname VALUE 'MV_DETAILS',
        attr2 TYPE scx_attrname VALUE '',
        attr3 TYPE scx_attrname VALUE '',
        attr4 TYPE scx_attrname VALUE '',
      END OF gc_rule_not_found.

    "! Constructor
    "! @parameter textid   | T100 text ID
    "! @parameter previous | Previous exception
    "! @parameter details  | Additional error details
    METHODS constructor
      IMPORTING
        textid   LIKE if_t100_message=>t100key OPTIONAL
        previous LIKE previous OPTIONAL
        details  TYPE string OPTIONAL.

  PROTECTED SECTION.
  PRIVATE SECTION.
ENDCLASS.


CLASS zcx_anm_exception IMPLEMENTATION.

  METHOD constructor.
    super->constructor( previous = previous ).

    mv_details = details.

    " Set default text ID if none provided
    CLEAR me->textid.
    IF textid IS NOT INITIAL.
      if_t100_message~t100key = textid.
    ELSE.
      if_t100_message~t100key = gc_scan_failed.
    ENDIF.
  ENDMETHOD.

ENDCLASS.
