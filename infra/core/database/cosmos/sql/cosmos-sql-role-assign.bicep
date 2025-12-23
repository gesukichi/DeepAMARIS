metadata description = 'Creates a SQL role assignment under an Azure Cosmos DB account.'
param accountName string

param roleDefinitionId string
param principalId string = ''
param createRoleAssignments bool = false


// Create the SQL role assignment only when explicitly allowed at plan-time
resource role 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2022-05-15' = if (createRoleAssignments && !empty(principalId)) {
  parent: cosmos
  name: guid(roleDefinitionId, principalId, cosmos.id)
  properties: {
    principalId: principalId
    roleDefinitionId: roleDefinitionId
    scope: cosmos.id
  }
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2022-08-15' existing = {
  name: accountName
}
