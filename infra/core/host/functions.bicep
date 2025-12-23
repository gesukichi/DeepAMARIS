metadata description = 'Creates an Azure Functions app.'

@description('The name of the function app.')
param name string

@description('The location for the function app.')
param location string = resourceGroup().location

@description('The tags to apply to the function app.')
param tags object = {}

@description('The resource ID of the app service plan.')
param appServicePlanId string

@description('The runtime stack for the function app.')
param runtimeName string = 'python'

@description('The runtime version for the function app.')
param runtimeVersion string = '3.12'

@description('Whether to enable managed identity.')
param managedIdentity bool = true

@description('The resource ID of the user-assigned managed identity.')
param userAssignedIdentityId string = ''

@description('The subnet ID for VNet integration.')
param virtualNetworkSubnetId string = ''

@description('Application settings for the function app.')
param appSettings object = {}

// Principal ID of the user-assigned managed identity attached to this function app (for role assignments)
param userAssignedIdentityPrincipalId string = ''

@description('Global flag to allow creation of role assignments')
param createRoleAssignments bool = false

// Optional Log Analytics Workspace ID to which diagnostic settings will send logs/metrics
param logAnalyticsWorkspaceId string = ''

// Optional storage-related settings. When empty, they won't be set to avoid invalid values during deployment.
@description('Connection string for AzureWebJobsStorage. Leave empty to skip setting at deploy time (use Key Vault or app config later).')
param azureWebJobsStorage string = ''

@description('Connection string for WEBSITE_CONTENTAZUREFILECONNECTIONSTRING. Leave empty to skip.')
param contentAzureFileConnectionString string = ''

@description('Name for WEBSITE_CONTENTSHARE (e.g., <app>-content). Leave empty to skip.')
param contentShareName string = ''

resource functionApp 'Microsoft.Web/sites@2022-03-01' = {
  name: name
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: managedIdentity ? (empty(userAssignedIdentityId) ? 'SystemAssigned' : 'SystemAssigned, UserAssigned') : 'None'
    userAssignedIdentities: managedIdentity && !empty(userAssignedIdentityId) ? {
      '${userAssignedIdentityId}': {}
    } : null
  }
  properties: {
    serverFarmId: appServicePlanId
    reserved: true
    httpsOnly: true
    virtualNetworkSubnetId: !empty(virtualNetworkSubnetId) ? virtualNetworkSubnetId : null
    siteConfig: {
      linuxFxVersion: '${toUpper(runtimeName)}|${runtimeVersion}'
      alwaysOn: false
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: [for setting in items(appSettings) : {
        name: setting.key
        value: setting.value
      }]
    }
  }
}

// App Settings that require storage account values
resource functionAppSettings 'Microsoft.Web/sites/config@2022-03-01' = {
  name: 'appsettings'
  parent: functionApp
  properties: union(
    appSettings,
    // Only include storage-related keys when values are provided to avoid invalid empty values.
    empty(azureWebJobsStorage) ? {} : { AzureWebJobsStorage: azureWebJobsStorage },
    empty(contentAzureFileConnectionString) ? {} : { WEBSITE_CONTENTAZUREFILECONNECTIONSTRING: contentAzureFileConnectionString },
    empty(contentShareName) ? {} : { WEBSITE_CONTENTSHARE: contentShareName },
    {
      FUNCTIONS_EXTENSION_VERSION: '~4'
      FUNCTIONS_WORKER_RUNTIME: runtimeName
      WEBSITE_RUN_FROM_PACKAGE: '1'
      SCM_DO_BUILD_DURING_DEPLOYMENT: 'false'
    }
  )
}

// Storage account for Functions
resource storageAccount 'Microsoft.Storage/storageAccounts@2022-05-01' = {
  name: 'st${uniqueString(resourceGroup().id, name)}'
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

// Diagnostic settings for Function App (send logs/metrics to Log Analytics when provided)
resource functionAppDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(logAnalyticsWorkspaceId)) {
  name: 'funcapp-diag'
  scope: functionApp
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'FunctionAppLogs'
        enabled: true
      }
      {
        category: 'AppServiceConsoleLogs'
        enabled: true
      }
      {
        category: 'AppServiceHTTPLogs'
        enabled: true
      }
      {
        category: 'AppServicePlatformLogs'
        enabled: true
      }
      {
        category: 'AppServiceAuditLogs'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

// Storage role assignments for the user-assigned managed identity
// Storage Blob Data Owner
resource storageRoleBlobOwner 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (createRoleAssignments && !empty(userAssignedIdentityPrincipalId)) {
  name: guid(storageAccount.id, userAssignedIdentityPrincipalId, 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b')
  scope: storageAccount
  properties: {
    principalId: userAssignedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b')
  }
}

// Storage Blob Data Contributor
resource storageRoleBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (createRoleAssignments && !empty(userAssignedIdentityPrincipalId)) {
  name: guid(storageAccount.id, userAssignedIdentityPrincipalId, 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  scope: storageAccount
  properties: {
    principalId: userAssignedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  }
}

// Storage Queue Data Contributor
resource storageRoleQueueContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (createRoleAssignments && !empty(userAssignedIdentityPrincipalId)) {
  name: guid(storageAccount.id, userAssignedIdentityPrincipalId, '974c5e8b-45b9-4653-ba55-5f855dd0fb88')
  scope: storageAccount
  properties: {
    principalId: userAssignedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '974c5e8b-45b9-4653-ba55-5f855dd0fb88')
  }
}

// Storage Table Data Contributor
resource storageRoleTableContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (createRoleAssignments && !empty(userAssignedIdentityPrincipalId)) {
  name: guid(storageAccount.id, userAssignedIdentityPrincipalId, '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3')
  scope: storageAccount
  properties: {
    principalId: userAssignedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3')
  }
}

output id string = functionApp.id
output name string = functionApp.name
output identityPrincipalId string = managedIdentity ? functionApp.identity.principalId : ''
output uri string = 'https://${functionApp.properties.defaultHostName}'
