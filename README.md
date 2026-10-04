# ApexVibe5 — Modular Assessment Backend

本地发票风险评估后端。FastAPI 提供 API，SQLite 保存业务数据，独立 Worker 调用 TeamRouter 的 **`gpt-6.1-sol`**，按七个模块生成带证据引用的分析。风险指数 **越高越危险**：`< 30 → LOW`，`≥ 30 → HIGH`。

本次交付范围是后端、Case 1 闭环测试及前端接入契约。仓库中的 `frontend/`（如已另行放入）是独立工作，不属于本次后端实现。历史架构资料位于 `deliverables/apexvibe5-handoff-v1/`；实际运行接口以 **[`contracts/openapi.json`](contracts/openapi.json)** 为准。

## 本地启动

需要 Python 3.12，以下命令在仓库根目录运行：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps -e .
cp .env.example .env  # 仅首次；已有 .env 时不要覆盖
```

在 `.env` 填入 `TEAMROUTER_API_KEY`。默认地址为 `https://api.teamorouter.com/v1`，模型为 `gpt-6.1-sol`，使用 OpenAI 兼容 Chat Completions 接口。密钥只在后端读取，`.env` 被 Git 忽略。

```bash
python -m apexdefend.manage init
uvicorn apexdefend.api:create_app --factory --host 127.0.0.1 --port 18080
```

另开终端，进入仓库并激活同一虚拟环境：

```bash
python -m apexdefend.worker
```

- API / Swagger：<http://127.0.0.1:18080/docs>
- 健康状态：<http://127.0.0.1:18080/health>
- SQLite：`runtime/apex.sqlite3`；原件：`runtime/files/`
- API 与 Worker 必须使用同一 `.env` / `APEX_DATA_DIR`。修改模型配置或密钥后，两者均需重启。

## Case 1 真实闭环

```bash
python scripts/live_case1.py --verify-rerun
```

脚本通过实际 HTTP API 创建 Case，上传原始 PDF，等待解析，执行七个 AI 模块，验证自动进入结果页，再分别上传原始 Excel、补充文字，验证仅目标模块重跑。每次执行创建一个新 Case，产生真实 TeamRouter 调用；没有 Mock 回退。

预期结果：发票 `CV-2026-1002-001`、GBP 8,000.00、风险指数 **5 / 100 LOW**、`eligible`、80% 演示预支额度 **GBP 6,400.00**。预期来自公开的合成参考数据和演示计分规则，服务端没有按文件名或 Case 编号硬编码结果。任何断言失败都会保留运行记录并以非零状态退出。

详细输出保存到 `runtime/live-case1.json`。实际验收记录见 [`docs/validation/`](docs/validation/)。Case 2 原件及架构样例保留，本阶段以 Case 1 真实闭环为验收范围。

## 已实现的行为

- Buyer / Seller 各自支持 Skip、Existing、Manual；跳过时从发票识别并匹配/创建本地实体；主体冲突需明确解决。
- 七个模块独立保存输入版本、AI 运行、证据、文字说明、人工调整、状态及审计事件。
- 补件或文字使对应模块过期；`rerun=true` 保存并重跑，`false` 仅保存；其他模块的有效结果保留。
- AI 根据当前证据选择规则并提供引用；后端验证结构、引用和规则，映射分数并聚合。人工调整独立保存，AI 重跑后需要重新确认。
- 初评批次全部结束后 `navigation.target=result`；失败与缺资料也结束等待，但不生成虚假的零分或 Low 结果。
- 持久任务队列、有限重试、租约恢复、旧任务提交保护、版本冲突检查与请求幂等。
- PDF 发票表单解析；PDF 文本、XLSX、CSV 补件。未实现的 XLS、Word、图片/OCR 在 capabilities 中明确标为 unavailable。

## 验证与交接

```bash
ruff check backend scripts
ruff format --check backend scripts
pytest
python scripts/export_openapi.py --check
```

自动化测试使用仅存在于 `backend/tests/` 的分析器替身，验证业务、存储、并发及契约；**不等同真实模型验收**。真实验收使用上面的 `live_case1.py`。GitHub Actions 运行离线测试，不需要 TeamRouter 密钥。

- [后端实现与数据流](docs/backend-implementation.md)
- [前端接入说明](docs/frontend-integration.md)
- [演示与排错](docs/demo-runbook.md)
- [实际 OpenAPI](contracts/openapi.json)
- [完整历史架构包](deliverables/apexvibe5-handoff-v1/README.md)

当前是单机展示服务：默认仅监听 loopback，使用固定的本地演示分析师身份，不含用户登录、多租户或生产部署。源发票、主体档案、交易与付款记录均为合成数据；融资输出用于演示。
