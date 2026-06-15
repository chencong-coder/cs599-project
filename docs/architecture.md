# 系统架构

## 架构总览

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

## 架构特点

1. **三层 Agent 嵌套**：Planner (总控) → SpecialistAgent (领域) → MCP Tools (底层 API)
2. **子 Agent 作为 Tool**：Hotel/Attraction/Weather Agent 被 `@tool` 装饰器包装，对 Planner 透明
3. **混合工具来源**：Planner 的工具来自子 Agent 包装 + 直接 MCP 路线工具

## 数据流

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
