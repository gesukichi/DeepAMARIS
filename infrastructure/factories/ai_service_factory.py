"""
AIサービスファクトリモジュール

app.pyのinit_openai_client関数を移植し、
ファクトリパターンとして実装
"""

import os
import json
import logging
import httpx
from typing import Optional, Dict, Any, List
from openai import AsyncAzureOpenAI
from azure.identity.aio import DefaultAzureCredential, ManagedIdentityCredential, get_bearer_token_provider
from azure.keyvault.secrets import SecretClient

from backend.settings import app_settings, MINIMUM_SUPPORTED_AZURE_OPENAI_PREVIEW_API_VERSION
from backend.keyvault_utils import KeyVaultService

# app.pyからget_secret_from_keyvault機能を移植
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential as SyncDefaultAzureCredential, ManagedIdentityCredential as SyncManagedIdentityCredential

# User agent for API calls
USER_AGENT = "GitHubCopilotChat-Sample/1.0.0"

# Global tools configuration (移植時はより良い管理方法を検討)
azure_openai_tools: List[Dict[str, Any]] = []
azure_openai_available_tools: List[str] = []


class AIServiceFactory:
    """
    Azure OpenAI クライアントの作成を担当するファクトリクラス
    
    app.pyのinit_openai_client関数を移植し、
    依存性注入とテスタビリティを向上させたファクトリパターン実装
    """
    
    def __init__(self, keyvault_service: Optional[KeyVaultService] = None, keyvault_client: Optional[SecretClient] = None):
        """
        Args:
            keyvault_service: Key Vaultサービスのインスタンス（DIコンテナから注入）
            keyvault_client: 従来のKey Vaultクライアント（後方互換性）
        """
        self.keyvault_service = keyvault_service
        self.keyvault_client = keyvault_client
        self.logger = logging.getLogger(__name__)
    
    def get_secret_from_keyvault(self, secret_name: str) -> Optional[str]:
        """
        Key Vaultからシークレットを取得する
        
        app.pyのget_secret_from_keyvault関数を移植
        
        Args:
            secret_name: シークレット名
            
        Returns:
            str: シークレット値、見つからない場合はNone
        """
        # Phase 4: 新しいサービス層を優先使用
        if self.keyvault_service:
            try:
                result = self.keyvault_service.get_secret(secret_name)
                if result:
                    self.logger.info(f"Successfully retrieved secret '{secret_name}' using KeyVaultService")
                    return result
            except Exception as e:
                self.logger.warning(f"KeyVaultService failed for '{secret_name}': {e}")
        
        # 後方互換性: 既存実装をフォールバック
        if not self.keyvault_client:
            return None
        
        try:
            secret = self.keyvault_client.get_secret(secret_name)
            self.logger.info(f"Successfully retrieved secret '{secret_name}' using legacy client")
            return secret.value
        except Exception as e:
            self.logger.error(f"Failed to retrieve secret {secret_name} from Key Vault: {e}")
            return None
    
    async def create_azure_openai_client(self) -> AsyncAzureOpenAI:
        """
        Azure OpenAI クライアントを作成する
        
        app.pyのinit_openai_client関数を移植
        
        Returns:
            AsyncAzureOpenAI: 設定されたAzure OpenAIクライアント
            
        Raises:
            ValueError: 必須設定が不足している場合
            Exception: クライアント初期化に失敗した場合
        """
        try:
            # API version check
            if (
                app_settings.azure_openai.preview_api_version
                < MINIMUM_SUPPORTED_AZURE_OPENAI_PREVIEW_API_VERSION
            ):
                raise ValueError(
                    f"The minimum supported Azure OpenAI preview API version is '{MINIMUM_SUPPORTED_AZURE_OPENAI_PREVIEW_API_VERSION}'"
                )

            # Endpoint validation and construction
            endpoint = await self._get_endpoint()
            
            # Authentication configuration
            aoai_api_key, ad_token_provider = await self._configure_authentication()
            
            # Deployment validation
            deployment = await self._get_deployment()
            
            # Azure Functions tools setup
            await self._setup_azure_functions_tools()
            
            # Create client
            azure_openai_client = AsyncAzureOpenAI(
                api_version=app_settings.azure_openai.preview_api_version,
                api_key=aoai_api_key,
                azure_ad_token_provider=ad_token_provider,
                default_headers={"x-ms-useragent": USER_AGENT},
                azure_endpoint=endpoint,
            )

            return azure_openai_client
            
        except Exception as e:
            self.logger.exception("Exception in Azure OpenAI initialization: %s", str(e))
            raise e
    
    async def _get_endpoint(self) -> str:
        """エンドポイントの取得と検証"""
        if (
            not app_settings.azure_openai.endpoint and
            not app_settings.azure_openai.resource
        ):
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_RESOURCE is required"
            )

        endpoint = (
            app_settings.azure_openai.endpoint
            if app_settings.azure_openai.endpoint
            else f"https://{app_settings.azure_openai.resource}.openai.azure.com/"
        )
        
        return endpoint
    
    async def _configure_authentication(self) -> tuple[Optional[str], Optional[Any]]:
        """
        認証設定の構成
        
        Returns:
            tuple: (api_key, ad_token_provider)
        """
        aoai_api_key = None
        ad_token_provider = None
        
        # 第一優先：新Key Vaultサービスからの取得（最も安全）
        if self.keyvault_service:
            try:
                openai_config = self.keyvault_service.get_openai_configuration()
                if openai_config.get("api_key"):
                    aoai_api_key = openai_config["api_key"]
                    self.logger.info("Using OpenAI API key from Key Vault service (secure)")
                    
                    # エンドポイントもKey Vaultから取得可能
                    if openai_config.get("endpoint"):
                        endpoint = openai_config["endpoint"]
                        self.logger.info("Using OpenAI endpoint from Key Vault service")
            except Exception as e:
                self.logger.warning(f"Failed to get OpenAI config from Key Vault service: {e}")
        
        # フォールバック：従来のKey Vault取得
        if not aoai_api_key:
            keyvault_secret = self.get_secret_from_keyvault("openai-api-key")
            if keyvault_secret:
                aoai_api_key = keyvault_secret
                self.logger.info("Using OpenAI API key from legacy Key Vault (secure fallback)")
        
        # 最終フォールバック：App Service設定
        if not aoai_api_key:
            aoai_api_key = app_settings.azure_openai.key
            if aoai_api_key and aoai_api_key.startswith("@Microsoft.KeyVault"):
                self.logger.info("Using OpenAI API key from App Service Key Vault reference (secure fallback)")
            elif aoai_api_key:
                self.logger.warning("Using OpenAI API key from app settings (fallback)")
            else:
                self.logger.error("No OpenAI API key available from any source")
        
        # Azure Entra ID認証の設定
        if not aoai_api_key:
            self.logger.debug("No AZURE_OPENAI_KEY found, using Azure Entra ID auth")
            
            # Use managed identity with explicit client ID
            managed_identity_client_id = os.environ.get("AZURE_CLIENT_ID")
            if managed_identity_client_id:
                # Use specific managed identity
                credential = ManagedIdentityCredential(client_id=managed_identity_client_id)
                self.logger.info(f"Using managed identity for OpenAI with client ID: {managed_identity_client_id}")
            else:
                # Fallback to default credential
                credential = DefaultAzureCredential()
                self.logger.info("Using DefaultAzureCredential for OpenAI")
                
            ad_token_provider = get_bearer_token_provider(
                credential,
                "https://cognitiveservices.azure.com/.default"
            )
        
        return aoai_api_key, ad_token_provider
    
    async def _get_deployment(self) -> str:
        """デプロイメント名の取得と検証"""
        deployment = app_settings.azure_openai.model
        if not deployment:
            raise ValueError("AZURE_OPENAI_MODEL is required")
        return deployment
    
    async def _setup_azure_functions_tools(self) -> None:
        """Azure Functions ツールのセットアップ"""
        if not app_settings.azure_openai.function_call_azure_functions_enabled:
            return
            
        try:
            base_url = app_settings.azure_openai.function_call_azure_functions_tools_base_url
            key = app_settings.azure_openai.function_call_azure_functions_tools_key
            
            if base_url and key:
                azure_functions_tools_url = f"{base_url}?code={key}"
                async with httpx.AsyncClient() as client:
                    response = await client.get(azure_functions_tools_url)
                    
                if response.status_code == httpx.codes.OK:
                    tools_data = json.loads(response.text)
                    azure_openai_tools.extend(tools_data)
                    for tool in tools_data:
                        azure_openai_available_tools.append(tool["function"]["name"])
                else:
                    self.logger.error(f"An error occurred while getting OpenAI Function Call tools metadata: {response.status_code}")
            else:
                self.logger.warning("Azure Functions tools configuration incomplete, skipping function call setup")
                
        except Exception as e:
            self.logger.warning(f"Failed to setup Azure Functions tools: {str(e)}")
    
    async def call_azure_function(self, function_name: str, function_args: str) -> Optional[str]:
        """
        Azure Functionの呼び出し
        
        app.pyのopenai_remote_azure_function_call関数を移植
        
        Args:
            function_name: 関数名
            function_args: 関数の引数（JSON文字列）
            
        Returns:
            str: 関数の実行結果、または無効化されている場合はNone
        """
        if not app_settings.azure_openai.function_call_azure_functions_enabled:
            return None

        azure_functions_tool_url = f"{app_settings.azure_openai.function_call_azure_functions_tool_base_url}?code={app_settings.azure_openai.function_call_azure_functions_tool_key}"
        headers = {'content-type': 'application/json'}
        body = {
            "tool_name": function_name,
            "tool_arguments": json.loads(function_args)
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(azure_functions_tool_url, data=json.dumps(body), headers=headers)
        response.raise_for_status()

        return response.text


# ファクトリのインスタンス作成用ヘルパー関数
def create_ai_service_factory(
    keyvault_service: Optional[KeyVaultService] = None,
    keyvault_client: Optional[SecretClient] = None
) -> AIServiceFactory:
    """
    AIServiceFactoryのインスタンスを作成する
    
    Args:
        keyvault_service: Key Vaultサービス（DIコンテナから注入される）
        keyvault_client: 従来のKey Vaultクライアント（後方互換性）
        
    Returns:
        AIServiceFactory: 設定済みのファクトリインスタンス
    """
    return AIServiceFactory(keyvault_service=keyvault_service, keyvault_client=keyvault_client)
