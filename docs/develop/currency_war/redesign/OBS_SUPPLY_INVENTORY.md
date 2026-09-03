# CW 新决策层 · obs 供给面盘点(OPEN-2 收口件)

> 类名已随 2026-09-03 命名迁移更替,对照 NAMING.md(本文为带日期预登记设计记录,类名保持当时事实,未改)。

> 独立调查员产出(2026-09)。需求侧单一源 = `docs/develop/currency_war/redesign/01_strategy_layer.md`(下称 v3 设计)+ `docs/develop/currency_war/comp-selection.md`(下称 comp-sel);供给侧以 `src/sr_od/application/currency_war/{obs,kernel,operations}` 与 `assets/game_data/screen_info/currency_war_*.yml` 实读为准。每行结论带来源;未确证处显式标注。
> 图例:✅ 现成且生产在跑 | 🟡 部分(已建模但有已知缺陷/覆盖不全) | ❌ 无供给。

---

## 1. 需求字段全集(带出处)

### 1.1 备战期基础状态(v3 §2 动作空间、§4.4 经济引擎、§4.5 卖出)

| # | 需求字段 | 出处 |
|---|---|---|
| N1 | 金币 gold(逐轮) | v3 §2/§4.4 金日程 |
| N2 | 等级 level / XP 进度 / 买经验单价 | v3 §2「级」、§4.4 升级决策 |
| N3 | 连胜/连败数(带符号) | v3 §4.4 连胜-息取舍(p43) |
| N4 | 位面 plane / 轮次 round_num | v3 §0 回合结构 |
| N5 | 位面节点序列(剩余节点类型) | v3 §0「P1 九节点…」;换线三触发之「位面边界」 |
| N6 | 当前节点类型(boss/遭遇/补给/奖励…) | v3 §4.7 强敌节点前置加强 |
| N7 | 部署上限 deploy_cap(= level+宝钻) | v3 §4.5 板满门/资源谓词 |
| N8 | bench 占用/满标志(9 槽) | v3 §4.5 囤积判据/bench 槽唯一稀缺([34]) |
| N9 | 刷价 / 概率表(REFRESH_PROB 或画面概率条) | v3 §4.4 刷新决策(p40) |
| N10 | 卖出退金口径 sell_refund | v3 §4.5 卖出价值 |

### 1.2 商店与持有(v3 §2、§4.1 六序、comp-sel §7)

| # | 需求字段 | 出处 |
|---|---|---|
| N11 | 商店 5 槽卡身份(name/faction/cost/star) | v3 §2「买」;comp-sel §7 件级估值 |
| N12 | 升星预览(✦数,已持同名副本印证) | cw_state.ShopCard.merge_preview(W104/ADR-0416;决策可作冗余信号) |
| N13 | 板面前后排角色身份+星级+站位 | v3 §4.8 部署与站位;comp-sel §7 输入轴 |
| N14 | 备战栏身份+星级(槽位) | v3 §4.5;[34] 备战席稀缺性定序 |
| N15 | 持有卡计数(同名同星全场计数) | v3 §4.1 序 5 凑星;merge_buy_k |
| N16 | 羁绊计数 board(全集口径)+ 距下档 | v3 §4.8;comp-sel §7 台阶推进 |
| N17 | 持有装备(owned)+ 穿戴映射(谁穿什么) | v3 §4.6 装备机器;E11 |
| N18 | 工具 7 件持有与数量(冶金炉/扳手/投影仪/令牌/特权卡) | v3 §4.6 回收;E10 |

### 1.3 环境与敌人(v3 §3/§4.2/§4.7)

| # | 需求字段 | 出处 |
|---|---|---|
| N19 | 职级 selected_difficulty(A1..A8-50) | v3 §4.7(难度→成型强度前置) |
| N20 | 敌数值难度 enemy_difficulty(逐轮真值) | v3 §0 战斗事实;判读域 |
| N21 | 位面 boss 序列(3 boss 身份) | v3 §5 MECHANIC_COUNTERS/BOSS 表(环境臂输入) |
| N22 | 敌人词缀列表(逐位面/节点) | v3 §4.2 权重环境分化 |
| N23 | 词缀→效果映射 | v3 §4.2 机制层知识(MECHANIC 表) |
| N24 | 位面特殊修正 plane_modifiers | cw_state 字段;v3 未直接点名(保留项) |
| N25 | HP | **决策层禁止读取**(v3 §4.7 [39]);仅判读域——列此声明供给面不为其建设 |
| N26 | 博弈模式 match_type | v3 §4.9 边界声明(启动配置,局外) |

### 1.4 事件决策面(v3 §4.9 全量目录 E1-E14)

| # | 事件 | 需要的可观测输入 |
|---|---|---|
| E1 | 投资环境三选一 | 三选项名(+效果文案)、已选 active_env |
| E2 | 投资策略三选一(可刷) | 三选项名、剩余刷新次数、已持 active_strategies |
| E3 | 遭遇分支(可刷 1 次) | 各卡难度档+奖励文本、刷新次数 |
| E4 | 补给选择+重刷 | 每列 角色+装备、钻标识、刷新次数 |
| E5 | 圣杯试炼接取(二选一)+生命周期 | 卡 objective/奖励文本、激活等级门槛、任务完成态 |
| E6 | 领航员绑定(姬子·启行) | 绑定 UI 候选、当前绑定对象、换绑时机 |
| E7 | 巨星选择 | 候选角色名 |
| E8 | 星徽/卡带驾驶员 | 获得虚数件事件 + 持有/穿戴态(逻辑推导) |
| E9 | 专家邀请函(五选一) | 候选名单 |
| E10 | 工具使用 | 工具持有计数(N18)+ 使用拖拽 UI |
| E11 | 装备合成配对 | 持有基础件(N17)+ 合成图谱(注册表) |
| E12 | 商店锁 | 锁按钮 UI + 锁状态 |
| E13 | 扑满类奖励节点 | 节点语义改写检测(env 改写) |
| E14 | 开拓者形态 | 部署排位(逻辑推导,无需画面) |

---

## 2. 对表矩阵

### 2.1 基础状态

| 需求 | 供给 | 来源 | 缺口补法 |
|---|---|---|---|
| N1 gold | ✅ | `cw_observation.read_gold_settled`(L148,稳定门)→ `read_game_state` L1606-1608;gold_readable 保真位 | 无 |
| N2 level/XP/单价 | ✅ | `read_level_raw_opt`/`read_xp_progress`/`read_level_up_cost`(cw_observation L299/720/785);三源仲裁 `_resolve_level` L1504(毒化防线);XP 常量 `cw_state.XP_*` L42-44 | 无 |
| N3 streak | 🟡 已知缺陷 | 结算真值 `parse_streak`(cw_settlement_obs L117,带符号,权威)→ session.last_streak;备战 magnitude `read_streak`(cw_observation L837)间歇误读,双源留证 L1735-1753 | 维持结算为主源即可;新层勿消费备战 magnitude |
| N4 plane/round | ✅ | `read_phase_round`(cw_observation L912,缓存+阶段门) | 无 |
| N5 节点序列 | ✅ | `read_node_sequence`(cw_observation L476)+ `cw_node_reader`(Hu 模板分类/圆检测 L198/280);位面详情 `read_plane_detail_nodes` L656;session 台账制 + 三票校验 L1652-1666 | invest-env 改写节点后重读已覆盖(`cw_node_validate.py` 注释 L10-50) |
| N6 node_type | ✅ | 同上台账制(L1661-1666);`gate_node_type` L396 | 无 |
| N7 deploy_cap | ✅ | `read_deploy_cap_debounced`(cw_observation,域外双帧一致采信,cap<level 不再恒拒——level 对照可毒化,见 strategy/05_observation.md);`max_units()` 单点收口(cw_state L265) | 无 |
| N8 bench 满 | ✅ | `read_bench_full`(cw_observation L1485,OCR 警告)+ 定长 9 槽占用数(`bench_is_full` cw_state L287) | 无 |
| N9 刷价/概率表 | ✅(刷价为常量) | 刷价 = `REFRESH_COST_BASE=2`(cw_state L53,ADR-0456:OCR rect 读的是利息徽标,已退链);概率条真值 `read_refresh_probs`(cw_observation L197)→ state.refresh_probs | 无 |
| N10 sell_refund | ✅(机制常量) | `cw_state.sell_refund` L870(cost=1 各星已实测定谳;cost≥2 的 −1 与 3/4 星 🟡 待实机核,L876-878) | 小:多 cost 档实机核对手续费 |

### 2.2 商店与持有

| 需求 | 供给 | 来源 | 缺口补法 |
|---|---|---|---|
| N11 商店 5 槽卡 | ✅ | `read_shop_cards`(cw_observation L1390,含 faction/name/cost/star);画面档 `currency_war_battle_prep_shop_open.yml`(商店牌-1..5);池一致性守卫 `cw_shop_obs.check_shop_pool` L66 | cost OCR miss 时按 3 估(`card_cost` L790)——已知口径,保持 |
| N12 升星预览 | 🟡 | `read_merge_preview`(cw_identity_obs L241,W104/ADR-0416);**0 双义**(真无副本∨读不到,fail-silent,cw_state L117-120 注释) | 新层按「未观测」消费即可,禁否定性决策 |
| N13 板面身份/星级/站位 | ✅ | `read_deployed_chars`(cw_identity_obs L587,SIFT+槽位)+ `read_star`(L125,3★ 全位置断言测试过);tracking + paddle 对齐截断/补齐(read_game_state L1893-1922,ADR-0417) | 残余风险=deploy SIFT 漂移(有 obs_conflict 留证) |
| N14 备战栏 | ✅ | `read_bench_chars`(cw_identity_obs L758);tracked_bench_chars + mutate 维护(shop.py);槽位模型 ADR-0316 | 同上,漂移走对账链 |
| N15 持有计数 | ✅(逻辑推导) | `same_star_count`/`merge_buy_k`/`merge_buy_completes`(cw_state L819-867)——由 tracked bench∪deployed 推导,无画面需求 | 依赖 N13/N14 tracking 质量 |
| N16 board | 🟡 已知缺陷 | 双源仲裁:computed(`board_from_tracked` L1323)底座 + 可视徽章覆写(ADR-0417,L1756-1814);`board_next_tier`(聚焦裁切 OCR,L1381;注册表派生 L1815-1821);`cw_faction_obs.read_displayed_factions` L196 | 左面板滚动截断是结构性漏——computed 兜底已有;非备战帧双不可信留证 |
| N17 装备持有+穿戴 | 🟡 | owned:`read_equip_grid`/`read_equips`(cw_equipment L223/374,SIFT+灰度模板,数量含 ∞ L326-341);穿戴:`read_row_equipped`/`read_equipped_below`(cw_identity_obs L1249/cw_equipment L531);BenchChar.equips 由 tracking 维护。**GameState.equips 注释「阶段 4 接线前默认空」(cw_state L221)**——state 级聚合是否已接线未确证 | 核对 read_game_state 是否回填 state.equips;未回填则补一条 session→state 注入(active_strategies 同款,L1830) |
| N18 工具持有/数量 | 🟡 | 装备区 row1 材料格识别(cw_equipment L262 注释:扳手/炉/投影仪/骰子同格堆叠,右下白字数量 1-5 或 ∞;L229 精密拆装扳手依赖全尺度回扫兜底) | 供给=识别有;**决策消费链无**(见 E10) |

### 2.3 环境与敌人

| 需求 | 供给 | 来源 | 缺口补法 |
|---|---|---|---|
| N19 职级 | ✅ | `read_selected_difficulty`(cw_observation L887,难度确认屏);画面档 `currency_war_difficulty_confirm.yml` | 无 |
| N20 敌数值难度 | 🟡 已知缺陷 | 两级管线 `read_enemy_difficulty`(L765,binarized OCR)+ live 保真位 `enemy_difficulty_live`(cw_state L159);**live=False 帧是简报恒值 ≈108,非爬升真值**(L1707-1714 注释) | 新层消费时必须带 live 位过滤 |
| N21 boss 序列 | ✅ | 简报 `read_bosses`(cw_briefing_obs L116)+ LCS 清名 L155;`collect_plane_intel`(handlers/collect_plane_intel.py,位面详情);`match_boss_sift`(cw_node_reader L111,节点条 boss 身份) | 无(3 位面粒度;节点级 boss 已有 SIFT 通道) |
| N22 词缀列表 | 🟡 | 简报 `read_affixes`(cw_briefing_obs L58)→ session.briefing_affixes → state.enemy_affixes(read_game_state L1869-1870);词缀效果 tooltip 采集 `read_affix_effect` L252 + 注册表回写 L346 | **词缀 OCR 校准 = 设计已登记知识缺口**(v3 §4.9);按位面/按节点的词缀区分粒度未确证(现供给=简报一次性) |
| N23 词缀效果 | ✅ | `cw_briefing_obs.load_affix_effects_from_file` L290 + 采集链(handle_briefing L78-151);静态效果表已采 | 版本更新重采走既有链 |
| N24 plane_modifiers | ❌(字段孤儿) | `cw_state.plane_modifiers` L233——全仓 0 写入 0 读取(grep 仅声明处);注释「§13.9 待核各 plane」 | 若新层消费才建:位面简报/详情屏采集 |
| N25 HP | ✅(仅判读域) | `read_hp_opt` + reconcile_hp 三层(hp/hp_readable/hp_trusted,ADR-0282/0428/0431/0491;cw_state L172-188) | **决策层禁读**(v3 §4.7)——不补不接 |
| N26 match_type | ✅ | `currency_war_mode_select.yml` + start 链;state.match_type(cw_state L232) | 局外配置,不进决策 |

### 2.4 事件决策面(v3 §4.9 落地前提逐项核对)

| 事件 | 供给 | 来源 | 缺口补法 |
|---|---|---|---|
| E1 投资环境 | ✅ | op=`handle_invest_env.py`;识别器 `obs/recognizers/invest_strategy_recognizer.py`(invest_env 同族);选项喂 `decide_invest(kind="env")`(cw_strategy L131);注册表 `cw_investments.get_env`;画面档 `currency_war_invest_env.yml`;采集 `operations/tools/harvest_invest_codex.py` | 无 |
| E2 投资策略 | ✅ | op=`handle_invest_strategy.py`;写 session.active_strategies(read_game_state L1830-1831 注入 state);`decide_invest(kind="strategy")` | 刷新次数 OCR:PickEvent.refresh 建议链已有(ADR-0146,handler 读「刷新次数N」,cw_state L572-586)——具体 reader 实现未逐行核,标未确证 |
| E3 遭遇分支 | ✅ | `read_encounter_options`(cw_node_obs L35:难度档其X+奖励带;**「其一」OCR 漏读默认 1** 已知缺陷 L26-28);op=`handle_encounter.py`;`decide_encounter`;画面档 `currency_war_encounter.yml` | 词缀分支 N/A(UI 不显,reader 注释 L38)——设计侧已知 |
| E4 补给选择 | 🟡 | `read_supply_options`(cw_node_obs L161:动态列数、角色+装备、SIFT 钻识别双通道实测对拍);op=`run_supply_node.py`;`decide_supply`;画面档 `currency_war_supply.yml` | **重刷(1 次)缺口**:reader 注释明言「无刷新按钮…refresh_used=True 跳过刷新逻辑」(L167)——与 v3 §4.9 E4「补给选择+重刷(1 次)」冲突;实机核补给屏是否真有刷新入口,有则补建档+op |
| E5 圣杯试炼 | 🟡 | 选择面 ✅:`handle_wish_trial.py`(卡 OCR→`decide_wish_trial` decision_v2/strategy.py L647)+ 画面档 `currency_war_wish_trial.yml`(祈愿试炼=命运圣杯绑定,doc L11);**生命周期 ❌**:任务条件检测/激活等级门槛/完成态/完成后可卖——v3 §4.9 知识缺口自认(L164),无任何 reader | 必须补:任务进度可观测性(备战屏任务区建档)+ 数据枚举采集 |
| E6 领航员绑定 | 🟡 未确证 | `handle_select_partner.py`(开局伙伴五选一?SIFT 立绘 r104,写 session.chosen_partner L146;`decide_partner`)+ 画面档 `currency_war_partner.yml`;cw_comps 特殊系统键 'navigator'(L138)仅知识位 | 「姬子·启行上场触发换绑 UI」与开局伙伴是否同一交互面**未确证**——需实机核;若独立 UI 则全缺(无档无 op) |
| E7 巨星选择 | ✅ | `read_megastar_options`(cw_node_obs L82,「盛会之星一X先生/女士!」正则实测);op=`run_megastar_node.py`;`decide_megastar`;画面档 `currency_war_megastar.yml`;session.chosen_megastar→state.megastar_char(L1871-1873) | 无 |
| E8 星徽/卡带驾驶员 | ✅(逻辑推导) | 虚数件识别在装备注册表(cw_equipment_data)+ P19 计数语义(`cw_bond_equips.unit_bond_tags`);驾驶员=部署决策,无独立 UI 需求 | 无(归部署机器) |
| E9 专家邀请函 | ✅ | `handle_bookcard.py`(书册卡五选一,2026-08-30 实机建档后落码;cw_identity_obs L797/L914)+ `decide_box_card`(decision_v2/strategy.py L685);`find_bookcards`(cw_identity_obs L967) | 无 |
| E10 工具使用 | 🟡→❌(决策面) | 持有观测见 N18;**使用侧 ❌**:`equip_all.py` L51/L751-754 明言「工具类(拆装扳手/冶金炉等)非 drag 穿…**冶金炉/扳手从不进决策快照(owned 恒空实证,run 26)**」 | 必须补:工具→目标拖拽 op(冶金炉/投影仪/令牌/扳手各有目标语义)+ 使用决策钩子;P14/p42 数学件先行 |
| E11 装备合成配对 | 🟡 | 穿戴/转移 ✅:`equip_all.py`(drag 穿,A/B 双套)+ `handle_equip_pick.py`(三选一);合成图谱 `cw_synthesis.py`(生成自 plaza);「穿着即合成」由游戏执行。合成**配对决策**的独立供给面未确证(未见显式「选两件合」op;依赖穿着即合的推导链) | 核对:目标线组件需求向量→穿序即配对决策,大概率纯逻辑推导无需新画面;有独立配对 UI 才补 |
| E12 商店锁 | ❌ | `cw_state.shop_locked` L234——**全仓唯一出现**(0 写 0 读);`currency_war_battle_prep_shop_open.yml` 无锁按钮 area(实读:仅 收起/牌1-5/刷新/概率表) | 必须补:锁按钮建档(battle_prep_shop_open 或独立子态)+ 锁状态识别 + ToggleLock op + 决策钩子(期权口径 p38 O3) |
| E13 扑满类奖励节点 | 🟡 | 节点语义改写检测:node_type 台账制 + invest-env 后重读(read_game_state L1652-1666;`cw_node_validate.py` special_env_evidence L55);「扑满」作为特定改写语义未单独建模 | 可延后:依赖 E1 环境采集覆盖率;扑满节点出现时的专项建档 |
| E14 开拓者形态 | ✅(逻辑推导) | 形态按排归一已在 SwapDeploy/DeployMove 语义内(cw_state L645-648 注释「开拓者按目标排做形态归一」);cw_chars 形态注册 | 无(归部署机器) |

---

## 3. 缺口清单(两级)

### 必须补(决策层第一版就消费)

1. **E12 商店锁**:全链无供给(orphan 字段 + 无建档 + 无 op)。v3 §4.9 E12 是第一版全量事件面(用户裁定 2026-08-31「必须全部」)——锁按钮建档、状态识别、op、决策钩子四件全缺。
2. **E10 工具使用决策面**:持有识别有(N18)但「从不进决策快照(owned 恒空实证)」(equip_all.py L751-754)。冶金炉/扳手/投影仪/令牌/特权卡的拖拽使用 op 全缺;v3 §4.6/E10 点名(投影仪=买牌替代/令牌=唯一定向装备获取)。
3. **E5 圣杯试炼生命周期**:选择面现成,任务条件检测/激活门槛/完成态零供给(设计 §4.9 知识缺口自认)。E5 决策机制(奖励偏好序+门槛检查+完成后件可卖)全部依赖它。
4. **N17 state 级装备聚合接线核对**:GameState.equips 注释「阶段 4 接线前默认空」——若 read_game_state 未回填,新层拿不到持有装备全集(与 active_strategies 同款 session→state 注入即可,小改)。

### 可延后

5. **N22 词缀按节点粒度**:现供给=简报一次性(位面级);新设计权重环境分化若只需位面级则够,需节点级再补。
6. **N24 plane_modifiers**:orphan 字段,无消费方;新层不点名则删或维持。
7. **E4 补给重刷**:reader 断言无刷新按钮,与设计冲突——实机核一次,有则小补。
8. **E6 领航员换绑 UI 独立性**:未确证是否独立于开局伙伴面;实机核。
9. **E13 扑满专项语义**:靠环境采集覆盖,出现再做。
10. **N10 sell_refund cost≥2 手续费实机核**(cw_state L876-878 🟡)。
11. **E2 刷新次数 reader 实现核对**(ADR-0146 声称 handler 读「刷新次数N」,reader 未逐行核,未确证)。

---

## 4. 事件面可观测性专节(v3 §4.9 十四项落地前提)

| # | screen_info 建档 | ops/handler | 决策钩子(decide_*) | 选项 reader |
|---|---|---|---|---|
| E1 | ✅ invest_env.yml | ✅ handle_invest_env | ✅ decide_invest | ✅(recognizer) |
| E2 | ✅ invest_strategy.yml | ✅ handle_invest_strategy | ✅ decide_invest | ✅(recognizer) |
| E3 | ✅ encounter.yml | ✅ handle_encounter | ✅ decide_encounter | ✅ read_encounter_options |
| E4 | ✅ supply.yml | ✅ run_supply_node | ✅ decide_supply | ✅ read_supply_options(重刷❌) |
| E5 | ✅ wish_trial.yml | ✅ handle_wish_trial | ✅ decide_wish_trial | ✅(OCR 卡文案);生命周期❌ |
| E6 | 🟡 partner.yml(开局面) | 🟡 handle_select_partner | ✅ decide_partner | ✅(SIFT 立绘);换绑面未确证 |
| E7 | ✅ megastar.yml | ✅ run_megastar_node | ✅ decide_megastar | ✅ read_megastar_options |
| E8 | —(无独立 UI) | —(归装备/部署) | 归部署 | 逻辑推导 |
| E9 | ✅(书册卡模板,cw_identity_obs L914) | ✅ handle_bookcard | ✅ decide_box_card | ✅ find_bookcards |
| E10 | 🟡(工具在装备格 N18) | ❌(equip_all 显式滤除) | ❌ | 🟡 持有有、使用无 |
| E11 | ✅ equip 相关(equip_float/equip_detail/armory_box_dialog) | 🟡 equip_all/handle_equip_pick | 🟡(穿序即配对,推导) | 🟡 |
| E12 | ❌ | ❌ | ❌(PickEvent 无锁语义) | ❌ |
| E13 | 🟡(通用节点链) | 🟡(node 台账+env 重读) | ❌(无专项) | 🟡 |
| E14 | — | ✅(deploy 形态归一) | 归部署 | 逻辑推导 |

另有长尾 overlay 已建 handler(设计 §4.9 外但同域):命运卜者强化三选一(`handle_fortune_picker.py`)、银狼策划事件(`handle_planner_event.py` + `decide_planner`)、星之书(`decide_star_tome` + `star_tome_popup.yml`)、选择装备三选一(`handle_equip_pick.py`)、简易武装箱弹窗(`handle_armory_box.py`)、奖励球/补给箱(`handle_reward_sphere.py`/`handle_supply_box.py`)、部署未满确认(`handle_deploy_not_full.yml`)、消耗品详情浮层 ESC(battle_loop.py L996)。**事件面骨架(选择→策略→确认)已产品化**,硬缺口集中在 E12 锁、E10 工具使用、E5 生命周期三处。

---

## 5. 数据质量已知坑(读数缺陷,消费前必看)

| 坑 | 出处 | 消费纪律 |
|---|---|---|
| hp 读不到 ≠ 漂移:None 化政策(禁 100 兜底)、readable/trusted 双位、帧龄门 | cw_state L172-188(ADR-0282/0428/0431/0491);cw_observation L1609-1651 | 决策层按 [39] 干脆不读;判读域按位过滤 |
| enemy_difficulty live=False 帧是简报恒值 ≈108 | cw_state L155-159;cw_observation L1707-1714(批㉖ F1/ADR-0449) | live=False 帧禁当「难度 vs 轮次」样本 |
| 刷价 OCR rect 读的是利息徽标(min(gold//10,5))非刷价 | cw_state L46-53(ADR-0456) | 恒用 REFRESH_COST_BASE 常量 |
| streak 备战 magnitude 间歇误读;结算带符号才权威 | cw_observation L1735-1753 | 主源 session.last_streak |
| level OCR+XP 双失读时启发式兜底会毒化 last_level_obs(乒乓) | cw_observation L1669-1696(2026-08-18 治本) | 走 _resolve_level 仲裁,勿旁路写 session |
| board 左面板滚动截断;非备战帧徽章与 computed 双不可信 | cw_observation L1756-1814(ADR-0417) | computed 底座 + 备战帧徽章覆写;非备战帧留证 |
| deployed 对齐:tracked vs paddle 分歧静默截断毒化 | cw_observation L1893-1922 | 已有 obs_conflict 留证;频发 >10 行/时排查 SIFT 漂移 |
| deploy SIFT 漂移曾致「预估 2★ 读回 1★」两度停机 | cw_state `_merge_bench` L730-737(r17 实证) | 合并域=全场(bench∪deployed),tracking 必须同口径 |
| 遭遇「其一」笔画细 OCR 漏读 → 默认难度 1 | cw_node_obs L26-28 | 易卡难度恒 1 兜底,已核 baseline |
| merge_preview=0 双义(真无副本 ∨ fail-silent) | cw_state L117-120 | 按「未观测」消费,禁否定性决策 |
| 商店牌 cost miss 按 3 估 | cw_state `card_cost` L790-792 | 已知保守口径 |
| 补给双装备行曾整行漏读(y 带已放宽修) | cw_node_obs L104-110 | 布局变异敏感,改动需回归 66 帧存档 |
| 装备 owned 顺序异常/布局双形态 | cw_equipment `_owned_order_anomaly` L454、cw_obs_core L105 | 穿戴真值锚只在角色详情大面板 |
| 工具不进决策快照(owned 恒空实证) | equip_all.py L751-754(run 26) | E10 补供给前别假设能读到工具持有进决策 |
| gold==0 可能是动画帧 miss(稳定门+重读) | cw_observe_full docstring L48-50;cw_observation L1603-1605 | 消费 gold_readable |
| 特效 overlay(盛会之星/圣杯/银狼升级)遮挡 heavy 观察 | prep_director.py L1202 | heavy 读要等特效帧过 |

---

## 6. 结论摘要

- **备战期状态(N1-N16)**:供给面成熟,识别/对账/保真位体系完整,新决策层可直接消费;主要纪律=带 readable/live 位消费、不旁路仲裁链。
- **事件面(E1-E14)**:十四项中 9 项✅、3 项🟡、**2 项硬缺(E12 商店锁全链、E10 工具使用决策链)**,E5 生命周期是第三个必须补块。第一版全量事件覆盖(用户裁定)的落地瓶颈=这三处。
- **孤儿字段**:shop_locked、plane_modifiers(cw_state 声明后 0 写 0 读)——新层消费前先补写链,否则是假供给。
- 未确证项已随行标注(E2 刷新次数 reader、E6 换绑面独立性、E11 配对 UI、N17 state 回填),建议实施批前逐一实机核。
