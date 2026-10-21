# Lightkeeper

**一张代码库的知识地图：Claude 改代码前先读它，结束前必须更新它。**

[English](README.md) · [中文](README.zh.md) · [在线画廊](https://light5566.github.io/claude-lightkeeper/)（Excalidraw、Mastodon、Gitea、Paperless-ngx 和 BookStack 的交互式代码地图）· [更新日志](CHANGELOG.md)

![Claude Code 与 Obsidian 并排：改代码前先查地图，改完后更新拥有该文件的笔记](https://light5566.github.io/claude-lightkeeper/assets/demo-v3.gif)

Lightkeeper 是一个 Claude Code 插件，也能作为 Hermes Agent 插件运行。它把"系统是怎么运作的"（模块、流程、集成、平台陷阱、决策、版本）维护成一份 Obsidian 兼容的 Markdown 地图，放在代码仓库**之外**，并通过 agent 的 hook 让这张地图始终保持真实：

- **会话引导**：告诉 agent 地图在哪、怎么查；
- **提示词匹配**：你刚问的问题涉及哪些笔记，立刻列出来；
- **编辑前指引**：改某个文件之前，先指向拥有这个文件的笔记；
- **Stop 提醒**：代码改了但地图没动时，点名这次改动属于哪些笔记；
- **维护信号**：哪些笔记太长了、代码变了笔记却没变、引用的文件已经不存在。

这是 [LLM-wiki 模式](https://www.noze.it/en/insights/llm-wiki/)在代码库上的应用，再用 hook 强制执行。三个生产系统、十个月的日常使用：464 篇笔记，4500 条带理由的连接。

[![画廊中 BookStack 的交互式地图](https://light5566.github.io/claude-lightkeeper/assets/map.png)](https://light5566.github.io/claude-lightkeeper/maps/bookstack.html)

```
$ vault find payment timeout
Payment  (module/shipped/full, updated 2026-10-02)
  Takes the money for an order.
  → 2 Modules/Payment.md
  connects:
    → Order — a paid order moves to fulfilment
    ← Refund — a refund reverses the gateway charge through Payment::reverse()
```

接着 agent 去改 `app/Services/PaymentService.php` 时，编辑前 hook 会说：

> `app/Services/PaymentService.php` is documented by vault note "Payment" (updated 2026-10-02) — read its Gotchas before going further.
> If this change alters behavior, updating the note afterwards is part of the definition of done.

当它想在没碰地图的情况下结束会话时：

> Knowledge vault not updated. 3 file(s) under app, routes changed in the last 6h, but no note in the vault moved. Affected notes: Payment, Order. Update the note(s): amend 'How it works' / 'Gotchas', bump 'updated:'.

## 和别的工具有什么不同

| | 记的是什么 | 怎么保持最新 |
|---|---|---|
| **claude-mem** 等记忆工具 | 过去的会话里发生了什么 | 自动抓取对话记录 |
| **Understand-Anything** 等代码图谱工具 | 每一个文件、函数、类 | 从 AST 重新生成 |
| **Lightkeeper** | 系统怎么运作、*为什么*这样：每条连接都带理由的精选笔记、AST 里不存在的 Gotchas、决策和客户裁定 | hook 让 agent 改之前读、结束前更新；信号告诉你哪篇笔记在说谎 |

记忆工具和它**一起用**，回答的是不同的问题。

## 为什么地图放在仓库之外

1. **Worktree。** 一个活跃的仓库同时有很多份 checkout。放在仓库里的地图会在每一份里各存一份，编辑器只能打开一份，过期的副本看起来和最新的一模一样。
2. **分支。** 在分支上写的笔记要等合并后才可见，地图会落后于工作整整一个分支的寿命。
3. **多仓库。** 后端加 Web 应用是一个系统。放在其中一个仓库里，另一个就成了二等公民。

代价是：地图的更新是另一个仓库里的另一次提交，git 无法把两者绑在一起。这正是 hook 和 `vault check` 这套仪式存在的原因。

## 从零安装

**需要：** [Claude Code](https://code.claude.com)、git、PATH 里有 Python 3.9 或更新版本（macOS 和大多数 Linux 自带）。Obsidian 可选但推荐：[obsidian.md/download](https://obsidian.md/download) 或 `brew install --cask obsidian`。

1. **在 Claude Code 里安装插件：**

   ```
   /plugin marketplace add Light5566/claude-lightkeeper
   /plugin install lightkeeper@claude-lightkeeper
   ```

   或在 shell 里：`claude plugin marketplace add Light5566/claude-lightkeeper && claude plugin install lightkeeper@claude-lightkeeper`。

2. **为一个或多个 checkout 创建 vault。** 在任意 Claude Code 会话中运行：

   ```
   /lightkeeper:init ~/vaults/myapp --name "My App" --repo ~/code/myapp --install-cli --git-hook
   ```

   这会生成脚手架（目录、约定、模板、Obsidian 配置、Bases 视图），写入描述它覆盖哪些仓库的 `_meta/vault.json`，把它登记到 `~/.claude/vaults`，把 `vault` 命令装到 `~/.local/bin`，并给 checkout 加上只报告、不拦截的 `post-merge` 和 `pre-push` 钩子。

3. **从代码生成第一批笔记：**

   ```
   /lightkeeper:seed
   ```

   Claude 提出领域划分和最多 60 个带真实文件路径的模块存根，征求你同意后写入。从这一刻起，第一次编辑就会触发编辑前指引。

4. **在 Obsidian 里打开：** *Open folder as vault* → 选 `~/vaults/myapp`。图谱配色、Properties 面板和 Bases 视图都已配好。

5. **在 checkout 里重启 Claude Code。** 会话引导出现，就完成了。

项目已经有 vault？一步克隆并登记：

```
/lightkeeper:init --clone git@github.com:your-team/myapp-vault.git --repo ~/code/myapp --install-cli --git-hook
```

已经有一个 Obsidian vault 想逐步迁入？`vault init --adopt ~/my-vault --name "My App" --repo ~/code/myapp` 只写配置并登记，不碰你的笔记；只有带 `type:` 的笔记才会被检查，可以慢慢来。

## Hook 一览

全部只是建议。没有一个能拦截编辑；在没有 vault 覆盖的仓库里、在没有 vault 的机器上，它们全都静默。

![编辑前提示与 Stop 提醒在 Claude Code 会话中触发](https://light5566.github.io/claude-lightkeeper/assets/hooks.png)

| 事件 | 说什么 | 什么时候不说话 |
|---|---|---|
| SessionStart | vault 在哪、怎么查、更新它是完成的一部分；每天一次报告需要关注的笔记数 | resume 时 |
| SessionStart（压缩上下文后） | 重新查 vault，别再把读过的代码读一遍 | |
| UserPromptSubmit | 最多三篇名字、别名或 flag 出现在你提示词里的笔记，附一句话简介和相邻笔记；每个会话一次，当提示词听起来像一个决定或裁定时提醒记录到 Decisions | 没有新匹配 |
| PreToolUse（Write/Edit） | 即将修改的文件归哪篇笔记管，以及它的邻居；存根笔记会说"还没记录任何内容，把你学到的写上去" | 文件无人认领，或本会话已经指过这篇笔记 |
| Stop | 过去 6 小时里被监视的文件变了但没有笔记变动；点名拥有者笔记，并统计没有笔记认领的文件 | vault 工作区有未提交改动，或在时间窗内已提交 |

## 怎么写笔记

每篇笔记都是普通 Markdown，frontmatter 一行一个键值。引擎从你的写法里读三样东西：

- **唯一的规则：每个 `[[链接]]` 都带一个理由。** `- [[Invoice]] — a paid order raises an invoice through InvoiceService::create()`。理由会变成每条搜索结果旁边的"影响范围"；没有理由的链接只会把图谱变成一团毛线。
- **模块笔记里的 *Where it lives* 表格是机器读的**：真实文件，每格第一个路径写完整，绝不写容器目录。编辑前 hook 就跑在这张文件→笔记的索引上。
- **诚实字段。** `status: shipped` 表示代码在生产分支上；`depth: stub` 表示笔记还很薄；每次碰笔记都要更新 `updated:`。笔记可以是错的；代码和笔记不一致时，以代码为准，修正笔记是这次改动的一部分。

脚手架里的 `_meta/Conventions.md` 和 `_meta/How to update.md` 有完整约定、触发表（什么样的改动该碰哪篇笔记）和"60 秒版本"。`knowledge-vault` skill 把这些教给 Claude。

## 命令行

```
vault find <terms>              主题搜索，分层：名字 → 别名/flag → 标签 → 全文
vault find --paths <files>      这些文件归哪些笔记管
vault check [--write]           检查；--write 还会重建索引并重新生成
                                Coverage.md、Vault Changelog.md、Attention.md 和 World.canvas
vault status                    覆盖率、过期笔记、需要关注的项、同步落后情况，一屏看完
vault sync [target] [--advance] 自上次对账以来仓库里落地了什么
vault log <note>                这篇笔记的 git 历史
vault export --html <file>      一个自包含的交互式地图
vault init ...                  创建、克隆或接管一个 vault
```

每个命令都接受 `--vault <path>`；不给的话，用覆盖当前目录的那个 vault。

`vault check` 会抓出解析不了的链接、重名笔记、没有理由的链接、容器目录声明、不合规的 frontmatter、孤儿笔记、过期笔记，以及任何像密钥或个人数据的东西（邮箱、长数字串、API key 形状、私钥）。每次提交 vault 前都带 `--write` 跑一次。

## 配置

vault 里的 `_meta/vault.json`：

```json
{
  "name": "My App",
  "repos": {
    "myapp":     {"remote": "github.com/acme/myapp", "watched": ["app", "routes", "database/migrations"],
                  "production_ref": "origin/main", "version_log": "CHANGELOG.md"},
    "myapp-web": {"remote": "github.com/acme/myapp-web", "watched": ["app", "components", "src"],
                  "production_ref": "origin/main"},
    "local-only": {"path": "~/code/experiment", "watched": ["src"]},
    "ops":        {"remote": "github.com/acme/monorepo", "root": "apps/ops", "watched": ["src"]}
  },
  "generic_dirs": ["app/Services"],
  "noise_files": ["TODO.md"],
  "stop_window_hours": 6,
  "tidy": {"max_words": 4000, "max_gotchas": 20, "stale_days": 60, "churn_commits": 5}
}
```

- `repos` 是 hook 的路由依据：一个 checkout 按 `remote` 子串（任意 URL 形式）或 `path` 匹配；`root` 用来圈定 monorepo 里的子应用。最长匹配胜出。键名就是 frontmatter 里 `repo:` 的取值。
- `watched` 是 Stop 提醒监视的目录。`vault init` 会按项目布局自动检测。
- `generic_dirs` 在内置的容器目录列表之外追加：这些目录不允许被某篇笔记整个认领。
- `tidy` 是维护信号的阈值。
- `_meta/local.md` 若存在，就是这个 vault 自己的规则（分支名、changelog 格式、数据隐私写法）。每个 skill 都会读它。

环境变量覆盖：`VAULT_ROOT`（指定 vault）、`VAULT_WATCHED`、`VAULT_WINDOW_HOURS`、`VAULT_STOP_NUDGE=quiet`（Stop 提醒只给你看，不进 agent 的上下文）。

## 团队协作

vault 是独立的 git 仓库，像共享代码一样共享它：

- 每个人安装插件并运行 `/lightkeeper:init --clone <url> --repo <checkout>`，所有人的 hook 都指向同一张地图。
- 同事推送的代码没有 hook 跟着，地图会漂移。`vault sync` 报告自上次对账以来每个仓库落地了什么，按拥有这些文件的笔记分组；`vault-sync` skill 负责补齐。只有笔记更新之后才推进游标。
- `vault init --git-hook` 装的 `post-merge` 和 `pre-push` 钩子会打印 vault 落后分支多少。它们从不拦截，不用 Claude 的同事也能看到。
- `vault init --backup-remote <url>` 让每次 vault 提交自动推送，单机 vault 永远只落后备份一次提交。
- **PR 评论机器人。** 在代码仓库的 workflow 里加一行 `uses: Light5566/claude-lightkeeper/action@main`，每个 pull request 都会收到一条评论：改动的文件归哪些笔记管，以及哪些文件没有笔记认领。只提醒，不拦截。配置见 [action/README.md](action/README.md)。

## 让地图保持诚实

`vault check --write` 把维护信号写进 `_meta/Attention.md`：

| 信号 | 规则 |
|---|---|
| consolidate | 超过 `max_words` 词或 `max_gotchas` 条 Gotcha |
| re-verify | `updated` 比 `stale_days` 还旧，**并且**此后至少 `churn_commits` 次提交碰过这篇笔记的文件 |
| promote | 文件一直在变的存根笔记 |
| path rot | *Where it lives* 里的路径在任何 worktree 和已提交的树里都不存在 |
| link rot | 链接理由里提到的 `Class::method` 在代码里找不到 |

会话引导每天提一次数量。`/lightkeeper:tidy` 负责处理：重组并去重 Gotchas 而不丢掉任何一个陷阱，先重读过期笔记背后的 diff 再确认或修正，从代码把存根写完整。

`_meta/Vault Changelog.md` 每次 `--write` 都从 vault 自己的 git 历史生成，所以"地图什么时候学到了什么"永远不用手动维护。`World.canvas` 同样会重新生成：每个领域一个分组，模块在里面，跨领域的连接带着理由。

## 兼容性

| | |
|---|---|
| Claude Code（CLI、桌面端、IDE 扩展） | hook、skill、命令和 CLI |
| Hermes Agent | hook、skill、流程和 CLI，通过仓库根目录的适配层；见下文 |
| 其他 agent（Cursor、Codex、Gemini CLI 等） | `vault` CLI 和 SKILL.md 文件 |
| macOS、Linux | 已测试 |
| Windows | 未测试；hook 直接调用 Python，WSL 或 Git Bash 应该可以 |
| Obsidian | 可选：图谱配色、Bases 视图和 canvas 是附加项；笔记本身是带 wikilink 的普通 Markdown，Foam、Logseq 或任何编辑器都能读 |
| Python | 3.9 或更新，只用标准库，不需要 pip 安装任何东西 |
| 语言和框架 | 任意；`vault init` 识别项目布局，其余交给 `vault.json` |

### Hermes Agent

仓库根目录同时也是一个 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 插件（`plugin.yaml`、`__init__.py`）。安装、启用，然后用同样的方式建 vault：

```
hermes plugins install Light5566/claude-lightkeeper
hermes plugins enable lightkeeper
python3 ~/.hermes/plugins/lightkeeper/bin/vault init ~/vaults/myapp --name "My App" --repo ~/code/myapp --install-cli --git-hook
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

需要会话的工作目录是被覆盖的 checkout，并使用本地终端后端。和 Claude Code 一样，什么都不会被拦截。Lightkeeper 不是 memory provider，所以能和 Hermes 自带的记忆以及任何记忆插件并存。要求 Hermes 0.22 或更新：已在 stable 0.22.2 的 `hermes chat -q` 模式用真实模型测试；消息网关、交互式多轮、上下文压缩后的行为，以及 host-unified 的 main 构建尚未验证。开发时，`bash check.sh` 用一个假的插件上下文驱动适配层；在装了 Hermes 的机器上跑 `hermes plugins validate .` 和 `hermes plugins doctor . --ci`。

## 刻意不做的事

- **MCP 服务器。** 地图是 hook 强制执行的纪律，加一个任何 agent 都能运行的 CLI；不是一个 agent 想起来才去查的数据库。
- **挖掘对话记录。** Stop hook 要求 agent 写下它学到的东西，而不是从记录里猜。
- **自动提交。** vault 的 diff 由人，或在你指示下的 agent，审阅后提交。

## 开发

```
bash check.sh      # 生成一个临时 vault，跑一遍每个 hook 和命令
```

MIT 许可。欢迎 issue 和 pull request。
