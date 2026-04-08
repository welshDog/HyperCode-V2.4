"""T16 — Kubernetes Helm chart test suite.

Tests validate the chart templates via `helm template` (dry-run rendering)
without a live cluster or Tiller.

Prerequisites:
  helm >= 3.14 installed and on PATH

Test coverage:
  1.  Chart structure — all required files exist
  2.  Chart.yaml — valid YAML, required fields present
  3.  values.yaml — valid YAML, sane defaults
  4.  helm template (dry-run) — renders without errors
  5.  Deployment templates — correct labels, replicas, image references
  6.  Service templates — correct ports and selectors
  7.  ConfigMap — all required env keys present
  8.  Secret — uses b64enc, helm.sh/resource-policy: keep
  9.  Ingress — disabled by default; enabled renders hosts correctly
  10. HPA — disabled by default; enabled renders correct metrics
  11. NOTES.txt — renders without errors
  12. Upgrade / rollback idempotency simulation
  13. Security context — non-root, capabilities dropped
  14. Resource limits — all containers have requests & limits
  15. Helm test pods — annotation present, restartPolicy Never
  16. Dependency declarations — postgresql + redis in Chart.yaml
  17. Neurodivergent branding — BROski mention in NOTES
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, List

import pytest
import yaml

CHART_DIR = Path(__file__).parent.parent / "hypercode"
TEMPLATES_DIR = CHART_DIR / "templates"


# ── Helpers ───────────────────────────────────────────────────────────────────

def helm_available() -> bool:
    try:
        subprocess.run(["helm", "version", "--short"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


HELM = pytest.mark.skipif(not helm_available(), reason="helm not installed")


def helm_template(values_overrides: dict | None = None) -> List[dict]:
    """Run `helm template` and return all rendered YAML documents."""
    cmd = ["helm", "template", "test-release", str(CHART_DIR), "--skip-crds"]
    if values_overrides:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(values_overrides, f)
            cmd += ["-f", f.name]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"helm template failed:\n{result.stderr}")
    docs = list(yaml.safe_load_all(result.stdout))
    return [d for d in docs if d is not None]


def find_docs(docs: List[dict], kind: str, name_contains: str = "") -> List[dict]:
    return [
        d for d in docs
        if d.get("kind") == kind
        and (not name_contains or name_contains in d["metadata"]["name"])
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Chart structure
# ─────────────────────────────────────────────────────────────────────────────

class TestChartStructure:
    REQUIRED_FILES = [
        "Chart.yaml",
        "values.yaml",
        "templates/_helpers.tpl",
        "templates/NOTES.txt",
        "templates/configmap.yaml",
        "templates/secret.yaml",
        "templates/serviceaccount.yaml",
        "templates/core-deployment.yaml",
        "templates/core-service.yaml",
        "templates/orchestrator-deployment.yaml",
        "templates/orchestrator-service.yaml",
        "templates/healer-deployment.yaml",
        "templates/ingress.yaml",
        "templates/hpa.yaml",
        "templates/tests/test-connection.yaml",
    ]

    @pytest.mark.parametrize("rel_path", REQUIRED_FILES)
    def test_required_file_exists(self, rel_path):
        assert (CHART_DIR / rel_path).exists(), f"Missing: {rel_path}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Chart.yaml validation
# ─────────────────────────────────────────────────────────────────────────────

class TestChartYaml:
    @pytest.fixture(autouse=True)
    def _load(self):
        with (CHART_DIR / "Chart.yaml").open() as f:
            self.chart = yaml.safe_load(f)

    def test_apiVersion_is_v2(self):
        assert self.chart["apiVersion"] == "v2"

    def test_name_is_hypercode(self):
        assert self.chart["name"] == "hypercode"

    def test_version_is_semver(self):
        import re
        assert re.match(r"\d+\.\d+\.\d+", self.chart["version"])

    def test_appVersion_matches_version(self):
        assert self.chart["appVersion"] == self.chart["version"]

    def test_description_not_empty(self):
        assert len(self.chart.get("description", "")) > 10

    def test_type_is_application(self):
        assert self.chart.get("type") == "application"

    def test_dependencies_include_postgresql(self):
        deps = {d["name"] for d in self.chart.get("dependencies", [])}
        assert "postgresql" in deps

    def test_dependencies_include_redis(self):
        deps = {d["name"] for d in self.chart.get("dependencies", [])}
        assert "redis" in deps

    def test_maintainers_present(self):
        assert len(self.chart.get("maintainers", [])) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 3. values.yaml validation
# ─────────────────────────────────────────────────────────────────────────────

class TestValuesYaml:
    @pytest.fixture(autouse=True)
    def _load(self):
        with (CHART_DIR / "values.yaml").open() as f:
            self.values = yaml.safe_load(f)

    def test_core_enabled_by_default(self):
        assert self.values["core"]["enabled"] is True

    def test_orchestrator_enabled_by_default(self):
        assert self.values["orchestrator"]["enabled"] is True

    def test_healer_enabled_by_default(self):
        assert self.values["healer"]["enabled"] is True

    def test_ingress_disabled_by_default(self):
        assert self.values["ingress"]["enabled"] is False

    def test_hpa_disabled_by_default(self):
        assert self.values["core"]["autoscaling"]["enabled"] is False

    def test_postgresql_enabled_by_default(self):
        assert self.values["postgresql"]["enabled"] is True

    def test_redis_enabled_by_default(self):
        assert self.values["redis"]["enabled"] is True

    def test_core_resources_have_requests_and_limits(self):
        res = self.values["core"]["resources"]
        assert "requests" in res and "limits" in res

    def test_replica_count_core_at_least_2(self):
        assert self.values["replicaCount"]["core"] >= 2

    def test_pod_security_context_non_root(self):
        assert self.values["podSecurityContext"]["runAsNonRoot"] is True

    def test_container_security_drops_all_capabilities(self):
        caps = self.values["containerSecurityContext"]["capabilities"]["drop"]
        assert "ALL" in caps

    def test_secrets_use_existing_false_by_default(self):
        assert self.values["secrets"]["useExisting"] is False


# ─────────────────────────────────────────────────────────────────────────────
# 4-16. helm template rendering tests (require helm binary)
# ─────────────────────────────────────────────────────────────────────────────

@HELM
class TestHelmTemplateRendering:
    @pytest.fixture(scope="class")
    def docs(self):
        return helm_template()

    def test_renders_without_error(self, docs):
        assert len(docs) > 0

    def test_all_docs_have_kind(self, docs):
        for doc in docs:
            assert "kind" in doc, f"Document missing 'kind': {doc}"

    def test_all_docs_have_metadata(self, docs):
        for doc in docs:
            assert "metadata" in doc


@HELM
class TestDeploymentTemplates:
    @pytest.fixture(scope="class")
    def docs(self):
        return helm_template()

    def test_core_deployment_rendered(self, docs):
        deployments = find_docs(docs, "Deployment", "core")
        assert len(deployments) >= 1

    def test_core_deployment_replicas(self, docs):
        deps = find_docs(docs, "Deployment", "core")
        assert deps[0]["spec"]["replicas"] == 2

    def test_orchestrator_deployment_rendered(self, docs):
        deps = find_docs(docs, "Deployment", "orchestrator")
        assert len(deps) >= 1

    def test_healer_deployment_rendered(self, docs):
        deps = find_docs(docs, "Deployment", "healer")
        assert len(deps) >= 1

    def test_healer_deployment_strategy_is_recreate(self, docs):
        deps = find_docs(docs, "Deployment", "healer")
        assert deps[0]["spec"]["strategy"]["type"] == "Recreate"

    def test_core_deployment_has_liveness_probe(self, docs):
        deps = find_docs(docs, "Deployment", "core")
        container = deps[0]["spec"]["template"]["spec"]["containers"][0]
        assert "livenessProbe" in container

    def test_core_deployment_has_readiness_probe(self, docs):
        deps = find_docs(docs, "Deployment", "core")
        container = deps[0]["spec"]["template"]["spec"]["containers"][0]
        assert "readinessProbe" in container

    def test_all_deployments_have_resource_limits(self, docs):
        deployments = find_docs(docs, "Deployment")
        for dep in deployments:
            for container in dep["spec"]["template"]["spec"]["containers"]:
                assert "resources" in container, (
                    f"{dep['metadata']['name']} container missing resources"
                )

    def test_configmap_checksum_annotation_on_core(self, docs):
        deps = find_docs(docs, "Deployment", "core")
        annotations = deps[0]["spec"]["template"]["metadata"].get("annotations", {})
        assert "checksum/config" in annotations

    def test_pod_security_context_non_root(self, docs):
        deps = find_docs(docs, "Deployment", "core")
        sec = deps[0]["spec"]["template"]["spec"].get("securityContext", {})
        assert sec.get("runAsNonRoot") is True


@HELM
class TestServiceTemplates:
    @pytest.fixture(scope="class")
    def docs(self):
        return helm_template()

    def test_core_service_rendered(self, docs):
        svcs = find_docs(docs, "Service", "core")
        assert len(svcs) >= 1

    def test_core_service_port_8000(self, docs):
        svcs = find_docs(docs, "Service", "core")
        ports = svcs[0]["spec"]["ports"]
        assert any(p["port"] == 8000 for p in ports)

    def test_orchestrator_service_rendered(self, docs):
        svcs = find_docs(docs, "Service", "orchestrator")
        assert len(svcs) >= 1

    def test_orchestrator_service_port_8081(self, docs):
        svcs = find_docs(docs, "Service", "orchestrator")
        ports = svcs[0]["spec"]["ports"]
        assert any(p["port"] == 8081 for p in ports)


@HELM
class TestConfigMapTemplate:
    @pytest.fixture(scope="class")
    def configmap(self):
        docs = helm_template()
        cms = find_docs(docs, "ConfigMap")
        assert cms, "No ConfigMap rendered"
        return cms[0]

    def test_redis_url_present(self, configmap):
        assert "REDIS_URL" in configmap["data"]

    def test_database_url_present(self, configmap):
        assert "HYPERCODE_DB_URL" in configmap["data"]

    def test_environment_is_production(self, configmap):
        assert configmap["data"]["ENVIRONMENT"] == "production"


@HELM
class TestSecretTemplate:
    @pytest.fixture(scope="class")
    def secret(self):
        docs = helm_template()
        secrets = find_docs(docs, "Secret")
        assert secrets, "No Secret rendered"
        return secrets[0]

    def test_resource_policy_keep_annotation(self, secret):
        annotations = secret.get("metadata", {}).get("annotations", {})
        assert annotations.get("helm.sh/resource-policy") == "keep"

    def test_secret_type_is_opaque(self, secret):
        assert secret["type"] == "Opaque"

    def test_data_has_api_key(self, secret):
        assert "api-key" in secret.get("data", {})

    def test_data_has_jwt_secret(self, secret):
        assert "jwt-secret" in secret.get("data", {})


@HELM
class TestIngressTemplate:
    def test_ingress_not_rendered_by_default(self):
        docs = helm_template()
        ingresses = find_docs(docs, "Ingress")
        assert len(ingresses) == 0

    def test_ingress_rendered_when_enabled(self):
        docs = helm_template({"ingress": {"enabled": True}})
        ingresses = find_docs(docs, "Ingress")
        assert len(ingresses) == 1

    def test_ingress_renders_hosts(self):
        docs = helm_template({
            "ingress": {
                "enabled": True,
                "hosts": [{"host": "hypercode.example.com", "paths": [
                    {"path": "/", "pathType": "Prefix", "service": "core", "port": 8000}
                ]}],
            }
        })
        ing = find_docs(docs, "Ingress")[0]
        rules = ing["spec"]["rules"]
        assert any(r["host"] == "hypercode.example.com" for r in rules)


@HELM
class TestHPATemplate:
    def test_hpa_not_rendered_by_default(self):
        docs = helm_template()
        hpas = find_docs(docs, "HorizontalPodAutoscaler")
        assert len(hpas) == 0

    def test_hpa_rendered_when_enabled(self):
        docs = helm_template({"core": {"autoscaling": {"enabled": True}}})
        hpas = find_docs(docs, "HorizontalPodAutoscaler")
        assert len(hpas) >= 1

    def test_hpa_min_replicas(self):
        docs = helm_template({
            "core": {"autoscaling": {"enabled": True, "minReplicas": 3, "maxReplicas": 8}}
        })
        hpa = find_docs(docs, "HorizontalPodAutoscaler")[0]
        assert hpa["spec"]["minReplicas"] == 3

    def test_hpa_max_replicas(self):
        docs = helm_template({
            "core": {"autoscaling": {"enabled": True, "minReplicas": 2, "maxReplicas": 6}}
        })
        hpa = find_docs(docs, "HorizontalPodAutoscaler")[0]
        assert hpa["spec"]["maxReplicas"] == 6


@HELM
class TestHelmTestPods:
    def test_test_pod_has_helm_hook_annotation(self):
        docs = helm_template()
        test_pods = [
            d for d in docs
            if d.get("kind") == "Pod"
            and "test" in d["metadata"].get("name", "")
        ]
        assert len(test_pods) >= 1
        for pod in test_pods:
            annotations = pod["metadata"].get("annotations", {})
            assert "helm.sh/hook" in annotations
            assert "test" in annotations["helm.sh/hook"]

    def test_test_pod_restart_policy_never(self):
        docs = helm_template()
        test_pods = [d for d in docs if d.get("kind") == "Pod"]
        for pod in test_pods:
            assert pod["spec"]["restartPolicy"] == "Never"


@HELM
class TestServiceAccountTemplate:
    def test_service_account_rendered_by_default(self):
        docs = helm_template()
        sas = find_docs(docs, "ServiceAccount")
        assert len(sas) >= 1

    def test_service_account_not_rendered_when_disabled(self):
        docs = helm_template({"serviceAccount": {"create": False}})
        sas = find_docs(docs, "ServiceAccount")
        assert len(sas) == 0


@HELM
class TestNotesRendering:
    def test_helm_lint_passes(self):
        result = subprocess.run(
            ["helm", "lint", str(CHART_DIR)],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"helm lint failed:\n{result.stdout}\n{result.stderr}"

    def test_broski_mention_in_notes(self):
        notes = (CHART_DIR / "templates" / "NOTES.txt").read_text()
        assert "BROski" in notes


# ─────────────────────────────────────────────────────────────────────────────
# 17. Upgrade / rollback simulation (values-only test)
# ─────────────────────────────────────────────────────────────────────────────

@HELM
class TestUpgradeRollback:
    def test_increasing_replicas_renders_more(self):
        docs_2 = helm_template({"replicaCount": {"core": 2}})
        docs_5 = helm_template({"replicaCount": {"core": 5}})
        core_2 = find_docs(docs_2, "Deployment", "core")[0]["spec"]["replicas"]
        core_5 = find_docs(docs_5, "Deployment", "core")[0]["spec"]["replicas"]
        assert core_5 > core_2

    def test_disabling_service_removes_deployment(self):
        docs = helm_template({"orchestrator": {"enabled": False}})
        deps = find_docs(docs, "Deployment", "orchestrator")
        assert len(deps) == 0

    def test_rollback_to_defaults_renders_clean(self):
        """Re-rendering with empty overrides must produce valid docs."""
        docs = helm_template({})
        assert len(docs) > 5
