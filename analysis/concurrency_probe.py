"""LAB_DEMO_NOT_ML concurrency probe: round trip is distinct from engine compute."""
import argparse,concurrent.futures,http.server,json,math,socket,sqlite3,statistics,subprocess,sys,tempfile,threading,time,urllib.request
from pathlib import Path
from datetime import datetime,timezone

def summary(values):
    ordered=sorted(values)
    return {'p50_ms':statistics.median(ordered),'p95_ms':ordered[math.ceil(.95*len(ordered))-1],'max_ms':max(ordered)} if ordered else None

def measure(server_kind):
    root=Path(__file__).resolve().parents[1];results=[]
    for n in (1,5,10,20):
        with tempfile.TemporaryDirectory(prefix='concurrency-') as folder:
            db=Path(folder)/'decisions.db'
            with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
            with (Path(folder)/'server.log').open('w') as log:
                command=[sys.executable,'-m','analysis.concurrency_probe','--serve',server_kind,'--port',str(port),'--db',str(db)]
                process=subprocess.Popen(command,cwd=root,stdout=log,stderr=log)
                try:
                    deadline=time.monotonic()+20
                    while True:
                        try:
                            with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=.2):break
                        except Exception:
                            if process.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Gatekeeper did not start')
                            time.sleep(.05)
                    timings=[];errors=[]
                    for repeat in range(3):
                        barrier=threading.Barrier(n)
                        def request(i):
                            body=json.dumps({'session_id':f'n{n}-r{repeat}-s{i}','source_ip':'127.0.0.1','stage':'S1','provenance':'LAB'}).encode()
                            req=urllib.request.Request(f'http://127.0.0.1:{port}/decide',data=body,headers={'Content-Type':'application/json'})
                            barrier.wait();start=time.perf_counter();error=None
                            try:
                                with urllib.request.urlopen(req,timeout=2) as response:
                                    result=json.load(response)
                                    if result.get('fail_cheap'):error='engine_fail_cheap'
                            except Exception as exc:error=type(exc).__name__
                            return (time.perf_counter()-start)*1000,error
                        with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
                            for latency,error in pool.map(request,range(n)):
                                timings.append(latency)
                                if error:errors.append(error)
                    with sqlite3.connect(db) as c:compute=[r[0] for r in c.execute('SELECT latency_ms FROM decision_log')]
                finally:
                    process.terminate()
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
            logs=(Path(folder)/'server.log').read_text()
            results.append({'N':n,'requests':len(timings),'round_trip':summary(timings),'engine_compute':summary(compute),
                'over_200ms':sum(t>.2*1000 for t in timings),'errors':errors,'broken_pipe_count':logs.count('BrokenPipeError'),
                'client_observation_timeout_seconds':2,'samples_ms':timings})
    return results

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--serve',choices=['serial','threaded','production']);parser.add_argument('--port',type=int);parser.add_argument('--db');parser.add_argument('--compare',action='store_true');parser.add_argument('--production',action='store_true');args=parser.parse_args()
    if args.serve:
        from gatekeeper.decision_api import run_server
        if args.serve=='serial':http.server.ThreadingHTTPServer=http.server.HTTPServer
        run_server(host='127.0.0.1',port=args.port,db_path=args.db);return
    result={'label':'LAB_DEMO_NOT_ML','commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'date':datetime.now(timezone.utc).isoformat(),
            'command':'python -m analysis.concurrency_probe'+(' --production' if args.production else (' --compare' if args.compare else '')),
            'note':'Simulated requests; 2s observation deadline, reported 200ms exceedances. Engine compute excludes HTTP queue and transport.',
            ('production_after' if args.production else 'serial'):measure('production' if args.production else 'serial')}
    if args.compare:result['threaded_experiment']=measure('threaded')
    target=Path(__file__).resolve().parents[1]/'results/cost/concurrency_probe.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,indent=2)+'\n')
    for kind in ('serial','threaded_experiment','production_after'):
        for row in result.get(kind,[]):
            print(kind,row['N'],row['round_trip'],'over200',row['over_200ms'],'errors',len(row['errors']),'BrokenPipe',row['broken_pipe_count'])
if __name__=='__main__':main()
