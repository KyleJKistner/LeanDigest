import http.client
import json
import threading
from http.server import ThreadingHTTPServer
import pytest
from proofreader.server import make_handler
from proofreader.source import parse_source

@pytest.fixture
def local_server():
    server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(parse_source('theorem t : True := by trivial')))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield server.server_port
    server.shutdown();server.server_close();thread.join(timeout=3)


def req(port,method,path,body=None,headers=None):
    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
    conn.request(method,path,body=body,headers=headers or {})
    response=conn.getresponse();result=(response.status,dict(response.getheaders()),response.read());conn.close();return result


def test_health(local_server):
    status,headers,body=req(local_server,'GET','/health')
    assert status==200 and json.loads(body)['lean_execution'] is False


def test_page(local_server):
    status,headers,body=req(local_server,'GET','/')
    assert status==200 and b'ProofReader' in body
    assert headers['X-Content-Type-Options']=='nosniff'


def test_read_endpoint_parses_without_compilation(local_server):
    status,_,body=req(local_server,'POST','/api/read',json.dumps({'source':'theorem t : False := by sorry'}),{'Content-Type':'application/json'})
    assert status==200
    d=json.loads(body)
    assert d['declarations'][0]['evidence']=='source'
    assert d['declarations'][0]['warnings']


def test_rebinding_host_is_rejected(local_server):
    assert req(local_server,'GET','/',headers={'Host':'attacker.example'})[0]==403


def test_cross_origin_is_rejected(local_server):
    assert req(local_server,'GET','/',headers={'Origin':'https://attacker.example'})[0]==403


def test_null_origin_is_rejected(local_server):
    assert req(local_server,'GET','/',headers={'Origin':'null'})[0]==403


def test_no_execution_endpoint(local_server):
    assert req(local_server,'POST','/api/execute',headers={'Content-Type':'application/json'})[0]==404


def test_no_arbitrary_file_serving(local_server):
    assert req(local_server,'GET','/../../etc/passwd')[0]==404


def test_non_json_is_rejected(local_server):
    assert req(local_server,'POST','/api/read','source=x',{'Content-Type':'text/plain'})[0]==415


def test_oversized_upload_is_rejected(local_server):
    assert req(local_server,'POST','/api/read','x',{'Content-Type':'application/json','Content-Length':'5000000'})[0]==413
