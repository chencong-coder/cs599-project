"""
配置中心 —— 统一管理环境变量、LLM 实例、MCP 连接参数。
使用 OpenAI 兼容接口调用通义千问（阿里百炼）。
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


@dataclass
class Config:
    """全局配置，单例语义 —— 模块级 CONFIG 实例"""

    # API 密钥
    api_key: str = field(
        default_factory=lambda: os.getenv("DASHSCOPE_API_KEY", "")
    )

    # LLM（OpenAI 兼容接口）
    model_name: str = "qwen3.7-plus"
    temperature: float = 0.7
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # MCP 连接（阿里百炼高德地图）
    mcp_transport: str = "http"
    mcp_url: str = "https://dashscope.aliyuncs.com/api/v1/mcps/amap-maps/mcp"

    # 工具领域映射
    tool_domains: dict = field(default_factory=lambda: {
        "poi":     ["maps_text_search", "maps_search_detail"],
        "weather": ["maps_weather"],
        "route":   [
            "maps_direction_walking_by_address",
            "maps_direction_driving_by_address",
            "maps_direction_transit_integrated_by_address",
        ],
    })

    # 自动检查初始化
    def __post_init__(self):
        if not self.api_key:
            raise ValueError("请配置 DASHSCOPE_API_KEY")

    # 创建模型实例对象
    def create_llm(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            streaming=True,
        )


CONFIG = Config()
