# 发票风险指数

风险指数越高越危险。它是本 Demo 的业务规则分，不是违约概率、模型置信度或信用分。本版数值与权重是**建议的演示策略**，没有经过真实金融样本校准。

## 计算

七模块风险贡献上限之和等于 100。每模块的 ai_score 是分析结果按该模块规则得到的贡献分，直接相加，无需再次乘权重。

```text
module.final_score = clamp(module.ai_score + requested_adjustment, 0, module.cap)
module.effective_adjustment = module.final_score - module.ai_score
aggregate.ai_total = Σ module.ai_score
aggregate.effective_adjustment_total = Σ module.effective_adjustment
aggregate.final_risk_score = Σ module.final_score
                           = ai_total + effective_adjustment_total
risk_band = LOW if final_risk_score < 30 else HIGH
```

总和天然落在 0–100，不再额外截断总分。比如 AI=5、请求调整=-10、模块 cap=15，则最终=0，实际生效=-5；界面可显示请求-10，但汇总的“人工调整”必须显示-5。允许的请求调整整数范围为 [-cap, cap]，超出范围返回422。

## 模块规则

| 模块 | cap | 演示规则和证据 |
|---|---:|---|
| invoice_integrity | 15 | 金额/日期/字段验证；一致 0；确认的算术不符 15，并要求人工复核 |
| buyer_verification | 10 | 与本地合成主体档案一致 0；明确注册号或地址矛盾 10；缺档案为 needs_info |
| seller_verification | 10 | 同上，不同角色独立计算 |
| relationship | 30 | 无关联声明冲突时，根据当前金额/可比历史金额中位数：<2 倍 0；[2,5) 倍 15；>=5 倍 30；确认关联声明冲突可取 30。同模块取最高适用档，不累加同一事实 |
| market_price | 10 | 可比 SKU/币种/单位/贸易条件范围内 0；超出范围不超过 25% 得 5；超过 25% 得 10；无可比数据为 needs_info |
| payment_history | 15 | 无违约且逾期笔数比例为 0 得 0；(0,20%] 得 5；(20%,50%] 得 10；>50% 或已确认违约得 15 |
| duplicate_financing | 10 | 本地有效台账内无匹配融资 0；确认同笔未结清融资 10，并添加硬阻断项 |

relation 模块 UI 描述应扩充为“买卖双方关系与历史交易规模”；金额突增属于交易上下文，而不是单价异常。历史比较限定相同双方、币种和商品类别，固定 observation window 和 as_of；基线只用已完成的历史交易，排除正在评估的发票。

市场价偏离比例：低于下界时 `(lower-price)/lower`，高于上界时 `(price-upper)/upper`。本演示本地范围 GBP 7–9/PCS、相同 SKU、DAP Bristol、运保包装已含，invoice 单价 8，两个案例都是 0 分。

## 缺数据与阻断

缺资料时 ai_score=null、state=needs_info，不是 0 分。结果未齐全时不发布当前 aggregate。低置信抽取先确认关键字段，不把 OCR 不确定性伪装成已确认商业风险。

融资建议按以下优先级计算：

1. 结果不存在、过期、解析未完成、人工调整待确认 → pending，无额度。
2. 存在 `confirmed_duplicate_financing`、`entity_mismatch` 或 `invoice_integrity_conflict` 阻断 → manual_review，即便指数低于30。
3. 当前有效总分 >=30 → manual_review，无自动建议额度。
4. 当前有效总分 <30 且无阻断 → eligible，建议预付比例80%。

Low/High 表示指数的两档；融资建议还需要证据完整性和明确冲突检查。人工减分不能清除硬阻断事实。这个补充规则不会改变两个基准 Demo 的结果。

## 金额和人工调整

金额用十进制定点字符串，如 `"8000.00"`；数据库用 minor units 整数。GBP 建议额度为 Decimal(amount) × Decimal('0.80')，四舍五入到 2 位，Case 1 为 GBP 6,400.00。后续多币种按币种精度规则，不假设所有货币有2位小数。

人工调整必须带 reason、操作者和 `applies_to_run_id`。操作者由服务端会话得出，不能信任前端 JSON 伪造 author。设置是“替换当前调整值”，不是再累加一次；历史事件仍追加。AI 重跑永不覆盖原 ai_score 历史，也不默默继承旧调整。

`contracts/risk-policy.json` 为本版唯一机器可读策略。前端不得内置阈值或自己计算融资额度。UI 可展示返回值，不承担评分。
