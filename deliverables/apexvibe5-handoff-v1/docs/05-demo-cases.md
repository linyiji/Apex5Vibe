# 两个案例与演示数据

本次 live 范围只包含用户提供的两张 PDF。Excel 用作抽取校验基准，也可在模块内演示补件；它不是付款历史或外部尽调数据。

## 数据分层

| 层 | 来源 | 是否附件中已存在 |
|---|---|---|
| invoice_fields | PDF 表单/文本，与 Excel 对照 | 是 |
| entity_profiles | 根据同一合成名称/注册号构造的本地演示档案 | 否，新增合成 seed |
| completed_trade_history | 同一双方12笔已完成交易，金额中位数 GBP 8,000 | 否，新增合成 seed |
| payment_history | 同12笔交易，10笔准时、2笔分别迟付3天/6天，无违约 | 否，新增合成 seed |
| market_benchmarks | 同 SKU、GBP、PCS、DAP 的 GBP 7–9 | 否，新增合成 seed |
| financing_registry | 覆盖本地 Demo 台账，没有两张目标发票的有效融资记录 | 否，新增合成 seed |

每条记录标记 `synthetic=true`、`source_type=authored_demo_seed`、as_of、source_id。不能把这些来源描述成联网查证的真实企业或真实市场数据。此设计选择共同的历史数据，从业务输入计算差异，而非按文件名返回 High/Low。

## 可复现结果

| 风险贡献 | Case 1 | Case 2 |
|---|---:|---:|
| 发票完整性 | 0 | 0 |
| 买方核对 | 0 | 0 |
| 卖方核对 | 0 | 0 |
| 关系与历史规模 | 0 | 30 |
| 商品与市场价 | 0 | 0 |
| 付款历史 | 5 | 5 |
| 重复融资 | 0 | 0 |
| 总分 | **5 LOW** | **35 HIGH** |
| 当前金额 / 历史中位数 | 1.00 倍 | 6.25 倍 |
| 融资建议 | eligible，GBP 6,400.00 | manual_review，额度 null |

High 的解释应为：“本次 GBP 50,000 是可比历史交易金额中位数 GBP 8,000 的 6.25 倍，需要复核交易规模变化的原因；单价与算术未见异常。”不能解释为已发现欺诈、伪造发票或异常商品价格。

此前对话里的 Low 5 / High 55 是尚未绑定附件的示例。本次没有资料支持额外20分，因此改为有明确推导的5/35。若业务后来提供其他风险证据，再由真实规则更新，而非为满足55分捏造融资或违约记录。

## 文件识别

PDF 的 SHA-256 记录于 `fixtures/source-manifest.json`，可用于验证样本完整性、缓存和展示识别。Case 选择不作为计分输入，文件名、页脚的 Test Case 1/2、期望风险标签均不能进入分析器。

已知哈希可读取预核对的表单映射以降低演示解析波动，但必须返回 `extraction_method=verified_form_fixture`。未知哈希不能偷偷套用 Case 1，必须实际解析或明确报当前 demo 不支持此输入。相同文件重复上传应幂等复用，同文件副本不是已经融资的证明。

## 演示脚本

1. 启动已实现的 API、Worker、前端；清空运行态，只保留合成参考资料。
2. 创建 Case，Buyer/Seller 均 Skip，上传 Case 1 PDF。
3. 页面显示真实抽取的 GBP 8,000 与两个主体；确认后开始初次评估。
4. 查看七模块状态完成，自动进入结果页：5 LOW，建议 GBP 6,400。
5. 创建独立 Case，使用 Select existing 或 Manual 演示，上传 Case 2 PDF。
6. 同样自动进入结果页：35 HIGH，显示 6.25 倍交易规模提示和 manual_review。
7. 在 Case 2 的 relationship 增加说明“本次为季节性批量采购，采购证明待补”。Save 后该模块 stale；Save & Re-run 重新分析。没有新增可核实证据时，分数保持30也属于正确结果。
8. 打开 Full view 查看新旧运行、说明引用、证据版本；其他六模块 run_id 不变。
9. 演示人工设置 relationship 调整 -10，理由“演示分析师调整”；AI=30 保留，模块 final=20，总分25 LOW。原始高风险结论和调整人/理由均保留。此步骤不是新增第三个演示案例。
10. 再重跑 relationship，旧调整 pending_review，建议 pending；确认新 run 的调整或归零后恢复建议。

首版默认 `demo_replay` 分析器以结构化资料稳定重算，并明确显示“演示引擎”。如果要 live 真 AI，提前配置 llm 模式并做演练，失败不静默假扮 AI 成功；可由操作者显式切回 demo。
