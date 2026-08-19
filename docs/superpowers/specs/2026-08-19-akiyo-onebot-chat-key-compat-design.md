# Akiyo OneBot Multi-Instance Chat-Key Compatibility Design

## Context

`nekro-plugin-group-daily-analysis` currently parses the original NekroAgent OneBot key `onebot_v11-group_<group_id>`. Akiyo NekroAgent adds a stable OneBot instance segment and emits `onebot_v11-<instance_key>-group_<group_id>`. The current fallback treats the full Akiyo key as the group ID, so OneBot history retrieval attempts `int("onebot_v11-...-group_...")`; the exception is converted to an empty message list and the command reports `no_messages` even when the group has history.

## Goal

Release v5.0.6 with a self-contained parser that preserves original NekroAgent behavior and correctly extracts the adapter, optional instance, chat kind, group ID, platform name, and UMO from Akiyo NekroAgent OneBot chat keys.

## Scope

Included:

- Parse original OneBot keys: `onebot_v11-group_123456` and `onebot_v11-private_123456`.
- Parse Akiyo multi-instance OneBot keys such as `onebot_v11-qq_1234567890-group_9876543210`.
- Keep `adapter_key` normalized to `onebot_v11`, so existing `BotManager` lookups continue to work.
- Expose the parsed optional `instance_key` for future routing work without changing current command or scheduler interfaces.
- Preserve QQ Official, Discord, Telegram, `group_...`, `private_...`, and raw-ID fallback behavior.
- Add regression tests, version updates, changelog, README compatibility documentation, and production deployment acceptance.

Excluded:

- Redesigning `BotManager` for multiple simultaneous OneBot connections.
- Changing Akiyo NekroAgent core code.
- Changing scheduling, report generation, group-list semantics, or non-OneBot adapters.
- Restarting or replacing NapCat, PostgreSQL, or Qdrant during deployment.

## Parser Design

`ParsedChatKey` gains `instance_key: str = ""` as a backward-compatible trailing field.

Parsing order:

1. Trim the input.
2. Match Akiyo OneBot keys with a dedicated anchored expression:
   `onebot_v11-<instance_key>-(group|private)_<chat_id>`.
3. Accept only Akiyo's documented instance-key character set `[a-z0-9_]{1,32}`.
4. Return `adapter_key="onebot_v11"`, the extracted `instance_key`, kind, and chat ID.
5. Otherwise run the existing generic original-format parser and legacy fallbacks unchanged.

The plugin deliberately does not import `nekro_agent.adapters.onebot_v11.core.channel`. Keeping the parser local avoids coupling the public plugin to Akiyo-only internal modules while mirroring the documented wire format.

## Compatibility and Failure Behavior

For `onebot_v11-qq_1234567890-group_9876543210`, the result must be:

- `adapter_key = "onebot_v11"`
- `instance_key = "qq_1234567890"`
- `kind = "group"`
- `chat_id = "9876543210"`
- `platform_name = "onebot"`
- `umo = "onebot:GroupMessage:9876543210"`

Original-format results must remain byte-for-byte equivalent for all existing exposed properties. Invalid or unknown keys retain the existing best-effort fallback rather than introducing a new hard failure in v5.0.6.

## Tests

The regression suite will cover:

- Original OneBot group key remains supported.
- Akiyo OneBot group key parses all fields correctly.
- Akiyo OneBot private key remains non-group and is rejected by `extract_group_id`.
- Invalid Akiyo instance segments do not get accepted as structured multi-instance keys.
- QQ Official behavior remains unchanged.

TDD evidence must show the new Akiyo test failing before implementation and passing afterward. The local reliable suite is `python -m unittest discover -s tests -v`; plain pytest currently collects the plugin root package and fails without a locally installed `nekro_agent`, so final verification will also run inside the real NekroAgent environment.

## Release

- Bump `metadata.yaml`, `pyproject.toml`, and `src/shared/constants.py` from `5.0.5` to `5.0.6`.
- Add `CHANGELOG.md` with a v5.0.6 entry describing the corrected false `no_messages` symptom.
- Add a README compatibility note for both original and Akiyo OneBot key formats.
- Commit on `codex/akiyo-chat-key-compat-20260819`, review the diff, then integrate and push `main` to `Akiyo-dayo/nekro-plugin-group-daily-analysis`.

## Production Deployment and Rollback

Target only Guangzhou host port 8021 (`/root/srv/nekro_agent`, container `nekro_agent`). Before changing anything:

- Record target image/container ID, start time, restart count, health, plugin commit/hash, and recent relevant logs.
- Record the same invariants for `nekro_napcat`, `nekro_postgres`, and `nekro_qdrant`.
- Back up the installed plugin, Compose file, and target deployment metadata.

Deploy the exact reviewed Git commit, rebuild or recreate only `nekro_agent`, and retain the backup for atomic rollback.

Acceptance requires:

- Container health and `/api/health` success.
- Plugin initialization without import or initialization errors.
- Installed source hash/commit matching the pushed repository commit.
- Parsing the production key (kept outside the public repository) `onebot_v11-qq_1234567890-group_9876543210` into group `9876543210`.
- A real OneBot `get_group_msg_history` request no longer raising the previous integer-conversion error.
- A real group-analysis command completing and sending its report when upstream model/T2I dependencies are available; external dependency failures must be reported separately from chat-key compatibility.
- Non-target container IDs, start times, and restart counts unchanged.

Rollback restores the backed-up plugin and recreates only `nekro_agent` using the recorded previous image/configuration.