from __future__ import annotations

from nekro_agent.api.plugin import ConfigBase, NekroPlugin
from pydantic import Field

plugin = NekroPlugin(
    name="群分析总结插件",
    module_name="group_daily_analysis",
    description=(
        "群日常分析总结插件：话题、称号、金句、活跃度报告与群漫画。"
        "移植自 SXP-Simon/astrbot_plugin_qq_group_daily_analysis。"
    ),
    version="5.0.5",
    author="SXPSimon",
    url="https://github.com/Akiyo-dayo/nekro-plugin-group-daily-analysis",
    support_adapter=["onebot_v11", "discord", "telegram", "qqbot_openclaw"],
    allow_sleep=False,
    sleep_brief="定时群分析与增量统计需要持续运行，因此禁止休眠。",
)


@plugin.mount_config()
class PluginConfig(ConfigBase):
    """群分析插件配置。提示词等高级项可通过 CORE_CONFIG_JSON 覆盖。"""

    EXPOSE_AGENT_TOOLS: bool = Field(
        default=True,
        title="向 Agent 暴露工具",
        description="关闭后，沙盒内不再出现群分析 / 群漫画等 Agent 工具，命令与定时任务仍可用。",
    )
    MODEL_GROUP: str = Field(
        default="default",
        title="分析用模型组",
        description="用于话题、称号、金句等分析的 NA chat 模型组。",
        json_schema_extra={
            "ref_model_groups": True,
            "model_type": "chat",
        },
    )
    T2I_API_URL: str = Field(
        default="",
        title="T2I 渲染服务地址",
        description="HTML 报告出图服务，例如 http://127.0.0.1:8000。图片格式报告需要此项。",
    )
    T2I_API_PATH: str = Field(
        default="/generate",
        title="T2I 接口路径",
        description="T2I 服务的生成接口路径，默认 /generate。",
    )

    GROUP_LIST_MODE: str = Field(
        default="none",
        title="群名单模式",
        description="none=全部群可用，whitelist=仅名单内，blacklist=排除名单。",
    )
    GROUP_LIST: str = Field(
        default="",
        title="群名单",
        description="每行一个群号或 UMO，例如 onebot:GroupMessage:123456。",
    )
    ANALYSIS_DAYS: int = Field(default=1, title="默认分析天数")
    MAX_MESSAGES: int = Field(default=1000, title="最多拉取消息数")
    MIN_MESSAGES_THRESHOLD: int = Field(default=200, title="最少消息数阈值")
    FILTER_BOT_MESSAGES: bool = Field(default=True, title="过滤机器人自己的消息")
    OUTPUT_FORMAT: str = Field(
        default="image",
        title="输出格式",
        description="image / text / html，可用逗号组合，例如 image,html。",
    )
    REPORT_TEMPLATE: str = Field(default="scrapbook", title="报告模板")
    ENABLE_ANALYSIS_REPLY: bool = Field(
        default=False,
        title="用文字提示代替表情回应",
    )
    SHOW_REPORT_CAPTION: bool = Field(default=True, title="发送报告时附带说明")
    DEBUG_MODE: bool = Field(default=False, title="调试模式")

    AUTO_ANALYSIS_TIME: str = Field(
        default="23:00",
        title="定时分析时间",
        description="24 小时制，多个时间用逗号分隔，例如 23:00,08:00。",
    )
    SCHEDULED_GROUP_LIST_MODE: str = Field(
        default="whitelist",
        title="定时分析名单模式",
        description="whitelist / blacklist / none。",
    )
    SCHEDULED_GROUP_LIST: str = Field(
        default="",
        title="定时分析群名单",
        description="留空且为白名单时，不会注册定时任务。",
    )

    INCREMENTAL_GROUP_LIST_MODE: str = Field(
        default="whitelist",
        title="增量分析名单模式",
        description="inherit / whitelist / blacklist。",
    )
    INCREMENTAL_GROUP_LIST: str = Field(default="", title="增量分析群名单")
    INCREMENTAL_MIN_MESSAGES: int = Field(default=300, title="增量触发消息数")
    INCREMENTAL_REPORT_IMMEDIATELY: bool = Field(
        default=False,
        title="增量后立即发报告（调试）",
    )

    ENABLE_DAILY_COMIC: bool = Field(default=False, title="启用群漫画")
    ENABLE_AUTO_DAILY_COMIC: bool = Field(default=True, title="分析完成后自动生成漫画")
    COMIC_GROUP_LIST_MODE: str = Field(
        default="inherit",
        title="漫画群名单模式",
        description="inherit / whitelist / blacklist。",
    )
    COMIC_GROUP_LIST: str = Field(default="", title="漫画群名单")

    HTML_BASE_URL: str = Field(default="", title="HTML 报告外链前缀")
    HTML_ONLY_URL: bool = Field(default=False, title="HTML 仅发送外链")

    CORE_CONFIG_JSON: str = Field(
        default="",
        title="高级嵌套配置 JSON",
        description="按原插件分组结构覆盖配置，例如 {\"prompts\": {...}}。留空则只用上方字段。",
    )


config: PluginConfig = plugin.get_config(PluginConfig)
