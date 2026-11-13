"""Loopback-only Cowrie launcher with real lifecycle hooks; upstream stays untouched.

Run in the pinned WSL environment with --state-dir pointing to Cowrie state.
S1 follows NEWKEYS, S2 follows each logged auth result, S3 follows session.params.
The synchronous local decision timeout is 200 ms; unavailable service stays cheap.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import sys
from urllib.parse import urlparse
from gatekeeper.decision_api import GatekeeperClient
from gatekeeper.feature_extractor import SessionFeatureExtractor


class LifecycleBridge:
    """Keep one decision state per SSH transport, including pre-authentication events."""
    def __init__(self, client, personas=None):
        from sensor.adaptive_server import PersonaManager
        self.client = client
        self.personas = personas or PersonaManager()
        self.sessions = {}

    def event(self, event):
        from sensor.adaptive_server import AdaptiveSessionAdapter
        sid = event.get('session')
        if not sid:
            return
        name = event.get('eventid')
        if name == 'cowrie.session.connect' and sid not in self.sessions:
            self.sessions[sid] = (AdaptiveSessionAdapter(str(event['src_ip']), str(sid),
                self.client, self.personas), SessionFeatureExtractor())
        if sid not in self.sessions:
            return
        adapter, extractor = self.sessions[sid]
        extractor.ingest_event(event)
        if name in ('cowrie.login.success', 'cowrie.login.failed'):
            self.stage(sid, 'S2')
        elif name == 'cowrie.session.params':
            self.stage(sid, 'S3')
        elif name == 'cowrie.command.input':
            adapter.on_command_received(str(event.get('input', '')))
        elif name == 'cowrie.session.closed':
            adapter.on_session_closed()
            del self.sessions[sid]

    def stage(self, sid, stage):
        if sid in self.sessions:
            adapter, extractor = self.sessions[sid]
            adapter._evaluate_stage(stage, extractor.extract_stage_features(stage))


def install(bridge):
    """Wrap verified pinned entry points before Twisted constructs its service."""
    from cowrie.core.events import EventDispatcher
    from cowrie.ssh.transport import HoneyPotSSHTransport
    from sensor import adaptive_server
    original_dispatch = EventDispatcher.dispatch
    original_newkeys = HoneyPotSSHTransport.ssh_NEWKEYS

    def dispatch(self, event):
        # Feature/decision failures must never suppress Cowrie's own event sinks.
        try:
            bridge.event(event)
        except Exception:
            adaptive_server.logger.exception('Adaptive event processing failed')
        return original_dispatch(self, event)

    def newkeys(self, packet):
        result = original_newkeys(self, packet)
        if packet == b'':
            bridge.stage(self.transportId, 'S1')
        return result

    if not adaptive_server.register_cowrie_session_adapter(bridge.client, bridge):
        raise RuntimeError('Adaptive session registration failed; refusing vanilla startup')
    EventDispatcher.dispatch = dispatch
    HoneyPotSSHTransport.ssh_NEWKEYS = newkeys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--gatekeeper-url', default='http://127.0.0.1:5000')
    parser.add_argument('--port', type=int, default=2222)
    args = parser.parse_args()
    if urlparse(args.gatekeeper_url).hostname != '127.0.0.1':
        parser.error('This lab launcher only permits the loopback gatekeeper')
    args.state_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(args.state_dir)
    # Verified EnvironmentConfigParser overrides; no identity keys are changed.
    os.environ.update(COWRIE_SSH_LISTEN_ENDPOINTS=f'tcp:{args.port}:interface=127.0.0.1',
        COWRIE_SSH_FORWARDING='false', COWRIE_TELNET_ENABLED='false',
        COWRIE_HONEYPOT_BACKEND='shell')
    from cowrie.scripts.cowrie import check_initialized, first_time_use, cowrie_init
    if not Path('etc/cowrie.cfg').exists():
        cowrie_init()
    check_initialized()
    first_time_use()
    from twisted.internet import reactor, defer
    # All Twisted-originated outbound traffic is disabled in this lab process.
    # The loopback GatekeeperClient uses urllib with the separately checked URL.
    def blocked(*args, **kwargs):
        raise PermissionError('Outbound connections disabled in adaptive lab launcher')
    reactor.connectTCP = blocked
    reactor.connectSSL = blocked
    reactor.listenUDP = blocked
    reactor.resolve = lambda *a, **kw: defer.fail(PermissionError('DNS disabled in adaptive lab launcher'))
    install(LifecycleBridge(GatekeeperClient(base_url=args.gatekeeper_url, timeout=.2)))
    from twisted.scripts import twistd
    sys.argv = ['twistd', '-n', '--umask=0022', '--pidfile', 'var/run/adaptive.pid',
                '--logger', 'cowrie.python.logfile.stdoutLogger', 'cowrie']
    twistd.run()


if __name__ == '__main__':
    main()
