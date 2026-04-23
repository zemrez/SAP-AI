"! Configuration manager for Anomaly Detective
"! CRUD operations on ZANM_CONFIG table
CLASS zcl_anm_config_manager DEFINITION
  PUBLIC
  FINAL
  CREATE PUBLIC.

  PUBLIC SECTION.

    TYPES: ty_config_tab TYPE STANDARD TABLE OF zanm_config WITH DEFAULT KEY.

    "! Default configuration keys
    CONSTANTS:
      gc_key_sidecar_url     TYPE char50 VALUE 'SAP_SIDECAR_URL',
      gc_key_llm_provider    TYPE char50 VALUE 'LLM_PROVIDER',
      gc_key_scan_days       TYPE char50 VALUE 'SCAN_DEFAULT_DAYS',
      gc_key_max_anomalies   TYPE char50 VALUE 'MAX_ANOMALIES_PER_SCAN',
      gc_key_risk_threshold  TYPE char50 VALUE 'HIGH_RISK_THRESHOLD',
      gc_key_auto_schedule   TYPE char50 VALUE 'AUTO_SCHEDULE_ENABLED',
      gc_key_schedule_cron   TYPE char50 VALUE 'SCHEDULE_CRON_EXPR',
      gc_key_llm_model       TYPE char50 VALUE 'LLM_MODEL_NAME'.

    "! Read a single configuration value by key
    "! @parameter iv_key   | Configuration key
    "! @parameter rv_value | Configuration value
    "! @raising zcx_anm_exception | CONFIG_NOT_FOUND if key does not exist
    CLASS-METHODS get_config
      IMPORTING
        iv_key          TYPE clike
      RETURNING
        VALUE(rv_value) TYPE string
      RAISING
        zcx_anm_exception.

    "! Upsert a configuration value (insert or update)
    "! @parameter iv_key         | Configuration key
    "! @parameter iv_value       | Configuration value
    "! @parameter iv_description | Human-readable description
    CLASS-METHODS set_config
      IMPORTING
        iv_key         TYPE clike
        iv_value       TYPE string
        iv_description TYPE clike OPTIONAL.

    "! Return all configuration entries
    "! @parameter rt_configs | Table of all config records
    CLASS-METHODS get_all_configs
      RETURNING
        VALUE(rt_configs) TYPE ty_config_tab.

    "! Delete a configuration entry
    "! @parameter iv_key | Configuration key to delete
    "! @raising zcx_anm_exception | CONFIG_NOT_FOUND if key does not exist
    CLASS-METHODS delete_config
      IMPORTING
        iv_key TYPE clike
      RAISING
        zcx_anm_exception.

    "! Insert default configuration values (idempotent)
    "! Called during initial setup — skips keys that already exist
    CLASS-METHODS init_defaults.

  PROTECTED SECTION.
  PRIVATE SECTION.
ENDCLASS.


CLASS zcl_anm_config_manager IMPLEMENTATION.

  METHOD get_config.
    DATA ls_config TYPE zanm_config.

    SELECT SINGLE config_value FROM zanm_config
      INTO rv_value
      WHERE config_key = iv_key.

    IF sy-subrc <> 0.
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_config_not_found
          details = |Configuration key '{ iv_key }' not found|.
    ENDIF.
  ENDMETHOD.


  METHOD set_config.
    DATA ls_config TYPE zanm_config.

    GET TIME STAMP FIELD DATA(lv_timestamp).

    ls_config-config_key   = iv_key.
    ls_config-config_value = iv_value.
    ls_config-updated_at   = lv_timestamp.
    ls_config-updated_by   = sy-uname.

    IF iv_description IS NOT INITIAL.
      ls_config-description = iv_description.
    ENDIF.

    " Try update first, insert if not found
    MODIFY zanm_config FROM ls_config.
    COMMIT WORK.
  ENDMETHOD.


  METHOD get_all_configs.
    SELECT * FROM zanm_config
      INTO TABLE rt_configs
      ORDER BY config_key.
  ENDMETHOD.


  METHOD delete_config.
    DELETE FROM zanm_config WHERE config_key = iv_key.

    IF sy-dbcnt = 0.
      RAISE EXCEPTION TYPE zcx_anm_exception
        EXPORTING
          textid  = zcx_anm_exception=>gc_config_not_found
          details = |Configuration key '{ iv_key }' not found for deletion|.
    ENDIF.

    COMMIT WORK.
  ENDMETHOD.


  METHOD init_defaults.
    " Helper macro-like approach: only insert if key does not exist
    DATA lt_defaults TYPE STANDARD TABLE OF zanm_config WITH DEFAULT KEY.
    DATA ls_config TYPE zanm_config.

    GET TIME STAMP FIELD DATA(lv_timestamp).

    DEFINE add_default.
      CLEAR ls_config.
      ls_config-config_key   = &1.
      ls_config-config_value = &2.
      ls_config-description  = &3.
      ls_config-updated_at   = lv_timestamp.
      ls_config-updated_by   = sy-uname.
      APPEND ls_config TO lt_defaults.
    END-OF-DEFINITION.

    add_default gc_key_sidecar_url    'http://localhost:8011' 'Python sidecar base URL'.
    add_default gc_key_llm_provider   'gemini'               'LLM provider (gemini/openai)'.
    add_default gc_key_llm_model      'gemini-pro'           'LLM model name'.
    add_default gc_key_scan_days      '30'                   'Default number of days for scan range'.
    add_default gc_key_max_anomalies  '500'                  'Max anomalies stored per scan'.
    add_default gc_key_risk_threshold '70'                   'Score threshold for HIGH severity'.
    add_default gc_key_auto_schedule  'X'                    'Enable auto-scheduled scans'.
    add_default gc_key_schedule_cron  '0 2 * * 1'            'Cron expression for scheduled scans'.

    " Insert only non-existing keys
    LOOP AT lt_defaults INTO ls_config.
      SELECT SINGLE config_key FROM zanm_config
        INTO @DATA(lv_exists)
        WHERE config_key = @ls_config-config_key.
      IF sy-subrc <> 0.
        INSERT zanm_config FROM ls_config.
      ENDIF.
    ENDLOOP.

    COMMIT WORK.
  ENDMETHOD.

ENDCLASS.
