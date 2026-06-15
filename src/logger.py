"""
可观测性日志系统 —— 结构化日志、Agent 调用链路追踪、异常捕获。
"""
import logging
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 日志格式
_FORMAT = (
    "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
)
_DATE_FORMAT = "%m-%d %H:%M:%S"

# 根 Logger
logger = logging.getLogger("travel_agent")
logger.setLevel(logging.DEBUG)

# 控制台 Handler（INFO 级别）
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT))
logger.addHandler(console)

# 文件 Handler（DEBUG 级别，全量日志）
file_handler = logging.FileHandler(LOG_DIR / "agent.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT))
logger.addHandler(file_handler)


class AgentTracer:
    """Agent 调用链路追踪器。

    用法:
        tracer = AgentTracer("TripPlanner")
        async with tracer.span("query_weather"):
            result = await weather_agent.invoke(query)
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self._log = logging.getLogger(f"travel_agent.{agent_name}")

    @asynccontextmanager
    async def span(self, operation: str, **metadata):
        """追踪一个操作 Span。"""
        start = time.perf_counter()
        self._log.info(f"▶ {operation} 开始 {metadata if metadata else ''}")
        try:
            yield
            elapsed = time.perf_counter() - start
            self._log.info(f"✓ {operation} 完成 ({elapsed:.2f}s)")
        except Exception as e:
            elapsed = time.perf_counter() - start
            self._log.error(f"✗ {operation} 失败 ({elapsed:.2f}s): {e}")
            raise


# 全局 tracer 工厂
def get_tracer(name: str) -> AgentTracer:
    return AgentTracer(name)
