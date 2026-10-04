# ApexVibe5 架构与对接包

版本：1.0 · 2026-10-04 · 面向本地双案例演示和后续 Codex 实现。

本包是经过附件核对的**架构、数据及 API 契约交付**。包含可读取的 SQLite 参考数据库、两个案例 JSON、七个模块输入/输出样例与校验工具。**没有实现 FastAPI 服务、真实 AI 调用或 Next.js 前端，也没有部署到 GitHub。** 当前工作目录没有既有代码或 Git remote。

建议采用 Next.js 前端（后续团队提供）+ FastAPI 模块化单体 + SQLite + 本地文件存储 + 单 Worker。一次评估由七个可独立执行、留存版本和证据的模块组成。

## 阅读顺序

1. [整体逻辑与附件结论](docs/01-product-and-source-review.md)
2. [系统架构与技术选择](docs/02-system-architecture.md)
3. [状态机、局部重跑与并发](docs/03-state-and-rerun.md)
4. [评分与融资建议规则](docs/04-risk-policy.md)
5. [两个演示案例与数据来源](docs/05-demo-cases.md)
6. [数据库与文件处理](docs/06-data-and-storage.md)
7. [API 行为说明](docs/07-api-contract.md)，配合 [OpenAPI 3.1](contracts/openapi.json)
8. [Next.js 前端交接](docs/08-frontend-handoff.md)
9. [AI 接入与提示词边界](docs/09-ai-provider.md)
10. [实施顺序、演示和验收](docs/10-implementation-and-acceptance.md)
11. [需求追踪与待定项](docs/11-decisions-and-traceability.md)

`contracts/schemas/` 是严格 JSON Schema。`contracts/modules/` 为七个模块定义。`examples/case_1/`、`examples/case_2/` 含 invoice、每模块输入/输出和完整结果。`examples/actions/` 含局部重跑、补充文字、人工调整和错误等请求响应样例。`fixtures/` 保存有来源标签的合成历史数据。`db/` 含 DDL、种子 SQL 和 SQLite 参考库。`source/` 为用户提供的五份原始附件副本，原始文件未修改。

## 本版固定的产品语义

- 指数越高越危险，0–100；`LOW < 30`，`HIGH >= 30`；没有 MEDIUM。
- 未出结果的风险值为 `null`，显示“待评估”，不是第三种风险等级。
- AI 分析结果、人工调整、证据、运行历史分别保存。
- 原始发票金额、主体等公共字段变更影响相关模块；普通模块补件只使目标模块失效。
- 初次批次所有模块结束（包括失败/缺资料）后自动进入结果页；局部重跑留在结果页。
- 已绑定附件的**建议演示数据**得到 Case 1：5/100 LOW；Case 2：35/100 HIGH。High 依赖本包额外构造的历史交易基线，不是 PDF 自带结论。此前对话的 55 分未被附件证实，本版不沿用。

## 本包可执行内容

```bash
python3 scripts/reference_demo.py
python3 -m venv .venv
.venv/bin/python -m pip install -r scripts/requirements-validation.txt
.venv/bin/python scripts/validate_contracts.py
```

第一条只计算参考案例，不调用 AI。后两条校验 JSON Schema、OpenAPI、样例、SQLite 与评分不变量。校验结果见 `validation/report.json`。从 JSON 重建数据库可运行 `python3 scripts/build_reference_db.py --output /tmp/apexvibe5-reference.sqlite3`，已有目标文件会被拒绝覆盖。

如交给后续 Codex，先使用 `CODEX_HANDOFF.md`，再按验收用例完成实际后端。源码仓库建议提交本包文本、明确标为合成的数据与附件；运行时上传文件、真实数据、密钥、缓存与本地生成库应忽略。
