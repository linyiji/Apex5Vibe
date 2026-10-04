# API 行为契约

以 `contracts/openapi.json` 为机器可读入口，base path `/v1`。JSON采用snake_case。风险只有LOW/HIGH/null。金额为十进制字符串。主键为不透明字符串；客户端不得按演示编号猜测记录。

## 核心接口

| 方法 / 路径 | 意图 |
|---|---|
| GET /capabilities | 解析格式、限制、执行模式和策略版本 |
| GET /entities | Select existing 的本地实体列表 |
| POST /cases | 创建Case，包含独立Buyer/Seller选择 |
| GET /cases | Queue，筛选状态或LOW/HIGH |
| GET /cases/{case_id} | 最新Workspace快照、模块摘要、导航信号 |
| POST /cases/{case_id}/invoice | 上传/显式替换主发票并排解析任务 |
| PATCH /cases/{case_id}/parties | 解决主体冲突或修订选择 |
| POST /cases/{case_id}/assessments | 开始初次评估；初次批次已开始则返回现有批次或409 |
| GET /cases/{case_id}/modules/{module_key} | Full view，包括证据、说明、运行历史、评分和动作 |
| POST /cases/{case_id}/modules/{module_key}/evidence | 上传目标模块补充文件 |
| POST /cases/{case_id}/modules/{module_key}/supplements | 保存文字，可原子地申请重跑 |
| POST /cases/{case_id}/modules/{module_key}/runs | 仅重跑目标模块 |
| GET /cases/{case_id}/modules/{module_key}/runs/{run_id} | 查看指定历史运行的完整输入、输出与错误 |
| POST /cases/{case_id}/modules/{module_key}/adjustments | 设置当前人工调整（0表示撤销生效值） |
| GET /jobs/{job_id} | 任务状态与可重试错误 |
| GET /cases/{case_id}/events?after_seq= | 游标读取审计/变更事件 |
| GET /cases/{case_id}/files/{file_id} | 同Case证据文件下载/预览 |

方法与路径均在OpenAPI内定义。SSE未来可新增独立流端点，当前events接口是JSON，不要把轮询响应当SSE。

## 幂等和乐观并发

所有POST以及PATCH都要求 `Idempotency-Key`。作用域为本地当前操作者+HTTP方法+规范化path+key，保存24小时。相同key且相同body返回原响应；不同body返回409。文件请求body_hash由文件sha256、规范化form字段和顺序构成；不要以multipart边界值构成哈希。

Case变更请求带expected_case_revision，模块变更带expected_module_version。模块input_version不作为通用UI行锁。版本不一致时409 VERSION_CONFLICT并返回当前版本；前端拉新快照后让用户重试，不静默覆盖。

响应体返回稳定资源ID，异步接收时包括job_id与job状态。201仅用于同步创建Case或人工调整等已完成写入；解析、初评、重跑、Save&Re-run均用202。纯保存文字也统一202，job可以null，语义是请求已接受，模块尚待再评估。

## 文件与正文

主发票与模块证据用multipart，字段见OpenAPI；文字说明、选择、重跑、人工调整用application/json。不要把本地电脑绝对路径当上传成功，也不要把file.name作为证据内容。上传成功返回file_id，后续引用使用该ID。

模块输出必须符合schemas并通过领域校验：ai_score在该模块cap范围内、分数等于matched_rules之和（同组只取一档）、引用必须存在于本次输入快照、case_id/module_key一致。JSON Schema不能代替跨字段业务检查。

## 错误

统一结构：`{"error":{"code":"VERSION_CONFLICT","message":"模块已更新，请刷新后重试","retryable":false,"details":{}},"request_id":"req_demo_001"}`。

| HTTP | code | 前端动作 |
|---|---|---|
| 400 | INVALID_REQUEST | 显示输入问题 |
| 404 | CASE_NOT_FOUND / FILE_NOT_FOUND | 回列表或保留错误页 |
| 409 | VERSION_CONFLICT / RUN_ALREADY_ACTIVE / IDEMPOTENCY_CONFLICT | 拉最新状态，保留用户草稿 |
| 413 | FILE_TOO_LARGE | 提示大小限制 |
| 415 | UNSUPPORTED_PARSER | 提示实际可用格式 |
| 422 | VALIDATION_ERROR / INVOICE_NOT_READY | 显示字段或缺资料详情 |
| 503 | ANALYZER_UNAVAILABLE | 显示重试，不能自动降成LOW |

`needs_info`是成功执行后的业务结果，不必作为HTTP500。异步任务失败在job/module状态里报告，原202不改写。

## 本地访问

Demo默认只绑定loopback，`actor_id=local_demo_analyst`由本地服务注入。前端不能提交任意actor_id；如果将服务开放给局域网/公网，必须先接真实认证与Case访问控制。CORS只允许配置的前端origin。API密钥只放后端.env，不出现在NEXT_PUBLIC变量或返回JSON。

本包的OpenAPI已可供mock和类型生成；后续FastAPI服务生成的/openapi.json应与之做差异检查。健康检查、内部管理及真实鉴权可在实施时补充，不作为当前展示的业务接口。
