# 前端接入已实现后端

本次仅后端，前端接入待后续实施。实际契约：`contracts/openapi.json`（也可 GET `/openapi.json`）。历史架构包的契约是设计基线，实际实现新增了运行 provider 元数据、错误字段及真实模块输入快照，以根目录导出文件为准。

## 地址与最短接入路径

开发地址 `http://127.0.0.1:18080`。CORS 默认允许 `http://localhost:3000` 和 `http://127.0.0.1:3000`（见 `.env.example`）。TeamRouter 密钥仅存在后端，任何 `NEXT_PUBLIC_*` 变量都不应包含它。

1. GET `/v1/capabilities`，显示可用格式与大小限制；GET `/v1/entities` 获取本地主体选项。
2. POST `/v1/cases`，Body `{"buyer":{"mode":"skip"},"seller":{"mode":"skip"}}`。保存 `case_id`，再 GET Workspace。
3. POST `/v1/cases/{case_id}/invoice`，multipart 字段 `file / expected_case_revision / replace=false`。202 仅代表排队。
4. 轮询 Workspace 直到解析结束；展示发票及买卖方解析状态，必要时 PATCH `/parties` 处理冲突。
5. POST `/assessments`，Body `{"expected_case_revision": 当前版本}`。每约 1 秒轮询 Workspace，切页/换 Case 时取消旧轮询。
6. 当 `initial_assessment_status == "settled"` 且 `navigation.target == "result"`，自动进入结果页。即使有失败或 needs_info 也应进入结果页显示原因，不继续无限等待。
7. 渲染 `aggregate.current_result` 和 `aggregate.decision`。局部重跑始终留在结果页。

初评进入结果页的信号不等于所有模块均成功。不要依赖进度条计时自动跳转，也不要需要额外点击 View result。

## 模块动作

统一前缀 `/v1/cases/{case_id}/modules/{module_key}`。模块 ID 为 `invoice_integrity / buyer_verification / seller_verification / relationship / market_price / payment_history / duplicate_financing`。

| 动作 | 接口 / Body |
|---|---|
| Full view | GET 模块前缀；包含当前 AI、证据、补充说明、调整和运行历史 |
| 上传证据 | POST `/evidence`，multipart `files` 可重复；`expected_module_version`，`rerun=true/false` |
| 补充文字 | POST `/supplements`，JSON `expected_module_version / text / rerun` |
| 独立重跑 | POST `/runs`，JSON `expected_module_version / reason` |
| 人工调整 | POST `/adjustments`，JSON `expected_module_version / applies_to_run_id / requested_adjustment / reason` |
| 历史运行 | GET `/runs/{run_id}`，含输入快照、AI 输出、模型/请求元数据和错误 |
| 原件下载 | GET `/v1/cases/{case_id}/files/{file_id}` |
| 状态历史 | GET `/v1/cases/{case_id}/events?after_seq=0&limit=50`，按 module_key 过滤展示 |

每次 mutation 都发送 `Idempotency-Key`（8–128 字符，推荐 UUID）。同一用户操作重试复用同一键及相同 Body；新操作生成新键。同键不同内容返回 409。幂等响应是原始受理响应，之后仍需 GET 最新状态。

`expected_module_version` 从最近一次 GET 获取。409 时重新取状态，保留用户草稿后重新提交；不要盲目改版本重放。文件与文字分别是两个事务；同时补文件和说明时可先 `rerun=false` 保存第一项，再取最新版本保存第二项并 `rerun=true`。

上传失败/未知格式不能显示成功。`capabilities.formats` 中 .pdf/.xlsx/.csv 可用；.xls/.docx/.doc/.png/.jpg 当前不可用。PDF 发票入口要求本次给定表单模板；PDF 补件要求可抽取文本，未接 OCR。

## 结果展示

| 字段 | 前端行为 |
|---|---|
| `state=queued/running` | 显示处理中；是否允许按钮以 allowed_actions 为准 |
| `state=failed/needs_info` | 显示具体错误/缺失项，当前分数不得补为 0 |
| `freshness=stale` | 显示旧分析已过期，新评估尚未完成 |
| `aggregate.current_result=null` | 当前总分不可用；融资决定 pending |
| `aggregate.last_valid_result` | 可展示历史分数，但明确“上一次结果”，不能当当前额度 |
| `adjustment_status=pending_review` | 新 AI 分已产生，人工调整需确认；当前融资仍 pending |
| `risk_band=LOW/HIGH` | 只有两档；未评估用 null，不增加 Medium |
| `decision.status=manual_review` | 需人工复核，不等于拒贷 |

金额使用字符串，例如 `"6400.00"`，不要用浮点数重新计算额度。AI 分、requested adjustment、effective adjustment、final score 分开显示。分数越高越危险；人工调整为 -5 表示降低风险。具体额度、阈值和阻断由后端决定。

Queue 为 GET `/v1/cases?risk_band=LOW|HIGH&limit=50&cursor=...`。其中 `risk_is_current=false` 表示展示历史风险档；结合 `aggregate_status` 显示过期或失败。无历史分数时 `risk_band=null`。

## 与现有前端原型的差异

若使用工作区现有前端，其 `/api` 简化四接口、three-band mock、`payment_behaviour`、`transaction_plausibility` 等不是本后端契约。需要增加 `/v1` client 和 view-model，不能仅改 Base URL 就宣称已接通。保留界面布局即可，数据流按上文替换；不把当前后端降回 Medium 或按补件数量自动减分。

本轮未实现任意规范化发票字段 PATCH；更正发票可重新上传（`replace=true`，无活动任务时），会使所有模块过期。主体选择有独立 PATCH 接口。Next.js 字段编辑若要持久化，应在后续新增有审计的后端编辑契约后再开放。

`scripts/live_case1.py --verify-rerun` 是接入流程的可执行参考；`runtime/live-case1.json` 是本地真实运行响应，不应打包到前端作为模拟“真实调用”。
