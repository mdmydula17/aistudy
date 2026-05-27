# graph/

## ONLY (唯一职责)
- LangGraph 状态机编排：Crawl → Vision → Extract → Save
- HITL (人类介入逃生舱) 逻辑：confidence < 0.6 或连续 3 次解析失败时挂起
- LangSmith Trace 集成（通过环境变量 LANGSMITH_API_KEY 自动启用）

## FORBIDDEN (禁止行为)
- 禁止 import `fastapi`（graph 层不依赖 Web 框架）
- 禁止直接操作 HTTP 请求/响应
- 禁止包含数据库连接创建逻辑（db_session 由外部注入）

## 节点流转图
```
crawl ──→ [有图片?] ──→ vision ──→ extract ──→ [需要重试?]
              │                          ↑            │
              └──→ extract ──────────────┘            │
                                                     ↓
                                              [需要人工?]
                                              ↓         ↓
                                            save      extract(重试)
```
