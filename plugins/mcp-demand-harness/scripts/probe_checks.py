"""Deterministic response contracts and bounded, best-effort redacted evidence."""
import hashlib
import json
import re

TYPES={'object':dict,'array':list,'string':str,'boolean':bool,'number':(int,float),'null':type(None)}

def decode_rpc(text, expected_id):
    messages=[line[5:].strip() for line in text.splitlines() if line.startswith('data:')]
    if not messages:messages=[text]
    for raw in messages:
        try:m=json.loads(raw)
        except ValueError:continue
        if isinstance(m,dict) and m.get('jsonrpc')=='2.0' and type(m.get('id')) is int and m['id']==expected_id:
            if 'error' in m:return {'_probe_error':'JSON-RPC error'}
            if isinstance(m.get('result'),dict):return m['result']
    return {'_probe_error':'missing, malformed or mismatched JSON-RPC result'}

def envelope(result):
    structured=result.get('structuredContent')
    if isinstance(structured,dict):return structured
    for block in result.get('content',[]):
        if isinstance(block,dict) and isinstance(block.get('text'),str):
            try:return json.loads(block['text'])
            except ValueError:continue
    return None

def payload(result):
    value=envelope(result)
    return value.get('data',value) if isinstance(value,dict) else value

def transport_checks(status, result):
    content=False
    if isinstance(result,dict):
        structured=result.get('structuredContent')
        if isinstance(structured,dict):
            # F1 (review 20261026-080924-da4beb3): structuredContent is the authoritative payload. Text that
            # accompanies explicitly empty structured data does not make the result nonempty.
            content=structured.get('data',structured) not in (None,{},[],"")
        else:
            # F1 (review 20261026-082123-182cc9e): the first JSON text block is the selected payload (see
            # envelope()); it decides emptiness. Prose makes a result nonempty only when no block is JSON.
            json_seen=False;prose=False
            for block in result.get('content',[]):
                if isinstance(block,dict) and isinstance(block.get('text'),str) and block['text'].strip():
                    try:
                        value=json.loads(block['text'])
                        if not json_seen:
                            json_seen=True
                            if isinstance(value,dict):value=value.get('data',value)
                            content=value not in (None,{},[],"")
                    except ValueError:prose=True
            if not json_seen:content=prose
    ok=200<=status<300 and isinstance(result,dict) and not result.get('isError') and '_probe_error' not in result and content
    return [{'check':'successful HTTP and nonempty MCP result without protocol/tool error','passed':ok,'detail':str(status)}]

def envelopes(result):
    """Every JSON envelope a result carries: structuredContent and each parseable text block.
    F2 (review 20261026-080924-da4beb3): a failure envelope in a later block was invisible before."""
    out=[]
    if isinstance(result.get('structuredContent'),dict):out.append(result['structuredContent'])
    for block in result.get('content',[]):
        if isinstance(block,dict) and isinstance(block.get('text'),str):
            try:v=json.loads(block['text'])
            except ValueError:continue
            if isinstance(v,dict):out.append(v)
    return out

def _excused_absence(env,contract,data=None):
    """A failure envelope is excused only as a not_found/404 denial matched by an explicit typed-absence branch.
    `data` is what the branch is evaluated against: the unwrapped payload for MCP envelopes, the whole body for
    REST (F2, review 20261026-082123-182cc9e round 2: REST contracts are body-relative)."""
    denial=env.get('denial',{})
    if not (isinstance(denial,dict) and denial.get('reason')=='not_found' and denial.get('status')==404):return False
    if data is None:data=env.get('data',env)
    for branch in (contract or {}).get('json_any_of',[]):
        reason=any(c.get('path')=='/absence/reason' and isinstance(c.get('equals'),str) and bool(c['equals']) for c in branch)
        explanation=any(c.get('path')=='/absence/message' and c.get('nonempty') is True for c in branch)
        if reason and explanation and structured_check(data,[branch])['passed']:return True
    return False

def application_error(result,contract=None):
    """True when the server reports a failure inside a 2xx reply.

    Assumption: `error` and `isError` are reserved keys at the top of the payload.
    A truthy value under either name is read as an application failure, so a
    product whose success payload carries a field named `error` (a count, a
    list of validation notes) would be graded as broken. Rename or nest such a
    field on the server side, or extend this check with a profile allowance,
    rather than relaxing the reserved-key rule for everyone.
    """
    for env in envelopes(result):
        if env.get('ok') is False and not _excused_absence(env,contract):return True
        d=env.get('data',env)   # F3 (review 20261026-082123-182cc9e): reserved keys apply to every envelope, not only the selected one
        if isinstance(d,dict) and (d.get('error') or d.get('isError')):return True
    data=payload(result)
    if isinstance(data,dict) and (data.get('error') or data.get('isError')):return True
    for block in result.get('content',[]):
        if isinstance(block,dict) and isinstance(block.get('text'),str) and re.match(r'(?i)^(error\s*:|exception\s*:|internal server error|traceback \()',block['text'].lstrip()):return True
    return False

def validate_contract(branches):
    if not isinstance(branches,list) or not branches:raise ValueError('json_any_of must have branches')
    for branch in branches:
        if not isinstance(branch,list) or not branch:raise ValueError('json_any_of branch must have predicates')
        for c in branch:
            if not isinstance(c,dict) or set(c)-{'path','type','nonempty','equals'}:raise ValueError('invalid JSON predicate')
            path=c.get('path')
            if not isinstance(path,str) or (path and not path.startswith('/')) or re.search(r'~(?![01])',path):raise ValueError('JSON Pointer required')
            if not (set(c)-{'path'}):raise ValueError('predicate needs an assertion')
            if 'type' in c and (not isinstance(c['type'],str) or c['type'] not in TYPES):raise ValueError('invalid predicate type')
            if 'nonempty' in c and c['nonempty'] is not True:raise ValueError('nonempty must be true')

def pointer(data,path):
    for part in path.split('/')[1:] if path else []:
        part=part.replace('~1','/').replace('~0','~')
        if isinstance(data,list):
            if not re.fullmatch(r'0|[1-9][0-9]*',part):raise ValueError('invalid array index')
            data=data[int(part)]
        elif isinstance(data,dict):data=data[part]
        else:raise ValueError('missing path')
    return data

def json_equal(a,b):
    """Equality that keeps JSON types apart, recursively: true is not 1 (F3, review 20261026-080924-da4beb3)."""
    if isinstance(a,bool) or isinstance(b,bool):return isinstance(a,bool) and isinstance(b,bool) and a==b
    if isinstance(a,dict) and isinstance(b,dict):return a.keys()==b.keys() and all(json_equal(a[k],b[k]) for k in a)
    if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(json_equal(x,y) for x,y in zip(a,b))
    return type(a)==type(b) and a==b

def structured_check(data,branches):
    validate_contract(branches)
    def matches(c):
        try:v=pointer(data,c['path'])
        except (KeyError,IndexError,ValueError,TypeError):return False
        if 'type' in c:
            typ=c['type']
            if not isinstance(v,TYPES[typ]) or (typ=='number' and isinstance(v,bool)):return False
        if 'nonempty' in c and (not isinstance(v,(dict,list,str)) or not v):return False
        if 'equals' in c and not json_equal(v,c['equals']):return False
        return True
    return {'check':'structured response contract','passed':any(all(matches(c) for c in b) for b in branches),'detail':''}

def body_ok(text,contract=None):
    """Nonempty JSON body without an application failure. F2 (review 20261026-082123-182cc9e): a 2xx body
    carrying ok:false is accepted only as a not_found/404 denial that an explicit typed-absence branch of
    `contract` matches, the same rule MCP envelopes get; every other failure stays rejected."""
    try:data=json.loads(text)
    except ValueError:return False
    if not isinstance(data,(dict,list)) or not data:return False
    if isinstance(data,dict):
        if data.get('error') or data.get('isError'):return False
        if data.get('ok') is False:return _excused_absence(data,contract,data=data)   # body-relative, no unwrapping
    return True

def receipt(value, secrets=(), limit=16384):
    raw=json.dumps(value,sort_keys=True,ensure_ascii=True)
    def clean(v):
        if isinstance(v,dict):return {k:('[redacted]' if re.search(r'password|secret|token|authorization|api.?key|cookie',k,re.I) else clean(x)) for k,x in v.items()}
        if isinstance(v,list):return [clean(x) for x in v]
        if isinstance(v,str):
            try:embedded=json.loads(v)
            except ValueError:embedded=None
            if isinstance(embedded,(dict,list)):
                cleaned=clean(embedded)
                if cleaned!=embedded:v=json.dumps(cleaned,sort_keys=True,ensure_ascii=True)
            if any(line.startswith('data:') for line in v.splitlines()):
                lines=[]
                for line in v.splitlines(keepends=True):
                    if line.startswith('data:'):
                        ending='\r\n' if line.endswith('\r\n') else ('\n' if line.endswith('\n') else '')
                        body=line[5:len(line)-len(ending)] if ending else line[5:]
                        line='data:'+clean(body)+ending
                    lines.append(line)
                v=''.join(lines)
            for secret in secrets:
                if secret:v=v.replace(secret,'[redacted]')
            return re.sub(r'(?i)Bearer\s+[^\s"<>]+|(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]+|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+','[redacted]',v)
        return v
    text=json.dumps(clean(value),sort_keys=True,ensure_ascii=True)
    return {'sha256':hashlib.sha256(raw.encode()).hexdigest(),'sanitized_text':text[:limit],
            'truncated':len(text)>limit,'redacted':text!=raw,'redaction':'best_effort','original_bytes':len(raw.encode())}
