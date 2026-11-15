"""LAB_DEMO_NOT_ML: slow harmless inputs on one SSH connection without PTY."""
import argparse
import json
import re
from harness.attackers.common import execute_ssh_command, validate_source_ip


def run_slow_recon(host='127.0.0.1',port=2222,source_ip=None,delay=2.0):
    validate_source_ip(host)
    commands=['id','uname -a','ls /','ls /opt/deploy']
    lines=[f'{command}; ls /opt/deploy/config.env; echo __DONE_{i}__' for i,command in enumerate(commands)]
    run=execute_ssh_command(host,port,'root','password',source_ip=source_ip,input_lines=lines+['exit'],line_delay=delay,timeout=15)
    observations=[]
    remaining=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', run.stdout).replace('\r','')
    for i,command in enumerate(commands):
        match=re.search(rf'(?m)^__DONE_{i}__\s*$',remaining)
        chunk=remaining[:match.start()] if match else remaining
        marker=bool(match)
        remaining=remaining[match.end():] if match else ''
        observations.append({'command':command,'marker_seen':bool(marker),
            'file_visible':bool(marker) and bool(re.search(r'(?m)^/opt/deploy/config\.env\s*$',chunk)),
            'output':chunk.strip()})
    return {'label':'LAB_DEMO_NOT_ML','returncode':run.returncode,'commands':observations}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',default='127.0.0.1',type=validate_source_ip)
    parser.add_argument('--port',type=int,default=2222)
    parser.add_argument('--source-ip',type=validate_source_ip)
    parser.add_argument('--fast',action='store_true')
    args=parser.parse_args()
    result=run_slow_recon(args.host,args.port,args.source_ip,.2 if args.fast else 2)
    print(json.dumps(result,indent=2))
    raise SystemExit(result['returncode'])
if __name__=='__main__': main()
