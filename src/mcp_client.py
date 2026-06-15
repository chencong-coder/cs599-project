"""
MCP 客户端管理器 —— 单例模式，全局共享高德地图 MCP 连接。
生产级增强：超时重试、熔断保护、日志追踪。
"""
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool
from src.config import CONFIG
from src.logger import get_tracer

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 2.0  # 秒


class MCPConnectionError(Exception):
    """MCP 连接异常（可重试）。"""
    pass


class MCPRateLimitError(Exception):
    """MCP 调用频率超限。"""
    pass


class McpClientManager:
    """
    高德地图 MCP 客户端单例。

    职责：
      1. 管理与阿里百炼 MCP 服务器的连接（含超时重试）
      2. 按领域（poi/weather/route）分发工具子集
      3. 缓存已加载工具，避免重复请求
      4. 熔断保护：连续失败 N 次后走降级逻辑

    用法：
      manager = McpClientManager()
      poi_tools = await manager.get_tools_for("poi")
    """

    _instance: "McpClientManager | None" = None

    def __new__(cls) -> "McpClientManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._client: MultiServerMCPClient | None = None
        self._tools_cache: dict[str, list[BaseTool]] = {}
        self._consecutive_failures = 0
        self._circuit_open = False
        self._initialized = True
        self._tracer = get_tracer("McpClientManager")

    # ==================== 连接管理 ====================

    async def _get_client(self) -> MultiServerMCPClient:
        """懒加载 MCP 客户端"""
        if self._client is None:
            self._client = MultiServerMCPClient({
                "amap-server": {
                    "transport": CONFIG.mcp_transport,
                    "url": CONFIG.mcp_url,
                    "headers": {
                        "Authorization": f"Bearer {CONFIG.api_key}"
                    }
                }
            })
        return self._client

    # ==================== 工具获取（含重试） ====================

    async def get_all_tools(self) -> list[BaseTool]:
        """获取 MCP 服务器暴露的全部工具（含超时重试）。"""
        if "all" in self._tools_cache:
            return self._tools_cache["all"]

        if self._circuit_open:
            raise MCPConnectionError("MCP 服务熔断中，请稍后重试")

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with self._tracer.span(f"MCP连接 (第{attempt}次)"):
                    client = await self._get_client()
                    tools = await asyncio.wait_for(
                        client.get_tools(),
                        timeout=30.0
                    )
                    self._tools_cache["all"] = tools
                    self._consecutive_failures = 0
                    return tools

            except asyncio.TimeoutError:
                last_error = MCPConnectionError(
                    f"MCP 连接超时 (第{attempt}/{MAX_RETRIES}次)"
                )
            except Exception as e:
                error_str = str(e)
                if "500" in error_str:
                    last_error = MCPConnectionError(
                        f"MCP 服务内部错误 (第{attempt}/{MAX_RETRIES}次): {e}"
                    )
                elif "429" in error_str or "限制" in error_str:
                    self._circuit_open = True
                    raise MCPRateLimitError(
                        f"MCP 调用频率超限，已触发熔断: {e}"
                    )
                else:
                    last_error = MCPConnectionError(
                        f"MCP 连接失败 (第{attempt}/{MAX_RETRIES}次): {e}"
                    )

            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY * attempt)

        self._consecutive_failures += 1
        if self._consecutive_failures >= 3:
            self._circuit_open = True

        raise last_error

    async def get_tools_for(self, domain: str) -> list[BaseTool]:
        """按领域获取工具子集（降级：MCP不可用时返回空列表）。"""
        try:
            all_tools = await self.get_all_tools()
            target_names = set(CONFIG.tool_domains.get(domain, []))
            return [t for t in all_tools if t.name in target_names]
        except (MCPConnectionError, MCPRateLimitError) as e:
            self._tracer._log.warning(
                f"MCP 不可用，领域 [{domain}] 工具降级为空: {e}"
            )
            return []

    # ==================== 生命周期 ====================

    async def close(self):
        """关闭 MCP 连接"""
        self._client = None
        self._tools_cache.clear()
        self._circuit_open = False
        self._consecutive_failures = 0

    @classmethod
    def reset(cls):
        """重置单例（测试用）"""
        cls._instance = None
