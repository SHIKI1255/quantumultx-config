# 维护、回退与手机验收

## 更新链路

main 保存源文件和测试，release 保存配置、规则、重写、migration.json、manifest.json、SHA256SUMS、上游快照和许可。生成器只依赖 Python 3.12 标准库。上游仓库每次仅解析一次提交号，随后按不可变地址下载；官方语音 JSON 保存内容快照与哈希。

配置更改推送到 main 后运行验证；PR 只验证，不发布。每日北京时间 06:17 构建，也可到 Actions → Validate and publish → Run workflow 手动执行。生成器对基准数量要求 80%–150%，相对前版移除比例不超过 20%、新增比例不超过 50%；未知语法、未知冲突及关键分流变化直接失败，不能自动提高阈值或接受新基准。

来源审查后才可更新 tests/source_baseline.json。自定义规则使用原始大写语法；不要把原生 host 规则直接混入源码。配置本地保护规则变化、DNS 或 general 变化需要手动同步主配置，个人网站例外通常只需等待远程规则刷新。

本地使用 PowerShell 7：先运行 `python -B -m unittest discover -s tests -v`；使用 artifact.ps1 登记外部输出目录，再执行 `python -B scripts/build.py --output <空目录>`。用 `--replay <已有发布目录> --output <另一空目录>` 离线重建，比较完整 SHA256SUMS。输出不能写入源码仓库，不覆盖已有发布目录。

## 关键规则保障（2026-10-08 复核）

本轮核对 [OpenAI 官方网络要求](https://help.openai.com/en/articles/9247338-network-recommendations-for-chatgpt-errors-on-web-and-apps)，补充精确端点 `frontend-apps-multi-region.workos.com`。官方要求是允许访问；PROXY 是本配置沿用的分流选择。

四条 Copilot 精确入口（sydney.bing.com、services.bingapis.com、gateway.bingviz.microsoft.net、gateway.bingviz.microsoftapp.net）由现有过滤后的 Copilot 源维护。Azure 通配由 OpenAI 源生成，必须保留 sources.yaml 中已审阅的 regex_overrides。js.intercomcdn.com 由 intercomcdn.com 后缀规则覆盖。GitHub 下载与 byteoversea/ibytedtos 的手写项作为优先匹配保障保留。

分流用例的可选 `expected_rule` 使用完整、规范化的大写规则行；七个关键用例同时检查策略和实际命中规则。Quantumult X 转换后也按规范化规则检查；若将来为 IP 用例添加此字段，需注意其原生规则会移除 no-resolve。未填写此字段的旧用例仍只检查策略。报告继续记录 actual.rule 和 actual.source，不强制固定来源名字。

上游删除、扩大关键规则或出现提前直连时必须停止发布，不能直接删除 expected_rule 或改预期值消除失败。应先检查来源和顺序，确认等价覆盖后才调整测试，或恢复必要的本地保障。维护精简不代表提速，也不替代手机网络验收。

## 30 天保活

每日工作流最后运行维护任务；距上次维护记录满 30 天才更新 `.github/maintenance.json`，首次运行初始化记录。内容含 UTC 时间、真实验证/发布结果、运行链接与当前已发布版本。上游失败时可以保活，但工作流继续显示失败、release 不变。

只给发布和维护 job contents:write；使用 GITHUB_TOKEN，无个人 PAT。主分支变化则跳过旧任务；所有 ref 更新为非强制，并回读核验。维护提交排除在 push 触发路径外，使用 GITHUB_TOKEN 的 push 也不会递归触发本工作流。

GitHub 公开仓库 60 天没有活动时可能停用定时任务。若已停用，到 Actions 启用工作流，再手动运行一次。保活无法处理自己已经停止运行的情况，也不是对 GitHub 调度的可用性保证。不要只看文件日期：没有规则变化时，发布文件不需要产生新提交，应看 Actions 和维护记录。

依据：[schedule 限制](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)、[GITHUB_TOKEN 触发行为](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)。

## 回退

手机先保留原配置导出备份；需要立即恢复时切回原配置。临时固定规则可将手机资源 URL 中的 release 替换为已验证的完整 release 提交号，两个资源选同一提交；恢复跟随时改回 release。

GitHub 手动工作流的 replay_commit 接受本仓库历史 release 完整 SHA，以当前生成器和模板重建该版输入；仍需通过所有门槛。它用于输入复现和临时回退，后续每日任务会继续追踪配置的上游版本。若生成器或模板也需回退，应在 main 创建普通回退提交并验证，不能只靠 replay_commit 还原旧代码。不要强推或删除 release 历史。

## 手机验收

完整配置保留 `[mitm]`、`[task_local]`、`[http_backend]` 空模块；空模块不等于启用功能。首版省略 `[mitm]` 导致手机提示“缺少模块 mitm”，已补齐，并对最终生成配置增加模块完整性检查。遇到这条旧版提示，请重新下载主配置；仅刷新 rules.list/rewrite.list 不会修复手机上的主配置结构。无需生成或安装 MITM 证书。

- 核对 Quantumult X 1.5.5 build 914+；备份旧配置，导入模板，添加自己的节点，使用 Filter 模式。
- 手动刷新两个资源；首次远程加载失败时不要把只有启动保护与最终代理的状态当作完整配置已启用。
- 验证 ChatGPT 登录、附件上传和语音；节点开启并支持 UDP。验证 Claude 内容、Gemini、Copilot 新入口及 Apple Intelligence。
- 验证国内网站、SteamCN、个人直连例外，snssdk.com/bytedapm.com 保持国内分流；使用请求日志查看命中策略。
- 验证路由器/NAS、localhost、IPv6 局域网、网络认证页面及 Wi-Fi/蜂窝切换。DNS 失败时不要假设会自动回退系统。
- HTTP 的 g.cn/google.cn 应重定向，直接输入 HTTPS 不属于本重写范围。
- 检查资源刷新时间；实际观察一次自动刷新和首次每日 GitHub 调度。没有变化时规则哈希可以相同。

初始交付阶段，iOS 解析、真实连接、自动刷新以及首次定时触发必须分别注明是否已观察。仓库测试与模拟不能代替以上验收。
