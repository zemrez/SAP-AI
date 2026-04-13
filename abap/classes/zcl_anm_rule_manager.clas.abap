"! Detection rule manager for Anomaly Detective
"! CRUD operations on ZANM_DET_RULE table
CLASS zcl_anm_rule_manager DEFINITION
  PUBLIC
  FINAL
  CREATE PUBLIC.

  PUBLIC SECTION.

    "! Return all detection rules
    "! @parameter rt_rules | Table of all rule records
    CLASS-METHODS get_rules
      RETURNING
        VALUE(rt_rules) TYPE STANDARD TABLE OF zanm_det_rule WITH DEFAULT KEY.

    "! Return a single rule by ID
    "! @parameter iv_rule_id | Rule UUID
    "! @parameter rs_rule    | Rule record
    "! @raising zcx_anm_exception | RULE_NOT_FOUND if ID does not exist
    CLASS-METHODS get_rule
      IMPORTING
        iv_rule_id     TYPE sysuuid_x16
      RETURNING
        VALUE(rs_rule) TYPE zanm_det_rule
      RAISING
        zcx_anm_exception.

    "! Update rule configuration and active status
    "! @parameter iv_rule_id    | Rule UUID
    "! @parameter iv_config_json | New JSON configuration
    "! @parameter iv_is_active  | Active flag
    "! @raising zcx_anm_exception | RULE_NOT_FOUND if ID does not exist
    CLASS-METHODS update_rule
      IMPORTING
        iv_rule_id     TYPE sysuuid_x16
        iv_config_json TYPE string OPTIONAL
        iv_is_active   TYPE abap_bool OPTIONAL
      RAISING
        zcx_anm_exception.

    "! Insert default detector configurations for all 6 detector types
    "! Idempotent — skips detectors that already have a rule
    CLASS-METHODS init_default_rules.

  PROTECTED SECTION.
  PRIVATE SECTION.
ENDCLASS.


CLASS zcl_anm_rule_manager IMPLEMENTATION.

  METHOD get_rules.
    SELECT * FROM zanm_det_rule
      INTO TABLE rt_rules
      ORDER BY detector.
  ENDMETHOD.


  METHOD get_rule.
    SELECT SINGLE * FROM zanm_det_rule
      INTO rs_rule
      WHERE rule_id = iv_rule_id.

    IF sy-subrc <> 0.
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_rule_not_found
          details = |Detection rule not found|.
    ENDIF.
  ENDMETHOD.


  METHOD update_rule.
    DATA ls_rule TYPE zanm_det_rule.

    SELECT SINGLE * FROM zanm_det_rule
      INTO ls_rule
      WHERE rule_id = iv_rule_id.

    IF sy-subrc <> 0.
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_rule_not_found
          details = |Detection rule not found for update|.
    ENDIF.

    IF iv_config_json IS NOT INITIAL.
      ls_rule-config_json = iv_config_json.
    ENDIF.

    IF iv_is_active IS SUPPLIED.
      ls_rule-is_active = iv_is_active.
    ENDIF.

    GET TIME STAMP FIELD ls_rule-updated_at.

    UPDATE zanm_det_rule FROM ls_rule.
    COMMIT WORK.
  ENDMETHOD.


  METHOD init_default_rules.
    DATA ls_rule TYPE zanm_det_rule.

    GET TIME STAMP FIELD DATA(lv_timestamp).

    " Check which detectors already have rules
    DATA lt_existing TYPE STANDARD TABLE OF zanm_det_rule-detector.
    SELECT detector FROM zanm_det_rule INTO TABLE lt_existing.

    DEFINE create_rule.
      READ TABLE lt_existing TRANSPORTING NO FIELDS WITH KEY table_line = &1.
      IF sy-subrc <> 0.
        CLEAR ls_rule.
        ls_rule-rule_id     = zcl_anm_uuid=>generate( ).
        ls_rule-detector    = &1.
        ls_rule-is_active   = abap_true.
        ls_rule-config_json = &2.
        ls_rule-created_at  = lv_timestamp.
        ls_rule-updated_at  = lv_timestamp.
        INSERT zanm_det_rule FROM ls_rule.
      ENDIF.
    END-OF-DEFINITION.

    " AMOUNT detector: flag amounts exceeding 3 standard deviations
    create_rule 'AMOUNT' '{"std_dev_threshold":3,"min_amount":1000,"lookback_days":90}'.

    " DUPLICATE detector: flag potential duplicates within 24-hour window
    create_rule 'DUPLICATE' '{"window_hours":24,"match_fields":["BELNR","DMBTR","LIFNR"],"similarity_threshold":0.95}'.

    " TIMING detector: flag postings during off-hours (22:00-05:00)
    create_rule 'TIMING' '{"off_hours_start":22,"off_hours_end":5,"include_weekends":true,"include_holidays":true}'.

    " COMBO detector: flag unusual account/vendor/cost center combinations
    create_rule 'COMBO' '{"min_frequency":3,"lookback_days":365,"confidence_threshold":0.9}'.

    " ROUND detector: flag suspiciously round amounts above threshold
    create_rule 'ROUND' '{"round_threshold":10000,"min_roundness":100,"max_occurrences":5}'.

    " ML detector: Isolation Forest anomaly detection parameters
    create_rule 'ML' '{"contamination":0.05,"n_estimators":100,"features":["DMBTR","HKONT","LIFNR","BUDAT"],"retrain_interval_days":30}'.

    COMMIT WORK.
  ENDMETHOD.

ENDCLASS.
