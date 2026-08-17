# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)
"""货币战争 评估函数(阶段键控加权的羁绊 + 经济 + 角色质量,A3;optionality/α(t) 承诺-期权 design 02/03;transition_tempo ADR-0140;target_progress 目标进度项)。

自 cw_decisions.py 一次性拆分而来(ADR-0145;纯移动零行为变化,函数名/签名不变)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.cw_comps import (
    COMMIT_FRAC,
    char_routes,
    clamp,
    escort_for,
    form_progress,
    skeleton_factions,
)
from sr_od.application.currency_war.cw_economy import (
    P2_REBUILD_GOLD_FLOOR,
    WIN_STREAK_BREAK_INTEREST,
    _char_synergies,
    _strategy_economy,
    economy_score,
    get_node_goal,
    roll_affordable,
)
from sr_od.application.currency_war.cw_factions import (
    FACTIONS,
    INTEREST_THRESHOLD,
)
from sr_od.application.currency_war.cw_state import (
    GameState,
    effective_hp_threshold,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.cw_comps import Comp

# —— eval 权重 ——
# 以下为 **V4.4 research meta 先验,冻结**(版本更新才改,不进用户调参面;review r5/r6 权重纪律)。
# 开发者阶段 6 手调的最敏感 3-5 维(均内部,非用户 GUI;用户配置走 develop config.md §3 转向轴):保血阈值(cw_state.HP_SAFE_THRESHOLD/DIFFICULTY_HP_TABLE,ADR-0204 迁入)/ obs schedule / MAX_REFRESH_PER_ROUND / α(t) r_open·r_close / fold 阈值。
CATEGORY_WEIGHT: dict[str, float] = {"combat": 10.0, "economy": 6.0, "support": 4.0, "independent": 2.0}

# (level benefit+3 < interest loss-6 → 不升)→ 卡 lv5-6 → 弱 comp → plane2 死。提权让升级战胜息损 → 升7-8
# → 高费 unit → comp value↑ → 攻坚 plane2。
CHAR_PRIORITY_BONUS: float = 8.0      # character_priority 角色分(每星)

FACTION_PRIORITY_BONUS: float = 1.0   # faction_priority rank 分

CLOSE_TO_NEXT_TIER_BONUS: float = 0.5  # 差 1 人推层的加成系数

SYNERGY_TIER_EXPONENT: float = 1.5     # 激活 tier 的超线性指数(收敛,task#16):深堆(高 tier)超线性奖励。

# 2026-08-04 实跑:bot 散阵(买每阵营 1 张)因 买新 tier-1 = 深化 tier1→2 同 delta(线性)→ 无偏好→散。
# 超线性(×1.5):深化 delta(2^1.5-1=1.83)> 散新(1^1.5=1)→ bot 偏好深化已有阵营 → 收敛(深堆>散)。
OFF_TARGET_DISCOUNT: float = 1.0       # 2026-08-04 revert(原 0.3):实跑发现 0.3 打折 board synergy 致 bot

# 卖成型 off-target 深堆(churn)= regression(vs 4-fix 无 commitment 清 plane1)。改 1.0(不打折)= 恢复
# 4-fix(super-linear synergy 单独)行为。commitment 正确实现 = prefilter(只 discount 新 off-target **buys**,
# 不动已有堆的 board eval)—— 待后续 task#16 续。target_comp 参数保留(prefilter 复用),effect 暂关。
# T#97 step-2(tuned):target bonus **只加在 tier 部分**(_base_tier,不含 close-to-next),避免 over-rush 弱-early。
# 2026-08-07 live:1.5× on whole tier_score(含 close-to-next)→ over-rush 弱-early 追击(count 2 冲 tier 3)→ HP 掉快
TARGET_FACTION_BONUS: float = 1.5      # target 阵营 tier 部分 ×1.5(tier-only,close-to-next 不加;见 synergy_score)

CEILING_BONUS_FACTOR: float = 0.3      # 高 ceiling 阵营(count/max_tier)潜力项系数

MAX_REFRESH_PER_ROUND: int = 2   # 每回合最多主动刷新(D 牌)次数(防无限刷;review r5 修死代码)



def _activated_tiers(faction: str, count: int) -> int:
    """该阵营在 count 人下激活了几个 tier。无信息返回 0。"""
    info = FACTIONS.get(faction)
    if info is None or count <= 0:
        return 0
    return sum(1 for t in info.tiers if t <= count)



def _max_tier(faction: str) -> int:
    info = FACTIONS.get(faction)
    return max(info.tiers) if info and info.tiers else 1



def _close_to_next(faction: str, count: int) -> bool:
    info = FACTIONS.get(faction)
    if info is None:
        return False
    nxt = next((t for t in info.tiers if t > count), None)
    return nxt is not None and count + 1 >= nxt



def _close_factions(state: GameState) -> set[str]:
    return {f for f, c in state.board.items() if _close_to_next(f, c)}



def synergy_score(state: GameState, faction_priority: list[str],
                  target_comp: Comp | None = None) -> float:
    """羁绊质量分:激活 tier × 类别 + 接近推层 + 偏好 + 高 ceiling 潜力项。

    target_comp 给定时(commitment,task#16):off-target 阵营 synergy × OFF_TARGET_DISCOUNT,
    聚焦深化 target 阵营 → target comp 更高 tier 更强。target_comp=None(reactive/测试)→ 不打折。
    """
    target_factions: set[str] = set(target_comp.form_tiers.keys()) if target_comp is not None else set()
    score = 0.0
    for faction, count in state.board.items():
        if count <= 0:
            continue
        info = FACTIONS.get(faction)
        cat_w = CATEGORY_WEIGHT[info.category] if info and info.category in CATEGORY_WEIGHT else 3.0
        # T#97 step-2(tuned):target bonus **只加在 _base_tier(tier 部分)**,不含 close-to-next —— 避免 over-rush
        _base_tier = cat_w * _activated_tiers(faction, count) ** SYNERGY_TIER_EXPONENT
        if target_factions:
            _base_tier *= TARGET_FACTION_BONUS if faction in target_factions else OFF_TARGET_DISCOUNT
        tier_score = _base_tier
        if _close_to_next(faction, count):
            tier_score += cat_w * CLOSE_TO_NEXT_TIER_BONUS   # close-to-next 不加 bonus(避免 rush 弱-early)
        mt = _max_tier(faction)
        if mt >= 6:
            tier_score += cat_w * (count / mt) * CEILING_BONUS_FACTOR
        score += tier_score
        if faction in faction_priority:
            score += (len(faction_priority) - faction_priority.index(faction)) * FACTION_PRIORITY_BONUS
    return score



def char_quality_score(state: GameState, character_priority: list[str],
                       target_comp=None) -> float:
    """角色质量分:character_priority 角色 × 星级 + **target 核心角色 × 星级**
    (r17:全场 3合1 落地后补——合并人数-2 但星级+1,target 核心的 2★ 战力增值
    必须计价,否则买第 3 张 delta 恒负 → 升星永不可达,与游戏语义相悖)。"""
    score = 0.0
    core_names: set[str] = set()
    if target_comp is not None:
        core_names = set(getattr(target_comp, 'core_chars', ()) or ())
    for bc in (*state.bench, *state.deployed):
        if bc.char_id in character_priority:
            score += CHAR_PRIORITY_BONUS * bc.star
        elif bc.char_id in core_names:
            score += CHAR_PRIORITY_BONUS * bc.star * 0.5   # target 核心星级(半权:低于用户 priority)
    return score



HP_DANGER: int = 40   # 保血触发阈值默认(hp 低于此 → 弃息保血)。A8 高难调高经 effective_hp_threshold(state,config)(D-32/3.5.1 已接,live-verified)。



def _phase_weights(plane: int, hp: int, hp_threshold: int = HP_DANGER) -> tuple[float, float, float]:
    """阶段键控权重 (synergy, economy, char)。A3 + review agent 经济学校准。

    **2026-08-03 修正(review agent + 用户)**:前期 economy **不该压低** —— 利息越早到 5 档(50 金)
    越好,经济滚雪球。原 "plane1 → economy 0.4" 把"前期"和"保血"混淆了。修正:
    - **HP 危险(hp<HP_DANGER):保血** —— 任何位面,弃息提质量(战力/角色加权、经济降权)。
    - **plane3(后期):锁血** —— 全力战力/星级(打 boss)。
    - **其余(健康):平衡 (1,1,1)** —— economy 不压低,可 snowball 到 50。

    A8 difficulty 已接(effective_hp_threshold,3.5.1/D-32 live-verified);win_streak 已接(_should_save_for_interest:连胜≥WIN_STREAK_BREAK_INTEREST 破息保连胜,C 杠杆 3 / R2-4b;结算源 session.last_streak 方向)。
    """
    if hp < hp_threshold:
        return (1.2, 0.4, 1.2)   # 保血:战力/角色优先,经济降权(任何位面 HP 危险)
    if plane == 3:
        return (1.3, 0.3, 1.3)   # 锁血:全力战力/星级(plane3 boss 战)
    return (1.0, 1.0, 1.0)       # 健康:平衡(economy 不压低,snowball 到 50)



def _refresh_cap(state: GameState, hp_threshold: int = HP_DANGER,
                 target_comp: Comp | None = None, config=None) -> int:
    """本回合 D 牌(刷新)上限(动态;review agent + 用户:固定 2 太死)。

    关键回合放宽:升 8 后 / plane3 搜核心、HP 危险锁血急救。
    刷新减费策略放宽:持有 REFRESH_DISCOUNT_STRATEGIES 任一(高效决策/加油站/采购专员等)
    → 每刷更便宜 → D牌效率更高 → 放宽到 6,关键回合多搜核心。
    策略数据源 = handle_invest_strategy 选时写回的 state.active_strategies(2026-08-14 接通)。
    """
    cap = MAX_REFRESH_PER_ROUND          # 基线 2
    if state.plane == 3 or state.level >= 8:
        cap = max(cap, 4)                # 升 8 后 / plane3:搜核心多刷
    if state.hp < hp_threshold:
        cap = max(cap, 4)                # 锁血急救:多刷找质量
    if state.node_type == 'boss':
        cap = max(cap, 4)                # ADR-0128(复查 #4):boss 关前把钱花完(D 出质量保 HP)
    if (target_comp is not None
            and target_comp.level_plan.get(state.level) is not None
            and target_comp.level_plan[state.level].action == 'roll'
            and roll_affordable(state, config, target_comp)):   # config 由调用方传(plan)
        # ADR-0128:comp 停留本级 roll → 放开刷;ADR-0147(评审 f3ab d2)加**可负担性门**:
        # E[刷到 2星核心]×2金 vs 预算金(gold−xp_floor),不可负担 → roll 让位 node plan
        # 不放宽。M20 死亡窗实证:满血也 4 刷×5 轮,散板 MC 恒正(reinforce+4/金币边际≈0)
        # 烧光金。金计价实现 = cw_economy.roll_affordable(expected_refreshes_for_card 接线)。
        cap = max(cap, 4)
    # ADR-0131:效果驱动替旧名单(REFRESH_DISCOUNT_STRATEGIES 语义错 —— 高效决策是 45 秒免费刷爆发
    # 非减半、采购专员是变同费 5 张非返现):有免费刷新额度/爆发窗/变卡稳定器 → 刷新变便宜/更值 → 放宽。
    _se = _strategy_economy(state)
    if (_se.free_refresh_per_node or _se.free_refresh_burst or _se.refresh_surprise_every):
        cap = max(cap, 6)
    # ⚖️ B2(ADR-0171 审判层消费端首口:3★/搜牌停手,M32「金 19-22 未转化」正缺此判决)。
    # 影子安全:try/except 静默回退(判决不可用 → cap 原值); verdict amend/abandon → cap 压 0
    # (搜牌窗该停 —— 线活但附着计划该改);判决 hold → 原值。证据 = 时间线掉队(p(t) 曲线)。
    try:
        from sr_od.application.currency_war.cw_comps import form_progress
        from sr_od.application.currency_war.cw_line_tribunal import (
            LineHypothesis,
            timeline_lag_lr,
            verdict,
        )
        from sr_od.application.currency_war.cw_progress_curves import (
            expected_curve_for_carry,
        )
        if target_comp is not None and target_comp.plaza_carry:
            curve = expected_curve_for_carry(target_comp.plaza_carry)
            if curve is not None:
                _t = (min(state.plane, 3) - 1) * 9 + min(state.round_num, 9)
                h = LineHypothesis('roll_cap_chase', target_comp.name, 'star_chase',
                                   checkpoints=[_t], deadline=_t + 4, expected=curve)
                _fp = form_progress(target_comp, state)
                lag = h.progress_lag(_t, _fp)
                if lag > 0:
                    h.add_evidence(_t, 'timeline_lag', f'{lag:.2f}', timeline_lag_lr(lag))
                    v = verdict(h, _t, cost_abandon=18.0, cost_hold=6.0)
                    if v.action != 'hold':
                        cap = 0   # amend/abandon:搜牌窗停(线活也该改附着计划——不再烧金搜)
    except Exception:   # noqa: BLE001  影子期失败安全:判决不可用 → 原 cap(=现状行为)
        pass
    return cap



def _economy_mode_for(state: GameState) -> str:
    """node spend_mode → economy_score 档位(14 §2.2;NodeGoal.spend_mode 单一源)。

    spend_mode 是节点节奏 gate,驱动 economy_score 利息/等级相对权重:
    - saving/interest → interest_first(攒息 snowball;P1 早期主目标尽快 50 金)
    - level → rush_level(弱化守息 + 强化等级;P2 升人口)
    - hold/allin/spend → adaptive(economy-low 由 _phase_weights plane3 we=0.3 处理,非此处)
    - adaptive → adaptive neutral(原 config.economy_mode 用户偏好辅已删,ADR-0204:死配置)

    与 _phase_weights 正交:本函数调 economy_score 内部(利息/等级相对权重),
    _phase_weights 调 economy_score 的 outer 乘子 we(HP/plane)。两者复合不双计。
    """
    # r14 切流预备:传全状态(47 号语义,同 cw_plan L780;关时零行为变化)
    _spend = get_node_goal(state.plane, state.round_num,
                           gold=state.gold, level=state.level, hp=state.hp).spend_mode
    if _spend in ("saving", "interest"):
        return "interest_first"
    if _spend == "level":
        # ADR-0148(评审 f3ab d1,进场金门槛):P2+ 穷金时 rush_level 是破产螺旋 —— 息权×0.5
        # + 跳卖息,而 P1 末已烧空、进场仅 13-18 金(M20 实证)根本升不动 8。降档 interest_first
        # 重建息引擎;自愈(金回升 ≥ P2_REBUILD_GOLD_FLOOR 自动回 rush_level)。
        if state.plane >= 2 and state.gold < P2_REBUILD_GOLD_FLOOR:
            return "interest_first"
        return "rush_level"
    return "adaptive"   # hold/allin/spend/adaptive → neutral



def _should_save_for_interest(state: GameState, config, target_comp: Comp | None) -> bool:
    """攒息门(经济统一论):全满足 → hold gold 攒利息(抑制散买/刷)。

    条件:gold<INTEREST_THRESHOLD(未满息)+ 板满(deployed≥max_units)+ HP 安全(≥threshold)
    + 板强(target 已 commit,form_progress≥COMMIT_FRAC)+ **非连胜中**(保连胜>吃息,见下)。
    tempo 破息出口(任一不满足即不攒息):HP 危险(由 _phase_weights 处理)/ 战力断档(板弱,D-142)/
    板未满(该 deploy 提战力)/ **连胜中**(本条,C 杠杆 3)。

    **保连胜 > 吃息(C 杠杆 3 winning half,R2-4b;14 §连胜中「2 胜+」)**:连胜 ≥ ``WIN_STREAK_BREAK_INTEREST``
    → 破息花钱提质量维持连胜(断连胜亏 > 利息亏 —— 连胜金 + 胜金 > 一档利息)。streak 带符号(连胜 + / 连败 −,
    结算源 session.last_streak,方向可靠);连败 fold 半已由 HP-gating 覆盖(02 R2-4b:血量安全→fold/不安全→急救)。
    """
    if state.gold >= INTEREST_THRESHOLD:
        return False
    # ADR-0128(攻略复查 #4,经济运营:18「boss 关前把钱花完」):boss 节点不攒息 —— 存金边际
    # 价值(5息)远低于板强保 HP(HP 是通关硬约束,息随时可再攒);read_node_type 对 boss 稳(实机核实)。
    if state.node_type == 'boss':
        return False
    if state.deployed_count() < state.max_units():
        return False
    if state.hp < effective_hp_threshold(state):
        return False
    if target_comp is None or form_progress(target_comp, state) < COMMIT_FRAC:
        return False
    # 连胜 ≥ 阈值 → 破息(保连胜>吃息,断连胜亏>利息亏);否则攒息。
    return (state.streak or 0) < WIN_STREAK_BREAK_INTEREST



def evaluate(state: GameState, config, faction_priority: list[str],
             target_comp: Comp | None = None) -> float:
    """局面总分(越高越好)= 阶段键控加权的(羁绊 + 经济 + 角色质量)+ 承诺-期权混合项。

    承诺-期权(F-3 / ADR 0096,2026-08-11 接线 ``α·commit + (1−α)·optionality``):
    - **commit 项**(target_comp 给定):``BENCH_TARGET``(持有 target 牌,**始终奖励** —— 早期也要攒核心件)
      + ``α·target_progress``(成型压力,早弱晚强:早期未成型是正常的,不该重罚;晚期必须成型 → 罚强)。
    - **optionality 项**(灵活期权):``(1−α)·optionality_score`` —— 早(α 小)保期权(bench 上属 ≥2 comp
      的通用角色),晚(α 大)让位 commit。optionality 与 commit 正交(ADR 0096:不同决策,不矛盾)。
    target_comp=None(reactive)→ commit 项归零,只剩 optionality(早期灵活)+ 基础分(A3 向后兼容)。
    core_chars 持有不在此重复计分(char_quality 已覆盖用户 character_priority)。
    """
    ws, we, wc = _phase_weights(state.plane, state.hp,
                                effective_hp_threshold(state))
    score = (
        ws * synergy_score(state, faction_priority, target_comp)
        + we * economy_score(state, _economy_mode_for(state))   # spend_mode→economy(§2.2;ADR-0102)
        + wc * char_quality_score(state, getattr(config, 'character_priority', []),
                                  target_comp=target_comp)   # r17:target 核心星级计价(3合1 全场域配套)
    )
    alpha = alpha_t(state)
    if target_comp is not None:
        # 成型压力(剩余进度罚)随 α:早期未成型不该重罚,晚期必须成型 → 罚强(F-3 commit 项)。
        score -= alpha * TARGET_PROGRESS_WEIGHT * _target_progress_remaining(state, target_comp)
        # BENCH_TARGET 不随 α 缩:持有 target 牌始终奖励(早期也要攒核心件;board 满→买 target 到 bench→
        # delta>0→bot 买→level up 后 deploy→target 深堆)。delta 中 phantom bench 抵消(plan greedy 消,净 delta 正确)。
        _bench_tgt = sum(1 for bc in state.bench
                         if _card_hits_target(bc.char_id, bc.faction, target_comp))
        score += BENCH_TARGET_WEIGHT * _bench_tgt
    # optionality(灵活期权,F-3):早期(α 小)保 ≥2 comp 通用角色,晚期(α→1)让位 commit。
    # 即使 reactive(target=None)也奖 —— 未 commit 时更该保灵活(通用角色随时可并入将来 target)。
    score += (1.0 - alpha) * OPTIONALITY_WEIGHT * optionality_score(state)
    # 过渡羁绊(P1 保血基础设施,review round-4 HIGH-2):早期凑能打伤害的羁绊(仙舟/狼狩/dot/列车/贝洛伯格)
    # 稳血到成型(限时 AV 下前期有输出不超时);fades as commit(α→1)。board 阵营数 OCR → 真信号现成。
    score += (1.0 - alpha) * transition_tempo_score(state, target_comp)
    return score



# target 成型剩余进度权重(战略层导向;占位,待实玩校准)。越大 → 越 commit 到 target。
TARGET_PROGRESS_WEIGHT: float = 15.0

BENCH_TARGET_WEIGHT: float = 3.0   # D-11 二次回退(2026-08-09 A/B 负):=8 局板更散(无 tier-2)、p2 hp3 < baseline hp16。

# 结论:buy hoard(BENCH_TARGET_WEIGHT)单杠杆不治 p2 死 —— bot 能激进买(7 张/轮),非 buy-quantity 限;
# 板散是 comp 选择/pivot + deploy 集中度问题,非 buy 权重。p2 死需更深工作(holistic 板强 / 接受 tier-2 靠星级装备)。
# =3 为 D-6 时期值,保留。D-11 两次试(=8)两次回退,确认非杠杆。


def _target_progress_remaining(state: GameState, target_comp: Comp) -> float:
    """target comp 剩余成型进度 0..1(0=已成型 form_tiers,1=完全没起步)。

    只看阵营 form_tiers(core_chars 持有由 char_quality 覆盖,不重复计分,03 去三重)。
    """
    if not target_comp.form_tiers:
        return 0.0
    tot = sum(max(0, t - state.board.get(f, 0)) / t for f, t in target_comp.form_tiers.items())
    return tot / len(target_comp.form_tiers)



def _card_hits_target(name: str, faction: str, target: Comp,
                      include_flex: bool = False) -> bool:
    """这张牌是否属于 target comp(**全羁绊匹配,流派安全**;治本流派/阵营断裂,决策见 ADR-0103)。

    True:name ∈ target.core_chars **或** 全羁绊(``_char_synergies`` + faction 兜底)∩ 目标阵营集非空。
    faction 兜底:name 未识别时用 OCR 的 card.faction(虽只阵营,聊胜于空)。

    ⚠️ 取代旧 ``card.faction in target.factions``(只阵营,流派主派 comp 的过渡/补充角色被误判 off-target:
    实跑 DOT 队 P1 输根因 —— 艾丝妲/椒丘等持续伤害流派角色 card.faction=银河学者/空 ∉ DOT.factions
    [持续伤害,星核猎手] → commit 后被 prefilter 跳过 → 凑不出 2DOT 过渡)。

    ADR-0152(评审🔴1)``include_flex`` 两档语义:
    - **False(默认,严格 = 核心阵营)**:deploy-swap 卖出候选 / bench 核心计数用 —— flex 单位是合法
      填充但**可被核心替换**(大丽花[盛会之星,列车flex] 让位给 列车 core 是升级非误卖)。
    - **True(宽松 = 核心+弹性)**:买牌 prefilter / deploy 许可用 —— flex 铺板是策略层奖励的合法
      形态(砂金=列车护盾流常驻),不拒买不上场。
    """
    if name in target.core_chars:
        return True
    syn = _char_synergies(name)
    if faction and faction != '?':
        syn = syn | {faction}
    return bool(syn & (target.all_factions if include_flex else set(target.factions)))



# ===== optionality_score + α(t) 承诺-期权(design 02/03 P1-1 + F-3;纯逻辑,evaluate 集成待 P0 验证)=====
# A8 是方差生存战:过早 commit 单一高 ceiling comp,遇克/缺关键牌即死。optionality 奖励 bench 角色
# 同时属 ≥2 可行 comp(保期权/容错);α(t) 早灵活(保期权)→ 晚承诺(深化 target)。
# ⚠️ **evaluate 集成延后**:改核心 eval 行为需游戏(P0)验证才稳;先纯函数 + 测试(零件)。

# α(t) 总回合阈值(R_OPEN 前 α=0 纯期权 / R_CLOSE 后 α=1 纯承诺);**值在代码**(阶段6实玩校准)。
R_OPEN: int = 2

R_CLOSE: int = 12

OPTIONALITY_WEIGHT: float = 8.0      # optionality 项权重(eval 集成时用;V4.4 先验,代码,实玩校准)

OPTIONALITY_PER_CHAR: float = 1.0    # 每个属 ≥2 comp 的 bench 角色加分



def _elapsed_rounds(state: GameState) -> int:
    """总回合数(``round_num + (plane-1)*6``;3 位面 × 6 关 = 18)。α(t) 用。"""
    return state.round_num + (state.plane - 1) * 6



def alpha_t(state: GameState) -> float:
    """承诺-期权时间衰减 α(t)(design F-3):总回合 < R_OPEN → 0(纯期权/灵活)、
    > R_CLOSE → 1(纯承诺/commit),之间线性。eval 集成时:``α·target_progress + (1-α)·optionality``。
    """
    if R_CLOSE <= R_OPEN:
        return 1.0
    return clamp((_elapsed_rounds(state) - R_OPEN) / (R_CLOSE - R_OPEN), 0.0, 1.0)



def optionality_score(state: GameState) -> float:
    """灵活性分:bench 角色属 **≥2 个 COMP_LIBRARY comp**(``shared_chars ∪ core_chars``)→ 加分(保期权)。

    设计 P1-1:保 ≥2 comp 可行的 bench 角色 → 遇克/缺牌可转型,容错;过早卖 shared_chars 扣分(未实现,
    集成时在 _bench_sell_value 加)。**未含 transition_chars**(已降级为参考字段,ADR-0149 由两级池替代)。
    评审🟡8:角色→comp 计数改调 ``char_routes()`` 单一源(原处自建 dict 同构实现,双源易漂移)。
    """
    if not state.bench:
        return 0.0
    routes = char_routes()
    score = 0.0
    for bc in state.bench:
        if bc.char_id and len(routes.get(bc.char_id, ())) >= 2:
            score += OPTIONALITY_PER_CHAR
    return score



# 过渡羁绊(P1 能打伤害的羁绊,前期凑出保血;review round-4 HIGH-2;comps/README「开局过渡分级」人上人级)。
# 限时 AV 下前期靠这些羁绊组合稳血到成型(DOT 慢热 P1 弱死根因之一 = 无过渡羁绊支撑)。
# 全局过渡基础设施(非 per-comp):任何 comp 的 P1 都可拿这些羁绊 tempo。
# ADR-0152(M4 方法论接线):主集从注册表派生(``cw_comps.skeleton_factions``:最低档 ≤3 人 +
# ≤2费成员 ≥2 —— plaza 实战开局组合的生成判据,版本更新自动传导);持续伤害/治疗手工补 ——
# 它们的过渡价值是**角色效果驱动**(桑博/艾丝妲带 DoT、藿藿/娜塔莎奶)非低费成员充足,派生判据筛不到。
TRANSITION_FACTIONS: set[str] = skeleton_factions() | {'持续伤害', '治疗'}

TRANSITION_TEMPO_BONUS: float = 3.0   # 每凑出(激活档)的过渡羁绊的早期保血分(占位,阶段 6 校准)


def _tier_activated(faction: str, count: int) -> bool:
    """该羁绊当前人数是否**激活了任意一档**(评审🟡7:tempo 判据与真实 tier 对齐)。

    FACTIONS.tiers 是激活人数档(升序);count ≥ 最低档才算「凑出」—— 仙舟(3/5/7/10)2 人不激活
    任何效果不算,巡海游侠(1/…)1 人即 tier-1 就算。未知羁绊(不在 FACTIONS)退回 count≥2 保守判。
    """
    info = FACTIONS.get(faction)
    if info is None or not info.tiers:
        return count >= 2
    return count >= min(info.tiers)



def transition_tempo_score(state: GameState,
                          target_comp: Comp | None = None) -> float:
    """P1 过渡羁绊分(review round-4 HIGH-2):board 凑出(激活档)能打伤害的过渡羁绊 → 早期保血(限时 AV 不超时)。

    人上人级 = 2 个能打伤害羁绊组合(仙舟/狼狩/dot/列车/贝洛伯格),稳血到成型。最多奖 2 个(更多边际
    递减);与 optionality 同(1−α)早期强调 —— 早期保期权/过渡,fades as commit(α→1)让位 target。
    board 阵营数 OCR 读 → 真信号现成。**双计说明(评审🟡7 更正)**:target 的核心阵营深堆会同时拿
    synergy(tier 效果)+tempo(早期能扛)—— 这是 intended(过渡期 target 阵营本来就既成型又保血),
    非重复奖励同一件事。
    评审🟡7:判「凑出」= **激活任意一档**(``_tier_activated``,非死板 ≥2)—— 仙舟 2 人不激活不奖,
    巡海游侠/星间旅人 1 人激活就奖(与真实游戏效果对齐)。

    ADR-0140(护航感知):target 给定且在护航窗口(P1 后期 ~ P2 分水岭前)→ 匹配护航套(escort_for)的
    羁绊凑出(≥2)额外加分 —— 护航是「有方向的过渡」(服务真主 C),比散凑过渡羁绊更值得买/留。
    """
    n = sum(1 for f in TRANSITION_FACTIONS if _tier_activated(f, state.board.get(f, 0)))
    score = min(n, 2) * TRANSITION_TEMPO_BONUS
    ec = escort_for(target_comp)
    if ec is not None and (state.plane, state.round_num) <= (ec.retire_plane, ec.retire_round):
        hit = sum(1 for f, need in ec.factions.items() if state.board.get(f, 0) >= min(2, need))
        if hit:
            score += hit * TRANSITION_TEMPO_BONUS * 1.5   # 护航羁绊加权(方向性过渡 > 散凑)
    return score
