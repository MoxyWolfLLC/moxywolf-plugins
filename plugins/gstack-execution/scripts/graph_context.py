#!/usr/bin/env python3
"""Versioned task context and evidence-only handoffs. No network or execution authority."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import sys

MAX_BYTES = 262144
RELATIONS = {'depends_on', 'implements', 'verifies', 'supports', 'supersedes'}
ATTEST = {'content', 'sha256'}   # content: artifact.content == file at source@revision; sha256: content == 'sha256:'+hexdigest of that file

def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()

def strings(value, label):
    if not isinstance(value, list) or any(not isinstance(x,str) or not x.strip() for x in value) or len(set(value)) != len(value):
        raise ValueError('invalid '+label)
    return value

def validate(manifest):
    if not isinstance(manifest,dict) or manifest.get('schema_version') != 1:
        raise ValueError('context schema_version must be 1')
    if len(json.dumps(manifest).encode()) > MAX_BYTES:
        raise ValueError('context exceeds 262144 bytes')
    if not isinstance(manifest.get('objective'),str) or not manifest['objective'].strip():
        raise ValueError('context objective required')
    artifacts=manifest.get('artifacts')
    if not isinstance(artifacts,list):raise ValueError('context artifacts required')
    index={}
    for a in artifacts:
        if not isinstance(a,dict):raise ValueError('invalid artifact')
        for key in ('id','kind','revision','source','content','reason'):
            if not isinstance(a.get(key),str) or not a[key].strip():raise ValueError('artifact '+key+' required')
        if a['id'] in index:raise ValueError('duplicate artifact '+a['id'])
        if a.get('status') not in {'proposed','accepted','rejected','superseded'}:raise ValueError('invalid artifact status')
        if 'attest' in a and a['attest'] not in ATTEST:raise ValueError('invalid artifact attest')
        if 'binds' in a:
            b=a['binds']
            if not isinstance(b,dict) or not b:raise ValueError('invalid artifact binds')
            for k,v in b.items():
                if not isinstance(k,str):raise ValueError('invalid artifact binds')
                if isinstance(v,str) and v:
                    if a.get('attest'):raise ValueError('attested artifact '+a['id']+' must bind by pointer, not by declared string')
                    continue
                # pointer form: the expected value is read from this artifact's own attested content, so a manifest cannot relabel it
                if isinstance(v,dict) and set(v)=={'pointer'} and isinstance(v['pointer'],str) and v['pointer'].startswith('/') and a.get('attest')=='content':continue
                raise ValueError('invalid artifact binds (a pointer binding needs attest: content)')
        index[a['id']]=a
    if not isinstance(manifest.get('links',[]),list):raise ValueError('invalid links')
    for edge in manifest.get('links',[]):
        if not isinstance(edge,dict) or edge.get('from') not in index or edge.get('to') not in index or edge.get('relation') not in RELATIONS:
            raise ValueError('invalid or dangling context link')
    for a in artifacts:
        for k in (a.get('binds') or {}):
            if k not in index:raise ValueError('artifact '+a['id']+' binds unknown artifact '+k)
            if not any(e['from']==a['id'] and e['to']==k and e['relation']=='depends_on' for e in manifest.get('links',[])):raise ValueError('artifact '+a['id']+' binds '+k+' without a depends_on link')
    if not isinstance(manifest.get('questions',[]),list):raise ValueError('invalid questions')
    qids=set()
    for q in manifest.get('questions',[]):
        if not isinstance(q,dict) or not isinstance(q.get('id'),str) or not q['id'].strip() or q['id'] in qids or not isinstance(q.get('text'),str) or not q['text'].strip() or type(q.get('blocking')) is not bool:
            raise ValueError('invalid question')
        qids.add(q['id'])
        if not set(strings(q.get('artifacts'),'question artifacts')) <= index.keys():raise ValueError('dangling question')
    return index

def attest(artifact,packet):
    """Refuse an artifact whose content no longer matches its source file at its revision.

    Only runs when the artifact declares `attest`. The source is read from the packet repository
    whose head equals the artifact revision, with `git show <revision>:<source>`, so a manifest
    that refreshes `revision` while keeping old `content` is stale, not current. An artifact
    without `attest` stays a declaration, as the contract says."""
    mode=artifact.get('attest')
    if not mode:return
    matches=[r for r in packet['repos'] if r.get('head')==artifact['revision'] and r.get('path')]
    if not matches:raise ValueError('stale attested artifact '+artifact['id']+': its revision is not a packet repository head')
    if len(matches)>1:raise ValueError('attested artifact '+artifact['id']+' revision matches more than one packet repository; ambiguous source')
    repo=matches[0]
    r=subprocess.run(['git','-C',repo['path'],'show',artifact['revision']+':'+artifact['source']],capture_output=True)
    if r.returncode!=0:raise ValueError('attested artifact '+artifact['id']+' source not found at revision')
    actual=r.stdout.decode('utf-8','replace') if mode=='content' else 'sha256:'+hashlib.sha256(r.stdout).hexdigest()
    if actual!=artifact['content']:raise ValueError('stale content for attested artifact '+artifact['id'])

def bound_value(artifact,spec):
    """Read a binding's expected value out of the artifact's own content by JSON pointer.
    The content is attested (see attest), so the value comes from the file at the revision,
    not from the manifest."""
    try:data=json.loads(artifact['content'])
    except ValueError:raise ValueError('pointer binding on non-JSON content for '+artifact['id'])
    for part in spec['pointer'].split('/')[1:]:
        part=part.replace('~1','/').replace('~0','~')
        try:data=data[int(part)] if isinstance(data,list) else data[part]
        except (KeyError,IndexError,ValueError,TypeError):raise ValueError('pointer binding '+spec['pointer']+' not found in '+artifact['id'])
    if not isinstance(data,str) or not data:raise ValueError('pointer binding '+spec['pointer']+' must name a nonempty string in '+artifact['id'])
    return data

def materialize(packet,node):
    selected=strings(node.get('context_inputs',[]),'context_inputs')
    required=strings(node.get('requires_accepted',[]),'requires_accepted')
    if 'context' not in packet:
        if selected or required:raise ValueError('declared context requires manifest')
        return None
    manifest=packet['context'];index=validate(manifest)
    for a in manifest['artifacts']:attest(a,packet)   # every attested artifact, selected or not: a manifest may not carry a tampered artifact nobody reads
    if not set(required)<=set(selected):raise ValueError('requires_accepted must be selected')
    heads={r['head'] for r in packet['repos']}
    for key in selected:
        if key not in index:raise ValueError('missing context artifact '+key)
        a=index[key]
        if a['revision'] not in heads:raise ValueError('stale context artifact '+key)
        if a['status'] in {'rejected','superseded'} or (key in required and a['status']!='accepted'):
            raise ValueError('unaccepted context artifact '+key)
        attest(a,packet)
        for k,v in (a.get('binds') or {}).items():   # a consumer that embeds a prerequisite's content is stale when that prerequisite moved
            expected=bound_value(a,v) if isinstance(v,dict) else v
            if index[k]['content']!=expected:raise ValueError('stale dependency binding '+key+' -> '+k)
    questions=[q for q in manifest.get('questions',[]) if not q['artifacts'] or set(q['artifacts']) & set(selected)]
    for q in questions:
        if q['blocking']:raise ValueError('blocking context question '+q['id'])
    out={'schema_version':1,'authority':'evidence_only','node_id':node['id'],
         'procedure_hash':fingerprint(node),'objective':manifest['objective'],
         'owner':packet.get('owner'),'revisions':packet['repos'],
         'artifacts':[index[k] for k in selected],
         'links':[e for e in manifest.get('links',[]) if e['from'] in selected and e['to'] in selected],
         'questions':questions}
    # Canonical serialization also detaches the handoff from caller-owned mutable objects.
    out=json.loads(json.dumps(out));out['digest']=fingerprint(out)
    return out

def verify(handoff, packet=None, node=None):
    body=dict(handoff);claimed=body.pop('digest',None)
    if body.get('schema_version')!=1 or body.get('authority')!='evidence_only' or claimed!=fingerprint(body):
        raise ValueError('invalid handoff digest or envelope')
    if (packet is None) != (node is None):raise ValueError('packet and node must be supplied together')
    if packet is not None:
        expected=materialize(packet,node)
        if expected is None or expected['digest']!=claimed:raise ValueError('handoff does not match current task')
    return claimed

def impact(manifest,changed):
    index=validate(manifest);affected=set(strings(changed,'changed artifacts'))
    if not affected<=index.keys():raise ValueError('unknown changed artifact')
    while True:
        expanded=affected | {e['from'] for e in manifest.get('links',[]) if e['to'] in affected}
        if expanded==affected:return sorted(affected)
        affected=expanded

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    m=s.add_parser('materialize');m.add_argument('packet');m.add_argument('node')
    v=s.add_parser('verify');v.add_argument('handoff');v.add_argument('--packet');v.add_argument('--node')
    i=s.add_parser('impact');i.add_argument('manifest');i.add_argument('changed',nargs='+')
    a=p.parse_args()
    try:
        load=lambda path:json.loads(Path(path).read_text())
        if a.command=='materialize':out=materialize(load(a.packet),load(a.node))
        elif a.command=='verify':out={'digest':verify(load(a.handoff),load(a.packet) if a.packet else None,load(a.node) if a.node else None),'authority':'evidence_only'}
        else:out={'affected':impact(load(a.manifest),a.changed)}
        print(json.dumps(out,sort_keys=True));return 0
    except (ValueError,KeyError,TypeError,OSError) as e:
        print('refused: '+str(e),file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())
