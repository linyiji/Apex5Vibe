# Next.js 前端交接

本包不新建或修改前端。HTML只作为交互参考。后续前端从OpenAPI生成或手写类型均可，但所有业务状态和分数必须以API为准。

## 页面映射

| 页面 | 数据和按钮行为 |
|---|---|
| Queue | GET /cases；分别展示stage、aggregate.status、risk_band。未评估显示“待评估”；过期风险显示“上次结果” |
| Step 1 | 两个独立三选一控件；Skip无需值，existing需要entity_id，manual需要名称；创建Case后上传字节 |
| Step 2 | 展示抽取字段和PDF对照、主体匹配及冲突；开始评估前发票必须ready、主体无未解决冲突 |
| Step 3 | 初次批次状态；轮询Case，七模块卡片各自状态。settled后自动router.replace到结果页 |
| Step 4 | 完整Workspace、当前/历史总分、融资建议、模块列表；局部重跑留在此页 |
| Module Full view | 详细结论、原始AI分、人工请求/实际调整、最终分、引用、文件、补充说明、运行和事件 |

## 自动跳转伪代码

```ts
// 交接示意，非交付的前端实现。
if (currentStep === 3 && workspace.initial_assessment_status === 'settled') {
  router.replace(`/cases/${workspace.case_id}/result`);
}
```

效果必须幂等。只在当前活动Case且页面是Step3触发；用户切去另一个Case之后，旧请求或旧timer不得把用户拉回。请求取消或按case_id丢弃晚到结果。

## 模块按钮矩阵

| 动作 | 允许条件 | 结果 |
|---|---|---|
| Upload evidence | Case存在且format ready | 目标模块stale，显示解析状态；可以在running时补件 |
| Save information | 非空文字，<=10,000字符 | 保存一条说明，目标模块stale，不自动重跑 |
| Save & Re-run | 非空文字 | 保存与排队为一个服务端命令；已有运行则标记请求最新版本重跑 |
| Re-run AI | 有足够已解析输入且无active job | 202，目标模块queued/running；其他模块不变 |
| Manual adjustment | 存在当前成功run，reason非空 | 保存绑定run的调整，不调用AI；运行中禁用，返回409防止竞态 |
| Full view | 始终 | 即使失败也能看到缺失输入、历史、错误与可用动作 |

前端根据后端allowed_actions渲染，不仅靠按钮隐藏做校验；服务端再次验证。失败/缺资料模块需要明确重试/补资料入口。

## 分数展示

- 模块：AI score + Effective manual adjustment = Final module score。
- 如果requested_adjustment被边界限制，同时解释请求值和实际生效值。
- 当前结果不完整时，顶部显示“结果待更新”；保留上次快照但不可沿用其可融资建议。
- `engine_mode=demo_replay` 显示“演示引擎”；llm显示真实provider/run信息的适度摘要。不要把demo伪装成真实联网尽调。
- Low绿色、High红色；处理中、资料不足、过期使用独立状态样式，避免重新引入Medium风险。
- AI置信度和风险贡献分使用不同字段及单位。
- 金额用invoice.currency格式化；不能保留原型固定£3,224。

## 数据同步

每1秒轮询正在变化的Case；稳定且无pending job时停止高频轮询，页面focus或写操作完成后重新拉取。失败退避到2秒、5秒。Query key包含case_id和module_key。显示最新revision，丢弃比当前revision更旧的响应。

局部变更后刷新目标Full view、Case summary及Queue相关记录；不要无条件清空全部模块。断线提示连接状态，不能通过前端模拟timer补出成功状态。刷新页面读取后端持久状态恢复。

## 前端交付验收

后端联调不依赖HTML内全局变量。用examples中的两个Workspace mock可先开发页面，再换成API。至少验证Skip/Manual/Existing，失败模块自动进入结果页，补文字后过期提醒，局部重跑及版本冲突，人工调整后原AI分保留。浏览器内不得包含AI密钥或直接打开SQLite文件。
