targetScope = 'resourceGroup'

@minLength(1)
@maxLength(64)
param environmentName string

@description('Primary location for all resources; defaults to resource group location')
param location string = resourceGroup().location

@description('Azure AI Search service name')
param searchServiceName string

@description('Resource group name of the Azure AI Search service')
param searchServiceResourceGroupName string = resourceGroup().name

var resourceToken = toLower(uniqueString(subscription().id, location, environmentName))
var vnetName = 'vnet-${resourceToken}'
var searchPrivateDnsZoneName = 'privatelink.search.windows.net'
var searchPrivateEndpointName = 'pe-search-${resourceToken}'

resource searchService 'Microsoft.Search/searchServices@2021-04-01-preview' existing = {
  name: searchServiceName
  scope: resourceGroup(searchServiceResourceGroupName)
}

resource vnet 'Microsoft.Network/virtualNetworks@2023-09-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: { addressPrefixes: [ '10.0.0.0/16' ] }
    subnets: [
      {
        name: 'functions-subnet'
        properties: {
          addressPrefix: '10.0.3.0/24'
          delegations: [
            {
              name: 'Microsoft.Web.serverFarms'
              properties: { serviceName: 'Microsoft.Web/serverFarms' }
            }
          ]
        }
      }
      {
        name: 'private-endpoint-subnet'
        properties: {
          addressPrefix: '10.0.2.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

resource pdns 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: searchPrivateDnsZoneName
  location: 'global'
}

resource vnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: pdns
  name: 'link-${vnet.name}'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: vnet.id }
  }
}

resource pe 'Microsoft.Network/privateEndpoints@2023-09-01' = {
  name: searchPrivateEndpointName
  location: location
  properties: {
    subnet: { id: resourceId('Microsoft.Network/virtualNetworks/subnets', vnetName, 'private-endpoint-subnet') }
    privateLinkServiceConnections: [
      {
        name: searchPrivateEndpointName
        properties: {
          privateLinkServiceId: searchService.id
          groupIds: [ 'searchService' ]
        }
      }
    ]
  }
}

resource zoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-09-01' = {
  name: 'search'
  parent: pe
  properties: {
    privateDnsZoneConfigs: [
      {
        name: searchPrivateDnsZoneName
        properties: {
          privateDnsZoneId: pdns.id
        }
      }
    ]
  }
  dependsOn: [ vnetLink ]
}

output vnetId string = vnet.id
output privateEndpointId string = pe.id
output privateDnsZoneId string = pdns.id
output note string = 'Private networking for Azure AI Search is provisioned.'
