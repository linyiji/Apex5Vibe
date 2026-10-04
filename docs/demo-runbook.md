# Case 1 演示与排错

## 演示准备

按根 README 初始化数据库，配置后端 `.env`，分别启动 API（18080）与 Worker。打开 `/health`，确认 `model=gpt-6.1-sol`、`analyzer_configured=true`；该健康检查只确认配置存在，不代表模型连通。真实连通由评估运行验证。

运行 `python scripts/live_case1.py --verify-rerun`：

1. Buyer/Seller 均 Skip，上传 Case 1 PDF。系统从真实表单读取 GBP 8,000 发票并匹配本地主体。
2. 提交初评，观察七个模块 queued → running → succeeded。
3. 初评 settled 后自动进入结果页信号，无需点下一步。
4. 预期 LOW 5/100。付款模块 5，其余模块 0，演示额度 GBP 6,400.00。
5. Invoice Integrity 上传 Case 1 XLSX 并重跑，仅该模块的输入版本/Run 改变。
6. Payment History 添加文字说明并重跑，仅该模块变化；事实没有改变时分数可以保持 5。
7. 查看 Full view、原件下载、运行输入、模型返回 ID、token usage 和审计历史。

原件已在 `deliverables/apexvibe5-handoff-v1/source/`，无需从 Downloads 再复制。原始案例与参考数据均为合成材料。后端不提供交易执行或放款操作。

## 常见状态

| 情况 | 处理 |
|---|---|
| 所有 Job 一直 queued | 确认独立 Worker 已启动，并与 API 使用相同数据库路径 |
| ANALYZER_NOT_CONFIGURED | 填入后端 `.env` 的密钥，重启 API 和 Worker |
| TeamRouter 401/403 | 检查本地密钥权限/有效性，服务端不会输出密钥或原始鉴权响应 |
| 408/429/5xx 或超时 | Worker 有最多 3 次尝试；失败后保留错误，可针对失败模块重跑 |
| INVALID_AI_OUTPUT / INVALID_AI_RULE / INVALID_AI_CITATION | 检查该 Run 的输入与错误；修正数据/Prompt 后局部重跑，不能直接填零 |
| needs_info | 补充实际缺失资料；模型缺资料不会给安全结论 |
| stale | 有新资料尚未重新评估；旧结果可看，但当前额度为 pending |
| 409 VERSION_CONFLICT | 刷新 Case/Module，基于当前版本重新操作，保留用户草稿 |
| Worker 中断 | 重启 Worker，等待原租约过期后恢复；最多 3 次领取，超限显式失败 |
| Excel 公式/无文本扫描 PDF | 当前解析器不支持，换成值文件/可抽取文本 PDF；失败补件未提供删除 UI/API |

诊断入口：`GET /v1/jobs/{job_id}`、Workspace 的模块错误、`GET /modules/{key}/runs/{run_id}` 与 `/events`。不要把密钥、`.env` 或 runtime 数据目录上传 GitHub。

数据库初始化可重复执行，只补缺少的合成参考数据，不清空 Case。演示重置建议切换 `APEX_DATA_DIR` 到新的目录，并重启两个进程；这样原记录可保留。测试使用临时独立目录，不影响演示数据库。

## 验收区分

离线 pytest 验证协议/业务正确性，测试分析器明确标记 `test_only`。`live_case1.py` 要求运行记录的 provider 为 teamrouter、requested_model 为 gpt-6.1-sol，并检查真实最终输出。脚本保存完整 JSON 后才退出，包括失败情况，不会把失败运行标记为成功。

后端接口与前端尚未实际联调；本轮通过 HTTP 脚本完成闭环。Case 2 的补充接口和真实验收步骤见 [补充实现说明](local-data-and-replacement.md)。


## 补充：本地数据与显式修正

已增加字段键映射、精确筛选本地参考资料及解析验证后的原子证据替代。接入 `evidence_group / supersedes_evidence_id`，展示 pending / active / failed / superseded 版本状态。完整说明与请求表见 [补充实现说明](local-data-and-replacement.md)。本轮仅本地测试；前后端联调后再上传 GitHub。
