# Lightkeeper

[![Listed on ClaudePluginHub](https://www.claudepluginhub.com/badge/light5566-lightkeeper)](https://www.claudepluginhub.com/plugins/light5566-lightkeeper?ref=badge)

**一张代码库的知识地图：你的编程 agent 改代码前先读它，结束前必须更新它。** 支持 Claude Code、Hermes Agent 和 Codex。

[English](README.md) · [中文](README.zh.md) · [在线画廊](https://light5566.github.io/claude-lightkeeper/)（Excalidraw、Mastodon、Gitea、Paperless-ngx 和 BookStack 的交互式代码地图）· [更新日志](CHANGELOG.md)

![Claude Code 与 Obsidian 并排：改代码前先查地图，改完后更新拥有该文件的笔记](https://light5566.github.io/claude-lightkeeper/assets/demo-v3.gif)

编程 agent 每开一个会话都要重新认识你的代码库；长会话的上下文一被压缩，它读过的内容也跟着丢了。Lightkeeper 把 agent 应该知道的东西写下来，再用 hook 在它打开文件的那一刻，把对应的笔记送到它面前。

```
/plugin marketplace add Light5566/claude-lightkeeper
/plugin install lightkeeper@claude-lightkeeper
/lightkeeper:init
```

在 Claude Code 里三行，第三行在你的项目里运行。它为你所在的仓库建一张地图，然后提议根据代码写出第一批笔记。不会往你的仓库里写任何东西：地图放在 `~/vaults/<名字>`。用 [Hermes Agent 或 Codex](docs/agents.zh.md)？安装命令在那里。

Lightkeeper 是一个 Claude Code 插件，也能作为 Hermes Agent 和 Codex 插件运行。它把"系统是怎么运作的"（模块、流程、集成、平台陷阱、决策、版本，以及它自己用法特殊的词）维护成一份 Obsidian 兼容的 Markdown 地图，放在代码仓库**之外**，并通过 agent 的 hook 让这张地图始终保持真实：

- **会话引导**：告诉 agent 地图在哪、怎么查；
- **提示词匹配**：你刚问的问题涉及哪些笔记，立刻列出来；
- **文件指引**：agent 第一次读或改某个文件时，指向拥有这个文件的笔记；
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

接着 agent 打开 `app/Services/PaymentService.php` 时，文件指引会说：

> `app/Services/PaymentService.php` is documented by vault note "Payment" (updated 2026-10-02) — read its Gotchas before going further.
> If you change this file and the change alters behavior, updating the note afterwards is part of the definition of done.

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

**需要：** [Claude Code](https://code.claude.com)、git、PATH 里有 Python 3.9 或更新版本（macOS 和大多数 Linux 自带）。Obsidian 可选：[obsidian.md/download](https://obsidian.md/download) 或 `brew install --cask obsidian`。

1. **在 Claude Code 里安装插件：**

   ```
   /plugin marketplace add Light5566/claude-lightkeeper
   /plugin install lightkeeper@claude-lightkeeper
   ```

   或在 shell 里：`claude plugin marketplace add Light5566/claude-lightkeeper && claude plugin install lightkeeper@claude-lightkeeper`。

2. **创建地图**，在项目里的会话中运行：

   ```
   /lightkeeper:init
   ```

   不带参数时，它覆盖你所在的仓库，用文件夹名给 vault 命名，放在 `~/vaults/<名字>`，并把 `vault` 命令装到 `~/.local/bin`。它会先把这些选择给你看，问一次再动手。想自己决定：`/lightkeeper:init ~/vaults/myapp --name "My App" --repo ~/code/myapp --repo ~/code/myapp-web --git-hook`。

3. **从代码生成第一批笔记：**

   ```
   /lightkeeper:seed
   ```

   Claude 提出领域划分和最多 60 个带真实文件路径的模块存根，征求你同意后写入。从这一刻起文件指针就会触发，当前会话也一样。会话引导从下一个会话开始出现。

就这些。还有三件事值得知道：

- **看地图：** 在 Obsidian 里打开 vault 文件夹（*Open folder as vault*），或运行 `vault export --html map.html` 生成一个能在浏览器里打开的单页。
- **检查是否正常：** `vault doctor` 在一屏里检查整个设置，每个问题旁边都给出修法。装了插件却没建地图时，在仓库里的第一个会话会提醒你一次。
- **关掉它：** `vault init --forget` 让这个项目不再使用该 vault，并移除它装的 git 钩子。vault 文件夹原样保留。

项目已经有 vault？一步克隆并登记：

```
/lightkeeper:init --clone git@github.com:your-team/myapp-vault.git --repo ~/code/myapp --git-hook
```

已经有一个 Obsidian vault 想逐步迁入？`vault init --adopt ~/my-vault --name "My App" --repo ~/code/myapp` 只写配置并登记，不碰你的笔记；只有带 `type:` 的笔记才会被检查，可以慢慢来。

## Hook 一览

全部只是建议。没有一个能拦截编辑；在没有 vault 覆盖的仓库里、在没有 vault 的机器上，它们全都静默。

![编辑前提示与 Stop 提醒在 Claude Code 会话中触发](https://light5566.github.io/claude-lightkeeper/assets/hooks.png)

| 事件 | 说什么 | 什么时候不说话 |
|---|---|---|
| SessionStart | vault 在哪、怎么查、更新它是完成的一部分；每天一次报告需要关注的笔记数 | resume 时 |
| SessionStart（压缩上下文后） | 重新查 vault，别再把读过的代码读一遍；列出压缩前用到、正文已被压缩掉的笔记，并让提示和指引重新指向它们 | |
| UserPromptSubmit | 最多三篇名字、别名或 flag 出现在你提示词里的笔记，附一句话简介和相邻笔记；提示词里出现术语表里的词时，附上它在这里的意思；每个会话一次，当提示词听起来像一个决定或裁定时提醒记录到 Decisions | 没有新匹配 |
| PreToolUse（Read/Write/Edit） | 即将读取或修改的文件归哪篇笔记管，以及它的邻居；读取时就提示，agent 还在规划阶段；存根笔记会说"还没记录任何内容，把你学到的写上去" | 文件无人认领，或本会话已经指过这篇笔记 |
| Stop | 过去 6 小时里被监视的文件变了但没有笔记变动；点名拥有者笔记，并统计没有笔记认领的文件 | vault 工作区有未提交改动，或在时间窗内已提交 |

## 怎么写笔记

每篇笔记都是普通 Markdown，frontmatter 一行一个键值。引擎从你的写法里读三样东西：

- **唯一的规则：每个 `[[链接]]` 都带一个理由。** `- [[Invoice]] — a paid order raises an invoice through InvoiceService::create()`。理由会变成每条搜索结果旁边的"影响范围"；没有理由的链接只会把图谱变成一团毛线。
- **模块笔记里的 *Where it lives* 表格是机器读的**：真实文件，每格第一个路径写完整，绝不写容器目录。编辑前 hook 就跑在这张文件→笔记的索引上。
- **术语表。** 这个代码库用法特殊的词，在 `9 Glossary` 里写一篇短笔记（`type: term`）：它在这里是什么意思、出现在哪里。提示词里一出现这个词，提示就会附上它的意思，agent 不用去猜。同一个词在不同模块里意思不同时，把每个意思写在 *Where it shows up* 里对应模块的那一行：提示会按模块列出意思，本次会话里已经用到的模块排在前面，并附上 *Not to be confused with* 的第一行。
- **诚实字段。** `status: shipped` 表示代码在生产分支上；`depth: stub` 表示笔记还很薄；每次碰笔记都要更新 `updated:`。笔记可以是错的；代码和笔记不一致时，以代码为准，修正笔记是这次改动的一部分。

脚手架里的 `_meta/Conventions.md` 和 `_meta/How to update.md` 有完整约定、触发表（什么样的改动该碰哪篇笔记）和"60 秒版本"。`knowledge-vault` skill 把这些教给 Claude。

## 命令行

```
vault find <terms>              主题搜索，分层：名字 → 别名/flag → 标签 → 全文
vault find --paths <files>      这些文件归哪些笔记管
vault check [--write]           检查；--write 还会重建索引并重新生成
                                Coverage.md、Vault Changelog.md、Attention.md 和 World.canvas
vault status                    覆盖率、过期笔记、需要关注的项、同步落后情况，一屏看完
vault status --session          最近一个会话里 hook 做了什么：运行次数、提到的笔记、哪些已更新
vault sync [target] [--advance] 自上次对账以来仓库里落地了什么
vault log <note>                这篇笔记的 git 历史
vault export --html <file>      一个自包含的交互式地图
vault export --agents-md        给 AGENTS.md 的一段说明：地图在哪、怎么查、哪篇笔记管哪些代码
vault doctor                    这里装好了吗、在工作吗？每个问题旁边给出修法
vault init                      在 git checkout 里：为这个仓库建 vault，全部用默认值
vault init <path> --repo ...    自己决定：创建、克隆（--clone）或接管（--adopt）一个 vault
vault init --forget             这里不再使用某个 vault；文件夹保留
```

每个命令都接受 `--vault <path>`；不给的话，用覆盖当前目录的那个 vault。

`vault export --agents-md` 是给不跑 Lightkeeper hook 的 agent 用的。它只打印这段说明，从不写进任何文件：你自己把它贴进 `AGENTS.md`、`CLAUDE.md` 或 `GEMINI.md`，或者让 agent 去贴，这样你能看到 diff。要刷新，就再跑一次，替换两个标记之间的内容。一个 vault 覆盖多个仓库时，在对应的 checkout 里跑，或者传 `--repo KEY`。

`vault check` 会抓出解析不了的链接、重名笔记、没有理由的链接、容器目录声明、不合规的 frontmatter、孤儿笔记、过期笔记，以及任何像密钥或个人数据的东西（邮箱、长数字串、API key 形状、私钥）。每次提交 vault 前都带 `--write` 跑一次。

## 兼容性

| | |
|---|---|
| Claude Code（CLI、桌面端、IDE 扩展） | hook、skill、命令和 CLI |
| Hermes Agent | hook、skill、流程和 CLI，通过仓库根目录的适配层；见 [docs/agents.zh.md](docs/agents.zh.md) |
| Codex | hook、skill 和 CLI，通过 `codex/` 里的适配层；见 [docs/agents.zh.md](docs/agents.zh.md) |
| 其他 agent（Cursor、Gemini CLI 等） | `vault` CLI、SKILL.md 文件，以及 `vault export --agents-md` 打印的、给它们的 AGENTS.md 用的一段说明 |
| macOS、Linux | 已测试 |
| Windows | 未测试；hook 直接调用 Python，WSL 或 Git Bash 应该可以 |
| Obsidian | 可选：图谱配色、Bases 视图和 canvas 是附加项；笔记本身是带 wikilink 的普通 Markdown，Foam、Logseq 或任何编辑器都能读 |
| Python | 3.9 或更新，只用标准库，不需要 pip 安装任何东西 |
| 语言和框架 | 任意；`vault init` 识别项目布局，其余交给 `vault.json` |

## 更多

- **[配置、团队协作、让地图保持诚实](docs/guide.zh.md)：** `vault.json`、和同事共用一个 vault、PR 评论机器人、分支上的笔记，以及指出哪些笔记已经过时的检查。
- **[Hermes Agent 和 Codex](docs/agents.zh.md)：** 安装命令，以及每个里面具体接了什么。

## 刻意不做的事

- **MCP 服务器。** 地图是 hook 强制执行的纪律，加一个任何 agent 都能运行的 CLI；不是一个 agent 想起来才去查的数据库。
- **挖掘对话记录。** Stop hook 要求 agent 写下它学到的东西，而不是从记录里猜。
- **自动提交。** vault 的 diff 由人，或在你指示下的 agent，审阅后提交。

## 开发

```
bash check.sh      # 生成一个临时 vault，跑一遍每个 hook 和命令
```

MIT 许可。欢迎 issue 和 pull request。
