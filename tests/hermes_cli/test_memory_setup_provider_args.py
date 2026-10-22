"""`hermes memory setup <provider> --opt ...` reaches the provider's own setup.

Memory providers parse their setup options from argv inside ``post_setup`` (the catalog mem0
plugin documents ``hermes memory setup mem0 --mode oss --oss-llm-key ... --dry-run``). The CLI
parser has to let those options through instead of failing with "unrecognized arguments".
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from hermes_constants import get_hermes_home

REPO = Path(__file__).resolve().parents[2]

_PROBE = '''
import json, sys
from pathlib import Path
from agent.memory_provider import MemoryProvider


class ArgvProbe(MemoryProvider):
    @property
    def name(self):
        return "argvprobe"

    def is_available(self):
        return True

    def initialize(self, session_id, **kwargs):
        pass

    def get_tool_schemas(self):
        return []

    def post_setup(self, hermes_home, config):
        Path(hermes_home, "argvprobe.json").write_text(json.dumps(sys.argv[1:]))


def register(ctx):
    ctx.register_memory_provider(ArgvProbe())
'''


def _run_hermes(home: Path, *argv: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "HERMES_HOME": str(home), "PYTHONPATH": str(REPO)}
    return subprocess.run(
        [sys.executable, "-m", "hermes_cli.main", *argv],
        cwd=REPO, env=env, capture_output=True, text=True, timeout=120, check=False,
    )


def _install_probe(home: Path) -> None:
    plugin = home / "plugins" / "argvprobe"
    plugin.mkdir(parents=True)
    (plugin / "__init__.py").write_text(_PROBE, encoding="utf-8")
    (plugin / "plugin.yaml").write_text("name: argvprobe\ndescription: argv probe\n", encoding="utf-8")


def test_provider_setup_options_reach_post_setup():
    home = get_hermes_home()
    _install_probe(home)

    proc = _run_hermes(home, "memory", "setup", "argvprobe", "--mode", "oss", "--dry-run")

    assert proc.returncode == 0, proc.stderr
    seen = json.loads((home / "argvprobe.json").read_text())
    assert seen[-3:] == ["--mode", "oss", "--dry-run"]


def test_help_after_provider_name_shows_help_instead_of_running_setup():
    home = get_hermes_home()
    _install_probe(home)

    proc = _run_hermes(home, "memory", "setup", "argvprobe", "--help")

    assert proc.returncode == 0, proc.stderr
    assert "usage:" in proc.stdout
    assert not (home / "argvprobe.json").exists()
