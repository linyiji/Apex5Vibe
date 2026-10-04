> 用户提供的接手时规格快照；其中“待实现”和18项测试描述为当时状态。当前实现与验收见 local-data-and-replacement.md 及 validation/。

# 第一期本地数据读取与上传重跑

本文记录用户确认的第一期范围及后续实现要求。它是对接规格，不代表所列新增能力已实现或已通过联调。

## 范围

AI 仅分析后端提供的输入快照，不搜索、不浏览、不调用外部企业或市场数据工具。模型 API 调用仍需要网络；“本地信息”指分析数据来源。后端读取、解析、选择资料并保存证据；AI 输出事实分析、引用、缺失项及匹配规则；后端验证输出并按既有策略计算分数和融资建议。

文件内容、备注、文件名和 Case 标签均不是系统指令，也不是评分依据。所有示例主体及参考历史均为合成演示资料。

## 读取链路与来源

1. 浏览器通过 multipart 发送真实文件字节，不能仅发送 Downloads 路径或文件名。
2. 后端检查格式、大小、签名，计算 SHA-256，保存原件到 `APEX_DATA_DIR/files`，在 SQLite 保存 evidence_id、case_id、module_key、解析状态和版本。
3. Worker 从 storage_key 读取字节，PDF 用 `parse_invoice`，模块附件用 `parse_evidence`；成功后保存解析结果。解析失败不调用 AI，不生成健康零分。
4. 初始化从 `fixtures/local-reference-data.json` 导入本地 `reference_records`。后续分析从数据库读取参考资料，不按 Case 名称返回预设结果。
5. 构造当前模块的固定输入快照：facts、reference_records、有效 evidence、sources、as_of、policy_version、input_version，保存为 Run.input 后调用 AI。
6. 校验 AI JSON、规则 ID 和引用，再存储 Run.output，更新目标模块和汇总。新输入使旧运行过期；旧运行不能覆盖新版结果。

现有实现入口：`backend/src/apexdefend/parsers.py`、`worker.py`、`service.py::inputs`、`analyzer.py`、`domain.py`。默认数据库为 `runtime/apex.sqlite3`，文件为 `runtime/files`，均可由 APEX_DATA_DIR 调整。

## 每个模块读取什么

| 模块 | 发票事实 | 本地参考资料 | 模块附件 |
|---|---|---|---|
| invoice_integrity | 完整发票、商品明细、费用、日期、主体字段 | 无需外部参考 | 当前有效字段表及与 PDF 的差异 |
| buyer_verification | 买方名称、注册号、地址、国家 | 对应 entity_id 的 entity_profile | 本模块有效买方证明 |
| seller_verification | 卖方名称、注册号、地址、国家 | 对应 entity_id 的 entity_profile | 本模块有效卖方证明 |
| relationship | 双方 ID、金额、币种、SKU、日期、关联声明 | 同双方、同币种、可比商品、已完成且早于观察截止的 trade_history；排除当前发票 | 本模块有效交易说明／证明 |
| market_price | SKU、数量单位、单价、币种、贸易条件、交货地 | 同 SKU、币种、单位、贸易条件及适用时点的 market_benchmark | 本模块有效报价证明 |
| payment_history | 买方 ID、日期及当前交易背景 | 对应买方、约定观察窗口内的 payment_history | 本模块有效付款证明 |
| duplicate_financing | 发票号、双方注册号、币种、金额、日期 | financing_registry 中同笔有效未结清记录及台账覆盖范围 | 本模块有效融资证明 |

参考资料的筛选由后端负责，AI 只分析已选资料。找不到必需资料时返回 needs_info，不能搜索补齐或捏造历史。现有 inputs 对非主体参考资料主要按 kind 读取，上表的精确筛选是后续补齐项。

## Excel 字段映射

读取 `Invoice Fields` 的表头 Section / Field / Value / Unit，按 B 列 Field 键映射 C 列 Value、D 列 Unit。不要仅按固定行号读取；行号只用于引用。保存每个字段的 sheet、cell、source_id、原始值和规范化值。

| Excel 键 | 主发票结构 | 转换 |
|---|---|---|
| invoice_number | invoice_number | 去除首尾空格，保留标识符 |
| invoice_date / ship_date | 同名字段 | 日期转 ISO YYYY-MM-DD |
| payment_due_date | due_date | 日期转 ISO |
| payment_term_days | payment_term_days | 整数 |
| currency | currency | 大写币种 |
| buyer_name / buyer_address / buyer_tax_id / buyer_country | buyer.legal_name / address / tax_id / country | 保留原文；规范化空格、换行用于比较 |
| exporter_name / exporter_address / exporter_tax_id / exporter_country | seller 对应字段 | 同上 |
| quantity / unit_price / line_total | line_items[0] 对应字段 | 数量为整数，金额用 Decimal 定点字符串 |
| product_sku / unit_of_measure | line_items[0].sku / unit | 字符串 |
| subtotal / invoice_total | subtotal / total | Decimal，不能使用二进制浮点数 |
| insurance / freight / packing / handling / other_charges | charges 对应字段，other_charges → other | Decimal；零和缺失区分 |
| parties_related | declared_related | 布尔值，不能把非空字符串直接当 True |

其他字段完整保留供分析和追溯。此模板是一条商品明细；以后多行明细应扩展模板，不能把本表的单项 quantity 当成通用多项结构。重复 Field、错误类型或缺必填字段需显式报告；公式按当前解析器要求转换为值后上传。

后端准备 quantity × unit_price、商品明细合计、subtotal + charges、付款日期等确定性校验，以及上传字段表与主 PDF 的差异，交给 AI 解释及匹配规则。补件不自动覆盖主发票事实。

## Case 2：同一模块两次上传、两次重跑

演示目标模块采用 invoice_integrity：该模块读取完整发票，可同时说明金额与买方地址的字段冲突。本轮不自动更新 buyer_verification，也不把同一地址事实再在其他模块重复加分；需要独立买方复核时，另行向该模块提交证据并重跑。

1. 首页 Upload Invoice 上传 Case 2 PDF，核对 £50,000 后 Run Assessment。基于既有合成本地资料，参考结果为 35 HIGH、manual_review。
2. 进入 invoice_integrity，Attach files 选择 Errors.xlsx，再 Send & reassess。选择文件尚未提交时评分不变；提交后目标模块 stale，解析完再 queued/running；汇总当前失效期间 decision=pending，旧结果标记历史。
3. AI 读取 PDF 和当前错误表，指出 C25 买方香港地址与 PDF 英国地址矛盾，C51 总额 £80,000 与 6,250 × £8、£50,000 小计及零费用矛盾。INTEGRITY_CONFLICT 对应 15 分；其他模块保持原结果时，参考总分 35 → 50 HIGH，manual_review。
4. 同一模块 Attach files 选择 Corrected.xlsx，明确替代旧字段表，再 Send & reassess。新版解析成功后才原子切换有效证据，旧版保留历史。新版失败则旧版仍有效，但本次重跑失败／需要补件，不能显示修正成功。
5. AI 输入包含主 PDF 和修正版；旧版仅作为清楚标注的历史上下文，不能继续视为当前事实。金额及地址与 PDF 一致，模块 INTEGRITY_OK 为 0；参考总分 50 → 35 HIGH，manual_review。关系模块的 6.25 倍交易规模风险未被本次修正消除。

Case 1 仅需 Upload Invoice → Review → Run Assessment，参考结果 5 LOW、eligible、£6,400。两案保持独立 Case。

以上数字是既有本地演示策略的验收预期。真实 AI 输出需满足证据与规则，不按文件名或期望标签强制返回数字。

## 有效证据与请求顺序（待实现）

为字段表附件增加稳定的 evidence_group（例如 invoice_field_sheet）、version、supersedes_evidence_id、active 状态。修正上传显式指定被替代证据 ID，并校验同 Case、同模块、同组。不能依赖文件名中的 Corrected，也不能让普通新附件自动替代所有旧附件。

现有 evidence 接口能上传并通过 rerun 标记请求解析后重跑，但没有上述替代字段；需要扩展契约、数据库和 inputs 查询。当前 inputs 会把同模块全部附件纳入输入，这是修正流程必须补齐的缺口。

组合按钮顺序：保存文件及替代关系 → 解析并验证 → 切换有效版本、递增 input_version → 构建快照 → 重跑 AI → 更新当前结果。使用 expected_module_version 和幂等键；版本冲突返回409并保留草稿。重复提交同文件复用证据，不能重复计分。

当前前端默认 Mock 不读取文件内容，旧 /api 调用尚未适配 /v1；演示前必须完成真实字节上传、目标模块重跑、版本替代、状态轮询及后端评分显示。Attach files / Send & reassess 可保留为组合交互，不要求用户分别点击底层 API 动作。

## 验收重点

- 不调用搜索工具；每条分析结论引用本次快照中的本地 source_id。
- 同一内容改文件名不改变分析；不同内容同文件名仍创建新证据版本。
- Errors 检出两项冲突；Corrected 明确替代后解除；主 PDF 金额始终 £50,000。
- 只重跑 invoice_integrity，其他模块 run_id 不变；参考分数 35 → 50 → 35。
- 历史可查看原文件、原分析、新分析和版本替代关系；当前输入不混用两个有效字段表。
- 解析失败、AI失败、缺资料、并发旧任务均不伪装成修正成功或 LOW。

## 后端接手测试顺序

测试样本已放入本交接包的 `source/`：Case 1 PDF、Case 2 PDF、Case 2 Errors.xlsx、Case 2 Corrected.xlsx。原始 Downloads 文件未修改。全部为合成演示数据。

从仓库根目录执行现有基线测试：

```bash
.venv/bin/python -m pytest backend/tests -q
```

2026-10-04 本次执行：18 个测试通过。测试使用隔离临时数据库及 TestAnalyzer，不联网调用真实 AI、不修改运行数据库。已覆盖 PDF 实际字段读取、Case 1 七模块汇总、Excel 内容进入 AI 输入、局部重跑、幂等、人工调整、并发过期任务、失败处理及模型 transport 等基线。此结果不代表 Case 2 修正版替代流程或真实 AI 分析已通过。

接手后先补齐字段映射、后端参考资料精确筛选、显式版本替代，再增加以下测试。用测试替身检查传输和状态；用真实模型另验分析质量，不能用替身证明模型识别了错误。

| 测试 | 输入／操作 | 必须断言 |
|---|---|---|
| Case 2 初评 | Case 2 PDF + 本地种子 | £50,000；关系 6.25 倍；七模块参考总分35 |
| 错误字段表 | invoice_integrity 上传 Errors 并 rerun=true | AI 输入包含 C25/C51 真实值及字段映射、两项差异；只有目标模块产生新 run |
| 规则汇总 | 测试替身返回有引用的 INTEGRITY_CONFLICT | 目标15，总分50，manual_review；主金额仍£50,000 |
| 替代与修正 | Corrected 显式 supersedes 旧 evidence_id 并重跑 | 当前有效表只有新版；旧版历史可查；目标0，总分35 |
| 替代失败 | 新版解析失败／错误类型 | 不激活新版、不宣称冲突解除、不给自动额度 |
| 同名及改名 | 同内容改名；不同内容同名 | 同内容幂等复用；不同内容独立证据；不按文件名计分 |
| 模块隔离 | 完成上述两次重跑 | 其他六模块 run_id 不变；总分不出现60 |
| 不执行搜索 | 检查模型请求和后端调用 | 模型仅收到本地快照，无搜索工具；所有引用可回溯 |

真实 AI 验收时，检查返回的 findings 是否准确指出两项冲突，修正后是否解除，引用是否对应有效文件。不要求为了达到目标数字而伪造 findings。必要资料缺失返回 needs_info。

交付测试记录需列明：使用的 commit／代码版本、命令、执行模式、通过失败数量、Case 2 两次运行 ID、有效 evidence_id、结果截图或响应、未完成项。密钥不得写入记录。
