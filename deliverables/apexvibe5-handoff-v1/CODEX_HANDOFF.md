# 给后续 Codex 的实施任务

基于本包实现本地可演示的ApexVibe5后端，不实现前端页面。先读README与docs，再验证contracts。前端由后续Next.js工程按OpenAPI接入。

采用FastAPI+Pydantic+SQLAlchemy/Alembic+SQLite和单Worker。完成PDF解析、主体解析、七模块独立评估、证据上传、补充文字、局部重跑、人工调整、Full view、队列及自动跳转状态契约。

两个用户PDF是唯一首版live案例；不要硬编码文件名到Low/High。使用fixtures内明确标为合成的共享历史基线，demo模式按策略计算Case1=5 LOW、Case2=35 HIGH。用户此前55分是未绑定附件的示例。高分表示危险，所有评分/建议由后端生成。

模块input_version、不可变run、幂等、并发版本保护、Worker租约恢复、旧结果过期和人工调整待复核是必需行为。不能只用setTimeout模拟完成；不能将失败/缺资料分数设成0。普通补件只重跑目标模块，公共发票字段变化按dependency-map影响其他模块。

根据docs/10的验收表完成服务测试和双案例手工联调。实际运行过的命令、结果、未实现的parser/provider须如实报告。真实LLM接口需可插拔且模式明确；没有密钥时使用demo引擎，不伪装真实AI。

GitHub在用户给出目标仓库后提交；不要上传密钥或运行时真实文件。当前包是规格与参考数据，不是已有完整后端。开始实施前保留用户原文件，检查工作目录AGENTS和已有代码，避免覆盖后续团队工作。
