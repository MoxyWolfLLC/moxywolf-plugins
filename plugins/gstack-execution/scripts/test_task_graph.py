"""Exercise the graph CLI with real subprocess workers and temporary repositories."""
import json
import os
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
if n.get('fail'): sys.exit(3)
r={'complete':True,'coverage':n['checks'],'evidence':['value:1'],'findings':[], 'summary':n['id']}
if n.get('finding'): r['findings']=[{'id':'F1','status':'TENTATIVE','detail':'candidate','evidence':['value:1']}]
if n.get('missing'): r['coverage']=[]
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
        self.graph={'name':'fixture','nodes':[self.node('prepare'),self.node('a',['prepare'],finding=True,delay=.3),self.node('b',['prepare'],finding=True,delay=.3),self.node('check',['a','b'],kind='checker'),self.node('report',['check'],kind='report')]}
    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.repo),*args],text=True).strip()
    def node(self,id,deps=None,kind='worker',**extra):
        deps=deps or []
        return dict(id=id,depends_on=deps,inputs=deps+['packet'],outputs=[id+'.json'],effects=['external_review'],on_failure='block',kind=kind,checks=[id],command=self.command,**extra)
    def call(self,*args):
        return subprocess.run([sys.executable,str(SCRIPT),*args],text=True,capture_output=True)
    def execute(self,cap=2):
        self.pfile.write_text(json.dumps(self.packet));self.wfile.write_text(json.dumps(self.graph))
        return self.call('run','--workflow',str(self.wfile),'--packet',str(self.pfile),'--run-dir',str(self.run),'--jobs',str(cap))
    def state(self): return json.loads((self.run/'state.json').read_text())
    def test_diamond_overlaps_and_preserves_all_findings(self):
        r=self.execute();self.assertEqual(r.returncode,0,r.stderr)
        s=self.state(); a=s['nodes']['a']['result'];b=s['nodes']['b']['result']
        self.assertLess(max(a['interval'][0],b['interval'][0]),min(a['interval'][1],b['interval'][1]))
        report=json.loads((self.run/'report.json').read_text())
        self.assertEqual({f['id'] for f in report['findings']},{'a:F1','b:F1'})
        self.assertEqual(report['sources']['a']['findings'][0]['status'],'TENTATIVE')
    def test_serial_cap_and_shared_proofs(self):
        for n in self.graph['nodes'][1:3]: n['effects']=['local_proof']
        r=self.execute(4);self.assertEqual(r.returncode,0,r.stderr)
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
    def test_resume_preserves_work_and_invalidates_descendants(self):
        self.assertEqual(self.execute().returncode,0)
        first=self.state();self.assertEqual(self.execute().returncode,0)
        self.assertEqual(first['nodes'],self.state()['nodes'])
        self.graph['nodes'][1]['finding']=False
        self.assertEqual(self.execute().returncode,0)
        s=self.state()
        self.assertEqual(s['nodes']['b']['attempts'],1)
        self.assertEqual(s['nodes']['a']['attempts'],2)
        self.assertEqual(s['nodes']['check']['attempts'],2)
        self.assertEqual(s['nodes']['report']['attempts'],2)
    def test_changed_revision_and_evidence_invalidate_cached_success(self):
        self.assertEqual(self.execute().returncode,0)
        (self.run/'a.json').write_text('{}')
        self.assertEqual(self.execute().returncode,0)
        self.assertEqual(self.state()['nodes']['a']['attempts'],2)
        (self.repo/'value').write_text('two');self.git('commit','-qam','two')
        self.packet['repos'][0]['head']=self.git('rev-parse','HEAD')
        self.assertEqual(self.execute().returncode,0)
        self.assertEqual(self.state()['nodes']['prepare']['attempts'],2)
    def test_data_denial_precedes_dispatch_and_export(self):
        self.packet['data_use']['allowed_commands']=[]
        r=self.execute();self.assertNotEqual(r.returncode,0)
        self.assertIn('data_use',r.stderr)
        self.packet['data_use']['allowed_commands']=[self.command]
        self.assertEqual(self.execute().returncode,0)
        r=self.call('export','--run-dir',str(self.run),'--output','/private/tmp/disallowed-graph-output.json')
        self.assertNotEqual(r.returncode,0)
        dest=self.root/'export.json'
        self.assertEqual(self.call('export','--run-dir',str(self.run),'--output',str(dest)).returncode,0)
        first=dest.stat().st_mtime_ns
        self.assertEqual(self.call('export','--run-dir',str(self.run),'--output',str(dest)).returncode,0)
        self.assertEqual(first,dest.stat().st_mtime_ns)
    def test_oversight_is_separate_from_machine_results(self):
        self.assertEqual(self.execute().returncode,0)
        evidence=self.root/'decision.txt';evidence.write_text('Human stopped publication.')
        r=self.call('observe','--run-dir',str(self.run),'--decision','stopped','--evidence',str(evidence),'--action','publish report')
        self.assertEqual(r.returncode,0,r.stderr)
        stats=self.call('oversight','--run-dir',str(self.run))
        self.assertEqual(stats.returncode,0,stats.stderr)
        summary=json.loads(stats.stdout);self.assertEqual(summary['human_decisions'],1);self.assertEqual(summary['override_rate'],1)
        self.assertEqual(self.state()['outcome'],'complete')
    def test_shared_log_and_timing_do_not_count_machine_events_as_humans(self):
        self.assertEqual(self.execute().returncode,0)
        evidence=self.root/'human.txt';evidence.write_text('Observed human edit')
        log=self.root/'shared.jsonl'
        r=self.call('observe','--run-dir',str(self.run),'--decision','edited','--evidence',str(evidence),'--action','publish',
                    '--requested-at','2026-01-01T00:00:00+00:00','--gate-log',str(log))
        self.assertEqual(r.returncode,0,r.stderr)
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
        self.assertEqual(self.execute().returncode,0)
        self.assertIn('proof ran',json.dumps(self.state()['nodes']['proof']['result']))
        self.assertIn('FAILED',json.dumps(self.state()['nodes']['proof']['result']))

    def test_export_rejects_tampered_report(self):
        self.assertEqual(self.execute().returncode,0)
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
args=sys.argv[1:]; tool=pathlib.Path(sys.argv[0]).name
prompt=args[-1] if tool=='codex' else args[args.index('-p')+1]
if '=== PACKET ===' in prompt:
 p=json.loads(prompt.split('=== PACKET ===\\n\\n')[1].split('\\n\\n=== CONTRACT')[0])
 r={'verdict':'blocking_findings' if os.environ.get('GRAPH_BLOCK') else 'no_blocking_findings','acceptance':[{'criterion':c,'met':True,'evidence':'value:1'} for c in p['acceptance_criteria']],'findings':[],'blocker_resolutions':[],'regressions_from_fixes':[],'notes':''}
 if os.environ.get('GRAPH_BLOCK'):r['findings']=[{'id':'F1','severity':'blocking','file':'value','line':1,'what':'bad','evidence':'value:1','criterion':p['acceptance_criteria'][0],'fix':'fix'}]
else:
 p=json.loads(prompt.splitlines()[1]);n=p['node']
 r={'complete':True,'coverage':n['checks'],'evidence':['value:1'],'findings':[],'summary':'checked'}
 if n.get('claim_id'):r['findings']=[{'id':n['claim_id'],'status':'BUILT','detail':'value exists','evidence':['value:1']}]
 if n['kind']=='checker':r['findings']=[dict(f,status='VERIFIED') for f in p['candidates']]
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
        r=self.builtin_run('verify');self.assertEqual(r.returncode,0,r.stderr)
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
        r=self.builtin_run('review');self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(self.state()['nodes']['review-0']['status'],'succeeded')
        self.assertEqual(self.state()['nodes']['review-1']['status'],'succeeded')

    def test_proof_cannot_disguise_its_effect_to_bypass_serialization(self):
        proof=self.node('proof',['prepare'],kind='proof',argv=[sys.executable,'-c','print("ok")'])
        proof.pop('command');proof['effects']=['external_review']
        self.packet['data_use']['allowed_commands'].append(proof['argv'])
        self.graph['nodes'].insert(1,proof)
        self.graph['nodes'][-2]['depends_on'].append('proof');self.graph['nodes'][-2]['inputs'].append('proof')
        self.assertNotEqual(self.execute().returncode,0)

    def test_report_refreshes_sources_when_checker_text_is_unchanged(self):
        self.graph['nodes'][-2]['stable']=True
        self.assertEqual(self.execute().returncode,0)
        self.graph['nodes'][1]['delay']=.1
        self.assertEqual(self.execute().returncode,0)
        report=json.loads((self.run/'report.json').read_text())
        self.assertEqual(report['sources']['a'],self.state()['nodes']['a']['result'])

    def test_builtin_graphs_materialize_frozen_nodes(self):
        for workflow in ['cso','verify','review']:
            r=self.call('plan','--workflow',workflow,'--packet',str(self.write_packet()))
            self.assertEqual(r.returncode,0,r.stderr)
            nodes=json.loads(r.stdout)['nodes'];self.assertTrue(nodes)
            if workflow=='verify':self.assertIn('claim-C1',[n['id'] for n in nodes])
    def write_packet(self):
        self.pfile.write_text(json.dumps(self.packet));return self.pfile

if __name__=='__main__':unittest.main()
