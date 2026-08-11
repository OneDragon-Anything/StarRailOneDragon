# 0091. 商店刷新概率表 REFRESH_PROB 实机 OCR 落地(推翻 placeholder)

- **Status**: accepted
- **Date**: 2026-08-11
- **原编号**: D-91

## Context
旧 `REFRESH_PROB` 是粗近似占位(仅 7 级 3 费=0.4 一个实测点 + 其余推测),Lv.4 还误写 `{1:1.0}`。备战 shop 底部 5 个百分比条**可点击**弹完整概率表 modal(此前误以为常驻显示)。

## Decision Drivers
- placeholder 不准(Lv.4 误写)
- 实机 OCR + VLM 双源复核一致(每行和=100%)
- 弹窗表是权威(底部条值 ≠ 理论概率)

## Considered Options
1. 保留 placeholder + bwiki 推测(不准)
2. 底部条 OCR(值 ≠ 理论概率,疑实际刷出分布 / 图形误读)
3. 实机点弹窗表 OCR + VLM 双源复核(选中,权威)

## Decision
`REFRESH_PROB` 落 `cw_shop_odds`(代码单一源,Lv1-10 × 1-5 费 实机 OCR + VLM 复核一致;如 Lv.4=65/25/10、Lv.7=19/30/40/10/1)。**基础表**;角色/装备/效果改概率留 A4.7(基础 × 修正因子,待数据采集)。备战 doc 子态 5 + economy_research §1 指向代码(不重贴,防双源)。

## Consequences
- 正向:概率表权威化;`acquirability_factor`(D-92)有理论地基;7 级 3 费=0.4 与旧实测点吻合。
- 负向:底部条含义待查(≠ 理论概率,疑当前轮实际刷出分布 / 图形误读)。
- 边界:基础表无修正因子;部分角色/效果改概率(A4.7)待全采集。

## Links
- `· docs/game/currency_war/data/economy_research.md` §1
- 关联 D-NN:D-21(level_plan 硬地基)、D-92(acquirability 用 REFRESH_PROB)、D-94(14 §1 概率表权威源更新)
