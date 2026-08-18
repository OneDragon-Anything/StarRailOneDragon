# 03 阵容规划层(战略层,A2,待做)

> 总见 [README](README.md)。auto-chess 的胜负手是「commit 哪个阵容 + 何时转型 + 巨星绑谁」。当前战术层只 reactive 加深领先 → 锁死低上限阵容。A2 加战略层。
> **review r1(方案)修正**:target_progress 去三重奖励(正确性-1)、comp_score 给显式公式(可实施性-1)、转型改比较型信号(正确性-4)、转型分阶段(正确性-5)、加巨星选择(完整性-2)、Comp 加转型字段(可实施性-2)、~~邪道阵容~~(**2026-08-03 反转:邪道非必需**)。

## 阵容库(comp library,meta 数据)

```
@dataclass
class LevelGoal:
    """某玩家等级该做什么(成型路线的一站;曲线随 COMP_LIBRARY 填,框架先定 —— 用户选 B)。"""
    action: str            # "level_up"(攒金升下一级,解锁更高费刷新率)/ "roll"(D 找核心)/ "stable"(稳住吃息)
    target_cost: int = 0   # roll 时重点找几费核心(0=不限;随等级升:前期1费/中期4费/后期5费)
    target_chars: list[str] = field(default_factory=list)   # 这级该找谁(core_chars 子集)
    star_goals: dict[str, int] = field(default_factory=dict)  # 角色名 → 目标星级(如 1费→3星、5费→2星)

@dataclass
class Comp:
    name: str                    # "追击飞霄"/"昼神阿雅"/"银枝群攻"/"万敌单C"(roster 见 cw_comps.COMP_LIBRARY 注册表(旧 data doc 已删))
    factions: list[str]          # 核心阵营组合 ["仙舟","追击"]
    core_chars: list[str]        # 核心角色(名)["青雀","知更鸟","昔涟"]
    form_tiers: dict[str,int]    # 成型 tier 目标 {"仙舟":7,"追击":5}
    strength: str                # S/A/B(**综合强度**,版本强度;2026-08-03:不标"邪道专打 A8" —— 邪道非必需)
    form_difficulty: str         # easy/medium/hard 成型难度(用户强调:成型难度是关键维度;物质分解液/反甲等难凑的标 hard)
    level_plan: dict[int, LevelGoal]  # **成型路线**(玩家等级 → 该等级做什么);驱动战术层花超额金(详下"经济统一论")
    key_equips: list[str]        # 关键装备 ["反重力皮靴"](详 07)
    countered_by_bosses: list[str]     # 克制这阵容的 boss/词缀 ["电视机"]
    affix_preference: list[str]  # 适合/避开的敌人词缀
    shared_chars: list[str]      # 与其他 comp 共享的 core(转型可复用)
    transition_chars: list[str]  # 早期打工牌(银河学者/夜之半神等,后期卖)
    typical_form_round: int      # 大致成型所需轮次(level_plan 的粗估汇总)
    version_tag: str             # "V4.4"(版本维护用,风险-2)
```

## 经济统一论:level_plan 驱动战术花超额金(2026-08-03 用户框架)

**用户洞察**:D 牌 / 买牌 / 买经验都是**经济(花钱)的一环**,不是三件事。方法论:
1. **维持 ≥50 金**(利息引擎,每回合白拿 5 金)—— 钱不到 50 先攒(`_maybe_sell_for_interest` 凑息)。
2. **超出 50 的钱"免费"**(不再生息)→ **该花**,花在哪由 **target_comp.level_plan[当前等级]** 决定:
   - `action=level_up` → 攒金升下一级(解锁更高费刷新率,为找高费核心铺路)。
   - `action=roll` → D 牌找 `target_cost` 费核心 / `target_chars`,按 `star_goals` 判断到没到位。
   - `action=stable` → 稳住吃息,不主动花。
3. **tempo 例外**:连胜/连败 streak(额外金)、HP 危险、战力断档 → 可**破息**(花到 50 以下)抢节奏。

**与战术层接法(02,2026-08-04 已落地)**:`plan()` 中 level_plan `level_up` + afford → **硬 gate 执行 LevelUp**(D-14,非纯贪心 eval delta);`target_comp=None` 时退化为通用曲线 `_DEFAULT_LEVEL_GOAL`。`select_comp`/`maybe_pivot`(cw_comps)选 target,shop.py 接线传 `_target_comp` 给 plan()。具体 level_plan 曲线:comp 自带优先,无则通用曲线兜底。
通用曲线(research 已有):前期 4-5 级 roll 找 1 费 / 中期升 7 roll 找 4 费、2-6 回合升 8 / 后期升 8-9 找 5 费 + 关键卡追 3 星。**完整刷新概率表 Lv1-10(bwiki 🟢,level_plan 硬地基)+ 节点×等级×动作骨架 + 骨架/参数分离论点见 [14 阶段节奏骨架](14_phase_skeleton.md)**(2026-08-09 调研 D-21)。
来源:research meta 阵容表 + cw_data + **用户实战补充**。meta(版本依赖),做成 config 可热更。起步 ~6-10 套:追击飞霄/昼神阿雅/银枝群攻/击破流萤/欢愉/列车同行/物质分解液/反甲反震(**2026-08-03:不标"邪道 A8 专项" —— 邪道非必需,这些只是可选的强阵容之一,成型难度各异**)。**用户认同方向**:攻略 + 实战定义足够多优秀阵容,多维打分(强度 + 成型难度 + boss 契合 + 装备契合),运行时按场面灵活选易成型又够强的。

## comp_score(显式公式,可实施性-1)

```
comp_score(comp, state, bosses, envs_chosen) =
    w_prog * progress(comp, state)
  + w_boss * boss_fit(comp, bosses)
  + w_env  * env_fit(comp, envs_chosen)
  + w_str  * strength_base(comp)
  - w_weak * countered_by_bosses_penalty(comp, bosses)

progress(comp, state) =                                 # 归一化 0..1
    0.6 * Σ_f (min(board[f], form_tiers[f]) / form_tiers[f]) / len(factions)   # 阵营 tier 进度
  + 0.4 * Σ_c (c in owned_chars(state)) / len(core_chars)                      # 核心角色持有

boss_fit(comp, bosses) = 1 - countered_by_bosses_penalty(comp, bosses)              # boss 克制(命中 weakness 降分)
env_fit(comp, envs) = 1 if comp.factions ∩ envs 概念股/邀请对应阵营 else 0.5    # 投资环境契合
strength_base(comp) = research meta 强度先验(S/A/B → 分)
```
**权重值不写进文档**(单一源 = `cw_comps` 的 `W_PROG/W_MECH/W_ENV/W_BOSS/W_EQUIP/W_STR`;阶段 6 实机校准)。设计原则:**progress 主导 + 可成型优先**(D-17:W_PROG↑/W_STR↓,解 select_comp 锁高强度不可成型 comp)。

`select_comp(state, config, bosses, envs)` = argmax comp_score over COMP_LIBRARY。**备选几套(N≈2-3)不冲突流派**(optionality,详下"select_comp 频率"+ P1-1),核心到了 commit 1 + 留 1 pivot。

## target_progress_score(去三重奖励,正确性-1)

**问题(r1)**:evaluate 已有 synergy_score(faction tier)+ char_quality(character_priority)。若 target_progress 再奖 core_char 持有 + faction 推进,一个 core_char 被三重计分 → eval 扭曲(过度买 core 破坏经济)。

**修法**:target_progress **只度量「距离 form_tiers 的剩余进度」**,不重复 synergy/char_quality 已奖的:
```
target_progress_score(state, target_comp) =
    WP * Σ_f max(0, form_tiers[f] - board[f]) / form_tiers[f]   # 剩余进度(越接近 0 越好 → 取负向贡献)
# 即:- WP * (剩余进度比例)。已成型(factions 都达 form_tiers)→ 0;完全没起步 → -WP。
# core_chars 持有**不在此重复计分**(char_quality 已覆盖);仅作 character_priority 动态补充:
#   若 core_char ∉ config.character_priority,evaluate 时把它临时并入(低权,≤ CHAR_PRIORITY_BONUS/2)。
```
WP(target_progress 权重,见 `TARGET_PROGRESS_WEIGHT` 代码,待校准;不在文档写值)。这样 core_char 的总分 = synergy(tier)+ char_quality(若 priority)+ target_progress 的进度推进(买它让剩余进度↓),**不三重**。

## 巨星选择(select_megastar,完整性-2)

盛会之星羁绊的核心决策:选 1 名盛会之星作巨星,不同巨星给全队不同 buff(factions.md:花火=战技点+普攻战技增伤、星期日=前后台强度、知更鸟=幸运一击、黑天鹅=5费增伤...)。

`select_megastar(state, target_comp) → char`:
- 若 target_comp.core_chars 含盛会之星角色 → 巨星绑该角色(如「知更鸟 comp」→ 知更鸟给幸运一击)。
- 否则按 buff 契合 target_comp:物理/前后台强度队→星期日;击破队→大丽花;多 5 费→黑天鹅。
- battle_loop 的「确认选择」分支(当前 naive 点左)改调此函数。

## 掉血归因(观测驱动决策框架,2026-08-11 用户)

COMP_LIBRARY 收录即**强度可信**(先验),观测**不推翻阵容选择**,只判**投资方向**。掉血按**成型度(form_progress)**三分:

| 状态 | 掉血含义 | 动作 |
|---|---|---|
| 成型中(form_progress 低) | 核心没凑齐 | **继续组建**(补过渡 / 通用辅助支撑,别掉太多血) |
| 成型后(form_progress 高) | **装备 / 星级不够**(阵容本身可信) | **花钱补强**(升星 / 穿装备),**不转型** |
| 凑不齐(核心不来 / ceiling 不可达) | 这套组建不了 | **转方向**(pivot,见下) |

→ **pivot 只服务"凑不齐"**,不用来"成型后掉血就换阵容"。comp_viability 观测的用途是判"继续组建 / 补强 / 转方向",不是简单"掉血→转"。

## 转型(pivot,比较型信号 + 分阶段,正确性-4/5)

**转型信号(比较型,删「N 回合无推进」)**:
1. **更优 comp 涌现**:存在 comp B,`comp_score(B)` 持续 > `comp_score(target)` 超阈值且差距扩大(连续 2 回合)。
2. **ceiling 不可达**:target 的 form_tiers 所需轮次 > 剩余轮次(typical_form_round 估算)。**已成型(form_progress=1.0)豁免** —— 不切走已完成 comp(D-33)。
3. **保命转型(仅未成型)**:hp 压力大 **且 target 未成型**(form_progress 低、凑不齐、靠它成型前会死)→ 切成型最快的 comp(低 typical_form_round)。**已成型 comp 掉血不转**(见上「掉血归因」:成型后掉血 = 装备/星级不够 → 花钱补强,不换阵容)。

**转型实现(分阶段,正确性-5)**:
- **阶段 2(当前)启发式**:转型触发 → 切 target_comp;eval 改用新 target;战术层贪心自然开始买新 comp 牌;**卖旧 comp 的 transition_chars + 非共享 core**(规则化,_bench_sell_value 已保留通用 + 接近推层,转型时旧 comp 牌不再是「接近推层」→ 可卖)。转型成本用**规则估算**(transition_chars 卖出回金 vs 新 comp 典型成型轮次),**不用多步搜索**。
- **阶段 3+ 多步搜索**:A1 加深为 2-3 步蒙特卡洛后,「卖旧→腾位→买新→deploy」链的期望 eval 可算 → 转型收益精确化。

**接口**:`maybe_pivot(state, target_comp, config) → Comp | None`(返回新 target 或 None 不转)。

**select_comp 频率 + 多套备选(2026-08-03 用户)**:**每回合跑**(不是每位面)—— 投资策略/环境选择在位面中进行 + 商店强随机,需每回合响应场面变化。**同时备选几套(N≈2-3)候选 comp(optionality,详 round3 P1-1)**:只要**不影响经济**(不为保选项乱买),保持几套可行 comp 的 shared_chars,看**哪个核心先到**再 commit 该 comp + 留 1 个 pivot 备选(早保持灵活、核心来了承诺)。**已知 tradeoff(r6)**:持多套时观测难归因到具体 comp(掉血不知算谁的),**commit 后 comp_tag 才清晰** —— 靠"核心到了尽早 commit"平衡用户"几套备选"和"观测驱动"。配合 F-3 的 α(t):早期保几套选项,核心到了(commit 信号 α 升)收敛到 commit1+pivot1。

## 与战术层接口

`evaluate(state, config, faction_priority, target_comp=None)`:
- target_comp 给定:加 `target_progress_score`(剩余进度,去三重)+ core_chars 动态并入 character_priority(低权)。
- target_comp=None:退化为 synergy + ceiling + 加深领先(r1/r2 已实现)。

`plan` 不变(硬门 + 贪心 + 蒙特卡洛 D 牌),evaluate 多 target_progress 项 → 动作导向 target。

## 数据需求(游戏边界)
- COMP_LIBRARY:meta,纯逻辑可建(research/cw_data 起步)。**非游戏**。
- bosses + 敌人词缀:OCR(开局简报 + A8 词缀)。**需游戏**。
- 投资环境/策略已选:bot 跟踪。**非游戏**。

## 测试(纯逻辑)
- mock COMP_LIBRARY + states → select_comp 选对(boss 克制降分、进度高的优先、成型难度按场面权衡:早期/穷 → 偏 easy 成型)。
- 转型信号:更优 comp 涌现 / ceiling 不可达(已成型豁免 D-33)/ hp<0.75×effective_hp_threshold(D-18/D-32)→ pivot。
- target_progress:去三重(core_char 总分 = synergy+char_quality+进度,不重复)。
- select_megastar:target.core_chars 含盛会之星 → 绑该角色。

## 版本维护(风险-2)
COMP_LIBRARY 加 version_tag;README checklist:版本更新 → 重抓 cw_data → 核对 factions/characters 变化 → 更新 comp strength/core_chars → 回归测试。COMP_LIBRARY 滞后 = 已知风险,target_comp=None 的 reactive 降级兜底。

## round 2 补充(新发掘)
- **R2-3 攻略推荐作 select_comp 先验(high,详 09)**:gameplay 确认游戏自带"攻略"实时给 comp 推荐(高亮角色+推荐装备),**跨版本有效**(game 自更新)。select_comp 把 `read_game_guide()→recommended_comp` 作**先验/运行时校准**:COMP_LIBRARY 为先验、攻略为校准;**版本过期(version_tag 不匹配)时攻略接管**(R2-12 staleness 运行时解)。攻略高亮角色也作 character_priority 动态补充。
- **R2-12 COMP_LIBRARY 运行时 staleness(med)**:version_check(game 内版本号 vs version_tag)→ 不匹配 select_comp 权重 ×0.5 混 reactive + 日志 warn;config 加 `trust_comp_library: float`。与 R2-3 攻略互补。
- **R2-9 env_fit 显式表(med)**:comp_score 的 env_fit 缺 env→faction 可执行映射。`ENV_FACTION_MAP: dict[env_name, list[faction]]` **已从 `INVESTMENT_ENVS` 派生(`cw_comps.py`,单一真相源;概念股/邀请/命运圣杯的 faction 字段)**;非映射 env(契约/时代/经济/规则/专家)目前走 0.5 中性,待分类建模(阶段 3a)。
- **R2-10 站位阵型(med)**:position_pref 只有 front/back,无列内排序/阵型。research"A8 谁吃第一击关乎生存"。Comp 加 `formation: dict[slot, role_requirement]`(如前排 slot1=存护);DeployMove 带 slot;`_pick_deploy_row` 升级 `_pick_deploy_slot`(主坦放前排首位等)。
- **R2-19 comp_score vs target_progress core_char 口径(low)**:comp_score.progress 用 0.4·core_char;target_progress 显式排除 core_char。分层:选 target 时算 core_char(评估契合),eval 驱动买牌时不算(避免三重)。注释清楚即可。

## round 3 补充(根本盲点:P1)
- **P1-1 optionality / 灵活性(high,详 02)**:eval 只奖励 commit(向 target 推进),不奖励灵活性。A8 是方差生存战 —— 过早 commit 单一高 ceiling comp,遇克制/miss 关键牌 = 直接死。加 `optionality_score`:bench 角色同时属于 ≥2 可行 comp(用 `shared_chars` 反查)→ 正分;holding transition_chars → 正分;过早卖 shared_chars → 扣分。select_comp 也保留 top-2 并行(不只选 1)。这是"承诺 vs 期权"的权衡,auto-chess 高手核心直觉。
- **P1-2 env→comp 亲和度矩阵(high,R2-9 升级)**:env_fit 二值(0.5/1.0)远不够。research §10.3"投资环境是 run 内最大单一决策" —— 拿到"昼之半神概念股"(送阿雅+鞋+刷新率)应让 select_comp **近乎硬绑昼神 comp**,权重碾压一切。升级为 `ENV_COMP_AFFINITY: dict[env_name, dict[comp_name, float]]`(每个 T0 env → 1-2 个 comp 大权重)。优先级 high(select_comp 地基;~~凹开局~~已删,不再依赖此判断好坏开局)。
- **P1-3 阵型 slot 级(high,R2-10 升级)**:research"A8 谁吃第一击关乎生存";反甲/反震类 comp **强度靠阵型**(坦克站前排吃伤触发反伤)。Comp 加 `formation: dict[slot, role_requirement]`(前排 slot1=存护/主坦);DeployMove 带 slot 索引;`_pick_deploy_row` → `_pick_deploy_slot`(主坦放前排首位、辅奶盾放 9-10 位)。不建阵型 = 这类靠阵型触发机制的 comp 评级是空的。
- **P0-1 → 观测驱动整合(2026-08-03 修订,详 10)**:comp_score 的 ground term 不用 `battle_predictor` 的 win_prob(精确战斗 sim 不可维护),改用 `comp_viability(state, target_comp, plane, tracker)`(评 **current target**:先验 + `perf_on_node_type` 观测)。`comp_score += w_battle * comp_viability(...)`。仍是"不只是 synergy 分"的 grounding,但 grounding 来自**观测结果 + 粗先验**,不是预测模型。**注意拆分(r5)**:评 **current target**(pivot/eval)用 `comp_viability`(含观测);评 **candidate comp**(select_comp,未 deploy 过)用 `comp_prior`(纯先验,无观测 —— 用已 commit 阵容的观测评未 commit 的 candidate 是逻辑错位)。

## round 4 补充(自洽性)
- **F-5 select_comp vs 观测签名(2026-08-03 修订;r5 拆双签名)**:原问题"select_comp 开局无当前 enemy / deployed 是打工牌 → battle_predictor(deployed, enemy) 对不上"在砍掉精确预测器后消解。但 review r5 发现新错位:**观测是已 commit 阵容的,不能评未 deploy 的 candidate**。故拆两签名(详 10):
  - `comp_prior(candidate_comp, state, plane)` → **select_comp 评分 candidate 用**(纯先验 4 项:成型进度 + 核心角色持有 + 关键装备 + research meta 强度,**无观测**)。
  - `comp_viability(current_comp, state, plane, tracker)` → **pivot / eval 评 current target 用**(先验 + `perf_on_node_type` 观测)。
  - 职责清晰:candidate 无观测(没打过),current 有观测(打过几关)。
- **F-3 optionality 时间衰减(HIGH)**:eval 中 target_progress 与 optionality 用 α(t) 平衡(详 02 round4 F-3),早灵活晚承诺。select_comp **备选几套(N≈2-3)直到核心到来**(2026-08-03 用户:几套备选不影响经济);核心到了(commit 信号 α 升)收敛到 **commit 1 + pivot 1**。optionality 限定**通用角色(≥2 comp)**,与 commit(pivot 粘性)正交不矛盾(ADR 0096)。
- **F-13 target_progress vs optionality shared_char 双重计分(LOW)**:shared_char 同时属 target + ≥2 其他 comp。optionality 只对"非 target 的可转型路径"计分(target 贡献由 target_progress 覆盖);或声明"两个分都拿是 intended"(既推进又保灵活)。注释清楚。

## round 5 补充(2026-08-06 第二轮调研驱动;why 见 decisions D-73)

> 第二轮 V4.4/V4.5 深度调研完成,知识库在 `.debug/temp/currency_war/strategy_research/`(分主题:01 阵容meta/02 角色/03 装备/04 经济/05 投资/06 boss词缀/07 节点伙伴A850/08 缺口与建议)。下文只列**对阵容规划层的设计影响**,细节查 research。

- **R5-1 列车同行 = 姬子·启行护盾反震流(V4.4 meta 顶层,用户确认)**:COMP_LIBRARY 的「列车同行」comp core_chars 以 **姬子·启行**(4费)+ 三月七(护盾)为核心;key_equips = 冷笑话引擎+火力风暴潮+高周频电锯+掩体生成枪(反震四件套);成型易-中(7-8级,9人口更优);**countered_by_bosses/affix_preference 必加「正当防卫」**(反伤词缀克反震,遇则必败 → 遭遇节点必刷新避开,见 06)。
- **R5-2 COMP_LIBRARY 补缺阵容**(每阵容带 form_difficulty/key_equips/countered_by_bosses,数据查 research/01):
  - **命运圣杯流**(Fate 联动,联动后 T0;core Archer+远坂凛+吉尔伽美什+Saber+星徽;form_difficulty=hard,4 个 5 费;**联动前投影不能升星**;祈愿试炼任务期不能拆羁绊)。
  - **欢愉队**(高配 T0;core 银狼LV.999 狼尊+爻光(不可替代)+火花+藿藿;form_difficulty=hard,双 5 费双 3 星)。
  - **万敌单C**(form_difficulty=easy,7 级成型,NGA 认 A8 最简单)。
  - **减益黄泉**(配千冶·刃 V4.4 质变;form_difficulty=medium-hard)。
- **R5-3 新角色 + 命运圣杯阵营**:`CHARACTER_ROSTER` 补 千冶·刃/姬子·启行(注意与原姬子区分)/远坂凛/吉尔伽美什/Archer/Saber/银狼LV.999/爻光/火花/绯英(费用+阵营+站位);`FACTIONS` 补 **命运圣杯**(唯一经济+战斗双修羁绊,激活祈愿试炼)。进了商店 OCR 才识别。
- **R5-4 词缀对策进 comp 评分**(详 research/06):`AFFIX_MECHANIC_MAP`+`MECHANIC_COUNTERS/SYNERGIES` 补全 + comp.countered_by_bosses/affix_preference 体现:**正当防卫→克高频/反震/反甲**(阿雅/姬子反震/白厄/欢愉)、**同步行动→克拉条但利 DOT**、**沉重脚步→刚需护盾**、急速制冷→需解控、重症难题→克奶盾。遇未 OCR 词缀落库,不硬编码全集。
- **R5-5 概念股送装备件 = 凹开局/选环境新维度**(详 research/03):每个概念股送的基础装备 = 该阵营核心装备合成件(昼神/追击送轮滑鞋→反重力皮靴;仙舟送折叠小刀→高周频电锯;列车送幸运星)。`decide_invest(kind="env")` 在 env/strategy priority 打分(旧 event_whitelist 已删,ADR-0204,拆成 env+strategy priority)上加一层:**优先选与 target_comp 核心装备合成件匹配的概念股**(补强 P1-2 ENV_COMP_AFFINITY,从「阵营亲和」细化到「装备件亲和」)。
- **R5-6 装备合成配方**(详 research/03,落 `cw_equipment`):基础件×2→进阶配方表(反重力皮靴=轮滑鞋×2;高周频电锯=幸运星+折叠小刀;永动机=光能电池×2…)。comp.key_equips 用规范名;equip_fit/supply 选装备据此。
- **R5-7 商店保底机制进 D 牌逻辑**:每第 5 次刷新必出 5 张同费(采购专员·彩每 5/·金每 7 缩短)。`_refresh_cap`/`_refresh_expected_delta` 建模「刷新计数器→第 5 次保底」;关键回合(升 8 搜核心)刷到第 5 次必出 5 张同费核心 → D 牌估值在该点跳升。
- **R5-8 姬子·启行「选择伙伴」升级**(详 research/07):`decide_partner` 当前「优先 core_chars 命中」→ 升级为按**当前最缺羁绊 + 装备需求**选(缺护盾→三月七、生存→符玄、输出→白厄、能量→风堇)。依赖 `read_partner` OCR(候选 char_id),当前 OCR 未接(idx=0 盲点),随阶段 5。
- **数值校准(不属本层,记下)**:刷新费默认 **2 金**(用户 2026-08-06 确认;条件触发后变 → 运行时读 `state.shop_refresh_cost`,代码 `SHOP_REFRESH_COST=2` 默认对);升级金价表 / 连胜阶梯 → 实机 OCR 采集(strategy/13 §13.6 接线)。
