# ADR-0455: 刷新费/连胜读取器对齐放大管线 + 刷新费 None 语义

- **Status**: accepted
- **Date**: 2026-08-29

## Context

备战小字数字字段中,`read_shop_refresh_cost`(文本-刷新金币数)与 `read_streak`
(文本-连胜数)是仅有的两个仍用 native 直读(`_ocr`,无放大)的字段——金币/等级/
升级费用/经验均已放大读(W332 家族口径),这两处是管线不一致的历史残留。
带横幅变体帧离线复跑实证:刷新费 rect 真值 0 被「读不到兜底 2」静默改成 2
(错值喂刷新期望/决策,最险单项);连胜 rect 真值 1 直读 miss、3x 放大可读。

## Considered Options

1. **放大两级管线 + 刷新费 None 语义(采纳)** —— 两字段对齐
   `read_level_up_cost` 形状:`_ocr_upscaled` 读空 → `_ocr_upscaled_binarized`
   重试;刷新费两级读空返 **None=读不到**,消费方走既有 `or 2` 兜底,
   「读不到」与「真 0」不再混写。连胜本就 None 语义,只换放大管线。
2. **保留兜底 2(拒绝)** —— 免费刷/减免档(真 0)与失读不可区分,兜底值
   直接进刷新期望账,是错值而非保守值。
3. **只加放大不改语义(拒绝)** —— 放大解决检出率,但不解决「读不到时写什么」
   的语义问题;横幅帧实证恰好两者都要。

## Decision

- `read_streak`:`_ocr` → `_ocr_upscaled`(3x;None 语义不变)。
- `read_shop_refresh_cost`:签名 `int` → `int | None`,两级放大管线 +
  `_parse_coin_fee_digit` 图标前缀归一(rect 内恒为金币图标+一位费用数字,
  图标被 OCR 系统性并入前缀 'G'/'O','GO'='G0'=0——同 ADR-0417 paddle
  人形前缀守卫的「图标并入数字」先验,先归一大写、残留 O→0 再取整数);
  守卫 0..10,域外/两级全空 → None。
- `read_game_state` 直写 `state.shop_refresh_cost`(可为 None);消费方审计:
  shop.py 刷价扣费、cw_line_switch、decision_v2(ev/candidates/scoring/
  economy_cycle/posture_release)、cw_sim、cw_telemetry 审计全部已用
  ``state.shop_refresh_cost or 2`` 形态,None 自动落默认 2,零适配改动。
- `cw_state.shop_refresh_cost` 字段默认值 2 不动(禁碰文件;None 只在
  「当帧读不到」时短暂出现,下一备战帧自愈,与 enemy_difficulty 双源语义同型)。

## Consequences

- 横幅帧真 0 恢复读 0;失读帧刷新期望退默认 2(与旧兜底等值),不再把失读
  伪装成读数。
- 实帧锁(test_cw_observation):横幅帧 刷0/连胜1 + 基线帧现读值;
  mock 锁 空→None、'G0'/'GO'→0。
- `read_node_type` 标签 rect 硬编码等其他 W558 缺陷不在本批(另行立项)。
