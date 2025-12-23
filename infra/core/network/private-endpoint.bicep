param name string
param location string = resourceGroup().location
param tags object = {}
param subnetId string
param targetResourceId string
param groupIds array
param customNetworkInterfaceName string = ''

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-09-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: name
        properties: {
          privateLinkServiceId: targetResourceId
          groupIds: groupIds
        }
      }
    ]
    customNetworkInterfaceName: !empty(customNetworkInterfaceName) ? customNetworkInterfaceName : null
  }
}

output id string = privateEndpoint.id
output name string = privateEndpoint.name
output networkInterfaceIds array = privateEndpoint.properties.networkInterfaces
