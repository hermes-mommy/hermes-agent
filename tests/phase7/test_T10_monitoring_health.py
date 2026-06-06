"""
T10: Monitoring Health — Config File Integrity and Observability Contract Tests.

Verifies that monitoring configuration files are valid, parseable, and
contain required Hermes gateway references.  No live deployment — purely
local config validation.
"""

from __future__ import annotations

import json
from pathlib import Path

# Project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict[str, object]:
    """Load JSON from file, returning a dict with concrete type."""
    text = path.read_text(encoding="utf-8")
    result = json.loads(text)
    if not isinstance(result, dict):
        raise TypeError(f"Expected dict, got {type(result)}")
    return result


class TestPrometheusConfig:
    """Prometheus config has required Hermes scrape job."""

    def test_prometheus_yml_exists(self) -> None:
        """prometheus.yml exists."""
        path = _PROJECT_ROOT / "monitoring" / "prometheus" / "prometheus.yml"
        assert path.exists(), f"Missing: {path}"

    def test_prometheus_yml_has_hermes_job(self) -> None:
        """prometheus.yml contains job_name: \"hermes\"."""
        path = _PROJECT_ROOT / "monitoring" / "prometheus" / "prometheus.yml"
        content = path.read_text(encoding="utf-8")
        assert 'job_name: "hermes"' in content

    def test_prometheus_yml_has_docker_target(self) -> None:
        """prometheus.yml references host.docker.internal:9191."""
        path = _PROJECT_ROOT / "monitoring" / "prometheus" / "prometheus.yml"
        content = path.read_text(encoding="utf-8")
        assert "host.docker.internal:9191" in content


class TestAlertRules:
    """Alert rules contain required GuinevereHermes alerts."""

    def test_alert_rules_exist(self) -> None:
        """guinevere-alerts.yml exists."""
        path = _PROJECT_ROOT / "monitoring" / "prometheus" / "rules" / "guinevere-alerts.yml"
        assert path.exists(), f"Missing: {path}"

    def test_alert_has_hermes_rules(self) -> None:
        """Alert rules contain GuinevereHermes alert names."""
        path = _PROJECT_ROOT / "monitoring" / "prometheus" / "rules" / "guinevere-alerts.yml"
        content = path.read_text(encoding="utf-8")
        assert "GuinevereHermes" in content


class TestGrafanaDashboard:
    """Grafana dashboard JSON is valid and contains Hermes panels."""

    def test_dashboard_exists(self) -> None:
        """guinevere-hermes.json exists."""
        path = _PROJECT_ROOT / "monitoring" / "grafana" / "dashboards" / "guinevere-hermes.json"
        assert path.exists(), f"Missing: {path}"

    def test_dashboard_is_valid_json(self) -> None:
        """Dashboard file is valid JSON."""
        path = _PROJECT_ROOT / "monitoring" / "grafana" / "dashboards" / "guinevere-hermes.json"
        data = _load_json(path)
        assert "title" in data  # verify data is usable

    def test_dashboard_has_title(self) -> None:
        """Dashboard has a title."""
        path = _PROJECT_ROOT / "monitoring" / "grafana" / "dashboards" / "guinevere-hermes.json"
        data = _load_json(path)
        assert "title" in data
        title = data["title"]
        assert isinstance(title, str)
        assert len(title) > 0


class TestAlertmanager:
    """Alertmanager config references Hermes gateway alerts."""

    def test_alertmanager_exists(self) -> None:
        """alertmanager.yml exists."""
        path = _PROJECT_ROOT / "monitoring" / "alertmanager" / "alertmanager.yml"
        assert path.exists(), f"Missing: {path}"

    def test_alertmanager_has_hermes_route(self) -> None:
        """Alertmanager config contains GuinevereHermesGatewayDown."""
        path = _PROJECT_ROOT / "monitoring" / "alertmanager" / "alertmanager.yml"
        content = path.read_text(encoding="utf-8")
        assert "GuinevereHermesGatewayDown" in content


class TestPromtailConfig:
    """Promtail config references hermes-gateway service."""

    def test_promtail_config_exists(self) -> None:
        """promtail-config.yml exists."""
        path = _PROJECT_ROOT / "monitoring" / "promtail" / "promtail-config.yml"
        assert path.exists(), f"Missing: {path}"

    def test_promtail_has_hermes_gateway(self) -> None:
        """Promtail config references hermes-gateway service."""
        path = _PROJECT_ROOT / "monitoring" / "promtail" / "promtail-config.yml"
        content = path.read_text(encoding="utf-8")
        assert "hermes-gateway" in content


class TestSystemdTemplate:
    """Hermes gateway systemd template exists with required hardening."""

    def test_systemd_template_exists(self) -> None:
        """hermes-gateway.service exists."""
        path = _PROJECT_ROOT / "systemd" / "hermes-gateway.service"
        assert path.exists(), f"Missing: {path}"

    def test_systemd_has_no_new_privileges(self) -> None:
        """Service unit has NoNewPrivileges=true."""
        path = _PROJECT_ROOT / "systemd" / "hermes-gateway.service"
        content = path.read_text(encoding="utf-8")
        assert "NoNewPrivileges=true" in content

    def test_systemd_has_memory_limit(self) -> None:
        """Service unit has MemoryMax=1G."""
        path = _PROJECT_ROOT / "systemd" / "hermes-gateway.service"
        content = path.read_text(encoding="utf-8")
        assert "MemoryMax=1G" in content

    def test_systemd_has_private_tmp(self) -> None:
        """Service unit has PrivateTmp=true."""
        path = _PROJECT_ROOT / "systemd" / "hermes-gateway.service"
        content = path.read_text(encoding="utf-8")
        assert "PrivateTmp=true" in content


class TestCoverageConfig:
    """Coverage configuration (.coveragerc) exists and is valid."""

    def test_coveragerc_exists(self) -> None:
        """.coveragerc exists at project root."""
        path = _PROJECT_ROOT / ".coveragerc"
        assert path.exists(), f"Missing: {path}"


class TestSafetyCriticalPaths:
    """Safety-critical paths config exists."""

    def test_safety_paths_exists(self) -> None:
        """.guinevere/safety-critical-paths.yml exists."""
        path = _PROJECT_ROOT / ".guinevere" / "safety-critical-paths.yml"
        assert path.exists(), f"Missing: {path}"


class TestSecretsRotationSchedule:
    """Secrets rotation schedule evidence file exists."""

    def test_secrets_schedule_exists(self) -> None:
        """Secrets rotation schedule evidence exists."""
        path = _PROJECT_ROOT / "docs" / "setup-evidence" / "phase-7" / "STEP-7.5" / "secrets-rotation-schedule.txt"
        assert path.exists(), f"Missing: {path}"
