"! UUID generator utility for Anomaly Detective
"! Wraps SAP standard UUID generation for SYSUUID_X16 keys
CLASS zcl_anm_uuid DEFINITION
  PUBLIC
  FINAL
  CREATE PUBLIC.

  PUBLIC SECTION.

    "! Generate a new UUID in RAW16 format
    "! @parameter rv_uuid | Generated UUID (SYSUUID_X16)
    CLASS-METHODS generate
      RETURNING
        VALUE(rv_uuid) TYPE sysuuid_x16.

    "! Generate a new UUID as a formatted string (32 hex chars)
    "! @parameter rv_uuid_str | Generated UUID as string
    CLASS-METHODS generate_as_string
      RETURNING
        VALUE(rv_uuid_str) TYPE string.

  PROTECTED SECTION.
  PRIVATE SECTION.
ENDCLASS.


CLASS zcl_anm_uuid IMPLEMENTATION.

  METHOD generate.
    TRY.
        rv_uuid = cl_system_uuid=>create_uuid_x16_static( ).
      CATCH cx_uuid_error.
        " Fallback: should never happen in production
        ASSERT 1 = 0.
    ENDTRY.
  ENDMETHOD.

  METHOD generate_as_string.
    DATA(lv_uuid_x16) = generate( ).

    " Convert RAW16 to hex string
    rv_uuid_str = lv_uuid_x16.
    CONDENSE rv_uuid_str NO-GAPS.
  ENDMETHOD.

ENDCLASS.
