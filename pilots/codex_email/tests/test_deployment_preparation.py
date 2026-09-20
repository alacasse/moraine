"""Local artifact checks; these are not multi-UID/systemd installation probes."""
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

DEPLOY = Path(__file__).resolve().parents[1] / "deploy"
spec = importlib.util.spec_from_file_location("verify_install", DEPLOY / "verify_install.py")
verify_install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_install)


def test_installation_gate_rejects_current_user_owned_code(tmp_path):
    # Real ownership, no os.geteuid/chown mock. We are an ordinary user.
    assert tmp_path.stat().st_uid != 0
    config = tmp_path / "config.json"
    config.write_text("{}")
    with pytest.raises(ValueError, match="administrator ownership"):
        verify_install.verify(tmp_path, config)


def test_gate_checks_trusted_system_file_and_rejects_mutable_symlink_target(tmp_path):
    verify_install.check_path(Path("/usr/bin/python3"))
    target = tmp_path / "editable.py"
    target.write_text("pass")
    link = tmp_path / "link.py"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="administrator ownership"):
        verify_install.check_path(link)


def test_supervision_probe_refuses_without_explicit_opt_in():
    result = subprocess.run([sys.executable, str(DEPLOY / "probe_supervision.py")],
                            capture_output=True, text=True)
    assert result.returncode == 2
    assert "explicit flag" in result.stderr


def test_identity_probe_refuses_same_uid_roles_before_access():
    result = subprocess.run([sys.executable, str(DEPLOY / "probe_identity.py"),
                             "--confirm-installed-probe", "--role", "agent",
                             "--expected-uid", "1000", "--human-uid", "1000",
                             "--service-uid", "1000", "--human-gid", "1000",
                             "--broker-pid", "1", "--opa-pid", "1"],
                            capture_output=True, text=True)
    assert result.returncode == 2
    assert "distinct real UIDs" in result.stderr


def test_standard_venv_directory_link_stays_inside_installation(tmp_path, monkeypatch):
    # Structural regression only: ownership gates are separately checked above.
    # No root-owned installation or OS isolation is simulated by this test.
    monkeypatch.setattr(verify_install, "check_path", lambda path: None)
    root = tmp_path / "install"
    lib = root / ".venv/lib"
    lib.mkdir(parents=True)
    (root / ".venv/lib64").symlink_to("lib", target_is_directory=True)
    verify_install.verify(root, tmp_path / "config.json")
    (root / "outside").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="stay inside"):
        verify_install.verify(root, tmp_path / "config.json")
