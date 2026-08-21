from __future__ import annotations

from chat_key import parse_chat_key
from nekro_agent.api.plugin import SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from plugin import config, plugin
from runtime import get_runtime
from src.application.services.analysis_application_service import DuplicateGroupTaskError
from src.shared.trace_context import TraceContext


def _group_from_ctx(_ctx: AgentCtx):
    chat_key = str(getattr(_ctx, "chat_key", "") or getattr(_ctx, "from_chat_key", "") or "")
    parsed = parse_chat_key(chat_key)
    if not parsed.is_group:
        raise ValueError("群分析工具只能在群聊中使用")
    return parsed, chat_key


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="生成群日常分析报告",
    description="分析当前群近期聊天并发送日常报告。",
)
async def tool_analyze_group(_ctx: AgentCtx, days: int = 1) -> str:
    """分析当前群并发送报告。

    Args:
        days: 回溯天数，默认 1。

    Returns:
        str: 发送结果状态。
    """
    if days <= 0:
        raise ValueError("days 必须大于 0")
    runtime = get_runtime()
    runtime.refresh_na_config()
    parsed, chat_key = _group_from_ctx(_ctx)
    runtime.bind_bots(chat_key)
    if not runtime.config_manager.is_group_allowed(parsed.umo):
        raise ValueError("此群未启用日常分析功能")
    TraceContext.set(TraceContext.generate(prefix="agent", group_name=parsed.chat_id))
    try:
        result = await runtime.analysis_service.execute_daily_analysis(
            group_id=parsed.chat_id,
            platform_id=parsed.adapter_key,
            manual=True,
            days=days,
        )
    except DuplicateGroupTaskError as exc:
        raise RuntimeError("该群已有分析任务正在执行") from exc
    if not result.get("success"):
        raise RuntimeError(result.get("reason") or "analysis_failed")
    return await runtime.send_analysis_report(result, chat_key)


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="生成群漫画",
    description="根据当前群近期话题生成漫画并发送到群里。",
)
async def tool_generate_comic(_ctx: AgentCtx, days: int = 1) -> str:
    """生成当前群漫画。

    Args:
        days: 回溯天数，默认 1。

    Returns:
        str: 任务状态。
    """
    if days <= 0:
        raise ValueError("days 必须大于 0")
    runtime = get_runtime()
    runtime.refresh_na_config()
    parsed, chat_key = _group_from_ctx(_ctx)
    runtime.bind_bots(chat_key)
    if not runtime.config_manager.get_enable_daily_comic():
        raise ValueError("漫画生成功能未启用")
    if not runtime.config_manager.is_comic_group_allowed(parsed.umo):
        raise ValueError("此群未启用漫画生成功能")
    try:
        result = await runtime.analysis_service.execute_comic_topic_analysis(
            group_id=parsed.chat_id,
            platform_id=parsed.adapter_key,
            days=days,
        )
    except DuplicateGroupTaskError as exc:
        raise RuntimeError("该群已有漫画话题提取任务正在执行") from exc
    if not result.get("success"):
        raise RuntimeError(result.get("reason") or "comic_topic_failed")
    status = runtime.try_trigger_comic_generation(
        parsed.chat_id,
        parsed.adapter_key,
        {"topics": result.get("topics", [])},
        require_auto_enabled=False,
    )
    if status != "started":
        raise RuntimeError(status)
    return "started"


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="查询增量分析状态",
    description="查询当前群增量分析滑动窗口的批次摘要。",
)
async def tool_incremental_status(_ctx: AgentCtx) -> str:
    """返回当前群增量分析摘要。

    Returns:
        str: 窗口内批次统计。
    """
    import time as time_mod
    from datetime import datetime

    runtime = get_runtime()
    runtime.refresh_na_config()
    parsed, _chat_key = _group_from_ctx(_ctx)
    if not runtime.config_manager.get_incremental_enabled():
        raise ValueError("增量分析未启用")
    analysis_days = runtime.config_manager.get_analysis_days()
    window_end = time_mod.time()
    window_start = window_end - (analysis_days * 24 * 3600)
    batches = await runtime.incremental_store.query_batches(
        parsed.chat_id, window_start, window_end
    )
    if not batches:
        start_str = datetime.fromtimestamp(window_start).strftime("%m-%d %H:%M")
        end_str = datetime.fromtimestamp(window_end).strftime("%m-%d %H:%M")
        return f"window={start_str}~{end_str}; batches=0"
    state = runtime.incremental_merge_service.merge_batches(
        batches, window_start, window_end
    )
    summary = state.get_summary()
    return (
        f"window={summary['window']}; analyses={summary['total_analyses']}; "
        f"messages={summary['total_messages']}; topics={summary['topics_count']}; "
        f"quotes={summary['quotes_count']}; participants={summary['participants']}; "
        f"peak={summary['peak_hours']}"
    )


@plugin.mount_collect_methods()
async def collect_available_methods(_ctx: AgentCtx):
    if not config.EXPOSE_AGENT_TOOLS:
        return []
    return plugin.sandbox_methods
