"""Check disjoint component accounting used in reporting-only S3 diagnostics."""
from analysis.exp0_robustness import component_name


def test_components_preserve_overlap_and_command_boundary():
    r = dict(cnt_command_input=4, cnt_file_upload=0, cnt_file_download=0, cnt_direct_tcpip_request=0)
    assert component_name(r) == 'negative'
    r['cnt_command_input'] = 5
    assert component_name(r) == 'commands'
    r['cnt_file_upload'] = 1
    r['cnt_direct_tcpip_request'] = 1
    assert component_name(r) == 'commands+transfer+direct-tcpip'
