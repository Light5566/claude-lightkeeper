# Lightkeeper：配置、团队协作、让地图保持诚实

[回到 README](../README.zh.md)

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
- **PR 评论机器人。** 在代码仓库的 workflow 里加一行 `uses: Light5566/claude-lightkeeper/action@main`，每个 pull request 都会收到一条评论：改动的文件归哪些笔记管、这些笔记还连着什么以及为什么、它们的第一条 Gotcha，以及哪些文件没有笔记认领。只提醒，不拦截。配置见 [action/README.md](../action/README.md)。

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

## 笔记与分支

所有分支共用一张地图也有一个问题：在功能分支上写的笔记，`main` 上的 agent 也会读到。所以 hook 会记下每篇笔记最后是在哪个分支上改的。当 agent 打开一个文件，而它的笔记最后写在当前 checkout 不包含的分支上，文件指针会说明这一点，并让 agent 先对照眼前的代码。分支合并后，提示自动消失。`vault status` 会列出这些笔记。记录只保存在本机（和 vault 注册表放在一起），不会写进 vault 或代码仓库。
