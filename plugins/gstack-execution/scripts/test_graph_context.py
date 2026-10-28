import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
import graph_context as gc

class ContextTests(unittest.TestCase):
    def setUp(self):
        self.packet = {'owner':'dorian','repos':[{'head':'a'*40}], 'context':{
            'schema_version':1,'objective':'Build approved design',
            'artifacts':[
                {'id':'design','kind':'design','revision':'a'*40,'status':'accepted','source':'DESIGN.md','content':'criteria','reason':'approved specification'},
                {'id':'code','kind':'implementation','revision':'a'*40,'status':'proposed','source':'src.py','content':'code','reason':'implementation'},
                {'id':'other','kind':'requirement','revision':'a'*40,'status':'accepted','source':'OTHER.md','content':'other','reason':'other task'}],
            'links':[{'from':'code','relation':'implements','to':'design'}],
            'questions':[]}}
        self.node={'id':'build','context_inputs':['design'],'requires_accepted':['design']}
    def test_scopes_context_and_binds_handoff(self):
        out=gc.materialize(self.packet,self.node)
        self.assertEqual([x['id'] for x in out['artifacts']],['design'])
        self.assertEqual(out['authority'],'evidence_only')
        self.assertEqual(gc.verify(out),out['digest'])
        out['artifacts'][0]['content']='tampered'
        with self.assertRaisesRegex(ValueError,'digest'):gc.verify(out)
    def test_rejects_stale_missing_and_unaccepted(self):
        for mutate in (
            lambda p:p['context']['artifacts'][0].update(revision='b'*40),
            lambda p:p['context']['artifacts'][0].update(status='proposed'),
            lambda p:p['context']['artifacts'].pop(0)):
            p=copy.deepcopy(self.packet);mutate(p)
            with self.assertRaises(ValueError):gc.materialize(p,self.node)
    def test_blocks_only_applicable_questions(self):
        self.packet['context']['questions']=[{'id':'Q1','artifacts':['other'],'blocking':True,'text':'unknown'}]
        gc.materialize(self.packet,self.node)
        self.packet['context']['questions'][0]['artifacts']=['design']
        with self.assertRaisesRegex(ValueError,'Q1'):gc.materialize(self.packet,self.node)
    def test_receiving_task_rejects_a_valid_but_outdated_handoff(self):
        handoff=gc.materialize(self.packet,self.node)
        self.packet['context']['artifacts'][0]['content']='new criteria'
        with self.assertRaisesRegex(ValueError,'current task'):
            gc.verify(handoff,self.packet,self.node)

    def test_impact_is_transitive_and_cycle_safe(self):
        m=self.packet['context'];m['links'].append({'from':'design','relation':'depends_on','to':'code'})
        self.assertEqual(gc.impact(m,['design']),['code','design'])
        self.assertEqual(gc.impact(m,['other']),['other'])
    def test_rejects_dangling_links_duplicates_and_oversize(self):
        for mutate in (
            lambda m:m['links'][0].update(to='missing'),
            lambda m:m['artifacts'].append(copy.deepcopy(m['artifacts'][0])),
            lambda m:m['artifacts'][0].update(content='x'*262145)):
            p=copy.deepcopy(self.packet);mutate(p['context'])
            with self.assertRaises(ValueError):gc.materialize(p,self.node)
    def test_legacy_packet_has_no_context(self):
        self.assertIsNone(gc.materialize({'repos':[]},{'id':'legacy'}))
    def test_cli_materializes_verifies_and_reports_impact(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);script=Path(gc.__file__)
            for name,data in [('packet',self.packet),('node',self.node),('manifest',self.packet['context'])]:
                (root/(name+'.json')).write_text(json.dumps(data))
            def call(*args):
                return subprocess.run([sys.executable,str(script),*map(str,args)],capture_output=True,text=True)
            result=call('materialize',root/'packet.json',root/'node.json')
            self.assertEqual(result.returncode,0,result.stderr)
            handoff=json.loads(result.stdout);(root/'handoff.json').write_text(result.stdout)
            verified=call('verify',root/'handoff.json')
            self.assertEqual(verified.returncode,0,verified.stderr)
            self.assertEqual(json.loads(verified.stdout)['digest'],handoff['digest'])
            result=call('impact',root/'manifest.json','design')
            self.assertEqual(json.loads(result.stdout)['affected'],['code','design'])
            handoff['objective']='changed';(root/'handoff.json').write_text(json.dumps(handoff))
            refused=call('verify',root/'handoff.json')
            self.assertEqual(refused.returncode,1)
            self.assertEqual(refused.stdout,'')
            self.assertIn('refused:',refused.stderr)

    def test_model_prompt_encloses_context_and_omits_full_manifest(self):
        import task_graph
        context=gc.materialize(self.packet,self.node)
        payload={'node':self.node,'packet':self.packet,'snapshots':[],
                 'dependencies':{},'candidates':[],'context':context}
        prompt=task_graph.node_prompt(payload)
        # Unselected artifact content must never reach the model.
        self.assertNotIn('OTHER.md',prompt)
        self.assertIn('DESIGN.md',prompt)
        self.assertTrue(task_graph.provenance_of({'context':context})['context']['untrusted_content'])

    def test_attested_artifact_refuses_stale_content_after_revision_refresh(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)/'repo';repo.mkdir()
            def git(*a):return subprocess.check_output(['git','-C',str(repo),'-c','user.email=t@x','-c','user.name=t',*a],text=True).strip()
            git('init','-q');git('config','core.hooksPath','/dev/null')
            (repo/'bank.json').write_text('{"v":1}');git('add','.');git('commit','-qm','one');h1=git('rev-parse','HEAD')
            packet={'owner':'o','repos':[{'path':str(repo),'base':h1,'head':h1}],'context':{'schema_version':1,'objective':'attest',
                'artifacts':[{'id':'bank','kind':'requirement','revision':h1,'status':'accepted','source':'bank.json','content':'{"v":1}','reason':'r','attest':'content'},
                             {'id':'bank-hash','kind':'requirement','revision':h1,'status':'accepted','source':'bank.json','content':'sha256:'+__import__('hashlib').sha256(b'{"v":1}').hexdigest(),'reason':'r','attest':'sha256'}]}}
            node={'id':'n','context_inputs':['bank','bank-hash'],'requires_accepted':['bank']}
            good=gc.materialize(packet,node);self.assertEqual(gc.verify(good,packet,node),good['digest'])
            (repo/'bank.json').write_text('{"v":2}');git('commit','-qam','two');h2=git('rev-parse','HEAD')
            packet['repos'][0].update(base=h2,head=h2)
            for a in packet['context']['artifacts']:a['revision']=h2      # revision refreshed, content stale
            with self.assertRaisesRegex(ValueError,'stale content for attested artifact bank'):gc.materialize(packet,node)
            with self.assertRaises(ValueError):gc.verify(good,packet,node)
            packet['context']['artifacts'][0]['content']='{"v":2}'       # one refreshed, the hash one still stale
            with self.assertRaisesRegex(ValueError,'stale content for attested artifact bank-hash'):gc.materialize(packet,node)
            packet['context']['artifacts'][1]['content']='sha256:'+__import__('hashlib').sha256(b'{"v":2}').hexdigest()
            fresh=gc.materialize(packet,node);self.assertNotEqual(fresh['digest'],good['digest'])
            unselected={'id':'n2','context_inputs':['bank-hash'],'requires_accepted':[]}
            packet['context']['artifacts'][0]['content']='{"v":3}'     # tampered, and n2 does not select it
            with self.assertRaisesRegex(ValueError,'stale content for attested artifact bank'):gc.materialize(packet,unselected)
            packet['context']['artifacts'][0]['content']='{"v":2}'
            packet['context']['artifacts'][0]['source']='missing.json'
            with self.assertRaisesRegex(ValueError,'source not found'):gc.materialize(packet,node)
            packet['context']['artifacts'][0].update(source='bank.json',attest='md5')
            with self.assertRaisesRegex(ValueError,'invalid artifact attest'):gc.materialize(packet,node)
    def test_binds_refuses_a_consumer_that_embeds_a_moved_prerequisite(self):
        m=self.packet['context']; m['artifacts'][1]['binds']={'design':'criteria'}
        node={'id':'build','context_inputs':['code','design'],'requires_accepted':[]}
        with self.assertRaisesRegex(ValueError,'without a depends_on link'):gc.materialize(self.packet,node)
        m['links'].append({'from':'code','relation':'depends_on','to':'design'})
        good=gc.materialize(self.packet,node)
        m['artifacts'][0]['content']='criteria v2'        # prerequisite refreshed, consumer still embeds the old one
        with self.assertRaisesRegex(ValueError,'stale dependency binding code -> design'):gc.materialize(self.packet,node)
        with self.assertRaises(ValueError):gc.verify(good,self.packet,node)
        m['artifacts'][1]['binds']={'design':'criteria v2'};self.assertNotEqual(gc.materialize(self.packet,node)['digest'],good['digest'])
        m['artifacts'][1]['binds']={'ghost':'x'}
        with self.assertRaisesRegex(ValueError,'binds unknown artifact'):gc.materialize(self.packet,node)
        m['artifacts'][1]['binds']={}
        with self.assertRaisesRegex(ValueError,'invalid artifact binds'):gc.materialize(self.packet,node)
    def test_pointer_binds_cannot_be_relabelled_in_the_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)/'repo';repo.mkdir()
            def git(*a):return subprocess.check_output(['git','-C',str(repo),'-c','user.email=t@x','-c','user.name=t',*a],text=True).strip()
            git('init','-q');git('config','core.hooksPath','/dev/null')
            h=__import__('hashlib');bank1='{"v":1}';bank2='{"v":2}'
            (repo/'bank.json').write_text(bank1);(repo/'fx.json').write_text(json.dumps({'bank':{'bank_hash':'sha256:'+h.sha256(bank1.encode()).hexdigest()}}))
            git('add','.');git('commit','-qm','one');h1=git('rev-parse','HEAD')
            def manifest(rev):
                return {'schema_version':1,'objective':'bind','artifacts':[
                    {'id':'bank','kind':'requirement','revision':rev,'status':'accepted','source':'bank.json','content':'sha256:'+h.sha256(subprocess.check_output(['git','-C',str(repo),'show',rev+':bank.json'])).hexdigest(),'reason':'r','attest':'sha256'},
                    {'id':'fx','kind':'evidence','revision':rev,'status':'accepted','source':'fx.json','content':subprocess.check_output(['git','-C',str(repo),'show',rev+':fx.json'],text=True),'reason':'r','attest':'content','binds':{'bank':{'pointer':'/bank/bank_hash'}}}],
                    'links':[{'from':'fx','relation':'depends_on','to':'bank'}]}
            node={'id':'n','context_inputs':['fx','bank'],'requires_accepted':['fx','bank']}
            packet={'owner':'o','repos':[{'path':str(repo),'base':h1,'head':h1}],'context':manifest(h1)}
            good=gc.materialize(packet,node)
            (repo/'bank.json').write_text(bank2);git('commit','-qam','two');h2=git('rev-parse','HEAD')
            packet={'owner':'o','repos':[{'path':str(repo),'base':h2,'head':h2}],'context':manifest(h2)}   # bank refreshed, fx.json still embeds the old hash
            with self.assertRaisesRegex(ValueError,'stale dependency binding fx -> bank'):gc.materialize(packet,node)
            with self.assertRaises(ValueError):gc.verify(good,packet,node)
            # a string-form relabel in the manifest would pass; the pointer form has nothing to relabel
            packet['context']['artifacts'][1]['binds']={'bank':{'pointer':'/bank/missing'}}
            with self.assertRaisesRegex(ValueError,'not found'):gc.materialize(packet,node)
            packet['context']['artifacts'][1].update(attest='sha256',binds={'bank':{'pointer':'/bank/bank_hash'}})
            with self.assertRaisesRegex(ValueError,'needs attest: content'):gc.materialize(packet,node)
    def test_attested_artifact_refuses_string_binding_no_silent_fallback(self):
        m=self.packet['context']; m['links'].append({'from':'code','relation':'depends_on','to':'design'})
        m['artifacts'][1].update(attest='content',source='src.py',binds={'design':'criteria'})
        node={'id':'build','context_inputs':['code','design'],'requires_accepted':[]}
        with self.assertRaisesRegex(ValueError,'must bind by pointer'):gc.materialize(self.packet,node)
    def test_attest_refuses_ambiguous_repository_selection(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)/'repo';repo.mkdir()
            def git(*a):return subprocess.check_output(['git','-C',str(repo),'-c','user.email=t@x','-c','user.name=t',*a],text=True).strip()
            git('init','-q');git('config','core.hooksPath','/dev/null');(repo/'f.txt').write_text('x');git('add','.');git('commit','-qm','one');h=git('rev-parse','HEAD')
            twin=Path(td)/'twin';subprocess.check_call(['git','clone','-q',str(repo),str(twin)])   # a second checkout at the same head
            packet={'owner':'o','repos':[{'path':str(repo),'base':h,'head':h},{'path':str(twin),'base':h,'head':h}],'context':{'schema_version':1,'objective':'amb',
                'artifacts':[{'id':'f','kind':'evidence','revision':h,'status':'accepted','source':'f.txt','content':'x','reason':'r','attest':'content'}]}}
            node={'id':'n','context_inputs':['f'],'requires_accepted':['f']}
            with self.assertRaisesRegex(ValueError,'more than one packet repository'):gc.materialize(packet,node)
            packet['repos'].pop();self.assertIsNotNone(gc.materialize(packet,node))   # one repository at that head: unambiguous
    def test_unattested_artifact_stays_a_declaration(self):
        self.packet['context']['artifacts'][0]['content']='anything';self.assertIsNotNone(gc.materialize(self.packet,self.node))

    def test_no_manifest_cannot_satisfy_declared_context(self):
        with self.assertRaises(ValueError):gc.materialize({'repos':[]},self.node)

if __name__=='__main__':unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout,verbosity=2))   # goal gstack-delivery-through-merge-3 item 1: counts on stdout
