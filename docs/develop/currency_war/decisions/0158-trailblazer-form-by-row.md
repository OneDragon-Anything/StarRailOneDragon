# ADR-0158 开拓者形态按排归一(羁绊计算修正)

## Status

Accepted(2026-08-16)

## Context

开拓者在货币战争中是**同一角色两形态**:前台=记忆命途(列车+能量)、后台=欢愉命途(列车+能量+**欢愉**);拖到另一排即切换,plaza `switch_freq` 363 次欢愉→记忆切换 = 同局反复换排是常态。注册表按形态分两条目(`开拓者·记忆/开拓者·欢愉`,立绘不同,SIFT 按立绘判身份)——但**身份计算(羁绊计数/装备/部署)按 char_id 原值进行**,换排后 tracking 里的形态名与游戏内实际命途错位:欢愉形态被拖上前排 → 游戏内「欢愉」羁绊已消失,计算侧仍计入(虚高);记忆侧漏算。

连带发现(测试暴露):`board_from_tracked`(ADR-0157 前落地的「计算为准」)只数 `factions`(阵营类),漏 `flows`(流派类:能量/欢愉/击破)——左面板与 OCR board 两者都计,只数 factions 系统性漏流派羁绊(开拓者的「欢愉」正在 flows)。

## Decision Drivers

1. 用户 2026-08-16 指示:计算羁绊的代码要注意开拓者的特殊性(前后台命途不一样)。
2. board 是 form_progress/pivot/economy 的地基,形态错位 = 羁绊计数双向错。

## Considered Options

- **按 char_id 原值算**(现状):拒绝 —— 换排后必错。
- **SIFT 立绘重判**(每次换排后重识别):重且滞后(识别在观察帧,不在转移帧)。
- **按排归一**(采纳):`trailblazer_form(name, row)` 纯函数,排是权威信息(转移/识别都已写 position_pref),零识别成本。

## Decision

1. `cw_chars.trailblazer_form(name, row)` / `is_trailblazer(name)`:`_TRAILBLAZER_FORMS` 表(基名→{排:形态});row 异常时按注册表 position_pref 兜底。
2. 接线四处:
   - `board_from_tracked`:计羁绊前先按 `position_pref` 归一形态;
   - `simulate` DeployMove:换排时同步 char_id + faction(前瞻语义);
   - `mutate_bench_deployed` DeployMove:同上(运行时 tracking 单一源语义);
   - `identify_slots` 已上阵排:SIFT 判名后按 row 归一消歧(立绘库两形态覆盖不均时防误判)。
3. 羁绊计数 = `factions + flows` 流派并入(与 OCR board 同口径)。
4. 测试 4 条锁定:形态解析/前后排羁绊差异(前排无欢愉、后排有)/simulate 换排切换/mutate 同步。

## Consequences

- bench 里的开拓者(未上阵)按识别名不变(bench 无排语义,固有偏好仅参考);首次 deploy 即归一。
- `independent`(独立羁绊:挚爱之人等)是否进 board 计数待核(面板是否显示独立羁绊行)——下轮观察。
