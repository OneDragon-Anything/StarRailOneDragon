# 0002. MCP 直调 + area CRUD 工具 > 手编 yml / HTTP 脚本

- **Status**: accepted
- **Date**: 2026-08-04(形式化;原始踩坑 2026-07 初)

## Context
两个早期踩坑:
1. 早期写过 `streamablehttp` 客户端脚本调 MCP server —— 其实 `mcp__sr_od__*` 工具一开始就在工具列表里,写 HTTP 客户端是绕路。
2. 改名模板时手编了 `enter_game.yml` + 重命名模板目录,漏了 `_od_merged.yml` 合并缓存 → daemon 按旧缓存加载报「未找到模板」。根因:只有 `save_screen` 同步独立 yml + `_od_merged.yml` 合并缓存;手编 yml 不重算合并缓存。

## Decision Drivers
- **不漏合并缓存**:screen_info 的真实加载源是 `_od_merged.yml`,手编分屏 yml 不重生成不生效。
- **不绕路**:MCP 工具已直连 server,别再写 HTTP 客户端。
- **可校验**:工具改动经框架 save_screen 走完整同步链。

## Considered Options
1. **HTTP 客户端脚本调 server**:绕路(工具已直连)。
2. **手编 screen_info yml / 手改模板目录**:漏合并缓存,daemon 加载旧缓存报错。
3. **MCP 工具直调 + area 走 CRUD 工具**(选中):直连 + 经 save_screen 同步。

## Decision
选 3:
- MCP 工具**直调**(`mcp__sr_od__analyze_screen` / `upsert_screen_area` / `delete_screen_area`),别写 HTTP 客户端脚本绕路;连接 stale 让用户 `/mcp` 重连。
- screen_info 的 area 改动**一律走 CRUD 工具**(`upsert_screen_area` / `delete_screen_area`)—— 经 `save_screen` 同步独立 yml + `_od_merged.yml` 合并缓存 + reload。
- **禁止手编 screen_info yml 或手改模板目录**。

## Consequences
- **正向**:不绕路、不漏合并缓存;改动走完整同步链可校验。
- **负向**:批量同屏改动(如 5 个 pc_rect 修正)用 N 次 MCP 直调比一次串行脚本低效(同屏 save 写竞争需串行)—— 该场景对「直调 > 脚本」待放宽(见 overview todo)。
- **follow-up**:批量场景的脚本化说明待补。

## Links
- SKILL.md「前置:工具用法」。
- 框架接口:`save_screen` / `upsert_screen_area` / `delete_screen_area` / `analyze_screen`(框架地基级,可写进 SKILL.md,见 skill-guide ADR-0002)。
