"""Explicit native Quantumult X conversion; static checks are not the iOS engine."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import ipaddress
import re

from build import Rule, REPOSITORY, RAW, require, parse_rule, records, route

MAPPING = {
    'DOMAIN': 'host', 'DOMAIN-SUFFIX': 'host-suffix', 'DOMAIN-KEYWORD': 'host-keyword',
    'DOMAIN-WILDCARD': 'host-wildcard', 'USER-AGENT': 'user-agent',
    'IP-CIDR': 'ip-cidr', 'IP-ASN': 'ip-asn', 'GEOIP': 'geoip', 'FINAL': 'final',
}
REVERSE = {v: k for k, v in MAPPING.items()} | {'ip6-cidr': 'IP-CIDR'}
BOOTSTRAP = {
    'localhost', 'lan', 'local', 'home.arpa', 'captive.apple.com',
    'dns.alidns.com', 'doh.pub', 'dns.pub',
    '10.0.0.0/8', '127.0.0.0/8', '169.254.0.0/16', '172.16.0.0/12',
    '192.168.0.0/16', '224.0.0.0/4', '255.255.255.255/32',
    '::1/128', 'fc00::/7', 'fe80::/10', 'ff00::/8',
}


@dataclass(frozen=True)
class NativeRule:
    kind: str
    value: str
    policy: str
    source: str = 'custom'

    @property
    def selector(self):
        return ','.join((self.kind, self.value))

    @property
    def line(self):
        return ', '.join((self.kind, self.policy) if self.kind == 'final'
                         else (self.kind, self.value, self.policy))


def convert(rule: Rule) -> NativeRule:
    require(rule.kind in MAPPING, 'Unknown canonical rule type')
    require(rule.options in {(), ('no-resolve',)}, 'Unknown canonical options')
    kind = MAPPING[rule.kind]
    if rule.kind == 'IP-CIDR' and ipaddress.ip_network(rule.value).version == 6:
        kind = 'ip6-cidr'
    return NativeRule(kind, rule.value.lower() if rule.kind == 'GEOIP' else rule.value,
                      rule.policy.lower(), rule.source)


def parse_native(line: str, source='native') -> NativeRule:
    fields = [p.strip() for p in line.split(',')]
    require(fields[0] in REVERSE, 'Unknown Quantumult X rule type')
    kind = fields[0]
    require(len(fields) == (2 if kind == 'final' else 3), 'Invalid native fields/options')
    require(fields[-1] in {'direct', 'proxy'}, 'Unknown native policy')
    value = '' if kind == 'final' else fields[1]
    canonical_value = value.upper() if kind == 'geoip' else value
    canonical_line = ','.join((REVERSE[kind], fields[-1].upper()) if kind == 'final'
                              else (REVERSE[kind], canonical_value, fields[-1].upper()))
    canonical = parse_rule(canonical_line, source=source)
    require(convert(canonical).kind == kind, 'Wrong IPv4/IPv6 rule family')
    return convert(canonical)


def native_conflicts(rules):
    first, conflicts = {}, set()
    for r in rules:
        prev = first.setdefault(r.selector, r)
        if prev.policy != r.policy:
            conflicts.add((r.selector, prev.policy, prev.source, r.policy, r.source))
    return conflicts


def check_native_conflicts(rules, allowed):
    approved = set()
    for item in allowed:
        fields = item['selector'].split(',')
        line = ','.join([*fields[:2], item['winner'], *fields[2:]])
        r = convert(parse_rule(line))
        approved.add((r.selector, item['winner'].lower(), item['winner_source'],
                      item['later'].lower(), item['later_source']))
    require(native_conflicts(rules) <= approved, 'Unregistered native policy conflict after conversion')


def route_native(rules, **inputs):
    """Validate explicit selectors, host-before-UA, and supplied IP/GeoIP facts.

    Does not emulate DNS, remote insertion, GeoIP databases or tunnel routing.
    Host selectors precede user-agent as documented. Network cases require their
    evidence in inputs; missing evidence remains UNRESOLVED rather than a pass.
    """
    ordered = [r for r in rules if r.kind.startswith('host')]
    ordered += [r for r in rules if r.kind == 'user-agent']
    ordered += [r for r in rules if not r.kind.startswith('host') and r.kind != 'user-agent']
    canonical = []
    for r in ordered:
        canonical.append(Rule(REVERSE[r.kind], r.value.upper() if r.kind == 'geoip' else r.value,
                              r.policy.upper(), (), r.source))
    # A known literal destination needs no domain DNS lookup; ASN/GeoIP are still
    # unknown when not supplied. Exact CIDR matches earlier in order can be proved.
    return route(canonical, **inputs)


def render_lines(rules):
    lines, prior = [], None
    for r in rules:
        if r.source != prior:
            lines.extend(['', '# ' + r.source])
            prior = r.source
        lines.append(r.line)
    return '\n'.join(lines).strip() + '\n'


def render_bundle(base, rules, allowed):
    sections = re.findall(r'^\[([^]]+)\]$', base, re.M)
    require(sections == ['general', 'dns', 'policy', 'server_remote', 'server_local',
                         'filter_remote', 'filter_local', 'rewrite_remote', 'rewrite_local',
                         'task_local', 'http_backend', 'mitm'],
            'Unexpected base sections')
    require(base.count('{{BOOTSTRAP_RULES}}') == 1, 'Missing bootstrap placeholder')
    for name, section in [('rules.list', 'filter_remote'), ('rewrite.list', 'rewrite_remote')]:
        content = base.split('[' + section + ']\n', 1)[1].split('\n[', 1)[0]
        active = [line for _, line in records(content)]
        require(len(active) == 1 and active[0].startswith(RAW + REPOSITORY + '/release/' + name + ','),
                'Wrong remote resource')
        opts = [x.strip() for x in active[0].split(',')[1:]]
        expected = ['tag=SHIKI1255-' + ('Rules' if name == 'rules.list' else 'Rewrite'),
                    'update-interval=86400', 'opt-parser=false']
        if section == 'filter_remote': expected += ['inserted-resource=false']
        expected += ['enabled=true']
        require(opts == expected, 'Unexpected remote parameters, parser or policy override')
    native, changes, seen, duplicates = [], [], set(), 0
    local, remote = [], []
    for index, rule in enumerate(rules, 1):
        r = convert(rule)
        require(parse_native(r.line).line == r.line, 'Native round-trip mismatch')
        target = 'filter_local' if r.kind == 'final' or (r.source == 'custom' and r.value in BOOTSTRAP) else 'rules.list'
        reasons = []
        if rule.options: reasons.append('no-resolve removed; native DNS semantics')
        if r.kind == 'user-agent': reasons.append('lower priority than host in Quantumult X')
        if r.kind == 'ip6-cidr': reasons.append('IPv6 rule family corrected')
        if target == 'filter_local': reasons.append('local bootstrap/final; template sync required')
        if r.line in seen:
            duplicates += 1
            reasons.append('exact native duplicate removed')
        else:
            seen.add(r.line)
            native.append(r)
            (local if target == 'filter_local' else remote).append(r)
        if reasons:
            changes.append({'index': index, 'source': rule.source, 'before': rule.line,
                            'after': r.line, 'target': target, 'reasons': reasons})
    require(len([r for r in local if r.kind == 'final']) == 1 and local[-1].line == 'final, proxy',
            'Invalid final policy')
    require(all(r.policy == 'direct' for r in local[:-1]), 'Bootstrap must stay direct')
    require(remote and remote[-1].line == 'geoip, cn, direct', 'CN fallback must remain last remotely')
    effective = local[:-1] + remote + local[-1:]
    check_native_conflicts(effective, allowed)
    before, remaining = base.split('[rewrite_local]\n', 1)
    rewrite, tail = remaining.split('\n[task_local]\n', 1)
    rewrites = [line for _, line in records(rewrite)]
    require(len(rewrites) == 2, 'Expected two HTTP redirect rules')
    for line in rewrites:
        parts = line.split()
        require(len(parts) == 4 and parts[0].startswith('^http://') and parts[1:3] == ['url', '302']
                and parts[3] == 'https://www.google.com$2', 'Unsupported rewrite change')
        re.compile(parts[0])
    config = (before + '[rewrite_local]\n# HTTP redirects are in the remote resource.\n'
              + '\n[task_local]\n' + tail).replace(
        '{{BOOTSTRAP_RULES}}', render_lines(local[:-1]).strip())
    require(re.findall(r'^\[([^]]+)\]$', config, re.M) == sections,
            'Generated configuration lost required modules')
    for section in ('task_local', 'http_backend', 'mitm'):
        content = config.split('[' + section + ']\n', 1)[1].split('\n[', 1)[0]
        require(not list(records(content)), f'{section} must remain inactive in this template')
    require('{{' not in config, 'Unexpanded template')
    outputs = {'quantumultx.conf': config.encode(), 'rules.list': render_lines(remote).encode(),
               'rewrite.list': ('# HTTP only. MITM is not enabled.\n' + '\n'.join(rewrites) + '\n').encode()}
    report = {'schema_version': 1, 'minimum_client': 'Quantumult X 1.5.5 build 914',
              'input_rules': len(rules), 'native_rules': len(effective),
              'local_rules': len(local), 'remote_rules': len(remote),
              'removed_native_duplicates': duplicates,
              'input_types': dict(sorted(Counter(r.kind for r in rules).items())),
              'native_types': dict(sorted(Counter(r.kind for r in native).items())),
              'no_resolve_removed': sum(bool(r.options) for r in rules),
              'user_agent_priority_changes': sum(r.kind == 'USER-AGENT' for r in rules),
              'changes': changes,
              'runtime_validation': 'UNVERIFIED: iOS parsing, actual priority, DNS, IPv6, UDP, refresh'}
    return outputs, effective, report
