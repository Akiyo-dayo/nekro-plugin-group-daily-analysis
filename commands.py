from __future__ import annotations

from typing import Annotated, AsyncIterator

from chat_key import parse_chat_key
from nekro_agent.api.plugin import (
    Arg,
    CmdCtl,
    CommandExecutionContext,
    CommandPermission,
    CommandResponse,
)

try:
    from nekro_agent.api.plugin import CommandOutputSegment, CommandOutputSegmentType
except ImportError:  # 原版 NA 未从 api.plugin 再导出这两项
    from nekro_agent.services.command.schemas import (
        CommandOutputSegment,
        CommandOutputSegmentType,
    )
from plugin import plugin
from runtime import get_runtime
from src.application.services.analysis_application_service import DuplicateGroupTaskError
from src.shared.trace_context import TraceContext
from src.utils.logger import logger


def _live_runtime():
    runtime = get_runtime()
    runtime.refresh_na_config()
    return runtime


def _parse_days(raw: str) -> int | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        value = int(text)
    except ValueError as exc:
        raise ValueError("天数必须是整数") from exc
    if value <= 0:
        raise ValueError("天数必须大于 0")
    return value


def _require_group(context: CommandExecutionContext):
    parsed = parse_chat_key(context.chat_key)
    if not parsed.is_group:
        raise ValueError("请在群聊中使用此命令")
    return parsed


@plugin.mount_command(
    name="群分析",
    description="分析当前群的近期聊天并发送日常报告",
    aliases=["group_analysis"],
    usage="群分析 [天数]",
    permission=CommandPermission.SUPER_USER,
    category="群分析",
    tags=["群分析", "日报", "总结"],
)
async def analyze_group_cmd(
    context: CommandExecutionContext,
    days: Annotated[str, Arg("分析天数，默认使用配置", positional=True)] = "",
) -> AsyncIterator[CommandResponse]:
    runtime = _live_runtime()
    if runtime._terminating:
        yield CmdCtl.failed("插件正在关闭")
        return
    try:
        parsed = _require_group(context)
    except ValueError as exc:
        yield CmdCtl.failed(str(exc))
        return
    runtime.bind_bots(context.chat_key)
    if not runtime.config_manager.is_group_allowed(parsed.umo):
        yield CmdCtl.failed("此群未启用日常分析功能")
        return
    day_count = _parse_days(days)
    yield CmdCtl.message("🔍 正在启动分析引擎，正在拉取最近消息...")
    try:
        TraceContext.set(TraceContext.generate(prefix="manual", group_name=parsed.chat_id))
        result = await runtime.analysis_service.execute_daily_analysis(
            group_id=parsed.chat_id,
            platform_id=parsed.adapter_key,
            manual=True,
            days=day_count,
        )
        if not result.get("success"):
            reason = result.get("reason")
            mapping = {
                "no_messages": "未找到足够的群聊记录",
                "muted": "当前群处于禁言状态，已跳过发送",
                "below_threshold": "消息数量未达到分析阈值",
            }
            yield CmdCtl.failed(mapping.get(str(reason), "分析失败，原因未知"))
            return
        status = await runtime.send_analysis_report(result, context.chat_key)
        yield CmdCtl.success(f"✅ 群分析完成（{status}）")
    except DuplicateGroupTaskError:
        yield CmdCtl.failed("该群的分析任务正在执行中，请稍后再试")
    except Exception as exc:
        logger.error(f"群分析失败: {exc}", exc_info=True)
        yield CmdCtl.failed(f"分析失败: {exc}")


@plugin.mount_command(
    name="群漫画",
    description="根据近期群聊话题生成趣味漫画",
    aliases=["group_comic", "daily_comic"],
    usage="群漫画 [天数]",
    permission=CommandPermission.SUPER_USER,
    category="群分析",
    tags=["群漫画", "漫画"],
)
async def generate_comic_cmd(
    context: CommandExecutionContext,
    days: Annotated[str, Arg("分析天数，默认使用配置", positional=True)] = "",
) -> AsyncIterator[CommandResponse]:
    runtime = _live_runtime()
    try:
        parsed = _require_group(context)
    except ValueError as exc:
        yield CmdCtl.failed(str(exc))
        return
    runtime.bind_bots(context.chat_key)
    if not runtime.config_manager.get_enable_daily_comic():
        yield CmdCtl.failed("漫画生成功能未启用")
        return
    if not runtime.config_manager.is_comic_group_allowed(parsed.umo):
        yield CmdCtl.failed("此群未启用漫画生成功能")
        return
    yield CmdCtl.message("🎨 正在提取群聊话题并生成漫画...")
    try:
        result = await runtime.analysis_service.execute_comic_topic_analysis(
            group_id=parsed.chat_id,
            platform_id=parsed.adapter_key,
            days=_parse_days(days),
        )
        if not result.get("success"):
            reason = result.get("reason")
            mapping = {
                "no_messages": "未找到可用于生成漫画的群聊记录",
                "no_topics": "未提取到可用于生成漫画的话题",
                "muted": "当前群处于禁言状态，已跳过发送",
            }
            yield CmdCtl.failed(mapping.get(str(reason), "漫画话题提取失败"))
            return
        status = runtime.try_trigger_comic_generation(
            parsed.chat_id,
            parsed.adapter_key,
            {"topics": result.get("topics", [])},
            require_auto_enabled=False,
        )
        messages = {
            "started": "✅ 漫画生成任务已启动，完成后会发送到群里",
            "duplicate": "该群已有漫画任务正在执行，请稍后再试",
            "blocked": "此群未启用漫画生成功能",
            "no_topics": "未提取到可用于生成漫画的话题",
        }
        if status == "started":
            yield CmdCtl.success(messages[status])
        else:
            yield CmdCtl.failed(messages.get(status, "漫画生成任务未启动，请查看插件日志"))
    except DuplicateGroupTaskError:
        yield CmdCtl.failed("该群的漫画话题提取任务正在执行，请稍后再试")
    except Exception as exc:
        logger.error("手动漫画生成失败: %s", exc, exc_info=True)
        yield CmdCtl.failed(f"漫画生成失败: {exc}")


@plugin.mount_command(
    name="增量状态",
    description="查看当前群的增量分析滑动窗口状态",
    aliases=["incremental_status"],
    usage="增量状态",
    permission=CommandPermission.SUPER_USER,
    category="群分析",
)
async def incremental_status_cmd(context: CommandExecutionContext) -> CommandResponse:
    runtime = _live_runtime()
    try:
        parsed = _require_group(context)
    except ValueError as exc:
        return CmdCtl.failed(str(exc))
    if not runtime.config_manager.get_incremental_enabled():
        return CmdCtl.failed("增量分析模式未启用，请在插件配置中开启")
    import time as time_mod
    from datetime import datetime

    analysis_days = runtime.config_manager.get_analysis_days()
    window_end = time_mod.time()
    window_start = window_end - (analysis_days * 24 * 3600)
    batches = await runtime.incremental_store.query_batches(
        parsed.chat_id, window_start, window_end
    )
    if not batches:
        start_str = datetime.fromtimestamp(window_start).strftime("%m-%d %H:%M")
        end_str = datetime.fromtimestamp(window_end).strftime("%m-%d %H:%M")
        return CmdCtl.success(f"滑动窗口 ({start_str} ~ {end_str}) 内尚无增量分析数据")
    state = runtime.incremental_merge_service.merge_batches(
        batches, window_start, window_end
    )
    summary = state.get_summary()
    return CmdCtl.success(
        f"📊 增量分析状态 (窗口: {summary['window']})\n"
        f"• 分析次数: {summary['total_analyses']}\n"
        f"• 累计消息: {summary['total_messages']}\n"
        f"• 话题数: {summary['topics_count']}\n"
        f"• 金句数: {summary['quotes_count']}\n"
        f"• 参与者: {summary['participants']}\n"
        f"• 高峰时段: {summary['peak_hours']}"
    )


@plugin.mount_command(
    name="分析设置",
    description="管理当前群的分析开关与状态",
    aliases=["analysis_settings"],
    usage="分析设置 [enable|disable|status|reload|test|filter_bot|incremental_debug]",
    permission=CommandPermission.SUPER_USER,
    category="群分析",
)
async def analysis_settings_cmd(
    context: CommandExecutionContext,
    action: Annotated[str, Arg("操作", positional=True, greedy=True)] = "status",
) -> AsyncIterator[CommandResponse]:
    runtime = _live_runtime()
    try:
        parsed = _require_group(context)
    except ValueError as exc:
        yield CmdCtl.failed(str(exc))
        return
    runtime.bind_bots(context.chat_key)
    action_name = (action or "status").strip().lower() or "status"
    group_id = parsed.chat_id
    target_id = parsed.umo

    if action_name == "enable":
        yield CmdCtl.success(await _handle_enable(runtime, group_id, target_id))
        return
    if action_name == "disable":
        yield CmdCtl.success(await _handle_disable(runtime, group_id, target_id))
        return
    if action_name == "reload":
        runtime.auto_scheduler.schedule_jobs(runtime.context)
        await runtime.refresh_incremental_target_states()
        yield CmdCtl.success("已重新加载配置并重启定时任务")
        return
    if action_name == "test":
        if not runtime.config_manager.is_group_allowed(target_id):
            yield CmdCtl.failed("请先启用当前群的分析功能")
            return
        yield CmdCtl.message("🧪 开始测试自动分析功能...")
        try:
            result = await runtime.auto_scheduler._perform_auto_analysis_for_group(
                group_id, parsed.adapter_key
            )
            if isinstance(result, dict) and result.get("success"):
                yield CmdCtl.success("自动分析及报告发送成功，请查看群消息")
            else:
                reason = (
                    result.get("reason", "unknown")
                    if isinstance(result, dict)
                    else "invalid_result"
                )
                yield CmdCtl.failed(f"自动分析或报告发送失败: {reason}")
        except DuplicateGroupTaskError:
            yield CmdCtl.failed("该群的分析任务正在执行中，请稍后再试")
        except Exception as exc:
            yield CmdCtl.failed(f"自动分析测试失败: {exc}")
        return
    if action_name == "incremental_debug":
        current = runtime.config_manager.get_incremental_report_immediately()
        runtime.config_manager.set_incremental_report_immediately(not current)
        yield CmdCtl.success(
            f"增量分析立即报告模式: {'已启用' if not current else '已禁用'}"
        )
        return
    if action_name == "filter_bot":
        current = runtime.config_manager.get_filter_bot_messages()
        runtime.config_manager.set_filter_bot_messages(not current)
        yield CmdCtl.success(f"过滤机器人消息: {'已启用' if not current else '已禁用'}")
        return

    is_allowed = runtime.config_manager.is_group_allowed(target_id)
    incremental_enabled = runtime.config_manager.get_incremental_enabled()
    incremental_status = "未启用"
    if incremental_enabled:
        incremental_status = (
            f"已启用 (每 {runtime.config_manager.get_incremental_min_messages()} 条消息触发)"
        )
    yield CmdCtl.success(
        "📊 当前群分析功能状态:\n"
        f"• 群分析功能: {'已启用' if is_allowed else '未启用'} "
        f"(模式: {runtime.config_manager.get_group_list_mode()})\n"
        f"• 自动分析: {'已启用' if runtime.config_manager.is_auto_analysis_enabled() else '未启用'} "
        f"({runtime.config_manager.get_auto_analysis_time()})\n"
        f"• 增量分析: {incremental_status}\n"
        f"• 调试模式: {'开启' if runtime.config_manager.get_incremental_report_immediately() else '关闭'}\n"
        f"• 过滤机器人: {'开启' if runtime.config_manager.get_filter_bot_messages() else '关闭'}\n"
        f"• 输出格式: {runtime.config_manager.get_output_format()[0]}\n"
        f"• 最小消息数: {runtime.config_manager.get_min_messages_threshold()}\n\n"
        "可用操作: enable, disable, status, reload, test, filter_bot, incremental_debug"
    )


@plugin.mount_command(
    name="设置格式",
    description="设置分析报告输出格式",
    aliases=["set_format"],
    usage="设置格式 [image|text|html]",
    permission=CommandPermission.SUPER_USER,
    category="群分析",
)
async def set_format_cmd(
    context: CommandExecutionContext,
    format_input: Annotated[str, Arg("格式名称或序号", positional=True, greedy=True)] = "",
) -> CommandResponse:
    runtime = _live_runtime()
    available = ["image", "text", "html"]
    if not format_input.strip():
        current = ", ".join(runtime.config_manager.get_output_format())
        listing = "\n".join(f"【{i}】{name}" for i, name in enumerate(available, start=1))
        return CmdCtl.success(f"当前输出格式: {current}\n可用格式:\n{listing}")
    raw = format_input.strip()
    target = None
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(available):
            target = available[idx]
    if not target:
        lowered = raw.lower()
        if lowered in available:
            target = lowered
    if not target:
        parts = [item.strip() for item in raw.replace("，", ",").split(",")]
        if all(item in available for item in parts) and len(parts) > 1:
            runtime.config_manager.set_output_format(parts)
            return CmdCtl.success(f"输出格式已设置为: {', '.join(parts)}")
        return CmdCtl.failed(f"无效格式 '{raw}'。可用: {', '.join(available)}")
    runtime.config_manager.set_output_format(target)
    return CmdCtl.success(f"输出格式已设置为: {target}")


@plugin.mount_command(
    name="设置模板",
    description="设置分析报告模板",
    aliases=["set_template"],
    usage="设置模板 [模板名称或序号]",
    permission=CommandPermission.SUPER_USER,
    category="群分析",
)
async def set_template_cmd(
    context: CommandExecutionContext,
    template_input: Annotated[str, Arg("模板名称或序号", positional=True, greedy=True)] = "",
) -> CommandResponse:
    runtime = _live_runtime()
    available = await runtime.template_command_service.list_available_templates()
    if not template_input.strip():
        current = runtime.config_manager.get_report_template()
        listing = "\n".join(f"【{i}】{name}" for i, name in enumerate(available, start=1))
        return CmdCtl.success(f"当前报告模板: {current}\n可用模板:\n{listing}")
    template_name, parse_error = runtime.template_command_service.parse_template_input(
        template_input, available
    )
    if parse_error:
        return CmdCtl.failed(parse_error)
    if not template_name or not await runtime.template_command_service.template_exists(
        template_name
    ):
        return CmdCtl.failed(f"模板不存在: {template_input}")
    runtime.config_manager.set_report_template(template_name)
    return CmdCtl.success(f"报告模板已设置为: {template_name}")


@plugin.mount_command(
    name="查看模板",
    description="查看可用报告模板及预览图",
    aliases=["view_templates"],
    usage="查看模板",
    permission=CommandPermission.SUPER_USER,
    category="群分析",
)
async def view_templates_cmd(context: CommandExecutionContext) -> CommandResponse:
    runtime = _live_runtime()
    available = await runtime.template_command_service.list_available_templates()
    if not available:
        return CmdCtl.failed("未找到任何可用的报告模板")
    current = runtime.config_manager.get_report_template()
    segments: list[CommandOutputSegment] = [
        CommandOutputSegment(
            type=CommandOutputSegmentType.TEXT,
            text=f"当前模板: {current}\n可用模板: {', '.join(available)}",
        )
    ]
    for name in available:
        preview = runtime.template_command_service.resolve_template_preview_path(name)
        if preview:
            segments.append(
                CommandOutputSegment(
                    type=CommandOutputSegmentType.IMAGE,
                    file_path=preview,
                )
            )
    return CmdCtl.success(segments)


async def _handle_enable(runtime, group_id: str, target_id: str) -> str:
    mode = runtime.config_manager.get_group_list_mode()
    if mode == "whitelist":
        glist = runtime.config_manager.get_group_list()
        if not runtime.config_manager.is_group_allowed(target_id):
            glist.append(target_id)
            runtime.config_manager.set_group_list(glist)
            runtime.auto_scheduler.schedule_jobs(runtime.context)
            await runtime.refresh_incremental_target_states()
            return f"已将当前群加入白名单\nID: {target_id}"
        return "当前群已在白名单中"
    if mode == "blacklist":
        glist = runtime.config_manager.get_group_list()
        removed = False
        for item in (target_id, group_id):
            if item in glist:
                glist.remove(item)
                removed = True
        if removed:
            runtime.config_manager.set_group_list(glist)
            runtime.auto_scheduler.schedule_jobs(runtime.context)
            await runtime.refresh_incremental_target_states()
            return "已将当前群从黑名单移除"
        return "当前群不在黑名单中"
    return "当前为无限制模式，所有群聊默认启用"


async def _handle_disable(runtime, group_id: str, target_id: str) -> str:
    mode = runtime.config_manager.get_group_list_mode()
    if mode == "whitelist":
        glist = runtime.config_manager.get_group_list()
        removed = False
        for item in (target_id, group_id):
            if item in glist:
                glist.remove(item)
                removed = True
        if removed:
            runtime.config_manager.set_group_list(glist)
            runtime.auto_scheduler.schedule_jobs(runtime.context)
            await runtime.refresh_incremental_target_states()
            return "已将当前群从白名单移除"
        return "当前群不在白名单中"
    if mode == "blacklist":
        glist = runtime.config_manager.get_group_list()
        if runtime.config_manager.is_group_allowed(target_id):
            glist.append(target_id)
            runtime.config_manager.set_group_list(glist)
            runtime.auto_scheduler.schedule_jobs(runtime.context)
            await runtime.refresh_incremental_target_states()
            return f"已将当前群加入黑名单\nID: {target_id}"
        return "当前群已在黑名单中"
    return "当前为无限制模式，如需禁用请切换到黑名单模式"
