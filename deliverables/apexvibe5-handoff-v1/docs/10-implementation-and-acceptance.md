# 实施顺序与验收

## 分阶段开发

1. 固化contract与fixtures；先运行本包校验，保留原始附件SHA-256。
2. 建FastAPI骨架、配置、本地SQLite迁移、文件存储、reference seed、Case/Entity接口。
3. 实现两张PDF的AcroForm抽取与Excel对照；每字段带来源，核对全部关键金额、主体、日期、数量。
4. 实现Jobs Worker、七模块输入组装和demo_analyzer；使用risk-policy统一计算5/35。
5. 实现证据、文字、局部重跑、版本竞争、人工调整、总分聚合和历史快照。
6. 实现Workspace/Queue/Full view接口和前端交接mock；接后续Next.js页面。
7. 接llm适配器，用同一数据集验证真正基于证据分析，不以case标签控制结果。
8. 执行双案例演示与异常场景验收；之后提交到指定GitHub仓库。

## 必须通过的验收

| ID | 操作 | 断言 |
|---|---|---|
| A01 | 两张PDF分别上传 | 实际抽取8000/50000、相同主体和SKU，金额不硬编码 |
| A02 | Skip/Skip | 两方仍关联/创建Entity |
| A03 | Manual或Existing与发票不符 | 明确conflict，不偷换主体；允许按发票解决 |
| A04 | 两个基准评估 | 建议演示策略得到5 LOW / 35 HIGH |
| A05 | 初评七模块结束 | 自动进结果页，只跳一次，失败也可看到结果页原因 |
| A06 | 上传payment_history附件 | 只有目标input_version变；其他6个run_id不变 |
| A07 | 保存文字 | 无任务自动重跑，模块stale，建议pending |
| A08 | Save & Re-run重复点击 | 相同幂等键只保存一次、排一个任务 |
| A09 | 分析期间新增证据 | 旧run被superseded，不覆盖新输入结果 |
| A10 | AI重跑 | 分数可升可降可不变，完全由证据与规则决定 |
| A11 | 人工调整 | 原AI分与run历史保留，有actor/reason；重跑后待确认 |
| A12 | 总分29/30 | 分别LOW/HIGH；无MEDIUM |
| A13 | 缺付款资料/解析失败 | 模块needs_info/failed，current_result=null，不能假设0分 |
| A14 | 相同PDF重复上传 | 幂等/去重；不凭重复上传判断已融资 |
| A15 | Case 1修改后看Case 2 | 数据互不污染，共用只读reference版本可追溯 |
| A16 | Worker中途重启 | 租约恢复，晚返回的旧token不可提交 |
| A17 | Full view/刷新/断线 | 历史与最新状态可从后端恢复，无前端timer伪造成功 |
| A18 | 改filename与case标签 | 保持相同事实时分数不变 |
| A19 | Low融资金额 | 8000×80%=6400，GBP；High额度为null |
| A20 | 补充文档包含指令 | 不改变系统规则，不绕过Schema/权限 |
| A21 | 请求-10而AI只有5 | 实际调整-5，final0，汇总加法一致 |
| A22 | 重跑时旧人工调整存在 | 留历史、pending_review、阻止直接套旧调整批准 |

本包已执行的是静态契约/参考计算/数据库完整性校验，不是以上全部后端与浏览器端到端测试。后续实现必须完成这些验收，不能把`validation/report.json`误当实际服务验收报告。

## GitHub 交付

当前目录没有已有Git仓库或remote，且本轮交付为架构包，没有创建仓库或推送。目标仓库明确后，可将本包作为docs/contracts/fixtures提交，实际后端另起backend目录；不要创建只有壳页面的前端冒充交付。

建议Git忽略：.env、.venv、storage/uploads、runtime/*.db、SQLite WAL/SHM、解析缓存、真实客户材料。附件均标注合成示例，但仍在README明确来源；源码库内的reference.sqlite3可由脚本重建，无需版本化二进制库。

## 当前可执行与后续待实现

已交付：原件快照、来源manifest、标准化JSON、合成reference、SQL、SQLite参考库、schema、OpenAPI、模块样例、分析prompt、校验器、前端交接与验收表。

待实现：HTTP服务、真实异步Worker、实际文件解析pipeline、通用新证据的AI处理、认证（如对外服务）、Next.js联调与GitHub部署。实现开始前只需要沿本包合同开发，无需再把四页HTML当成业务代码复制。
