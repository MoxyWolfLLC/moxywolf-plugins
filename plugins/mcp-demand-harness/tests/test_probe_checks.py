import json
import sys
import unittest
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]/'scripts'))
import probe_checks as pc

class Semantics(unittest.TestCase):
    def test_rpc_errors_malformed_and_wrong_id_cannot_be_results(self):
        for text in ('{}','not json',json.dumps({'jsonrpc':'2.0','id':1,'error':{'message':'bad'}}),json.dumps({'jsonrpc':'2.0','id':2,'result':{'content':[]}})):
            self.assertIn('_probe_error',pc.decode_rpc(text,1))
        self.assertEqual(pc.decode_rpc('data: '+json.dumps({'jsonrpc':'2.0','id':1,'result':{'content':[]}})+'\n\n',1),{'content':[]})
    def test_tool_and_http_errors_fail_before_content(self):
        self.assertFalse(pc.transport_checks(200,{'isError':True,'content':[{'text':'expected'}]})[0]['passed'])
        self.assertFalse(pc.transport_checks(500,{'content':[{'text':'expected'}]})[0]['passed'])
        self.assertFalse(pc.transport_checks(200,{'_probe_error':'rpc error'})[0]['passed'])
    def test_structured_success_or_explicit_absence(self):
        contract=[[{'path':'/roles','type':'array','nonempty':True}],
                  [{'path':'/absence/reason','type':'string','nonempty':True}]]
        for data in ({'roles':[{'id':'role-1'}]},{'absence':{'reason':'not held'}}):
            self.assertTrue(pc.structured_check(data,contract)['passed'])
        for data in ({'roles':[]},{'roles':'roles'},{'absence':{}},{'error':'roles'}):
            self.assertFalse(pc.structured_check(data,contract)['passed'])
    def test_bad_contract_is_refused(self):
        for c in ([],[[]],[[{'path':'roles','type':'array'}]],[[{'path':'/roles','type':'anything'}]],[[{'path':'/roles','nonempty':'yes'}]],[[{'path':'/roles','equals':False,'extra':1}]]):
            with self.assertRaises(ValueError):pc.validate_contract(c)
    def test_nested_payload_and_pointer_escaping(self):
        self.assertEqual(pc.payload({'structuredContent':{'ok':True,'data':{'roles':[1]}}}),{'roles':[1]})
        self.assertEqual(pc.payload({'content':[{'type':'text','text':'{"roles":[1]}'}]}),{'roles':[1]})
        self.assertTrue(pc.structured_check({'a/b':{'~key':False}},[[{'path':'/a~1b/~0key','equals':False}]])['passed'])
    def test_receipt_redacts_then_bounds_and_records_original_hash(self):
        original={'token':'secret','note':'Bearer abcdefghi','nested':{'password':'hidden'},'rows':'x'*10000}
        e=pc.receipt(original,['secret'],limit=300)
        rendered=json.dumps(e)
        self.assertNotIn('secret',rendered);self.assertNotIn('hidden',rendered);self.assertNotIn('abcdefghi',rendered)
        self.assertTrue(e['truncated']);self.assertEqual(len(e['sha256']),64)
        self.assertLessEqual(len(e['sanitized_text']),300)
    def test_application_exceptions_in_text_are_not_success(self):
        for text in ('Error: database unavailable','Internal Server Error','Traceback (most recent call last):'):
            self.assertTrue(pc.application_error({'content':[{'type':'text','text':text}]}))
        self.assertFalse(pc.application_error({'content':[{'type':'text','text':'{"absence":{"reason":"not_held"}}'}]}))

    def test_empty_text_and_text_failure_envelopes_fail(self):
        for r in ({'content':[{'type':'text','text':''}]},{'structuredContent':{'ok':True,'data':None}},{'content':[{'type':'text','text':'{"ok":true,"data":null}'}]}):
            self.assertFalse(pc.transport_checks(200,r)[0]['passed'])
        self.assertTrue(pc.application_error({'content':[{'type':'text','text':'{"ok":false,"message":"database unavailable"}'}]}))
    def test_error_denial_cannot_use_a_success_branch(self):
        contract={'json_any_of':[[{'path':'/roles','type':'array','nonempty':True}]]}
        result={'structuredContent':{'ok':False,'denial':{'reason':'error','status':500},'data':{'roles':['stale']}}}
        self.assertTrue(pc.application_error(result,contract))
        absence={'structuredContent':{'ok':False,'denial':{'reason':'not_found','status':404},'data':{'absence':{'reason':'no_prior_version_retained','message':'only one version'}}}}
        contract={'json_any_of':[[{'path':'/absence/reason','equals':'no_prior_version_retained'},{'path':'/absence/message','type':'string','nonempty':True}]]}
        self.assertFalse(pc.application_error(absence,contract))
    def test_json_text_secrets_are_redacted(self):
        value={'content':[{'type':'text','text':'{"password":"private-value","api_key":"private-key"}'}]}
        r=pc.receipt(value)
        self.assertTrue(r['redacted']);self.assertNotIn('private-value',r['sanitized_text']);self.assertNotIn('private-key',r['sanitized_text'])

    def test_sse_secrets_are_redacted_without_flagging_safe_json(self):
        text='event: message\ndata: {"result":{"structuredContent":{"password":"private-value"}}}\n\n'
        r=pc.receipt(text)
        self.assertTrue(r['redacted']);self.assertNotIn('private-value',r['sanitized_text'])
        safe='{"safe":1}'
        r=pc.receipt(safe)
        self.assertFalse(r['redacted']);self.assertEqual(json.loads(r['sanitized_text']),safe)

    def test_rest_json_error_is_not_success(self):
        self.assertFalse(pc.body_ok('{"error":"exception"}'))
        self.assertFalse(pc.body_ok('{}'));self.assertFalse(pc.body_ok('[]'))
        self.assertTrue(pc.body_ok('{"stigs":[{"slug":"rhel_9"}]}'))

if __name__=='__main__':unittest.main()
