---
screen_name: 货币战争-备战
appears_in: [currency_war]
last_updated: 2026-08-04
source_image: screens/货币战争-备战/(多子态,见下)
---

# 货币战争-备战(策略主战场)

每个位面每轮的备战:买牌 / 升等级 / D 牌 / 部署 / 出战。bot 策略(`cw_decisions.plan`)在此运行,是自动化核心画面。screen_info:`assets/game_data/screen_info/currency_war_battle_prep.yml`。

## 何时出现 + 状态流转

- **入口**:投资环境「确认」→ 本屏(Plane 1 Round 1);每轮战斗后 → 事件/下一轮 → 回本屏。
- **出口**:点「出战」→ 自动战斗 → 结算 → (事件/下一轮)→ 下一备战 或 位面切换。
- **子态**(同屏,差异 = 商店开关,**影响 reader 可读性**):
  - **shop 关闭**:右上角 HP 可读(`read_hp` 真值);右下金币区空。bot 入口默认此态(上轮收起)。
  - **shop 开启**:右上 HP 区**空**(`read_hp`→100);右下金币可读;商店牌区显示刷新概率%。plan-time 此态。
  - → `BuyShopCards` 修复:shop 关闭帧读 HP 覆盖 state.hp(见 `cw_observation.read_hp`)。

## 识别特征(稳定锚点)

- 独有文字:「备战阶段」(顶栏)+「购买经验」(左下)+「出战」(右)+ 位面-轮次「X-Y」。
- screen_info:`货币战争-备战` 匹配(命中 购买经验/商店/出战 area)。

## 可交互元素(screen_info area,坐标见 yml)

- 「商店」/「收起」:底部右,切换 shop 开/关。
- 「购买经验」:左下,买经验升等级(= 上阵数上限)。
- 「刷新」:中右,D 牌(刷新商店)。
- 「商店牌-1..5」:顶部 5 张可买牌(点击购买)。
- 「备战栏-1..9」:底部,持有角色(拖拽源)。
- 「前排-1..4 / 后排-1..6」:舞台部署槽(拖拽目标)。
- 「出战」:右,进自动战斗。

## 关键 reader(`cw_observation`,区域全在 screen_info)

- `read_hp`(⚠️ shop 关闭态才准)、`read_gold`(shop 开态准)、`read_level`(OCR+启发式兜底)、`read_phase_round`(位面-轮次)、`read_board`(左面板阵营计数,**解析脆,已加 sanity bound**)、`read_shop_cards`(5 牌:阵营/名/cost)、`read_deployed_count`(舞台「X/Y」已部署数)、`read_bench_full`(席满警告)。
- **不读**:bench/deployed **角色身份**(无名字,纯立绘 → 需 SIFT 模板,见 `currency_war_char_id`;现有忘却之庭脸近景模板错来源,待建货币战争立绘库)。

## 识别快照

### 1. shop 关闭态(默认 / 入口)
- 命中:screen「货币战争-备战」+ area 购买经验/商店/出战。
- OCR:备战阶段 / 1-1 / HP(右上,如 60/84/29)/ 购买经验 / 出战 / 商店(= 关)。
- fixture:`screens/货币战争-备战/shop_closed.webp`(HP84)、`shop_closed_lowhp.webp`(HP29,<HP_DANGER)、`shop_closed_a8_start.webp`(A8 起 HP60)。

### 2. shop 开启态(plan-time)
- OCR:备战阶段 / 购买经验 / **收起**(= 开)/ 商店牌 5 张(名+阵营)/ 刷新概率%(65/25/10…)/ 金币(右下)。
- fixture:`screens/货币战争-备战/shop_open.webp`。

## 备注

- **read_hp shop 态依赖(已修)**:HP 只 shop 关闭时显示;`BuyShopCards` 在 shop 关闭帧读 hp 覆盖 state.hp。回归测试 `test_read_hp_shop_state`。
- **read_board 解析脆**:面板格式复杂("X/Y" 或激活 tier 串),已加 count∈[1,9] sanity bound 防 213 垃圾;真实格式待视觉核实后重写。
- **bench/deployed 身份**:无名字 → SIFT 模板(待建货币战争立绘库);deploy 现走位置式(`DeployBench`)。
- 策略接法详 `docs/game/currency_war/strategy/`;reader 详 `cw_observation.py`。
