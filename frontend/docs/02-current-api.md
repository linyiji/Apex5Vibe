> 历史基线：本文件记录联调前的 Mock 原型。当前 Live 实现见 [联调说明](03-backend-integration.md)，真实结果见 [Live 验收](05-live-integration-verification.md)。

# 当前前端原型接口

本页描述 `lib/api.ts` 实际行为，不是工作区 `/v1` 契约。完整类型见 [lib/types.ts](../lib/types.ts)。

## 配置

```dotenv
NEXT_PUBLIC_API_MODE=mock
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

只有模式严格等于 `live` 才发请求。当前 URL 为 BASE_URL + path，所以 BASE_URL 应为无尾斜线的 origin，不带 `/api` 或 `/v1`。公开变量打入客户端构建；变更后重启开发服务，生产环境重新构建。

浏览器直接访问后端，无代理、鉴权、跨域 cookie、超时、重试、轮询、幂等 key 或并发版本。JSON 请求带 Content-Type；multipart 不手写 boundary。当前 GET 也带 JSON Content-Type，跨域可能触发预检。后端 CORS 需允许实际前端 origin。

## 请求清单

| 函数 | 方法 / 路径 | 请求 | 成功响应 |
|---|---|---|---|
| extractInvoice | POST `/api/invoices/extract` | multipart `file` | ExtractedInvoice |
| runAssessment | POST `/api/assessments` | JSON `{ invoice }` | 完整 Assessment |
| getAssessment | GET `/api/assessments/{id}` | 编码后的路径 ID | 完整 Assessment |
| submitAnalystInput | POST `/api/assessments/{id}/reassess` | multipart `module_id`、`note`、重复 `files` | 下一版本 Assessment，含 previous |
| loadDemoInvoice | 无 HTTP | 本地生成 | 本地 ExtractedInvoice，Live 模式亦如此 |

multipart 的实际字段名是 `files`，不是字面量 `files[]`。备注可空，UI 要求备注或附件至少一个。任何 2xx 均被强制断言为完整返回类型，所以后端 202 job 回执不能直接渲染为 Assessment。

## ExtractedInvoice

顶层：`file_name: string`、`simulated: boolean`、`fields`、`line_items[]`。

fields 必须包含全部 10 个键，每个值都是 `{value: string|null, status, source: string|null}`；缺失也返回对象，不能省略 key。status 为 `extracted | uncertain | missing | edited`。

| 键 | 意义 |
|---|---|
| seller / buyer | 主体名称字符串，不是实体对象 |
| buyer_registration | 买方注册号 |
| invoice_number | 发票编号 |
| invoice_date / due_date | 日期字符串 |
| amount | 如 `4030.00`，前端随后转 number |
| currency | 如 GBP |
| bank_account | 原型银行字段 |
| po_reference | PO 引用 |

LineItem 为 `{description: string, quantity: number|null, unit_price: number|null, amount: number|null}`。不能直接替换为后端含主体对象、定点金额及来源引用的 Invoice。

## Assessment

| 字段 | 类型 / 语义 |
|---|---|
| id / version / createdAt | string / number / ISO 时间 |
| invoice | ExtractedInvoice |
| score | number，预期 0–100，不支持 null |
| band | `low | medium | high` |
| recommendation | `eligible | manual_review | decline` |
| advanceRate / financingAmount | number 或 null；比例 0–1 |
| modules | 7 个 RiskModule，按 points 降序显示 |
| drivers | id/moduleId/title/explanation/points/whatToCheck[] |
| completeness | percent 和 items[]；item 含 id/label/status/note/moduleId |
| evidence | EvidenceItem[] |
| preliminary | boolean |
| previous | null 或 AssessmentSnapshot |

RiskModule：id/name/description/status/points/summary/checks/evidence。status 是 `clear | watch | risk`；check.result 是 `pass | warn | fail | unknown`，均不是后端任务状态。

模块 ID：invoice_integrity、buyer_verification、seller_verification、transaction_plausibility、relationship、payment_behaviour、duplicate_financing。

EvidenceItem：field/value/label/detail/source/confidence/addedAt；source 为 analyst_note/upload/reference_data，confidence 为 user_provided/document/verified，没有 file_id、run_id 或下载地址。

AssessmentSnapshot：version/score/band/recommendation/modulePoints/moduleSummaries。后两个以 ModuleId 为 key。后端 `last_valid_result` 不必然表示紧邻的上一版本，需单独定义版本变化来源。

## 错误与请求示例

旧错误格式为非 2xx 的 `{"detail":"readable message"}`。断网展示后端地址；成功但非 JSON 的响应会变成 `{}`，存在运行时异常风险。

现有后端格式是 `{"error":{"code":"...","message":"...","retryable":false,"details":{}},"request_id":"..."}`。后续应保留状态码、code、details、request_id；409 刷新快照且保留草稿，422 显示字段问题，503 允许重试。

```bash
# 仅适用于实现旧四接口的兼容服务，不适用于当前 /v1 契约。
curl -X POST 'http://localhost:8000/api/assessments/ASM-example/reassess' \
  -F 'module_id=seller_verification' \
  -F 'note=Supplier confirmed the new account' \
  -F 'files=@/absolute/path/bank-letter.pdf'
```

## 可用样例

下列文件来自实际执行原型的 demoInvoice、computeAssessment、interpretSubmission，固定本次基线，不宣称符合 `/v1` Schema：

- [完整抽取结果](fixtures/frontend-extracted-invoice.json)：全部 10 字段。
- [初始评估](fixtures/frontend-assessment-v1.json)：23 / Medium / 71%。
- [确认卖方后](fixtures/frontend-assessment-v2.json)：9 / Low / 86%，含 v1 摘要。
- [补 PO 后](fixtures/frontend-assessment-v3.json)：5 / Low / 100%。

后端 Case 1/2 的 Workspace 应读取 `../deliverables/apexvibe5-handoff-v1/examples/`（相对前端工程根），不要混用两个演示策略的数据。
