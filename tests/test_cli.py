import json
import shutil
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "bin" / "abacus"


class StatuslineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.settings = self.home / ".claude" / "settings.json"
        self.env = dict(os.environ, HOME=str(self.home), ABACUS_HOME=str(self.home / ".abacus"))

    def tearDown(self):
        self.tmp.cleanup()

    def abacus(self, *args):
        return subprocess.run([sys.executable, str(CLI), *args], env=self.env, capture_output=True, text=True)

    def test_enable_disable_roundtrip(self):
        self.assertEqual(self.abacus("statusline", "enable").returncode, 0)
        sl = json.loads(self.settings.read_text())["statusLine"]
        self.assertTrue(sl["command"].endswith("abacus-status --line"))
        self.assertEqual(self.abacus("statusline", "disable").returncode, 0)
        self.assertNotIn("statusLine", json.loads(self.settings.read_text()))

    def test_never_silently_replaces_your_status_line(self):
        self.settings.parent.mkdir(parents=True)
        mine = {"type": "command", "command": "my-prompt"}
        self.settings.write_text(json.dumps({"statusLine": mine, "theme": "dark"}))
        p = self.abacus("statusline", "enable")
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(json.loads(self.settings.read_text())["statusLine"], mine)
        self.assertEqual(self.abacus("statusline", "enable", "--replace").returncode, 0)
        self.assertEqual(self.abacus("statusline", "disable").returncode, 0)
        after = json.loads(self.settings.read_text())
        self.assertEqual(after["statusLine"], mine)   # restored
        self.assertEqual(after["theme"], "dark")       # other settings untouched

    def test_wrap_keeps_yours_and_restores_it_exactly(self):
        self.settings.parent.mkdir(parents=True)
        mine = {"type": "command", "command": "~/bin/costline.py", "padding": 1, "refreshInterval": 5}
        self.settings.write_text(json.dumps({"statusLine": mine}))
        p = self.abacus("statusline", "enable")                          # no flag: explain the choices, change nothing
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("--wrap", p.stderr)
        self.assertEqual(json.loads(self.settings.read_text())["statusLine"], mine)
        self.assertEqual(self.abacus("statusline", "enable", "--wrap").returncode, 0)
        sl = json.loads(self.settings.read_text())["statusLine"]
        self.assertTrue(sl["command"].endswith("abacus-status --line --wrap"))
        self.assertEqual((sl["padding"], sl["refreshInterval"]), (1, 5))  # your other settings kept
        saved = json.loads((self.home / ".abacus" / "state" / "statusline.backup.json").read_text())
        self.assertEqual(saved, mine)                                    # what abacus-status --wrap runs
        self.assertIn("already enabled", self.abacus("statusline", "enable", "--wrap").stdout)
        self.assertEqual(self.abacus("statusline", "disable").returncode, 0)
        self.assertEqual(json.loads(self.settings.read_text())["statusLine"], mine)

    def test_wrap_without_a_status_line_just_enables(self):
        self.assertEqual(self.abacus("statusline", "enable", "--wrap").returncode, 0)
        self.assertTrue(json.loads(self.settings.read_text())["statusLine"]["command"].endswith("--line"))


if __name__ == "__main__":
    unittest.main()


class OnboardingTest(unittest.TestCase):
    """What a brand-new user sees: untrusted folders and a missing PATH are named, with the fix."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.ab = self.home / ".abacus"
        for role in ("orchestrator", "concierge"):
            (self.ab / "agents" / role).mkdir(parents=True)
        self.repo = self.home / "src" / "repo-a"
        self.repo.mkdir(parents=True)
        (self.ab / "agents" / "fleet.json").write_text(json.dumps({"workers": {
            "agent:orchestrator": {"repo": str(self.ab / "agents" / "orchestrator")},
            "coder:repo-a": {"repo": str(self.repo)}}}))
        (self.home / ".claude.json").write_text(json.dumps({"projects": {
            str((self.ab / "agents" / "orchestrator").resolve()): {"hasTrustDialogAccepted": True}}}))
        self.env = dict(os.environ, HOME=str(self.home), ABACUS_HOME=str(self.ab), SHELL="/bin/zsh",
                        PATH="/usr/bin:/bin")

    def tearDown(self):
        self.tmp.cleanup()

    def abacus(self, *args):
        return subprocess.run([sys.executable, str(CLI), *args], env=self.env, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL)

    def test_trust_names_exactly_the_untrusted_folders(self):
        out = self.abacus("trust").stdout
        self.assertIn(str((self.ab / "agents" / "concierge").resolve()), out)
        self.assertIn(str(self.repo.resolve()), out)
        self.assertNotIn(str((self.ab / "agents" / "orchestrator").resolve()) + " && claude", out)

    def test_doctor_reports_trust_and_path_with_fixes(self):
        p = self.abacus("doctor")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("folders trusted in Claude Code     1/3", p.stdout)
        self.assertIn("needs trust:", p.stdout)
        self.assertIn('add: export PATH="$HOME/.abacus/bin:$PATH"', p.stdout)
        self.assertIn("not on your PATH", p.stdout)   # CLIs judged against the user's PATH, not the CLI's own

    def test_doctor_knows_when_the_rc_file_is_set_but_the_shell_is_stale(self):
        (self.home / ".zshrc").write_text('export PATH="$HOME/.abacus/bin:$PATH"\n')
        self.assertIn("(new terminals have it)", self.abacus("doctor").stdout)


class PathDetectionTest(OnboardingTest):
    def test_path_set_in_zprofile_counts(self):
        (self.home / ".zprofile").write_text('export PATH="$HOME/.abacus/bin:$PATH"\n')
        out = self.abacus("doctor").stdout
        self.assertIn(".zprofile (new terminals have it)", out)
        self.assertNotIn("add: export PATH", out)


class FirstMessageTest(unittest.TestCase):
    """Setup output and `abacus demo status` tell the operator to name the beads (a goal without one costs a
    question back from the orchestrator)."""

    @classmethod
    def setUpClass(cls):
        from importlib.machinery import SourceFileLoader
        cls.cli = SourceFileLoader("abacus_cli", str(CLI)).load_module()

    def test_two_repo_names_both_beads_and_the_approved_order(self):
        msg = self.cli.first_message("two-repo", {"repo-a": "repo-a-1", "repo-b": "repo-b-2"})
        self.assertEqual(msg, "Build repo-a-1, then repo-b-2 which depends on it. I approve that order.")

    def test_decision_names_the_bead(self):
        self.assertEqual(self.cli.first_message("decision", {"ledger": "ledger-9"}), "Build ledger-9.")

    def test_first_message_follows_the_scenario_beads(self):
        # setup and `abacus demo status` both print first_message, which reads demos/<scenario>/scenario.json
        self.assertEqual(self.cli.first_message("heartbeat", {"sdk-internal": "s-1", "bwcli-rs": "b-2"}),
                         "Build s-1, then b-2 which depends on it. I approve that order.")


class VersionAndInstallTest(unittest.TestCase):
    """`abacus --version`, and the installer putting `abacus` itself on ~/.abacus/bin."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve()
        self.env = dict(os.environ, HOME=str(self.home), ABACUS_HOME=str(self.home / ".abacus"),
                        ABACUS_NO_PATH_LINK="1")

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, cli, *args):
        return subprocess.run([sys.executable, str(cli), *args], env=self.env, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL)

    def test_version_comes_from_the_version_file(self):
        p = self.run_cli(CLI, "--version")
        self.assertEqual(p.returncode, 0, p.stderr)
        want = (CLI.parents[1] / "VERSION").read_text().strip()
        self.assertEqual(p.stdout.splitlines()[0], f"abacus {want}")
        self.assertRegex(want, r"^\d+\.\d+\.\d+$")
        self.assertIn("abacus-infra         not installed", p.stdout)

    def test_install_links_abacus_and_keeps_the_workspace_on_reinstall(self):
        ws = self.home / "ws"
        ws.mkdir()
        p = self.run_cli(CLI, "install", "--dev", "--skip-prereqs", "--workspace", str(ws))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        link = self.home / ".abacus" / "bin" / "abacus"
        self.assertTrue(link.is_symlink())
        v = self.run_cli(link, "--version")
        self.assertIn("abacus-standards     working tree (dev)", v.stdout)
        p = self.run_cli(link, "install", "--dev", "--skip-prereqs")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        cfg = json.loads((self.home / ".abacus" / "config.json").read_text())
        self.assertEqual(cfg["workspace_root"], str(ws))

    def test_install_takes_several_workspace_roots(self):
        roots = [self.home / "src", self.home / "work"]
        for r in roots:
            r.mkdir()
        args = ["install", "--dev", "--skip-prereqs"] + [x for r in roots for x in ("--workspace", str(r))]
        p = self.run_cli(CLI, *args)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        cfg = json.loads((self.home / ".abacus" / "config.json").read_text())
        self.assertEqual(cfg["workspace_roots"], [str(r) for r in roots])
        self.assertEqual(cfg["workspace_root"], str(roots[0]))        # older readers, and where demos go
        p = self.run_cli(CLI, "install", "--dev", "--skip-prereqs")     # reinstall keeps both
        self.assertEqual(json.loads((self.home / ".abacus" / "config.json").read_text())["workspace_roots"],
                         [str(r) for r in roots])
        p = self.run_cli(CLI, "install", "--dev", "--skip-prereqs", "--workspace", str(self.home / "nope"))
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("does not exist", p.stderr + p.stdout)


class HeartbeatResetPiecesTest(unittest.TestCase):
    """The parts of the heartbeat pilot's setup/reset that don't need real repositories or sessions."""

    @classmethod
    def setUpClass(cls):
        from importlib.machinery import SourceFileLoader
        cls.cli = SourceFileLoader("abacus_cli_hb", str(CLI)).load_module()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def repo(self, gitignore):
        r = self.root / "r"
        r.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=r, check=True)
        (r / ".gitignore").write_text(gitignore)
        (r / ".claude").mkdir()
        (r / ".claude" / "settings.json").write_text("{}")
        (r / ".claude" / "settings.local.json").write_text("{}")
        return r

    def ignored(self, r, path):
        return subprocess.run(["git", "check-ignore", "-q", path], cwd=r).returncode == 0

    def test_first_message_names_both_heartbeat_beads(self):
        self.assertEqual(self.cli.first_message("heartbeat", {"sdk-internal": "sdk-1", "bwcli-rs": "bwcli-2"}),
                         "Build sdk-1, then bwcli-2 which depends on it. I approve that order.")

    def test_heartbeat_criteria_only_read_their_own_repository(self):
        # i3p: a worker can't check a sibling from its worktree; cross-repo conditions live on the WAITS-ON line
        beads = self.cli.scenario_spec("heartbeat")["beads"]
        for b in beads:
            self.assertNotIn("../", b["acceptance"], b["title"])
        self.assertIn("WAITS-ON sdk-internal:{sdk-internal}", beads[1]["description"])

    def test_every_scenario_has_its_files_and_beads(self):
        for scenario, info in self.cli.SCENARIOS.items():
            spec = self.cli.scenario_spec(scenario)
            self.assertTrue(spec["beads"], scenario)
            self.assertEqual({b["repo"] for b in spec["beads"]}, set(info["repos"]), scenario)
            if scenario != "heartbeat":   # heartbeat copies your own checkouts instead of a template
                for repo in info["repos"]:
                    self.assertTrue((self.cli.DEMOS / scenario / repo).is_dir(), (scenario, repo))
        self.assertTrue(os.access(self.cli.DEMOS / "two-repo" / "repo-b" / "scripts" / "sync-textkit.sh", os.X_OK))

    def test_fill_leaves_other_braces_alone(self):
        self.assertEqual(self.cli.fill("FILED AGAINST: {sha} {repo-a} fn x() {}", {"sha": "abc", "repo-a": "a-1"}),
                         "FILED AGAINST: abc a-1 fn x() {}")

    def test_reset_is_offered_for_every_scenario(self):
        p = subprocess.run([sys.executable, str(CLI), "demo", "reset", "--help"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        self.assertIn("heartbeat", p.stdout)
        self.assertIn("--empty-boards", p.stdout)


class ChatTest(unittest.TestCase):
    """abacus chat attaches to the running concierge by id: by name, stale Agent View records make it ambiguous."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.bin = t / "bin"
        self.bin.mkdir()
        sessions = [
            {"id": "old1", "name": "agent:concierge", "pid": None, "startedAt": 1},       # stopped record
            {"id": "orch1", "name": "agent:orchestrator", "pid": 5, "startedAt": 2},     # mentions it in task text
            {"id": "live1", "name": "agent:concierge", "pid": 42, "startedAt": 3},       # the running one
        ]
        (self.bin / "claude").write_text(
            "#!/bin/sh\nif [ \"$1\" = agents ]; then cat <<'J'\n" + json.dumps(sessions) +
            "\nJ\nelse echo \"CLAUDE $*\"; fi\n")
        (self.bin / "claude").chmod(0o755)
        self.env = dict(os.environ, HOME=str(t), ABACUS_HOME=str(t / ".abacus"),
                        PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}")

    def tearDown(self):
        self.tmp.cleanup()

    def test_attaches_to_the_live_concierge_by_id(self):
        p = subprocess.run([sys.executable, str(CLI), "chat"], env=self.env, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), "CLAUDE attach live1")


class ChatSlowStartTest(unittest.TestCase):
    """Claude Code can take most of a minute to register a new background session; abacus chat waits for it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.bin = t / "bin"
        self.bin.mkdir()
        live = json.dumps([{"id": "late1", "name": "agent:concierge", "pid": 42, "startedAt": 3}])
        # Agent View lists the concierge only from the 8th poll on (the first poll is before the start).
        (self.bin / "claude").write_text(
            f"#!/bin/sh\nif [ \"$1\" = agents ]; then echo x >> {t}/polls\n"
            f"  if [ $(wc -l < {t}/polls) -ge 8 ]; then echo '{live}'; else echo '[]'; fi\n"
            "else echo \"CLAUDE $*\"; fi\n")
        (self.bin / "abacus-session").write_text("#!/bin/sh\nexit 0\n")
        for f in ("claude", "abacus-session"):
            (self.bin / f).chmod(0o755)
        self.env = dict(os.environ, HOME=str(t), ABACUS_HOME=str(t / ".abacus"),
                        PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}")

    def tearDown(self):
        self.tmp.cleanup()

    def chat(self, **env):
        return subprocess.run([sys.executable, str(CLI), "chat"], env=dict(self.env, **env),
                              capture_output=True, text=True)

    def test_keeps_waiting_says_so_and_attaches(self):
        p = self.chat()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("waiting for agent:concierge to appear in Agent View", p.stdout)
        self.assertTrue(p.stdout.strip().endswith("CLAUDE attach late1"), p.stdout)

    def test_gives_up_with_a_way_forward(self):
        p = self.chat(ABACUS_CHAT_WAIT="2")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("hasn't appeared in Agent View after 2s", p.stderr)
        self.assertIn("claude agents", p.stderr)


class RenameTest(unittest.TestCase):
    """0.4.0 renamed abacus-orchestrator to abacus-agents: the installer explains a checkout under the old name."""

    def test_old_folder_name_gets_a_rename_hint(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            for name in ("abacus-infra", "abacus-standards", "abacus-orchestrator"):
                (base / name / ".git").mkdir(parents=True)
            from importlib.machinery import SourceFileLoader
            cli = SourceFileLoader("abacus_cli_rn", str(CLI)).load_module()
            with self.assertRaises(SystemExit):
                cli.find_components(base)
            p = subprocess.run([sys.executable, "-c",
                                f"import sys; from importlib.machinery import SourceFileLoader as L; "
                                f"c = L('x', {str(CLI)!r}).load_module(); "
                                f"c.find_components(__import__('pathlib').Path({t!r}))"],
                               capture_output=True, text=True)
            self.assertIn("was renamed abacus-agents in 0.4.0", p.stderr)


class SetupArchivesThePreviousRunTest(unittest.TestCase):
    """8xk: replacing a scenario's sandbox archives the previous run, so the orchestrator never reads stale pages."""

    def setUp(self):
        import argparse
        from importlib.machinery import SourceFileLoader
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name).resolve()
        self.ws, self.home = t / "src" / "ws", t / "home"
        self.ws.mkdir(parents=True); self.home.mkdir()
        old_home = os.environ.get("ABACUS_HOME")
        os.environ["ABACUS_HOME"] = str(self.home)
        try:
            self.cli = SourceFileLoader("abacus_cli_8xk", str(CLI)).load_module()
        finally:
            os.environ.pop("ABACUS_HOME") if old_home is None else os.environ.__setitem__("ABACUS_HOME", old_home)
        self.calls = []
        self.cli.stop_scenario = lambda s, why: self.calls.append(("stop", s))
        self.cli.archive_run_state = lambda s: self.calls.append(("archive", s))
        self.cli.say = lambda m: None
        self.ns = lambda **kw: argparse.Namespace(**dict({"scenario": "heartbeat", "dir": None, "force": False}, **kw))

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, **extra):
        (self.home / "config.json").write_text(json.dumps(dict(
            {"workspace_root": str(self.ws), "workspace_roots": [str(self.ws)]}, **extra)))

    def test_moving_to_the_sandbox_folder_archives(self):
        old = self.ws / "abacus-pilot"; old.mkdir()
        self.config(demo_dirs={"heartbeat": str(old)})
        d = self.cli.setup_dir(self.ns())
        self.assertEqual(d, self.ws.parent / "abacus-sandboxes" / "heartbeat")
        self.assertEqual(self.calls, [("stop", "heartbeat"), ("archive", "heartbeat")])

    def test_force_in_place_archives_but_a_first_setup_does_not(self):
        self.config()
        self.cli.setup_dir(self.ns(force=True))                        # nothing there yet
        self.assertEqual(self.calls, [])
        d = self.ws.parent / "abacus-sandboxes" / "heartbeat"
        (d / "sdk-internal").mkdir(parents=True)
        self.cli.setup_dir(self.ns(force=True))
        self.assertEqual(self.calls, [("stop", "heartbeat"), ("archive", "heartbeat")])

    def test_a_reset_that_already_archived_isnt_archived_twice(self):
        self.config()
        d = self.ws.parent / "abacus-sandboxes" / "heartbeat"
        (d / "x").mkdir(parents=True)
        a = self.ns(force=True); a._archived = True
        self.cli.setup_dir(a)
        self.assertEqual(self.calls, [])


class AddRepositoryTest(unittest.TestCase):
    """0.8.0: `abacus add <path>` brings a repository in with one command."""

    @classmethod
    def setUpClass(cls):
        from importlib.machinery import SourceFileLoader
        cls.cli = SourceFileLoader("abacus_cli_add", str(CLI)).load_module()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name).resolve()
        self.ws = self.t / "ws"
        self.ws.mkdir()
        self.env = dict(os.environ, HOME=str(self.t), ABACUS_HOME=str(self.t / ".abacus"), ABACUS_NO_PATH_LINK="1")

    def tearDown(self):
        self.tmp.cleanup()

    def abacus(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(CLI), *args], env=self.env, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, cwd=cwd)

    def make_repo(self, name="myCodeRepo"):
        r = self.ws / name
        r.mkdir()
        g = lambda *a: subprocess.run(["git", *a], cwd=r, check=True, capture_output=True)
        g("init", "-q", "-b", "main"); g("config", "user.email", "t@example.com"); g("config", "user.name", "t")
        (r / "Makefile").write_text(".PHONY: gate check\ngate:\n\ttrue\ncheck:\n\ttrue\n")
        (r / "README.md").write_text("# my code\n")
        g("add", "-A"); g("commit", "-q", "-m", "init")
        return r

    def test_detects_gates_from_the_repositorys_own_files(self):
        cases = {
            "Makefile": (".PHONY: gate\ngate:\n\ttrue\ncheck:\n\ttrue\n", ("make gate", "make check")),
            "Cargo.toml": ("[package]\nname='x'\n", ("cargo test", "cargo check")),
            "go.mod": ("module x\n", ("go vet ./... && go test ./...", "go vet ./...")),
            "package.json": (json.dumps({"scripts": {"lint": "eslint .", "test": "jest"}}),
                             ("npm run lint && npm test", "npm run lint")),
        }
        for i, (fname, (content, want)) in enumerate(cases.items()):
            d = self.t / f"r{i}"
            d.mkdir()
            (d / fname).write_text(content)
            self.assertEqual(self.cli.detect_gates(d)[:2], want, fname)
        empty = self.t / "empty"; empty.mkdir()
        self.assertEqual(self.cli.detect_gates(empty), (None, None, None))

    def test_add_adopts_registers_and_commits(self):
        p = self.abacus("install", "--dev", "--skip-prereqs", "--workspace", str(self.ws))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        r = self.make_repo()
        p = self.abacus("add", str(r), "--yes")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue((r / ".beads").is_dir())
        cfg = json.loads((r / ".abacus" / "config.json").read_text())
        self.assertEqual((cfg["project"], cfg["gate"], cfg["fast_check"]), ("mycoderepo", "make gate", "make check"))
        for fleet in (self.t / ".abacus" / "fleet.json", self.t / ".abacus" / "agents" / "fleet.json"):
            self.assertIn("coder:mycoderepo", json.loads(fleet.read_text())["workers"], fleet)
        log = subprocess.run(["git", "log", "-1", "--format=%s"], cwd=r, capture_output=True, text=True).stdout
        self.assertEqual(log.strip(), "Adopt Abacus conventions")
        self.assertEqual(subprocess.run(["git", "status", "--porcelain"], cwd=r, capture_output=True,
                                        text=True).stdout.strip(), "")
        self.assertIn("plan <an issue link", p.stdout)
        # one doctor: inside the repository, `abacus doctor` checks it too
        d = self.abacus("doctor", cwd=r)
        self.assertIn("This repository", d.stdout)
        self.assertIn("ADOPTED", d.stdout)

    def test_add_refuses_uncommitted_changes(self):
        self.abacus("install", "--dev", "--skip-prereqs", "--workspace", str(self.ws))
        r = self.make_repo()
        (r / "README.md").write_text("changed\n")
        p = self.abacus("add", str(r), "--yes")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("uncommitted changes", p.stderr)
        self.assertFalse((r / ".abacus").exists())


class PathLinkTest(unittest.TestCase):
    """A program can't change its parent shell's PATH; the installer links `abacus` into a folder already on it."""

    def setUp(self):
        from importlib.machinery import SourceFileLoader
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name).resolve()
        self.bin = t / "onpath"
        self.bin.mkdir()
        saved = {k: os.environ.get(k) for k in ("PATH", "ABACUS_HOME", "ABACUS_NO_PATH_LINK")}
        os.environ.update(PATH=f"{self.bin}{os.pathsep}/usr/bin:/bin", ABACUS_HOME=str(t / ".abacus"))
        os.environ.pop("ABACUS_NO_PATH_LINK", None)
        try:
            self.cli = SourceFileLoader("abacus_cli_link", str(CLI)).load_module()
        finally:
            for k, v in saved.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        (t / ".abacus").mkdir()
        self.cli.PATH_LINK_DIRS = (str(t / "not-on-path"), str(self.bin))

    def tearDown(self):
        self.tmp.cleanup()

    def test_links_into_the_first_writable_folder_on_path(self):
        link = self.cli.link_abacus_on_path()
        self.assertEqual(link, self.bin / "abacus")
        self.assertEqual(os.path.realpath(link), os.path.realpath(self.cli.HOME / "bin" / "abacus"))
        self.assertEqual(self.cli.link_abacus_on_path(), link)          # idempotent

    def test_never_replaces_someone_elses_abacus(self):
        (self.bin / "abacus").write_text("#!/bin/sh\necho other\n")
        self.assertIsNone(self.cli.link_abacus_on_path())
        self.assertIn("other", (self.bin / "abacus").read_text())


class InstallHintTest(unittest.TestCase):
    """Missing-tool advice fits the platform: xcode-select on macOS, the package manager on Linux, WSL on Windows."""

    @classmethod
    def setUpClass(cls):
        from importlib.machinery import SourceFileLoader
        cls.cli = SourceFileLoader("abacus_cli_hint", str(CLI)).load_module()

    def hint(self, tool, platform, have=()):
        return self.cli.install_hint(tool, platform, which=lambda t: f"/usr/bin/{t}" if t in have else None)

    def test_hints_per_platform(self):
        self.assertEqual(self.hint("git", "darwin"), "xcode-select --install")
        self.assertEqual(self.hint("git", "linux", have=("apt-get",)), "sudo apt-get install git")
        self.assertEqual(self.hint("python3", "linux", have=("dnf",)), "sudo dnf install python3")
        self.assertEqual(self.hint("git", "linux"), "install git with your system's package manager")
        self.assertIn("WSL", self.hint("git", "win32"))

    def test_beads_uses_homebrew_only_when_it_exists(self):
        self.assertTrue(self.hint("bd", "darwin", have=("brew",)).startswith("brew install beads"))
        self.assertEqual(self.hint("bd", "linux"), "npm install -g @beads/bd")


class UpdateTest(unittest.TestCase):
    """0.9.0: `abacus update` fetches each clone from its configured source and fast-forwards, then publishes."""

    @classmethod
    def setUpClass(cls):
        from importlib.machinery import SourceFileLoader
        cls.cli = SourceFileLoader("abacus_cli_update", str(CLI)).load_module()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name).resolve()
        (t / "up").mkdir(); (t / "src").mkdir(); (t / "ws").mkdir()
        here = CLI.parents[2]
        self.git = lambda cwd, *a: subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True,
                                                  text=True).stdout.strip()
        for name in ("abacus", "abacus-standards", "abacus-infra", "abacus-agents"):
            self.git(t, "clone", "-q", "--bare", "--branch", "main", str(here / name), str(t / "up" / f"{name}.git"))
            self.git(t / "src", "clone", "-q", str(t / "up" / f"{name}.git"), name)
        # run the code under test: the working tree's CLI and sources.json, inside the throwaway clone (never the
        # real working tree, which `update` would fast-forward)
        for f in ("bin/abacus", "sources.json"):
            shutil.copy2(CLI.parents[1] / f, t / "src" / "abacus" / f)
        self.env = dict(os.environ, HOME=str(t), ABACUS_HOME=str(t / ".abacus"), ABACUS_NO_PATH_LINK="1",
                        ABACUS_NO_RESTART="1")
        p = self.abacus("install", "--dev", "--skip-prereqs", "--workspace", str(t / "ws"))
        assert p.returncode == 0, p.stdout + p.stderr
        cfg_path = t / ".abacus" / "config.json"
        cfg = json.loads(cfg_path.read_text())
        cfg["sources"] = {n: {"url": str(t / "up" / f"{n}.git"), "branch": "main"}
                          for n in ("abacus", "abacus-standards", "abacus-infra", "abacus-agents")}
        cfg_path.write_text(json.dumps(cfg))

    def tearDown(self):
        self.tmp.cleanup()

    def abacus(self, *args):
        cli = self.t / "src" / "abacus" / "bin" / "abacus"
        return subprocess.run([sys.executable, str(cli), *args], env=self.env, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL)

    def publish_upstream_change(self):
        work = self.t / "work"
        self.git(self.t, "clone", "-q", str(self.t / "up" / "abacus.git"), "work")
        self.git(work, "config", "user.email", "t@example.com"); self.git(work, "config", "user.name", "t")
        ch = work / "CHANGELOG.md"
        text = ch.read_text()
        i = text.index("\n## ")
        ch.write_text(text[:i + 1] + "## 9.9.9 (test)\n- a brand new thing\n\n" + text[i + 1:])
        self.git(work, "commit", "-q", "-am", "Release 9.9.9")
        self.git(work, "push", "-q", "origin", "main")
        return self.git(work, "rev-parse", "HEAD")

    def test_check_shows_whats_new_and_changes_nothing(self):
        before = self.git(self.t / "src" / "abacus", "rev-parse", "HEAD")
        self.publish_upstream_change()
        p = self.abacus("update", "--check")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("abacus: 1 new commit(s)", p.stdout)
        self.assertIn("Release 9.9.9", p.stdout)
        self.assertIn("a brand new thing", p.stdout)
        self.assertEqual(self.git(self.t / "src" / "abacus", "rev-parse", "HEAD"), before)

    def test_update_fast_forwards_and_publishes(self):
        new = self.publish_upstream_change()
        p = self.abacus("update")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(self.git(self.t / "src" / "abacus", "rev-parse", "HEAD"), new)
        self.assertIn("updated to abacus", p.stdout)
        self.assertIn("roles deployed", p.stdout)
        p = self.abacus("update")                                           # nothing new now
        self.assertIn("abacus: up to date", p.stdout)

    def test_local_commits_stop_the_update_before_anything_changes(self):
        clone = self.t / "src" / "abacus-infra"
        self.git(clone, "config", "user.email", "t@example.com"); self.git(clone, "config", "user.name", "t")
        (clone / "NOTES.md").write_text("mine\n")
        self.git(clone, "add", "-A"); self.git(clone, "commit", "-q", "-m", "local work")
        before = self.git(self.t / "src" / "abacus", "rev-parse", "HEAD")
        self.publish_upstream_change()
        p = self.abacus("update")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("abacus-infra: has 1 local commit(s)", p.stdout + p.stderr)
        self.assertIn("nothing was changed", p.stderr)
        self.assertEqual(self.git(self.t / "src" / "abacus", "rev-parse", "HEAD"), before)

    def test_sources_and_remote_matching(self):
        self.assertEqual(self.cli.repo_id("git@github.com:dasien/abacus.git"),
                         self.cli.repo_id("https://github.com/dasien/abacus"))
        self.assertNotEqual(self.cli.repo_id("https://github.com/dasien/abacus.git"),
                            self.cli.repo_id("https://github.com/someone-else/abacus.git"))
        shipped = json.loads((CLI.parents[1] / "sources.json").read_text())["repos"]
        self.assertEqual(shipped["abacus-agents"]["url"], "https://github.com/dasien/abacus-agents.git")
        self.assertEqual({v["branch"] for v in shipped.values()}, {"main"})


class FleetMergeTest(unittest.TestCase):
    """0.10.0: an existing fleet gains new settings on its roles (the orchestrator's "lanes") without losing yours."""

    def test_existing_roles_gain_new_settings_and_keep_your_values(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t).resolve()
            env = dict(os.environ, HOME=str(t), ABACUS_HOME=str(t / ".abacus"), ABACUS_NO_PATH_LINK="1")
            (t / ".abacus").mkdir()
            (t / ".abacus" / "fleet.json").write_text(json.dumps({"workers": {
                "agent:orchestrator": {"repo": "~/.abacus/agents/orchestrator", "model": "sonnet"},
                "coder:mine": {"repo": "/x/mine"}}}))
            (t / "ws").mkdir()
            p = subprocess.run([sys.executable, str(CLI), "install", "--dev", "--skip-prereqs", "--workspace",
                                str(t / "ws")], env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            w = json.loads((t / ".abacus" / "fleet.json").read_text())["workers"]
            self.assertTrue(w["agent:orchestrator"]["lanes"])
            self.assertEqual(w["agent:orchestrator"]["model"], "sonnet")        # your value kept
            self.assertIn("coder:mine", w)
            self.assertIn("agent:orchestrator gained", p.stdout)
