"""T16 — Kubernetes Helm chart validation tests.

Tests validate the HyperCode V2.0 Helm chart WITHOUT requiring a live cluster.
All assertions run against parsed YAML / template rendering output only.

Coverage:
  1. Chart metadata (Chart.yaml)
  2. Default values structure (values.yaml)
  3. Template file existence
  4. Secret template security
  5. Deployment templates — core, orchestrator, healer
  6. Service templates
  7. HPA template
  8. Ingress template
  9. ConfigMap template
  10. ServiceAccount template
  11. Security context settings
  12. Resource limits declared
  13. Liveness / readiness probes
  14. Cross-file consistency checks
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

# ── Paths ─────────────────────────────────────────────────────────────────────

CHART_ROOT = Path(__file__).parents[1] / "helm" / "hypercode"
CHART_YAML = CHART_ROOT / "Chart.yaml"
VALUES_YAML = CHART_ROOT / "values.yaml"
TEMPLATES_DIR = CHART_ROOT / "templates"
TEST_TEMPLATE = TEMPLATES_DIR / "tests" / "test-connection.yaml"


def _load_yaml(path: Path) -> Any:
    with path.open() as f:
        return yaml.safe_load(f)


chart = _load_yaml(CHART_YAML)
values = _load_yaml(VALUES_YAML)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Chart.yaml metadata
# ─────────────────────────────────────────────────────────────────────────────

class TestChartMetadata:
    def test_chart_yaml_exists(self):
        assert CHART_YAML.exists()

    def test_chart_has_name(self):
        assert "name" in chart
        assert chart["name"] == "hypercode"

    def test_chart_has_version(self):
        assert "version" in chart
        # Must be semver-ish: digits.digits.digits
        assert re.match(r"^\d+\.\d+\.\d+", str(chart["version"]))

    def test_chart_has_app_version(self):
        assert "appVersion" in chart

    def test_chart_has_description(self):
        assert "description" in chart
        assert len(chart["description"]) > 5

    def test_chart_api_version_is_v2(self):
        assert chart.get("apiVersion") == "v2"

    def test_chart_type_is_application(self):
        assert chart.get("type") == "application"

    def test_chart_has_postgresql_dependency(self):
        deps = {d["name"] for d in chart.get("dependencies", [])}
        assert "postgresql" in deps

    def test_chart_has_redis_dependency(self):
        deps = {d["name"] for d in chart.get("dependencies", [])}
        assert "redis" in deps

    def test_postgresql_dependency_has_condition(self):
        for dep in chart.get("dependencies", []):
            if dep["name"] == "postgresql":
                assert "condition" in dep
                break

    def test_redis_dependency_has_condition(self):
        for dep in chart.get("dependencies", []):
            if dep["name"] == "redis":
                assert "condition" in dep
                break


# ─────────────────────────────────────────────────────────────────────────────
# 2. values.yaml structure
# ─────────────────────────────────────────────────────────────────────────────

class TestValuesStructure:
    def test_values_yaml_exists(self):
        assert VALUES_YAML.exists()

    def test_has_replica_count(self):
        assert "replicaCount" in values

    def test_replica_count_has_core(self):
        assert "core" in values["replicaCount"]
        assert isinstance(values["replicaCount"]["core"], int)

    def test_has_core_section(self):
        assert "core" in values

    def test_core_has_service(self):
        assert "service" in values["core"]

    def test_core_service_has_port(self):
        assert "port" in values["core"]["service"]
        assert values["core"]["service"]["port"] == 8000

    def test_has_orchestrator_section(self):
        assert "orchestrator" in values

    def test_orchestrator_has_service_port(self):
        assert values["orchestrator"]["service"]["port"] == 8081

    def test_has_postgresql_section(self):
        assert "postgresql" in values

    def test_postgresql_has_enabled_flag(self):
        assert "enabled" in values["postgresql"]
        assert isinstance(values["postgresql"]["enabled"], bool)

    def test_has_redis_section(self):
        assert "redis" in values

    def test_redis_has_enabled_flag(self):
        assert "enabled" in values["redis"]

    def test_has_ingress_section(self):
        assert "ingress" in values

    def test_ingress_disabled_by_default(self):
        assert values["ingress"]["enabled"] is False

    def test_has_secrets_section(self):
        assert "secrets" in values

    def test_secrets_use_existing_flag_present(self):
        assert "useExisting" in values["secrets"]

    def test_has_service_account_section(self):
        assert "serviceAccount" in values

    def test_service_account_create_is_bool(self):
        assert isinstance(values["serviceAccount"]["create"], bool)

    def test_has_pod_security_context(self):
        assert "podSecurityContext" in values

    def test_runs_as_non_root(self):
        assert values["podSecurityContext"].get("runAsNonRoot") is True

    def test_has_container_security_context(self):
        assert "containerSecurityContext" in values

    def test_privilege_escalation_disabled(self):
        assert values["containerSecurityContext"].get("allowPrivilegeEscalation") is False

    def test_capabilities_drop_all(self):
        caps = values["containerSecurityContext"].get("capabilities", {})
        assert "ALL" in caps.get("drop", [])

    def test_has_pdb_section(self):
        assert "podDisruptionBudget" in values

    def test_core_has_resources(self):
        assert "resources" in values["core"]

    def test_core_resources_has_requests_and_limits(self):
        res = values["core"]["resources"]
        assert "requests" in res
        assert "limits" in res

    def test_core_liveness_probe_configured(self):
        assert "livenessProbe" in values["core"]
        probe = values["core"]["livenessProbe"]
        assert probe["httpGet"]["path"] == "/health"

    def test_core_readiness_probe_configured(self):
        assert "readinessProbe" in values["core"]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Template file existence
# ─────────────────────────────────────────────────────────────────────────────

class TestTemplateFiles:
    REQUIRED_TEMPLATES = [
        "_helpers.tpl",
        "configmap.yaml",
        "core-deployment.yaml",
        "core-service.yaml",
        "orchestrator-deployment.yaml",
        "orchestrator-service.yaml",
        "healer-deployment.yaml",
        "hpa.yaml",
        "ingress.yaml",
        "secret.yaml",
        "serviceaccount.yaml",
        "NOTES.txt",
        "tests/test-connection.yaml",
    ]

    @pytest.mark.parametrize("template", REQUIRED_TEMPLATES)
    def test_template_file_exists(self, template):
        assert (TEMPLATES_DIR / template).exists(), f"Missing template: {template}"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Secret template security
# ─────────────────────────────────────────────────────────────────────────────

class TestSecretTemplate:
    def test_secret_yaml_exists(self):
        assert (TEMPLATES_DIR / "secret.yaml").exists()

    def test_secret_uses_helm_if_condition(self):
        content = (TEMPLATES_DIR / "secret.yaml").read_text()
        assert "if" in content  # conditional rendering

    def test_secret_kind_is_secret(self):
        content = (TEMPLATES_DIR / "secret.yaml").read_text()
        assert "kind: Secret" in content

    def test_secret_no_hardcoded_credentials(self):
        content = (TEMPLATES_DIR / "secret.yaml").read_text().lower()
        forbidden = ["changeme", "password123", "secret123", "sk-ant-"]
        for pattern in forbidden:
            assert pattern not in content, f"Hardcoded credential found: {pattern}"

    def test_values_secret_values_are_empty_by_default(self):
        """Secret values in values.yaml should be empty strings — not defaults."""
        secret_vals = values.get("secrets", {}).get("values", {})
        for key, val in secret_vals.items():
            assert val == "" or val is None, (
                f"Secret '{key}' has a non-empty default value in values.yaml"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Deployment templates
# ─────────────────────────────────────────────────────────────────────────────

class TestDeploymentTemplates:
    DEPLOYMENT_TEMPLATES = [
        "core-deployment.yaml",
        "orchestrator-deployment.yaml",
        "healer-deployment.yaml",
    ]

    @pytest.mark.parametrize("template", DEPLOYMENT_TEMPLATES)
    def test_deployment_kind(self, template):
        content = (TEMPLATES_DIR / template).read_text()
        assert "kind: Deployment" in content

    @pytest.mark.parametrize("template", DEPLOYMENT_TEMPLATES)
    def test_deployment_has_selector(self, template):
        content = (TEMPLATES_DIR / template).read_text()
        assert "selector:" in content

    @pytest.mark.parametrize("template", DEPLOYMENT_TEMPLATES)
    def test_deployment_has_image(self, template):
        content = (TEMPLATES_DIR / template).read_text()
        assert "image:" in content

    @pytest.mark.parametrize("template", DEPLOYMENT_TEMPLATES)
    def test_deployment_uses_helm_include_for_name(self, template):
        content = (TEMPLATES_DIR / template).read_text()
        # Should use {{ include "hypercode.fullname" . }} pattern
        assert 'include "hypercode.' in content

    def test_core_deployment_references_correct_port(self):
        content = (TEMPLATES_DIR / "core-deployment.yaml").read_text()
        assert "8000" in content

    def test_orchestrator_deployment_references_correct_port(self):
        content = (TEMPLATES_DIR / "orchestrator-deployment.yaml").read_text()
        # Port may be a literal OR a values template reference
        assert "8081" in content or "orchestrator.service.port" in content


# ─────────────────────────────────────────────────────────────────────────────
# 6. Service templates
# ─────────────────────────────────────────────────────────────────────────────

class TestServiceTemplates:
    SERVICE_TEMPLATES = ["core-service.yaml", "orchestrator-service.yaml"]

    @pytest.mark.parametrize("template", SERVICE_TEMPLATES)
    def test_service_kind(self, template):
        content = (TEMPLATES_DIR / template).read_text()
        assert "kind: Service" in content

    @pytest.mark.parametrize("template", SERVICE_TEMPLATES)
    def test_service_has_selector(self, template):
        content = (TEMPLATES_DIR / template).read_text()
        assert "selector:" in content

    @pytest.mark.parametrize("template", SERVICE_TEMPLATES)
    def test_service_has_port_definition(self, template):
        content = (TEMPLATES_DIR / template).read_text()
        assert "port:" in content


# ─────────────────────────────────────────────────────────────────────────────
# 7. HPA template
# ─────────────────────────────────────────────────────────────────────────────

class TestHPATemplate:
    def test_hpa_exists(self):
        assert (TEMPLATES_DIR / "hpa.yaml").exists()

    def test_hpa_kind(self):
        content = (TEMPLATES_DIR / "hpa.yaml").read_text()
        assert "HorizontalPodAutoscaler" in content

    def test_hpa_references_min_replicas(self):
        content = (TEMPLATES_DIR / "hpa.yaml").read_text()
        assert "minReplicas" in content

    def test_hpa_references_max_replicas(self):
        content = (TEMPLATES_DIR / "hpa.yaml").read_text()
        assert "maxReplicas" in content

    def test_hpa_uses_conditional(self):
        content = (TEMPLATES_DIR / "hpa.yaml").read_text()
        assert "if" in content  # should be guarded by autoscaling.enabled


# ─────────────────────────────────────────────────────────────────────────────
# 8. Ingress template
# ─────────────────────────────────────────────────────────────────────────────

class TestIngressTemplate:
    def test_ingress_exists(self):
        assert (TEMPLATES_DIR / "ingress.yaml").exists()

    def test_ingress_kind(self):
        content = (TEMPLATES_DIR / "ingress.yaml").read_text()
        assert "kind: Ingress" in content

    def test_ingress_guarded_by_enabled_flag(self):
        content = (TEMPLATES_DIR / "ingress.yaml").read_text()
        assert "ingress.enabled" in content or ".Values.ingress.enabled" in content

    def test_ingress_references_class_name(self):
        content = (TEMPLATES_DIR / "ingress.yaml").read_text()
        assert "ingressClassName" in content or "className" in content


# ─────────────────────────────────────────────────────────────────────────────
# 9. ConfigMap template
# ─────────────────────────────────────────────────────────────────────────────

class TestConfigMapTemplate:
    def test_configmap_exists(self):
        assert (TEMPLATES_DIR / "configmap.yaml").exists()

    def test_configmap_kind(self):
        content = (TEMPLATES_DIR / "configmap.yaml").read_text()
        assert "kind: ConfigMap" in content

    def test_configmap_no_secrets(self):
        content = (TEMPLATES_DIR / "configmap.yaml").read_text().lower()
        # ConfigMaps should not contain sensitive keywords
        forbidden = ["password", "secret", "token", "api_key", "apikey"]
        for word in forbidden:
            assert word not in content, (
                f"Potential secret '{word}' found in ConfigMap template — use Secret instead"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 10. ServiceAccount template
# ─────────────────────────────────────────────────────────────────────────────

class TestServiceAccountTemplate:
    def test_serviceaccount_exists(self):
        assert (TEMPLATES_DIR / "serviceaccount.yaml").exists()

    def test_serviceaccount_kind(self):
        content = (TEMPLATES_DIR / "serviceaccount.yaml").read_text()
        assert "kind: ServiceAccount" in content

    def test_serviceaccount_guarded_by_create_flag(self):
        content = (TEMPLATES_DIR / "serviceaccount.yaml").read_text()
        assert "serviceAccount.create" in content or ".Values.serviceAccount.create" in content


# ─────────────────────────────────────────────────────────────────────────────
# 11. Helm test template
# ─────────────────────────────────────────────────────────────────────────────

class TestHelmTestTemplate:
    def test_test_connection_exists(self):
        assert TEST_TEMPLATE.exists()

    def test_test_connection_is_pod(self):
        content = TEST_TEMPLATE.read_text()
        assert "kind: Pod" in content

    def test_test_connection_has_helm_hook_annotation(self):
        content = TEST_TEMPLATE.read_text()
        assert "helm.sh/hook" in content
        assert '"test"' in content or "test" in content

    def test_test_connection_has_never_restart(self):
        content = TEST_TEMPLATE.read_text()
        assert "restartPolicy: Never" in content

    def test_test_connection_tests_core_health(self):
        content = TEST_TEMPLATE.read_text()
        assert "/health" in content

    def test_test_connection_tests_orchestrator(self):
        content = TEST_TEMPLATE.read_text()
        assert "orchestrator" in content.lower()

    def test_test_connection_has_delete_policy(self):
        content = TEST_TEMPLATE.read_text()
        assert "hook-delete-policy" in content


# ─────────────────────────────────────────────────────────────────────────────
# 12. Cross-file consistency
# ─────────────────────────────────────────────────────────────────────────────

class TestCrossFileConsistency:
    def test_chart_version_format_matches_app_version(self):
        """chart.version and chart.appVersion should have the same major.minor."""
        chart_ver = str(chart["version"])
        app_ver = str(chart["appVersion"]).strip('"')
        chart_major_minor = ".".join(chart_ver.split(".")[:2])
        app_major_minor = ".".join(app_ver.split(".")[:2])
        assert chart_major_minor == app_major_minor, (
            f"Chart version {chart_ver} and appVersion {app_ver} major.minor mismatch"
        )

    def test_core_port_consistent_in_values_and_probe(self):
        port = values["core"]["service"]["port"]
        probe_port = values["core"]["livenessProbe"]["httpGet"]["port"]
        assert port == probe_port, (
            f"core.service.port ({port}) != livenessProbe port ({probe_port})"
        )

    def test_postgresql_enabled_default_matches_dependency_condition(self):
        # values["postgresql"]["enabled"] should be a bool so the condition works
        assert isinstance(values["postgresql"]["enabled"], bool)

    def test_redis_enabled_default_matches_dependency_condition(self):
        assert isinstance(values["redis"]["enabled"], bool)

    def test_helpers_tpl_defines_fullname(self):
        content = (TEMPLATES_DIR / "_helpers.tpl").read_text()
        assert "hypercode.fullname" in content

    def test_helpers_tpl_defines_labels(self):
        content = (TEMPLATES_DIR / "_helpers.tpl").read_text()
        assert "hypercode.labels" in content

    def test_notes_txt_references_chart_name(self):
        content = (TEMPLATES_DIR / "NOTES.txt").read_text(encoding="utf-8")
        assert "hypercode" in content.lower() or "HyperCode" in content
