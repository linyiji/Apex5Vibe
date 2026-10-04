# 后端联调准备

状态：前端目录与基线验证已准备；真实联调未实施。日期：2026-10-04。

产品范围（用户已确认）：仅 PC 浏览器 Web 端。以下实施顺序与验收清单均以 PC 使用场景为准；移动端布局与兼容性不属于联调任务或阻塞项。

对照资料为工作区的 [OpenAPI 3.1](../../deliverables/apexvibe5-handoff-v1/contracts/openapi.json)、[前端交接](../../deliverables/apexvibe5-handoff-v1/docs/08-frontend-handoff.md)、[评分策略](../../deliverables/apexvibe5-handoff-v1/contracts/risk-policy.json) 及 `backend/src/apexdefend/config.py`。这些资料描述目标契约，不等于服务已运行或已验收。文件校验值记录在 source-manifest.json。

建议以现有 `/v1` 契约作为下一阶段的对接基线，保留当前界面布局，改造数据与状态层；最终契约冻结前不擅自选择另一套业务规则。不要为了适配原型，将后端规则降回三档风险或删掉任务/版本信息。

## 1. 契约差异

| 项目 | 当前前端 | 工作区后端契约 | 联调动作 |
|---|---|---|---|
| 基路径 | `/api` 四接口 | `/v1` Case / Module / Job 资源 | 新增 v1 client，分开 transport 与 Mock |
| ID | 本地 case ID + assessment ID | 后端 case_id / run_id / job_id | URL 与数据恢复使用后端 case_id |
| 上传顺序 | 上传抽取 → 本地 Case | 创建 Case → 上传发票 → 解析任务 | 改造首页与 Review 加载状态 |
| 主体输入 | 两个名称文本框 | 买/卖双方独立 Skip / Existing / Manual，且有冲突处理 | 增加主体选择与解决界面 |
| 初评 | 一次 POST 返回完整结果 | 202，异步初始批次和 Workspace | 轮询 job/Case，settled 后进入结果页 |
| 模块 | 含 transaction_plausibility / payment_behaviour | 含 market_price / payment_history | 按业务语义迁移，见下表 |
| 风险 | low≤10、medium≤25、high>25 | LOW<30、HIGH≥30；未出分为 null | 消除硬编码三档文案和颜色映射 |
| 建议 | eligible / manual_review / decline | eligible / manual_review / pending | 以 API decision 为准，不把 HIGH 当 decline |
| 缺资料 | 加分且仍有总分，可出现初步 eligible | needs_info，当前总分可能不可用，decision=pending | 支持 null、pending、上次有效结果 |
| 模块分 | 一个 points | ai_score / requested_adjustment / effective_adjustment / final_score | 扩展卡片和人工调整展示 |
| 状态 | clear/watch/risk 展示标签 | 执行 state + freshness + adjustment_status | 不把展示标签当任务状态 |
| 再评估 | 备注和文件同请求，整体新 Assessment | evidence / supplements / runs 分开，局部失效重跑 | 顺序保存并传版本；只更新目标模块 |
| 金额 | 文本转 number，默认四舍五入到整数 | 十进制字符串，如 `6400.00` | 展示后端值，保留精度，不重新计算额度 |
| 错误 | `{detail}` | `{error:{code,message,retryable,details},request_id}` | 统一错误对象，按错误码反馈 |
| 写入保护 | 无 | Idempotency-Key + expected revision/version | 每个逻辑动作稳定 key，重试复用 |
| 历史 | sessionStorage | 服务端 Queue / runs / events | API 恢复、历史分页和审计入口 |
| 文件 | object URL / 文件名 | file_id、解析状态、下载接口 | 真实字节上传与持久预览 |
| 格式/大小 | 主发票 15 MiB，附件无统一约束 | capabilities 返回 formats / max_file_bytes / max_files_per_request | 根据能力动态限制 |
| 操作权限 | 固定按钮 | allowed_actions | 根据服务端动作列表显示与禁用 |
| 策略标识 | 固定 Mock 文案 | engine_mode / policy_version | 显示实际执行模式，保留来源 |

当前 Mock 分数和后端 Demo 属于不同案例策略。前端 23→9→5 不能作为后端 Case 1/2 的预期。后端资料的参考结果是 Case 1 = 5/LOW、GBP 6,400.00，Case 2 = 35/HIGH、manual_review、无建议额度。

### 本次收尾时可见的后端实现补充

只读检查 `backend/src/apexdefend/api.py` 已可见 `/v1` 路由和额外 `/health`，没有上述四个 `/api` 兼容路由。本次未启动、修改或验收后端；其源码后续可能继续变化。

- 当前 capabilities / Workspace 的 `engine_mode` 为 `llm`，没有证据表明已提供可切换的 demo_replay 服务；固定数字先用于契约样例验收，真实 AI 执行另验。
- capabilities 当前多返回 `model`，而交接包 Capabilities Schema 使用 `additionalProperties=false` 且未定义 model。冻结契约时需明确同步 Schema 或调整响应，不能直接假设生成类型完全一致。
- 默认单文件 20 MiB、每请求最多 10 文件；capabilities 仅 PDF/XLSX/CSV 标为 ready，图片及 DOC/DOCX/XLS 不可用。
- `parse_invoice` 检查特定 PDF AcroForm 字段/模板，普通 PDF、扫描图片和前端本地虚构 Demo 并不等价于可解析的主发票。证据支持格式与主发票模板能力应分开表达，并处理 UNSUPPORTED_INVOICE_TEMPLATE。

这些结论来自静态源码，不是 HTTP 调用结果。联调前应再次比对运行服务的 `/openapi.json` 与交接契约。

## 2. 七模块对应

| 原型 ID | 后端 ID | 注意事项 |
|---|---|---|
| invoice_integrity | invoice_integrity | 同名，输出要增加规则、引用、状态和版本 |
| buyer_verification | buyer_verification | 用主体匹配/档案结果代替固定文案 |
| seller_verification | seller_verification | 原型 16/26 分超出现有后端 cap=10，不能照搬银行变更规则 |
| transaction_plausibility | market_price + relationship 的部分语义 | 不可只重命名；市场单价、历史交易规模、PO 缺失需重新归属 |
| relationship | relationship | 后端同时处理关联与历史交易规模异常 |
| payment_behaviour | payment_history | 可调整标识，但贡献分与规则不同 |
| duplicate_financing | duplicate_financing | 需要展示确认重复融资的硬阻断，不能只展示分数 |

完整性百分比、风险原因 drivers、extracted/uncertain/edited、紧邻版本 previous，并非后端 Workspace 的一一对应字段。可从明确的字段构造展示模型；没有来源时应隐藏或扩展契约，不能制造默认值。原型全部字段可编辑，但现有契约没有通用 `PATCH invoice`，只有主体修订及发票替换：这是联调前必须明确的缺口。

## 3. 目标请求顺序

路径均相对 `/v1`：

1. GET `/capabilities` 和 `/entities`，确定格式、限制、执行模式与主体选项。
2. POST `/cases`，发送独立 buyer/seller 选择，取得 case_id 和 revision。写入带 Idempotency-Key。
3. POST `/cases/{id}/invoice`：multipart file、replace、expected_case_revision，接收 202/job_id。
4. GET `/jobs/{job_id}` / `/cases/{id}` 等待解析，展示实际发票与来源。主体冲突用 PATCH `/cases/{id}/parties` 解决。
5. 字段修订保存方式确定且 Invoice ready 后，POST `/cases/{id}/assessments`，传 expected_case_revision，接收 202。
6. 轮询 Workspace 展示各模块，初始批次 settled 后进入结果页；failed/needs_info 也能结束批次并显示结果状态。
7. GET `/cases/{id}/modules/{key}` 取详情；证据 POST evidence、文字 POST supplements、重跑 POST runs，按最新 module_version 串行提交。
8. 补文件和备注组合操作需确定是否合并事务；现有 endpoints 不能直接复现旧“一次 multipart 同交文字与文件”。避免提前 rerun 后再写另一半导致重复执行。
9. 人工调整 POST adjustments，绑定当前成功 run、reason 与版本；不能覆盖原 AI 分，也不在前端本地加减。
10. GET cases / events / files / run detail 恢复列表、审计和原件。events 当前为 JSON 游标读取，不是 SSE。

轮询建议遵循现有交接：活动时约 1 秒，失败退避 2/5 秒，稳定后停止高频轮询。切 Case 或卸载时取消请求；丢弃旧 case_id / revision 的晚到结果。初次自动跳转仅针对当前 Case；局部重跑保持在结果页。

409 VERSION_CONFLICT 时拉新快照、保留草稿；不要静默覆盖。任务失败、后端断开都不应回退 Mock 成功或自动显示 Low。上传需要发送字节，不能只发送本地路径或文件名。

## 4. 本地地址与配置

| 来源 | 当前值 |
|---|---|
| 前端旧 `.env.example` | `http://localhost:8000`，只适用于旧 `/api` 分支 |
| 后端 OpenAPI 示例 server | `http://127.0.0.1:8000/v1` |
| 后端 Settings 默认端口 | `18080`，可由 APEX_PORT 覆盖 |
| 后端默认 CORS | `http://localhost:3000` |
| 本次前端验证 origin | `http://127.0.0.1:3000` |

正式联调必须确认实际服务地址。`localhost` 与 `127.0.0.1` 是不同 CORS origin；可以统一使用 localhost 或在后端允许准确的两个开发 origin。本次未修改后端配置。现有 `api.ts` 还不会调用 `/v1`，不要提前把 BASE_URL 改为 `/v1` 后误以为已完成适配。

后续服务就绪后可先只读探测（此命令本次未作为真实后端验收执行）：

```bash
curl -i http://127.0.0.1:18080/v1/capabilities
curl -i http://127.0.0.1:18080/v1/cases
```

AI 密钥只留在后端环境，不放 NEXT_PUBLIC 变量。当前前端仅按本地开发准备，鉴权与对外部署属于后续服务范围。

## 5. 按顺序开展的工作

| 顺序 | 任务 | 主要文件 / 产出 |
|---|---|---|
| P0-1 | 冻结 OpenAPI/风险规则/模块定义/字段编辑方式/补件事务与地址 | 双方确认契约，不复制原型评分 |
| P0-2 | 分离 v1 DTO、HTTP transport、展示转换、Mock | 建议 `lib/backend-types.ts`、`lib/http.ts`、`lib/backend-api.ts`、`lib/view-model.ts`；当前尚未创建 |
| P0-3 | 服务端 Case 创建、上传、解析、主体选择/冲突、刷新恢复 | 首页、评估页、case-store、表单 |
| P0-4 | job/Workspace 轮询及 nullable/current/stale/incomplete 显示 | ProcessingState、Summary、RiskScore、模块卡片 |
| P0-5 | 按版本补件、局部重跑、409 与任务失败 | AnalystInput、DecisionView、错误展示 |
| P1-1 | Module Full view、原件、运行历史、人工调整与审计 | 模块详情、证据列表、文件组件 |
| P1-2 | 服务端 Queue、分页/刷新、金额精度、模式与文案 | PastEvaluations、format、Header、Preview |
| P1-3 | 两案例联调和异常路径验收 | 按下表记录真实执行结果 |

可继续复用布局、上传交互、步骤条、折叠卡、笔记区和分值变化的视觉结构。`lib/types.ts` 的旧类型不能通过强制类型断言直接承接 Workspace；应新增 DTO 后逐步替换，避免丢掉错误、过期和未评估状态。

## 6. PC Web 端联调验收清单（全部待真实后端验证）

- [ ] capabilities 的可用格式、单文件大小与文件数限制反映到 UI。
- [ ] Buyer/Seller 的 Skip、Existing、Manual 可独立使用；冲突阻止不合法初评。
- [ ] 上传返回真实 file_id，解析失败/不支持格式/超限可恢复；刷新可打开原件。
- [ ] 未出分显示待评估；失败和 needs_info 不伪装为 0/LOW。
- [ ] 初评按真实模块状态推进，settled 后导航；切 Case 不发生旧请求跳转。
- [ ] Case 1 契约样例为 5/LOW/eligible/GBP 6,400.00；Case 2 为 35/HIGH/manual_review/无额度；参考样例先验证展示，真实服务另记录实际执行。
- [ ] LLM 模式单独验证输出契约与证据，不把参考 replay 数字当作任意 AI 运行保证。
- [ ] 只补目标模块资料时，目标变 stale；其他模块状态和历史保留。
- [ ] 局部重跑留在结果页，保留旧结果标识，当前无效时不继续展示可融资额度。
- [ ] 人工调整保留原 AI 分、请求/实际调整与 reason；过期调整需重新确认。
- [ ] 幂等重试不重复创建；409 保留草稿；400/404/413/415/422/503 有可理解反馈。
- [ ] 断网、取消、超时、任务失败可恢复；没有自动回退模拟成功。
- [ ] 刷新、重新打开与服务重启后按后端 Case 恢复；列表与详情一致。
- [ ] 金额保留必要精度；策略和 engine_mode 文案与后端一致。

完成本页准备不代表这些项目已验收。本次实际结果见 [验证记录](04-verification.md)。
