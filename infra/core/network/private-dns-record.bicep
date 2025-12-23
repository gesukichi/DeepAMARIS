param privateDnsZoneName string
param recordName string
param recordType string = 'A'
param ttl int = 300
param targetIpAddress string

resource privateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' existing = {
  name: privateDnsZoneName
}

resource aRecord 'Microsoft.Network/privateDnsZones/A@2020-06-01' = if (recordType == 'A') {
  parent: privateDnsZone
  name: recordName
  properties: {
    ttl: ttl
    aRecords: [
      {
        ipv4Address: targetIpAddress
      }
    ]
  }
}

output recordId string = recordType == 'A' ? aRecord.id : ''
output recordName string = recordName
