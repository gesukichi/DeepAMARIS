param appServiceName string
param subnetId string

resource appService 'Microsoft.Web/sites@2022-03-01' existing = {
  name: appServiceName
}

resource vnetIntegration 'Microsoft.Web/sites/networkConfig@2022-03-01' = {
  name: 'virtualNetwork'
  parent: appService
  properties: {
    subnetResourceId: subnetId
  }
}

output result string = 'VNet integration configured'
