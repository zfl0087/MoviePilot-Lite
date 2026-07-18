from __future__ import annotations

from types import SimpleNamespace

from app.core.config import settings
from app.doctor import checks, run_doctor
from app.doctor.formatters import format_json_report, format_text_report
from app.doctor.models import DoctorFinding, DoctorFindingStatus, DoctorSeverity
from app.doctor.runner import DoctorRunner


def test_doctor_report_has_stable_json_shape(tmp_path, monkeypatch):
    """doctor JSON 报告应包含稳定状态、环境、汇总和发现列表。"""
    monkeypatch.setattr(settings, "CONFIG_DIR", str(tmp_path))
    (settings.LOG_PATH).mkdir(parents=True, exist_ok=True)
    (settings.ROOT_PATH / "public").mkdir(exist_ok=True)

    report = run_doctor()
    payload = report.to_dict()

    assert payload["schema_version"] == 1
    assert payload["status"] in {"healthy", "degraded", "failed"}
    assert payload["environment"]["config_path"] == str(tmp_path)
    assert isinstance(payload["summary"]["total"], int)
    assert isinstance(payload["findings"], list)
    assert any(item["id"] == "runtime.paths" for item in payload["findings"])


def test_doctor_formatters_include_status_and_finding(tmp_path, monkeypatch):
    """doctor 文本和 JSON 格式化应展示状态与诊断项。"""
    monkeypatch.setattr(settings, "CONFIG_DIR", str(tmp_path))
    report = run_doctor()
    report.add_finding(
        DoctorFinding(
            id="test.demo",
            severity=DoctorSeverity.Warn,
            status=DoctorFindingStatus.Degraded,
            title="测试诊断项",
            detail="测试原因",
            recommendation="测试建议",
        )
    )

    text = format_text_report(report)
    json_text = format_json_report(report)

    assert "MoviePilot Doctor" in text
    assert "测试诊断项" in text
    assert '"schema_version": 1' in json_text
    assert '"test.demo"' in json_text


def test_doctor_fix_removes_stale_runtime(tmp_path, monkeypatch):
    """doctor --fix 应清理指向失效进程的 runtime 文件。"""
    monkeypatch.setattr(settings, "CONFIG_DIR", str(tmp_path))
    settings.TEMP_PATH.mkdir(parents=True, exist_ok=True)
    runtime_file = settings.TEMP_PATH / "moviepilot.runtime.json"
    runtime_file.write_text('{"pid": 999999, "create_time": 1}', encoding="utf-8")

    report = run_doctor(fix=True)

    assert not runtime_file.exists()
    finding = report.find("runtime.backend_stale")
    assert finding is not None
    assert finding.fixed


def test_doctor_accepts_healthy_unmanaged_backend_port(monkeypatch):
    """doctor 在容器中应把健康的非 CLI 管理后端端口识别为正常。"""
    occupant = SimpleNamespace(pid=12345)
    monkeypatch.setattr(checks, "_port_occupants", lambda port: [occupant])
    monkeypatch.setattr(checks, "_process_description", lambda process: f"PID {process.pid} (python)")
    monkeypatch.setattr(checks, "_is_expected_port_process", lambda name, process: False)
    monkeypatch.setattr(
        checks,
        "_backend_health_payload",
        lambda port: {"success": True, "data": {"BACKEND_VERSION": "v2-test"}},
    )

    runner = DoctorRunner()
    checks._check_port(runner, name="backend", port=3001, managed_process=None)

    finding = runner.report.find("port.backend_listening_unmanaged")
    assert finding is not None
    assert finding.status == DoctorFindingStatus.Ok
    assert finding.severity == DoctorSeverity.Info
    assert finding.context["backend_version"] == "v2-test"
    assert runner.report.find("port.backend_occupied") is None


def test_doctor_core_dependencies_do_not_require_browser_runtime(monkeypatch) -> None:
    """正式 Lite Doctor 不得把浏览器模拟包认定为核心依赖。"""
    inspected = []

    def find_spec(name):
        inspected.append(name)
        return object()

    monkeypatch.setattr(checks.importlib.util, "find_spec", find_spec)
    runner = DoctorRunner()

    checks._check_dependencies(runner)

    assert "cloakbrowser" not in checks.CORE_DEPENDENCIES
    assert "playwright" not in checks.CORE_DEPENDENCIES
    assert "cloakbrowser" not in inspected
    assert runner.report.find("dependencies.core").status == DoctorFindingStatus.Ok


def test_doctor_still_reports_missing_real_core_dependency(monkeypatch) -> None:
    """移除浏览器检查后，真实核心包缺失仍必须报告错误。"""
    missing = checks.CORE_DEPENDENCIES[0]
    monkeypatch.setattr(
        checks.importlib.util,
        "find_spec",
        lambda name: None if name == missing else object(),
    )
    runner = DoctorRunner()

    checks._check_dependencies(runner)

    finding = runner.report.find("dependencies.core_missing")
    assert finding is not None
    assert finding.status == DoctorFindingStatus.Failed
    assert missing in finding.detail
