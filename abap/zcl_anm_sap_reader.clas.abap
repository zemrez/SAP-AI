"! SAP FI data reader for Anomaly Detective
"! Reads standard SAP tables (BKPF/BSEG, BSIK/BSAK, FAGLFLEXT)
"! All methods enforce BUKRS-level authorization
CLASS zcl_anm_sap_reader DEFINITION
  PUBLIC
  FINAL
  CREATE PUBLIC.

  PUBLIC SECTION.

    "! Journal entry header + line item structure
    TYPES:
      BEGIN OF ty_journal_entry,
        bukrs TYPE bukrs,
        belnr TYPE belnr_d,
        gjahr TYPE gjahr,
        blart TYPE blart,
        budat TYPE budat,
        cpudt TYPE cpudt,
        cputm TYPE cputm,
        usnam TYPE usnam,
        buzei TYPE buzei,
        hkont TYPE hkont,
        shkzg TYPE shkzg,
        dmbtr TYPE dmbtr,
        waers TYPE waers,
        lifnr TYPE lifnr,
        kunnr TYPE kunnr,
        kostl TYPE kostl,
        sgtxt TYPE sgtxt,
      END OF ty_journal_entry,
      tt_journal_entries TYPE STANDARD TABLE OF ty_journal_entry WITH DEFAULT KEY.

    "! Vendor invoice structure
    TYPES:
      BEGIN OF ty_vendor_invoice,
        bukrs TYPE bukrs,
        lifnr TYPE lifnr,
        belnr TYPE belnr_d,
        gjahr TYPE gjahr,
        budat TYPE budat,
        bldat TYPE bldat,
        dmbtr TYPE dmbtr,
        waers TYPE waers,
        zlsch TYPE dzlsch,
        zfbdt TYPE dzfbdt,
        zbd1t TYPE dzbd1t,
        xblnr TYPE xblnr,
        sgtxt TYPE sgtxt,
      END OF ty_vendor_invoice,
      tt_vendor_invoices TYPE STANDARD TABLE OF ty_vendor_invoice WITH DEFAULT KEY.

    "! GL balance structure
    TYPES:
      BEGIN OF ty_gl_balance,
        bukrs  TYPE bukrs,
        hkont  TYPE hkont,
        gjahr  TYPE gjahr,
        poper  TYPE poper,
        drcrk  TYPE shkzg,
        hslvt  TYPE dmbtr,
        hsl01  TYPE dmbtr,
        hsl02  TYPE dmbtr,
        hsl03  TYPE dmbtr,
        hsl04  TYPE dmbtr,
        hsl05  TYPE dmbtr,
        hsl06  TYPE dmbtr,
        hsl07  TYPE dmbtr,
        hsl08  TYPE dmbtr,
        hsl09  TYPE dmbtr,
        hsl10  TYPE dmbtr,
        hsl11  TYPE dmbtr,
        hsl12  TYPE dmbtr,
      END OF ty_gl_balance,
      tt_gl_balances TYPE STANDARD TABLE OF ty_gl_balance WITH DEFAULT KEY.

    "! Read journal entries (BKPF + BSEG) for a company code and date range
    "! @parameter iv_bukrs     | Company code
    "! @parameter iv_date_from | Start date
    "! @parameter iv_date_to   | End date
    "! @parameter rt_entries   | Journal entry records
    "! @raising zcx_anm_exception | SAP_READ_ERROR on DB errors
    "! @raising cx_no_authority   | When user lacks BUKRS authorization
    CLASS-METHODS get_journal_entries
      IMPORTING
        iv_bukrs          TYPE bukrs
        iv_date_from      TYPE budat
        iv_date_to        TYPE budat
      RETURNING
        VALUE(rt_entries) TYPE tt_journal_entries
      RAISING
        zcx_anm_exception
        cx_no_authority.

    "! Read vendor invoices (BSIK open + BSAK cleared) for a company code and date range
    "! @parameter iv_bukrs     | Company code
    "! @parameter iv_date_from | Start date
    "! @parameter iv_date_to   | End date
    "! @parameter rt_invoices  | Vendor invoice records
    "! @raising zcx_anm_exception | SAP_READ_ERROR on DB errors
    "! @raising cx_no_authority   | When user lacks BUKRS authorization
    CLASS-METHODS get_vendor_invoices
      IMPORTING
        iv_bukrs           TYPE bukrs
        iv_date_from       TYPE budat
        iv_date_to         TYPE budat
      RETURNING
        VALUE(rt_invoices) TYPE tt_vendor_invoices
      RAISING
        zcx_anm_exception
        cx_no_authority.

    "! Read GL account balances from FAGLFLEXT for a company code and fiscal year
    "! @parameter iv_bukrs    | Company code
    "! @parameter iv_gjahr    | Fiscal year
    "! @parameter rt_balances | GL balance records
    "! @raising zcx_anm_exception | SAP_READ_ERROR on DB errors
    "! @raising cx_no_authority   | When user lacks BUKRS authorization
    CLASS-METHODS get_gl_balances
      IMPORTING
        iv_bukrs           TYPE bukrs
        iv_gjahr           TYPE gjahr
      RETURNING
        VALUE(rt_balances) TYPE tt_gl_balances
      RAISING
        zcx_anm_exception
        cx_no_authority.

  PROTECTED SECTION.
  PRIVATE SECTION.
ENDCLASS.


CLASS zcl_anm_sap_reader IMPLEMENTATION.

  METHOD get_journal_entries.
    " Authorization check
    zcl_anm_auth=>check_authority(
      iv_actvt = zcl_anm_auth=>gc_actvt_display
      iv_bukrs = iv_bukrs ).

    " Join BKPF (header) with BSEG (line items) for the given date range
    SELECT bkpf~bukrs, bkpf~belnr, bkpf~gjahr, bkpf~blart,
           bkpf~budat, bkpf~cpudt, bkpf~cputm, bkpf~usnam,
           bseg~buzei, bseg~hkont, bseg~shkzg, bseg~dmbtr,
           bseg~waers, bseg~lifnr, bseg~kunnr, bseg~kostl,
           bseg~sgtxt
      FROM bkpf
      INNER JOIN bseg ON  bseg~bukrs = bkpf~bukrs
                      AND bseg~belnr = bkpf~belnr
                      AND bseg~gjahr = bkpf~gjahr
      INTO TABLE @rt_entries
      WHERE bkpf~bukrs = @iv_bukrs
        AND bkpf~budat BETWEEN @iv_date_from AND @iv_date_to.

    IF sy-subrc <> 0.
      " No data is not an error — return empty table
      RETURN.
    ENDIF.
  ENDMETHOD.


  METHOD get_vendor_invoices.
    " Authorization check
    zcl_anm_auth=>check_authority(
      iv_actvt = zcl_anm_auth=>gc_actvt_display
      iv_bukrs = iv_bukrs ).

    " Read open vendor items (BSIK)
    DATA lt_open TYPE tt_vendor_invoices.
    SELECT bukrs, lifnr, belnr, gjahr, budat, bldat,
           dmbtr, waers, zlsch, zfbdt, zbd1t, xblnr, sgtxt
      FROM bsik
      INTO TABLE @lt_open
      WHERE bukrs = @iv_bukrs
        AND budat BETWEEN @iv_date_from AND @iv_date_to.

    " Read cleared vendor items (BSAK)
    DATA lt_cleared TYPE tt_vendor_invoices.
    SELECT bukrs, lifnr, belnr, gjahr, budat, bldat,
           dmbtr, waers, zlsch, zfbdt, zbd1t, xblnr, sgtxt
      FROM bsak
      INTO TABLE @lt_cleared
      WHERE bukrs = @iv_bukrs
        AND budat BETWEEN @iv_date_from AND @iv_date_to.

    " Merge results
    rt_invoices = lt_open.
    APPEND LINES OF lt_cleared TO rt_invoices.

    " Sort by posting date descending
    SORT rt_invoices BY budat DESCENDING belnr DESCENDING.
  ENDMETHOD.


  METHOD get_gl_balances.
    " Authorization check
    zcl_anm_auth=>check_authority(
      iv_actvt = zcl_anm_auth=>gc_actvt_display
      iv_bukrs = iv_bukrs ).

    " Read from new GL totals table (FAGLFLEXT)
    SELECT rldnr, rbukrs AS bukrs, racct AS hkont, ryear AS gjahr,
           rpmax AS poper, drcrk,
           hslvt, hsl01, hsl02, hsl03, hsl04, hsl05, hsl06,
           hsl07, hsl08, hsl09, hsl10, hsl11, hsl12
      FROM faglflext
      INTO CORRESPONDING FIELDS OF TABLE @rt_balances
      WHERE rbukrs = @iv_bukrs
        AND ryear  = @iv_gjahr
        AND rldnr  = '0L'.   " Leading ledger only

    IF sy-subrc <> 0.
      RETURN.
    ENDIF.
  ENDMETHOD.

ENDCLASS.
