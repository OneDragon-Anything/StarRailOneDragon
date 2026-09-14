"""自算复核共享判定核(T-153 自证循环迁移;ADR-0593)。

循环面(C1-C7,ADR-0593 §1)的豁免边从「静默采信策略自述」降级为
「自算复核通过才豁免」。本模块 = 各检查器迁移面与检测器面(检测器
集以 ``sim.checks.suspects.detector_ids()`` 公开口实数为准)共用
的自算判定核(单一源;同判定核两处消费,禁第二实现——先例 = launch 判据
核 kernel/cw_launch_admission 消费纪律)。输入形状 = 账本行 dict:sim 检查
器与生产 ``tools/cw/review_skeleton.merge_round_rows`` 合并行同构(ADR-0593
§4.1);正面先例 = ADR-0564 §G4 roster-diff 差分自算、ADR-0589 执行点
披露(dec_board_full/dec_bench_2star)。

复核三态(本批统一语义,消费方按态处置):
- ``ok``:自算支持自述 → 豁免照旧(兼容策略:避免一刀切翻旧案);
- ``mismatch``:自算反驳自述 → 可疑项条目 + 不豁免(迁移的产出面);
- ``unverifiable``:自算数据不可得(旧账本无披露键/标签解析失败)→ 豁免
  照旧——无键回退先例 = ADR-0589(检查器静默回退行末近似),缺证据不
  定罪,防历史批次全量假红。
"""

from __future__ import annotations

from types import SimpleNamespace

#: 复核三态常量(语义见模块 docstring;字符串面供事件字段/日志直读)
REVIEW_OK: str = 'ok'
REVIEW_MISMATCH: str = 'mismatch'
REVIEW_UNVERIFIABLE: str = 'unverifiable'

#: 冷启动豁免词表中「断言买牌身份」的自述键(C1 复核辖域)。仅这两个词
#: 语义 = 身份断言(其余 line/p2_core/emergency/swap/board_focus 等是
#: 通道语义,无从机械复核,unverifiable → 豁免照旧)。词表单一源 =
#: kernel/cw_registry(本元组只圈复核辖域,不是第二词表)。
COLDSTART_IDENTITY_CLAIMS: tuple[str, ...] = ('bridge_seed', 'engine')


def buy_identity(row: dict, action: dict) -> str:
    """买入身份自算(检测器/复核共用的 classify_buy 同源口径)。

    身份真值优先级:动作行 ``channel`` 键(sim 引擎 classify_buy 执行点
    转录,B=引擎自算)→ classify_buy 纯函数重算(生产动作无 channel 键
    时的回退,与引擎同一函数 = 无第二实现)。行 state 缺键时按空局面
    分类(bridge_seed/engine 只看注册表,不受影响;pair 会退 off——
    pair 语义需持有语境,语境缺失的降级方向 = 宁可疑不宁放)。
    """
    channel = action.get('channel')
    if isinstance(channel, str) and channel:
        return channel
    from sr_od.application.currency_war.kernel.cw_line_defs import (
        classify_buy as _classify,
    )

    st = row.get('state') or {}
    board = st.get('board_factions') or st.get('board') or {}
    bench = [
        SimpleNamespace(faction=b.get('faction') or '')
        for b in (st.get('bench') or []) if isinstance(b, dict)
    ]
    shim = SimpleNamespace(plane=row.get('plane') or 1, board=board,
                           bench=bench)
    card = action.get('card') or {}
    return _classify(
        SimpleNamespace(name=card.get('name') or '',
                        faction=card.get('faction') or ''),
        shim)


def is_engine_piece(name: str) -> bool:
    """引擎件身份(kernel 单一源委托;T-126 批 5 收拢第二实现,P78-7)。

    判定核单一源 = ``kernel.cw_card_identity.is_engine_piece``(本函数
    原为同判据第二实现;ADR-0625 候裁 5 申报的「生产决策位无可直调
    单一源」缺口随 kernel 侧补齐闭合,本委托保持消费方零改)。"""
    from sr_od.application.currency_war.kernel.cw_card_identity import (
        is_engine_piece as _kernel_pred,
    )
    return _kernel_pred(name)


def held_names_upto(rows: list[dict], idx: int) -> set[str]:
    """第 idx 行之前所有行的 bench∪deployed char_id 集(轮末快照近似)。

    「购买时未持有」的持有语境 = 上一轮末状态(本轮内先买后卖的漂移
    窗口 ±1,与 check_buys_at_full_bench 的期初 bench 口径同款近似
    声明)。生产合并行 bench 可能含 None 槽(生产快照不定长),过滤。
    """
    held: set[str] = set()
    for row in rows[:max(0, idx)]:
        st = row.get('state') or {}
        for b in (st.get('bench') or []):
            if isinstance(b, dict) and b.get('char_id'):
                held.add(b['char_id'])
        for d in (st.get('deployed') or []):
            if isinstance(d, dict) and d.get('char_id'):
                held.add(d['char_id'])
    return held


def k_members_of_row(row: dict) -> tuple[str, ...] | None:
    """行 target 标签 → 当前线名册(与 check_levelup_budget_gate 的
    _k_members 同源解析:过渡配方标签走 pair_target_comp,普通名走
    get_comp;单一源 = predicates.line_members)。

    标签空/解析失败 → None(不可复核,消费方按 unverifiable 处置)。
    """
    label = row.get('target_comp') or ''
    if not label:
        return None
    from sr_od.application.currency_war.kernel.cw_comps import get_comp
    from sr_od.application.currency_war.kernel.cw_intention import (
        pair_target_comp,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.predicates import (
        line_members,
    )
    try:
        if label.startswith('过渡配方·'):
            comp = pair_target_comp(
                tuple(label.removeprefix('过渡配方·').split('+')))
        else:
            comp = get_comp(label)
    except Exception:   # noqa: BLE001  解析失败=不可复核,不定罪
        return None
    if comp is None:
        return None
    return line_members(comp)


def _action_bool(action: dict, key: str) -> bool | None:
    """动作行披露 bool 键读取(ADR-0589 形态:bool 才算披露在场)。"""
    v = action.get(key)
    return v if isinstance(v, bool) else None


def levelup_prereq_review(row: dict, action: dict, prev_level: int) -> str:
    """升级授权可核前置复核(C2 迁移核;pop_slot/m3_batch 存在性腿)。

    前置 = 板满 ∧ bench 有等待上场名册件(授权语义出处 =
    check_levelup_interest_engine_gate docstring:pop_slot=[33] 人口位,
    m3_batch arm1_existence 同语境)。真值优先级:执行点披露
    (``dec_board_full``/``dec_bench_2star`` = ADR-0589 键;
    ``dec_bench_wait_member`` = 本批新增披露)→ 行末快照近似(cap 按
    轮内升级量回退,同 check_levelup_budget_gate 回退式)。

    **板满腿与名册可解析性解耦**(ADR-0593 后果.1(L6)):板满是授权前缀的
    必要条件。名册不可解析时,待上场腿不可得;板满腿可作名册无关
    反证的**只限引擎执行点披露**(``dec_board_full`` 键在场且 False
    ——执行点真值,封死「不锁线/写坏标签即豁免谎报」后门);行末
    近似有部署时序 ±漂移窗(弱证据),不足以单独定罪 → 落
    unverifiable(豁免照旧)。待上场腿披露键在名册不可解析语境恒
    False 是语境缺失非证据(seed4 r3 arm1 未锁期发射实证,禁据键定罪)。
    """
    members = k_members_of_row(row)
    board_full = _action_bool(action, 'dec_board_full')
    st = row.get('state') or {}
    if members is None:
        # 名册不可解析:仅执行点披露 False 可作名册无关反证(L6)
        if _action_bool(action, 'dec_board_full') is False:
            return REVIEW_MISMATCH
        return REVIEW_UNVERIFIABLE
    if board_full is None:
        cap = st.get('cap')
        dep_n = sum(1 for d in (st.get('deployed') or [])
                    if isinstance(d, dict) and d.get('char_id'))
        lvups = sum(1 for a in row.get('actions') or []
                    if a.get('__type__') == 'LevelUp')
        board_full = (dep_n >= (cap - lvups)) if cap is not None else None
    wait = _action_bool(action, 'dec_bench_wait_member')
    if wait is None:
        member_set = set(members)
        wait = any(isinstance(b, dict)
                   and b.get('char_id') in member_set
                   for b in (st.get('bench') or []))
    if board_full is None or wait is None:
        return REVIEW_UNVERIFIABLE
    return REVIEW_OK if (board_full and wait) else REVIEW_MISMATCH


def seed_identity_review(rows: list[dict], row_idx: int,
                         action: dict) -> str:
    """种子身份自算复核(C7 迁移核;engine_seed 辖域的自算底座)。

    种子语义 = P1 未持有引擎件放行通道(语义锚 = ADR-0633 种子获取判据):
    复核 = 引擎件(注册表现算)∧ 购买时未持有(前轮末快照 + 同轮更早
    买入)。任一不成立 → mismatch(自报 engine_seed 但机械身份失配,
    即 T-153 C7 的「改标脱离检查网」攻击面显形)。
    """
    name = (action.get('card') or {}).get('name') or ''
    if not is_engine_piece(name):
        return REVIEW_MISMATCH
    held = held_names_upto(rows, row_idx)
    for a in (rows[row_idx].get('actions') or []):
        if a is action:
            break   # 只数同轮更早的买入(本动作之前)
        if a.get('__type__') == 'BuyCard' \
                and (a.get('card') or {}).get('name') == name:
            return REVIEW_MISMATCH
    if name in held:
        return REVIEW_MISMATCH
    return REVIEW_OK


def copy_collection_review(held_before: set[str],
                           round_same_name_buys: int) -> str:
    """copy(3合1 副本素材)收集语境复核(C4 迁移核)。

    机械证据 = 同轮同名买入 ≥2(收集语境第 3 份,ADR-0276 同族口径)
    或 **购买时点净持有**同名(第 2/3 份副本路径)。两证据皆无的单张
    凭空 copy → mismatch(自报素材语境但无素材形态)。

    净持有语义(ADR-0593 后果.5(L2)):调用方传入的 ``held_before`` 必须
    是「买入-卖出台账销账」后的净集——曾持有但中途已卖出的名不在此
    (「终身持有通行证」形态封死,探针 = r1 买→r2 卖→r3 copy 买同轮
    卖必产失配)。
    """
    if round_same_name_buys >= 2:
        return REVIEW_OK
    if held_before:
        return REVIEW_OK
    return REVIEW_MISMATCH


def sell_line_membership_review(row: dict, action: dict) -> str:
    """转化类卖出分键的线成员复核(C4 迁移核;line_switch_collapse 写端
    证明义务的检查端补位,ADR-0591 §4)。

    真值 = 卖出执行点披露 ``dec_sell_in_line``(本批新增;引擎现算被卖件
    是否当前线名册成员)。**名册不可解析(行 target 空标签/查无)=
    unverifiable**——未锁线期的合法线账闭合(seed18 p1r1 孤儿清算
    实证:T-141)不携可解析标签,彼时披露键恒 False 是语境缺失,
    非「非线成员」证据,禁据此定罪。键在场且名册可解析而 False
    (卖的不是线成员却自报转化/清算分键)→ mismatch。
    """
    if k_members_of_row(row) is None:
        return REVIEW_UNVERIFIABLE
    v = _action_bool(action, 'dec_sell_in_line')
    if v is None:
        return REVIEW_UNVERIFIABLE
    return REVIEW_OK if v else REVIEW_MISMATCH
