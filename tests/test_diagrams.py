"""Tests for md2pdf diagram rendering and cross-platform binary resolution.

Migrated from the legacy tools/md2pdf/test_md2pdf.py. The mocked-subprocess
tests patch the ``md2pdf.diagrams`` module's own ``subprocess``/``shutil``/
``Path`` references. Integration tests ``skipif`` the ``d2``/``mmdr`` CLIs are
absent. Adds an extensionless-POSIX resolver test (critique E6).
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from md2pdf import diagrams


MERMAID_SRC = "flowchart LR\n    A --> B --> C"
D2_SRC = "x -> y: edge\ny -> z: edge"


def _patch_resolver(monkeypatch, fake="/fake/bin/tool"):
    monkeypatch.setattr(diagrams, "_resolve_diagram_binary", lambda lang: fake)


# --- render_diagram command formation --------------------------------------

def test_render_diagram_d2_command_formation(tmp_path, monkeypatch):
    _patch_resolver(monkeypatch, "/fake/d2")
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs

        class R:
            returncode = 0
            stderr = b""
        return R()

    monkeypatch.setattr(diagrams.subprocess, "run", fake_run)
    out = diagrams.render_diagram("d2", D2_SRC, tmp_path, "My Slide")
    assert out.name.startswith("diagram_d2_") and out.suffix == ".pdf"
    cmd = captured["cmd"]
    assert cmd[0] == "/fake/d2"
    assert cmd[1:5] == ["--theme", "0", "--browser", "0"]
    assert cmd[-1] == str(out)
    kw = captured["kwargs"]
    assert kw["timeout"] == 30
    assert kw["capture_output"] is True
    assert kw["stdin"] == subprocess.DEVNULL


def test_render_diagram_mermaid_command_formation(tmp_path, monkeypatch):
    _patch_resolver(monkeypatch, "/fake/mmdr")
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd

        class R:
            returncode = 0
            stderr = b""
        return R()

    monkeypatch.setattr(diagrams.subprocess, "run", fake_run)
    out = diagrams.render_diagram("mermaid", MERMAID_SRC, tmp_path, "Flow")
    assert out.name.startswith("diagram_mermaid_") and out.suffix == ".png"
    cmd = captured["cmd"]
    assert cmd[0] == "/fake/mmdr"
    assert "-e" in cmd and cmd[cmd.index("-e") + 1] == "png"
    assert "-w" in cmd and cmd[cmd.index("-w") + 1] == "2400"
    assert "-t" in cmd and cmd[cmd.index("-t") + 1] == "default"
    # mmdr 0.3.1 has no background flag; it renders opaque white by default.
    assert "-b" not in cmd
    assert "-H" not in cmd  # must not distort aspect ratio


def test_render_diagram_hash_namespacing(tmp_path, monkeypatch):
    _patch_resolver(monkeypatch)

    def fake_run(cmd, **kwargs):
        class R:
            returncode = 0
            stderr = b""
        return R()

    monkeypatch.setattr(diagrams.subprocess, "run", fake_run)
    a = diagrams.render_diagram("d2", "a -> b", tmp_path, "S")
    b = diagrams.render_diagram("d2", "c -> d", tmp_path, "S")
    assert a.name != b.name


def test_render_diagram_idempotent_returns_existing(tmp_path, monkeypatch):
    _patch_resolver(monkeypatch)
    calls = {"n": 0}

    def fake_run(cmd, **kwargs):
        calls["n"] += 1

        class R:
            returncode = 0
            stderr = b""
        return R()

    monkeypatch.setattr(diagrams.subprocess, "run", fake_run)
    first = diagrams.render_diagram("d2", D2_SRC, tmp_path, "S")
    # Simulate the renderer having produced the output file.
    first.write_bytes(b"%PDF-stub")
    second = diagrams.render_diagram("d2", D2_SRC, tmp_path, "S")
    assert first == second
    # subprocess.run invoked once for the first call; the second short-circuits.
    assert calls["n"] == 1


def test_render_diagram_timeout_raises(tmp_path, monkeypatch):
    _patch_resolver(monkeypatch)

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, 30)

    monkeypatch.setattr(diagrams.subprocess, "run", fake_run)
    with pytest.raises(SystemExit) as ei:
        diagrams.render_diagram("mermaid", MERMAID_SRC, tmp_path, "Hung Slide")
    msg = str(ei.value)
    assert "timed out" in msg and "Hung Slide" in msg and "mermaid" in msg


def test_render_diagram_nonzero_raises_with_stderr(tmp_path, monkeypatch):
    _patch_resolver(monkeypatch)

    def fake_run(cmd, **kwargs):
        class R:
            returncode = 1
            stderr = "syntax error at line 2".encode("utf-8")
        return R()

    monkeypatch.setattr(diagrams.subprocess, "run", fake_run)
    with pytest.raises(SystemExit) as ei:
        diagrams.render_diagram("d2", "bad!!", tmp_path, "Broken Slide")
    msg = str(ei.value)
    assert "d2" in msg and "Broken Slide" in msg and "syntax error at line 2" in msg


def test_render_diagram_missing_binary_raises(tmp_path, monkeypatch):
    # Real resolver, but force both PATH lookup and fallback to fail.
    monkeypatch.setattr(diagrams.shutil, "which", lambda name: None)
    monkeypatch.setattr(diagrams.Path, "exists", lambda self: False)
    with pytest.raises(SystemExit) as ei:
        diagrams.render_diagram("mermaid", MERMAID_SRC, tmp_path, "No Tool")
    msg = str(ei.value)
    assert "mmdr" in msg and "cargo install mmdr" in msg


def test_render_diagram_zero_byte_cache_is_rerendered(tmp_path, monkeypatch):
    # A pre-existing ZERO-byte output (from a prior aborted run) must NOT be
    # returned as-is; render_diagram re-invokes the renderer.
    _patch_resolver(monkeypatch)
    calls = {"n": 0}

    def fake_run(cmd, **kwargs):
        calls["n"] += 1
        target = next(a for a in cmd if str(a).endswith((".pdf", ".png")))
        Path(target).write_bytes(b"%PDF-rendered")

        class R:
            returncode = 0
            stderr = b""
        return R()

    monkeypatch.setattr(diagrams.subprocess, "run", fake_run)
    digest = hashlib.sha256(D2_SRC.encode("utf-8")).hexdigest()[:16]
    stale = tmp_path / f"diagram_d2_{digest}.pdf"
    stale.write_bytes(b"")
    assert stale.stat().st_size == 0

    out = diagrams.render_diagram("d2", D2_SRC, tmp_path, "S")
    assert out == stale
    assert calls["n"] == 1  # the zero-byte cache did not short-circuit
    assert out.stat().st_size > 0  # replaced with a real render


def test_render_diagram_nonzero_removes_partial_out_file(tmp_path, monkeypatch):
    # A failed render must not leave a partial out_file behind.
    _patch_resolver(monkeypatch)

    def fake_run(cmd, **kwargs):
        target = next(a for a in cmd if str(a).endswith((".pdf", ".png")))
        Path(target).write_bytes(b"partial")

        class R:
            returncode = 1
            stderr = b"boom"
        return R()

    monkeypatch.setattr(diagrams.subprocess, "run", fake_run)
    digest = hashlib.sha256(D2_SRC.encode("utf-8")).hexdigest()[:16]
    out_file = tmp_path / f"diagram_d2_{digest}.pdf"
    with pytest.raises(SystemExit):
        diagrams.render_diagram("d2", D2_SRC, tmp_path, "Broken Slide")
    assert not out_file.exists()  # partial output cleaned up


def test_render_diagram_timeout_removes_partial_out_file(tmp_path, monkeypatch):
    # A timeout must also clean up any partially written out_file.
    _patch_resolver(monkeypatch)
    digest = hashlib.sha256(MERMAID_SRC.encode("utf-8")).hexdigest()[:16]
    out_file = tmp_path / f"diagram_mermaid_{digest}.png"

    def fake_run(cmd, **kwargs):
        target = next(a for a in cmd if str(a).endswith((".pdf", ".png")))
        Path(target).write_bytes(b"partial")
        raise subprocess.TimeoutExpired(cmd, 30)

    monkeypatch.setattr(diagrams.subprocess, "run", fake_run)
    with pytest.raises(SystemExit):
        diagrams.render_diagram("mermaid", MERMAID_SRC, tmp_path, "Hung Slide")
    assert not out_file.exists()


# --- cross-platform binary resolution (critique E6) ------------------------

def test_resolve_binary_prefers_path(monkeypatch):
    monkeypatch.setattr(diagrams.shutil, "which",
                        lambda name: f"/usr/bin/{name}" if name == "d2" else None)
    assert diagrams._resolve_diagram_binary("d2") == "/usr/bin/d2"


def test_resolve_binary_extensionless_posix(monkeypatch):
    # Simulate POSIX: candidate names are extensionless; PATH resolves 'mmdr'.
    monkeypatch.setattr(diagrams.os, "name", "posix")
    seen = {}

    def fake_which(name):
        seen.setdefault("names", []).append(name)
        return "/home/u/.cargo/bin/mmdr" if name == "mmdr" else None

    monkeypatch.setattr(diagrams.shutil, "which", fake_which)
    resolved = diagrams._resolve_diagram_binary("mermaid")
    assert resolved == "/home/u/.cargo/bin/mmdr"
    # On POSIX only the extensionless name is probed (no '.exe').
    assert seen["names"] == ["mmdr"]


def test_resolve_binary_windows_probes_exe(monkeypatch):
    # Simulate Windows: PATH misses the plain name but has '<name>.exe'.
    monkeypatch.setattr(diagrams.os, "name", "nt")
    probed = []

    def fake_which(name):
        probed.append(name)
        return r"C:\\tools\\d2.exe" if name == "d2.exe" else None

    monkeypatch.setattr(diagrams.shutil, "which", fake_which)
    resolved = diagrams._resolve_diagram_binary("d2")
    assert resolved == r"C:\\tools\\d2.exe"
    assert probed == ["d2", "d2.exe"]


def test_resolve_binary_fallback_dir(monkeypatch):
    # PATH misses entirely; a fallback-dir candidate exists.
    monkeypatch.setattr(diagrams.os, "name", "posix")
    monkeypatch.setattr(diagrams.shutil, "which", lambda name: None)

    real_exists = Path.exists

    def fake_exists(self):
        if self.name == "d2" and self.parent.name == "bin":
            return True
        return real_exists(self)

    monkeypatch.setattr(diagrams.Path, "exists", fake_exists)
    resolved = diagrams._resolve_diagram_binary("d2")
    assert resolved.endswith("d2")
    assert "go" in resolved and "bin" in resolved


# --- integration tests (skipif CLI absent) ---------------------------------

def _d2_available() -> bool:
    try:
        diagrams._resolve_diagram_binary("d2")
        return True
    except SystemExit:
        return False


def _mmdr_available() -> bool:
    try:
        diagrams._resolve_diagram_binary("mermaid")
        return True
    except SystemExit:
        return False


@pytest.mark.skipif(not _d2_available(), reason="d2 CLI not available")
def test_render_diagram_d2_integration(tmp_path):
    out = diagrams.render_diagram("d2", D2_SRC, tmp_path, "D2 Slide")
    assert out.exists() and out.suffix == ".pdf" and out.stat().st_size > 0


@pytest.mark.skipif(not _mmdr_available(), reason="mmdr CLI not available")
def test_render_diagram_mermaid_integration(tmp_path):
    out = diagrams.render_diagram("mermaid", MERMAID_SRC, tmp_path, "Mermaid Slide")
    assert out.exists() and out.suffix == ".png" and out.stat().st_size > 0


@pytest.mark.skipif(not _d2_available(), reason="d2 CLI not available")
def test_render_diagram_d2_invalid_syntax_raises(tmp_path):
    with pytest.raises(SystemExit) as ei:
        diagrams.render_diagram("d2", "a -> : : broken {{{", tmp_path, "Bad D2")
    assert "d2" in str(ei.value) and "Bad D2" in str(ei.value)


@pytest.mark.skipif(not _mmdr_available(), reason="mmdr CLI not available")
def test_render_diagram_mermaid_invalid_syntax_raises(tmp_path):
    with pytest.raises(SystemExit) as ei:
        diagrams.render_diagram(
            "mermaid", "notadiagram @@@ !!!", tmp_path, "Bad Mermaid"
        )
    assert "mmdr" in str(ei.value) and "Bad Mermaid" in str(ei.value)
