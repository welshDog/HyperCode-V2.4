import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "check_fleet_manifest_containment.py"


def test_passes_on_clean_manifest(tmp_path):
    manifest = tmp_path / "render.yml"
    manifest.write_text(
        "services:\n"
        "  governor:\n"
        "    environment:\n"
        "      SAFETY_SHEPHERD_URL: http://safety-shepherd:8096\n"
        "    volumes:\n"
        "      - ./governance-control:/governance:ro\n"
        "  fleet-controller:\n"
        "    environment: {}\n"
    )
    r = subprocess.run([sys.executable, str(SCRIPT), str(manifest)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_fails_when_socket_mounted(tmp_path):
    manifest = tmp_path / "render.yml"
    manifest.write_text(
        "services:\n"
        "  governor:\n"
        "    volumes:\n"
        "      - /var/run/docker.sock:/var/run/docker.sock:ro\n"
    )
    r = subprocess.run([sys.executable, str(SCRIPT), str(manifest)], capture_output=True, text=True)
    assert r.returncode == 1
    assert "docker.sock" in r.stdout


def test_fails_on_docker_host_env(tmp_path):
    manifest = tmp_path / "render.yml"
    manifest.write_text(
        "services:\n"
        "  fleet-controller:\n"
        "    environment:\n"
        "      DOCKER_HOST: tcp://x:2375\n"
        "  governor:\n"
        "    environment: {}\n"
    )
    r = subprocess.run([sys.executable, str(SCRIPT), str(manifest)], capture_output=True, text=True)
    assert r.returncode == 1


def test_fails_when_watched_service_missing(tmp_path):
    """A watched service absent from the render (profile rename, broken
    `include:` chain, partial `config` render) must fail loudly, not pass
    vacuously — the containment proof is meaningless if the thing it's
    supposed to be watching silently isn't there."""
    manifest = tmp_path / "render.yml"
    manifest.write_text(
        "services:\n"
        "  governor:\n"
        "    environment:\n"
        "      SAFETY_SHEPHERD_URL: http://safety-shepherd:8096\n"
        "    volumes:\n"
        "      - ./governance-control:/governance:ro\n"
    )
    r = subprocess.run([sys.executable, str(SCRIPT), str(manifest)], capture_output=True, text=True)
    assert r.returncode == 1
    assert "fleet-controller" in r.stdout
    assert "not present" in r.stdout
