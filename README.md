<div align="center">

# 群分析总结插件 · NekroAgent

[![Version](https://img.shields.io/badge/version-v5.1.2-76bad9?style=for-the-badge)](https://github.com/Akiyo-dayo/nekro-plugin-group-daily-analysis)
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
   - **漫画绘图模型组**：选类型为绘图(draw) 的模型组（默认 `default-draw`）；调用格式可选「聊天模式」或「图像生成」
   - 其余（T2I、群名单、定时）可先保持默认；图片报告默认走 AstrBot 官方出图服务
   - 需要 HTML 网页外链时，写在「高级嵌套配置 JSON」，不要单独找外链输入框

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
| 基础设置 | 群名单、输出格式（图片/文本/HTML 可多选）、报告模板、人格标签（MBTI/SBTI/ACGTI）等 |
| 图片渲染策略 | 两轮出图格式/质量/分辨率、内地/海外字体镜像 |
| LLM 设置 | 分析用模型组，以及话题/称号/金句/质量/漫画提示词的专用模型组 |
| 分析功能开关 | 话题、称号、金句、聊天质量锐评，以及是否继承 NA 人设 |
| 提示词模板 | 原版话题/称号/金句/质量/漫画提示词，含用户 ID 引用说明 |
| 定时 / 增量 / HTML / 群文件 | 与原版分组一致 |
| 每日群漫画 | 漫画绘图模型组（NA 的 draw 模型组）和调用格式；分镜文案仍用「画图提示词模型」 |
| T2I 渲染服务地址 | NA 适配项。默认 AstrBot 官方端点，一般不用改 |
| 高级嵌套配置 JSON | 仅作覆盖用；日常请用上方分组选项 |

每项配置的说明会显示在 WebUI 标题旁的问号里，下拉项与原版 `_conf_schema.json` 对齐。命令里改过的名单会写入插件数据目录的 `nested_config.json`；WebUI 保存的字段在重启后优先生效。

### Agent 工具

开启「向 Agent 暴露工具」后，沙盒可调用：

- 生成群日常分析报告
- 生成群漫画
- 查询增量分析状态

失败时会抛异常，而不是返回错误字符串，以便 Agent 自行修正。

## 图片报告与 T2I

图片格式走与原 AstrBot 相同的 HTML 转图片接口。**默认已指向 AstrBot 官方端点**（`https://t2i.soulter.top/text2img`），和原版一样不用先填。留空也会回落到该地址。

出图慢或失败时再改「T2I 渲染服务地址」：

- 国内加速：`https://t2i.vercel.ciallo.de5.net`
- Hugging Face 空间：<https://huggingface.co/spaces/clown145/astrbot-t2i-service>
- API 示例：`https://clown145-astrbot-t2i-service.hf.space`
- 自托管：Docker 后填本机地址，例如 `http://127.0.0.1:8999`；文档见 [AstrBot 自建 T2I](https://docs.astrbot.app/others/self-host-t2i.html)

接口路径默认 `/generate`。若日志出现渲染超时或无效图片，可在「图片渲染策略」里加大超时，或换更近的节点。

### HTML 报告外链（可选）

在「HTML 设置」里填写外链 Base URL；也可以用高级 JSON 覆盖：

```json
{
  "html": {
    "html_base_url": "https://report.example.com",
    "html_only_url": true
  }
}
```

前提是你已经用 Nginx 等把插件数据目录里的 HTML 报告挂到了这个前缀。不发网页外链就留空，群里仍会发图片/文本/HTML 文件本身。

## 各平台注意

**OneBot（NapCat / LLOneBot / SnowLuma 等）**  
走协议 `get_group_msg_history` 拉历史，这是最完整的日报路径。

同时兼容原版 NekroAgent 的 `onebot_v11-group_<group_id>`，以及 Akiyo NekroAgent 的多实例格式 `onebot_v11-<instance_key>-group_<group_id>`。v5.0.6 会解析并保留 `instance_key`，避免把完整 `chat_key` 误当群号；同一 NA 多个 OneBot 实例的完整出站路由不在本次修复范围内，仍沿用现有 BotManager 绑定行为。

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
