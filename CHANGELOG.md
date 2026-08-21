# 更新日志

## 5.1.2（2026-08-21）

漫画出图改成选 NekroAgent 的绘图模型组，不再让人去填 AstrBot 供应商 JSON。

- 面板新增「漫画绘图模型组」和「调用格式」（聊天模式 / 图像生成），对接系统里类型为 draw 的模型组。
- 去掉 WebUI 上的「通用生图 / 大香蕉」后端选项；那是 AstrBot 插件，NA 里没有。
- 原绘图供应商 JSON 表隐藏，需要时仍可写在高级嵌套配置里作为额外候选。
- 「画图提示词模型」标明只生成分镜文案，不是出图接口。
- 已在原版 NekroAgent 2.3.3 上验证：插件能加载，群命令可用，`ExtraField(model_type=draw)` 可构造，配置里会写出 `DRAW_MODEL_GROUP`。

## 5.1.1（2026-08-21）

WebUI 里改过的报告模板会立刻用于下一次分析，报告页脚也改成本仓库地址。

- 分析、漫画、定时任务和设置命令会从当前 NA 配置重新叠加，不再沿用进程启动时的模板快照。
- 报告页脚 GitHub 改为 `Akiyo-dayo/nekro-plugin-group-daily-analysis`；模板设计者署名（如 Template by Liangyu-G）保留。
- 官方 T2I 对带视口/缩放参数的请求返回 5xx 时，会去掉高级参数再出一次图，避免直接落成纯文本。
- 自动分析在未指定平台时优先走 OneBot，避免和 Minecraft 等其它适配器抢默认实例。

## 5.1.0（2026-08-21）

按原版 AstrBot 插件完整恢复 WebUI 配置，而不再只暴露一小截扁平项。

- 配置项从原版 `_conf_schema.json` 生成：报告模板、输出格式、图片格式/质量/镜像、LLM 模型组、AI 分析开关、人设继承、提示词模板等都回到面板，标题旁带原版问号说明。
- 内置选项改为下拉/列表，不再只用纯文本框硬填。
- 分析用模型组走 NA 模型组选择器；人设走 NA 人设选择器。漫画角色方案、绘图供应商等原版嵌套表以 JSON 文本保留。
- LLM 调用补上 HTTP 状态和响应摘要，空内容不再被当成成功；网关拒绝 `response_format` 时会去掉 schema 再试。
- 分析人格接到 NA 人设（可洛喵等），可按原版开关继承会话人设。

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
