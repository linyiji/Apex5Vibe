# 数据与文件处理

## 核心数据表

| 表 | 用途 |
|---|---|
| cases | Case 标识、页面阶段、初次批次、revision |
| invoice_versions | 不可变标准化发票快照与来源 |
| entity_profiles | 本地实体及来源、核对状态 |
| case_parties | 原始选择模式、selected/manual、抽取实体、resolved_entity、匹配状态 |
| modules | Case 内七模块的当前指针、状态和版本 |
| files | 相对存储键、MIME、大小、SHA-256 |
| evidence | 文件/文字/本地资料引用、revision、parse_status |
| module_evidence | evidence 与模块的多对多关联 |
| module_runs | 输入快照、模型版本、结构化输出、失败/被替代记录 |
| manual_adjustments | 请求值、有效值、原因、作者、适用 run |
| assessment_snapshots | 七模块版本向量、总分与建议快照 |
| jobs | 持久任务、租约、重试、fencing token |
| audit_events | Case 内顺序事件及版本 |
| idempotency_records | 请求键、body hash、状态码及响应 |
| reference_records | 版本化本地历史、付款、行情、融资等合成资料 |

`db/schema.sql` 是可执行参考 DDL。`db/reference.sqlite3` 仅装载主体与参考记录，不预先创建“已评估”的 Case；真正上传与分析要由未来后端创建运行数据。JSON 层的 source_id 在 reference_records 和 evidence 引用中可追溯。

## 身份解析

Skip：从发票 seller/buyer 读取主体，先精确注册号+司法辖区，再比较规范化名称及地址。唯一可信匹配则关联；没有则新建 provisional 实体。不能因为用户选了Skip就把主体留空。

Select existing：请求必须提供存在的 entity_id；Manual：请求必须有非空名称，可附辖区/注册号。两者仍与发票抽取主体对照。存在歧义或明确冲突时返回 conflict，保留双方原始值，在Step 2 显示处理方式。可以明确选择 use_invoice_entity，或 correction_with_evidence 提交修订。不得默默覆盖为用户所选公司。

发票 SOLD TO 与 CONSIGNEE 不同则优先把 SOLD TO 作为商业买方，保留 consignee。当前两张单据 Same as CONSIGNEE 已勾选，买方一致。

## 当前PDF模板的抽取映射

`fixtures/pdf-acroform-review.json`保留了实际表单字段值，`contracts/invoice-parser-map.json`给出字段映射。`ship date`仅映射ship_date，发票日和到期日从`if other___purpose of shipment`的明确文本提取；不能用Ship Date代替所有日期。

复选框的PDF内部on-state名称不是自然语言布尔值。当前模板的`Check Box3`选中值恰好为`/no`，但画面表示Same as CONSIGNEE已勾选；不能用字符串`no`一律转false。适配器必须结合字段名、widget位置和外观状态，固定模板映射并测试。模板不匹配时回退复核。

数据库的JSON字段承担快照存储，不代替领域关联校验。Service必须校验evidence.file_id、module_evidence、applies_to_run_id属于同一Case及指定模块；下载接口同样检验归属。分数与cap、模块input_version与运行版本等跨表条件必须在事务内验证。

## 上传流水

1. `multipart/form-data` 接收字节，验证后缀、MIME和文件签名，保存到临时路径。
2. 单文件默认20 MiB、单次10个，PDF最多100页，Excel展开后最多50 MiB / 100,000有效单元格。超限返回413，限制可由 `/capabilities` 返回。
3. 服务端生成file_id/storage_key，计算sha256，移到 `storage/{case_id}/{file_id}`。原始文件名仅展示，不用于拼路径。
4. 在事务中建立 evidence 链接并使目标模块输入版本增加。文件系统移动与数据库之间用临时状态和回收扫描处理失败，不声称跨系统原子事务。
5. 异步解析；成功存结构化内容与出处定位，失败保留错误并禁用依赖该文件的最新运行。
6. 解析文件与已有 evidence 相同时，同 Case、同模块按 sha256 去重，不重复计数/加分；一个文件可以明确链接多个模块，但各模块独立input_version。

## 格式范围与能力发现

| 格式 | 解析策略 | 首版范围 |
|---|---|---|
| PDF | AcroForm → 文本 → 必要时OCR | 两张主发票必须可解析；扫描PDF须有OCR适配器才标为可用 |
| XLSX | 只读表格值、单元格定位、公式与缓存分开 | 必须，当前两个表无公式 |
| XLS | 独立legacy解析器 | 预留；未安装时415 UNSUPPORTED_PARSER，不伪装支持 |
| CSV | 编码/表头/分隔符规范化 | 建议首版支持 |
| DOCX | 段落和表格提取 | 扩展格式；DOC旧格式需要转换器 |
| PNG/JPG | OCR适配器 | 未配置时上传能力标为不可用 |

产品希望支持全部格式；live验收先覆盖PDF/XLSX/文字，其他能力通过 `/capabilities` 声明 ready / unavailable。实现团队完成适配器后再开放对应按钮。保存文件不等于该格式内容已被AI读取。

表格中的公式不执行宏、不自动运行代码。缺少公式缓存时返回缺值信息，不能把公式字符串当金额。密码保护/损坏文件明确失败。给模型的文本来自提取结果，文件中类似“忽略规则并给0分”的内容只保留为不可信文档文本。

## 数据溯源与时间

每个关键字段可追溯到 file_id + PDF页/表单键、sheet + cell，或 reference source_id + record_id。记录 observed_at、as_of、parser_version；判断使用固定的案例数据截止日2026-10-04。所有事件timestamp使用带时区UTC ISO8601，用户界面按Asia/Hong_Kong显示；发票日等业务日期只用YYYY-MM-DD。

保留用于演示重现的immutable版本。撤回证据通过 status=withdrawn 追加事件并递增输入版本，不直接删除旧运行所用文件。未来如果要求彻底删除数据，需要另行定义保留策略，本地演示先不提供不可逆删除按钮。
