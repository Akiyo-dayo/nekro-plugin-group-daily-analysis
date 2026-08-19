# Akiyo OneBot Chat-Key Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship group-daily-analysis v5.0.6 with backward-compatible parsing for Akiyo NekroAgent multi-instance OneBot chat keys, then push and deploy only Guangzhou NA port 8021.

**Architecture:** Keep parsing local to `chat_key.py` instead of importing Akiyo NekroAgent internals. Recognize the anchored Akiyo format before the existing generic parser, normalize the adapter to `onebot_v11`, and expose the optional instance segment without changing current BotManager/scheduler interfaces. Release metadata and README document the compatibility boundary; production rollout is target-only and reversible.

**Tech Stack:** Python 3.10+, `unittest`, existing NekroAgent plugin structure, Git worktree, PowerShell remote Bash wrapper, Docker Compose.

## Global Constraints

- Keep original format `onebot_v11-group_123456` working unchanged.
- Support Akiyo format `onebot_v11-<instance_key>-group_<group_id>` with instance keys `[a-z0-9_]{1,32}`.
- Do not import `nekro_agent.adapters.onebot_v11.core.channel` from the public plugin.
- Bump all plugin version declarations from `5.0.5` to `5.0.6`.
- Do not redesign multi-account BotManager routing in this patch.
- Deploy only Guangzhou `/root/srv/nekro_agent` container `nekro_agent`; leave NapCat/PostgreSQL/Qdrant untouched.
- Preserve backups and record rollback metadata before production mutation.

---

### Task 1: Add and implement Akiyo chat-key parsing

**Files:**
- Modify: `tests/test_na_shell.py:22-38` — add parser regression coverage.
- Modify: `chat_key.py:6-65` — add the anchored Akiyo parser and `instance_key` field.

**Interfaces:**
- Consumes: `parse_chat_key(chat_key: str) -> ParsedChatKey` and existing legacy fallbacks.
- Produces: `ParsedChatKey(adapter_key: str, kind: str, chat_id: str, instance_key: str = "")` with existing `platform_name`, `is_group`, and `umo` properties unchanged.

- [ ] **Step 1: Add the Akiyo regression tests before implementation.**

Append these methods to `ChatKeyTests` in `tests/test_na_shell.py`:

```python
def test_parse_chat_key_akiyo_onebot_instance_group(self) -> None:
    parsed = parse_chat_key(
        "onebot_v11-qq_1234567890-group_9876543210"
    )
    self.assertTrue(parsed.is_group)
    self.assertEqual(parsed.adapter_key, "onebot_v11")
    self.assertEqual(parsed.instance_key, "qq_1234567890")
    self.assertEqual(parsed.chat_id, "9876543210")
    self.assertEqual(parsed.platform_name, "onebot")
    self.assertEqual(parsed.umo, "onebot:GroupMessage:9876543210")

def test_parse_chat_key_akiyo_onebot_instance_private(self) -> None:
    parsed = parse_chat_key("onebot_v11-qq_1234567890-private_987654321")
    self.assertFalse(parsed.is_group)
    self.assertEqual(parsed.instance_key, "qq_1234567890")
    self.assertEqual(parsed.chat_id, "987654321")
    with self.assertRaises(ValueError):
        extract_group_id("onebot_v11-qq_1234567890-private_987654321")

def test_parse_chat_key_rejects_invalid_akiyo_instance_segment(self) -> None:
    parsed = parse_chat_key("onebot_v11-QQ-1234567890-group_9876543210")
    self.assertEqual(parsed.instance_key, "")
    self.assertEqual(parsed.chat_id, "onebot_v11-QQ-1234567890-group_9876543210")
```

- [ ] **Step 2: Run only the new tests and verify the expected red failure.**

Run from the worktree root:

```powershell
python -m unittest tests.test_na_shell.ChatKeyTests.test_parse_chat_key_akiyo_onebot_instance_group tests.test_na_shell.ChatKeyTests.test_parse_chat_key_akiyo_onebot_instance_private tests.test_na_shell.ChatKeyTests.test_parse_chat_key_rejects_invalid_akiyo_instance_segment -v
```

Expected before implementation: the first two tests fail because the current parser returns the whole key as `chat_id` and has no `instance_key`; the invalid-segment test may pass. A collection/import error is not acceptable red evidence and must be fixed by using the command above rather than pytest.

- [ ] **Step 3: Implement the minimum parser change.**

In `chat_key.py`, add:

```python
_AKIYO_ONEBOT_CHAT_KEY_RE = re.compile(
    r"^onebot_v11-(?P<instance_key>[a-z0-9_]{1,32})-"
    r"(?P<kind>group|private)_(?P<chat_id>.+)$"
)
```

Change the dataclass to:

```python
@dataclass(frozen=True)
class ParsedChatKey:
    adapter_key: str
    kind: str
    chat_id: str
    instance_key: str = ""
```

At the start of `parse_chat_key`, after trimming and before `_CHAT_KEY_RE.match(text)`, add:

```python
    akiyo_match = _AKIYO_ONEBOT_CHAT_KEY_RE.match(text)
    if akiyo_match:
        return ParsedChatKey(
            adapter_key="onebot_v11",
            kind=akiyo_match.group("kind"),
            chat_id=akiyo_match.group("chat_id"),
            instance_key=akiyo_match.group("instance_key"),
        )
```

Keep every existing fallback branch unchanged, relying on the dataclass default `instance_key=""`.

- [ ] **Step 4: Run the targeted tests and then the full reliable suite.**

```powershell
python -m unittest tests.test_na_shell.ChatKeyTests -v
python -m unittest discover -s tests -v
```

Expected: all chat-key tests and the full existing suite pass; the suite count increases from 12 to 15 tests.

- [ ] **Step 5: Review the parser diff and commit the code/tests.**

```powershell
git diff --check
git diff -- chat_key.py tests/test_na_shell.py
git add chat_key.py tests/test_na_shell.py
git commit -m "fix: support Akiyo OneBot instance chat keys"
```

---

### Task 2: Release metadata and documentation

**Files:**
- Modify: `metadata.yaml:4` — set `version: v5.0.6`.
- Modify: `plugin.py:15` — set the runtime plugin declaration to `version="5.0.6"`.
- Modify: `pyproject.toml:3` — set project version to `5.0.6`.
- Modify: `src/shared/constants.py:71` — set `PLUGIN_VERSION = "5.0.6"`.
- Modify: `README.md:5,161-176` — update the release badge and document original/Akiyo OneBot key forms and the current compatibility boundary.
- Create: `CHANGELOG.md` — record the v5.0.6 fix and deployment-facing symptom.

**Interfaces:**
- Consumes: Task 1 parser behavior and the existing README OneBot section.
- Produces: consistent package/plugin metadata and a user-visible changelog entry.

- [ ] **Step 1: Update all version declarations.**

Use exact replacements:

```text
metadata.yaml: version: v5.0.5 -> version: v5.0.6
pyproject.toml: version = "5.0.5" -> version = "5.0.6"
src/shared/constants.py: PLUGIN_VERSION = "5.0.5" -> PLUGIN_VERSION = "5.0.6"
plugin.py: version="5.0.5" -> version="5.0.6"
README.md badge: version-v5.0.5 -> version-v5.0.6
```

- [ ] **Step 2: Add the changelog entry.**

Create `CHANGELOG.md` with:

```markdown
# Changelog

## v5.0.6 - 2026-08-19

### Fixed

- 兼容 Akiyo NekroAgent 的 OneBot 多实例会话 Key，例如 `onebot_v11-qq_1234567890-group_9876543210`。
- 修复群历史接口把完整 `chat_key` 误当群号，导致真实有消息的群被误报为 `no_messages` 的问题。

### Compatibility

- 保留原版 NekroAgent 的 `onebot_v11-group_<group_id>` 格式。
- 本版本只修复会话 Key 解析；同一 NA 多个 OneBot 实例的完整出站路由仍不在本次变更范围内。
```

- [ ] **Step 3: Add the README compatibility note.**

Under the existing OneBot platform note, add a paragraph stating that both `onebot_v11-group_<group_id>` and Akiyo's `onebot_v11-<instance_key>-group_<group_id>` are accepted, and that `instance_key` is parsed for compatibility while this release keeps the existing single BotManager binding behavior.

- [ ] **Step 4: Verify release metadata and docs.**

```powershell
Select-String -Path metadata.yaml,plugin.py,pyproject.toml,src/shared/constants.py,README.md -Pattern '5\.0\.5|5\.0\.6'
Select-String -Path README.md,CHANGELOG.md -Pattern 'onebot_v11-qq_1234567890-group_9876543210|v5\.0\.6|no_messages'
git diff --check
python -m unittest discover -s tests -v
```

Expected: no stale `5.0.5` version declarations, compatibility documentation is present, and the full suite remains green.

- [ ] **Step 5: Commit the release metadata.**

```powershell
git add metadata.yaml plugin.py pyproject.toml src/shared/constants.py README.md CHANGELOG.md docs/superpowers/plans/2026-08-19-akiyo-onebot-chat-key-compat.md
git commit -m "release: group daily analysis v5.0.6"
```

---

### Task 3: Review, push, and target-only Guangzhou deployment

**Files:**
- No additional source changes expected.
- Deployment evidence/backup files stay outside the repository under the operations workspace.

**Interfaces:**
- Consumes: reviewed Task 1 and Task 2 commits.
- Produces: pushed `main` commit, target-only production deployment, and independent acceptance evidence.

- [ ] **Step 1: Run pre-push verification.**

```powershell
git status --short --branch
git log --oneline --decorate -5
python -m unittest discover -s tests -v
git diff origin/main...HEAD --check
git diff --stat origin/main...HEAD
```

Confirm the diff contains only the parser/tests, release metadata, README, changelog, and committed design/plan documents.

- [ ] **Step 2: Push the reviewed branch content to GitHub `main`.**

```powershell
git push origin HEAD:main
git fetch origin main
git rev-parse HEAD
git rev-parse origin/main
```

The two hashes must match.

- [ ] **Step 3: Capture Guangzhou read-only baseline before mutation.**

Use the existing UTF-8-safe wrapper from the operations workspace with a UTF-8 no-BOM Bash script file containing:

```bash
date -Is
cd /root/srv/nekro_agent
docker compose ps
docker inspect -f '{{.Id}} {{.State.StartedAt}} {{.RestartCount}} {{.Config.Image}} {{.State.Health.Status}}' nekro_agent
docker inspect -f '{{.Id}} {{.State.StartedAt}} {{.RestartCount}} {{.Config.Image}}' nekro_napcat nekro_postgres nekro_qdrant
docker exec nekro_agent sh -lc 'sha256sum /app/nekro_agent/plugins/workdir/group_daily_analysis/chat_key.py /app/nekro_agent/plugins/workdir/group_daily_analysis/metadata.yaml 2>/dev/null || true'
docker logs --since 30m nekro_agent 2>&1 | tail -n 300
```

Run the script through:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
python .\_ops_guangzhou_readonly.py <bash-script-path> --timeout 60
```

Save the output in the operations workspace. If the installed path differs, resolve it from Docker/Compose before writing.

- [ ] **Step 4: Back up target files and deploy only `nekro_agent`.**

Create a timestamped backup under `/root/srv/nekro_agent/config_backups/group_daily_analysis-v5.0.5-<timestamp>/` containing the installed plugin directory, Compose file, and baseline inspect output. Stage the exact pushed source into the plugin path, verify `chat_key.py` and version hashes, then run only the target service lifecycle command (for example `docker compose up -d --build --no-deps nekro_agent` if the Compose project is source-built). Do not run a project-wide `up`, `down`, or `restart`.

- [ ] **Step 5: Verify target health and plugin load.**

Run the wrapper with a Bash script containing:

```bash
cd /root/srv/nekro_agent
docker compose ps nekro_agent
curl -fsS http://127.0.0.1:8021/api/health
docker logs --since 5m nekro_agent 2>&1 | grep -E 'group_daily_analysis|群分析插件已在 NekroAgent 中初始化|Traceback|ImportError|ModuleNotFoundError' | tail -n 200 || true
docker exec nekro_agent python -c 'from pathlib import Path; import sys; p=Path("/app/nekro_agent/plugins/workdir/group_daily_analysis"); sys.path.insert(0, str(p)); from chat_key import parse_chat_key; x=parse_chat_key("onebot_v11-qq_1234567890-group_9876543210"); print(x); assert x.adapter_key == "onebot_v11" and x.instance_key == "qq_1234567890" and x.chat_id == "9876543210" and x.umo == "onebot:GroupMessage:9876543210"'
```

- [ ] **Step 6: Perform real history and group-analysis acceptance.**

Use the existing production test path to invoke the target group's `群分析` in its actual chat. Separately verify logs do not contain the old `invalid literal for int() with base 10: 'onebot_v11-qq_1234567890-group_9876543210'` or a false `no_messages` caused by that exception. If analysis is blocked by LLM/T2I/upstream quota, record that as an external dependency result and still retain the successful parser/history acceptance.

- [ ] **Step 7: Confirm non-target invariants and rollback readiness.**

Re-run the exact container inspect command and compare `Id`, `State.StartedAt`, and `RestartCount` for `nekro_napcat`, `nekro_postgres`, and `nekro_qdrant` to the baseline. Confirm the backup path and exact previous image/config are recorded. Only then report deployment completion.

---

## Self-review checklist

- The plan covers every requirement in the approved design: parser, tests, version, changelog, README, push, target-only deployment, acceptance, and rollback.
- No implementation step depends on an undefined function or a new external dependency.
- The local test command avoids the known root-package pytest collection problem while production verification runs inside the actual NA container.
- The plan explicitly separates chat-key/history correctness from external LLM/T2I availability.