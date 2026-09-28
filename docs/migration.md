# Shadowrocket 到 Quantumult X 的迁移差异

基准：SHIKI1255/shadowrocket-config 源码提交 `4e77c7727e5ef1e1b9d6a2e63f3a855c17bf574e`，配置 SHA-256 `70c49c0fb6b7b4521d41268946724ff02e5c0b0bccf606775e182353aaafb503`。首次转换使用相同上游版本；后续每日更新独立进行。

## 规则转换

| 输入 | 输出 | 首次数量 |
| --- | --- | ---: |
| DOMAIN | host | 167 |
| DOMAIN-SUFFIX | host-suffix | 13,618 |
| DOMAIN-KEYWORD | host-keyword | 57 |
| DOMAIN-WILDCARD | host-wildcard | 1 |
| IP-CIDR | ip-cidr / ip6-cidr，按地址族拆分 | 172 / 18 |
| IP-ASN | ip-asn | 5 |
| USER-AGENT | user-agent | 71 |
| GEOIP / FINAL | geoip / final | 1 / 1 |

输入按来源精确去重 262 条后为 14,111 条；原有 42 项策略冲突按已审查清单保留先出现的策略。输出共 14,111 条，未因转换额外删除规则。19 条局域网/DNS 保护规则进入主配置，final 在主配置末尾，其他 14,091 条进入统一远程资源。

195 个 no-resolve 标记明确移除；官方示例未给出对应参数，不能认为 DNS 行为等价。71 条 User-Agent 规则保留，但官方规定 Host 优先于 User-Agent。类型内顺序保留，不扩大后缀、关键词、Azure 通配符的匹配范围。

每次发布的 [migration.json](https://raw.githubusercontent.com/SHIKI1255/quantumultx-config/release/migration.json) 逐项登记 no-resolve、IPv6、User-Agent 和本地规则迁移，含原规则、输出规则、来源及原因。

Python 检查验证显式域名选择器、Host 优先于 User-Agent，以及测试明确提供的 IP/ASN/国家数据。它不模拟原生 DNS、不同类型规则之间所有优先级、GeoIP 数据库或隧道路由。缺少解析证据的网络兜底标为 UNRESOLVED。84 项关键用例及当前 23 个语音 IP 的静态验证不能替代手机请求记录。

## 基础设置

| Shadowrocket 设置 | 迁移结果 |
| --- | --- |
| update-url | 改为 filter_remote/rewrite_remote；主配置手动同步 |
| bypass-system、skip-proxy | 用局域网/本机/认证域名保护规则和系统 DNS 实现对应需求，不宣称系统绕行完全等价 |
| tun-excluded-routes | IPv4 映射 excluded_routes；IPv6 局域网用 ip6-cidr direct，不宣称与内核排除路由等价 |
| dns-server、direct-dns-server、proxy-dns-server | 改为阿里、腾讯双 DoH；代理连接按原生节点侧解析处理 |
| fallback-dns-server、dns-direct-system、dns-direct-fallback-proxy | 不照搬；局域网显式 system，不承诺双 DoH 失败后系统兜底 |
| use-local-host-item-for-proxy | 使用 Quantumult X 原生解析行为，无虚构对应开关 |
| ipv6=true、prefer-ipv6=false | 不设置 no-ipv6，不人为强制 IPv6 优先；实际选路由手机验收 |
| private-ip-answer=true | 不增加丢弃私网答案的 DNS 过滤项 |
| icmp-auto-reply | icmp_auto_reply=true |
| udp-policy-not-supported-behaviour | fallback_udp_policy=reject；不增加端口白名单或 STUN/QUIC 拦截 |
| always-real-ip | dns_exclusion_list，保留原域名范围 |
| Host 的 server:system | server=/域名/system；localhost 交由系统处理，不写禁止的 127.0.0.1 address 映射 |
| URL Rewrite、always-reject-url-rewrite | 仅保留两条 HTTP→HTTPS Google 302；HTTPS 入站重写不在本方案中，不启用 MITM |

DNS、UA、IPv6 与 no-resolve 是明确的兼容差异，不能宣称两个客户端行为完全一致。ChatGPT 语音仍依赖节点 UDP 能力。

依据：[官方配置示例](https://github.com/crossutility/Quantumult-X/blob/master/sample.conf)、[官方匹配说明](https://github.com/crossutility/Quantumult-X/blob/master/README.md)、[官方远程规则示例](https://github.com/crossutility/Quantumult-X/blob/master/filter.snippet)。核对基准为官方仓库提交 `af6fb594233ec4a3ec6d4ccb3601e9c36b75ea2d`。
