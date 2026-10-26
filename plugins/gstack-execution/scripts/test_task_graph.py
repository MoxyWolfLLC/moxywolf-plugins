"""Exercise the graph CLI with real subprocess workers and temporary repositories."""
import json
import os
import signal
import time
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('task_graph.py')

class GraphTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.repo = self.root/'repo'; self.repo.mkdir()
        self.git('init','-q'); self.git('config','user.email','test@example.invalid'); self.git('config','user.name','Test')
        self.git('config','core.hooksPath','/dev/null')
        (self.repo/'value').write_text('one'); self.git('add','.'); self.git('commit','-qm','one')
        self.sha = self.git('rev-parse','HEAD')
        self.worker=self.root/'worker.py'
        self.worker.write_text('''import json,sys,time,pathlib
p=json.loads(pathlib.Path(sys.argv[-1]).read_text()); n=p['node']; start=time.time()
assert (pathlib.Path(p['snapshots'][0])/'value').read_text() in ('one','two')
time.sleep(n.get('delay',0))
if n.get('barrier'):
    d=pathlib.Path(n['barrier']['dir']); d.mkdir(parents=True,exist_ok=True); (d/n['id']).write_text('')
    t=time.time()+20
    while time.time()<t and not all((d/x).exists() for x in n['barrier']['peers']): time.sleep(.01)
if n.get('log'):
    with open(n['log'],'a') as f: f.write(json.dumps({'id':n['id'],'t':time.time(),'correction':p.get('correction')})+'\\n')
if n.get('fail_once') and not pathlib.Path(n['fail_once']).exists():
    pathlib.Path(n['fail_once']).write_text(''); print('transient boom token=ghp_abcdefghijklmnopqrstuvwxyz1234', file=sys.stderr); sys.exit(3)
if n.get('stray'): pathlib.Path(n['stray']).parent.mkdir(parents=True,exist_ok=True); pathlib.Path(n['stray']).write_text('{}')
if n.get('fail_if_exists') and pathlib.Path(n['fail_if_exists']).exists(): print('upstream wobble',file=sys.stderr); sys.exit(3)
if n.get('fail'): print('boom at '+repr(time.time()),file=sys.stderr); sys.exit(3)
if n.get('bad_shape_once') and not pathlib.Path(n['bad_shape_once']).exists():
    pathlib.Path(n['bad_shape_once']).write_text(''); print(json.dumps(n['bad_shape'])); sys.exit(0)
r={'complete':True,'coverage':n['checks'],'evidence':['value:1'],'findings':[], 'summary':n['id']}
if n.get('finding'): r['findings']=[{'id':'F1','status':'TENTATIVE','detail':'candidate','evidence':['value:1']}]
if n.get('missing'): r['coverage']=[]
if n.get('claim_status'): r['findings']=[{'id':n['claim_id'],'status':n['claim_status'],'detail':'claim result','evidence':['value:1']}]
if n.get('kind')=='checker': r['findings']=[dict(f,status='VERIFIED') for f in p['candidates']]
if n.get('malformed'): r['findings']=[dict(f,status='BOGUS',evidence=[None]) for f in p['candidates']]
r['interval']=[start,time.time()]
if n.get('stable'): r.pop('interval')
print(json.dumps(r))
''')
        self.command=[sys.executable,str(self.worker)]
        self.policy={'owner':'dorianatmoxywolf','allowed_tools':['claude','codex'], 'allow_repository':True,'allow_history':True,
                     'allowed_commands':[self.command], 'output_roots':[str(self.root)], 'classification':'internal'}
        self.packet={'owner':'dorianatmoxywolf','builder':'codex','repos':[{'path':str(self.repo),'base':self.sha,'head':self.sha}],
                     'claims':[{'id':'C1','text':'value exists'}], 'spec':'value exists','scope':'all','data_use':self.policy}
        self.pfile=self.root/'packet.json';self.wfile=self.root/'workflow.json';self.run=self.root/'run'
        self.graph={'name':'fixture','nodes':[self.node('prepare'),self.node('a',['prepare'],finding=True,delay=.3),self.node('b',['prepare'],finding=True,delay=.3),self.node('check',['a','b'],kind='checker'),self.node('report',['prepare','a','b','check'],kind='report',findings_from=['check'])]}
    def ok(self,r):
        """XE-024: an executor call that should succeed. A bare 1 != 0 threw the stderr away,
        and an intermittent failure then left nothing to diagnose it with."""
        self.assertEqual(r.returncode,0,'executor stderr:\n'+(r.stderr or '')[-4000:]+'\nstdout:\n'+(r.stdout or '')[-4000:])
    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.repo),*args],text=True).strip()
    def node(self,id,deps=None,kind='worker',**extra):
        deps=deps or []
        return dict(id=id,depends_on=deps,inputs=deps+['packet'],outputs=[id+'.json'],effects=['local_report'] if kind=='report' else ['external_review'],on_failure='block',kind=kind,checks=[id],command=self.command,**extra)
    def call(self,*args):
        return subprocess.run([sys.executable,str(SCRIPT),*args],text=True,capture_output=True)
    def execute(self,cap=2,audit=False,grants=None):
        self.pfile.write_text(json.dumps(self.packet));self.wfile.write_text(json.dumps(self.graph))
        args=['run','--workflow',str(self.wfile),'--packet',str(self.pfile),'--run-dir',str(self.run),'--jobs',str(cap)]
        if audit:args.append('--audit-writes')
        if grants:args+=['--grants',str(grants)]
        return self.call(*args)

    def test_context_is_delivered_and_stale_context_blocks_all_workers(self):
        self.packet['context']={'schema_version':1,'objective':'test','artifacts':[
            {'id':'design','kind':'design','revision':self.sha,'status':'accepted',
             'source':'DESIGN.md','content':'criteria','reason':'specification'}]}
        self.graph['nodes'][0].update(context_inputs=['design'],requires_accepted=['design'])
        self.worker.write_text(self.worker.read_text().replace("n=p['node']; start=time.time()", "n=p['node']; start=time.time()\nif n['id']=='prepare': assert p['context']['artifacts'][0]['id']=='design'"))
        self.ok(self.execute())
        report=json.loads((self.run/'report.json').read_text())
        self.assertEqual(report['context_handoffs']['prepare']['artifacts'][0]['id'],'design')
        before=(self.run/'events.jsonl').read_text()
        self.packet['context']['artifacts'][0]['revision']='b'*40
        result=self.execute()
        self.assertNotEqual(result.returncode,0)
        self.assertIn('stale context artifact',result.stderr)
        self.assertEqual((self.run/'events.jsonl').read_text(),before)

    def test_every_context_refusal_starts_zero_workers_and_makes_no_run_directory(self):
        """Goal gstack-delivery-through-merge, item 1: each refusal is raised by preflight, before
        root.mkdir and before any worker command, so the run directory never appears and the worker
        log is never written. Cases: stale attested source, refreshed revision with stale content,
        moved prerequisite with an unchanged consumer pointer binding, ambiguous repository
        selection, and tampering with a selected and with an unselected attested artifact."""
        import hashlib
        sha256=lambda b:'sha256:'+hashlib.sha256(b).hexdigest()
        log=self.root/'workers.log'
        (self.repo/'fx.json').write_text(json.dumps({'bank':{'bank_hash':sha256(b'one')}}))
        self.git('add','.');self.git('commit','-qm','fx');h1=self.git('rev-parse','HEAD')
        (self.repo/'value').write_text('two');self.git('commit','-qam','two');h2=self.git('rev-parse','HEAD')
        def artifact(id,source,content,rev,attest='content',**extra):
            return dict(id=id,kind='evidence',revision=rev,status='accepted',source=source,content=content,reason='r',attest=attest,**extra)
        def manifest(rev,value_content,fx_content):
            return {'schema_version':1,'objective':'refuse','artifacts':[
                artifact('value','value',value_content,rev,attest='sha256'),
                artifact('fx','fx.json',fx_content,rev,binds={'value':{'pointer':'/bank/bank_hash'}})],
                'links':[{'from':'fx','relation':'depends_on','to':'value'}]}
        fx1=(self.repo/'fx.json').read_text()
        def packet(rev,ctx,repos=None):
            return dict(self.packet,repos=repos or [{'path':str(self.repo),'base':rev,'head':rev}],context=ctx)
        twin=self.root/'twin';subprocess.check_call(['git','clone','-q',str(self.repo),str(twin)])
        cases={
            'stale attested source': (packet(h1,manifest(h1,sha256(b'stale'),fx1)),'stale content for attested artifact value'),
            'refreshed revision with stale content': (packet(h2,manifest(h2,sha256(b'one'),fx1)),'stale content for attested artifact value'),
            'moved prerequisite, consumer pointer unchanged': (packet(h2,manifest(h2,sha256(b'two'),fx1)),'stale dependency binding fx -> value'),
            'ambiguous repository selection': (packet(h1,manifest(h1,sha256(b'one'),fx1),repos=[{'path':str(self.repo),'base':h1,'head':h1},{'path':str(twin),'base':h1,'head':h1}]),'more than one packet repository'),
            'selected artifact tampered': (packet(h1,manifest(h1,sha256(b'one'),fx1.replace(sha256(b'one'),sha256(b'x')))),'stale content for attested artifact fx'),
            'unselected artifact tampered': (packet(h1,manifest(h1,sha256(b'one'),fx1.replace(sha256(b'one'),sha256(b'x')))),'stale content for attested artifact fx'),
        }
        for name,(pk,message) in cases.items():
            with self.subTest(case=name):
                selected=['value'] if name.startswith('unselected') else ['value','fx']
                graph={'name':'fixture','nodes':[self.node('prepare',log=str(log),context_inputs=selected,requires_accepted=selected),self.node('report',['prepare'],kind='report',log=str(log))]}
                run=self.root/('run-'+str(len(name)))
                self.pfile.write_text(json.dumps(pk));self.wfile.write_text(json.dumps(graph))
                r=self.call('run','--workflow',str(self.wfile),'--packet',str(self.pfile),'--run-dir',str(run),'--jobs','2')
                self.assertNotEqual(r.returncode,0,r.stdout)
                self.assertIn(message,r.stderr)
                self.assertFalse(run.exists(),'run directory was created before the refusal')
                self.assertFalse(log.exists(),'a worker started before the refusal')
        # The same graph with fresh, consistent evidence proceeds: the refusals are about the evidence, not the shape.
        fresh=packet(h1,manifest(h1,sha256(b'one'),fx1))
        graph={'name':'fixture','nodes':[self.node('prepare',log=str(log),context_inputs=['value','fx'],requires_accepted=['value','fx']),self.node('report',['prepare'],kind='report')]}
        self.pfile.write_text(json.dumps(fresh));self.wfile.write_text(json.dumps(graph))
        self.ok(self.call('run','--workflow',str(self.wfile),'--packet',str(self.pfile),'--run-dir',str(self.run),'--jobs','2'))
        self.assertTrue(log.exists())

    def test_audit_fails_a_node_writing_outside_its_declared_outputs(self):
        """EV-003. A real edge that was never declared: the validator compares
        declarations against each other, so it has nothing to compare and the write is
        invisible until something runs beside it."""
        self.graph['nodes'][1]['stray']=str(self.run/'reviews'/'sneaky.json')
        r=self.execute(audit=True)
        self.assertEqual(r.returncode,1,r.stdout)
        self.assertIn('a',json.loads(r.stdout)['failed'])
        self.assertIn('undeclared write by a',self.state()['nodes']['a']['error'])
        self.assertIn('reviews/sneaky.json',self.state()['nodes']['a']['error'])

    def test_audit_passes_a_graph_whose_handlers_write_only_what_they_declare(self):
        """The sweep has to be quiet on a clean graph or nobody will run it."""
        r=self.execute(audit=True)
        self.ok(r)
        self.assertEqual(self.state()['outcome'],'complete')

    def test_audit_forces_serial_execution(self):
        """Attributing a write to a node while another node is writing would be a
        declaration that can be false, which is the defect this is meant to find."""
        r=self.execute(cap=4,audit=True)
        self.ok(r)
        a=self.state()['nodes']['a']['result']['interval'];b=self.state()['nodes']['b']['result']['interval']
        self.assertFalse(max(a[0],b[0])<min(a[1],b[1]),'audit mode must not overlap nodes')

    def _tg(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('tg',SCRIPT);tg=importlib.util.module_from_spec(spec);spec.loader.exec_module(tg);return tg

    def test_the_executor_owned_files_are_excluded_where_the_snapshot_is_taken(self):
        """The exclusion lives in tree_digest and only there. Repeating it inside
        undeclared_writes would give one rule two homes, which is how a rule gets
        changed in one place and silently kept in the other."""
        tg=self._tg();d=self.root/'snap';(d/'reviews').mkdir(parents=True)
        for name in ('state.json','packet.json','graph.json','run.lock','a.json'):(d/name).write_text('{}')
        (d/'reviews'/'r.json').write_text('{}')
        self.assertEqual(sorted(tg.tree_digest(d)),['a.json','reviews/r.json'])

    def test_f5_hidden_paths_and_lock_files_are_not_exempt_from_the_sweep(self):
        """Exempting every hidden path and every .lock handed a handler two places to
        write unobserved. Blocker F5 of review 20260912-122421-80159e3-_lrr97ak."""
        tg=self._tg();d=self.root/'snap2';(d/'.hidden').mkdir(parents=True)
        for name in ('state.json','run.lock','.hidden/evil.json','handler.lock','ok.json'):(d/name).write_text('{}')
        seen=sorted(tg.tree_digest(d))
        self.assertEqual(seen,['.hidden/evil.json','handler.lock','ok.json'])
        self.assertNotIn('state.json',seen);self.assertNotIn('run.lock',seen)

    def test_undeclared_writes_reports_creations_and_modifications_only(self):
        tg=self._tg();node={'id':'n','outputs':['n.json']}
        self.assertEqual(tg.undeclared_writes({},{'n.json':'aa'},node),[],'a declared output is not undeclared')
        self.assertEqual(tg.undeclared_writes({},{'extra.json':'cc'},node),['extra.json'])
        self.assertEqual(tg.undeclared_writes({'extra.json':'cc'},{'extra.json':'cc'},node),[],'unchanged files are not writes')
        self.assertEqual(tg.undeclared_writes({'extra.json':'cc'},{'extra.json':'dd'},node),['extra.json'],'a modification is a write')
    def state(self): return json.loads((self.run/'state.json').read_text())
    def test_diamond_overlaps_and_preserves_all_findings(self):
        # Each sibling waits for the other's marker, so they overlap when run concurrently and time out
        # (and fail the overlap below) when run serially. A bare sleep raced process start-up on slow CI.
        for n in self.graph['nodes'][1:3]: n['barrier']={'dir':str(self.root/'barrier'),'peers':['a','b']}
        r=self.execute();self.ok(r)
        s=self.state(); a=s['nodes']['a']['result'];b=s['nodes']['b']['result']
        self.assertLess(max(a['interval'][0],b['interval'][0]),min(a['interval'][1],b['interval'][1]))
        report=json.loads((self.run/'report.json').read_text())
        self.assertEqual({f['id'] for f in report['findings']},{'a:F1','b:F1'})
        self.assertEqual(report['sources']['a']['findings'][0]['status'],'TENTATIVE')
    def test_report_requires_explicit_sources_before_dispatch(self):
        self.graph['nodes'][-1]['depends_on']=['check']
        self.graph['nodes'][-1]['inputs']=['packet','check']
        r=self.execute()
        self.assertNotEqual(r.returncode,0)
        self.assertFalse((self.run/'state.json').exists())

    def test_report_finding_selection_must_be_declared(self):
        self.graph['nodes'][-1]['findings_from']=['absent']
        r=self.execute()
        self.assertNotEqual(r.returncode,0)
        self.assertFalse((self.run/'state.json').exists())

    def test_report_consumes_only_passed_inputs_without_state(self):
        import task_graph
        deps={'check':{'findings':[], 'evidence':['declared']}}
        node=self.node('report',['check'],kind='report')
        result=task_graph.worker(node,self.packet,deps,self.root/'no-state')
        self.assertEqual(result['sources'],deps)

    def test_serial_cap_and_shared_proofs(self):
        for n in self.graph['nodes'][1:3]: n['effects']=['local_proof']
        r=self.execute(4);self.ok(r)
        s=self.state();a=s['nodes']['a']['result']['interval'];b=s['nodes']['b']['result']['interval']
        self.assertGreaterEqual(max(a[0],b[0]),min(a[1],b[1]))
    def test_invalid_graphs_are_refused_before_dispatch(self):
        import copy
        base=copy.deepcopy(self.graph)
        for defect in ['cycle','missing','writer','effect','input']:
            self.graph=copy.deepcopy(base)
            if defect=='cycle': self.graph['nodes'][0]['depends_on']=['a'];self.graph['nodes'][0]['inputs']=['packet','a']
            if defect=='missing':self.graph['nodes'][1]['depends_on']=['absent']
            if defect=='writer':self.graph['nodes'][1]['outputs']=['prepare.json']
            if defect=='effect':self.graph['nodes'][1]['effects']=['merge']
            if defect=='input':self.graph['nodes'][1]['inputs']=['packet','b']
            r=self.execute();self.assertNotEqual(r.returncode,0,defect)
            self.assertFalse((self.run/'report.json').exists())
    def test_worker_failure_and_missing_coverage_never_pass(self):
        for flag in ['fail','missing']:
            self.graph['nodes'][1][flag]=True
            r=self.execute();self.assertNotEqual(r.returncode,0)
            self.assertEqual(self.state()['outcome'],'incomplete')
            self.assertNotEqual(self.state()['nodes'].get('report',{}).get('status'),'succeeded')
            self.graph['nodes'][1].pop(flag)
    def dispatches(self,log):
        rows=[json.loads(l) for l in log.read_text().splitlines()];by={}
        for x in rows:by.setdefault(x['id'],[]).append(x)
        return rows,by
    def test_a_retrying_node_recovers_and_its_green_sibling_never_moves(self):
        """XE-036 criterion 8, first case. Fails at d81d9fc, where validate_graph refuses `retry`."""
        log=self.root/'dispatches.jsonl'
        for n in self.graph['nodes']:n['log']=str(log)
        a=self.graph['nodes'][1];a.update(on_failure='retry',max_attempts=3,fail_once=str(self.root/'a.failed-once'))
        self.ok(self.execute())
        rows,by=self.dispatches(log)
        self.assertEqual({k:len(v) for k,v in by.items()},{'prepare':1,'a':2,'b':1,'check':1})
        self.assertGreater(by['check'][0]['t'],max(by['a'][1]['t'],by['b'][0]['t']))
        s=self.state();self.assertEqual(s['outcome'],'complete')
        self.assertEqual((s['nodes']['b']['attempts'],s['nodes']['report']['attempts']),(1,1))
        self.assertEqual(s['nodes']['b']['result_hash'],__import__('hashlib').sha256(json.dumps(json.loads((self.run/'b.json').read_text()),sort_keys=True).encode()).hexdigest())
        self.assertIsNone(by['a'][0]['correction'])
        c=by['a'][1]['correction']
        self.assertEqual((c['node'],c['previous_attempt'],c['category']),('a',1,'handler_exit'))
        self.assertEqual(c['signature'],s['nodes']['a']['signature'])
        self.assertIn('transient boom',c['diagnostics']);self.assertNotIn('ghp_abcdefghij',c['diagnostics'])
        # F1 (review 20261012-212850): the planted token must be absent everywhere, not only from the excerpt
        for name,text in (('correction',json.dumps(c)),('state.json',(self.run/'state.json').read_text()),('events.jsonl',(self.run/'events.jsonl').read_text()),('input log',log.read_text())):
            self.assertNotIn('ghp_abcdefghij',text,name)
        self.assertEqual(c['reason'],'worker exited 3')
        self.assertEqual(c['scope'],{'repos':[{'path':str(self.repo.resolve()),'head':self.sha}],'checks':a['checks'],'depends_on':a['depends_on'],'effects':a['effects'],'outputs':a['outputs']})
        cycle=s['nodes']['a']['cycle'];self.assertEqual(cycle['dispatches'],2)
        self.assertEqual([h['status'] for h in cycle['history']],['failed','succeeded']);self.assertEqual(cycle['history'][0]['category'],'handler_exit')
        self.assertTrue(Path(cycle['history'][0]['diagnostics']).is_file())
        events=[json.loads(l) for l in (self.run/'events.jsonl').read_text().splitlines()]
        kinds=[e['action'] for e in events if e.get('node')=='a']
        self.assertEqual(kinds,['node-start','node-failed','node-retry','node-start','node-succeeded'])
        self.assertTrue(all(e.get('signature') for e in events if e.get('node')=='a'))
        report=json.loads((self.run/'report.json').read_text())
        self.assertEqual({f['id'] for f in report['findings']},{'a:F1','b:F1'});self.assertEqual(set(report['sources']),{'prepare','a','b','check'})
    def events(self,node=None):
        rows=[json.loads(l) for l in (self.run/'events.jsonl').read_text().splitlines()]
        return [r for r in rows if node is None or r.get('node')==node]
    def test_an_always_failing_retry_node_stops_at_its_budget_and_stays_stopped(self):
        log=self.root/'dispatches.jsonl'
        for n in self.graph['nodes']:n['log']=str(log)
        self.graph['nodes'][1].update(on_failure='retry',fail=True)
        r=self.execute();self.assertNotEqual(r.returncode,0)
        rows,by=self.dispatches(log);self.assertEqual(len(by['a']),3);self.assertEqual(len(by['b']),1)
        s=self.state();self.assertEqual(s['outcome'],'incomplete');self.assertEqual(s['nodes']['a']['status'],'failed')
        self.assertEqual((s['nodes']['check']['status'],s['nodes']['report']['status']),('blocked','blocked'))
        self.assertEqual(s['nodes']['a']['cycle']['dispatches'],3);self.assertEqual(s['nodes']['a']['cycle']['closed'],'handler_exit')
        self.assertEqual([e['action'] for e in self.events('a')],['node-start','node-failed','node-retry','node-start','node-failed','node-retry','node-start','node-failed','node-exhausted'])
        self.assertFalse((self.run/'report.json').exists())
        self.assertNotEqual(self.call('export','--run-dir',str(self.run),'--output',str(self.root/'out.json')).returncode,0)
        r=self.execute();self.assertNotEqual(r.returncode,0)
        rows,by=self.dispatches(log);self.assertEqual(len(by['a']),3,'resume bought a fourth dispatch');self.assertEqual(len(by['b']),1)
        self.assertEqual(self.state()['nodes']['b']['attempts'],1)
    def test_an_interrupted_dispatch_is_counted_and_green_work_is_not_repeated(self):
        log=self.interrupt_a(2)
        self.ok(self.execute())
        s=self.state();cycle=s['nodes']['a']['cycle']
        self.assertEqual(cycle['dispatches'],2);self.assertEqual([h['status'] for h in cycle['history']],['interrupted','succeeded'])
        self.assertEqual(s['nodes']['b']['attempts'],1);self.assertEqual(s['nodes']['a']['attempts'],2)
        rows,by=self.dispatches(log);self.assertEqual(len(by['b']),1)
        self.assertEqual(by['a'][-1]['correction']['category'],'interrupted')
        failed=[e for e in self.events('a') if e['action']=='node-failed'];self.assertEqual([(e['category'],e['attempt'],e['retry']) for e in failed],[('interrupted',1,True)])
    def test_block_still_performs_no_retry(self):
        self.graph['nodes'][1]['fail_once']=str(self.root/'a.failed-once')
        r=self.execute();self.assertNotEqual(r.returncode,0)
        s=self.state();self.assertEqual(s['nodes']['a']['attempts'],1);self.assertEqual(s['nodes']['a']['cycle']['dispatches'],1)
        self.assertNotIn('node-retry',[e['action'] for e in self.events()]);self.assertEqual(s['nodes']['check']['status'],'blocked')
    def test_invalid_retry_declarations_are_refused_before_dispatch(self):
        log=self.root/'dispatches.jsonl'
        for n in self.graph['nodes']:n['log']=str(log)
        cases=[('a',{'on_failure':'bogus'}),('a',{'on_failure':'retry','max_attempts':4}),('a',{'on_failure':'retry','max_attempts':0}),
               ('a',{'on_failure':'retry','max_attempts':True}),('a',{'on_failure':'retry','max_attempts':'3'}),('report',{'on_failure':'retry'})]
        for id,change in cases:
            node=next(n for n in self.graph['nodes'] if n['id']==id);saved=dict(node);node.update(change)
            r=self.execute();self.assertNotEqual(r.returncode,0,change);self.assertFalse((self.run/'state.json').exists(),change)
            node.clear();node.update(saved)
        self.packet['proofs']=[{'id':'t','argv':[sys.executable,'-c','pass']}];self.packet['data_use']['allowed_commands'].append(self.packet['proofs'][0]['argv'])
        proof=self.node('proof',['prepare'],kind='proof',argv=self.packet['proofs'][0]['argv']);proof.pop('command');proof.update(effects=['local_proof'],on_failure='retry')
        self.graph['nodes'].insert(1,proof)
        for n in self.graph['nodes'][-2:]:n['depends_on'].append('proof');n['inputs'].append('proof')
        r=self.execute();self.assertNotEqual(r.returncode,0);self.assertIn('retry is not accepted on proof',r.stderr)
        self.assertFalse(log.exists(),'a refused graph dispatched a worker')
    def test_negative_findings_are_results_and_never_retried(self):
        self.graph['nodes'][1].update(on_failure='retry',claim_id='C1',claim_status='MISSING',finding=False)
        self.packet['proofs']=[{'id':'t','argv':[sys.executable,'-c','raise SystemExit(1)']}];self.packet['data_use']['allowed_commands'].append(self.packet['proofs'][0]['argv'])
        proof=self.node('proof',['prepare'],kind='proof',argv=self.packet['proofs'][0]['argv']);proof.pop('command');proof['effects']=['local_proof']
        self.graph['nodes'].insert(1,proof)
        for n in self.graph['nodes'][-2:]:n['depends_on'].append('proof');n['inputs'].append('proof')
        self.ok(self.execute())
        s=self.state();self.assertEqual(s['nodes']['a']['result']['findings'][0]['status'],'MISSING');self.assertEqual(s['nodes']['a']['cycle']['dispatches'],1)
        self.assertEqual(s['nodes']['proof']['result']['findings'][0]['status'],'FAILED');self.assertEqual(s['nodes']['proof']['attempts'],1)
        self.assertNotIn('node-retry',[e['action'] for e in self.events()])
    def test_governance_failures_get_no_correction_attempt(self):
        self.graph['nodes'][1]['on_failure']='retry'
        self.packet['data_use']['allowed_commands']=[]
        r=self.execute();self.assertNotEqual(r.returncode,0);self.assertIn('data_use',r.stderr);self.assertFalse((self.run/'state.json').exists())
        self.packet['data_use']['allowed_commands']=[self.command]
        self.graph['nodes'][1]['stray']=str(self.run/'rogue.json')
        r=self.execute(audit=True);self.assertNotEqual(r.returncode,0)
        s=self.state();a=s['nodes']['a'];self.assertEqual(a['status'],'failed');self.assertEqual(a['cycle']['dispatches'],1)
        self.assertEqual(a['cycle']['history'][0]['category'],'undeclared_write');self.assertEqual(a['cycle']['closed'],'undeclared_write')
        self.assertNotIn('node-retry',[e['action'] for e in self.events()])
        # F2 (review 20261012-212850): a handler that writes where it shouldn't and THEN fails is still an undeclared write, never a retry
        self.run=self.root/'run2';self.graph['nodes'][1].update(stray=str(self.run/'rogue.json'),fail=True)
        r=self.execute(audit=True);self.assertNotEqual(r.returncode,0)
        a=self.state()['nodes']['a'];self.assertEqual(a['cycle']['dispatches'],1);self.assertEqual(a['cycle']['history'][0]['category'],'undeclared_write')
        self.assertIn('handler then failed',a['error']);self.assertNotIn('node-retry',[e['action'] for e in self.events()])
        self.assertTrue(Path(a['cycle']['history'][0]['diagnostics']).is_file(),'the original failure diagnostics are kept')
    def test_invalidation_still_works_and_prior_cycles_survive(self):
        self.graph['nodes'][1].update(on_failure='retry',fail_once=str(self.root/'a.failed-once'))
        self.ok(self.execute());self.assertEqual(self.state()['nodes']['a']['cycle']['dispatches'],2)
        (self.run/'a.json').write_text('{}');self.ok(self.execute())
        s=self.state();self.assertEqual(s['nodes']['a']['cycle']['dispatches'],3,'a tampered output is re-dispatched under the same signature');self.assertEqual(s['nodes']['b']['attempts'],1)
        first=s['nodes']['a']['cycle']
        (self.repo/'value').write_text('two');self.git('commit','-qam','two');self.packet['repos'][0]['head']=self.git('rev-parse','HEAD')
        self.ok(self.execute())
        s=self.state();a=s['nodes']['a'];self.assertNotEqual(a['cycle']['signature'],first['signature']);self.assertEqual(a['cycle']['dispatches'],1)
        self.assertEqual(a['cycles_prior'][0],first);self.assertEqual([h['status'] for h in first['history']],['failed','succeeded','succeeded'])
        self.assertTrue(Path(first['history'][0]['diagnostics']).is_file(),'the first failure\'s diagnostics outlived two later successes')
        second=a['cycle'];self.graph['nodes'][0]['finding']=True   # prepare changes, so a's dependency result changes
        self.ok(self.execute())
        a=self.state()['nodes']['a'];self.assertNotEqual(a['cycle']['signature'],second['signature']);self.assertEqual(a['cycles_prior'][:2],[second,first])
        self.assertEqual(self.state()['nodes']['check']['attempts'],4)
    def test_an_earlier_cycles_diagnostics_are_never_overwritten(self):
        # F3 (review 20261012-212850): attempt 1 fails in two cycles; the first excerpt must survive the second byte for byte
        self.graph['nodes'][0]['stable']=True;self.graph['nodes'][1].update(on_failure='retry',max_attempts=1,fail=True)
        self.assertNotEqual(self.execute().returncode,0)
        first=self.state()['nodes']['a']['cycle'];p1=Path(first['history'][0]['diagnostics']);b1=p1.read_bytes();self.assertIn(b'boom at',b1)
        (self.repo/'value').write_text('two');self.git('commit','-qam','two');self.packet['repos'][0]['head']=self.git('rev-parse','HEAD')
        self.assertNotEqual(self.execute().returncode,0)
        a=self.state()['nodes']['a'];p2=Path(a['cycle']['history'][0]['diagnostics'])
        self.assertNotEqual(p1,p2);self.assertEqual(p1.read_bytes(),b1);self.assertNotEqual(p2.read_bytes(),b1);self.assertEqual(a['cycles_prior'][0],first)
        # F3 (round 2): A -> B -> A. The returning signature resumes its own closed cycle: no dispatch, no overwrite.
        second=a['cycle'];self.packet['repos'][0]['head']=self.sha
        self.assertNotEqual(self.execute().returncode,0);a=self.state()['nodes']['a']
        self.assertEqual(a['cycle'],first,'the first cycle came back untouched');self.assertEqual(a['cycles_prior'],[second])
        self.assertEqual(p1.read_bytes(),b1);self.assertEqual(self.events('a')[-1]['action'],'node-exhausted')
    def test_an_exhausted_dependent_stays_exhausted_through_an_upstream_wobble(self):
        # F4 (review 20261012-212850): blocking a node must not drop its cycle, or a recovered upstream hands it a fresh budget
        log=self.root/'dispatches.jsonl'
        for n in self.graph['nodes']:n['log']=str(log)
        marker=self.root/'wobble';self.graph['nodes'][0].update(stable=True,fail_if_exists=str(marker))
        self.graph['nodes'][1].update(on_failure='retry',fail=True)
        self.assertNotEqual(self.execute().returncode,0);self.assertEqual(self.state()['nodes']['a']['cycle']['dispatches'],3)
        (self.run/'prepare.json').write_text('{}');marker.write_text('')
        self.assertNotEqual(self.execute().returncode,0);a=self.state()['nodes']['a'];self.assertEqual(a['status'],'blocked');self.assertEqual(a['cycle']['dispatches'],3)
        marker.unlink()
        self.assertNotEqual(self.execute().returncode,0);a=self.state()['nodes']['a']
        self.assertEqual(a['cycle']['dispatches'],3);self.assertEqual(len(self.dispatches(log)[1]['a']),3,'a recovered upstream bought a fourth dispatch')
        self.assertEqual(self.state()['nodes']['prepare']['attempts'],3)
    def test_a_predictable_bad_shape_is_an_invalid_result_and_retries(self):
        # F5 (review 20261012-212850): [] / coverage [[]] / findings [None] are refused results, not unclassified executor crashes
        for i,shape in enumerate([[],{'complete':True,'coverage':[[]],'evidence':['x'],'findings':[],'summary':'s'},{'complete':True,'coverage':['a'],'evidence':['x'],'findings':[None],'summary':'s'},None]):
            self.run=self.root/('run%d'%i);self.graph['nodes'][1].update(on_failure='retry',bad_shape_once=str(self.root/('shape%d'%i)),bad_shape=shape)
            self.ok(self.execute());a=self.state()['nodes']['a']
            self.assertEqual([h['status'] for h in a['cycle']['history']],['failed','succeeded'],shape);self.assertEqual(a['cycle']['history'][0]['category'],'invalid_result',shape)
    def interrupt_a(self,cap):
        log=self.root/'dispatches.jsonl'
        for n in self.graph['nodes']:n['log']=str(log)
        self.graph['nodes'][1].update(on_failure='retry',max_attempts=cap,delay=6)
        self.pfile.write_text(json.dumps(self.packet));self.wfile.write_text(json.dumps(self.graph))
        proc=subprocess.Popen([sys.executable,str(SCRIPT),'run','--workflow',str(self.wfile),'--packet',str(self.pfile),'--run-dir',str(self.run),'--jobs','2'],text=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        deadline=time.time()+20
        while time.time()<deadline:
            try:
                s=self.state()
                if s['nodes'].get('a',{}).get('status')=='running' and s['nodes'].get('b',{}).get('status')=='succeeded':break
            except (OSError,ValueError):pass
            time.sleep(.05)
        else:proc.kill();self.fail('a never reached running while b succeeded')
        proc.kill();proc.wait();return log
    def test_an_interruption_in_the_final_slot_is_recorded_and_exhausts(self):
        # F6 (review 20261012-212850): the interrupted attempt is a failure event, and it can be the one that spends the budget
        log=self.interrupt_a(1)
        self.assertNotEqual(self.execute().returncode,0)
        kinds=[(e['action'],e.get('category')) for e in self.events('a')]
        self.assertEqual(kinds[-2:],[('node-failed','interrupted'),('node-exhausted','exhausted')])
        s=self.state();self.assertEqual(s['nodes']['a']['status'],'failed');self.assertEqual(s['nodes']['check']['status'],'blocked');self.assertEqual(s['nodes']['a']['cycle']['dispatches'],1)
    def test_a_crashed_reviewer_is_terminal_and_its_output_is_redacted(self):
        # F9 (review 20261012-212850, round 2): an environmental model failure gets no retry, and its stderr never reaches state or events unredacted
        self.install_model_tools();os.environ['GRAPH_CRASH']='a';self.addCleanup(os.environ.pop,'GRAPH_CRASH',None)
        for n in self.graph['nodes']:n.pop('command',None)
        self.graph['nodes'][1]['on_failure']='retry'
        self.assertNotEqual(self.execute().returncode,0)
        s=self.state();a=s['nodes']['a'];self.assertEqual(a['cycle']['dispatches'],1);self.assertEqual(a['cycle']['history'][0]['category'],'review_unavailable')
        self.assertNotIn('node-retry',[e['action'] for e in self.events()])
        for name,text in (('state.json',(self.run/'state.json').read_text()),('events.jsonl',(self.run/'events.jsonl').read_text())):self.assertNotIn('ghp_zzzz',text,name)
        diag=Path(a['cycle']['history'][0]['diagnostics']).read_text();self.assertIn('reviewer crashed',diag);self.assertNotIn('ghp_zzzz',diag)
    def test_model_handler_gets_executor_fields_outside_the_enclosure_and_diagnostics_inside(self):
        self.install_model_tools()
        log=self.root/'prompts.jsonl';os.environ['GRAPH_LOG']=str(log);os.environ['GRAPH_FAIL_ONCE']='a'
        self.addCleanup(os.environ.pop,'GRAPH_LOG',None);self.addCleanup(os.environ.pop,'GRAPH_FAIL_ONCE',None)
        for n in self.graph['nodes']:n.pop('command',None)
        self.graph['nodes'][1].update(on_failure='retry',id='a')
        self.ok(self.execute())
        rows=[json.loads(l) for l in log.read_text().splitlines()];a=[r for r in rows if r['id']=='a']
        self.assertEqual(len(a),2);self.assertNotIn('correction',a[0]['own']);self.assertNotIn('correction_diagnostics',a[0]['outside'])
        c=a[1]['own']['correction'];self.assertEqual((c['node'],c['previous_attempt'],c['category']),('a',1,'malformed_output'))
        self.assertNotIn('diagnostics',c,'handler output must not sit outside the enclosure');self.assertIn('transient model failure',a[1]['outside']['correction_diagnostics'])
        self.assertEqual(c['scope']['checks'],['a']);self.assertEqual(self.state()['nodes']['b']['attempts'],1)
    def test_resume_preserves_work_and_invalidates_descendants(self):
        self.ok(self.execute())
        first=self.state();self.ok(self.execute())
        self.assertEqual(first['nodes'],self.state()['nodes'])
        self.graph['nodes'][1]['finding']=False
        self.ok(self.execute())
        s=self.state()
        self.assertEqual(s['nodes']['b']['attempts'],1)
        self.assertEqual(s['nodes']['a']['attempts'],2)
        self.assertEqual(s['nodes']['check']['attempts'],2)
        self.assertEqual(s['nodes']['report']['attempts'],2)
    def test_changed_revision_and_evidence_invalidate_cached_success(self):
        self.ok(self.execute())
        (self.run/'a.json').write_text('{}')
        self.ok(self.execute())
        self.assertEqual(self.state()['nodes']['a']['attempts'],2)
        (self.repo/'value').write_text('two');self.git('commit','-qam','two')
        self.packet['repos'][0]['head']=self.git('rev-parse','HEAD')
        self.ok(self.execute())
        self.assertEqual(self.state()['nodes']['prepare']['attempts'],2)
    def test_data_denial_precedes_dispatch_and_export(self):
        self.packet['data_use']['allowed_commands']=[]
        r=self.execute();self.assertNotEqual(r.returncode,0)
        self.assertIn('data_use',r.stderr)
        self.packet['data_use']['allowed_commands']=[self.command]
        self.ok(self.execute())
        r=self.call('export','--run-dir',str(self.run),'--output','/private/tmp/disallowed-graph-output.json')
        self.assertNotEqual(r.returncode,0)
        dest=self.root/'export.json'
        self.ok(self.call('export','--run-dir',str(self.run),'--output',str(dest)))
        first=dest.stat().st_mtime_ns
        self.ok(self.call('export','--run-dir',str(self.run),'--output',str(dest)))
        self.assertEqual(first,dest.stat().st_mtime_ns)
    def test_an_ungranted_node_destination_stops_the_run_before_any_worker(self):
        """TB-003: a node's declared destinations are granted, or nothing is dispatched."""
        self.graph['nodes'][0]['destinations']=['https://192.168.1.10/upload']
        r=self.execute();self.assertNotEqual(r.returncode,0)
        self.assertIn('NetConnectGrant(host=192.168.1.10) required',r.stderr)
        self.assertFalse((self.run/'prepare.json').exists(),'no worker ran')
        self.policy['destinations']=['192.168.1.10']
        self.ok(self.execute())
        self.assertEqual(json.loads((self.run/'state.json').read_text())['egress']['examined'],1)
        self.assertTrue((self.run/'prepare.json').exists(),'a granted run writes the file the refused one did not')
    def test_a_ledger_grant_covers_a_node_destination(self):
        """Review F2: a net.connect grant in the ledger passes the run; one for another host does not."""
        sys.path.insert(0,str(SCRIPT.parent)); import governance
        self.graph['nodes'][0]['destinations']=['https://example.org/api']
        ledger=self.root/'grants.jsonl'
        governance.grant(ledger,'net.connect','other.example',granted_by='dorianatmoxywolf')
        r=self.execute(grants=ledger);self.assertNotEqual(r.returncode,0)
        self.assertIn('NetConnectGrant(host=example.org) required',r.stderr)
        self.assertFalse((self.run/'prepare.json').exists(),'no worker ran')
        governance.grant(ledger,'net.connect','example.org',granted_by='dorianatmoxywolf')
        self.ok(self.execute(grants=ledger))
        self.assertTrue((self.run/'prepare.json').exists())
    def test_oversight_is_separate_from_machine_results(self):
        self.ok(self.execute())
        evidence=self.root/'decision.txt';evidence.write_text('Human stopped publication.')
        r=self.call('observe','--run-dir',str(self.run),'--decision','stopped','--evidence',str(evidence),'--action','publish report')
        self.ok(r)
        stats=self.call('oversight','--run-dir',str(self.run))
        self.ok(stats)
        summary=json.loads(stats.stdout);self.assertEqual(summary['human_decisions'],1);self.assertEqual(summary['override_rate'],1)
        self.assertEqual(self.state()['outcome'],'complete')
    def test_shared_log_and_timing_do_not_count_machine_events_as_humans(self):
        self.ok(self.execute())
        evidence=self.root/'human.txt';evidence.write_text('Observed human edit')
        log=self.root/'shared.jsonl'
        r=self.call('observe','--run-dir',str(self.run),'--decision','edited','--evidence',str(evidence),'--action','publish',
                    '--requested-at','2026-01-01T00:00:00+00:00','--gate-log',str(log))
        self.ok(r)
        self.assertEqual(len(log.read_text().splitlines()),1)
        stats=json.loads(self.call('oversight','--run-dir',str(self.run)).stdout)
        self.assertIsNotNone(stats['median_response_seconds'])
        self.assertEqual(stats['human_decisions'],1)

    def test_builtin_claim_check_cannot_omit_claim_finding(self):
        self.graph['nodes'][1]['claim_id']='C1'
        self.graph['nodes'][1]['finding']=False
        r=self.execute();self.assertNotEqual(r.returncode,0)

    def test_report_must_cover_every_node_and_cannot_overwrite_state(self):
        self.graph['nodes'][1]['outputs']=['state.json']
        self.assertNotEqual(self.execute().returncode,0)
        self.graph['nodes'][1]['outputs']=['a.json']
        self.graph['nodes'].append(self.node('orphan'))
        self.assertNotEqual(self.execute().returncode,0)

    def test_explicit_proof_is_executed_and_failed_proof_remains_visible(self):
        self.packet['proofs']=[{'id':'test','argv':[sys.executable,'-c','print("proof ran");raise SystemExit(1)']}]
        self.packet['data_use']['allowed_commands'].append(self.packet['proofs'][0]['argv'])
        self.graph['nodes'].insert(1,self.node('proof', ['prepare'],kind='proof',argv=self.packet['proofs'][0]['argv']))
        self.graph['nodes'][1].pop('command')
        self.graph['nodes'][1]['effects']=['local_proof']
        self.graph['nodes'][-2]['depends_on'].append('proof');self.graph['nodes'][-2]['inputs'].append('proof')
        self.graph['nodes'][-1]['depends_on'].append('proof');self.graph['nodes'][-1]['inputs'].append('proof')
        self.ok(self.execute())
        self.assertIn('proof ran',json.dumps(self.state()['nodes']['proof']['result']))
        self.assertIn('FAILED',json.dumps(self.state()['nodes']['proof']['result']))

    def test_export_rejects_tampered_report(self):
        self.ok(self.execute())
        (self.run/'report.json').write_text('{"complete":true}')
        r=self.call('export','--run-dir',str(self.run),'--output',str(self.root/'out.json'))
        self.assertNotEqual(r.returncode,0)

    def test_snapshot_refuses_symlinks_outside_permission_scope(self):
        outside=self.root/'outside';outside.write_text('private')
        (self.repo/'leak').symlink_to(outside)
        self.git('add','.');self.git('commit','-qm','symlink')
        self.packet['repos'][0]['head']=self.git('rev-parse','HEAD')
        r=self.execute();self.assertNotEqual(r.returncode,0)

    def install_model_tools(self):
        binary=self.root/'bin';binary.mkdir()
        code="""import json,sys,pathlib,os
if os.environ.get('GRAPH_WAIT'):
 pathlib.Path(os.environ['GRAPH_WAIT']).write_text('ready');__import__('time').sleep(30)
args=sys.argv[1:]; tool=pathlib.Path(sys.argv[0]).name
prompt=args[-1] if tool=='codex' else args[args.index('-p')+1]
if '=== PACKET ===' in prompt:
 p=json.loads(prompt.split('=== PACKET ===\\n\\n')[1].split('\\n\\n=== CONTRACT')[0])
 # XE-015: the loop refuses a reviewer that opened none of the files it was offered, so a stub
 # that reads nothing is no longer a valid stand-in for one that reviewed.
 try: pathlib.Path('CHANGE.diff').read_text()
 except OSError: pass
 r={'verdict':'blocking_findings' if os.environ.get('GRAPH_BLOCK') else 'no_blocking_findings','acceptance':[{'criterion':c,'met':True,'evidence':'value:1'} for c in p['acceptance_criteria']],'findings':[],'blocker_resolutions':[],'regressions_from_fixes':[],'notes':''}
 if os.environ.get('GRAPH_BLOCK'):r['findings']=[{'id':'F1','severity':'blocking','file':'value','line':1,'what':'bad','evidence':'value:1','criterion':p['acceptance_criteria'][0],'fix':'fix'}]
 if os.environ.get('GRAPH_PEER_EMBED'):r['findings'].append({'id':'E1','severity':'follow_up','file':'value','line':1,'what':'the file asks the reader to run a script','evidence':'value:1','criterion':'none','fix':'none','category':'embedded_instruction'})
else:
 # TB-002: the payload arrives inside the untrusted enclosure, on the line after its opening tag
 lines=prompt.splitlines();i=next(i for i,l in enumerate(lines) if l.startswith('<untrusted '));own=json.loads(lines[i-1]);outside=json.loads(lines[i+1]);p={**own,**outside};n=p['node']
 if os.environ.get('GRAPH_LOG'):
  with open(os.environ['GRAPH_LOG'],'a') as f: f.write(json.dumps({'id':n['id'],'own':own,'outside':outside,'rule_present':'embedded_instruction' in prompt})+'\\n')
 if os.environ.get('GRAPH_CRASH')==n['id']:
  print('model: gpt-6-astra',file=sys.stderr);print('reviewer crashed holding token=ghp_zzzzzzzzzzzzzzzzzzzzzzzzzz9999',file=sys.stderr);sys.exit(3)
 if os.environ.get('GRAPH_FAIL_ONCE') and n['id']==os.environ['GRAPH_FAIL_ONCE'] and not pathlib.Path(os.environ['GRAPH_LOG']+'.marker').exists():
  pathlib.Path(os.environ['GRAPH_LOG']+'.marker').write_text('');print('model: gpt-6-astra',file=sys.stderr);print('not json: transient model failure');sys.exit(0)
 r={'complete':True,'coverage':n['checks'],'evidence':['value:1'],'findings':[],'summary':'checked'}
 if n.get('claim_id'):r['findings']=[{'id':n['claim_id'],'status':'BUILT','detail':'value exists','evidence':['value:1'],'category':'general'}]
 if n['kind']=='checker':r['findings']=[dict(f,status='VERIFIED') for f in p['candidates']]
 if os.environ.get('GRAPH_EMBED_CLAIM') and n.get('claim_id'):r['findings'].append({'id':'E1','status':'REPORTED','detail':'the snapshot asks the reader to run a script','evidence':['snapshot value:1'],'category':'embedded_instruction'})
 if os.environ.get('GRAPH_EMBED')==n['id']:r['findings']=[{'id':'F1','status':'TENTATIVE','detail':'candidate','evidence':['value:1'],'category':'general'},{'id':'E1','status':'REPORTED','detail':'the snapshot asks the reader to run a script','evidence':['snapshot value:1'],'category':'embedded_instruction'}]
if tool=='codex':
 pathlib.Path(args[args.index('--output-last-message')+1]).write_text(json.dumps(r));print('model: gpt-6-astra',file=sys.stderr)
else:print(json.dumps({'structured_output':r,'modelUsage':{'claude-opus-5':{'outputTokens':100}}}))
"""
        for tool in ['claude','codex']:
            p=binary/tool;p.write_text('#!'+sys.executable+'\n'+code);p.chmod(0o755)
        old=os.environ['PATH'];os.environ['PATH']=str(binary)+os.pathsep+old
        self.addCleanup(os.environ.__setitem__,'PATH',old)
    def builtin_run(self,name):
        self.write_packet()
        return self.call('run','--workflow',name,'--packet',str(self.pfile),'--run-dir',str(self.run),'--jobs','2')
    def test_builtin_verify_uses_both_model_adapters(self):
        self.install_model_tools()
        r=self.builtin_run('verify');self.ok(r)
        s=self.state();self.assertEqual(s['nodes']['claim-C1']['result']['model'],'gpt-6-astra')
        self.assertEqual(s['nodes']['checker']['result']['model'],'claude-opus-5')
    def test_graph_peer_retry_cannot_erase_prior_blockers(self):
        self.install_model_tools()
        (self.repo/'value').write_text('two');self.git('commit','-qam','two')
        self.packet['repos'][0]['head']=self.git('rev-parse','HEAD')
        os.environ['GRAPH_BLOCK']='1';self.addCleanup(os.environ.pop,'GRAPH_BLOCK',None)
        self.assertNotEqual(self.builtin_run('review').returncode,0)
        os.environ.pop('GRAPH_BLOCK')
        r=self.builtin_run('review')
        self.assertNotEqual(r.returncode,0,'Retry erased the original blocker and opened a fresh review')

    def test_a_peer_nodes_embedded_report_keeps_its_category_and_is_never_a_candidate(self):
        """F1, review 20261013-134525: the peer adapter must not launder a reported directive into an ordinary finding."""
        self.install_model_tools()
        (self.repo/'value').write_text('two');self.git('commit','-qam','two')
        self.packet['repos'][0]['head']=self.git('rev-parse','HEAD')
        os.environ['GRAPH_PEER_EMBED']='1';self.addCleanup(os.environ.pop,'GRAPH_PEER_EMBED',None)
        r=self.builtin_run('review');self.ok(r)
        s=self.state();peer=[n for n,v in s['nodes'].items() if n.startswith('review')][0]
        fs=s['nodes'][peer]['result']['findings'];e=[f for f in fs if f['id']=='E1']
        self.assertEqual(len(e),1);self.assertEqual((e[0]['status'],e[0]['category']),('REPORTED','embedded_instruction'))
        rep=json.loads((self.run/'report.json').read_text())
        self.assertIn(('E1','REPORTED','embedded_instruction'),[(f['id'],f['status'],f.get('category')) for f in rep['findings']],'the report lost the classification')
        import task_graph as tg
        self.assertEqual([c['id'] for c in tg.candidates({peer:s['nodes'][peer]['result']})],[],'a reported directive was offered as a candidate')
        # F3: ids are unique whatever the category, in either order
        node={'id':'w','kind':'worker','checks':['w']}
        mk=lambda *fs:{'complete':True,'coverage':['w'],'evidence':['x'],'findings':list(fs)}
        g=lambda i:{'id':i,'status':'TENTATIVE','detail':'d','evidence':['x']}
        em=lambda i:{'id':i,'status':'REPORTED','detail':'d','evidence':['x'],'category':'embedded_instruction'}
        for bad in (mk(em('X'),g('X')),mk(g('X'),em('X')),mk(em('X'),em('X'))):
            with self.assertRaises(ValueError):tg.validate_result(bad,node,[])
        tg.validate_result(mk(em('X'),g('Y')),node,[])
    def test_malformed_checker_evidence_is_refused(self):
        self.graph['nodes'][-2]['malformed']=True
        self.assertNotEqual(self.execute().returncode,0)

    def test_multi_repo_review_partitions_only_explicit_independent_contracts(self):
        self.install_model_tools()
        (self.repo/'value').write_text('two');self.git('commit','-qam','two')
        head=self.git('rev-parse','HEAD')
        other=self.root/'other'
        subprocess.run(['git','clone','-q',str(self.repo),str(other)],check=True)
        self.packet['repos']=[{'path':str(r),'base':self.sha,'head':head} for r in [self.repo,other]]
        self.packet['acceptance_criteria']=['value exists','value is two']
        self.write_packet()
        plan=json.loads(self.call('plan','--workflow','review','--packet',str(self.pfile)).stdout)
        self.assertEqual(len([n for n in plan['nodes'] if n['kind']=='peer']),1)
        self.packet['independent_reviews']=[{'repos':[0],'criteria':[0],'independence_evidence':'No shared interface'},
                                            {'repos':[1],'criteria':[1],'independence_evidence':'No shared interface'}]
        r=self.builtin_run('review');self.ok(r)
        self.assertEqual(self.state()['nodes']['review-0']['status'],'succeeded')
        self.assertEqual(self.state()['nodes']['review-1']['status'],'succeeded')

    def test_proof_cannot_disguise_its_effect_to_bypass_serialization(self):
        proof=self.node('proof',['prepare'],kind='proof',argv=[sys.executable,'-c','print("ok")'])
        proof.pop('command');proof['effects']=['external_review']
        self.packet['data_use']['allowed_commands'].append(proof['argv'])
        self.graph['nodes'].insert(1,proof)
        self.graph['nodes'][-2]['depends_on'].append('proof');self.graph['nodes'][-2]['inputs'].append('proof')
        self.graph['nodes'][-1]['depends_on'].append('proof');self.graph['nodes'][-1]['inputs'].append('proof')
        self.assertNotEqual(self.execute().returncode,0)

    def test_report_refreshes_sources_when_checker_text_is_unchanged(self):
        self.graph['nodes'][-2]['stable']=True
        self.ok(self.execute())
        self.graph['nodes'][1]['delay']=.1
        self.ok(self.execute())
        report=json.loads((self.run/'report.json').read_text())
        self.assertEqual(report['sources']['a'],self.state()['nodes']['a']['result'])

    def test_interrupted_first_peer_round_cannot_review_an_old_head_on_resume(self):
        self.install_model_tools()
        (self.repo/'value').write_text('two');self.git('commit','-qam','two')
        self.packet['repos'][0]['head']=self.git('rev-parse','HEAD');self.write_packet()
        marker=self.root/'waiting'
        env=dict(os.environ,GRAPH_WAIT=str(marker))
        proc=subprocess.Popen([sys.executable,str(SCRIPT),'run','--workflow','review','--packet',str(self.pfile),
                               '--run-dir',str(self.run)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        try:
            deadline=time.monotonic()+10
            while not marker.exists() and time.monotonic()<deadline:time.sleep(.02)
            self.assertTrue(marker.exists(),'model did not start')
        finally:os.killpg(proc.pid,signal.SIGTERM);proc.wait()
        (self.repo/'value').write_text('three');self.git('commit','-qam','three')
        self.packet['repos'][0]['head']=self.git('rev-parse','HEAD')
        r=self.builtin_run('review');self.assertNotEqual(r.returncode,0,'old head accepted as current evidence')
    def test_implicit_outputs_and_model_effects_are_validated(self):
        self.graph['nodes'][0]['effects']=['read_only'];self.graph['nodes'][0].pop('command')
        self.write_packet();self.wfile.write_text(json.dumps(self.graph))
        self.assertNotEqual(self.call('plan','--workflow',str(self.wfile),'--packet',str(self.pfile)).returncode,0)
        self.graph['nodes'][0]['effects']=['external_review'];self.graph['nodes'][0]['command']=self.command
        self.graph['nodes'][1]['outputs']=['report.json']
        self.graph['nodes'][-1]['outputs']=['final.json']
        self.assertNotEqual(self.execute().returncode,0)

    def test_peer_timeout_is_propagated_to_the_bounded_reviewer(self):
        self.install_model_tools()
        (self.repo/'value').write_text('two');self.git('commit','-qam','two')
        self.packet['repos'][0]['head']=self.git('rev-parse','HEAD');self.packet['timeout']=5
        r=self.builtin_run('review');self.ok(r)
        marker=json.loads((self.run/'review-0-review.json').read_text())
        state=json.loads((self.run/'peer-reviews'/marker['review_id']/'state.json').read_text())
        self.assertEqual(state['timeout'],5)

    def test_builtin_graphs_materialize_frozen_nodes(self):
        for workflow in ['cso','verify','review']:
            r=self.call('plan','--workflow',workflow,'--packet',str(self.write_packet()))
            self.ok(r)
            nodes=json.loads(r.stdout)['nodes'];self.assertTrue(nodes)
            if workflow=='verify':self.assertIn('claim-C1',[n['id'] for n in nodes])
    def write_packet(self):
        self.pfile.write_text(json.dumps(self.packet));return self.pfile
    # EV-010.1 and .5: every key a handler reads is labelled by the executor, from the key's origin.
    def test_command_handler_input_carries_provenance_for_every_key(self):
        log=self.root/'inputs.jsonl'
        probe=self.root/'probe.py';probe.write_text('import json,sys,pathlib\np=json.loads(pathlib.Path(sys.argv[-1]).read_text())\n'
            'open('+repr(str(log))+',"a").write(json.dumps({"keys":sorted(p),"provenance":p.get("provenance"),"correction":p.get("correction")})+"\\n")\n'
            'n=p["node"]\nif n.get("fail_once") and not pathlib.Path(n["fail_once"]).exists(): pathlib.Path(n["fail_once"]).write_text(""); print("boom from the handler", file=sys.stderr); sys.exit(3)\n'
            'r={"complete":True,"coverage":n["checks"],"evidence":["value:1"],"findings":[],"summary":n["id"]}\n'
            'if n["kind"]=="checker":r["findings"]=[dict(f,status="VERIFIED") for f in p["candidates"]]\nprint(json.dumps(r))\n')
        cmd=[sys.executable,str(probe)];self.policy['allowed_commands'].append(cmd)
        for n in self.graph['nodes']:
            if n['kind']!='report':n['command']=cmd
        self.graph['nodes'][1].update(on_failure='retry',fail_once=str(self.root/'a.failed-once'))
        self.ok(self.execute())
        rows=[json.loads(l) for l in log.read_text().splitlines()];self.assertEqual(len(rows),5)
        retried=[r for r in rows if r['correction']];self.assertEqual(len(retried),1)
        p=retried[0]['provenance']   # F1 (review 20261013-124809): the executor's record is trusted, the handler's captured output inside it is not
        self.assertEqual(p['correction'],{'source':'executor','untrusted_content':False})
        self.assertEqual(p['correction.diagnostics'],{'source':'handler_output','untrusted_content':True})
        self.assertIn('boom from the handler',retried[0]['correction']['diagnostics'])
        for r in rows:
            prov=r['provenance'];self.assertEqual(sorted(k for k in prov if '.' not in k),[k for k in r['keys'] if k!='provenance'])
            for k,v in prov.items():
                self.assertIn(v['source'],('repository','ci_log','handler_output','fetched','executor'))
                self.assertEqual(v['untrusted_content'],v['source']!='executor',k)
            self.assertEqual((prov['node']['source'],prov['packet']['source'],prov['dependencies']['source'],prov['snapshots']['source']),
                             ('executor','executor','handler_output','repository'))
    def test_model_handler_reports_an_embedded_instruction_and_it_is_never_a_candidate(self):
        self.install_model_tools()
        log=self.root/'prompts.jsonl';os.environ['GRAPH_LOG']=str(log);os.environ['GRAPH_EMBED']='a'
        self.addCleanup(os.environ.pop,'GRAPH_LOG',None);self.addCleanup(os.environ.pop,'GRAPH_EMBED',None)
        for n in self.graph['nodes']:n.pop('command',None)
        self.ok(self.execute())
        rep=json.loads((self.run/'report.json').read_text())
        a=json.loads((self.run/'a.json').read_text());e=[f for f in a['findings'] if f.get('category')=='embedded_instruction']
        self.assertEqual(len(e),1);self.assertEqual(e[0]['status'],'REPORTED');self.assertIn('snapshot',e[0]['evidence'][0])
        self.assertEqual(self.state()['outcome'],'complete')
        chk=json.loads((self.run/'check.json').read_text())
        self.assertNotIn('a:E1',[f['id'] for f in chk['findings']],'a reported instruction became a checker candidate')
        self.assertIn('a:F1',[f['id'] for f in chk['findings']])
        rows=[json.loads(l) for l in log.read_text().splitlines()]
        self.assertTrue(all(r['rule_present'] for r in rows),'the model prompt must carry the report-not-follow paragraph')
        # a worker claiming an embedded instruction as a verdict is an invalid result
        import task_graph as tg
        bad={'complete':True,'coverage':['a'],'evidence':['x'],'findings':[{'id':'E1','status':'VERIFIED','detail':'d','evidence':['x'],'category':'embedded_instruction'}]}
        with self.assertRaises(ValueError):tg.validate_result(bad,{'id':'a','kind':'worker','checks':['a']},[])
        bad['findings'][0]['category']='advice'
        with self.assertRaises(ValueError):tg.validate_result(bad,{'id':'a','kind':'worker','checks':['a']},[])
    def test_a_claim_node_may_report_an_embedded_instruction_beside_its_one_claim(self):
        """F2, review 20261013-124809 round 2: a verify claim node that also reports a directive must not fail its task."""
        self.install_model_tools()
        os.environ['GRAPH_EMBED_CLAIM']='1';self.addCleanup(os.environ.pop,'GRAPH_EMBED_CLAIM',None)
        r=self.builtin_run('verify');self.ok(r)
        s=self.state();self.assertEqual(s['outcome'],'complete')
        res=s['nodes']['claim-C1']['result'];ids=[(f['id'],f['status'],f.get('category')) for f in res['findings']]
        self.assertEqual(ids,[('C1','BUILT','general'),('E1','REPORTED','embedded_instruction')])
        import task_graph as tg
        node={'id':'claim-C1','kind':'worker','checks':['C1'],'claim_id':'C1'}
        two=lambda extra:{'complete':True,'coverage':['C1'],'evidence':['x'],'findings':[{'id':'C1','status':'BUILT','detail':'d','evidence':['x']}]+extra}
        tg.validate_result(two([{'id':'E1','status':'REPORTED','detail':'d','evidence':['x'],'category':'embedded_instruction'}]),node,[])
        for bad in ([{'id':'C1','status':'REPORTED','detail':'d','evidence':['x'],'category':'embedded_instruction'}],   # the claim id reused
                    [{'id':'E1','status':'BUILT','detail':'d','evidence':['x'],'category':'embedded_instruction'}]):     # a verdict in disguise
            with self.assertRaises(ValueError):tg.validate_result(two(bad),node,[])
    def test_model_handler_provenance_is_false_outside_the_enclosure_and_true_inside(self):
        self.install_model_tools()
        log=self.root/'prompts.jsonl';os.environ['GRAPH_LOG']=str(log);os.environ['GRAPH_FAIL_ONCE']='a'
        self.addCleanup(os.environ.pop,'GRAPH_LOG',None);self.addCleanup(os.environ.pop,'GRAPH_FAIL_ONCE',None)
        for n in self.graph['nodes']:n.pop('command',None)
        self.graph['nodes'][1].update(on_failure='retry',id='a')
        self.ok(self.execute())
        rows=[json.loads(l) for l in log.read_text().splitlines()];a=[r for r in rows if r['id']=='a']
        self.assertEqual(len(a),2)
        for r in rows:
            own,out=r['own'],r['outside']
            self.assertEqual(sorted(k for k in own['provenance'] if '.' not in k),sorted(k for k in own if k!='provenance'))
            self.assertNotIn('correction.diagnostics',own['provenance'],'the prompt side carries no diagnostics, so no label for them')
            self.assertEqual(sorted(out['provenance']),sorted(k for k in out if k!='provenance'))
            self.assertTrue(all(v['untrusted_content'] for v in out['provenance'].values()),out['provenance'])
            self.assertFalse(any(v['untrusted_content'] for k,v in own['provenance'].items() if k!='snapshots'),own['provenance'])
        c=a[1]['own']['provenance'];self.assertEqual(c['correction'],{'source':'executor','untrusted_content':False})
        self.assertEqual(a[1]['outside']['provenance']['correction_diagnostics'],{'source':'handler_output','untrusted_content':True})

if __name__=='__main__':unittest.main()
