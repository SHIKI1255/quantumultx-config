"""The public LAN endpoint must not open a general private-node escape hatch."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import render_client as renderer
from shared_data import BuildError


class HomeLanTemplate(unittest.TestCase):
    def setUp(self):
        self.base = (ROOT / 'config/base.conf').read_text(encoding='utf-8')
        self.data = {'local_rules_text': 'host, localhost, direct\n',
                     'rules_text': 'host-suffix, example.com, proxy\ngeoip, cn, direct\n', 'report': {}}

    def test_optional_node_preserves_selected_node_routing(self):
        files = renderer.quantumult(self.base, self.data)
        text = files['quantumultx.conf'].decode()
        self.assertEqual(text.count(renderer.HOME_LAN_NODE), 1)
        self.assertTrue(renderer.HOME_LAN_NODE.endswith('tag=Home-LAN'))
        self.assertIn('udp-relay=true', renderer.HOME_LAN_NODE)
        self.assertEqual(files['rules.list'].decode(), self.data['rules_text'])
        self.assertIn('final, proxy', text)
        self.assertIn('fallback_udp_policy = reject', text)
        policy = text.split('[policy]\n')[1].split('\n[')[0]
        self.assertFalse([l for l in policy.splitlines() if l.strip() and not l.startswith('#')])

    def test_other_endpoints_credentials_and_protocol_changes_stop(self):
        node = renderer.HOME_LAN_NODE
        changes = [node + '\n' + node, '', node.replace('192.168.5.4', '203.0.113.1'),
                   node.replace('7897', '1080'), node.replace('socks5=', 'http='),
                   node + ', username=user, password=secret', node + ', over-tls=true',
                   node.replace('udp-relay=true', 'udp-relay=false'),
                   node.replace('Home-LAN', 'other'),
                   node.replace('fast-open=false', 'fast-open=true'),
                   node + '\nsocks5=192.168.5.5:7897, tag=other']
        for changed in changes:
            with self.subTest(changed=changed), self.assertRaises(BuildError):
                renderer.quantumult(self.base.replace(node, changed), self.data)

    def test_duplicate_sections_or_private_subscription_stop(self):
        for changed in [self.base.replace('[server_local]\n', '[server_local]\n[server_local]\n'),
                        self.base.replace('[server_remote]\n', '[server_remote]\nhttps://example.com/sub?token=test\n')]:
            with self.assertRaises(BuildError):
                renderer.quantumult(changed, self.data)
