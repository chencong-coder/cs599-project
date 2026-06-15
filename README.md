# 🧳 智能旅行助手 (AI Travel Agent)

## 项目简介
基于 Multi-Agent 架构的智能旅行规划系统，集成高德地图 MCP 服务，支持 CLI 和 Web 双界面。用户输入目的地、日期和偏好，AI 自动规划包含天气、景点、酒店、餐饮、交通和预算的完整旅行方案。

## 方向
**方向一：Agentic AI 原生开发**

本项目从零构建了一个多层 Multi-Agent 智能体系统，使用 LangGraph 作为 Agent 编排框架，通过 MCP 协议集成外部地图服务，实现 Planner → Specialist → MCP Tools 三层 Agent 协作架构。

## 技术栈
- **AI IDE**: VS Code
- **LLM**: 通义千问 (qwen3.7-plus) via 阿里百炼 DashScope API
- **Agent 框架**: LangChain + LangGraph
- **MCP 协议**: langchain-mcp-adapters（连接高德地图服务）
- **Web 界面**: Streamlit 1.32.0
- **配置管理**: python-dotenv
- **运行环境**: Python 3.12+

## 目录结构
```
src/
├── Agent.py                  # CLI 入口
├── app.py                    # Streamlit Web 入口
├── config.py                 # 配置中心：API Key、模型参数、MCP 连接
├── mcp_client.py             # MCP 客户端管理器（单例模式）
├── prompts.py                # System Prompt 集中管理（5 个 Prompt）
├── render.py                 # 渲染引擎：JSON 解析 + CLI/Web 格式化输出
└── agents/
    ├── planner.py            # 总控 Agent：编排子 Agent + 流式输出
    └── specialist.py         # 领域专家 Agent：POI 搜索 / 天气查询
```

### 模块职责
| 模块 | 职责 |
|------|------|
| `config.py` | 全局配置单例，LLM 工厂方法，OpenAI 兼容接口调用通义千问 |
| `mcp_client.py` | MCP 连接生命周期管理，按领域（poi/weather/route）分发工具 |
| `specialist.py` | 单一职责 ReAct Agent，封装酒店搜索、景点搜索、天气查询 |
| `planner.py` | 总控编排：加载工具 → 创建子 Agent → 包装为 Tool → 流式输出 |
| `prompts.py` | 5 个 System Prompt 集中管理，定义 JSON 输出 Schema 和工作流 |
| `render.py` | JSON → CLI 格式化（Unicode 边框 + emoji）/ Web 渲染 |
| `Agent.py` | CLI 演示入口，支持流式 / 非流式两种模式 |
| `app.py` | Streamlit Web UI，侧边栏参数 + 主区域结果展示 + Markdown 下载 |

## 环境搭建

### 1. 依赖安装
```bash
# 创建虚拟环境
conda create -n agent python=3.12
conda activate agent

# 安装依赖
pip install langchain langchain-community langchain-mcp-adapters
pip install streamlit python-dotenv dashscope
```

### 2. 环境变量配置
在项目根目录创建 `.env` 文件（⚠️ 不硬编码 API Key，不提交到版本控制）：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
```

> 阿里百炼 API Key 申请地址：https://dashscope.console.aliyun.com/

### 3. 启动步骤
```bash
# CLI 模式（命令行输出）
python src/Agent.py

# Web 模式（Streamlit 图形界面）
streamlit run src/app.py
```

## 项目状态
- [x] Proposal
- [x] MVP
- [x] Final

---

## 系统架构
```
┌──────────────────────────────────────────────────────────┐
│                      用户界面层                           │
│   Agent.py (CLI)          app.py (Streamlit Web)          │
└──────────────┬──────────────────────┬────────────────────┘
               │                      │
┌──────────────▼──────────────────────▼────────────────────┐
│                   TripPlanner (总控 Agent)                │
│                                                          │
│   system_prompt: PLANNER_AGENT_PROMPT                    │
│   tools: [search_hotel, search_attraction,               │
│           query_weather, maps_direction_*]               │
│                                                          │
│   职责：接收用户需求 → 编排子 Agent → 整合结果 → JSON     │
└──┬──────────────┬──────────────┬─────────────────────────┘
   │              │              │
   ▼              ▼              ▼
┌──────┐  ┌──────┐  ┌──────┐  ┌─────────────────────┐
│Hotel │  │Attrc │  │Weathr│  │ MCP 路线工具（直接）  │
│Agent │  │Agent │  │Agent │  │ walking/driving/     │
│      │  │      │  │      │  │ transit              │
└──┬───┘  └──┬───┘  └──┬───┘  └──────────┬──────────┘
   │         │         │                  │
   │    ┌────┘    ┌────┘                  │
   ▼    ▼         ▼                       │
┌─────────────────────────────────────────▼──────────────┐
│               McpClientManager (单例)                    │
│                                                         │
│   transport: http                                       │
│   url: dashscope.aliyuncs.com/api/v1/mcps/amap-maps/mcp│
│                                                         │
│   ★ 工具按领域分发: poi / weather / route               │
│   ★ 懒加载 + 缓存: 首次访问时才建立连接并缓存工具列表    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│              阿里百炼 MCP 服务 (高德地图)                  │
│                                                          │
│   15 个工具: maps_text_search, maps_weather,              │
│   maps_direction_*, maps_geo, maps_distance, ...         │
└──────────────────────────────────────────────────────────┘
```

### 架构特点
1. **三层 Agent 嵌套**：Planner (总控) → SpecialistAgent (领域) → MCP Tools (底层 API)
2. **子 Agent 作为 Tool**：Hotel/Attraction/Weather Agent 被 `@tool` 装饰器包装，对 Planner 透明
3. **混合工具来源**：Planner 的工具来自子 Agent 包装 + 直接 MCP 路线工具

### 数据流
```
用户输入自然语言
      │
      ▼
┌─────────────────┐
│  build_prompt()  │  结构化参数 → 自然语言 prompt 字符串
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ TripPlanner     │
│   .stream()     │
│                 │
│  Planner LLM    │  根据 system_prompt 决定调用哪些工具
│   ↓             │
│  query_weather  │  → WeatherAgent.invoke() → MCP maps_weather
│   ↓             │     返回天气数据 JSON
│  search_hotel   │  → HotelAgent.invoke() → MCP maps_text_search
│   ↓             │     返回酒店列表
│  search_attrcn  │  → AttractionAgent.invoke() → MCP maps_text_search
│   ↓             │     返回景点列表
│  maps_direction │  → 直接调用 MCP 路线工具
│   ↓             │
│  Planner LLM    │  整合所有工具结果，按 Schema 生成 JSON
│   ↓             │
│  逐 token       │  ──── stream ────→ CLI 终端 或 Web spinner
│  yield          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  parse_plan()    │  从混合文本中提取 JSON
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  格式化渲染      │
│  · CLI: format_plan_cli()  → Unicode 边框 + emoji
│  · Web: st.markdown + CSS  → 卡片 + Tab + Metric
└─────────────────┘
```

## 设计模式
| 模式 | 应用位置 | 说明 |
|------|---------|------|
| **单例模式** | `McpClientManager` | `__new__` + `_initialized` 双重保护，保证全局唯一 MCP 连接 |
| **工厂方法** | `Config.create_llm()` | 统一 LLM 实例创建，隔离构造细节 |
| **门面模式** | `TripPlanner` | 对外暴露简单的 `invoke()`/`stream()` 接口，隐藏内部多 Agent 复杂性 |
| **装饰器模式** | `@tool` 包装子 Agent | 将 SpecialistAgent 适配为 LangChain Tool 接口 |
| **策略模式** | `tool_domains` 字典 | 工具按领域分组，运行时按需选择策略 |
| **适配器模式** | `render.py` | 将 JSON 数据适配为 CLI 格式 / Streamlit 组件两种视图 |

## 关键 Bug 修复记录
### Bug 1：ChatTongyi 流式 tool_calls 的 KeyError（已解决）
- **症状**：`KeyError: 'name'` at `tongyi.py:606`
- **根因**：`langchain_community` 的 `subtract_client_response()` 未对 `prev_function` 做 key 存在性检查
- **最终方案**：切换为 `ChatOpenAI` + 百炼 OpenAI 兼容接口，从根源规避该 Bug

### Bug 2：`nonlocal` 作用域错误
- **症状**：`SyntaxError: no binding for nonlocal 'full_text' found`
- **根因**：`app.py` 的 `_collect()` 嵌套函数使用 `nonlocal` 引用模块级变量
- **修复**：将 `_collect()` 改为只 return 结果，变量处理移到外层同步代码

### Bug 3：天气卡片文字不可见
- **症状**：天气预报卡片区域文字颜色过浅
- **根因**：CSS 未设置 `color`，Streamlit 暗色主题下文字默认白色
- **修复**：添加 `color: #1a1a1a` 到 `.weather-card` 和 `.budget-card`
