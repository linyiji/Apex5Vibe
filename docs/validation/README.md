> Historical backend-only acceptance. The current English PC Web integration is documented in [Live browser acceptance](../../frontend/docs/05-live-integration-verification.md). The code and case IDs below identify the earlier baseline.

# 本地后端验收记录

日期：2026-10-04。功能代码版本：`f6d81501823ecbccf46563ced404703a4e8e348d`（本地提交，未推送）。逐文件校验值见 [backend-source-hashes.json](backend-source-hashes.json)。结构化记录、Run ID、模型返回 ID、引用和实际输出见 [local-live-acceptance.json](local-live-acceptance.json)。

## 执行结果

| 验证 | 执行模式 | 结果 |
|---|---|---|
| `pytest backend/tests -q` | 隔离临时 SQLite、测试分析器、无模型网络调用 | 27 通过，0 失败 |
| `scripts/live_case1.py --verify-rerun --report runtime/live-case1-v2.json` | 实际 HTTP API + Worker + TeamRouter | 7 模块初评 + Excel/文字局部重跑，9 次模型调用通过 |
| `scripts/live_case2.py` | 实际 HTTP API + Worker + TeamRouter | 初评 + Errors + Corrected，9 次模型调用通过 |
| OpenAPI 3.1、实际 Workspace/Run 响应验证 | JSON Schema / OpenAPI validator | 通过 |
| 服务与 Worker 重启恢复 | 读取原 SQLite | 两案最终分数、有效版本、运行历史均保留 |

真实调用请求和返回模型均为 **gpt-6.1-sol**，通过 `https://api.teamorouter.com/v1/chat/completions`。本轮两案共 18 个成功模型运行，Job attempt 均为 1，无自动模型回退。AI 只接收后端选定的本地快照；未提供搜索工具。测试替身仅用于离线测试，不作为真实分析证据。

pytest 有 1 条依赖弃用提示：Starlette 提示未来 TestClient 应迁移到 httpx2；没有失败项。当前测试环境由 requirements-dev.lock 固定。

## Case 1

Case ID：`case_07ca2fd5a5d54f15a1b32383ed202669`。

实际结果 **5 → 5 → 5 LOW**：付款历史5分，其余六项0分，主发票 GBP 8,000.00，eligible，80% 演示预支额度 GBP 6,400.00。Excel 仅重跑 invoice_integrity；文字仅重跑 payment_history；未修改其他模块 Run。

此前第一版真实闭环记录另保留在 `case1-live.json`，对应最初 Case ID 和19项离线基线；本页27项及上述 Case ID 是补充规格后的复测。

## Case 2

Case ID：`case_8bcdeffc8a7745ddb23f1288c5ef8c3e`。

| 阶段 | 总分 | 完整性分 | 结果 |
|---|---:|---:|---|
| PDF 初评 | 35 HIGH | 0 | manual_review |
| Errors 字段表 | 50 HIGH | 15 | manual_review |
| Corrected 显式替代 | 35 HIGH | 0 | manual_review |

模型准确指出：Invoice Fields!C25 香港买方地址与 PDF 英国地址冲突；C51 的 GBP80,000 与 PDF、6,250×8、小计50,000和零费用冲突。Corrected 后模型说明地址/金额一致，算术检查通过。主 PDF 始终 GBP50,000，其他六模块 Run ID 不变；关系模块30分仍保留。

- 错误证据：`file_d4caa1b2696a422d9c683d8805aa51a1`；错误分析 Run：`run_f61ae4e51d314823aa6a4c9fa2bf2ff7`。
- 当前有效修正版：`file_32314c97810f4439aa41436471c00b05`；修正分析 Run：`run_ea8cf10fc1544eb68aba03d124833f4b`。
- 旧证据状态 superseded、新证据 active；原文件可下载，历史输入及输出可查看。

完整响应样例保存在 `contracts/examples/`，包含初评/错误/修正 Workspace 和两次目标模块 Run。原始完整验收输出在本机 `runtime/live-case1-v2.json`、`runtime/live-case2.json`，不打包密钥或运行数据库。

## Historical scope boundary

此记录描述联调前的后端基线；后续英文 PC Web 联调结果见下方入口。GitHub 尚未上传。当前支持指定 AcroForm 主发票及 PDF文本/XLSX/CSV 补件，不支持任意扫描件 OCR、XLS、Word、图片、登录或生产放款。所有发票、主体与历史资料是合成演示数据。
