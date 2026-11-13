"""Canonical stage counter vectors shared by offline training and live inference.

All counters correspond to verified Cowrie events. Aggregate replay checks counts,
not whether historical whole-session counters were available at a live prefix.
"""
import math

STAGE_ALLOWED_FEATURES = {
    'S1': ['cnt_session_connect', 'cnt_client_version', 'cnt_client_kex'],
    'S2': ['cnt_session_connect', 'cnt_client_version', 'cnt_client_kex',
           'cnt_client_fingerprint', 'cnt_login_failed', 'cnt_login_success'],
    'S3': ['cnt_session_connect', 'cnt_client_version', 'cnt_client_kex',
           'cnt_client_fingerprint', 'cnt_login_failed', 'cnt_login_success',
           'cnt_client_size', 'cnt_client_var', 'cnt_session_params'],
    'S4': [], 'S5': [],
}
EVENT_COUNTERS = {
    'cowrie.session.connect': 'cnt_session_connect',
    'cowrie.client.version': 'cnt_client_version',
    'cowrie.client.kex': 'cnt_client_kex',
    'cowrie.client.fingerprint': 'cnt_client_fingerprint',
    'cowrie.login.failed': 'cnt_login_failed',
    'cowrie.login.success': 'cnt_login_success',
    'cowrie.client.size': 'cnt_client_size',
    'cowrie.client.var': 'cnt_client_var',
    'cowrie.session.params': 'cnt_session_params',
}


def stage_vector(stage, counters):
    """Return ordered finite numeric counters, zero for absent or invalid input."""
    values = []
    for name in STAGE_ALLOWED_FEATURES[stage]:
        try:
            value = float(counters.get(name, 0) or 0)
        except (TypeError, ValueError):
            value = 0.0
        values.append(value if math.isfinite(value) else 0.0)
    return values


def stage_counters(stage, counters):
    """Expose the same canonical vector by feature name for the decision API."""
    return dict(zip(STAGE_ALLOWED_FEATURES[stage], stage_vector(stage, counters)))
