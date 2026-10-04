# AI 接入与重算契约

AI每次根据目标模块的**完整当前证据快照**重新分析，产生结构化发现；后端验证发现和引用后执行策略，生成新的ai_score。它不能只更新文案，也不能把旧分数加上“附件数量×权重”。

## 输入

输入包括case_id/module_key/input_version、该模块必需的invoice字段、本地只读Provider取出的相关资料、文件解析内容、补充文字及其出处、评分策略版本。模型不需要拿到整个数据库、其他Case或全部模块的内容。

`examples/case_*/modules/*.input.json`展示模块输入。`contracts/modules/*.json`列出必需数据、可接受证据、读取范围和适用规则。选取资料由后端确定性查询执行，模型不可自由拼接SQL。

## 输出

结构化输出包括：summary、findings（code、事实、引用、confidence）、missing_inputs、matched_rule_ids、ai_score、blocking_flags、provenance。llm可以提出matched_rule_ids和ai_score，但后端必须重算并校验；不一致视为无效输出，最多一次格式修复，再失败，不能采用模型总分。

confidence不参与风险公式；没有可验证事实时保留unknown/needs_info。模型不能把用户补充文字自动升级为已由外部登记机关证实的记录。

## 适配器

```python
class EvidenceAnalyzer:
    async def analyze(self, module_input, policy) -> StructuredFindings:
        ...

class LocalDataProvider:
    def entity_profile(self, entity_id, version): ...
    def comparable_trades(self, seller_id, buyer_id, sku, currency, as_of): ...
    def payment_records(self, buyer_id, as_of): ...
    def market_benchmark(self, sku, currency, unit, trade_terms, as_of): ...
    def financing_records(self, normalized_invoice_key, as_of): ...
```

`demo_replay`：本地结构化资料输入，确定性规则分析/重算，输出provenance明确标为demo_analyzer。支持新版本输入，但对不支持的任意材料明确返回needs_info；不能自称真正LLM理解了任意新文件。

`llm`：同样的输入输出接口，真实模型分析文件解析内容和文字，读取本地资料。模型服务可以是本地模型或远程API，数据库在本地不等于推理一定离线。配置 provider/model/base_url/secret。Key不进Git或前端。远程推理会发送所选证据，应在部署配置中明确。

默认live展示可先用稳定演示适配器。需要真正AI时再切llm并跑同样验收；不自动隐藏模式变化。`cached_llm`如后续增加，缓存键必须包含完整input_hash、prompt/model/policy版本；失配时不能返回旧结果。

## 提示词边界

系统规则、JSON Schema和评分配置由后端定义。PDF、表格、Word、OCR、用户补充文字全部放在标记为UNTRUSTED_EVIDENCE的输入区域。遇到“忽略规则”“直接批准”“给0分”等字样，只按证据内容记录，不执行命令。

case_1/case_2、文件名中Low/High、期待分数、演示脚本均不传给分析器作为决策依据。内容引用要落到同一次快照可访问的source_id。输出HTML一律按纯文本展示，不能把模型返回字符串直接innerHTML。

`prompts/module-analysis.md`提供可用的系统提示模板。后续团队需要实现provider调用、响应结构验证、超时/重试与审计，不应把本包参考脚本当成已经上线的AI。
