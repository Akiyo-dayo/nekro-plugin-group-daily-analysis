<div align="center">

# 群分析总结插件 · NekroAgent

[![Version](https://img.shields.io/badge/version-v5.0.5-76bad9?style=for-the-badge)](https://github.com/Akiyo-dayo/nekro-plugin-group-daily-analysis)
[![NekroAgent](https://img.shields.io/badge/NekroAgent-Plugin-6c5ce7?style=for-the-badge)](https://github.com/KroMiose/nekro-agent)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

基于群聊记录生成日常分析报告（话题、称号、金句、活跃度）和群漫画。

本仓库是 [SXP-Simon/astrbot_plugin_qq_group_daily_analysis](https://github.com/SXP-Simon/astrbot_plugin_qq_group_daily_analysis)（v5.0.5，MIT）到 [NekroAgent](https://github.com/KroMiose/nekro-agent) 的移植：分析内核、报告模板与漫画流水线来自原项目；命令、配置、定时任务和协议对接改为 NA 插件接口。

</div>

## 效果

报告模板与观感对齐原插件。以下预览图来自原仓库，仅作效果说明：

<table align="center" width="100%">
  <tr>
    <td align="center" width="33.3%" valign="top">
      <p><b>Scrapbook（默认）</b></p>
      <img src="https://fastly.jsdelivr.net/gh/SXP-Simon/astrbot_plugin_qq_group_daily_analysis@main/assets/scrapbook-demo.jpg" alt="Scrapbook 示例" height="420">
    </td>
    <td align="center" width="33.3%" valign="top">
      <p><b>HatsuneMiku</b></p>
      <img src="https://fastly.jsdelivr.net/gh/SXP-Simon/astrbot_plugin_qq_group_daily_analysis@main/assets/HatsuneMiku-demo.jpg" alt="HatsuneMiku 示例" height="420">
    </td>
    <td align="center" width="33.3%" valign="top">
      <p><b>ATRI</b></p>
      <img src="https://fastly.jsdelivr.net/gh/SXP-Simon/astrbot_plugin_qq_group_daily_analysis@main/assets/ATRI-demo.jpg" alt="ATRI 示例" height="420">
    </td>
  </tr>
  <tr>
    <td align="center" width="33.3%" valign="top">
      <p><b>Retro Futurism</b></p>
      <img src="https://fastly.jsdelivr.net/gh/SXP-Simon/astrbot_plugin_qq_group_daily_analysis@main/assets/retro_futurism-demo.jpg" alt="Retro Futurism 示例" height="420">
    </td>
    <td align="center" width="33.3%" valign="top">
      <p><b>Hack</b></p>
      <img src="https://fastly.jsdelivr.net/gh/SXP-Simon/astrbot_plugin_qq_group_daily_analysis@main/assets/hack-demo.jpg" alt="Hack 示例" height="420">
    </td>
    <td align="center" width="33.3%" valign="top">
      <p><b>BlueArchive</b></p>
      <img src="https://fastly.jsdelivr.net/gh/SXP-Simon/astrbot_plugin_qq_group_daily_analysis@main/assets/BlueArchive-demo.jpg" alt="BlueArchive 示例" height="420">
    </td>
  </tr>
</table>

<p align="center">
  <img src="https://fastly.jsdelivr.net/gh/SXP-Simon/astrbot_plugin_qq_group_daily_analysis@main/assets/comic-demo.jpg" alt="群漫画示例" width="60%">
  <br>
  <b>群漫画示例（原仓库 Demo）</b>
</p>

完整模板列表：`scrapbook`、`simple`、`spring_festival`、`ATRI`、`HatsuneMiku`、`BlueArchive`、`hack`、`retro_futurism`。

## 功能

- 话题、用户称号、金句、聊天质量锐评
- 活跃度统计与可视化报告（图片 / 文本 / HTML）
- 每日群漫画（可选，分析完成后联动或单独生成）
- 定时日报 + 增量滑动窗口
- 群黑白名单、定时名单、增量名单、漫画名单
- 群指令 + 定时任务 + 可开关的 Agent 沙盒工具
- OneBot / Discord / Telegram / QQ 官方机器人

## 安装

1. 把本仓库放到 NekroAgent 的插件目录，例如：

   ```text
   nekro-agent/plugins/nekro-plugin-group-daily-analysis
   ```

2. 安装依赖（若 NA 环境尚未包含）：

   ```bash
   pip install -r requirements.txt
   ```

3. 重启或重载插件，确认日志出现：`群分析插件已在 NekroAgent 中初始化`。

4. 在插件配置中填写：
   - **分析用模型组**：NA 里已配置的 chat 模型组
   - **T2I 渲染服务地址**：图片报告必需，见下文
   - 按需填写群名单、定时时间、增量阈值、漫画开关

5. 在目标群执行 `分析设置 enable`，再执行 `群分析`。

本插件 `allow_sleep=False`，无人说话时定时分析仍会执行。

## 命令

需要超级用户权限，请在**群聊**中使用。

| 命令 | 说明 |
| --- | --- |
| `群分析 [天数]` | 分析近期群聊并发送报告 |
| `群漫画 [天数]` | 根据话题生成漫画 |
| `增量状态` | 查看增量滑动窗口 |
| `分析设置 [动作]` | 管理当前群：`enable` / `disable` / `status` / `reload` / `test` / `filter_bot` / `incremental_debug` |
| `设置格式 [image\|text\|html]` | 报告输出格式，可用逗号组合 |
| `设置模板 [名称或序号]` | 切换报告模板 |
| `查看模板` | 列出模板（有预览图时一并发送） |

## 配置要点

| 项 | 说明 |
| --- | --- |
| 向 Agent 暴露工具 | 默认开启。关闭后沙盒不再出现分析/漫画工具，命令和定时任务仍可用 |
| 群名单模式 | `none` 全部可用；`whitelist` 仅名单内；`blacklist` 排除名单 |
| 定时分析时间 | 24 小时制，多个时间用逗号分隔，例如 `23:00,08:00` |
| 定时名单 | 白名单且为空时**不会**注册定时任务 |
| 增量名单 | `inherit` 跟随定时名单；白名单为空表示不启用增量 |
| 每日群漫画 | 总开关 + 分析完成后自动联动；可用 `群漫画` 单独生成 |
| T2I 渲染服务地址 | HTML 出图服务，例如 `http://127.0.0.1:8000` |
| 高级嵌套配置 JSON | 按原插件分组结构覆盖提示词等字段 |

命令里改过的名单会写入插件数据目录的 `nested_config.json`，重启后仍保留。

### Agent 工具

开启「向 Agent 暴露工具」后，沙盒可调用：

- 生成群日常分析报告
- 生成群漫画
- 查询增量分析状态

失败时会抛异常，而不是返回错误字符串，以便 Agent 自行修正。

## 图片报告与 T2I

图片格式依赖独立的 HTML 转图片服务（与原 AstrBot 插件同一类 T2I 接口）。未配置 `T2I_API_URL` 时，图片报告无法渲染，会回退到文本。

可参考原项目说明：

- Hugging Face 空间：<https://huggingface.co/spaces/clown145/astrbot-t2i-service>
- API 示例：`https://clown145-astrbot-t2i-service.hf.space`
- 自托管文档：[AstrBot 自建 T2I](https://docs.astrbot.app/others/self-host-t2i.html)

若日志出现渲染超时或无效图片，可在高级 JSON 里加大 `t2i_rendering` 的超时，或换更近的 T2I 节点。

## 各平台注意

**OneBot（NapCat / LLOneBot / SnowLuma 等）**  
走协议 `get_group_msg_history` 拉历史，这是最完整的日报路径。

**QQ 官方机器人**  
官方 API 不能按群回拉历史。插件只会缓存**启用之后**收到的群消息。启用前的聊天无法自动补齐。配置名单时建议使用完整 UMO 或 NA 的 `chat_key`。

**Discord**  
需要 Message Content Intent，以及频道「查看消息历史」权限。

**Telegram**  
若 Bot 不是管理员，拉进群前先在 BotFather 关闭 Group Privacy；已经在群里则需移出再拉入后设置才生效。

## 致谢

- 原插件：[astrbot_plugin_qq_group_daily_analysis](https://github.com/SXP-Simon/astrbot_plugin_qq_group_daily_analysis) · SXP-Simon
- 运行框架：[NekroAgent](https://github.com/KroMiose/nekro-agent) · KroMiose
- NA 移植仓库：本仓库

保留原项目 MIT 许可证。预览图版权与效果归原作者；本仓库仅做框架移植，未宣称拥有原视觉设计。

## 许可证

MIT。见 [LICENSE](LICENSE)。
