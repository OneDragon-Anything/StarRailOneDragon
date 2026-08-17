# Claude Code：接入团队 AGENTS.md

> 适用于 Claude Code 用户;所用工具不同见 [../ai_coding.md](../ai_coding.md) 按工具并列的接法。

> [ai_coding.md](../ai_coding.md)「团队源 vs 个人入口」在 Claude Code 上的具体接线。

## 推荐:用 `@` 引入 AGENTS.md

1. `.claude/CLAUDE.md` 用 `@../AGENTS.md` **引入** `AGENTS.md`。Claude Code 启动时自动加载,无需配置。
2. **Claude 特有**的项目级规则写在 `@` 引入的**下方**(提交、团队共享)。例如强制 `uv`、用 context7、Bash 后台等。
3. **个人**偏好写仓库根 `CLAUDE.local.md`(gitignore),加载在 `CLAUDE.md` 之后。

> 入口文件优先放工具自己的配置目录(`.claude/`),不堆项目根。最理想是工具能直接读 `AGENTS.md` —— 那样根本不需要入口文件。

## 推荐 `.claude/settings.json`(个人本地,不进版本库)

`.claude/settings.json` 被 `.gitignore` 忽略,每位开发者自行创建。推荐内容:

```json
{
  "env": { "ENABLE_LSP_TOOL": "true" },
  "permissions": {
    "allow": [
      "Bash(uv *)",
      "mcp__plugin_context7_context7"
    ],
    "deny": [
      "Bash(python *)",
      "Bash(python3 *)"
    ]
  },
  "enabledPlugins": {
    "context7@claude-plugins-official": true,
    "uv-pyright-lsp@onedragon-cc-plugins": true,
    "superpowers@claude-plugins-official": true
  },
  "lspServers": {
    "uv-pyright": {
      "command": "uv",
      "args": ["run", "pyright-langserver", "--stdio"],
      "extensionToLanguage": { ".py": "python", ".pyi": "python" }
    }
  },
  "additionalDirectories": []
}
```

> `deny: Bash(python *)` 只拦截 Claude Code 经 Bash 工具发起的 `python` 调用(强制走 `uv run`),不影响你自运行 `debug.bat`/`env.bat`。插件(context7 / uv-pyright-lsp)需各自 trust 对应 marketplace;uv-pyright 还需 `pyproject.toml` 的 `[tool.pyright] extraPaths=["src"]` 才能解析 src-layout。

## 其他工具(无原生引入机制时)

若某工具既读不了 `AGENTS.md`、又没有 `@` 之类的引入语法,只能读它自己固定的入口文件,就用**硬链接**让该文件镜像 `AGENTS.md`(入口位置同样遵循「优先配置目录,其次根目录」):

```powershell
New-Item -ItemType HardLink -Path "CLAUDE.md" -Target "AGENTS.md"
```

- 该入口文件应被 `.gitignore` 忽略,仅本地生效(个人级)。
- 工具特有的项目级内容,另起一个**提交**的文件维护,不要塞进 `AGENTS.md`。
- 将来某工具支持引入语法时,优先用引入、弃用硬链接。(Unix:`ln AGENTS.md CLAUDE.md`。)

## 相关文档

- [ai_coding.md](../ai_coding.md) — 通用方法论(团队源 vs 个人入口)
- [commit-trailer.md](commit-trailer.md) — commit trailer 自动注入
- [AGENTS.md](../../../AGENTS.md) — 团队源
