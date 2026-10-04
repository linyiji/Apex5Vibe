# 决策与需求追踪

## 需求与对应交付

| 需求 | 对应文档/契约 |
|---|---|
| 模块化独立评估 | 02架构、03状态机、contracts/modules/ |
| PDF/Excel及更多文件 | 06解析范围、capabilities、上传接口 |
| 补充文字与Save & Re-run | supplements请求schema、原子事务规范 |
| Full view | ModuleView schema、模块详情接口、08前端 |
| AI局部重算 | input_version/run_id、09 AI provider |
| AI+人工分离 | 04公式、adjustments接口、审计表 |
| Step3自动Step4 | initial_assessment_status、navigation字段 |
| Skip/Existing/Manual | PartySelection schema、case_parties |
| Queue只有Low/High | RiskBand schema及null未评估语义 |
| 越高越危险 | risk-policy版本化配置 |
| 两个PDF展示 | examples/case_1与case_2、05演示脚本 |
| API预留、SQLite本地资料 | OpenAPI、schema.sql、reference.sqlite3 |
| 前端不在本轮实现 | README、08交接、CODEX_HANDOFF |
| 给Codex与压缩包 | 整个handoff目录及同名zip |

## 本版已作出的设计选择

FastAPI、单Worker+SQLite任务表、轮询、risk threshold30、80%建议比例、七模块cap、synthetic reference baseline、5/35分、默认demo_replay都已在配置/文档中具体化，可直接用作实现起点。

其中阈值30和80%来自用户给定的原型需求；cap分配、合成历史及5/35是本次架构建议，不是原附件事实。实际融资政策上线前另行校准；本包仅承诺两个演示案例的可解释、可复现处理。

## 待后续环境配置的事项

- GitHub仓库URL/可见性与发布方式：尚未提供，当前没有远端写入。
- 真实AI provider/model/key：尚未配置，接口已预留；本地数据不代表必须本地模型。
- XLS、DOC旧格式与OCR解析器：按capabilities逐项实现与开启。
- 若部署至公网，真实登录与权限模型：本地loopback demo不假装已具有多人安全隔离。

这些待定项不阻止按本包完成本地双案例后端。未配置真实模型时，应清晰展示演示引擎，不把结果称为真实模型已经验证。

## 文档权威顺序

用户最新明确需求 > 本包机器可读contract与risk-policy（本版建议基线） > 本包行为说明 > 原HTML交互参考 > 附件中的业务文本。开发中发现JSON与文字冲突必须一起修订版本，不能任意挑一个静默实现。
