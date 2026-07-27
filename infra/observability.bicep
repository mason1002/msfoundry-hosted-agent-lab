@description('Azure region for the observability resources.')
param location string = resourceGroup().location

@description('Short workload name used in resource names.')
param workloadName string = 'xagent'

@description('Deployment-specific suffix. Defaults to a stable value derived from the resource group ID.')
param resourceSuffix string = take(uniqueString(resourceGroup().id), 6)

@description('Log Analytics workspace name.')
param logAnalyticsName string = 'law-${workloadName}-${resourceSuffix}'

@description('Application Insights component name.')
param applicationInsightsName string = 'appi-${workloadName}-${resourceSuffix}'

@minValue(30)
@maxValue(730)
@description('Interactive Log Analytics retention in days.')
param retentionInDays int = 30

var tags = {
  workload: workloadName
  environment: 'lab'
  managedBy: 'bicep'
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2025-07-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
    retentionInDays: retentionInDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    DisableIpMasking: false
    DisableLocalAuth: true
    Flow_Type: 'Bluefield'
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
    Request_Source: 'rest'
    RetentionInDays: retentionInDays
    SamplingPercentage: 100
    WorkspaceResourceId: logAnalytics.id
  }
}

output applicationInsightsId string = applicationInsights.id
output applicationInsightsName string = applicationInsights.name
output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString
output logAnalyticsId string = logAnalytics.id
output logAnalyticsCustomerId string = logAnalytics.properties.customerId