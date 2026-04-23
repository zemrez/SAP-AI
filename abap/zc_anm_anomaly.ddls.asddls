@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Consumption View - Anomaly'

@UI.headerInfo: {
  typeName: 'Anomaly',
  typeNamePlural: 'Anomalies',
  title: { type: #STANDARD, value: 'AnomalyType' },
  description: { type: #STANDARD, value: 'Description' }
}

@Search.searchable: true

define view entity ZC_ANM_ANOMALY
  as select from ZI_ANM_ANOMALY
{
      @UI.facet: [
        { id: 'General',    purpose: #STANDARD, type: #IDENTIFICATION_REFERENCE, label: 'General',    position: 10 },
        { id: 'Financial',  purpose: #STANDARD, type: #FIELDGROUP_REFERENCE,     label: 'Financial',  position: 20, targetQualifier: 'Financial' },
        { id: 'Resolution', purpose: #STANDARD, type: #FIELDGROUP_REFERENCE,     label: 'Resolution', position: 30, targetQualifier: 'Resolution' }
      ]

      @UI.lineItem: [{ position: 10 }]
      @UI.identification: [{ position: 10 }]
  key AnomalyId,

      @UI.lineItem: [{ position: 15 }]
      ScanId,

      @UI.lineItem: [{ position: 20 }]
      @Search.defaultSearchElement: true
      Detector,

      @UI.lineItem: [{ position: 30 }]
      @Search.defaultSearchElement: true
      AnomalyType,

      @UI.lineItem: [{ position: 40, criticality: 'SeverityCriticality' }]
      RiskScore,

      @UI.lineItem: [{ position: 50, criticality: 'SeverityCriticality' }]
      Severity,

      @UI.fieldGroup: [{ qualifier: 'Financial', position: 10 }]
      @UI.lineItem: [{ position: 60 }]
      DocumentNumber,

      @UI.selectionField: [{ position: 10 }]
      @UI.fieldGroup: [{ qualifier: 'Financial', position: 20 }]
      CompanyCode,

      @UI.fieldGroup: [{ qualifier: 'Financial', position: 30 }]
      FiscalYear,

      @UI.fieldGroup: [{ qualifier: 'Financial', position: 40 }]
      PostingDate,

      @UI.fieldGroup: [{ qualifier: 'Financial', position: 50 }]
      AmountInLocalCurrency,

      @UI.fieldGroup: [{ qualifier: 'Financial', position: 60 }]
      Currency,

      @UI.identification: [{ position: 20 }]
      Description,

      DetailsJson,

      @UI.lineItem: [{ position: 70, criticality: 'StatusCriticality' }]
      @UI.selectionField: [{ position: 20 }]
      Status,

      @UI.fieldGroup: [{ qualifier: 'Resolution', position: 10 }]
      AssignedTo,

      @UI.fieldGroup: [{ qualifier: 'Resolution', position: 20 }]
      Resolution,

      @UI.fieldGroup: [{ qualifier: 'Resolution', position: 30 }]
      ResolvedAt,

      @UI.lineItem: [{ position: 80 }]
      CreatedAt,

      /* Virtual elements for UI criticality (defined in interface view) */
      @UI.hidden: true
      SeverityCriticality,

      @UI.hidden: true
      StatusCriticality,

      /* Associations */
      _ScanRun
}
