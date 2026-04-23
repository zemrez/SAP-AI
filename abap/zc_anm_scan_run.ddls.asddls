@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Consumption View - Scan Run'

@Metadata.allowExtensions: true

@UI.headerInfo: {
  typeName: 'Scan Run',
  typeNamePlural: 'Scan Runs',
  title: { type: #STANDARD, value: 'ScanId' },
  description: { type: #STANDARD, value: 'ScanType' }
}

@Search.searchable: true

define view entity ZC_ANM_SCAN_RUN
  as projection on ZI_ANM_SCAN_RUN
{
      @UI.facet: [
        { id: 'General', purpose: #STANDARD, type: #IDENTIFICATION_REFERENCE, label: 'General', position: 10 },
        { id: 'Results', purpose: #STANDARD, type: #FIELDGROUP_REFERENCE,     label: 'Results', position: 20, targetQualifier: 'Results' }
      ]

      @UI.lineItem: [{ position: 10 }]
      @UI.identification: [{ position: 10 }]
  key ScanId,

      @UI.lineItem: [{ position: 20 }]
      @UI.selectionField: [{ position: 10 }]
      CompanyCode,

      @UI.lineItem: [{ position: 30 }]
      @Search.defaultSearchElement: true
      ScanType,

      @UI.lineItem: [{ position: 40, criticality: 'StatusCriticality' }]
      @UI.selectionField: [{ position: 20 }]
      Status,

      @UI.identification: [{ position: 20 }]
      DateFrom,

      @UI.identification: [{ position: 30 }]
      DateTo,

      @UI.fieldGroup: [{ qualifier: 'Results', position: 10 }]
      @UI.lineItem: [{ position: 50 }]
      RecordsScanned,

      @UI.fieldGroup: [{ qualifier: 'Results', position: 20 }]
      @UI.lineItem: [{ position: 60 }]
      AnomalyCount,

      @UI.fieldGroup: [{ qualifier: 'Results', position: 30 }]
      ErrorMessage,

      @UI.lineItem: [{ position: 70 }]
      StartedAt,

      FinishedAt,

      @UI.lineItem: [{ position: 80 }]
      CreatedBy,

      CreatedAt,

      /* Virtual element for status criticality (defined in interface view) */
      @UI.hidden: true
      StatusCriticality
}
