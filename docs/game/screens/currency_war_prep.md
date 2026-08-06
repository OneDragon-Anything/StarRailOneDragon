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
- **顶栏按钮**(攻略 / 教学 / 数据银行 / 数据统计,screen_info `按钮-*`):**数据银行**(右上)开
  **非破坏性 overlay** —— 进图鉴分类菜单(角色 71/71 / 羁绊 / 装备 / 投资环境 / 投资策略 / 竞争对手),
  **对局保留**(不退出备战,关掉即回备战;2026-08-06 实测)。bot 不自动化它,但作**手动查图鉴 / 数据采集
  入口** —— 图鉴 = canonical 模板 + 数据源(装备/投资环境等全量图标 + 效果;D-68 投资环境、D-76 装备
  采集均经此),bot 开发者建档 / 核对数据用。

## 关键 reader(`cw_observation`,区域全在 screen_info)

**OCR/area 字段层(全接,doc 13 §13.2 备战可采字段)**:
- 进度/节点:`read_phase_round`(位面-轮次,区域-阶段)、`read_node_type`(当前节点类型,顶部标签 首领→boss 等;D-73,仅 boss 实机核实)
- 经济:`read_gold`(文本-金币数)、`read_level`(文本-等级,OCR+`_expected_level` 兜底)、`read_xp_progress`(文本-升级所需经验 "X/Y";D-72)、`read_level_up_cost`(文本-购买经验金币数;D-74)、`read_shop_refresh_cost`(文本-刷新金币数,默认 2;D-74)、`read_streak`(文本-连胜数;D-74)
- 难度:`read_enemy_difficulty`(文本-难度 左上角;D-74,⚠️ stylized OCR 常空,可靠读待 vision/digit-CV)
- 棋盘:`read_board` + `read_board_next_tier`(区域-羁绊面板 "X/Y"→count + 下个 tier 阈值;D-69,聚焦 OCR 治了旧"213"误读脆)、`read_deployed_count`(区域-部署数「X/Y」)
- 商店:`read_shop_cards`(商店牌区 5 牌:阵营/名/cost)、`read_bench_full`(席满警告)
- 生命:`read_hp`(⚠️ shop 关闭态才准,文本-剩余血量)

**视觉身份层(SIFT,`cw_identity_obs`,D-75 已接线 + 实测验证)**:
- bench/deployed **角色身份**(`read_bench_chars` / `read_deployed_chars`):裁 screen_info 槽位
  (前排-1..4 / 后排-1..6 / 备战栏-1..9)→ SIFT 对 `character_avatar` 脸近景库 → `resolve_char_name`
  → 规范名。**D-75 实测扭转旧结论**:脸近景库对备战半身立绘强命中(4/4 前排:佩拉/黑塔/Saber/藿藿,
  inliers 23-30 vs 第二名 3-4;备战栏 8/9),**无需从零采半身模板**。与 bot 跟踪(deployed/bench
  默认由 buy/deploy 推演)互补 —— 视觉 reads 是离线重建 / 漂移恢复旁路(不进 read_game_state)。
  待核:配饰/帽子重角色(黑天鹅)、货币战争变体(姬子·启行 共脸异名 → 归一基础名,子串消歧)。

**未接(前沿,需图标库 或 bot 跟踪)**:
- `Unit.equips`(角色身上装备,纯图标 → 装备图标库 / bot 跟踪 equip 动作)
- `active_strategies`(右面板图标列,vision 探到 ~x1797-1918 y172-404;identity 需策略图标库 / bot 跟踪 decide_invest 拾取)
- `inventory.available_equips`(区域-道具装备 [1252,90,1918,710],icon → 装备图标库 / bot 跟踪)
- `node_path`(顶部节点行图标序列 → 节点类型图标库 + 多态实机定 icon↔类型映射)
- `shop_locked`:备战未见独立 lock 控件(商店/收起=开关非锁)→ 非备战字段

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
- **read_board 脆已治(D-69)**:旧全屏 OCR 把 "2/3" 误读 "213" 显脆;根因=全屏密度。`_board_pairs` 区域 OCR 读对 "X/Y" → count=X + next_tier=Y(`read_board_next_tier`,doc 13 FactionState.next_tier)。
- **bench/deployed 身份(D-75 已接)**:脸近景库 SIFT 强命中(见上「视觉身份层」);reader 在
  `cw_identity_obs`,与 bot 跟踪互补(离线重建 / 漂移恢复)。deploy 运行时仍走位置式(`DeployBench`)。
- 策略接法详 `docs/game/currency_war/strategy/`;reader 详 `cw_observation.py`。
