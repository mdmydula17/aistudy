# crawler/

## ONLY (唯一职责)
- 使用 DrissionPage 驱动浏览器抓取目标网页内容
- 输出标准化的 `CrawlResult`（raw_text + image_urls）

## FORBIDDEN (禁止行为)
- 禁止 import `app.crud`、`app.graph`、`app.api`、`app.models`
- 禁止混入业务逻辑（如 LLM 调用、数据库写入、状态判断）
- 禁止直接操作数据库
