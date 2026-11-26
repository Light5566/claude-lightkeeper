# 在 Hermes Agent 和 Codex 上使用 Lightkeeper

[回到 README](../README.zh.md)

## Hermes Agent

仓库根目录同时也是一个 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 插件（`plugin.yaml`、`__init__.py`）。安装、启用，然后用同样的方式建 vault：

```
hermes plugins install Light5566/claude-lightkeeper
hermes plugins enable lightkeeper
cd ~/code/myapp && python3 ~/.hermes/plugins/lightkeeper/bin/vault init
```

注册表文件沿用历史名字 `~/.claude/vaults`，不需要装 Claude Code。你得到的东西分三层：

- **CLI 兼容。** `vault` 在任何 shell 里都能用。`--install-cli` 把它放进 PATH，启动器会找到 Hermes 的安装目录。
- **工作流集成。** 三个 skill 和五个流程都是 Hermes skill：`lightkeeper:knowledge-vault`、`lightkeeper:vault-sync`、`lightkeeper:vault-tidy`、`lightkeeper:init`、`lightkeeper:seed`、`lightkeeper:tidy`、`lightkeeper:trace`、`lightkeeper:release`。首轮引导会列出它们，agent 用 `skill_view` 加载。
- **自动生命周期。** 适配层通过 Hermes 的插件 hook，运行与 Claude Code 完全相同的 hook 脚本。接了哪些、哪里不同：

| 行为 | 在 Hermes 里 |
|---|---|
| 会话引导 | 附在新会话的第一条消息后（`pre_llm_call`）；续接的会话不触发，上下文压缩后也不会再发 |
| 提示词提示 | 附在触发它的那条消息后 |
| 编辑指针 | 在编辑之后，不是之前：作为 `lightkeeper` 字段放在 `write_file` / `patch` 的 JSON 结果里送达（`transform_tool_result`）。agent 由此知道刚改的文件属于哪篇笔记，继续之前先读它的 Gotchas。在任何编辑之前就点名笔记的，是提示词提示和会话引导 |
| Stop 提醒 | 走 Hermes 的 verify 门（`pre_verify`）：在 Hermes 看到文件编辑的那一轮，提醒会作为一条合成的用户消息回来，每个回答最多一次，agent 继续干活；没有文件编辑的轮次不触发 |
| 给你的通知 | 会话结束时（`/new`、退出）再显示一次提醒，不会进入模型 |

需要会话的工作目录是被覆盖的 checkout，并使用本地终端后端。和 Claude Code 一样，什么都不会被拦截。Lightkeeper 不是 memory provider，所以能和 Hermes 自带的记忆以及任何记忆插件并存。要求 Hermes 0.22 或更新：已在 stable 0.22.2 的 `hermes chat -q` 模式用真实模型测试，覆盖 `patch` 和 `write_file`、编辑指针、verify 门提醒、笔记更新和会话结束通知；消息网关、交互式多轮、上下文压缩后的行为、同一 gateway 上的并发会话，以及 host-unified 的 main 构建尚未验证。开发时，`bash check.sh` 用一个假的插件上下文驱动适配层；在装了 Hermes 的机器上跑 `hermes plugins validate .` 和 `hermes plugins doctor . --ci`。

## Codex

Codex 从同一个 marketplace 安装插件，并通过 `codex/` 里的一个小适配层运行 Lightkeeper 的 hook：

```
codex plugin marketplace add Light5566/claude-lightkeeper
codex plugin add lightkeeper@claude-lightkeeper
```

在项目目录里的终端中创建 vault（如果已经用 Claude Code 建过就跳过）。不带参数时，它覆盖你所在的仓库并安装 `vault` 命令，之后的命令直接用 `vault …`。`<version>` 是 Codex 为所装版本建的文件夹：

```
python3 ~/.codex/plugins/cache/claude-lightkeeper/lightkeeper/<version>/bin/vault init
```

| 行为 | 在 Codex 里 |
|---|---|
| 会话引导 | 和 Claude Code 一样，包括压缩上下文后的简短提醒 |
| 提示词匹配 | 和 Claude Code 一样 |
| 文件指引 | `apply_patch` 新增、修改、删除或移动的每个文件都会提示。agent 和补丁的结果一起读到它，所以是在编辑之后马上知道文件归哪篇笔记，和 Hermes 一样。Codex 通过 shell 读文件，所以没有读取时的提示：在任何编辑之前就点名笔记的，是提示词匹配和会话引导 |
| Stop 提醒 | 显示给你，并且每个会话一次作为下一条提示发回给 agent：Codex 的 Stop hook 没有上下文通道，适配层用 `decision: block`，把提醒作为理由 |
| Skill | `knowledge-vault`、`vault-sync` 和 `vault-tidy`。五个斜杠命令是 Claude Code 的；在 Codex 里用 `vault` 命令行 |

安装后第一次启动 Codex TUI 时，它会请你审核插件的 hook：四个都要信任。在那里被关掉的 hook 会一直关着，直到你在 `/hooks` 里重新打开。已在 Codex CLI 0.166.0-alpha.6 的 `codex exec` 模式用真实模型测试，覆盖会话引导、带术语表词条的提示词匹配、`apply_patch` 上的文件指引，以及 Stop 的两条路径：笔记已更新时保持安静；否则提醒发回给 agent，由它更新笔记或说明为什么不需要，下一次 Stop 保持安静。交互式 TUI 会话和上下文压缩后的行为尚未验证。开发时，`bash check.sh` 用假的 payload 驱动适配层。
