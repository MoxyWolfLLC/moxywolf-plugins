"""Declared data boundaries and shared gate-log compatibility; not an authentication layer."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def data_permission(packet,tool=None,command=None,output=None):
    policy=packet.get('data_use',{})
    owner=packet.get('owner',packet.get('release_owner'))
    if (policy.get('owner')!=owner or not policy.get('classification') or
            policy.get('allow_repository') is not True or policy.get('allow_history') is not True):
        raise ValueError('data_use: repository/history permission and accountable owner required')
    if tool and tool not in policy.get('allowed_tools',[]):raise ValueError('data_use: tool destination denied: '+tool)
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
