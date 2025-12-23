targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

param appServicePlanName string = ''
param appServicePlanResourceGroupName string = ''
param backendServiceName string = ''
param resourceGroupName string = ''

@description('When false, the template will NOT create a new App Service Plan. Set to true to allow creating one when no existing plan name is provided.')
param allowAppServicePlanCreation bool = false

param searchServiceName string = ''
param searchServiceResourceGroupName string = ''
param searchServiceResourceGroupLocation string = location
param searchServiceSkuName string = ''
param searchIndexName string = 'gptkbindex'
param searchUseSemanticSearch bool = false
param searchSemanticSearchConfig string = 'default'
param searchTopK int = 5
param searchEnableInDomain bool = true
param searchContentColumns string = 'content'
param searchFilenameColumn string = 'filepath'
param searchTitleColumn string = 'title'
param searchUrlColumn string = 'url'

param openAiResourceName string = ''
param openAiResourceGroupName string = ''
param openAIModel string = 'turbo'
param openAIModelName string = 'gpt-35-turbo'
param openAITemperature int = 0
param openAITopP int = 1
param openAIMaxTokens int = 1000
param openAIStopSequence string = ''
param openAISystemMessage string = 'You are an AI assistant that helps people find information.'
param openAIStream bool = true
param embeddingDeploymentName string = 'embedding'

// Azure AI Agents & Bing Grounding Configuration
param azureAIAgentKey string = ''
param bingGroundingConnId string = ''

// Network Configuration
param enablePrivateNetworking bool = false

// Used by prepdocs.py: Form recognizer
param formRecognizerServiceName string = ''
param formRecognizerResourceGroupName string = ''
param formRecognizerResourceGroupLocation string = location
param formRecognizerSkuName string = ''

// Used for the Azure AD application
param authClientId string
@secure()
param authClientSecret string

// Used for Cosmos DB
param cosmosAccountName string = ''

param keyVaultName string = 'aiprojeckeyvaulta6075dab'
// Optional: prefer an existing Log Analytics workspace if provided
param logAnalyticsName string = ''

@description('Id of the user or app to assign application roles')
param principalId string = ''

@description('When false, role assignments will not be created. Set to true to enable RBAC creation.')
param createRoleAssignments bool = false

var abbrs = loadJsonContent('abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, location, environmentName))
var tags = { 'azd-env-name': environmentName }

// Organize resources in a resource group
resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

resource openAiResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(openAiResourceGroupName)) {
  name: !empty(openAiResourceGroupName) ? openAiResourceGroupName : resourceGroup.name
}

// User-assigned managed identity
module userAssignedIdentity 'core/security/managed-identity.bicep' = {
  name: 'user-identity'
  scope: resourceGroup
  params: {
    name: '${abbrs.managedIdentityUserAssignedIdentities}${resourceToken}'
    location: location
    tags: tags
  }
}

resource searchServiceResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(searchServiceResourceGroupName)) {
  name: !empty(searchServiceResourceGroupName) ? searchServiceResourceGroupName : resourceGroup.name
}


// Create an App Service Plan to group applications under the same payment plan and SKU
// If the caller provided an existing App Service Plan name, reference it; otherwise create one
// Reference to an existing App Service Plan in the deployment resource group when a name is provided
resource existingAppServicePlan_inRG 'Microsoft.Web/serverfarms@2022-03-01' existing = if (!empty(appServicePlanName)) {
  scope: resourceGroup
  name: appServicePlanName
}

// Reference to an existing App Service Plan in an explicit resource group when both name and resourceGroup are provided
resource existingAppServicePlan_other 'Microsoft.Web/serverfarms@2022-03-01' existing = if (!empty(appServicePlanName) && !empty(appServicePlanResourceGroupName)) {
  scope: az.resourceGroup(appServicePlanResourceGroupName)
  name: appServicePlanName
}

// Create an App Service Plan only when the caller allows it and no existing plan name is provided
module appServicePlan 'core/host/appserviceplan.bicep' = if (empty(appServicePlanName) && allowAppServicePlanCreation) {
  name: 'appserviceplan'
  scope: resourceGroup
  params: {
    name: '${abbrs.webServerFarms}${resourceToken}'
    location: location
    tags: tags
    sku: {
      name: 'B1'
      capacity: 1
    }
    kind: 'linux'
  }
}

// Provide a unified id variable for the app service plan (existing or newly created)
// Compute app service plan id: use existing resource if name provided, otherwise construct resourceId for the plan this template would create
// Use existing App Service Plan id when a name is provided; otherwise construct resourceId for the plan the module would create
// Decide which existing plan id to use: explicit resource-group-scoped one when provided, otherwise deployment-rg one, otherwise construct resourceId for a plan the module would create
// Compute app service plan id: prefer explicit existing plan in other RG, then existing plan in deployment RG.
// If no existing plan is provided and creation is allowed, reference the module's created id; otherwise leave empty to force caller to provide an existing plan.
var appServicePlanId = !empty(appServicePlanName) && !empty(appServicePlanResourceGroupName) ? existingAppServicePlan_other.id : ( !empty(appServicePlanName) ? existingAppServicePlan_inRG.id : (allowAppServicePlanCreation ? resourceId('Microsoft.Web/serverfarms', '${abbrs.webServerFarms}${resourceToken}') : '') )

// Virtual Network for private networking
module virtualNetwork 'core/network/vnet.bicep' = if (enablePrivateNetworking) {
  name: 'vnet'
  scope: resourceGroup
  params: {
    name: 'vnet-${resourceToken}'
    location: location
    tags: tags
    addressPrefix: '10.0.0.0/16'
    subnets: [
      {
        name: 'app-subnet'
        addressPrefix: '10.0.1.0/24'
        delegations: [
          {
            name: 'Microsoft.Web.serverFarms'
            properties: {
              serviceName: 'Microsoft.Web/serverFarms'
            }
          }
        ]
      }
      {
        name: 'functions-subnet'
        addressPrefix: '10.0.3.0/24'
        delegations: [
          {
            name: 'Microsoft.Web.serverFarms'
            properties: {
              serviceName: 'Microsoft.Web/serverFarms'
            }
          }
        ]
      }
      {
        name: 'private-endpoint-subnet'
        addressPrefix: '10.0.2.0/24'
        privateEndpointNetworkPolicies: 'Disabled'
      }
    ]
  }
}

// The application frontend
var appServiceName = !empty(backendServiceName) ? backendServiceName : '${abbrs.webSitesAppService}backend-${resourceToken}'
var authIssuerUri = '${environment().authentication.loginEndpoint}${tenant().tenantId}/v2.0'
// Private networking names for Search PE/DNS
var searchPrivateDnsZoneName = 'privatelink.search.windows.net'
var searchPrivateEndpointName = 'pe-search-${resourceToken}'

module backend 'core/host/appservice.bicep' = if (empty(backendServiceName)) {
  name: 'web'
  scope: resourceGroup
  params: {
    name: appServiceName
    location: location
    tags: union(tags, { 'azd-service-name': 'backend' })
  appServicePlanId: appServicePlanId
    runtimeName: 'python'
    runtimeVersion: '3.12'
    scmDoBuildDuringDeployment: true
    managedIdentity: true
    userAssignedIdentityId: userAssignedIdentity.outputs.id
    authClientSecret: authClientSecret
    authClientId: authClientId
    authIssuerUri: authIssuerUri
    virtualNetworkSubnetId: ''
    appSettings: {
      // Key Vault
      AZURE_KEYVAULT_NAME: existingKeyVault.name
  AZURE_KEYVAULT_URI: existingKeyVault.properties.vaultUri
      ENABLE_KEY_VAULT: 'true'
  // search
  AZURE_SEARCH_INDEX: searchIndexName
  AZURE_SEARCH_SERVICE: searchService.outputs.name
  // NOTE: Do NOT emit the Search admin key from the template. Store the admin key in Key Vault
  // and grant the user-assigned managed identity access to read the secret. The application
  // should fetch the key at runtime using its managed identity or use the Search REST API
  // with Azure AD credentials where possible.
      AZURE_SEARCH_USE_SEMANTIC_SEARCH: searchUseSemanticSearch
      AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG: searchSemanticSearchConfig
      AZURE_SEARCH_TOP_K: searchTopK
      AZURE_SEARCH_ENABLE_IN_DOMAIN: searchEnableInDomain
      AZURE_SEARCH_CONTENT_COLUMNS: searchContentColumns
      AZURE_SEARCH_FILENAME_COLUMN: searchFilenameColumn
      AZURE_SEARCH_TITLE_COLUMN: searchTitleColumn
      AZURE_SEARCH_URL_COLUMN: searchUrlColumn
      // openai
      AZURE_OPENAI_RESOURCE: existingOpenAi.name
      AZURE_OPENAI_MODEL: openAIModel
      AZURE_OPENAI_MODEL_NAME: openAIModelName
      AZURE_OPENAI_ENDPOINT: existingOpenAi.properties.endpoint
      AZURE_OPENAI_TEMPERATURE: openAITemperature
      AZURE_OPENAI_TOP_P: openAITopP
      AZURE_OPENAI_MAX_TOKENS: openAIMaxTokens
      AZURE_OPENAI_STOP_SEQUENCE: openAIStopSequence
      AZURE_OPENAI_SYSTEM_MESSAGE: openAISystemMessage
      AZURE_OPENAI_STREAM: openAIStream
      // cosmos db
      AZURE_COSMOSDB_ACCOUNT: existingCosmos.name
      AZURE_COSMOSDB_DATABASE: 'db_conversation_history'
      AZURE_COSMOSDB_CONVERSATIONS_CONTAINER: 'conversations'
      // Azure AI Agents & Bing Grounding
      AZURE_AI_AGENT_ENDPOINT: 'https://ai-agents-service-jp.services.ai.azure.com/api/projects/ai-agents-service-jp-AAAL'
      AZURE_AI_AGENT_KEY: azureAIAgentKey
      BING_GROUNDING_CONN_ID: bingGroundingConnId
    }
  }
}

// Reference existing App Service if backendServiceName is provided
resource existingBackend 'Microsoft.Web/sites@2022-03-01' existing = if (!empty(backendServiceName)) {
  name: backendServiceName
  scope: resourceGroup
}

// VNet Integration for App Service (if private networking is enabled and backend is newly created)
module vnetIntegration 'core/host/appservice-vnet-integration.bicep' = if (enablePrivateNetworking && empty(backendServiceName)) {
  name: 'vnet-integration'
  scope: resourceGroup
  params: {
    appServiceName: appServiceName
  subnetId: resourceId('Microsoft.Network/virtualNetworks/subnets', 'vnet-${resourceToken}', 'app-subnet')
  }
  dependsOn: [
    backend
  ]
}

// Azure Functions Search Proxy
module searchProxyFunction 'core/host/functions.bicep' = {
  name: 'search-proxy-function'
  scope: resourceGroup
  params: {
    name: 'func-search-proxy-${resourceToken}'
    location: location
    tags: union(tags, { 'azd-service-name': 'search-proxy' })
    appServicePlanId: appServicePlanId
    runtimeName: 'python'
    runtimeVersion: '3.12'
    managedIdentity: true
    userAssignedIdentityId: userAssignedIdentity.outputs.id
    virtualNetworkSubnetId: ''
  userAssignedIdentityPrincipalId: userAssignedIdentity.outputs.principalId
  createRoleAssignments: createRoleAssignments
  logAnalyticsWorkspaceId: logAnalyticsWorkspaceId
    appSettings: {
  // Search Proxy Configuration
  SEARCH_ENDPOINT: 'https://${searchService.outputs.name}.search.windows.net'
  SEARCH_INDEX: searchIndexName
  // NOTE: Do NOT pass the admin key here. Use Key Vault and managed identity to retrieve the key at runtime.
      // Key Vault Configuration
      AZURE_KEYVAULT_NAME: existingKeyVault.name
      AZURE_KEYVAULT_URI: existingKeyVault.properties.vaultUri
      // Managed Identity
      AZURE_CLIENT_ID: userAssignedIdentity.outputs.clientId
      // Functions Runtime
      FUNCTIONS_WORKER_RUNTIME: 'python'
      WEBSITE_RUN_FROM_PACKAGE: '1'
    }
  }
}

// VNet Integration for Functions (if private networking is enabled)
var fnSubnetId = resourceId('Microsoft.Network/virtualNetworks/subnets', 'vnet-${resourceToken}', 'functions-subnet')

module functionsVnetIntegration 'core/host/appservice-vnet-integration.bicep' = if (enablePrivateNetworking) {
  name: 'functions-vnet-integration'
  scope: resourceGroup
  params: {
    appServiceName: searchProxyFunction.outputs.name
    subnetId: fnSubnetId
  }
}

// Private DNS Zone for Azure AI Search and VNet link (only when private networking is enabled)
module searchPrivateDnsZone 'core/network/private-dns-zone.bicep' = if (enablePrivateNetworking) {
  name: 'pdnsz-search'
  scope: resourceGroup
  params: {
    name: searchPrivateDnsZoneName
    tags: tags
    virtualNetworkId: resourceId('Microsoft.Network/virtualNetworks', 'vnet-${resourceToken}')
  }
}

// Private Endpoint for Azure AI Search (only when private networking is enabled)
module searchPrivateEndpoint 'core/network/private-endpoint.bicep' = if (enablePrivateNetworking) {
  name: searchPrivateEndpointName
  scope: resourceGroup
  params: {
    name: searchPrivateEndpointName
    location: location
    tags: tags
    subnetId: resourceId('Microsoft.Network/virtualNetworks/subnets', 'vnet-${resourceToken}', 'private-endpoint-subnet')
    targetResourceId: searchService.outputs.id
    groupIds: [ 'searchService' ]
  }
}

// Bind Private DNS Zone to the Private Endpoint using a zone group (preferred over manual A records)
module searchPeDnsZoneGroup 'core/network/private-endpoint-dns-zone-group.bicep' = if (enablePrivateNetworking) {
  name: 'search-dns-zone-group'
  scope: resourceGroup
  params: {
    privateEndpointName: searchPrivateEndpointName
  privateDnsZoneId: resourceId('Microsoft.Network/privateDnsZones', searchPrivateDnsZoneName)
    zoneGroupName: 'search'
  }
  dependsOn: [
    searchPrivateDnsZone
    searchPrivateEndpoint
  ]
}

// Log Analytics workspace for diagnostics
// Only create the workspace when the caller didn't provide an existing name
module logAnalytics 'core/monitor/loganalytics.bicep' = if (empty(logAnalyticsName)) {
  name: 'loganalytics'
  scope: resourceGroup
  params: {
    name: 'log-${resourceToken}'
    location: location
    tags: tags
    retentionInDays: 30
  }
}

// Allow using an existing Log Analytics workspace when a name is provided
resource existingLogAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' existing = if (!empty(logAnalyticsName)) {
  scope: resourceGroup
  name: logAnalyticsName
}

// Compute log analytics workspace id: prefer existing when provided, otherwise use the created module's output id
// Use existing Log Analytics workspace id when a name is provided; otherwise construct resourceId for the workspace the module would create
var logAnalyticsWorkspaceId = !empty(logAnalyticsName) ? existingLogAnalytics.id : resourceId('Microsoft.OperationalInsights/workspaces', 'log-${resourceToken}')

// Grant Monitoring Metrics Publisher to the user-assigned identity
module monitorMetricsPublisherRole 'core/security/role.bicep' = if (createRoleAssignments) {
  scope: resourceGroup
  name: 'monitor-metrics-publisher-role'
  params: {
    principalId: userAssignedIdentity.outputs.principalId
    roleDefinitionId: '3913510d-42f4-4e42-8a64-420c390055eb'
    principalType: 'ServicePrincipal'
  }
}


// Azure OpenAI Service (using existing resource)
resource existingOpenAi 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: !empty(openAiResourceName) ? openAiResourceName : 'cog-5b5qpqbzmgmdu'
  scope: openAiResourceGroup
}

module searchService 'core/search/search-services.bicep' = {
  name: 'search-service'
  scope: searchServiceResourceGroup
  params: {
    name: !empty(searchServiceName) ? searchServiceName : 'gptkb-${resourceToken}'
    location: searchServiceResourceGroupLocation
    tags: tags
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    sku: {
      name: !empty(searchServiceSkuName) ? searchServiceSkuName : 'standard'
    }
  semanticSearch: 'free'
  publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
  }
}

// The application database (using existing Cosmos DB)
resource existingCosmos 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' existing = {
  name: !empty(cosmosAccountName) ? cosmosAccountName : 'cosmos-5b5qpqbzmgmdu'
  scope: az.resourceGroup('rg-1')
}

// Cosmos DB roles for user and managed identity
module cosmosRoleUser 'core/security/role.bicep' = if (createRoleAssignments && !empty(principalId)) {
  scope: az.resourceGroup('rg-1')
  name: 'cosmos-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // DocumentDB Account Contributor
    principalType: 'User'
  createRoleAssignments: createRoleAssignments
  }
}

module cosmosRoleBackend 'core/security/role.bicep' = if (createRoleAssignments) {
  scope: az.resourceGroup('rg-1')
  name: 'cosmos-role-backend'
  params: {
    principalId: userAssignedIdentity.outputs.principalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // DocumentDB Account Contributor
    principalType: 'ServicePrincipal'
  createRoleAssignments: createRoleAssignments
  }
}

// Key Vault for secrets management (using existing Key Vault)
resource existingKeyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
  scope: az.resourceGroup('rg-1')
}

// Key Vault access for App Service
module keyVaultRoleBackend 'core/security/role.bicep' = if (createRoleAssignments) {
  scope: az.resourceGroup('rg-1')
  name: 'keyvault-role-backend'
  params: {
    principalId: userAssignedIdentity.outputs.principalId
    roleDefinitionId: '4633458b-17de-408a-b874-0445c86b69e6' // Key Vault Secrets User
    principalType: 'ServicePrincipal'
  createRoleAssignments: createRoleAssignments
  }
}


// USER ROLES
module openAiRoleUser 'core/security/role.bicep' = if (createRoleAssignments && !empty(principalId)) {
  scope: openAiResourceGroup
  name: 'openai-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    principalType: 'User'
  createRoleAssignments: createRoleAssignments
  }
}

module searchRoleUser 'core/security/role.bicep' = if (createRoleAssignments && !empty(principalId)) {
  scope: searchServiceResourceGroup
  name: 'search-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
    principalType: 'User'
  createRoleAssignments: createRoleAssignments
  }
}

module searchIndexDataContribRoleUser 'core/security/role.bicep' = if (createRoleAssignments && !empty(principalId)) {
  scope: searchServiceResourceGroup
  name: 'search-index-data-contrib-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
    principalType: 'User'
  createRoleAssignments: createRoleAssignments
  }
}

module searchServiceContribRoleUser 'core/security/role.bicep' = if (createRoleAssignments && !empty(principalId)) {
  scope: searchServiceResourceGroup
  name: 'search-service-contrib-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
    principalType: 'User'
  createRoleAssignments: createRoleAssignments
  }
}

// SYSTEM IDENTITIES
module openAiRoleBackend 'core/security/role.bicep' = if (createRoleAssignments) {
  scope: openAiResourceGroup
  name: 'openai-role-backend'
  params: {
    principalId: userAssignedIdentity.outputs.principalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    principalType: 'ServicePrincipal'
  createRoleAssignments: createRoleAssignments
  }
}

module searchRoleBackend 'core/security/role.bicep' = if (createRoleAssignments) {
  scope: searchServiceResourceGroup
  name: 'search-role-backend'
  params: {
    principalId: userAssignedIdentity.outputs.principalId
    roleDefinitionId: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
    principalType: 'ServicePrincipal'
  createRoleAssignments: createRoleAssignments
  }
}

// For doc prep
module docPrepResources 'docprep.bicep' = {
  name: 'docprep-resources${resourceToken}'
  params: {
    location: location
    resourceToken: resourceToken
    tags: tags
    principalId: principalId
    resourceGroupName: resourceGroup.name
    formRecognizerServiceName: formRecognizerServiceName
    formRecognizerResourceGroupName: formRecognizerResourceGroupName
    formRecognizerResourceGroupLocation: formRecognizerResourceGroupLocation
    formRecognizerSkuName: !empty(formRecognizerSkuName) ? formRecognizerSkuName : 'S0'
  }
}
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = resourceGroup.name

output BACKEND_URI string = !empty(backendServiceName) ? 'https://${backendServiceName}.azurewebsites.net' : backend.outputs.uri

// Search Proxy Functions
output SEARCH_PROXY_FUNCTION_URI string = searchProxyFunction.outputs.uri
output SEARCH_PROXY_FUNCTION_NAME string = searchProxyFunction.outputs.name

// search
output AZURE_SEARCH_INDEX string = searchIndexName
output AZURE_SEARCH_SERVICE string = searchService.outputs.name
output AZURE_SEARCH_SERVICE_RESOURCE_GROUP string = searchServiceResourceGroup.name
output AZURE_SEARCH_SKU_NAME string = searchService.outputs.skuName
output AZURE_SEARCH_USE_SEMANTIC_SEARCH bool = searchUseSemanticSearch
output AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG string = searchSemanticSearchConfig
output AZURE_SEARCH_TOP_K int = searchTopK
output AZURE_SEARCH_ENABLE_IN_DOMAIN bool = searchEnableInDomain
output AZURE_SEARCH_CONTENT_COLUMNS string = searchContentColumns
output AZURE_SEARCH_FILENAME_COLUMN string = searchFilenameColumn
output AZURE_SEARCH_TITLE_COLUMN string = searchTitleColumn
output AZURE_SEARCH_URL_COLUMN string = searchUrlColumn

// openai
output AZURE_OPENAI_RESOURCE string = existingOpenAi.name
output AZURE_OPENAI_RESOURCE_GROUP string = openAiResourceGroup.name
output AZURE_OPENAI_ENDPOINT string = existingOpenAi.properties.endpoint
output AZURE_OPENAI_MODEL string = openAIModel
output AZURE_OPENAI_MODEL_NAME string = openAIModelName
output AZURE_OPENAI_SKU_NAME string = existingOpenAi.sku.name
output AZURE_OPENAI_EMBEDDING_NAME string = embeddingDeploymentName
output AZURE_OPENAI_TEMPERATURE int = openAITemperature
output AZURE_OPENAI_TOP_P int = openAITopP
output AZURE_OPENAI_MAX_TOKENS int = openAIMaxTokens
output AZURE_OPENAI_STOP_SEQUENCE string = openAIStopSequence
output AZURE_OPENAI_SYSTEM_MESSAGE string = openAISystemMessage
output AZURE_OPENAI_STREAM bool = openAIStream

// Used by prepdocs.py:
output AZURE_FORMRECOGNIZER_SERVICE string = docPrepResources.outputs.AZURE_FORMRECOGNIZER_SERVICE
output AZURE_FORMRECOGNIZER_RESOURCE_GROUP string = docPrepResources.outputs.AZURE_FORMRECOGNIZER_RESOURCE_GROUP
output AZURE_FORMRECOGNIZER_SKU_NAME string = docPrepResources.outputs.AZURE_FORMRECOGNIZER_SKU_NAME

// cosmos
output AZURE_COSMOSDB_ACCOUNT string = existingCosmos.name
output AZURE_COSMOSDB_DATABASE string = 'db_conversation_history'
output AZURE_COSMOSDB_CONVERSATIONS_CONTAINER string = 'conversations'

// Key Vault
output AZURE_KEYVAULT_NAME string = existingKeyVault.name
output AZURE_KEYVAULT_URI string = existingKeyVault.properties.vaultUri

output AUTH_ISSUER_URI string = authIssuerUri

// Required AZD outputs (unique)
output RESOURCE_GROUP_ID string = resourceGroup.id
