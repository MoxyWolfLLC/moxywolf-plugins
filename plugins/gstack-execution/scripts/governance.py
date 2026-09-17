"""Declared data boundaries, capability grants, and shared gate-log compatibility; not an authentication layer."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from fnmatch import fnmatch


# --- XE-002: a grant binds to a scope and re-resolves -------------------------
#
# The packet's data_use policy declares authority per invocation and matches tools by exact
# string. Anything the human plainly authorized but did not name in that exact form is denied,
# so the human is asked again. A ledger fixes the shape, not the trust: this file is writable
# by the agent it governs (see GOVERNANCE.md), so the ledger is a convenience for the human,
# never a security control. The security property lives in ONE_SHOT_ONLY -- classes no grant
# can ever satisfy in advance -- and in protected-branch enforcement outside this process.

GRANT_CLASSES = {
    'vcs.push', 'pr.open', 'pr.bypass_review', 'merge',
    'review.send_code', 'external.model_call',
    'secret.read', 'thirdparty.configure',
    'prod.data_write', 'mail.send',
}
# No grant satisfies these in advance, at any scope, however the human words it.
ONE_SHOT_ONLY = {'merge', 'prod.data_write', 'mail.send', 'pr.bypass_review'}
SCOPES = ('once', 'session', 'project')


def _ledger(path):
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def grant(ledger, klass, resource, granted_by, scope='project', excludes=(), session=None):
    """Append a capability grant. The human's decision becomes a pattern, not a sentence."""
    if klass not in GRANT_CLASSES:
        raise ValueError(f'unknown action class: {klass}; extend GRANT_CLASSES deliberately')
    if scope not in SCOPES:
        raise ValueError(f'unknown scope: {scope}')
    if klass in ONE_SHOT_ONLY and scope != 'once':
        raise ValueError(f'{klass} is one-shot by construction; it cannot be granted at scope {scope!r}')
    if scope == 'session' and not session:
        raise ValueError('a session-scoped grant needs the session id it is bound to')
    if not granted_by:
        raise ValueError('a grant records the human who granted it')
    row = {'granted_at': datetime.now(timezone.utc).isoformat(), 'class': klass,
           'resource': resource, 'scope': scope, 'granted_by': granted_by,
           'excludes': list(excludes), 'session': session}
    row['id'] = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()[:12]
    ledger = Path(ledger); ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(str(ledger) + '.lock', 'a') as mutex:
        fcntl.flock(mutex, fcntl.LOCK_EX)
        with open(ledger, 'a') as f:
            f.write(json.dumps(row) + '\n'); f.flush()
    return row


def resolve(ledger, klass, resource, session=None, consume=None):
    """The grant covering this action, or None. Matching is by pattern; prose is never re-read.

    A `once` grant is covered only while unconsumed: pass the ids already spent in `consume`.
    """
    if klass in ONE_SHOT_ONLY:
        spent = set(consume or ())
        for row in _ledger(ledger):
            if (row['class'] == klass and row['scope'] == 'once' and row['id'] not in spent
                    and _matches(row, resource)):
                return row
        return None
    for row in _ledger(ledger):
        if row['class'] != klass or not _matches(row, resource):
            continue
        if row['scope'] == 'session' and row.get('session') != session:
            continue
        if row['scope'] == 'once' and row['id'] in set(consume or ()):
            continue
        return row
    return None


def _matches(row, resource):
    if any(fnmatch(resource, x) for x in row.get('excludes', [])):
        return False
    return fnmatch(resource, row['resource'])


def data_permission(packet,tool=None,command=None,output=None,ledger=None,session=None):
    policy=packet.get('data_use',{})
    owner=packet.get('owner',packet.get('release_owner'))
    if (policy.get('owner')!=owner or not policy.get('classification') or
            policy.get('allow_repository') is not True or policy.get('allow_history') is not True):
        raise ValueError('data_use: repository/history permission and accountable owner required')
    if tool and tool not in policy.get('allowed_tools',[]):
        # A standing grant covers what the packet did not happen to name. Absent one, refuse:
        # falling back to re-reading a prior approval's wording is the defect XE-002 removes.
        if not (ledger and resolve(ledger, 'review.send_code', tool, session=session)):
            raise ValueError('data_use: tool destination denied: '+tool)
    if command and command not in policy.get('allowed_commands',[]):raise ValueError('data_use: command not authorized')
    if output and not any(Path(output).resolve().is_relative_to(Path(p).resolve()) for p in policy.get('output_roots',[])):
        raise ValueError('data_use: output destination denied')


def gate_record(log,owner,decision,action,revision,evidence,requested_at='',outcome='observed; not release authorization'):
    """Use the shared writer when installed; deduplicate under a local advisory lock."""
    log=Path(log);log.parent.mkdir(parents=True,exist_ok=True)
    identity=json.dumps([owner,decision,action,revision,evidence],sort_keys=True)
    key=hashlib.sha256(identity.encode()).hexdigest()
    note=json.dumps({'event_id':key,'revision':revision,'evidence':evidence})
    with open(str(log)+'.lock','a') as mutex:
        fcntl.flock(mutex,fcntl.LOCK_EX)
        if log.exists():
            for line in log.read_text().splitlines():
                if json.loads(line).get('note')==note:return key
        row={'recorded_at':datetime.now(timezone.utc).isoformat(),'requested_at':requested_at,
             'skill':'gstack-execution:task-graph','tier':'side-effectful-gated','action':action,
             'target':json.dumps(revision,sort_keys=True),'decision':decision,'approver':owner,'outcome':outcome,'note':note}
        writer=log.parent/'record_decision.py'
        if writer.is_file():
            args=[sys.executable,str(writer),'--log',str(log)]
            for field in ('skill','tier','action','target','decision','approver','requested_at','outcome','note'):
                args += ['--'+field.replace('_','-'),row[field]]
            subprocess.run(args,check=True,capture_output=True,text=True,timeout=30)
        else:
            # Same shared schema for installations without the team writer; no signed machine-review rows.
            with open(log,'a') as f:f.write(json.dumps(row)+'\n');f.flush()
    return key
