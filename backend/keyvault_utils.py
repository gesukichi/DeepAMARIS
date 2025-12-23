"""
Azure Key Vault integration utilities for secure secret management.
This module provides functionality to retrieve secrets from Azure Key Vault
and integrate them with the application's settings.
"""

import os
import logging
from typing import Dict, Optional, Any
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from pydantic import BaseModel, Field


class KeyVaultConfig(BaseModel):
    """Configuration for Azure Key Vault integration."""
    
    vault_url: str = Field(..., description="Azure Key Vault URL")
    use_managed_identity: bool = Field(default=True, description="Use Managed Identity for authentication")
    client_id: Optional[str] = Field(default=None, description="Client ID for user-assigned managed identity")
    
    @property
    def vault_name(self) -> str:
        """Extract vault name from URL."""
        return self.vault_url.split('//')[1].split('.')[0]


class KeyVaultSecretManager:
    """Manager for retrieving secrets from Azure Key Vault."""
    
    def __init__(self, config: KeyVaultConfig):
        self.config = config
        self._client: Optional[SecretClient] = None
        self._cache: Dict[str, str] = {}
        
    @property
    def client(self) -> SecretClient:
        """Lazy initialization of Key Vault client."""
        if self._client is None:
            try:
                if self.config.use_managed_identity:
                    if self.config.client_id:
                        credential = ManagedIdentityCredential(client_id=self.config.client_id)
                    else:
                        credential = ManagedIdentityCredential()
                else:
                    # ローカル環境用：Managed Identityを除外してAzure CLI認証を使用
                    credential = DefaultAzureCredential(exclude_managed_identity_credential=True)
                
                self._client = SecretClient(
                    vault_url=self.config.vault_url,
                    credential=credential
                )
                
                # Test connection
                list(self._client.list_properties_of_secrets(max_page_size=1))
                logging.info(f"Successfully connected to Key Vault: {self.config.vault_name}")
                
            except Exception as e:
                logging.error(f"Failed to connect to Key Vault: {str(e)}")
                raise
                
        return self._client
    
    def get_secret(self, secret_name: str, default_value: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a secret from Key Vault with caching.
        
        Args:
            secret_name: Name of the secret in Key Vault
            default_value: Default value if secret is not found
            
        Returns:
            Secret value or default value
        """
        # Check cache first
        if secret_name in self._cache:
            return self._cache[secret_name]
            
        try:
            secret = self.client.get_secret(secret_name)
            value = secret.value
            
            # Cache the value
            self._cache[secret_name] = value
            
            logging.debug(f"Successfully retrieved secret: {secret_name}")
            return value
            
        except Exception as e:
            logging.warning(f"Failed to retrieve secret '{secret_name}': {str(e)}")
            return default_value
    
    def get_secrets_batch(self, secret_names: Dict[str, str]) -> Dict[str, Optional[str]]:
        """
        Retrieve multiple secrets at once.
        
        Args:
            secret_names: Dictionary of {local_name: keyvault_secret_name}
            
        Returns:
            Dictionary of {local_name: secret_value}
        """
        results = {}
        
        for local_name, kv_secret_name in secret_names.items():
            results[local_name] = self.get_secret(kv_secret_name)
            
        return results
    
    def clear_cache(self):
        """Clear the secret cache."""
        self._cache.clear()
        logging.debug("Key Vault secret cache cleared")


# Secret name mappings for Key Vault
SECRET_MAPPINGS = {
    # Azure AD Authentication
    "AZURE_CLIENT_SECRET_VALUE": "azure-client-secret",
    "AZURE_SERVER_APP_SECRET": "azure-server-app-secret", 
    "AUTH_CLIENT_SECRET": "auth-client-secret",
    
    # Cosmos DB
    "AZURE_COSMOSDB_ACCOUNT_KEY": "cosmosdb-account-key",
    
    # External Data Sources
    "ELASTICSEARCH_ENCODED_API_KEY": "elasticsearch-api-key",
    "PINECONE_API_KEY": "pinecone-api-key",
    "MONGODB_PASSWORD": "mongodb-password",
    "AZURE_COSMOSDB_MONGO_VCORE_CONNECTION_STRING": "cosmosdb-mongo-connection-string",
    "AZURE_SQL_SERVER_CONNECTION_STRING": "sql-server-connection-string",
    
    # Promptflow
    "PROMPTFLOW_API_KEY": "promptflow-api-key",
    
    # Optional: Legacy API Keys (if not using Managed Identity)
    "AZURE_OPENAI_KEY": "openai-api-key",
    "AZURE_OPENAI_EMBEDDING_KEY": "openai-embedding-key", 
    "AZURE_SEARCH_KEY": "search-api-key",
}


def initialize_keyvault_secrets() -> Optional[Dict[str, Optional[str]]]:
    """
    Initialize and retrieve secrets from Key Vault.
    
    Returns:
        Dictionary of environment variable names and their values from Key Vault
    """
    # Check if Key Vault is configured
    vault_url = os.environ.get("AZURE_KEYVAULT_URL")
    if not vault_url:
        logging.info("AZURE_KEYVAULT_URL not configured, skipping Key Vault integration")
        return None
    
    try:
        # Initialize Key Vault configuration
        config = KeyVaultConfig(
            vault_url=vault_url,
            use_managed_identity=os.environ.get("AZURE_KEYVAULT_USE_MANAGED_IDENTITY", "true").lower() == "true",
            client_id=os.environ.get("AZURE_KEYVAULT_CLIENT_ID")
        )
        
        # Initialize secret manager
        secret_manager = KeyVaultSecretManager(config)
        
        # Retrieve all secrets
        secrets = secret_manager.get_secrets_batch(SECRET_MAPPINGS)
        
        # Update environment variables with retrieved secrets
        for env_var, secret_value in secrets.items():
            if secret_value is not None:
                os.environ[env_var] = secret_value
                logging.info(f"Successfully loaded secret for {env_var} from Key Vault")
        
        logging.info(f"Key Vault integration completed. Loaded {len([v for v in secrets.values() if v is not None])} secrets")
        return secrets
        
    except Exception as e:
        logging.error(f"Key Vault initialization failed: {str(e)}")
        return None


# Auto-initialize Key Vault secrets when module is imported
if __name__ != "__main__":
    initialize_keyvault_secrets()


def get_secret(secret_name: str, default_value: Optional[str] = None) -> Optional[str]:
    """
    Simple helper function to get a secret from Key Vault.
    
    Args:
        secret_name: Name of the secret in Key Vault
        default_value: Default value if secret is not found
        
    Returns:
        Secret value or default value
    """
    vault_url = os.environ.get("AZURE_KEYVAULT_URL")
    if not vault_url:
        logging.warning("AZURE_KEYVAULT_URL not configured, returning default value")
        return default_value
    
    try:
        # Initialize Key Vault configuration
        use_managed_identity = os.environ.get("AZURE_KEYVAULT_USE_MANAGED_IDENTITY", "true").lower() == "true"
        
        config = KeyVaultConfig(
            vault_url=vault_url,
            use_managed_identity=use_managed_identity,
            client_id=os.environ.get("AZURE_KEYVAULT_CLIENT_ID")
        )
        
        # Initialize secret manager
        secret_manager = KeyVaultSecretManager(config)
        
        # Retrieve the secret
        secret_value = secret_manager.get_secret(secret_name, default_value)
        
        if secret_value:
            logging.debug(f"Successfully retrieved secret: {secret_name}")
        else:
            logging.warning(f"Secret '{secret_name}' not found, using default value")
        
        return secret_value
        
    except Exception as e:
        logging.error(f"Failed to retrieve secret '{secret_name}': {str(e)}")
        return default_value


class KeyVaultService:
    """
    Key Vault統合サービス - app.py移行用のファサード
    
    TDD Phase 4: app.pyのKey Vault機能を段階的に移行するためのサービス層
    """
    
    def __init__(self, secret_manager: KeyVaultSecretManager):
        self.secret_manager = secret_manager
        self.logger = logging.getLogger(__name__)
    
    @classmethod
    def from_environment(cls) -> "KeyVaultService":
        """環境変数からKey Vaultサービスを初期化"""
        vault_url = (
            os.environ.get("AZURE_KEY_VAULT_URL")
            or os.environ.get("AZURE_KEYVAULT_URL") 
            or os.environ.get("AZURE_KEYVAULT_URI")
        )
        
        if not vault_url:
            raise ValueError("Key Vault URL not configured in environment variables")
        
        use_managed_identity = os.environ.get("AZURE_KEYVAULT_USE_MANAGED_IDENTITY", "true").lower() == "true"
        
        config = KeyVaultConfig(
            vault_url=vault_url,
            use_managed_identity=use_managed_identity,
            client_id=os.environ.get("AZURE_KEYVAULT_CLIENT_ID")
        )
        
        secret_manager = KeyVaultSecretManager(config)
        return cls(secret_manager)
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        app.pyのget_secret_from_keyvault関数の代替
        
        Args:
            secret_name: Key Vaultのシークレット名
            
        Returns:
            シークレット値またはNone
        """
        return self.secret_manager.get_secret(secret_name)
    
    def get_openai_configuration(self) -> Dict[str, Any]:
        """
        OpenAI設定をKey Vaultから取得
        
        Returns:
            OpenAI設定辞書
        """
        config = {}
        
        # API Key取得
        api_key = self.get_secret("openai-api-key")
        if api_key:
            config["api_key"] = api_key
        
        # エンドポイント取得
        endpoint = self.get_secret("openai-endpoint")
        if endpoint:
            config["endpoint"] = endpoint
        
        # デプロイメント名取得  
        deployment = self.get_secret("openai-deployment")
        if deployment:
            config["deployment"] = deployment
            
        return config
    
    def get_frontend_settings(self) -> Dict[str, Any]:
        """
        フロントエンド設定をKey Vaultから取得（機密情報を除外）
        
        Returns:
            フロントエンド安全設定辞書
        """
        settings = {}
        
        # アプリタイトル
        title = self.get_secret("app-title")
        if title:
            settings["title"] = title
        
        # UIテーマ
        theme = self.get_secret("ui-theme") 
        if theme:
            settings["theme"] = theme
            
        # 認証要求設定
        auth_required = self.get_secret("auth-required")
        if auth_required:
            settings["auth_required"] = auth_required.lower() == "true"
            
        return settings


# app.py互換性のためのヘルパー関数（移行期間中の使用）
def get_secret_from_keyvault_new(secret_name: str) -> Optional[str]:
    """
    app.pyのget_secret_from_keyvault関数の新実装
    
    既存のapp.py関数をbackend/keyvault_utils.pyの実装に移行するためのヘルパー
    """
    try:
        service = KeyVaultService.from_environment()
        return service.get_secret(secret_name)
    except Exception as e:
        logging.error(f"Failed to retrieve secret using new KeyVaultService: {e}")
        return None
