"""可疑项检测器集 D1-D11(T-153 自证循环迁移的复盘面;ADR-0593)。

**架构定位**(ADR-0593 §4,用户裁定 2026-09-08):检测的归宿 =
复盘模板生成器(tools/cw/review_skeleton.py)——逐局复盘文档生成时,
生成器对本局决策数据跑本检测器集,把可疑项作为预填条目嵌入对应
决策节点小节(判定三槽之前);**禁独立附录清单**。机械事实类检查留
检查器(批量统计哨兵职能不变),结构合法性留生成侧,需语境裁决的
豁免边 = 本检测器面——三类各归其位。

**条目三要素**(ADR-0593 §4.2):①模式名+定位(轮/op/节点);②自算值 vs
自报值对照(自述失配类条目的核心;无自报的机械条目只给自算值);
③裁决问句(具体二选一,不是泛泛「请检查」)。

**与检查器的关系**(ADR-0593 §4.2):同一判定核两处消费,避免第二实现
(判据函数单一源纪律,同 launch 判据核先例)——D1/D3/D4/D5 的身份/
前置/种子复核核 = sim/checks/selfcalc(检查器迁移面同吃);D2/D7/D8/
D9 = 段级检查器函数直接复用(现函数逻辑即检测器);D6 语境条目 =
机械不复算(时序歧义),只打包邻近轮意向交复盘者。输入形状与段级
检查器同构(``rows: list[dict]``),输入 = 按 (plane, round, ts) 合并
排序后的账本轮行。
"""

from __future__ import annotations

from collections.abc import Callable

from sr_od.application.currency_war.sim.checks import selfcalc as _sl
from sr_od.application.currency_war.sim.checks.ledger import (
    _normalize_buy_reason,
)
from sr_od.application.currency_war.sim.checks.segments import (
    _seg_engines,
    _seg_gold0,
    _seg_target_roster,
    seg_check_break_interest_exception,
    seg_check_overflow_idle_spend,
    seg_check_p1_blood_budget_levelup,
    seg_check_p1_blood_budget_refresh,
    seg_check_p2_bleed_gold_stack,
    seg_check_p2_blood_budget_levelup,
    seg_check_untrusted_hp_levelup,
)

#: 模式中文名(条目与模板节点引用用;键 = 检测器 id)
MODE_NAMES: dict[str, str] = {
    'D1': '同轮买卖分键复核',
    'D2': '溢金停手失配',
    'D3': '追级授权前置',
    'D4': '冷启动身份失配',
    'D5': '种子回卖辖域自算',
    'D6': '成型后④臂语境',
    'D7': '破息无例外',
    'D8': '血预算停手',
    'D9': 'P2 血降金堆',
    'D10': '部署欠载',
    'D11': '幻影实体与槽超买',
}


def _entry(mode: str, row: dict, detail: str, *,
           evidence: dict | None = None) -> dict:
    """条目统一形状(定位坐标 = (plane, round_num);节点类型随行)。"""
    ev: dict = {
        'mode': mode,
        'mode_name': MODE_NAMES[mode],
        'plane': row.get('plane'),
        'round_num': row.get('round_num'),
        'node': (row.get('sim') or {}).get('node') or '',
        'detail': detail,
    }
    if evidence:
        ev['evidence'] = evidence
    return ev


def _cross_ref(mode: str, row: dict, anchor_round: int) -> dict:
    """跨轮连击的交叉引用行(锚轮小节持全条目;本行插被跨越轮)。

    ADR-0593 §4.1 通用归属规则:跨轮模式锚 = 达成阈值的触发轮,被跨越的
    前几轮小节各加一行「↗ 本轮参与 {检测名} 连击(锚 r{n})」——节点内
    交叉引用,不另立清单(禁独立附录的同一条裁定)。
    """
    return {
        'mode': mode, 'mode_name': MODE_NAMES[mode],
        'plane': row.get('plane'), 'round_num': row.get('round_num'),
        'node': (row.get('sim') or {}).get('node') or '',
        'cross_ref': True, 'anchor_round': anchor_round,
        'detail': f'↗ 本轮参与 {MODE_NAMES[mode]} 连击(锚 r{anchor_round})',
    }


# =====================================================================
# --- D1 同轮买卖振荡 + 自报分键复核(ADR-0593 §4.1;C4 检测器面) --------
# =====================================================================

def d1_same_round_pair_review(rows: list[dict]) -> list[dict]:
    """同轮买卖对的自算身份 vs 自报分键对照,失配即条目。

    判定核 = selfcalc 三复核(copy 收集语境/种子身份/转化分键线成员)
    ——与 check_no_same_round_buy_sell / check_oscillation_xp_cap 的
    迁移面同吃(selfcalc 单一源);本检测器是**复盘面**:豁免对失配
    产「振荡候选」条目交复盘者裁决,机械判违面留在检查器。
    持有语境 = 净持有(买入入集/卖出台账销账;ADR-0593 后果.5(L2),「终身持有
    通行证」形态封死)。
    """
    from sr_od.application.currency_war.kernel.cw_prep_actions import (
        SELL_BENCH_ORPHAN_REASONS,
    )
    from sr_od.application.currency_war.kernel.cw_state import (
        SELL_BENCH_CONVERT_REASONS,
    )
    out: list[dict] = []
    held_net: set[str] = set()
    for idx, row in enumerate(rows):
        round_buys: dict[str, list[dict]] = {}
        copy_round_buys: dict[str, int] = {}
        held_before_round = set(held_net)   # 本轮前净持有(复核基线)
        for a in row.get('actions') or []:
            if a.get('__type__') == 'BuyCard':
                n = (a.get('card') or {}).get('name')
                if n:
                    round_buys.setdefault(n, []).append(a)
                    if _normalize_buy_reason(a.get('reason') or '') \
                            == 'copy':
                        copy_round_buys[n] = copy_round_buys.get(n, 0) + 1
                    held_net.add(n)   # 净持有:买入入集
            elif a.get('__type__') == 'SellBench':
                n = a.get('name')
                held_net.discard(n)   # 净持有销账(跨轮;ADR-0593 后果.5(L2))
                buys = round_buys.get(n) or []
                if not buys:
                    continue
                claimed: list[str] = [
                    _normalize_buy_reason(b.get('reason') or '')
                    for b in buys]
                claimed.append(a.get('sell_reason') or '')
                # 转化类结构化分键入自报面(ADR-0611:与
                # 检查器按键分工同构,转化类读 convert_reason/孤儿读
                # reason;披露面加法增益)
                claimed.append(a.get('convert_reason') or '')
                claimed = [c for c in claimed if c]
                # 自算身份(ADR-0593 §D1:线外散牌/孤儿/垫件/收集语境);
                # 持有证据 = 本轮前净持有快照(本轮 copy 买不算持有)
                if copy_round_buys.get(n, 0) >= 2 \
                        or n in held_before_round:
                    identity = f'收集语境第{copy_round_buys.get(n, 0) + 1}份/已持有(副本素材)'
                elif all(_sl.seed_identity_review(rows, idx, b)
                         == _sl.REVIEW_OK for b in buys):
                    identity = '引擎种子(未持有引擎件首购)'
                else:
                    members = _sl.k_members_of_row(row)
                    if members is not None and n in members:
                        identity = '线成员(孤儿清算/线账闭合语境候选)'
                    elif members is None:
                        identity = '名册不可解析(未锁线,线成员腿不可得)'
                    else:
                        identity = '线外散牌/垫件'
                # 失配判定(与检查器复核同判据;任一自报分键被自算反驳;
                # T-165 按键分工:转化类读 convert_reason,孤儿读
                # sell_reason ∈ cw_prep_actions.SELL_BENCH_ORPHAN_REASONS
                # (T-180 起与发射位登记门分离的独立闭集),与
                # check_no_same_round_buy_sell 零双源同构)
                _conv_key = a.get('convert_reason') or ''
                _orph_key = a.get('sell_reason') or ''
                _conv_orphan_claim = ''
                if _conv_key in SELL_BENCH_CONVERT_REASONS:
                    _conv_orphan_claim = _conv_key
                elif _orph_key in SELL_BENCH_ORPHAN_REASONS:
                    _conv_orphan_claim = _orph_key
                mismatch = ''
                if _conv_orphan_claim \
                        and _sl.sell_line_membership_review(row, a) \
                        == _sl.REVIEW_MISMATCH:
                    mismatch = (f'自报转化分键={_conv_orphan_claim}'
                                ' 但自算非线成员')
                elif 'copy' in claimed \
                        and _sl.copy_collection_review(
                            held_before_round, copy_round_buys.get(n, 0)) \
                        == _sl.REVIEW_MISMATCH:
                    mismatch = '自报 copy(3合1 素材) 但自算无收集语境'
                elif 'engine_seed' in claimed \
                        and any(_sl.seed_identity_review(rows, idx, b)
                                == _sl.REVIEW_MISMATCH for b in buys):
                    mismatch = '自报 engine_seed 但自算非种子身份'
                if mismatch:
                    out.append(_entry('D1', row, (
                        f'可疑项(振荡候选):p{row.get("plane")}'
                        f'r{row.get("round_num")} 买{n}→同轮卖{n};'
                        f'自报分键={claimed or ["(无)"]};'
                        f'自算身份={identity};{mismatch}'
                        '——请裁决: 合法转化 / 振荡'), evidence={
                            'buy_reasons': claimed,
                            'sell_reason': a.get('sell_reason'),
                            'convert_reason': a.get('convert_reason'),
                            'self_calc_identity': identity,
                        }))
    return out


# =====================================================================
# --- D2 溢金未泄 + 停手失配(ADR-0593 §4.1;C5 检测器面,包装 seg 事件) --
# =====================================================================

def d2_overflow_stop_mismatch(rows: list[dict]) -> list[dict]:
    """溢金零花费轮条目;自报停手∧自算未成型 = 成型谎报 emphasized。

    判定核单一源 = seg_check_overflow_idle_spend(本批已迁移:自算
    先行、谎报不豁免);本检测器只做条目化——自洽停手不产条目
    (seg 豁免面已过滤),机械违规与谎报失配都产条目交复盘裁决。
    """
    out: list[dict] = []
    for ev in seg_check_overflow_idle_spend(rows):
        row = {'plane': ev.get('plane'), 'round_num': ev.get('round_num'),
               'sim': {'node': ev.get('node') or ''}}
        claimed = bool(ev.get('suspect'))
        out.append(_entry('D2', row, (
            f'可疑项(溢金/停手失配):p1r{ev.get("round_num")} '
            f'金{ev.get("gold_before")} 零花费;自报停手='
            f'{"真" if claimed else "假"};自算成型度='
            f'{ev.get("engines")}(<2)——请裁决: '
            f'{"谎报停手定谳 / 语境豁免" if claimed else "漏花定谳 / 合法保留"}'),
            evidence={'gold_before': ev.get('gold_before'),
                      'engines': ev.get('engines'),
                      'formed_stop_claimed': claimed,
                      'suspect': ev.get('suspect') or ''}))
    return out


# =====================================================================
# --- D3 追级授权前置失配(ADR-0593 §4.1;C2 复核面 + C3 辖域缺口补位) ---
# =====================================================================

def d3_levelup_prereq(rows: list[dict]) -> list[dict]:
    """lv≥5∧时点金<50 的升级逐条语境条目(交复盘者裁决授权)。

    辖域 = 追级段全部升级(含白名单臂)——C3 的预算闸辖域缺口
    (非 m3_batch 自报完全不经闸,ADR-0593 §C3)由本检测器
    补位:可自算前置(板满/待上场)现场给出,static_ev/dp 腿标注
    「EV 总账需回放」。判定核 = selfcalc.levelup_prereq_review
    (与 C2 检查器迁移面同吃)。
    """
    out: list[dict] = []
    prev_level = 3
    for row in rows:
        if (row.get('plane') or 1) != 1:
            continue
        gold0 = _seg_gold0(row)
        for a in row.get('actions') or []:
            if a.get('__type__') != 'LevelUp':
                continue
            if prev_level >= 5 and gold0 is not None and gold0 < 50:
                basis = a.get('auth', '') or ''
                full = a.get('dec_board_full')
                wait = a.get('dec_bench_wait_member')
                if not isinstance(full, bool):
                    full = None
                # 待上场腿在名册不可解析语境(未锁/空标签)恒不可得——
                # 披露键彼时恒 False 是语境缺失非证据(seed4 r3 实证,
                # arm1 未锁期合法发射;口径同 selfcalc.levelup_prereq_review)
                if not isinstance(wait, bool) \
                        or _sl.k_members_of_row(row) is None:
                    wait = None
                if full is None or wait is None:
                    prereq = '部分前置不可得(EV 总账需回放复演)'
                else:
                    prereq = f'板满={full}/待上场={wait}'
                out.append(_entry('D3', row, (
                    f'可疑项(追级授权前置):p1r{row.get("round_num")} '
                    f'升级(lv{prev_level} 时点金{gold0}<50);'
                    f'自报授权={basis or "(空)"};可自算前置:{prereq};'
                    '——请裁决: 授权成立 / 谎报臂名 / 越闸追级'),
                    evidence={'auth': basis, 'gold_before': gold0,
                              'level_before': prev_level,
                              'dec_board_full': full,
                              'dec_bench_wait_member': wait,
                              'note': ('m3_batch 逐击预算闸辖该击'
                                       if basis.startswith('m3_batch')
                                       else '非 m3_batch 自报:预算闸不经,本条即辖域补位')}))
            prev_level = ((row.get('state') or {}).get('level')
                          or prev_level)
    return out


# =====================================================================
# --- D4 冷启动方向件身份失配(ADR-0593 §4.1;C1 检测器面) ----------------
# =====================================================================

def d4_coldstart_identity(rows: list[dict]) -> list[dict]:
    """开局轮(p1 r≤2)买入的身份断言复核:classify_buy 同源自算。

    判定核 = selfcalc.buy_identity(channel 披露优先,classify_buy
    重算回退;与 C1 检查器迁移面同吃)。pair/off 自报走检查器机械
    判违面,不在本检测器重复。
    """
    out: list[dict] = []
    for row in rows:
        if (row.get('plane') or 1) != 1 \
                or (row.get('round_num') or 9) > 2:
            continue
        for a in row.get('actions') or []:
            if a.get('__type__') != 'BuyCard':
                continue
            reason = _normalize_buy_reason(a.get('reason') or '')
            if reason not in _sl.COLDSTART_IDENTITY_CLAIMS:
                continue
            identity = _sl.buy_identity(row, a)
            if identity == reason:
                continue   # 复核通过:不产条目(自洽)
            out.append(_entry('D4', row, (
                f'可疑项(冷启动):p{row.get("plane")}r'
                f'{row.get("round_num")} 买{(a.get("card") or {}).get("name")};'
                f'自报={reason};自算身份={identity}'
                '——请裁决: 门内放行 / 改标绕门'), evidence={
                    'claimed_reason': reason,
                    'self_calc_identity': identity,
                }))
    return out


# =====================================================================
# --- D5 种子回卖辖域自算(ADR-0593 §4.1;C7 检测器面,自算圈辖域) -------
# =====================================================================

def d5_seed_resell_scope(rows: list[dict]) -> list[dict]:
    """机械种子身份(引擎件∧购买时未持有)≤2 轮内被卖 → 条目。

    辖域不依赖自报 engine_seed(C7 的「改标脱离检查网」攻击面的
    检测器补位);买入轮小节加交叉引用行(ADR-0593 §4.1 归属规则)。
    种子身份判定核 = selfcalc(与 C7 检查器迁移面同吃)。

    「≤2 轮」窗口轴 = **行序单调轴**(ADR-0593 后果.5(L3)):round_num 是
    位面内编号跨位面重启(cw_state 注),行输入本就按 ts 单调排序
    (sim 轮装配 ts 递增/生产账本行按 (plane,round,ts) 排序),
    行下标差即全局轮距——位面间紧邻(如 p1 末轮买→p2 r1 卖)不漏报,
    跨面远距不再因编号回绕产生假阳。
    """
    out: list[dict] = []
    seed_buys: dict[str, dict] = {}   # name → {'idx': 行下标, 'row': 行}
    for idx, row in enumerate(rows):
        round_seen: set[str] = set()
        for a in row.get('actions') or []:
            t = a.get('__type__')
            if t == 'BuyCard':
                n = (a.get('card') or {}).get('name')
                if not n or n in round_seen:
                    continue
                round_seen.add(n)
                if _sl.is_engine_piece(n) \
                        and n not in _sl.held_names_upto(rows, idx):
                    seed_buys[n] = {'idx': idx, 'row': row}
            elif t == 'SellBench':
                n = a.get('name')
                if n not in seed_buys:
                    continue
                gap = idx - seed_buys[n]['idx']
                if 1 <= gap <= 2:
                    buy_row = seed_buys[n]['row']
                    out.append(_entry('D5', row, (
                        f'可疑项(种子回卖):p{row.get("plane")}'
                        f'r{row.get("round_num")} 买(行序-{gap})→卖 {n};'
                        f'自算种子身份依据='
                        '引擎件∧购买时未持有(不依赖自报分键)'
                        '——请裁决: 合法转化 / 种子归零振荡'), evidence={
                            'buy_round': buy_row.get('round_num'),
                            'sell_round': row.get('round_num'),
                            'round_gap': gap, 'name': n,
                        }))
                    out.append(_cross_ref('D5', buy_row,
                                          row.get('round_num') or 0))
                seed_buys.pop(n, None)
    return out


# =====================================================================
# --- D6 成型后过渡件④臂语境条目(ADR-0593 §4.1;C6 检测器面) ------------
# =====================================================================

def d6_transition_arm_context(rows: list[dict]) -> list[dict]:
    """成型后 ④ 臂买因的过渡件买入 → 语境打包条目(机械不复算)。

    定型位真值 = 策略单方认定且机械不可复算(时序歧义,C6 判定保留,
    见 seg_check_formed_still_buying_transition docstring);本检测器
    打包「④臂买入+邻近轮意向态+通道」交复盘者裁决定型位合法性。
    违例回落面(带④买因不在放行集/非④臂买过渡件)留在检查器。
    """
    from sr_od.application.currency_war.kernel.cw_card_identity import (
        transition_release_names,
    )
    release = transition_release_names()
    out: list[dict] = []
    formed = False
    for idx, row in enumerate(rows):
        if (row.get('plane') or 1) != 1:
            continue
        formed = formed or _seg_engines(row) >= 2
        if not formed:
            continue
        st_names = {d.get('char_id') for d in
                    ((row.get('state') or {}).get('deployed') or [])} \
            | {b.get('char_id') for b in
               ((row.get('state') or {}).get('bench') or [])
               if isinstance(b, dict)}
        target_label = row.get('target_comp') or ''
        labels = target_label.removeprefix('过渡配方·').split('+')
        for a in row.get('actions') or []:
            if a.get('__type__') != 'BuyCard':
                continue
            name = (a.get('card') or {}).get('name') or ''
            # 通道身份:channel 披露优先(sim),生产 BuyCard 行无该键
            # → classify_buy 同源重算(ADR-0593 后果.5 附加①,生产面不再恒哑)
            identity_ch = _sl.buy_identity(row, a)
            if identity_ch not in ('engine', 'pair'):
                continue
            if name in st_names:
                continue
            if any(name in _seg_target_roster(lb) for lb in labels):
                continue
            if a.get('reason') != 'transition_component_buy' \
                    or name not in release:
                continue   # 违例回落面归检查器;只辖放行面语境条目
            prev = rows[idx - 1] if idx > 0 else {}
            nxt = rows[idx + 1] if idx + 1 < len(rows) else {}

            def _phase(r: dict) -> str:
                v = r.get('v3_intention') or {}
                if not isinstance(v, dict):
                    return '(不可得)'
                return (f'{v.get("phase") or "?"}'
                        f'/{v.get("locked_comp") or "未锁"}')

            out.append(_entry('D6', row, (
                f'可疑项(成型后过渡件):p1r{row.get("round_num")} '
                f'买{name}(身份={identity_ch});自报④臂=真'
                f'(放行集内);邻近意向态: r{prev.get("round_num") or "?"}'
                f'={_phase(prev)} / r{row.get("round_num")}='
                f'{_phase(row)} / r{nxt.get("round_num") or "?"}'
                f'={_phase(nxt)}'
                '——请裁决: 未定型期合法前瞻 / 越辖买入'), evidence={
                    'bought': name, 'identity': identity_ch,
                    'target_comp': target_label,
                }))
    return out


# =====================================================================
# --- D7/D8/D9 机械段检查的条目化包装(ADR-0593 §4.1:现函数逻辑即检测器)
# =====================================================================

def _wrap_seg(mode: str, fn: Callable[[list[dict]], list[dict]],
              rows: list[dict], title: str,
              question: str) -> list[dict]:
    """段级检查事件 → 可疑项条目(判定核单一源 = 被包装函数)。"""
    out: list[dict] = []
    for ev in fn(rows) or []:
        row = {'plane': ev.get('plane'), 'round_num': ev.get('round_num'),
               'sim': {'node': (ev.get('node') or '')
                       if isinstance(ev.get('node'), str) else ''}}
        out.append(_entry(mode, row, (
            f'可疑项({title}):p{ev.get("plane")}'
            f'r{ev.get("round_num")} {ev.get("detail")}'
            f'——请裁决: {question}'), evidence={
                'check_event': {k: v for k, v in ev.items()
                                if k not in ('plane', 'round_num')},
            }))
    return out


def d7_break_interest(rows: list[dict]) -> list[dict]:
    """破息无例外条目(判定核 = seg_check_break_interest_exception;
    例外①吃引擎自算 channel、②连胜自算重放——非自报,ADR-0593 §4.1)。"""
    return _wrap_seg('D7', seg_check_break_interest_exception, rows,
                     '破息无例外', '例外成立 / 无授权破息')


def d8_blood_budget(rows: list[dict]) -> list[dict]:
    """血预算停手族条目(停升级 P1/P2+停刷新+不可信帧升级;机械)。"""
    out: list[dict] = []
    out += _wrap_seg('D8', seg_check_p1_blood_budget_levelup, rows,
                     '血预算', '急救必要 / 追级泵未停')
    out += _wrap_seg('D8', seg_check_p2_blood_budget_levelup, rows,
                     '血预算', '急救必要 / 追级泵未停')
    out += _wrap_seg('D8', seg_check_p1_blood_budget_refresh, rows,
                     '血预算', '终止豁免辖内 / 停付未生效')
    out += _wrap_seg('D8', seg_check_untrusted_hp_levelup, rows,
                     '血预算', '观测修复 / 不可信帧违规')
    return out


def d9_p2_bleed_gold_stack(rows: list[dict]) -> list[dict]:
    """P2 血降金堆条目(判定核 = seg_check_p2_bleed_gold_stack;
    锚 = 连击阈值达成轮,被跨越轮加交叉引用行——ADR-0593 §4.1-D9)。"""
    out: list[dict] = []
    events = seg_check_p2_bleed_gold_stack(rows) or []
    anchor_rn: int | None = None
    for ev in events:
        streak = int(ev.get('streak') or 0)
        row = {'plane': ev.get('plane'), 'round_num': ev.get('round_num'),
               'sim': {'node': ''}}
        if streak == 2:
            anchor_rn = ev.get('round_num')
            out.append(_entry('D9', row, (
                f'可疑项(P2 溢余堆积):p2r{ev.get("round_num")} '
                f'金 {ev.get("prev_gold")}→{ev.get("gold")} 未泄、hp '
                f'{ev.get("prev_hp")}→{ev.get("hp")} 在掉(第 2 连轮,锚)'
                '——请裁决: 定向花缺失 / 合法攒息'), evidence={
                    'streak': streak, 'anchor': True,
                }))
        elif streak > 2 and anchor_rn is not None:
            out.append(_cross_ref('D9', row, int(anchor_rn)))
        else:
            out.append(_entry('D9', row, (
                f'可疑项(P2 溢余堆积):p2r{ev.get("round_num")} '
                f'金 {ev.get("prev_gold")}→{ev.get("gold")}、hp '
                f'{ev.get("prev_hp")}→{ev.get("hp")}'
                '——请裁决: 定向花缺失 / 合法攒息'), evidence={
                    'streak': streak,
                }))
    return out


# =====================================================================
# --- D10/D11 机械事实条目(披露键现读/注册表现算) -------------------
# =====================================================================

def d10_deploy_lag(rows: list[dict]) -> list[dict]:
    """部署欠载条目:``sim.deploy_lag_units``>0(引擎执行点自算披露;
    ADR-0593 §4.1-D10。数据源单一 = 该披露键,检查器同吃,无第二实现)。"""
    out: list[dict] = []
    for row in rows:
        n = (row.get('sim') or {}).get('deploy_lag_units') or 0
        if int(n) > 0:
            out.append(_entry('D10', row, (
                f'可疑项(围栏认可未上):p{row.get("plane")}'
                f'r{row.get("round_num")} 残余可上 {n} 件'
                '(deploy_lag_units 引擎披露)'
                '——请裁决: 部署时序回归 / 合法 hold'), evidence={
                    'deploy_lag_units': int(n),
                }))
    return out


def d11_phantom_and_slot(rows: list[dict]) -> list[dict]:
    """幻影/注册表外实体上身、槽超买条目(纯机械;注册表单一源 =
    EQUIPMENT_ROSTER,与检查器镜像纪律同款——值漂移由双向锁辖)。"""
    from sr_od.application.currency_war.data.cw_equipment_data import (
        EQUIPMENT_ROSTER,
    )
    out: list[dict] = []
    for row in rows:
        st = row.get('state') or {}
        phantom: list[str] = []
        for eq in st.get('equipped') or []:
            name = eq.get('equip')
            if name and name not in EQUIPMENT_ROSTER:
                phantom.append(f'{name}→{eq.get("char")}')
        for e in st.get('owned_equips') or []:
            if e and e not in EQUIPMENT_ROSTER:
                phantom.append(f'{e}(owned)')
        if phantom:
            out.append(_entry('D11', row, (
                f'可疑项(非法实体):p{row.get("plane")}'
                f'r{row.get("round_num")} 注册表外装备 {phantom}'
                '——请裁决: 注册表更新缺失 / 幻影实体回归'), evidence={
                    'phantom_names': phantom,
                }))
        # 槽超买(波内同名买入 > 供给槽位;与 check_shop_slot_consumption
        # 同判据的镜像消费——ADR-0593 §4.3:机械事实留检查器,本条目化面
        # 供复盘定位;两处漂移由测试仓双向锁辖)
        waves = (row.get('sim') or {}).get('shop_waves') or []
        if waves:
            def _supply(wave: dict) -> dict[str, int]:
                s: dict[str, int] = {}
                for c in wave.get('cards') or []:
                    n = c.get('name')
                    if n:
                        s[n] = s.get(n, 0) + 1
                return s
            supply = _supply(waves[0])
            bought: dict[str, int] = {}
            wi = 0
            for a in row.get('actions') or []:
                t = a.get('__type__')
                if t == 'RefreshShop':
                    wi += 1
                    if wi >= len(waves):
                        break
                    supply = _supply(waves[wi])
                    bought = {}
                elif t == 'BuyCard':
                    n = (a.get('card') or {}).get('name')
                    if not n:
                        continue
                    bought[n] = bought.get(n, 0) + 1
                    if bought[n] > supply.get(n, 0):
                        out.append(_entry('D11', row, (
                            f'可疑项(槽超买):p{row.get("plane")}'
                            f'r{row.get("round_num")} {n} 波内买 '
                            f'{bought[n]} 份 > 供给 {supply.get(n, 0)} 槽'
                            '——请裁决: 账本写坏 / 槽消费缺失'), evidence={
                                'name': n, 'bought': bought[n],
                                'supply': supply.get(n, 0),
                            }))
    return out


#: 检测器注册表(id → fn(rows)->list[entry];复盘模板生成器消费面)
_SUSPECT_DETECTORS: dict[str, Callable[[list[dict]], list[dict]]] = {
    'D1': d1_same_round_pair_review,
    'D2': d2_overflow_stop_mismatch,
    'D3': d3_levelup_prereq,
    'D4': d4_coldstart_identity,
    'D5': d5_seed_resell_scope,
    'D6': d6_transition_arm_context,
    'D7': d7_break_interest,
    'D8': d8_blood_budget,
    'D9': d9_p2_bleed_gold_stack,
    'D10': d10_deploy_lag,
    'D11': d11_phantom_and_slot,
}


def detector_ids() -> list[str]:
    """检测器 id 清单(生成器元信息/测试登记门用;自然序 D2<D10)。"""
    return sorted(_SUSPECT_DETECTORS, key=lambda m: int(m[1:]))


def run_suspect_checks(rows: list[dict]) -> list[dict]:
    """对单局账本行跑全部检测器 → 可疑项条目列表。

    条目按 (plane, round_num, mode) 排序——模板生成器按序插入对应
    节点小节;检测器异常不炸面(与 run_segment_checks 同纪律,异常
    计入 ``_errors``)。
    """
    out: list[dict] = []
    errors: dict[str, str] = {}
    for mode in detector_ids():
        try:
            out.extend(_SUSPECT_DETECTORS[mode](rows) or [])
        except Exception as exc:   # noqa: BLE001  检测器异常不炸生成
            errors[mode] = repr(exc)
    out.sort(key=lambda e: (e.get('plane') or 0, e.get('round_num') or 0,
                            int(str(e.get('mode', 'D0'))[1:])
                            if str(e.get('mode', '')).startswith('D')
                            else 99))
    if errors:
        out.append({'mode': '_errors', 'errors': errors,
                    'detail': '检测器异常(见 errors)'})
    return out
