# 第一期补充规格的后端实现

对应原始补充文档 `requirements-phase1-local-data.md`，其中保留接手时描述和历史测试数量。当前实现及验收以本文和 `validation/` 为准。本轮仅本地后端测试，未进行前后端联调或 GitHub 上传。

## 参考资料筛选

`references.select_reference` 在保存 Run.input 前执行。主体匹配 entity_id 和已验证状态；交易匹配双方、SKU、币种、已完成状态及观察窗口并排除当前发票；市场匹配 SKU、单位、币种、贸易条件、交货地点及适用时间；付款匹配买方、币种及窗口；融资匹配同笔发票各身份/金额/日期字段，仅保留有效未结清记录及台账覆盖声明。

参考快照不晚于策略 as_of。交易/付款截止日为 `min(as_of, invoice_date - 1 day, record.window_end)`，起点为资料 window_start，缺省为 as_of 当年 1 月 1 日。演示时点固定为 2026-10-04。缺必需可比资料时直接返回 needs_info，provider=local_validation、model=null；不调用 AI 猜测，不计零分。模型只收到选中的本地快照，没有搜索工具。

## Excel 字段表

定位 `Invoice Fields` 工作表的 `Section / Field / Value / Unit` 表头，按 B 列 Field 键映射 C 列 Value；行号只用于引用。保存 source_id、sheet、cell、原始值、规范化值和 Unit。金额用 Decimal 字符串；整数、日期、布尔值显式转换；0 与缺失区分。重复字段、缺必填、错误类型和公式显式失败，其他字段保留。

`field_sheets.py` 针对单行商品模板生成 `field_sheet.fields / differences / checks`；PDF facts 增加 `deterministic_checks`。验证数量×单价、明细合计、小计+费用和付款日期差。附件不覆盖 PDF。每次 Run 都按当前 PDF 重算差异，避免主发票更换后沿用旧比较。

Errors 的 C25 为香港买方地址，与 PDF 英国地址冲突；C51 总额 80,000 与 PDF、6,250×8、小计和零费用得出的 50,000 冲突。AI 根据实际差异解释并选规则，一个模块只取一条最高规则，不按冲突数量重复加分。

## 显式替代 API

POST `/v1/cases/{case_id}/modules/invoice_integrity/evidence`，multipart：

| 字段 | 首次上传 Errors | 上传 Corrected |
|---|---|---|
| files | 真实 XLSX 字节，单文件 | 真实修正版字节，单文件 |
| expected_module_version | 最新 GET 返回值 | 重新 GET 的最新值 |
| rerun | true | true |
| evidence_group | invoice_field_sheet | invoice_field_sheet |
| supersedes_evidence_id | 省略 | Errors 的 evidence_id |

每次新操作使用新 Idempotency-Key，网络重试复用同键和 Body。`invoice_field_sheet` 仅允许在 invoice_integrity 上传 XLSX。普通补件可不分组，此时不自动替代旧文件；需要版本管理的附件应始终带稳定分组。

Evidence 增加 `evidence_group / version / supersedes_evidence_id`；status 包括 pending、active、failed、superseded。SQLite 唯一索引限制同组最多一个 active 和一个 pending。

1. 保存候选文件和替代关系，模块 stale，当前融资 pending，旧证据仍 active。
2. 解析和字段验证失败：候选 failed，旧证据 active，模块 needs_info，不调用 AI。
3. 成功后同事务将旧版本和已恢复的失败候选归入 superseded，再激活新版；所有原件、指针、运行历史保留。
4. 只用 active 证据构建 AI 快照，不混用新旧字段表。AI 成功后才更新当前结果；AI 失败时新版证据仍 active，但评分非 current。

上传受理时 input_version 递增，用于阻止运行中的旧任务提交；解析激活时再递增以绑定有效内容变化。版本差不是文件数量。module_version 还随状态变化，用于提交乐观锁。

同内容改名复用当前 active/pending evidence，不重复添加或计分；rerun=true 可显式重跑同一证据。不同内容同名创建新版本；有旧版本时必须显式指定替代关系。目标必须同 Case、同模块、同组且 active，错误/并发替代返回 409。解析失败可再次指定旧 active evidence 上传有效修正版恢复。

## 验收与范围

离线测试见 `backend/tests/test_case2_replacement.py`，真实模型验收见 `scripts/live_case2.py` 和 `validation/`。预期：Case 2 关系30+付款5=35；Errors 完整性15，总分50；Corrected 完整性0，总分35。主金额始终50,000，其他六模块 run_id 不变，不自动重跑买方验证。

前端仍需接入 /v1、真实字节上传、替代字段和轮询。通用无分组失败附件尚无删除接口。未实现 OCR、外部资料查询、登录或生产放款。
