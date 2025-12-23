param privateEndpointName string
param privateDnsZoneId string
param zoneGroupName string = 'default'

// Existing Private Endpoint in the same resource group
resource pe 'Microsoft.Network/privateEndpoints@2023-09-01' existing = {
  name: privateEndpointName
}

resource zoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-09-01' = {
  name: zoneGroupName
  parent: pe
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'config'
        properties: {
          privateDnsZoneId: privateDnsZoneId
        }
      }
    ]
  }
}

output id string = zoneGroup.id
