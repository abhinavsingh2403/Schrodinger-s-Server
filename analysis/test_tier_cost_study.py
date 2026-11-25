"""Check that cost purity uses the last decision of each session."""
from analysis.tier_cost_study import summarize


def test_final_tiers_and_interleaved_intervals():
    rows=[("a","S1","T1","2020-01-01T00:00:00"),("b","S1","T2","2020-01-01T00:00:01"),
          ("a","S3","T2","2020-01-01T00:00:02"),("b","S3","T2","2020-01-01T00:00:05")]
    result=summarize(rows)
    assert result["final_tiers"]=={"T2":2}
    assert result["decision_fraction"]["T1"]==.25
    assert result["observed_time_fraction"]["T1"]==2/6

def test_matched_login_changes_only_pty(monkeypatch):
    from types import SimpleNamespace
    from analysis import tier_cost_study as study

    calls = []
    def execute(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout="srv-app-01\n")

    monkeypatch.setattr(study, "execute_ssh_command", execute)
    for tier in ("T1", "T2"):
        assert study.matched_login(tier, "127.0.0.1", 2222)["ok"]
    assert [kwargs.pop("allocate_pty") for _, kwargs in calls] == [False, True]
    assert calls[0] == calls[1]

def test_renderer_appends_once_and_reports_signed_repeat_difference(tmp_path, monkeypatch):
    import json
    from analysis import render_tier_cost as reporter

    monkeypatch.setattr(reporter, "ROOT", tmp_path)
    report = tmp_path / "COST_PER_TIER.md"
    report.write_text("Historical table\n")
    trace = [dict(rows=[["a", "S2", "T2", "rule_r1_login_success", "DEFAULT", .7]],
                  invocation=1, command="hostname", distinct_visitors=1, pty=False)]
    (tmp_path / "t1_trace.json").write_text(json.dumps(trace))
    for tier, cpu in (("T1", 2), ("T2", 1)):
        stats = dict(wall_time=1, mean_cpu_pct=cpu, max_cpu_pct=cpu, mean_memory_mb=10,
                     max_memory_mb=10, timestamp="2026-01-01")
        summary = summarize([("a", "S2", tier, "2026-01-01T00:00:00")])
        runs = [dict(stats=stats, summary=summary, samples=1)] * 3
        (tmp_path / f"cost_{tier}_only.json").write_text(json.dumps(dict(runs=runs)))
    reporter.render()
    expected = report.read_text()
    reporter.render()
    assert report.read_text() == expected
    assert expected.startswith("Historical table\n\n## T1 purity fix")
    assert "-1.00 to -1.00 percentage points" in expected
