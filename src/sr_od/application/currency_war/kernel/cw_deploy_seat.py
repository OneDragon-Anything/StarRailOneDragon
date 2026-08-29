"""腾席判据函数族 + deploy 全局不变量(kernel 单一源)。

自 strategy_v1(cw_plan/cw_evaluate)语义保持平移(买层接管批段 0,ADR-0477):
decision_v2 腾席链(/部署/升级门)消费的判据不再经 strategy_v1 豁免边,
统一消费本模块;strategy_v1 整桶退役后本模块是这些符号的唯一源。
迁移为逐字符语义保持(函数体零改动,仅 import 面收拢到 kernel/data 合法向);
等价性证据 = 平移前后同参 fuzz 对照(见 ADR-0477;对照记录随迁移批存档,git 历史可溯)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_factions import (
    FACTIONS,
    INTEREST_THRESHOLD,
)
from sr_od.application.currency_war.kernel.cw_comps import EARLY_CORE_POOL
from sr_od.application.currency_war.kernel.cw_economy import (
    _char_synergies,
    _want_level_up,
    _xp_gold_floor,
    xp_click_cost,
)
from sr_od.application.currency_war.kernel.cw_state import (
    BenchChar,
    GameState,
    bench_occupied,
    iter_occupied_deployed,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp


def _close_to_next(faction: str, count: int) -> bool:
    info = FACTIONS.get(faction)
    if info is None:
        return False
    nxt = next((t for t in info.tiers if t > count), None)
    return nxt is not None and count + 1 >= nxt


def _close_factions(state: GameState) -> set[str]:
    return {f for f, c in state.board.items() if _close_to_next(f, c)}


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


def _bench_faction_counts(state: GameState) -> dict[str, int]:
    """已 collect 各阵营计数 = board(deployed ground truth)+ bench(_should_deploy 用)。"""
    counts: dict[str, int] = dict(state.board)
    for c in state.bench:
        if c is not None and c.faction and c.faction != '?':
            counts[c.faction] = counts.get(c.faction, 0) + 1
    return counts


def _dep_activates_tier(bc: BenchChar, state: GameState) -> bool:
    """r90 C1 上场即激活档:该牌上场后 board 阵营计数命中**此前未达**的激活档。

    攻略 #245「手上有 4击破 才让白厄上场」的判据形式化:final 件的上场窗口之一 =
    上场本身产生确定羁绊增量(新档激活)。deepen 已达最高档不算(那是深化,归框架件管)。
    ⚠️ 口径:只数场上(board),bench 囤牌不计入激活(游戏正确口径;并入 bench 会误判
    「囤 2 张后第 1 张即激活」提前散上)。本函数只评估**候选卡本身**;「bench 囤的第
    2/3 张同阵营齐档后整组上场」的组合窗口不在此判(靠窗口①定型/②位面末兜底,
    单卡永不触发③——r90 审计 A.a 记录,接受该简化)。
    """
    syn = _char_synergies(bc.char_id) if bc.char_id else set()
    if bc.faction and bc.faction != '?':
        syn = syn | {bc.faction}
    for f in syn:
        _i = FACTIONS.get(f)
        if _i is None or not _i.tiers:
            continue
        cur = state.board.get(f, 0)
        new = cur + 1
        hits_new = any(new >= t for t in _i.tiers)
        hits_old = any(cur >= t for t in _i.tiers)
        if hits_new and not hits_old:
            return True
    return False


def deploy_legal(bc: BenchChar, deployed_names: set[str]) -> bool:
    """⚖️ 全局不变量守卫(单一源,r94):**场上同名禁双**(游戏规则 5.1.7 实测,ADR-0125)。

    **一切「把角色放上场」的路径必须过本守卫**——买后 deploy / 腾席链 / 换位 /
    任何新 deploy 路径。历史上散在三处内联,第 4 处新路径(腾席链 a,r93)漏写 →
    藿藿被拖 5 次全拒实证。收口单一函数后新路径只需调用,不再依赖"记得写"。
    同名在场 → False(留 bench 待 3合1 合并,合并域=全场)。
    单一源现址 = 本模块(kernel;自 strategy_v1 平移,ADR-0477)。
    """
    return not (bc.char_id and bc.char_id in deployed_names)


def deployed_name_set(state: GameState) -> set[str]:
    """场上角色名集(deploy_legal 的配套取数;单一源防各处自算漂移)。"""
    return {b.char_id for b in iter_occupied_deployed(state.deployed) if b.char_id}


def _card_supports_target(name: str, faction: str, state, target) -> bool:
    """买牌/deploy 的 off-target 判定(**配对纪律版**,M25 实证修正)。

    M4 方法论:骨架是「成对凑羁绊」非散买。规则:
    - 核心(core_chars 或核心阵营羁绊)→ 恒 True;
    - **枢纽早期核心**(EARLY_CORE_POOL,千冶·刃/姬子·启行等存活≥0.8)→ 单买 True
      (跨路线复用,买了就是开局,plaza M3);
    - flex 弹性羁绊 → 仅当该羁绊在 board+bench 已有 ≥1(深化成对)才 True;
      散买 flex 单张 = spread 合法化(M25 实锤:8 阵营各 1,列车:1 卡死,hp10 死 2-4)。
    """
    if target is None:
        return False
    if _card_hits_target(name, faction, target):   # 严格档(核心)
        return True
    if name in EARLY_CORE_POOL:
        return True
    syn = _char_synergies(name)
    if faction and faction != '?':
        syn = syn | {faction}
    flex = target.all_factions - set(target.factions)
    if not flex:
        return False
    counts = _bench_faction_counts(state)
    return any(f in flex and counts.get(f, 0) >= 1 for f in syn)


def _bench_sell_value(bc: BenchChar, character_priority: list[str], close_factions: set[str],
                      target_comp: Comp | None = None) -> float:
    """角色"留下价值"(越低越该卖):星级 + 优先角色 + 接近推层阵营 + target 核心保护。

    review 🔴:加 target_comp —— target 核心卡(core_chars / 全羁绊命中)高额保护分,
    防 plan 卖掉 target 核心凑息(承诺须贯穿卖路径,非只买/部署;否则一边承诺一边卖 target)。
    """
    val = float(bc.star)
    if bc.char_id in character_priority:
        val += 100
    if bc.faction in close_factions:
        val += 50
    if target_comp is not None and _card_hits_target(bc.char_id, bc.faction, target_comp):
        val += 100   # target 核心保护(同 priority 量级);commit 后绝不卖 target 凑息
    return val


def _weakest_bench_idx(state: GameState, character_priority: list[str],
                       target_comp: Comp | None = None) -> int | None:
    """最弱可卖 bench 下标(腾席链 c 步共用;strategy/03(原 doc 15§5.2c))。

    **3合1 重复件保护**(strategy/03(原 doc 15§4.1) 待加项,2026-08-14 P1 落地):bench 内同名 ≥2 张 =
    3合1 进行中(再买 1 张即自动升星,价值远超残值)→ 保护不卖;全被保护 → 返回 None
    (无可卖,调用方走 DeferSpheres/留置)。
    返回值坐标系:state.bench 的下标(0 基,含 None 槽位),执行期现读快照。
    """
    if bench_occupied(state.bench) == 0:
        return None
    from collections import Counter
    # 按 (char_id, star) 计数(review L-5):3合1 只合并同名同星,同名不同星不构成进度 → 不保护
    _counts = Counter((bc.char_id, bc.star) for bc in state.bench
                      if bc is not None and bc.char_id)
    _protected = {i for i, bc in enumerate(state.bench)
                  if bc is not None and bc.char_id
                  and _counts[(bc.char_id, bc.star)] >= 2}
    # ADR-0316 槽位表:只收占用槽(None 槽不可卖,跳过)
    _candidates = [i for i, bc in enumerate(state.bench)
                   if bc is not None and i not in _protected]
    if not _candidates:
        return None   # 全是 3合1 进行件:无可卖(调用方 DeferSpheres/留置)
    close = _close_factions(state)
    return min(_candidates,
               key=lambda i: _bench_sell_value(state.bench[i],
                                               character_priority, close,
                                               target_comp))


def _should_deploy(bc: BenchChar, state: GameState, target: Comp | None) -> bool:
    """是否 deploy 该角色(L2 deploy cap,防 spread-lock)。

    r90 C1 **final 件条件窗口**(663 帖攻略精读 #243/#245/#249:final 件买而囤 bench,
    等窗口才上场 —— 用户定性「凑 final 不是问题,让它上场却取不了胜利才是」):
    双轨期(P1 未定型)target 件**不再即买即上**(旧直 True = P1 板长成 final
    散件打不过过渡阵容,第9局四线散板实证)。P1 的板 = 过渡框架;final 件囤 bench,
    上场窗口(任一):
    - ①非双轨(定型信号 ready / 进 P2)→ 无条件上;
    - ②位面末变阵窗(round ≥ 8;#243「1-8 奖励关后 d,1-9 变阵」)→ 换 final 上;
    - ③上场即激活阵营档(见 ``_dep_activates_tier``;#245 白厄=4击破齐)→ 即刻兑现;
    - ④框架在册件(TRANSITION_PACK 非 drop,仙舟/列车/通用)→ 双轨期临时 target 照上(r70)。
    窗口外落回集中判据(阵营 count≥2 深化)。

    ⚖️ r94:本函数顶部统一执行 ``deploy_legal``(场上同名禁双,全局不变量)——
    所有调用方(腾席链/任何新路径)经此即受保护,内联守卫不再各写。
    deploy 条件(任一,窗口外):
    - target 阵营角色(窗口内,见上)。
    - bc.faction 在 bench+deployed 已 count≥2(集中阵营深化)。
    否则留 bench(off-target 单张可 sell,防 deployed-lock 永久占槽)。
    """
    if not deploy_legal(bc, deployed_name_set(state)):
        return False   # 场上同名禁双(5.1.7,全局不变量;留 bench 待 3合1)
    if target is not None and _card_supports_target(bc.char_id, bc.faction, state, target):
        if not state.dual_track_phase:
            return True   # ①已定型/进 P2:final 即主力
        if state.round_num >= 8:
            return True   # ②位面末变阵窗(P1 r8 奖励关起 → r9 boss 前换 final)
        if _dep_activates_tier(bc, state):
            return True   # ③上场即激活档(确定战力即刻兑现)
        # 双轨期窗口外:final 件囤 bench(stash),落到下方框架/集中判据
    if state.dual_track_phase and bc.char_id:
        # r72 口径对齐(review #3):三侧统一「当先框架非 drop + 通用件」——
        # 散件 drop(艾丝妲/佩拉)不自动上(应急件,op 侧同口径);通用 carry
        # (千冶·刃 29%→64%)三侧都认。框架由 session 单一源。
        # r107 审计C:白名单从 FRAMEWORKS 单一源派生(r102 加量子时硬编码
        # 遗漏 → 希儿/缇宝/符玄双轨期囤 bench 不上场,量子同频 trait 型连
        # 底部兜底都接不住)。
        from sr_od.application.currency_war.kernel.cw_transition import (
            FRAMEWORKS as _FWS,
        )
        from sr_od.application.currency_war.kernel.cw_transition import (
            TRANSITION_PACK as _TP,
        )
        _e = _TP.get(bc.char_id)
        if _e is not None and (_e[0] in _FWS or _e[0] == '通用') and _e[1] != 'drop':
            return True
    return _bench_faction_counts(state).get(bc.faction, 0) >= 2


def _pick_deploy_row(state: GameState, bc: BenchChar,
                     target_comp: Comp | None = None) -> tuple[str, bool]:
    """按角色 position_pref 选排(偏好排优先,满则另一排);无空位返回 (row, False)。

    ADR-0139:target_comp.char_positions(角色→front/back)覆盖命途默认 —— comp 特定站位是攻略实证
    (爻光必后台/万敌独前排),比命途 position_pref 更准;无条目按默认。
    """
    if state.deployed_count() >= state.max_units():
        return ("front", False)
    pref = bc.position_pref or "back"
    if target_comp is not None and bc.char_id in target_comp.char_positions:
        pref = target_comp.char_positions[bc.char_id]
    if pref == "front" and state.front_count() < state.front_max:
        return ("front", True)
    if state.back_count() < state.back_max:
        return ("back", True)
    if state.front_count() < state.front_max:
        return ("front", True)
    return ("front", False)


def level_up_gate(state: GameState, target_comp: Comp | None = None,
                  committed: bool | None = None) -> bool:
    """买经验硬门(腾席链 b 步与 sim 侧共用单一源;strategy/03(原 doc 15§5.2b) / §4.1;ADR-0129)。

    条件 = level<10 + 该买经验(_want_level_up)+ 存金允许(扣单击价后不破 _xp_gold_floor)。
    旧门要求 gold≥整级大金(36-60)→ 实际每击仅 4-8 金 → 过度保守 → 升级滞后(M15 live 实锤)。
    ⚠️ gold 前置:shop 关态 gold 读空 —— 调用方须在 shop 开态的 fresh state 上判
    (EnsureShopOpen 后重读;strategy/03(原 doc 15§5.2b) M2)。

    committed 显式传参(退役批(ADR-0466/0467/0469) C5 换源,ADR-0456 后设计件;蓝图 §4.3-R1):
    None=挂账层旧口径(读 GameState 双轨标志);step 级调用方(dv 腾席链 b)
    从 prep_brain.committed_from 取权威值传入——fresh 帧装配边界不再靠
    双轨标志回填,堵「漏回填=恒按已定型激进化放升级」病理。

    **溢出金 XP 放行(r85,用户 50 金息律「>50 的每一分都无存钱意义,该升级就升级」)**:
    金 ≥ INTEREST_THRESHOLD + 单击价 时(息满溢出区),_want_level_up 的 False
    (DP 攒息姿态压 target_level)不再拦 —— 溢出部分买经验不损息档地板 50,
    白嫖人口进度;姿态的「攒息」目的此时已达成,不矛盾。P1 末 60-70 金闲置
    实证(用户演示局对照)即此缺口。地板仍守(花后 ≥50)。
    """
    if state.level >= 10:
        return False
    want = _want_level_up(state, target_comp, committed)
    if not want:
        # r85 溢出区放行:息满 + 够单击 + 花后不破 50 地板 → 姿态压制不拦溢出金
        return (state.gold >= INTEREST_THRESHOLD + xp_click_cost(state)
                and state.gold - xp_click_cost(state) >= INTEREST_THRESHOLD)
    return state.gold - xp_click_cost(state) >= _xp_gold_floor(state, want)
