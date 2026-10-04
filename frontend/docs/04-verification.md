> 历史基线：本文件记录联调前的 Mock 原型。当前 Live 实现见 [联调说明](03-backend-integration.md)，真实结果见 [Live 验收](05-live-integration-verification.md)。

# 本地整理与验证记录

日期：2026-10-04（Asia/Hong_Kong）。范围：前端安装、检查、构建和 Mock 浏览器流程；真实后端联调没有执行。

用户随后确认产品只面向 PC 浏览器。正式验收与待修项按 PC 场景统计，移动端适配不在范围内；之前的手机检查仅作为历史观察保留。

## 来源与目录

- 原文件：`/Users/mac/Downloads/apexvibe-frontend.zip`。
- SHA-256：`4ad72a3f68b2ce5dace664254c10d359c6bd6e8db6022a7e4b795785b4006354`。
- 解压目录：`/Users/mac/Apex5vibe/frontend`，原始 46 个文件全部存在。
- 解压前检查归属目录、路径穿越、符号链接及异常单文件大小；目标目录原先不存在，没有覆盖旧工程。
- 各原始文件哈希见 [source-manifest.json](source-manifest.json)。原 ZIP 未修改，原 README 另存 [original-readme.md](original-readme.md)。

## 环境与执行结果

| 检查 | 结果 |
|---|---|
| Node / npm | 24.18.0 / 11.6.2 |
| `npm ci --no-audit --no-fund` | 成功，安装 366 个包；保留原 package-lock.json |
| `npm run lint` | 退出码 0，无 lint 错误 |
| `npm run build` | 退出码 0，生产编译、TypeScript、静态页面生成通过 |
| 生成路由 | `/` 静态、`/_not-found` 静态、`/assessment/[id]` 动态 |
| 新增 `npm run typecheck` | 退出码 0，next typegen + tsc --noEmit 通过 |
| 开发启动 | `npm run dev -- --hostname 127.0.0.1 --port 3000`，启动成功 |
| Git 忽略 | node_modules、.next、.env.local 被忽略；.env.example 允许提交 |

已安装主要版本：Next 16.3.8、React/React DOM 19.2.8、Tailwind/PostCSS 4.3.3、lucide-react 1.51.0、TypeScript 5.9.3、ESLint 9.39.5。

安装出现 ESLint 9 的版本支持弃用提示；未升级依赖以避免改变原包锁定基线。`npm ls --depth=0` 返回 0，但列出若干 WASM 可选相关包为 extraneous；本次安装、构建和浏览器流程未因此失败。未执行依赖安全审计，也不把这些检查当作安全审计结论。

## 浏览器实际验证

使用独立 agent-browser 0.38.2 会话，在 `http://127.0.0.1:3000`、Mock 模式执行；未发送文件或备注到远程 AI/后端。所用 PDF 来自工作区的演示附件，仅在浏览器模拟流程中读取文件名与预览。

| 用例 | 观察 | 结论 |
|---|---|---|
| 首页打开 | 有品牌、上传、Demo、历史记录；无空白页和框架错误遮罩 | 通过 |
| Use Demo Invoice | 进入 Review，显示 10 字段及不确定/缺失标记 | 通过 |
| 编辑发票号 | 改为 INV-2026-014-REVIEW，显示 Edited；结果及列表保留 | 通过 |
| 初评 | 23 / Medium / manual_review / 71%，七模块可见 | 通过 |
| 确认卖方备注 | 提交 Supplier emailed us on 2 Oct confirming the new account | 通过：v2=9 / Low / 86%，额度 £3,224 |
| PO 补件 | 选择 Transaction Plausibility，附加演示 PDF | 通过：v3=5 / Low / 100%，previous=9 |
| 分值变化 | 显示 What changed、模块前后值与摘要 | 通过 |
| 结果刷新 | 同会话仍显示 version 3 / 100% | 通过 |
| 首页历史与再次打开 | 显示 23→5、2 次再评估；打开后仍为 v3/5 | 通过 |
| 不支持的主文件 | 尝试 JSON，出现 Unsupported file | 通过 |
| PDF 上传 | 显示 embed 原件及 Simulated extraction 提示 | 通过（只验证 Mock 上传/预览） |
| PDF Review 刷新 | embed 消失，退回固定演示地址的排版 | **已复现限制**，需要后端 file_id 恢复 |
| 不存在的 Case URL | Assessment not found 与新建入口 | 通过 |
| 浏览器错误 | 检查的流程中 errors 为空；console 仅 DevTools/HMR 信息 | 未发现运行时异常 |

风险分有 900ms 动画。截图在分值稳定后重新保存，避免把中间帧当最终结果。

## 可查看的截图

- [桌面首页](screenshots/home-desktop.png)
- [桌面最终结果](screenshots/decision-desktop.png)

### 范围外的历史观察

确认 PC 范围前，曾检查 390×844 手机视口：首页内容宽 390px，结果页内容宽 592px，存在横向溢出。该观察不计为本项目验收失败、待修任务或联调阻塞。原始截图保留：[手机首页](screenshots/home-mobile.png)、[手机结果页](screenshots/decision-mobile-overflow.png)。

## 本次改动边界

保留页面、组件、业务算法、样式和锁文件。本次只做安装准备、配置/文档整理：

1. 新增 `.nvmrc`（Node 24）及 `typecheck` 脚本。
2. `.gitignore` 放行 `.env.example`；创建本地 `.env.local`，保持 mock。
3. `.env.example` 注明旧接口与 `/v1` 差异、URL 填法与公开变量边界。
4. README 改为中文入口，原 README 归档；FRONTEND.md 增加契约差异提示。
5. api.ts、types.ts、mock-data.ts 只修正文档注释和失效的 CLAUDE.md 引用，没有改运行逻辑。
6. 新增代码梳理、接口说明、联调清单、来源清单、4 份原型 JSON 样例和本验证记录。

与原 ZIP 比较，变更的原文件仅为 `.env.example`、`.gitignore`、`package.json`、`README.md`、`FRONTEND.md` 及上述 3 个 lib 文件。框架生成的 next-env.d.ts 当前与原文件一致。

后端、根目录配置及现有交付包均未由本次任务修改。没有提交 Git、发布或部署。

## 尚未验证

真实 OCR/AI、四个 Live 请求、后端任务/持久化/CORS/鉴权、真实文件解析、多用户并发、超时/取消/409、所有负向 Mock 分支、PC 版 Safari/Firefox 与无障碍专项。

下一阶段按 [联调准备](03-backend-integration.md) 实施与验收。当前结论是“本地前端演示可运行，代码与契约已梳理”，不是“前后端已联调完成”。
