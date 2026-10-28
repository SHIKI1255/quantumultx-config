# SHIKI1255-Rules | Quantumult X

公共域名、上游来源、分类、顺序和回归用例集中在[唯一维护入口](https://github.com/SHIKI1255/shadowrocket-config/tree/main/shared)。本仓库保留客户端模板和发布；不要另建一份个人规则清单。

适用 Quantumult X 1.5.5 build 914+。先备份手机配置，导入[主配置模板](https://raw.githubusercontent.com/SHIKI1255/quantumultx-config/release/quantumultx.conf)，自行添加节点并使用 Filter 模式。

[统一分流资源](https://raw.githubusercontent.com/SHIKI1255/quantumultx-config/release/rules.list)与[HTTP 重写](https://raw.githubusercontent.com/SHIKI1255/quantumultx-config/release/rewrite.list)每 86400 秒刷新；tag 保留 SHIKI1255-Rules / SHIKI1255-Rewrite。不要重复添加资源或设置 force-policy。

主配置保留全部必需段，包括空 [mitm]；基础设置、节点不随远程规则刷新覆盖。本轮不增加机场 Hosts，不改变双 DoH、IPv6 或 UDP 回退。

## 家庭局域网节点

模板内提供一个可选节点 `Home-LAN`（家庭局域网）：SOCKS5，`192.168.5.4:7897`，无认证、无 TLS、关闭 TCP Fast Open，开启节点 UDP 转发（`udp-relay=true`）。该私网地址不包含机场凭据，是公开模板唯一允许的节点例外。

新用户导入主配置模板即可获得声明。已有用户先备份手机配置，在原有 `[server_local]` 段添加下列一行；若已有旧名“家庭局域网”或同名节点则替换原记录，不重复添加配置段或节点，也不覆盖已有机场订阅：

```ini
socks5=192.168.5.4:7897, fast-open=false, udp-relay=true, tag=Home-LAN
```

**仅刷新远程规则不会新增或修改此节点。** 保持 Filter 分流模式，在家手动选择 `Home-LAN`，离家或电脑关闭后切回机场节点；不增加策略组、自动选择或自动回退。手机直连请求仍直接访问，代理请求交给电脑，由电脑 Clash 再次分流。

家庭电脑须开启“允许局域网连接”、运行 Clash 并保持地址固定；手机需能访问该电脑的 7897 端口，并允许应用访问本地网络。只在受信任的家庭局域网使用，不设置公网端口转发。无需更改电脑 TUN、系统代理或 DNS 监听。

节点 UDP 转发已开启，`fallback_udp_policy = reject` 保持不变。开启选项不等于 UDP 端到端已验证；共享入口、防火墙及电脑实际出口都需支持相应流量。手机导入、网页、语音、游戏及切回机场节点需实机验收，UDP 异常时可切回已验证的机场节点。关闭电脑或切换蜂窝网络后，本节点预期不可用。

回退时选回机场节点，或将本地记录恢复为节点名“家庭局域网”、`udp-relay=false`；远程规则和重写资源无需回退。更新前固定版本：[旧版主配置模板](https://raw.githubusercontent.com/SHIKI1255/quantumultx-config/397cd9d5e66908ad7a20b6d7267a52d8fa3366f5/quantumultx.conf)。

## 维护与更新

公共修改只在 https://github.com/SHIKI1255/shadowrocket-config/tree/main/shared 进行。平台 DNS/基础模板在本仓库 config 中；config/shared.json 是协议/分类结构契约，结构变化需要审阅后同步本地模板。

GitHub 每小时第 47 分检查公共版本；有变化、需要恢复或构建代码变化时完整构建，main 修改及普通手动触发仍完整构建。消费者固定公共发布 SHA 并校验数据，只读取资源，不执行远程代码。[当前发布清单](https://raw.githubusercontent.com/SHIKI1255/quantumultx-config/release/manifest.json)中的 shared_version 用于核对三端版本。沿用 30 天维护记录；不承诺构建后手机立即刷新。

下载失败、未知语法/协议、异常增删、未知冲突或用例失败均保留上一版。首次无缓存失败不算安装成功；Clash 必须核对缓存加载。

普通域名规则自动刷新；主配置、资源结构、DNS 架构及适配脚本变化需手动同步。机场订阅和 Hosts 模块仍独立维护，不把私有订阅放到 GitHub。

## 验证与回退

Python 3.12 标准库，Windows 使用 PowerShell 7；Clash 还运行 Node 适配和隔离 Mihomo 检查。

```powershell
python -B -m unittest discover -s tests -v
python -B scripts/build.py --output <新的仓库外目录> --previous-release
python -B scripts/build.py --replay <构建目录> --output <新的离线目录>
```

两次 SHA256SUMS 必须一致。固定版本将 release 替换为发布 SHA；完全冻结还需冻结内部资源地址。恢复本地备份由使用者操作，不自动重载应用。手机解析、实际联网、语音与后台刷新另行验收。

[公共规则与必要平台差异](https://github.com/SHIKI1255/shadowrocket-config/tree/main/shared) · [第三方许可](docs/third_party.md)

有限重试、失败快照、人工审核候选和通知去重见[自动发布异常处理](docs/release-resilience.md)。
