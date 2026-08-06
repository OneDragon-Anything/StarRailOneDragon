---
screen_name: 货币战争-备战
appears_in: [currency_war]
last_updated: 2026-08-07
source_image: screens/货币战争-备战/(多子态,见识别快照)
---

# 货币战争-备战(策略主战场)

每个位面每轮的备战:买牌 / 升等级 / D 牌 / 部署 / 出战。bot 策略(`cw_decisions.plan`)在此运行,是自动化核心画面,也是货币战争出现最多的画面。screen_info:`assets/game_data/screen_info/currency_war_battle_prep.yml`(screen_id `currency_war_battle_prep`)。

## 何时出现 + 状态流转

- **入口**:投资环境「确认」→ 本屏(Plane 1 Round 1);每轮战斗后 → 事件/下一轮 → 回本屏。
- **出口**:点「出战」→ 自动战斗 → 结算 → (事件/下一轮)→ 下一备战 或 位面切换。
- **子态**(同屏,差异 = 商店开关,**影响 reader 可读性**):

  | 子态 | 入口 | HP(右上 文本-剩余血量) | 金币(右下 文本-金币数) | 商店按钮 | 商店牌区 |
  |---|---|---|---|---|---|
  | shop 关闭 | 上轮收起 / 入口默认 | **可见**(真值) | 空(不可读) | 「商店」 | 隐藏 |
  | shop 开启 | 点「商店」 | 空(read_hp→100) | **可见** | 「收起」 | 5 张牌 + 刷新概率% |

  - plan 在 shop 开启态运行;HP 须在 shop 关闭帧读(见下 reader)。

## 识别特征(稳定锚点)

- 独有文字:「备战阶段」(顶栏)+「购买经验」(左下)+「出战」(右)+ 位面-轮次「X-Y」。
- id_mark area:`备战标识-购买经验` → 精准匹配(`is_precise`)。

## 可交互元素(screen_info area,坐标见 yml)

- 「商店」/「收起」(按钮-商店):底部右,切换 shop 开/关。
- 「购买经验」(备战标识-购买经验):左下,买经验升等级(= 上阵数上限)。
- 「刷新」(按钮-刷新):中右,D 牌(刷新商店)。
- 「商店牌-1..5」:顶部 5 张可买牌(点击购买);部分牌带「试用」红标。
- 「备战栏-1..9」:底部,持有角色(拖拽源)。
- 「前排-1..4 / 后排-1..6」:舞台部署槽(拖拽目标);舞台带「前台区域/后台区域」文字标签(~906,288 / ~906,564)。
- 「出战」(按钮-出战):右,进自动战斗。
- **顶栏按钮**(按钮-攻略/教学/数据银行/数据统计):**数据银行**(右上)开**非破坏性 overlay** → 图鉴分类菜单(角色/羁绊/装备/投资环境/投资策略/竞争对手),**对局保留**(关掉即回备战)。bot 不自动化,但作手动查图鉴 / 数据采集入口(图鉴 = canonical 模板 + 数据源)。
- **惊喜盒(Surprise Box)** @ ~(1395,235):中部偏右的礼盒(沙漏 + 倒计时数字,如「12 节点」)。**倒计时型奖励,自动开启**(装惊喜道具,倒计时结束自动开),**非点击领取** —— 点击只弹 tooltip(「惊喜盒 / 打开倒计时:12 节点 / 自动开启」),ESC 关回备战。bot 无需动作(自动开);纯信息元素。(live 建档补,之前漏。)
- **节点行 / node_path**(顶部一排 ~9 个节点图标,连线成进度路径):每节点图标示类型(宝箱=奖励 / 交叉剑=战斗 / 购物袋=补给 / 角色头像=boss 等),状态色(金=已过 / 红=当前 / 黑=未到)。bot 可读后续节点序列(战略信息:知将到什么)。纯图标无文字 → 需节点类型图标库。(live 建档补,之前漏。)

## 关键 reader(`cw_observation`,区域走 screen_info)

**可靠(实图跨子态核实)**:
- 进度/节点:`read_phase_round`(区域-阶段「X-Y」)、`read_node_type`(顶部节点标签 首领→boss / 战斗→battle 等;**仅 battle/boss 稳**,见备注)。
- 经济:`read_gold`(文本-金币数,shop 开启态)、`read_level`(文本-等级「LV.N」)、`read_xp_progress`(文本-升级所需经验「X/Y」)。
- 棋盘:`read_board` + `read_board_next_tier`(区域-羁绊面板「X/Y」→ 阵营 count + 下个 tier 阈值)、`read_deployed_count`(区域-部署数「X/Y」,如 5/5)。
- 商店:`read_shop_cards`(商店牌区 5 牌:阵营/名/cost,name 经 CHARACTER_ROSTER 匹配得规范名 + cost)、`read_bench_full`(「备战席已满」警告)。
- 生命:`read_hp`(文本-剩余血量,**仅 shop 关闭态可读**;shop 开启态该区空 → 返 100)。

**不可行(paddle OCR det 检测不到)**:
- `read_level_up_cost` / `read_shop_refresh_cost`:费用是按钮底部的**小 + stylized 彩色印刷数字**(购买经验「4」、刷新「2」),paddle **det 阶段看不见**(聚焦 OCR 按钮区只读到标签文字「购买经验」/「刷新」/「LV.」/「0/6」,漏掉费用数字;VLM 放大确认数字在)。**OCR reader 不可行,非 area 错** → plan 用**静态估**(`LEVEL_UP_COST_TABLE` + refresh 默认 2;固定游戏机制常量,本就该静态);要精确值需 colored-digit CV 模板(低优)。`文本-购买经验金币数` / `文本-刷新金币数` 两 area 实为无效 OCR 目标。

**弱**:
- `read_enemy_difficulty`(文本-难度 左上角):stylized 数字,OCR 常空。
- `read_streak`(文本-连胜数):实图全 None(数字未显或 area 待核)。

**视觉身份层(SIFT,`cw_identity_obs`)**:
- bench/deployed 角色身份(`read_bench_chars` / `read_deployed_chars`):裁 screen_info 槽位(前排/后排/备战栏)→ SIFT 对 `character_avatar` 脸近景库 → 规范名。脸近景库对备战半身立绘强命中;与 bot 跟踪(buy/deploy 推演)互补,作离线重建 / 漂移恢复旁路(不进 read_game_state)。

**未接(需图标库 或 bot 跟踪)**:
- `Unit.equips`(角色身上装备,纯图标)、`active_strategies`(右面板图标列 ~x1797-1918)、`inventory.available_equips`(区域-道具装备)、`node_path`(顶部节点行图标序列)。

## 识别快照

### 1. shop 开启态(plan-time)— `screens/货币战争-备战/shop_open.webp`
- 命中:screen「货币战争-备战」`is_precise=True`(备战标识-购买经验 conf 0.9999 + 按钮-出战 conf 0.999)。
- OCR:备战阶段 / 1-3 / 购买经验 / **收起**(= 开)/ 商店牌 5 张(群攻·翡翠 / 护盾·丹恒·腾荒 / 追击·不死途 / 追击·飞霄 / 护盾·三月七)/ 刷新概率 ■65% ■25% ■10% / 金币 5 / 刷新 / 出战。board 7 阵营(仙舟/追击/夜之半神/群攻/欢愉/减益/银河学者)。

### 2. shop 关闭态(默认 / 入口)— `screens/货币战争-备战/shop_closed.webp`
- 命中:`is_precise=True`(购买经验 + 按钮-商店 + 按钮-出战)。
- OCR:备战阶段 / 1-3 / 战斗(node=battle)/ **HP 84**(右上 文本-剩余血量)/ 购买经验 / 商店(= 关)/ 出战。board 6 阵营。金币区空。fixture 变体:`shop_closed_lowhp.webp`(HP 29)、`shop_closed_a8_start.webp`(A8 起 HP 60、board 空)。

### 3. 部署后 + boss 节点 — `screens/货币战争-备战/deployed_p1r9.webp`
- 命中:`is_precise=True`(购买经验 + 按钮-商店 + 按钮-出战)。
- OCR:备战阶段 / 1-9 / **首领**(node=boss)/ HP 60 / deployed **5/5**(区域-部署数)/ 金币 20 / Lv.5 / 4/20(xp)/ 前台区域·后台区域(舞台前后排标签)。board 8 阵营。

## 备注 / 待查

- **建档进行中(live,不 declaring done)**:live + VLM 发现之前漏的元素(惊喜盒 / 节点行 / 球体)。用户指出「备战很多可识别元素,之前没建全」→ 继续逐元素 live 核(不沿用 autonomous webp/代码假设)。
- **read_node_type 不可靠根因(live 建档查明)**:其扫描 band 会抓**已过节点(金色)**的标签(如已过的「奖励」节点)当**当前节点** → 误报 reward(实测 round 1-1 当前是菱形节点,但读到已过的「奖励」)。修法:只取**当前节点(红色高亮)**下方的标签(位置随当前节点变,需先定位红色节点),而非扫整条 band。battle/boss 偶然对(恰当前节点标签在 band 内)。
- **HP shop 态依赖**:HP 只 shop 关闭时显示右上;shop 开启态该区空,调用方需在 shop 关闭帧读 hp 覆盖。
- **board「X/Y」聚焦读**:全屏 OCR 会把 "2/3" 误读 "213"(密度);`_board_pairs` 区域裁切 OCR 读对 → count=X + next_tier=Y。
- **node_type band 不稳**:顶部标签 band 偶把非当前节点(如 reward)或 shop 开启态漏读;仅 battle/boss 稳,其余节点类型待多子态实机核全。
- **费用字段 OCR 不可行**:见上「不可行」;静态估是对的,别建/修 area、别接线 cost reader。
- **streak / enemy_difficulty**:实图读不到(streak 全 None;difficulty stylized 常空);待核实显示条件 / 改 digit-CV。
- 策略接法详 `docs/game/currency_war/strategy/`;reader 详 `cw_observation.py`;identity 详 `cw_identity_obs.py`。
