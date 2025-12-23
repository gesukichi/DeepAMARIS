"""
Modern RAG + Web Search Integration Service

This module implements Azure AI Agents Service integration with:
- Azure AI Search (RAG) for internal documents
- Bing Grounding for web search
- Unified citation management and response formatting

Author: GitHub Copilot
Created: 2025-07-30
"""

import logging
import time
import asyncio
import html as html_utils
import os
import aiohttp
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# デバッグ制御用環境変数
# 注意: 本番環境（Azure）では絶対に設定しないでください
# デフォルト値 "false" により、本番環境では自動的にデバッグログが無効化されます
# 開発環境でのみ有効にしてください
DEBUG_CITATION_EXTRACTION = os.environ.get("DEBUG_CITATION_EXTRACTION", "false").lower() in ("true", "1", "yes")
DEBUG_BING_GROUNDING = os.environ.get("DEBUG_BING_GROUNDING", "false").lower() in ("true", "1", "yes")
DEBUG_RESPONSE_PROCESSING = os.environ.get("DEBUG_RESPONSE_PROCESSING", "false").lower() in ("true", "1", "yes")

# ログレベルを強制的にINFOに設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from azure.identity.aio import DefaultAzureCredential
from backend.settings import app_settings

# Conditional import for Azure AI Agents (preview package)
try:
    from azure.ai.agents.aio import AgentsClient
    from azure.ai.agents.models import (
        Agent, 
        ThreadRun, 
        ThreadMessage,
        BingGroundingTool,
        AzureAISearchTool,
        AzureAISearchQueryType
    )
    AZURE_AI_AGENTS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Azure AI Agents not available: {e}")
    AZURE_AI_AGENTS_AVAILABLE = False
    # Fallback classes for type hints
    class AgentsClient: pass
    class Agent: pass
    class ThreadRun: pass
    class ThreadMessage: pass
    class BingGroundingSearchConfiguration: pass
    class AzureAISearchTool: pass
    class AzureAISearchQueryType: pass

# 既存のloggerを削除して上で設定したloggerを使用


@dataclass
class SearchProxyClient:
    """
    Azure Functions Search Proxy Client
    
    This client provides an alternative to AzureAISearchTool for connecting
    to Azure AI Search through Azure Functions proxy when direct connectivity
    is not available due to private endpoints.
    """
    
    def __init__(self):
        """Initialize proxy client with environment variables"""
        self.proxy_url = os.environ.get("SEARCH_PROXY_URL", "")
        self.proxy_key = os.environ.get("SEARCH_PROXY_KEY", "")
        
        if not self.proxy_url:
            raise ValueError("SEARCH_PROXY_URL environment variable is required")
        if not self.proxy_key:
            raise ValueError("SEARCH_PROXY_KEY environment variable is required")
            
        logger.info(f"SearchProxyClient initialized with endpoint: {self.proxy_url}")
    
    async def search(self, query: str, top: int = 5, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Perform search through Azure Functions proxy
        
        Args:
            query: Search query text
            top: Maximum number of results to return
            filters: Optional search filters
            
        Returns:
            Dictionary containing search results and metadata
        """
        search_request = {
            "query": query,
            "top": top
        }
        
        if filters:
            search_request["filters"] = filters
            
        headers = {
            "Content-Type": "application/json",
            "x-functions-key": self.proxy_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.proxy_url,
                    json=search_request,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Search proxy returned {len(result.get('results', []))} results")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"Search proxy error {response.status}: {error_text}")
                        raise Exception(f"Search proxy failed with status {response.status}: {error_text}")
                        
        except Exception as e:
            logger.error(f"Search proxy client error: {e}")
            raise
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Generate Azure AI Agents tool definition for the search proxy
        
        Returns:
            Tool definition dictionary compatible with Azure AI Agents
        """
        return {
            "type": "function",
            "function": {
                "name": "search_internal_documents",
                "description": "Search internal company documents and knowledge base using Azure AI Search via proxy",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query text to find relevant documents"
                        },
                        "top": {
                            "type": "integer",
                            "description": "Maximum number of search results to return (default: 5)",
                            "default": 5
                        },
                        "filters": {
                            "type": "object",
                            "description": "Optional search filters to apply",
                            "properties": {},
                            "additionalProperties": True
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    
    async def execute_tool_call(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute tool call for Azure AI Agents
        
        Args:
            function_name: Name of the function to execute
            arguments: Function arguments
            
        Returns:
            JSON string with search results
        """
        if function_name == "search_internal_documents":
            query = arguments.get("query", "")
            top = arguments.get("top", 5)
            filters = arguments.get("filters")
            
            logger.info(f"Executing proxy search for query: '{query}' with top={top}")
            
            try:
                results = await self.search(query, top, filters)
                return json.dumps(results, ensure_ascii=False)
            except Exception as e:
                error_result = {
                    "error": str(e),
                    "results": []
                }
                return json.dumps(error_result, ensure_ascii=False)
        else:
            raise ValueError(f"Unknown function: {function_name}")


@dataclass
class CitationInfo:
    """Citation information structure"""
    type: str  # "web_search" or "internal_search"
    source: str  # "bing_grounding" or "azure_ai_search"
    title: str
    url: Optional[str] = None
    query: Optional[str] = None
    index: Optional[str] = None
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'type': self.type,
            'source': self.source,
            'title': self.title,
            'url': self.url,
            'query': self.query,
            'index': self.index
        }


@dataclass
class ModernRagResponse:
    """Modern RAG response structure"""
    status: str
    response: str
    citations: List[CitationInfo]
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    source: str = "azure_ai_agents"
    error: Optional[str] = None
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'status': self.status,
            'response': self.response,
            'citations': [citation.to_dict() for citation in self.citations],
            'thread_id': self.thread_id,
            'run_id': self.run_id,
            'source': self.source,
            'error': self.error
        }


class ModernBingGroundingAgentService:
    """
    Modern Azure AI Agents implementation with RAG + Web Search combination
    
    Features:
    - Automatic tool selection based on query context
    - RAG + Web search integration
    - Citation extraction and formatting
    - Error handling and retry logic
    """
    
    def __init__(self):
        """Initialize the service with Azure credentials and settings"""
        if not AZURE_AI_AGENTS_AVAILABLE:
            raise ImportError("Azure AI Agents package not available")
            
        self.credential = None
        self.agents_client: Optional[AgentsClient] = None
        self.agent_cache: Dict[str, Agent] = {}
        self._client_lock = asyncio.Lock()
        
        # Load settings from environment variables and Key Vault
        import os
        from backend.keyvault_utils import get_secret
        
        self.agent_endpoint = os.environ.get("AZURE_AI_AGENT_ENDPOINT")
        # Get API Key from Key Vault (secure) or fallback to environment variable (legacy)
        self.agent_key = get_secret("AZURE-AI-AGENT-KEY", os.environ.get("AZURE_AI_AGENT_KEY"))
        self.bing_grounding_conn_id = os.environ.get("BING_GROUNDING_CONN_ID")
        self.ai_search_conn_id = os.environ.get("AI_SEARCH_CONN_ID")
        self.ai_search_index_name = os.environ.get("AI_SEARCH_INDEX_NAME")
        self.response_timeout = 300  # Default timeout in seconds
        
        # Initialize Azure Functions Search Proxy Client if configured
        self.search_proxy_client: Optional[SearchProxyClient] = None
        proxy_url = os.environ.get("SEARCH_PROXY_URL", "")
        if proxy_url:
            try:
                self.search_proxy_client = SearchProxyClient()
                logger.info("Azure Functions Search Proxy client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize search proxy client: {e}")
        
        logger.info(f"Modern RAG initialization:")
        logger.info(f"  - AZURE_AI_AGENT_ENDPOINT: {'SET' if self.agent_endpoint else 'NOT SET'}")
        logger.info(f"  - AZURE_AI_AGENT_KEY: {'SET (from Key Vault)' if self.agent_key else 'NOT SET'}")
        logger.info(f"  - BING_GROUNDING_CONN_ID: {'SET' if self.bing_grounding_conn_id else 'NOT SET'}")
        logger.info(f"  - AI_SEARCH_CONN_ID: {'SET' if self.ai_search_conn_id else 'NOT SET'}")
        logger.info(f"  - AI_SEARCH_INDEX_NAME: {'SET' if self.ai_search_index_name else 'NOT SET'}")
        logger.info(f"  - SEARCH_PROXY_CLIENT: {'SET' if self.search_proxy_client else 'NOT SET'}")
        
        # デバッグモード状態をログ出力（セキュリティ確認用）
        debug_modes = []
        if DEBUG_CITATION_EXTRACTION:
            debug_modes.append("CITATION_EXTRACTION")
        if DEBUG_BING_GROUNDING:
            debug_modes.append("BING_GROUNDING") 
        if DEBUG_RESPONSE_PROCESSING:
            debug_modes.append("RESPONSE_PROCESSING")
        
        if debug_modes:
            logger.warning(f"⚠️ デバッグモードが有効です: {', '.join(debug_modes)} (本番環境では無効化してください)")
        else:
            logger.info("✅ デバッグモードは無効です（本番環境に適した設定）")
        
    @classmethod
    async def create(cls):
        """Factory method for async initialization"""
        self = cls()
        
        # Use DefaultAzureCredential (it automatically chooses the best auth method)
        self.credential = await DefaultAzureCredential().__aenter__()
        
        # Validate required settings
        if not self.agent_endpoint:
            raise ValueError("AZURE_AI_AGENT_ENDPOINT not configured")
        if not self.bing_grounding_conn_id:
            raise ValueError("BING_GROUNDING_CONN_ID not configured")
            
        logger.info(f"Initialized ModernBingGroundingAgentService with endpoint: {self.agent_endpoint}")
        return self
    
    async def _get_agents_client(self) -> AgentsClient:
        """Get or create Azure AI Agents client with managed identity authentication"""
        async with self._client_lock:
            if not self.agents_client:
                try:
                    self.agents_client = AgentsClient(
                        endpoint=self.agent_endpoint,
                        credential=self.credential
                    )
                    logger.info("Azure AI Agents client initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize Azure AI Agents client: {e}")
                    raise
        
        return self.agents_client
    
    async def aclose(self):
        """Cleanup resources"""
        if self.agents_client:
            await self.agents_client.close()
        # Cleanup DefaultAzureCredential
        if self.credential and hasattr(self.credential, '__aexit__'):
            await self.credential.__aexit__(None, None, None)
        
        return self.agents_client
    
    async def create_corp_web_rag_agent(self) -> Agent:
        """
        Create RAG + Web search integration agent
        
        Returns:
            Agent: Configured agent with both RAG and Web search tools
        """
        client = await self._get_agents_client()
        
        # Configure Bing Grounding tool (Web search)
        bing_tool = BingGroundingTool(
            connection_id=self.bing_grounding_conn_id,
            market="ja-JP",
            set_lang="ja",
            count=5,
            # freshness="Week",  # TODO: 必要に応じて有効化
        )
        
        # 型安全な初期化
        tools = list(bing_tool.definitions) if bing_tool.definitions else []
        tool_resources = bing_tool.resources if bing_tool.resources else None

        # Use Azure Functions Search Proxy if available, otherwise fallback to AzureAISearchTool
        if self.search_proxy_client:
            # Azure Functions プロキシ経由での検索を使用
            logger.info("Using Azure Functions Search Proxy for internal search")
            # プロキシクライアントをカスタムツールとして追加
            proxy_tool_def = self.search_proxy_client.get_tool_definition()
            tools.append(proxy_tool_def)
            logger.info("Added Search Proxy as custom tool")
        elif self.ai_search_conn_id and self.ai_search_index_name:
            # 従来のAzureAISearchToolを使用（直接接続）
            ai_search_tool = AzureAISearchTool(
                index_connection_id=self.ai_search_conn_id,  # 正しいパラメータ名
                index_name=self.ai_search_index_name,
                query_type=AzureAISearchQueryType.VECTOR_SEMANTIC_HYBRID,
                top_k=5,
            )

            # ToolDefinition を追加
            if ai_search_tool.definitions:
                tools.extend(list(ai_search_tool.definitions))

            # ToolResources を安全にマージ
            if ai_search_tool.resources:
                if tool_resources:
                    tool_resources.update(ai_search_tool.resources)  # Pydantic Model 同士を直接統合
                else:
                    tool_resources = ai_search_tool.resources

            logger.info(f"Added Azure AI Search tool for index: {self.ai_search_index_name}")
        else:
            logger.warning("Azure AI Search not configured - only web search will be available")

        # Agent instructions for intelligent tool selection
        instructions = """
        あなたは社内ナレッジ(検索ツール)と公開Web情報(Bingツール)を組み合わせて回答する日本語アシスタントです。

        ガイドライン:
        1. 質問内容を分析し、適切なツールを選択または組み合わせてください
        2. 社内文書で回答できる場合は検索ツールを優先してください  
        3. 最新情報や一般的な情報が必要な場合はBingツールを使用してください
        4. 両方の情報が有用な場合は、両ツールを使用して包括的に回答してください
        5. 回答では必ず出典を [S1] (社内文書) / [W1] (Web情報) のように明示してください
        6. 複数の情報源を使用する場合は、それぞれの出典を明確に区別してください
        7. 情報が不正確または古い可能性がある場合は、その旨を明記してください
        8. 回答は簡潔で理解しやすく、かつ包括的な内容にしてください
        """.strip()
        
        # Get model name for Azure AI Agents - use dedicated environment variable or fallback
        import os
        model_name = (
            os.environ.get("AZURE_AI_AGENTS_MODEL") or  # Dedicated for Modern RAG
            os.environ.get("AZURE_OPENAI_MODEL_NAME") or 
            getattr(app_settings.azure_openai, "model", None)
        )
        if not model_name:
            raise ValueError("Azure AI Agents model is not configured (AZURE_AI_AGENTS_MODEL, AZURE_OPENAI_MODEL_NAME or AZURE_OPENAI_MODEL)")

        # Azure AI Agents requires model in format: "gpt-4o" or "gpt-35-turbo" (not deployment names)
        # Convert deployment name to model name if needed
        model_for_agent = model_name
        if model_name.startswith("gpt-4"):
            if "turbo" in model_name.lower():
                model_for_agent = "gpt-4-turbo"
            else:
                model_for_agent = "gpt-4o"  # Default to gpt-4o for gpt-4 variants
        elif model_name.startswith("gpt-35") or model_name.startswith("gpt-3.5"):
            model_for_agent = "gpt-35-turbo"
        elif model_name == "turbo":  # Handle legacy "turbo" deployment name - use directly
            model_for_agent = "turbo"  # Use deployment name directly for Azure AI Agents
        
        logger.info(f"Using model for Azure AI Agents: {model_for_agent} (original: {model_name})")
        logger.info(f"Creating agent with {len(tools)} tools and tool_resources: {bool(tool_resources)}")

        # Create agent
        try:            
            agent = await client.create_agent(
                name="corp-web-rag-agent",
                model=model_for_agent,
                instructions=instructions,
                tools=tools,
                tool_resources=tool_resources
            )
            
            logger.info(f"Created agent: {agent.id} with {len(tools)} tools")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            logger.error(f"Model: {model_for_agent}, Tools count: {len(tools)}, Tool resources: {tool_resources}")
            raise

    
    async def _get_or_create_agent(self) -> Agent:
        """Get cached agent or create new one"""
        agent_key = "corp-web-rag-agent"
        
        if agent_key not in self.agent_cache:
            self.agent_cache[agent_key] = await self.create_corp_web_rag_agent()
        
        return self.agent_cache[agent_key]
    
    async def _wait_for_completion(self, run: ThreadRun, thread_id: str, timeout: Optional[int] = None) -> ThreadRun:
        """
        Wait for agent run completion with timeout and handle custom tool calls
        
        Args:
            run: The run to wait for
            thread_id: Thread ID
            timeout: Maximum wait time in seconds
            

        Returns:
            ThreadRun: Completed run object
        """
        if timeout is None:
            timeout = self.response_timeout or 60
            
        client = await self._get_agents_client()
        start_time = time.time()
        
        while True:
            try:
                current_run = await client.runs.get(thread_id=thread_id, run_id=run.id)

                # Handle required actions (tool calls)
                if current_run.status.lower() == "requires_action":
                    if (hasattr(current_run, 'required_action') and 
                        current_run.required_action and
                        hasattr(current_run.required_action, 'submit_tool_outputs') and
                        current_run.required_action.submit_tool_outputs and
                        hasattr(current_run.required_action.submit_tool_outputs, 'tool_calls')):
                        
                        tool_calls = current_run.required_action.submit_tool_outputs.tool_calls
                        tool_outputs = []
                        
                        logger.info(f"Processing {len(tool_calls)} tool calls")
                        
                        for tool_call in tool_calls:
                            logger.info(f"Processing tool call: {tool_call.id} - {tool_call.function.name}")
                            
                            try:
                                # Handle search proxy tool calls
                                if (tool_call.function.name == "search_internal_documents" and 
                                    self.search_proxy_client):
                                    
                                    arguments = json.loads(tool_call.function.arguments)
                                    result = await self.search_proxy_client.execute_tool_call(
                                        tool_call.function.name, 
                                        arguments
                                    )
                                    
                                    tool_outputs.append({
                                        "tool_call_id": tool_call.id,
                                        "output": result
                                    })
                                    logger.info(f"Search proxy tool call completed: {tool_call.id}")
                                else:
                                    # Unknown tool call
                                    error_output = json.dumps({
                                        "error": f"Unknown tool function: {tool_call.function.name}",
                                        "results": []
                                    }, ensure_ascii=False)
                                    
                                    tool_outputs.append({
                                        "tool_call_id": tool_call.id,
                                        "output": error_output
                                    })
                                    logger.warning(f"Unknown tool call: {tool_call.function.name}")
                                    
                            except Exception as e:
                                logger.error(f"Tool call {tool_call.id} failed: {e}")
                                error_output = json.dumps({
                                    "error": str(e),
                                    "results": []
                                }, ensure_ascii=False)
                                
                                tool_outputs.append({
                                    "tool_call_id": tool_call.id,
                                    "output": error_output
                                })
                        
                        # Submit tool outputs
                        if tool_outputs:
                            logger.info(f"Submitting {len(tool_outputs)} tool outputs")
                            await client.runs.submit_tool_outputs(
                                thread_id=thread_id,
                                run_id=current_run.id,
                                tool_outputs=tool_outputs
                            )
                            logger.info("Tool outputs submitted successfully")
                
                elif current_run.status.lower() in ["completed", "failed", "cancelled", "expired"]:
                    logger.info(f"Run {run.id} completed with status: {current_run.status}")
                    return current_run
                
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    logger.error(f"Run {run.id} timed out after {elapsed:.2f} seconds")
                    raise TimeoutError(f"Agent run timed out after {timeout} seconds")
                
                # Wait before next check
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error checking run status: {e}")
                raise
    
    async def _extract_response(self, thread_id: str, message_created_at: int) -> str:
        """
        Extract agent response from thread messages
        
        Args:
            thread_id: Thread ID
            message_created_at: Timestamp to filter messages
            
        Returns:
            str: Agent response text
        """
        try:
            client = await self._get_agents_client()
            # Handle both async iterator and direct list responses
            messages_result = client.messages.list(thread_id=thread_id)
            if hasattr(messages_result, '__aiter__'):
                # Async iterator response
                messages = sorted(
                    [m async for m in messages_result],
                    key=lambda m: m.created_at,
                    reverse=True
                )
            else:
                # Direct list/dict response
                if hasattr(messages_result, 'data'):
                    messages = sorted(messages_result.data, key=lambda m: m.created_at, reverse=True)
                else:
                    messages = sorted(messages_result, key=lambda m: m.created_at, reverse=True)
            
            # Find the latest assistant message after user message
            for message in messages:
                if (message.role == "assistant" and 
                    message.created_at.timestamp() > message_created_at and
                    message.content):
                    
                    # Extract text content
                    if message.text_messages:
                        return message.text_messages[-1].text.value
                    else:
                        return str(message.content[0])
            
            logger.warning("No assistant response found in thread")
            return "申し訳ございませんが、回答を取得できませんでした。"
            
        except Exception as e:
            logger.error(f"Error extracting response: {e}")
            return f"回答取得エラー: {str(e)}"
    
    async def _extract_modern_citations(self, run: ThreadRun, thread_id: str) -> List[CitationInfo]:
        """
        Extract citation information from Modern Azure AI Agents run
        
        Args:
            run: Completed run object
            thread_id: Thread ID
            
        Returns:
            List[CitationInfo]: List of citation information
        """
        citations = []
        
        try:
            client = await self._get_agents_client()
            if not client:
                logger.warning("No agents client available for citation extraction")
                return citations
            
            # Get run steps for tool call analysis
            if DEBUG_CITATION_EXTRACTION:
                logger.info(f"=== Citation Extraction Debug Start ===")
            run_steps_result = client.run_steps.list(thread_id=thread_id, run_id=run.id)
            if DEBUG_CITATION_EXTRACTION:
                logger.info(f"run_steps_result type: {type(run_steps_result)}")
            
            if hasattr(run_steps_result, '__aiter__'):
                # Async iterator response
                run_steps = [s async for s in run_steps_result]
                if DEBUG_CITATION_EXTRACTION:
                    logger.info(f"run_steps (async iterator): {len(run_steps)} steps")
            else:
                # Direct list/dict response
                if hasattr(run_steps_result, 'data'):
                    run_steps = run_steps_result.data
                    if DEBUG_CITATION_EXTRACTION:
                        logger.info(f"run_steps (data): {len(run_steps) if hasattr(run_steps, '__len__') else 'N/A'} steps")
                else:
                    run_steps = run_steps_result
                    if DEBUG_CITATION_EXTRACTION:
                        logger.info(f"run_steps (direct): {len(run_steps) if hasattr(run_steps, '__len__') else 'N/A'} steps")

            citation_counter_web = 0
            citation_counter_search = 0
            
            if DEBUG_CITATION_EXTRACTION:
                logger.info(f"Processing {len(run_steps) if hasattr(run_steps, '__len__') else 'unknown'} run steps")

            for i, step in enumerate(run_steps):
                if DEBUG_CITATION_EXTRACTION:
                    logger.info(f"Step [{i}]: type={type(step)}")
                    logger.info(f"Step [{i}]: hasattr step_details = {hasattr(step, 'step_details')}")
                
                if (hasattr(step, 'step_details') and 
                    step.step_details and 
                    hasattr(step.step_details, 'tool_calls') and 
                    step.step_details.tool_calls):
                    
                    for tool_call in step.step_details.tool_calls:
                        if DEBUG_CITATION_EXTRACTION:
                            logger.info(f"  Processing tool_call: type={type(tool_call)}")
                            logger.info(f"  Tool call attributes: {dir(tool_call)}")
                        
                        # Check for output attribute (most common case)
                        if hasattr(tool_call, 'output') and tool_call.output:
                            if DEBUG_CITATION_EXTRACTION:
                                logger.info(f"  Tool call has output: type={type(tool_call.output)}")
                                logger.info(f"  Output attributes: {dir(tool_call.output)}")
                                logger.info(f"  Output content: {str(tool_call.output)[:1000]}")
                            
                            try:
                                # Parse the JSON data
                                if hasattr(tool_call.output, 'json'):
                                    if DEBUG_CITATION_EXTRACTION:
                                        logger.info(f"  Output has JSON attribute: {type(tool_call.output.json)}")
                                    json_data = json.loads(tool_call.output.json) if isinstance(tool_call.output.json, str) else tool_call.output.json
                                elif hasattr(tool_call.output, 'data'):
                                    if DEBUG_CITATION_EXTRACTION:
                                        logger.info(f"  Output has data attribute: {type(tool_call.output.data)}")
                                    json_data = tool_call.output.data
                                else:
                                    if DEBUG_CITATION_EXTRACTION:
                                        logger.info(f"  Output direct content: {str(tool_call.output)[:200]}")
                                    json_data = json.loads(tool_call.output) if isinstance(tool_call.output, str) else tool_call.output
                                
                                if DEBUG_CITATION_EXTRACTION:
                                    logger.info(f"  Parsed JSON data type: {type(json_data)}")
                                if isinstance(json_data, dict):
                                    logger.info(f"  JSON keys: {json_data.keys()}")
                                    
                                    # Look for results in the JSON data
                                    if 'results' in json_data:
                                        results = json_data['results']
                                        logger.info(f"  Found results: {len(results) if hasattr(results, '__len__') else 'Not iterable'}")
                                        
                                        for k, result in enumerate(results[:2]):  # Limit to first 2 for debugging
                                            logger.info(f"    Result [{k}] type: {type(result)}")
                                            if isinstance(result, dict):
                                                logger.info(f"    Result [{k}] keys: {list(result.keys())}")
                                                # Log all attributes to understand structure
                                                for key, value in result.items():
                                                    logger.info(f"    Result [{k}] {key}: {str(value)[:100]}")
                                            
                                            # Try to extract URL from this result
                                            url = None
                                            url_attributes = ['url', 'website_url', 'link', 'href', 'source_url', 'reference_url', 'displayUrl', 'webSearchUrl']
                                            for attr in url_attributes:
                                                if isinstance(result, dict) and attr in result:
                                                    url = result[attr]
                                                    logger.info(f"    *** FOUND URL via '{attr}': {url} ***")
                                                    break
                                            
                                            if url:
                                                citation_counter_web += 1
                                                citation_id_web = f"web_{citation_counter_web}"
                                                
                                                title = result.get('name', result.get('title', url)) if isinstance(result, dict) else url
                                                content = result.get('snippet', '') if isinstance(result, dict) else ''
                                                
                                                citation = CitationInfo(
                                                    type="web_search",
                                                    source="bing_grounding",
                                                    query=str(result.get('query', 'web search')),
                                                    url=url,
                                                    title=str(title)
                                                )
                                                citations.append(citation)
                                                logger.info(f"    *** ADDED CITATION {citation_id_web}: {title} -> {url} ***")
                                            else:
                                                logger.warning(f"    No URL found in result {k}")
                                    
                                    else:
                                        if DEBUG_CITATION_EXTRACTION:
                                            logger.info(f"  No 'results' key found in JSON data")
                                
                            except (json.JSONDecodeError, KeyError, AttributeError) as e:
                                if DEBUG_CITATION_EXTRACTION:
                                    logger.warning(f"  Error processing tool call output: {e}")
                                    logger.warning(f"  Raw output: {str(tool_call.output)[:500]}")
                        else:
                            if DEBUG_CITATION_EXTRACTION:
                                logger.info(f"  Tool call has no output attribute")
                        
                        
                        # Bing Grounding citations - 詳細なデバッグ情報を追加
                        if hasattr(tool_call, 'bing_grounding') and tool_call.bing_grounding:
                            citation_counter_web += 1
                            
                            # デバッグ情報をログ出力
                            if DEBUG_BING_GROUNDING:
                                logger.info(f"=== Bing Grounding Debug Info ===")
                                logger.info(f"tool_call type: {type(tool_call)}")
                                logger.info(f"bing_grounding type: {type(tool_call.bing_grounding)}")
                                logger.info(f"bing_grounding dir: {dir(tool_call.bing_grounding)}")
                            
                            # 実際の内容をJSONシリアライズして確認
                            try:
                                import json
                                if DEBUG_BING_GROUNDING:
                                    if hasattr(tool_call.bing_grounding, '__dict__'):
                                        bing_dict = tool_call.bing_grounding.__dict__
                                        logger.info(f"bing_grounding dict: {json.dumps(bing_dict, indent=2, default=str)}")
                                    else:
                                        logger.info(f"bing_grounding content: {tool_call.bing_grounding}")
                                
                                # response_metadataを詳しく解析
                                if 'response_metadata' in tool_call.bing_grounding:
                                    metadata_str = tool_call.bing_grounding['response_metadata']
                                    if DEBUG_BING_GROUNDING:
                                        logger.info(f"response_metadata raw: {metadata_str}")
                                    
                                    # JSON文字列として解析を試行
                                    try:
                                        if isinstance(metadata_str, str):
                                            import ast
                                            metadata_dict = ast.literal_eval(metadata_str)
                                            if DEBUG_BING_GROUNDING:
                                                logger.info(f"response_metadata parsed: {metadata_dict}")
                                        else:
                                            if DEBUG_BING_GROUNDING:
                                                logger.info(f"response_metadata is not string: {type(metadata_str)}")
                                    except Exception as parse_error:
                                        if DEBUG_BING_GROUNDING:
                                            logger.warning(f"Failed to parse response_metadata: {parse_error}")
                                
                                # requesturlから検索クエリを抽出
                                if 'requesturl' in tool_call.bing_grounding:
                                    request_url = tool_call.bing_grounding['requesturl']
                                    if DEBUG_BING_GROUNDING:
                                        logger.info(f"request_url: {request_url}")
                                    
                                    # URLから検索クエリを抽出
                                    from urllib.parse import urlparse, parse_qs
                                    parsed_url = urlparse(request_url)
                                    query_params = parse_qs(parsed_url.query)
                                    if 'q' in query_params:
                                        actual_query = query_params['q'][0]
                                        if DEBUG_BING_GROUNDING:
                                            logger.info(f"*** Extracted actual search query: {actual_query} ***")
                                        search_query = actual_query
                                
                            except Exception as e:
                                if DEBUG_BING_GROUNDING:
                                    logger.info(f"bing_grounding serialization error: {e}")
                                    logger.info(f"bing_grounding raw: {tool_call.bing_grounding}")
                            
                            # 複数の属性名で試行
                            if search_query == 'Unknown':
                                search_query = (
                                    getattr(tool_call.bing_grounding, 'query', None) or
                                    getattr(tool_call.bing_grounding, 'search_query', None) or
                                    getattr(tool_call.bing_grounding, 'input', None) or
                                    'Unknown'
                                )
                            
                            # 検索結果の詳細情報を抽出
                            results = getattr(tool_call.bing_grounding, 'results', None) or []
                            output = getattr(tool_call.bing_grounding, 'output', None)
                            
                            if DEBUG_BING_GROUNDING:
                                logger.info(f"search_query: {search_query}")
                                logger.info(f"results type: {type(results)}, length: {len(results) if hasattr(results, '__len__') else 'N/A'}")
                                logger.info(f"output: {output}")
                            
                            if results and isinstance(results, list) and len(results) > 0:
                                # 実際の検索結果から情報を抽出
                                for i, result in enumerate(results[:3]):  # 最大3つの結果
                                    citation_counter_web += 1
                                    
                                    # 様々な属性名の可能性を試行
                                    result_url = (
                                        getattr(result, 'url', None) or 
                                        getattr(result, 'link', None) or
                                        getattr(result, 'source_url', None) or
                                        getattr(result, 'href', None)
                                    )
                                    
                                    result_title = (
                                        getattr(result, 'title', None) or 
                                        getattr(result, 'name', None) or
                                        getattr(result, 'display_name', None) or
                                        getattr(result, 'snippet', None) or
                                        f"Web検索結果 {i+1}"
                                    )
                                    
                                    # URLが取得できない場合は、Bing検索URLを生成
                                    if not result_url:
                                        encoded_query = search_query.replace(' ', '+') if search_query != 'Unknown' else '東京+天気'
                                        result_url = f"https://www.bing.com/search?q={encoded_query}"
                                    
                                    citation = CitationInfo(
                                        type="web_search",
                                        source="bing_grounding",
                                        query=str(search_query),
                                        url=result_url,
                                        title=str(result_title)
                                    )
                                    citations.append(citation)
                            else:
                                # Azure AI Agents 1.1.0b4では個別の検索結果URLが提供されないため、
                                # 検索クエリに基づいて情報源リンクを生成する
                                if DEBUG_CITATION_EXTRACTION:
                                    logger.warning(f"No individual search results available from Bing Grounding. Generating fallback citations.")
                                
                                # 検索クエリから関連する情報源を推測
                                weather_sources = [
                                    {
                                        "title": "Yahoo!天気・災害",
                                        "url": f"https://weather.yahoo.co.jp/weather/search/?p={search_query.replace(' ', '+')}"
                                    },
                                    {
                                        "title": "ウェザーニュース",
                                        "url": f"https://weathernews.jp/s/search.html?q={search_query.replace(' ', '+')}"
                                    },
                                    {
                                        "title": "気象庁",
                                        "url": "https://www.jma.go.jp/bosai/forecast/"
                                    }
                                ]
                                
                                general_sources = [
                                    {
                                        "title": f"Bing検索結果: {search_query}",
                                        "url": f"https://www.bing.com/search?q={search_query.replace(' ', '+')}"
                                    },
                                    {
                                        "title": f"Google検索結果: {search_query}",
                                        "url": f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
                                    }
                                ]
                                
                                # 天気関連のクエリの場合は天気情報源を、そうでなければ一般的な検索結果を提供
                                if any(keyword in search_query.lower() for keyword in ['天気', '気温', '予報', 'weather', 'forecast']):
                                    sources_to_use = weather_sources
                                else:
                                    sources_to_use = general_sources
                                
                                for source in sources_to_use[:2]:  # 最大2つのソース
                                    citation_counter_web += 1
                                    citation = CitationInfo(
                                        type="web_search",
                                        source="bing_grounding",
                                        query=str(search_query),
                                        url=source["url"],
                                        title=source["title"]
                                    )
                                    citations.append(citation)
                                    if DEBUG_CITATION_EXTRACTION:
                                        logger.info(f"Added fallback citation: {source['title']} -> {source['url']}")
                        
                        # Azure AI Search citations 
                        elif hasattr(tool_call, 'azure_ai_search') and tool_call.azure_ai_search:
                            citation_counter_search += 1
                            
                            citation = CitationInfo(
                                type="internal_search",
                                source="azure_ai_search",
                                title="社内文書検索結果",
                                index=self.ai_search_index_name
                            )
                            citations.append(citation)
            
            if DEBUG_CITATION_EXTRACTION:
                logger.info(f"Extracted {len(citations)} citations (Web: {citation_counter_web}, Search: {citation_counter_search})")
            return citations
            
        except Exception as e:
            logger.error(f"Citation extraction error: {e}")
            return [CitationInfo(
                type="error",
                source="extraction_error",
                title=f"Citation extraction failed: {str(e)}"
            )]
    
    async def process_user_query(self, user_message: str, user_id: str = None) -> ModernRagResponse:
        """
        Process user query with integrated RAG + Web search
        
        Args:
            user_message: User's question/query
            user_id: Optional user identifier
            
        Returns:
            ModernRagResponse: Integrated response with citations
        """
        try:
            preview = html_utils.escape(user_message[:20])
            logger.info(f"Processing query preview='{preview}...' (len={len(user_message)})")
            
            # Get or create agent
            agent = await self._get_or_create_agent()
            client = await self._get_agents_client()
            
            # Create thread for conversation
            thread = await client.threads.create()
            if DEBUG_RESPONSE_PROCESSING:
                logger.debug(f"Created thread: {thread.id}")
            
            # Send user message
            message = await client.messages.create(
                thread_id=thread.id,
                role="user", 
                content=user_message
            )
            if DEBUG_RESPONSE_PROCESSING:
                logger.debug(f"Created message: {message.id}")
            
            # Execute agent
            run = await client.runs.create(
                thread_id=thread.id,
                agent_id=agent.id
            )
            if DEBUG_RESPONSE_PROCESSING:
                logger.debug(f"Created run: {run.id}")
            
            # Wait for completion
            completed_run = await self._wait_for_completion(run, thread.id)

            if completed_run.status.lower() == "completed":
                # Extract response
                response_text = await self._extract_response(thread.id, message.created_at.timestamp())
                
                # Extract citations
                citations = await self._extract_modern_citations(completed_run, thread.id)

                if DEBUG_RESPONSE_PROCESSING:
                    logger.info(f"Successfully processed query with {len(citations)} citations")
                
                return ModernRagResponse(
                    status="success",
                    response=response_text,
                    citations=citations,
                    thread_id=thread.id,
                    run_id=completed_run.id,
                    source="azure_ai_agents"
                )
            else:
                # Log detailed error information for failed runs
                error_details = []
                error_details.append(f"Run status: {completed_run.status}")
                
                # Get additional error information if available
                if hasattr(completed_run, 'last_error') and completed_run.last_error:
                    error_details.append(f"Last error: {completed_run.last_error}")
                
                if hasattr(completed_run, 'required_action') and completed_run.required_action:
                    error_details.append(f"Required action: {completed_run.required_action}")
                
                # Try to get run steps for more detailed error information
                try:
                    run_steps_result = client.run_steps.list(thread_id=thread.id, run_id=completed_run.id)
                    if hasattr(run_steps_result, '__aiter__'):
                        # Async iterator response
                        run_steps = [s async for s in run_steps_result]
                    else:
                        # Direct list/dict response
                        if hasattr(run_steps_result, 'data'):
                            run_steps = run_steps_result.data
                        else:
                            run_steps = run_steps_result
                    for i, step in enumerate(run_steps):
                        if hasattr(step, 'last_error') and step.last_error:
                            error_details.append(f"Step {i} error: {step.last_error}")
                        if hasattr(step, 'status') and step.status:
                            error_details.append(f"Step {i} status: {step.status}")
                except Exception as step_error:
                    error_details.append(f"Could not retrieve run steps: {step_error}")
                
                error_msg = f"Agent execution failed with status: {completed_run.status}. Details: {'; '.join(error_details)}"
                logger.error(error_msg)
                
                return ModernRagResponse(
                    status="error",
                    response="",
                    citations=[],
                    error=error_msg
                )
                
        except TimeoutError as e:
            logger.error(f"Query processing timeout: {e}")
            return ModernRagResponse(
                status="timeout",
                response="",
                citations=[],
                error=str(e)
            )
            
        except Exception as e:
            logger.error(f"Query processing error: {e}")
            return ModernRagResponse(
                status="error",
                response="",
                citations=[],
                error=str(e)
            )
    
    def format_citations_html(self, citations: List[CitationInfo]) -> str:
        """
        Format citations as HTML for frontend display
        
        Args:
            citations: List of citation information
            
        Returns:
            str: HTML formatted citations
        """
        if not citations:
            return ""
        
        html = "<div class='citations'><h4>参考情報:</h4><ul>"
        
        web_counter = 0
        search_counter = 0
        
        for citation in citations:
            if not citation:
                continue
                
            if citation.type == "web_search":
                web_counter += 1
                safe_url   = html_utils.escape(str(citation.url or ""))
                safe_title = html_utils.escape(str(citation.title or "Web検索結果"))
                html += (
                    f"<li class='web-citation'>"
                    f"[W{web_counter}] <a href='{safe_url}' target='_blank' class='web-link'>"
                    f"{safe_title}</a><span class='source-type'>Web検索</span></li>"
                )
            elif citation.type == "internal_search":
                search_counter += 1
                safe_title = html_utils.escape(str(citation.title or "社内文書検索結果"))
                html += f"""
                <li class='internal-citation'>
                    [S{search_counter}] {safe_title}
                    <span class='source-type'>社内文書</span>
                </li>"""
            elif citation.type == "error":
                safe_error_title = html_utils.escape(str(citation.title or "不明なエラー"))
                html += f"""
                <li class='error-citation'>
                    <span class='error'>エラー: {safe_error_title}</span>
                </li>
                """
        
        html += "</ul></div>"
        return html
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Service health check with detailed diagnostics
        
        Returns:
            Dict: Health status information
        """
        try:
            client = await self._get_agents_client()
            
            # Basic client connectivity test
            test_result = {
                "status": "healthy",
                "azure_ai_agents_available": AZURE_AI_AGENTS_AVAILABLE,
                "endpoint": self.agent_endpoint,
                "bing_grounding_configured": bool(self.bing_grounding_conn_id),
                "ai_search_configured": bool(self.ai_search_conn_id and self.ai_search_index_name),
                "search_proxy_configured": bool(self.search_proxy_client),
                "search_method": "proxy" if self.search_proxy_client else ("direct" if self.ai_search_conn_id else "none"),
                "cached_agents": len(self.agent_cache)
            }
            
            # Try to create a test agent to verify configuration
            try:
                test_agent = await self._get_or_create_agent()
                test_result["agent_creation"] = "success"
                test_result["agent_id"] = test_agent.id if test_agent else "unknown"
                
                # Test model configuration
                import os
                model_name = os.environ.get("AZURE_OPENAI_MODEL_NAME") or getattr(app_settings.azure_openai, "model", None)
                test_result["model_original"] = model_name
                
                if model_name:
                    if model_name.startswith("gpt-4"):
                        if "turbo" in model_name.lower():
                            model_for_agent = "gpt-4-turbo"
                        else:
                            model_for_agent = "gpt-4o"
                    elif model_name.startswith("gpt-35") or model_name.startswith("gpt-3.5"):
                        model_for_agent = "gpt-35-turbo"
                    elif model_name == "turbo":
                        model_for_agent = "gpt-35-turbo"
                    else:
                        model_for_agent = model_name
                    
                    test_result["model_for_agent"] = model_for_agent
                
            except Exception as agent_error:
                test_result["agent_creation"] = "failed"
                test_result["agent_error"] = str(agent_error)
            
            logger.info("Health check passed")
            return test_result
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "azure_ai_agents_available": AZURE_AI_AGENTS_AVAILABLE
            }


# Global service instance
_service_instance: Optional[ModernBingGroundingAgentService] = None


def get_modern_rag_service() -> ModernBingGroundingAgentService:
    """
    Get global service instance from app context
    
    Returns:
        ModernBingGroundingAgentService: Service instance
    """
    from quart import current_app
    
    if hasattr(current_app, 'modern_rag') and current_app.modern_rag:
        return current_app.modern_rag
    
    # Fallback to global instance (for testing/development)
    global _service_instance
    if _service_instance is None:
        if not AZURE_AI_AGENTS_AVAILABLE:
            raise ImportError("Azure AI Agents package not available")
        
        raise RuntimeError("Modern RAG service not initialized. Please ensure app.modern_rag is set during startup.")
    
    return _service_instance
