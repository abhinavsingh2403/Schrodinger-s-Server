"""Check whether WSL loopback clients reach a Docker Desktop listener as distinct peers."""
import subprocess
import time

IMAGE = "schrodinger-final-edge:latest"
LISTENER = """import socket
with socket.socket() as server:
    server.bind(('',2222))
    server.listen()
    print('ready', flush=True)
    peers = set()
    for index in range(2):
        conn, peer = server.accept()
        with conn:
            peers.add(peer[0])
            if index == 1:
                print('unique_peers', len(peers), flush=True)
    server.accept()
"""


def output(*args):
    return subprocess.check_output(args, text=True, timeout=30).strip()


def main():
    container = output("docker", "run", "--pull=never", "--rm", "-d", "--read-only",
                       "--cap-drop", "ALL", "--user", "65534:65534", "-p",
                       "127.0.0.1::2222", "--entrypoint", "python", IMAGE, "-u", "-c", LISTENER)
    try:
        port = int(output("docker", "port", container, "2222/tcp").rsplit(":", 1)[1])
        for _ in range(30):
            if output("docker", "logs", container) == "ready":
                break
            time.sleep(.1)
        else:
            raise RuntimeError("Docker listener did not become ready")
        client = ("import socket,sys\nfor src in ('127.0.0.2','127.0.0.3'):\n"
                  " with socket.create_connection(('127.0.0.1',int(sys.argv[1])),3,"
                  "source_address=(src,0)) as conn: conn.recv(1)")
        output("wsl", "-e", "python3", "-c", client, str(port))
        log = output("docker", "logs", container).splitlines()[-1]
        print(log)
        return 0 if log == "unique_peers 2" else 1
    finally:
        output("docker", "stop", "-t", "0", container)


if __name__ == "__main__":
    raise SystemExit(main())
