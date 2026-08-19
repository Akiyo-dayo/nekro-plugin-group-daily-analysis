# Changelog

## v5.0.6 - 2026-08-19

### Fixed

- 兼容 Akiyo NekroAgent 的 OneBot 多实例会话 Key，例如 `onebot_v11-qq_1234567890-group_9876543210`。
- 修复群历史接口把完整 `chat_key` 误当群号，导致真实有消息的群被误报为 `no_messages` 的问题。

### Compatibility

- 保留原版 NekroAgent 的 `onebot_v11-group_<group_id>` 格式。
- 本版本只修复会话 Key 解析；同一 NA 多个 OneBot 实例的完整出站路由仍不在本次变更范围内。
