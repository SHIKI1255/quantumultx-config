"""Local template adapter; shared resources are data, never executable code."""
import json,re
from shared_data import require,json_bytes,records,digest,deterministic_zip

def quantumult(base, data):
    sections = ['general','dns','policy','server_remote','server_local','filter_remote','filter_local',
                'rewrite_remote','rewrite_local','task_local','http_backend','mitm']
    require(re.findall(r'^\[([^]]+)\]$',base,re.M) == sections, 'Missing/duplicate Quantumult X modules')
    require(base.count('{{BOOTSTRAP_RULES}}') == 1, 'Missing bootstrap marker')
    for name in ('policy','server_remote','server_local','task_local','http_backend','mitm'):
        section = base.split('['+name+']\n',1)[1].split('\n[',1)[0]
        require(not list(records(section)), 'Unexpected active private/MITM section')
    for filename, section in [('rules.list','filter_remote'),('rewrite.list','rewrite_remote')]:
        active = [s for _,s in records(base.split('['+section+']\n',1)[1].split('\n[',1)[0])]
        tag = 'SHIKI1255-Rules' if filename == 'rules.list' else 'SHIKI1255-Rewrite'
        expected = 'https://raw.githubusercontent.com/SHIKI1255/quantumultx-config/release/'+filename+', tag='+tag+', update-interval=86400, opt-parser=false'
        if filename == 'rules.list': expected += ', inserted-resource=false'
        expected += ', enabled=true'
        require(active == [expected], 'Unexpected remote parser/policy/order')
    for _,line in records(data['local_rules_text']):
        require(line.endswith(', direct') and not line.startswith(('final,','geoip,')), 'Invalid local protection')
    require(data['rules_text'].endswith('geoip, cn, direct\n') and not any(
        l.startswith('final,') for _,l in records(data['rules_text'])), 'Invalid remote tail')
    before, remaining = base.split('[rewrite_local]\n',1)
    rewrite, tail = remaining.split('\n[task_local]\n',1)
    rewrites = [s for _,s in records(rewrite)]
    require(len(rewrites)==2, 'Expected two HTTP rewrites')
    for line in rewrites:
        fields=line.split()
        require(len(fields)==4 and fields[0].startswith('^http://') and fields[1:3]==['url','302']
                and fields[3]=='https://www.google.com$2', 'Unapproved rewrite')
        re.compile(fields[0])
    text=(before+'[rewrite_local]\n# HTTP redirects are in the remote resource.\n\n[task_local]\n'+tail).replace(
        '{{BOOTSTRAP_RULES}}',data['local_rules_text'].strip())
    require('{{' not in text, 'Unexpanded template')
    return {'quantumultx.conf':text.encode(),'rules.list':data['rules_text'].encode(),
            'rewrite.list':('# HTTP only. MITM is not enabled.\n'+'\n'.join(rewrites)+'\n').encode(),
            'migration.json':json_bytes(data['report'])}

def render(root,client,payload,contract):
    return quantumult((root/"config/base.conf").read_text(encoding="utf-8"),payload["platforms"][client])
