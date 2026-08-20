# 更新日志

## 5.0.6（2026-08-21）

同时兼容原版 NekroAgent（KroMiose 官方镜像）和 akiyo 版 NekroAgent。

- 兼容 Akiyo 的 OneBot 多实例会话 Key，例如 `onebot_v11-qq_1234567890-group_9876543210`；原版仍用 `onebot_v11-group_<群号>`。
- 修复把完整 `chat_key` 误当群号、有消息却报 `no_messages` 的问题。
- 命令输出类型 `CommandOutputSegment` 先从公开 `api.plugin` 导入，原版未再导出时回退到 `services.command.schemas`。
- 加载时把插件目录加入 `sys.path`，避免工作区模块找不到 `cron` / `plugin` 等同级文件。
- 原版镜像缺少的运行时依赖（httpx、aiohttp、diskcache、ulid-py、markupsafe、Pillow、Jinja2）改为按需装进插件动态包目录；PyPI 源使用阿里云镜像。
- 去掉对 APScheduler 的依赖，改用插件内的每日定时调度，官方镜像也能跑自动分析。
- 自带 `astrbot` 适配层，官方镜像无需预装 AstrBot。
- OneBot 绑定改为扫描已连接的 QQ 协议端，排除 Minecraft 等其它适配器；调用协议 API 时走 `call_api`，避免 nonebot 的 `__getattr__` 把 `call_action` 伪装成三参数调用。

## 5.0.5（2026-08-20）

默认改用 AstrBot 官方 T2I 出图，高级 JSON 仍保留 HTML 报告链接。

## 5.0.0（2026-08-20）

NekroAgent 移植版首次发布：话题、称号、金句、活跃度报告与群漫画。
