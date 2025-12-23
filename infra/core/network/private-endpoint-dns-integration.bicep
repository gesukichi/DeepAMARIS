param privateEndpointName string
param privateDnsZoneName string
param location string = resourceGroup().location
param tags object = {}

// Get private endpoint information
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-09-01' existing = {
  name: privateEndpointName
}

// Get network interface details
resource networkInterface 'Microsoft.Network/networkInterfaces@2023-09-01' existing = {
  name: split(privateEndpoint.properties.networkInterfaces[0].id, '/')[8]
}

// Create DNS A record for the private endpoint
module dnsRecord 'private-dns-record.bicep' = {
  name: 'dns-record-${privateEndpointName}'
  params: {
    privateDnsZoneName: privateDnsZoneName
    recordName: split(privateDnsZoneName, '.')[0] == 'privatelink' ? '*' : '@'
    targetIpAddress: networkInterface.properties.ipConfigurations[0].properties.privateIPAddress
  }
}

output privateIpAddress string = networkInterface.properties.ipConfigurations[0].properties.privateIPAddress
output networkInterfaceId string = networkInterface.id
output dnsRecordId string = dnsRecord.outputs.recordId
