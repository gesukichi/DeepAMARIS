@description('Creates an Azure Key Vault for secure secret management')
param name string
param location string = resourceGroup().location
param tags object = {}

@description('Principal ID for access policy')
param principalId string

@description('Enable soft delete (recommended for production)')
param enableSoftDelete bool = true

@description('Retention days for soft delete')
param softDeleteRetentionInDays int = 90

@description('Enable purge protection (recommended for production)')
param enablePurgeProtection bool = true

@description('Enable RBAC authorization')
param enableRbacAuthorization bool = true
@description('Global flag to allow creation of role assignments')
param createRoleAssignments bool = false

@description('Enable Key Vault for disk encryption')
param enabledForDiskEncryption bool = false

@description('Enable Key Vault for deployment')
param enabledForDeployment bool = false

@description('Enable Key Vault for template deployment')
param enabledForTemplateDeployment bool = true

@description('Private endpoint subnet ID (optional)')
param privateEndpointSubnetId string = ''

@description('Private DNS zone IDs for private endpoint')
param privateDnsZoneIds array = []

@description('Disable public network access')
param publicNetworkAccess string = 'Enabled'

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableSoftDelete: enableSoftDelete
    softDeleteRetentionInDays: softDeleteRetentionInDays
    enablePurgeProtection: enablePurgeProtection ? enablePurgeProtection : null
    enableRbacAuthorization: enableRbacAuthorization
    enabledForDiskEncryption: enabledForDiskEncryption
    enabledForDeployment: enabledForDeployment
    enabledForTemplateDeployment: enabledForTemplateDeployment
    publicNetworkAccess: publicNetworkAccess
    networkAcls: {
      defaultAction: publicNetworkAccess == 'Disabled' ? 'Deny' : 'Allow'
      bypass: 'AzureServices'
    }
    accessPolicies: enableRbacAuthorization ? [] : [
      {
        tenantId: subscription().tenantId
        objectId: principalId
        permissions: {
          secrets: [
            'get'
            'list'
            'set'
            'delete'
            'recover'
            'backup'
            'restore'
          ]
        }
      }
    ]
  }
}

// Private endpoint for Key Vault (optional)
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-09-01' = if (!empty(privateEndpointSubnetId)) {
  name: '${name}-pe'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: '${name}-pl'
        properties: {
          privateLinkServiceId: keyVault.id
          groupIds: [
            'vault'
          ]
        }
      }
    ]
  }
}

// Private DNS zone group for private endpoint
resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-09-01' = if (!empty(privateEndpointSubnetId) && !empty(privateDnsZoneIds)) {
  name: 'default'
  parent: privateEndpoint
  properties: {
    privateDnsZoneConfigs: [for zoneId in privateDnsZoneIds: {
      name: split(zoneId, '/')[8]
      properties: {
        privateDnsZoneId: zoneId
      }
    }]
  }
}

// RBAC role assignments (when RBAC is enabled)
resource keyVaultSecretsOfficerRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableRbacAuthorization && createRoleAssignments) {
  name: guid(keyVault.id, principalId, 'Key Vault Secrets Officer')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7') // Key Vault Secrets Officer
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

@description('The resource ID of the Key Vault')
output keyVaultId string = keyVault.id

@description('The name of the Key Vault')
output keyVaultName string = keyVault.name

@description('The URI of the Key Vault')
output keyVaultUri string = keyVault.properties.vaultUri

@description('The private endpoint ID (if created)')
output privateEndpointId string = !empty(privateEndpointSubnetId) ? privateEndpoint.id : ''
