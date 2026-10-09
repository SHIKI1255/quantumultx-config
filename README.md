# Quantumult X 自动维护配置

适用于 Quantumult X 1.5.5 build 914 或更新版本。主配置留在手机，一份分流资源和一份 HTTP 重写资源自动刷新；节点与订阅由你在手机添加。

## 首次使用

1. 先导出并保存手机原配置，核对 Quantumult X 版本。
2. 从[主配置模板](https://raw.githubusercontent.com/SHIKI1255/quantumultx-config/release/quantumultx.conf)导入一份新配置。模板已含远程资源，无需再重复添加。
3. 在手机添加自己的节点或订阅，选择代理节点并启用分流（Filter）模式。仓库没有可直接使用的节点。
4. 手动刷新两项资源，确认加载成功，再按[手机验收清单](docs/maintenance.md#手机验收)验证。首次下载遇到网络不可达时，先用已有可用连接下载模板和资源。

| 固定文件 | 用途 |
| --- | --- |
| [quantumultx.conf](https://raw.githubusercontent.com/SHIKI1255/quantumultx-config/release/quantumultx.conf) | 首次导入、手动同步基础设置 |
| [rules.list](https://raw.githubusercontent.com/SHIKI1255/quantumultx-config/release/rules.list) | 统一分流资源，混合 direct/proxy |
| [rewrite.list](https://raw.githubusercontent.com/SHIKI1255/quantumultx-config/release/rewrite.list) | 两条 HTTP Google 重定向 |

手机资源刷新间隔为 86400 秒。GitHub 每天北京时间 06:17 构建，也支持源码修改和手动触发；两者独立运行，GitHub 完成不等于手机立即更新。DNS、基础设置及节点不会被资源刷新覆盖。模板变更需对照差异手动同步，避免覆盖手机节点。

## 日常维护

| 入口 | 修改内容 |
| --- | --- |
| `config/base.conf` | DNS、IPv6、基础设置、资源引用、两条重写模板 |
| `rules/custom.list` | 局域网、关键端点和兼容规则，沿用大写 Shadowrocket **源码格式**，由生成器转换 |
| `config/sources.yaml` | 上游来源、顺序、过滤与异常阈值；采用 JSON 语法的 YAML 1.2 子集 |

例如在 `rules/custom.list` 添加 `DOMAIN-SUFFIX,example.com,DIRECT`，检查通过后推送，等待 CI 和手机资源刷新。前 19 条局域网/DNS 启动保护规则会进入主配置，改动这些规则仍需同步模板。生成的 `release` 文件不要直接编辑。

保持 blackmatrix7 通用分类、v2fly AI/TikTok 及 OpenAI 官方语音 IP；不新增广告拦截、脚本、MITM 或区域策略组。2026-10-09 已删除用途未确认的 `checkout.mzxnyysm.com` 个人直连例外，该域名及子域名恢复正常分流，不新增拒绝或强制代理规则。

本次复核保留 61 条手写规则，与 Shadowrocket 的规则源码一致。GitHub 下载保障、`byteoversea.com`、`ibytedtos.com` 刻意前置；相同上游记录生成时去重。五条 Arkose/Statsig/Featuregates 记录是历史登录兼容，当前必要性未实机确认，不标为官方必需项。[OpenAI 官方清单](https://help.openai.com/en/articles/9247338-network-recommendations-for-chatgpt-errors-on-web-and-apps)的 30 个域名模式及 `ws.chatgpt.com` 已有明确覆盖。上游来源、过滤和顺序保持原样，不新增共享 CDN 或历史 Apple 域名排除项。

DNS 保持 AliDNS/DoH.pub 双 DoH，以及局域网、localhost 和网络认证域名的系统解析例外。双 DoH 是并发查询，不是主备顺序；不承诺二者失败后自动回退系统 DNS。代理目标由节点侧解析，本地结果用于规则判断和直连；参见 [Quantumult X 官方示例](https://github.com/crossutility/Quantumult-X/blob/master/sample.conf)。本次不改变 DNS、IPv6、UDP、节点或重写，也不加入 GeekSpeed Hosts。已有用户仅需刷新远程分流资源，无需重导主配置。

本次 98 个分流用例在源码及原生转换后均检查，53 个同时核对实际命中规则；原有 42 项已登记冲突不变。同一上游快照下总规则从 14,153 条减为 14,152 条。需要临时回退时，将现有远程分流资源 URL 改为[变更前固定 rules.list](https://raw.githubusercontent.com/SHIKI1255/quantumultx-config/bab3539cefb4066a28a8c13f56fe99cad4039e8a/rules.list)，保持原资源参数、不重复添加；恢复时改回 release 地址。主配置和重写无需回退。

本仓库独立保存生成器和来源配置，不在线引用 Shadowrocket 仓库的发布配置。首次迁移共 14,111 条规则：主配置 20 条（19 条保护规则和最终兜底），远程资源 14,091 条。运行版本以 [manifest](https://raw.githubusercontent.com/SHIKI1255/quantumultx-config/release/manifest.json) 为准。

## 自动更新的边界

每次固定上游提交再抓取，未知语法、未登记冲突、关键分流回归、异常增删或下载失败均阻止发布，保留上次成功版本。CI 验证后一次性更新 release 分支；手机分别读取两个资源，不保证跨文件同时刷新，本项目规则与简单重写互不依赖。

每 30 天在 main 提交一次真实维护记录，避免长期没有仓库活动。记录写在发布之后，失败时如实记载失败，不能代替规则验证，也不改变订阅内容。仍需处理 Actions 被停用、GitHub 故障或节点不可用等情况。

参阅[迁移差异](docs/migration.md)、[维护、回退与手机验收](docs/maintenance.md)、[第三方许可](docs/third_party.md)。本地静态检查不能证明 iOS 实际连接或后台自动刷新正常。
