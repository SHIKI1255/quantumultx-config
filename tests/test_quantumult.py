import copy
import json
import re
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build as b
import quantumult as q


class QuantumultTests(unittest.TestCase):
    def native(self, *lines):
        return [q.convert(b.parse_rule(line)) for line in lines]

    def minimal(self):
        return [b.parse_rule(line) for line in ['DOMAIN,localhost,DIRECT', 'IP-CIDR,::1/128,DIRECT,no-resolve',
                'DOMAIN-SUFFIX,example.com,PROXY', 'GEOIP,CN,DIRECT', 'FINAL,PROXY']]

    def render(self, rules=None, base=None):
        return q.render_bundle(base or (b.ROOT/'config/base.conf').read_text(), rules or self.minimal(), [])

    def test_ipv6_wildcard_and_no_resolve(self):
        rules = self.native('IP-CIDR,2001:4860::/32,PROXY,no-resolve',
                            'IP-ASN,15169,PROXY,no-resolve', 'DOMAIN-WILDCARD,chatgpt-*.azure.com,PROXY')
        self.assertEqual([r.line for r in rules], ['ip6-cidr, 2001:4860::/32, proxy',
                          'ip-asn, 15169, proxy', 'host-wildcard, chatgpt-*.azure.com, proxy'])
        for r in rules: self.assertEqual(q.parse_native(r.line).line, r.line)

    def test_native_expected_rule_guards_after_conversion(self):
        cases = json.loads((b.ROOT/'tests/routing_cases.json').read_text())
        for case in (c for c in cases if 'expected_rule' in c):
            domain = case['input']['domain']
            good = self.native(case['expected_rule'])
            b.check_case_result(case, q.route_native(good, **case['input']), context='Native routing')
            variants = {
                'missing': self.native('FINAL,PROXY'),
                'broader_same_policy': self.native('DOMAIN-SUFFIX,' + domain.rsplit('.', 1)[-1] + ',PROXY'),
                'earlier_direct': self.native('DOMAIN,' + domain + ',DIRECT', case['expected_rule']),
            }
            for reason, rr in variants.items():
                with self.subTest(case=case['name'], reason=reason), self.assertRaises(b.BuildError):
                    b.check_case_result(case, q.route_native(rr, **case['input']), context='Native routing')

    def test_native_unknown_format_family_policy_or_options_fail(self):
        for line in ['ip-cidr, ::1/128, direct', 'ip6-cidr, 1.2.3.4/32, proxy',
                     'host, example.com, proxy, no-resolve', 'host, x.com, secret',
                     'DOMAIN,x.com,PROXY', 'host-regex, .*, proxy']:
            with self.subTest(line=line), self.assertRaises(b.BuildError): q.parse_native(line)

    def test_host_priority_over_user_agent(self):
        rules = self.native('USER-AGENT,Example*,DIRECT', 'DOMAIN-SUFFIX,openai.com,PROXY', 'FINAL,PROXY')
        self.assertEqual(q.route_native(rules, domain='api.openai.com', user_agent='Example/1')['policy'], 'PROXY')
        self.assertEqual(q.route_native(rules, domain='other.test', user_agent='Example/1')['policy'], 'DIRECT')

    def test_dns_dependent_fallback_not_falsely_proven(self):
        rules = self.native('IP-ASN,15169,PROXY,no-resolve', 'GEOIP,CN,DIRECT', 'FINAL,PROXY')
        self.assertEqual(q.route_native(rules, domain='unknown.test')['policy'], 'UNRESOLVED')
        self.assertEqual(q.route_native(rules, ip='1.2.3.4', asn='9999', country='CN')['policy'], 'DIRECT')

    def test_conversion_induced_conflict_stops(self):
        rules = self.native('IP-CIDR,8.8.8.8/32,PROXY,no-resolve', 'IP-CIDR,8.8.8.8/32,DIRECT')
        with self.assertRaises(b.BuildError): q.check_native_conflicts(rules, [])

    def test_bootstrap_final_and_http_rewrites_are_separate(self):
        files, rules, report = self.render()
        self.assertIn(b'ip6-cidr, ::1/128, direct', files['quantumultx.conf'])
        self.assertNotIn(b'::1/128', files['rules.list'])
        self.assertNotIn(b'final,', files['rules.list'])
        self.assertTrue(files['rules.list'].endswith(b'geoip, cn, direct\n'))
        self.assertNotIn(b'url 302', files['quantumultx.conf'])
        self.assertEqual(files['rewrite.list'].count(b'url 302'), 2)
        self.assertNotIn(b'^https', files['rewrite.list'])
        self.assertEqual(report['no_resolve_removed'], 1)
        self.assertEqual(report['local_rules'], 3)

    def test_reproducible_render(self):
        self.assertEqual(self.render(), self.render())

    def test_published_config_has_all_official_modules_without_enabling_mitm(self):
        # Import failed on a real device when mitm was omitted. Check the final
        # artifact, not only the source: rewrite extraction must preserve its tail.
        files, _, _ = self.render()
        config = files['quantumultx.conf'].decode()
        expected = {'general', 'dns', 'policy', 'server_remote', 'server_local',
                    'filter_remote', 'filter_local', 'rewrite_remote', 'rewrite_local',
                    'task_local', 'http_backend', 'mitm'}
        sections = re.findall(r'^\[([^]]+)\]$', config, re.M)
        self.assertEqual(set(sections), expected)
        self.assertEqual(len(sections), len(expected))
        for name in ['task_local', 'http_backend', 'mitm']:
            content = config.split('['+name+']\n', 1)[1].split('\n[', 1)[0]
            self.assertEqual(list(b.records(content)), [])
        self.assertNotIn(b'[mitm]', files['rewrite.list'])
        self.assertNotIn(b'[task_local]', files['rewrite.list'])

    def test_missing_module_or_active_mitm_fails_before_publish(self):
        base = (b.ROOT/'config/base.conf').read_text()
        for name in ['mitm', 'task_local', 'http_backend']:
            with self.subTest(missing=name), self.assertRaises(b.BuildError):
                self.render(base=base.replace('['+name+']\n', ''))
            with self.subTest(active=name), self.assertRaises(b.BuildError):
                self.render(base=base.replace('['+name+']\n', '['+name+']\nhostname = example.com\n'))

    def test_no_remote_force_policy_or_unapproved_parser(self):
        base = (b.ROOT/'config/base.conf').read_text()
        for changed in [base.replace('opt-parser=false', 'opt-parser=true'),
                        base.replace('inserted-resource=false', 'force-policy=proxy'),
                        base.replace('/release/rules.list', '/main/rules.list')]:
            with self.assertRaises(b.BuildError): self.render(base=changed)

    def test_template_dns_ipv6_udp_and_private_nodes_contract(self):
        base = (b.ROOT/'config/base.conf').read_text()
        active = '\n'.join(line for _, line in b.records(base))
        self.assertIn('doh-server = https://dns.alidns.com/dns-query, https://doh.pub/dns-query', active)
        for pattern in ['no-ipv6', 'no-system', 'udp_whitelist', 'udp_drop_list', 'password=', 'p12 =']:
            self.assertNotIn(pattern, active)
        self.assertIn('server = /*.lan/system', active)
        self.assertIn('fallback_udp_policy = reject', active)
        for section in ['policy', 'server_remote', 'server_local', 'task_local', 'http_backend', 'mitm']:
            content = base.split('['+section+']')[1].split('\n[')[0]
            self.assertEqual(list(b.records(content)), [])


if __name__ == '__main__':
    unittest.main()
