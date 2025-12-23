param name string
param location string = resourceGroup().location
param tags object = {}
param addressPrefix string = '10.0.0.0/16'
param subnets array = []

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2023-09-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        addressPrefix
      ]
    }
    subnets: [for subnet in subnets: {
      name: subnet.name
      properties: {
        addressPrefix: subnet.addressPrefix
        serviceEndpoints: subnet.?serviceEndpoints ?? []
        delegations: subnet.?delegations ?? []
        networkSecurityGroup: subnet.?networkSecurityGroupId != null ? {
          id: subnet.networkSecurityGroupId
        } : null
        routeTable: subnet.?routeTableId != null ? {
          id: subnet.routeTableId
        } : null
        privateEndpointNetworkPolicies: subnet.?privateEndpointNetworkPolicies ?? 'Disabled'
        privateLinkServiceNetworkPolicies: subnet.?privateLinkServiceNetworkPolicies ?? 'Enabled'
      }
    }]
  }
}

output id string = virtualNetwork.id
output name string = virtualNetwork.name
output subnets array = [for i in range(0, length(subnets)): {
  id: virtualNetwork.properties.subnets[i].id
  name: virtualNetwork.properties.subnets[i].name
  addressPrefix: virtualNetwork.properties.subnets[i].properties.addressPrefix
}]
