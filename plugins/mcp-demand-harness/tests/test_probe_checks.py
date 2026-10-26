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

    # Review 20261026-080924-da4beb3 (Codex), blocking findings F1-F3
    def test_f1_text_cannot_make_empty_structured_data_nonempty(self):
        r={'structuredContent':{'ok':True,'data':None},'content':[{'type':'text','text':'No records'}]}
        self.assertFalse(pc.transport_checks(200,r)[0]['passed'])
        r={'structuredContent':{'ok':True,'data':{}},'content':[{'type':'text','text':'{"roles":[1]}'}]}
        self.assertFalse(pc.transport_checks(200,r)[0]['passed'])
        self.assertTrue(pc.transport_checks(200,{'structuredContent':{'ok':True,'data':{'roles':[1]}},'content':[{'type':'text','text':'x'}]})[0]['passed'])
        self.assertTrue(pc.transport_checks(200,{'content':[{'type':'text','text':'plain prose answer'}]})[0]['passed'])
    def test_f2_failure_envelope_in_any_block_is_seen(self):
        r={'content':[{'type':'text','text':'{"roles":[1]}'},{'type':'text','text':'{"ok":false,"denial":{"reason":"rate_limited","status":429}}'}]}
        self.assertTrue(pc.application_error(r))
        r={'structuredContent':{'ok':True,'data':{'roles':[1]}},'content':[{'type':'text','text':'{"ok":false,"denial":{"reason":"error","status":500}}'}]}
        self.assertTrue(pc.application_error(r))
        absence={'content':[{'type':'text','text':'{"roles":[1]}'},{'type':'text','text':'{"ok":false,"denial":{"reason":"not_found","status":404},"data":{"absence":{"reason":"r","message":"m"}}}'}]}
        contract={'json_any_of':[[{'path':'/absence/reason','equals':'r'},{'path':'/absence/message','type':'string','nonempty':True}]]}
        self.assertFalse(pc.application_error(absence,contract))
        self.assertTrue(pc.application_error(absence,{'json_any_of':[[{'path':'/roles','type':'array'}]]}))
    def test_f3_equals_keeps_json_booleans_and_numbers_apart_recursively(self):
        self.assertFalse(pc.structured_check({'role':{'enabled':1}},[[{'path':'/role','equals':{'enabled':True}}]])['passed'])
        self.assertFalse(pc.structured_check({'flags':[1,0]},[[{'path':'/flags','equals':[True,False]}]])['passed'])
        self.assertFalse(pc.structured_check({'n':1.0},[[{'path':'/n','equals':1}]])['passed'])
        self.assertTrue(pc.structured_check({'role':{'enabled':True,'n':[1,{'k':'v'}]}},[[{'path':'/role','equals':{'enabled':True,'n':[1,{'k':'v'}]}}]])['passed'])
        self.assertFalse(pc.structured_check({'role':{'enabled':True}},[[{'path':'/role','equals':{'enabled':True,'extra':1}}]])['passed'])

    # Review 20261026-082123-182cc9e (Codex), blocking findings F1-F3
    def test_r2_f1_prose_cannot_make_empty_json_text_data_nonempty(self):
        r={'content':[{'type':'text','text':'{"ok":true,"data":null}'},{'type':'text','text':'No records'}]}
        self.assertFalse(pc.transport_checks(200,r)[0]['passed'])
        self.assertTrue(pc.transport_checks(200,{'content':[{'type':'text','text':'plain prose answer'}]})[0]['passed'])
        self.assertTrue(pc.transport_checks(200,{'content':[{'type':'text','text':'{"roles":[1]}'},{'type':'text','text':'a note'}]})[0]['passed'])
    def test_r2_f2_rest_body_accepts_only_an_explicit_typed_absence(self):
        body='{"ok":false,"denial":{"reason":"not_found","status":404},"absence":{"reason":"catalog_not_held","message":"none held"}}'
        contract={'json_any_of':[[{'path':'/absence/reason','equals':'catalog_not_held'},{'path':'/absence/message','type':'string','nonempty':True}]]}
        self.assertTrue(pc.body_ok(body,contract))
        self.assertFalse(pc.body_ok(body))
        self.assertFalse(pc.body_ok(body,{'json_any_of':[[{'path':'/stigs','type':'array'}]]}))
        for denial in ('{"reason":"rate_limited","status":429}','{"reason":"unauthorized","status":401}','{"reason":"error","status":500}'):
            self.assertFalse(pc.body_ok('{"ok":false,"denial":'+denial+',"absence":{"reason":"catalog_not_held","message":"m"}}',contract))
    def test_r2_f2b_rest_absence_is_body_relative_even_with_a_data_field(self):
        contract={'json_any_of':[[{'path':'/absence/reason','equals':'catalog_not_held'},{'path':'/absence/message','type':'string','nonempty':True}]]}
        body='{"ok":false,"denial":{"reason":"not_found","status":404},"absence":{"reason":"catalog_not_held","message":"none held"},"data":{}}'
        self.assertTrue(pc.body_ok(body,contract))
        nested='{"ok":false,"denial":{"reason":"not_found","status":404},"data":{"absence":{"reason":"catalog_not_held","message":"m"}}}'
        self.assertFalse(pc.body_ok(nested,contract))   # REST paths are body-relative; nothing is unwrapped
        mcp={'structuredContent':{'ok':False,'denial':{'reason':'not_found','status':404},'data':{'absence':{'reason':'catalog_not_held','message':'m'}}}}
        self.assertFalse(pc.application_error(mcp,contract))   # MCP still evaluates against data
    def test_r2_f3_reserved_error_keys_apply_to_every_envelope(self):
        r={'structuredContent':{'ok':True,'data':{'roles':[1]}},'content':[{'type':'text','text':'{"error":"database unavailable"}'}]}
        self.assertTrue(pc.application_error(r))
        r={'content':[{'type':'text','text':'{"roles":[1]}'},{'type':'text','text':'{"isError":true}'}]}
        self.assertTrue(pc.application_error(r))
        self.assertFalse(pc.application_error({'structuredContent':{'ok':True,'data':{'roles':[1]}},'content':[{'type':'text','text':'{"roles":[1]}'}]}))

    # Review 20261026-084746-6e76541 (Codex), F1
    def test_r3_f1_untyped_404_is_never_an_absence(self):
        self.assertFalse(pc.rest_typed_absence('{"absence":"route missing"}',{'absence_acceptable':True}))
        self.assertFalse(pc.rest_typed_absence('{"absence":{"reason":"r","message":"m"}}',{'absence_acceptable':True}))   # no ok:false/denial: not a typed absence
        typed='{"ok":false,"denial":{"reason":"not_found","status":404},"absence":{"reason":"catalog_not_held","message":"m"}}'
        self.assertFalse(pc.rest_typed_absence(typed,{'absence_acceptable':True}))   # no branch names it
        self.assertTrue(pc.rest_typed_absence(typed,{'json_any_of':[[{'path':'/absence/reason','equals':'catalog_not_held'},{'path':'/absence/message','type':'string','nonempty':True}]]}))
        self.assertFalse(pc.rest_typed_absence('not json',{'json_any_of':[[{'path':'/absence/reason','equals':'x'}]]}))

if __name__=='__main__':unittest.main()
