"""Independent C review probes. Does not edit implementation or use real services."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import sys
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import tempfile
import threading
import time
import httpx

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'experiments/c_capability'))
from executor import Executor
from server import Server

spec = importlib.util.spec_from_file_location('review_provider', ROOT / 'experiments/common/provider.py')
provider_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provider_module)


def grant_data(expiry):
    return {'agent':'agent:alice','account':'alice','expires_at':expiry,
            'recipients':['trusted@example.test'],'document_ids':['public-note'],
            'merchants':['shop.test'],'currency':'CAD','auto_limit_minor':1000,'hard_limit_minor':5000}


def email():
    return {'type':'email.send','account':'alice','to':['trusted@example.test'],'cc':[],'bcc':[],
            'subject':'Review','body':'Hello','attachments':[{'id':'public-note','version':1}]}


def start(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread


def stop(server, thread):
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def unicode_probe():
    with tempfile.TemporaryDirectory(prefix='review-c-unicode-') as directory:
        path = Path(directory)
        provider = provider_module.Provider(0,path/'provider','provider-test')
        pt = start(provider)
        executor = Executor(path/'executor',f'http://127.0.0.1:{provider.server_port}','provider-test')
        server = Server(0,executor,{'agent:alice':'agent-test','agent:bob':'bob-test','human:alice':'human-test'})
        st = start(server)
        try:
            grant = executor.create_grant('human:alice',grant_data(int(time.time())+600))
            body = {**grant,'idempotency_key':'surrogate','action':{**email(),'subject':'\ud800'}}
            with httpx.Client(base_url=f'http://127.0.0.1:{server.server_port}',trust_env=False,
                              headers={'Authorization':'Bearer agent-test'}) as client:
                try:
                    response = client.post('/requests',content=json.dumps(body).encode('ascii'))
                    observed = {'status':response.status_code,'body':response.json()}
                except httpx.HTTPError as error:
                    observed = {'connection_error':type(error).__name__}
                health = client.get('/health').status_code
            with provider.connect() as db:
                counts = {'effects':db.execute('select count(*) from effects').fetchone()[0],
                          'reads':db.execute('select count(*) from reads').fetchone()[0]}
            return {'observed':observed,'subsequent_health':health,**counts}
        finally:
            stop(server,st)
            executor.close()
            stop(provider,pt)


def expiry_during_preparation():
    class DelayedFirstDocument(provider_module.Handler):
        def do_GET(self):
            if self.path.startswith('/documents/'):
                self.server.request_times.append(time.time())
            super().do_GET()

        def reply(self,status,payload):
            if self.path.startswith('/documents/') and len(self.server.request_times)==1:
                # Delay only response to the first authorized read. The root provider
                # has already durably recorded that access when it calls reply().
                time.sleep(max(0, self.server.expiry-time.time()+0.2))
            super().reply(status,payload)

    with tempfile.TemporaryDirectory(prefix='review-c-expiry-') as directory:
        path=Path(directory)
        provider=provider_module.Provider(0,path/'provider','provider-test')
        provider.RequestHandlerClass=DelayedFirstDocument
        provider.request_times=[]
        provider.expiry=int(time.time())+2
        pt=start(provider)
        executor=Executor(path/'executor',f'http://127.0.0.1:{provider.server_port}','provider-test')
        try:
            grant=executor.create_grant('human:alice',grant_data(provider.expiry))
            action=email()
            action['attachments']*=2
            result=executor.submit('agent:alice',{**grant,'idempotency_key':'expiry','action':action})
            with provider.connect() as db:
                reads=[dict(row) for row in db.execute('select * from reads')]
            return {'expiry':provider.expiry,'read_started_at':provider.request_times,
                    'reads_after_expiry':sum(t>=provider.expiry for t in provider.request_times),
                    'result':result,'provider_reads':reads}
        finally:
            executor.close()
            stop(provider,pt)


def expiry_during_reservation():
    class TimestampEffects(provider_module.Handler):
        def do_POST(self):
            if self.path == '/effects':
                self.server.effect_times.append(time.time())
            super().do_POST()

    with tempfile.TemporaryDirectory(prefix='review-c-reservation-') as directory:
        path=Path(directory)
        provider=provider_module.Provider(0,path/'provider','provider-test')
        provider.RequestHandlerClass=TimestampEffects
        provider.effect_times=[]
        pt=start(provider)
        executor=Executor(path/'executor',f'http://127.0.0.1:{provider.server_port}','provider-test')
        blocker=None
        try:
            expiry=int(time.time())+3
            grant=executor.create_grant('human:alice',{**grant_data(expiry),'auto_limit_minor':0})
            order={'type':'order.create','account':'alice','merchant':'shop.test','sku':'paper',
                   'quantity':1,'amount_minor':500,'currency':'CAD',
                   'shipping_address_id':'home','recurring':False}
            pending=executor.submit('agent:alice',{**grant,'idempotency_key':'expiry-claim','action':order})
            assert pending['state']=='pending',pending
            blocker=sqlite3.connect(executor.database,isolation_level=None)
            blocker.execute('BEGIN IMMEDIATE')
            started=time.time()
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(executor.approve,'human:alice',pending['request_id'],
                                   {'action_digest':pending['action_digest']})
                time.sleep(max(0,expiry-time.time()+.2))
                blocked_until=time.time()
                still_waiting=not future.done()
                blocker.execute('COMMIT')
                result=future.result(timeout=5)
            with provider.connect() as db:
                effects=[dict(row) for row in db.execute('select * from effects')]
            return {'expiry':expiry,'approval_started_at':started,
                    'sqlite_lock_released_at':blocked_until,'approval_waited_for_sqlite':still_waiting,
                    'effect_started_at':provider.effect_times,
                    'effects_after_expiry':sum(t>=expiry for t in provider.effect_times),
                    'result':result,'provider_effect_count':len(effects)}
        finally:
            if blocker:
                blocker.close()
            executor.close()
            stop(provider,pt)


if __name__=='__main__':
    results={'unicode':unicode_probe(),'expiry_during_preparation':expiry_during_preparation(),
             'expiry_during_reservation':expiry_during_reservation()}
    destination=ROOT/'experiments/results/review-c/probes.json'
    destination.write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))
