"""货币战争 期望态(Expected State)infra(W971 EXPECTED_STATE.md FINAL v3.1;P4)。

机制(02-state §4.3 定稿):操作 op 执行后,按逻辑规则推进 session 对应字段
并登记**期望态条目**(谁产生/哪一轮/什么字段族);回到能识别该字段的画面
(覆盖点)时实读覆盖 actual,覆盖时对条目 diff 对账——不一致当场留证
(``expected_reconcile.jsonl``),一致或到账即清账。决策读路径不变:决策永远
读 session 字段本体(= 期望态优先的最新值)。

雏形收编 = 载体统一、语义分道(EXPECTED_STATE §1,禁一刀切):
- **buy 通道**:保留 ``BuyExpect`` 载体 + DD-005 降级 + 消费即清;
  expected_state 仅统一载体挂载点(kind='buy_expect',条目 = 整段 BuyExpect);
- **xp 通道**:保留 XpLedger 锚点 + 轮界重锚(外生经验流吸收进锚点,
  对账差值不判罚,累计披露 exogenous_xp)——本模块只做簿记镜像;
- **tracked 族**:``cw_reconcile.reconcile_tracking`` 裁决器语义原样
  (双空读守卫/star 回退防抖/合成特效帧态门/银狼升费豁免)——expected_state
  只接管登记 + 清账簿记,不改裁决语义。

分包边界:本模块在 kernel(决策核与执行面共同消费的纯函数);留证 IO
(jsonl 追加)经注入槽 ``set_evidence_sink`` 缺省关——生产武装点在 app
装配(``decision_assembly.install_obs_ports`` 同点),测试零真实落盘
(测试纪律:不写真实 .debug)。
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_exec_state import exec_state_of
from sr_od.application.currency_war.kernel.cw_merge_simulate import (
    merge_simulate,
)
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    ClickSpheres,
    DeployMove,
    LevelUp,
    PickBoxCard,
    PrepAction,
    RunBuyPhase,
    SellBench,
    SellDeployed,
)
from sr_od.application.currency_war.kernel.cw_state import (
    DEPLOYED_FRONT_CAPACITY,
    BenchChar,
    iter_occupied,
    sell_refund,
)

# ============================================================ 容器与条目


@dataclass
class ExpectedEntry:
    """期望态条目(EXPECTED_STATE §1 数据结构)。

    [字段定义] path = 字段路径(身份寻址:tracked 族 = 槽位路径,比对按
    身份匹配豁免位移;simple 族 = session/last_state 字段名);value = 推进值
    (str 含「待实读」标记 = 到账登记区粗粒度条目,覆盖点只清账不 diff);
    produced_by = 产生者 op 名;at_round = 产生轮次标记('p1-r4' 形);
    kind = 字段族(buy_expect/xp_ledger/tracked/gold/xp/owned/pending_reward/
    merge_group...);confirm_point = 绑定的确认覆盖点(F7:条目在不可确认
    覆盖点不计 stall 时钟、不做 diff,仅透传);group_id = 合成链组条目 id
    (一次 BuyCard 的一组互相依赖槽位变更打包,组确认清账——禁逐 path
    独立清账产生半确认中间态)。
    """
    path: str
    value: Any
    produced_by: str
    at_round: str
    kind: str
    confirm_point: str = 'prep_obs'
    group_id: str = ''
    # diff 已上报标记(第六局复盘缺陷③去重):同条目只留证一次——重复
    # diff(清账失败/覆盖点多次经过)静默清账不再写 expected_reconcile;
    # 条目被 apply_op_effect 重新登记(last-wins 新对象)即复位 → 可重报。
    reported: bool = False


def register_expected(session, entry: ExpectedEntry) -> None:
    """登记一条期望态(exec_state_of(session).expected_state 容器;缺容器时惰性建——
    兼容未升级的 session 构造路径,如旧回放)。同 path 覆盖(last-wins)。"""
    store = getattr(exec_state_of(session), 'expected_state', None)
    if store is None:
        store = {}
        exec_state_of(session).expected_state = store
    store[entry.path] = entry


def clear_expected(session, paths: list[str]) -> None:
    """清账(覆盖点确认后;组条目按 group_id 整组清)。"""
    store = getattr(exec_state_of(session), 'expected_state', None)
    if not store:
        return
    group_ids: set[str] = set()
    for p in paths:
        e = store.pop(p, None)
        if e is not None and e.group_id:
            group_ids.add(e.group_id)
    if group_ids:
        for p in [p for p, e in store.items() if e.group_id in group_ids]:
            del store[p]


def expected_round_key(session) -> str:
    """当前轮次标记('p{plane}-r{round}';last_state 缺失 = '?'。"""
    st = getattr(session, 'last_state', None)
    if st is None:
        return '?'
    return f"p{int(getattr(st, 'plane', 1) or 1)}-r{int(getattr(st, 'round_num', 1) or 1)}"


# ============================================================ 留证注入槽

#: 留证 sink(签名:dict 行)。缺省关 = 只 log 不落盘;生产武装点 =
#: decision_assembly.install_obs_ports(追加 expected_reconcile.jsonl)。
_EVIDENCE_SINK: Callable[[dict], None] | None = None


def set_evidence_sink(fn: Callable[[dict], None] | None) -> None:
    """注入留证 sink(生产 = expected_reconcile.jsonl 追加;None = 关)。"""
    global _EVIDENCE_SINK
    _EVIDENCE_SINK = fn


def _emit_evidence(row: dict) -> None:
    try:
        if _EVIDENCE_SINK is not None:
            row = dict(row)
            row.setdefault('ts', time.time())
            _EVIDENCE_SINK(row)
    except Exception as e:  # noqa: BLE001  留证 best-effort
        log.debug(f'[cw-expect] evidence sink skip: {e}')


# ============================================================ apply_op_effect


def _char_fee(name: str) -> int | None:
    """角色招募费(注册表单一源);未知 → None(回金不可算 → 到账登记)。"""
    try:
        from sr_od.application.currency_war.data.cw_chars import CHARACTERS
        ch = CHARACTERS.get(name)
        return int(getattr(ch, 'cost', 0) or 0) or None
    except Exception:  # noqa: BLE001  注册表异常按未知处理
        return None


def _session_tracked(session) -> tuple[list[BenchChar], list[BenchChar | None]]:
    m = getattr(exec_state_of(session), 'tracked_bench_chars', None) or []
    d = getattr(exec_state_of(session), 'tracked_deployed', None) or []
    return list(m), list(d)


def _advance_gold(session, delta: int) -> None:
    """last_state.gold 期望推进(可为负;None 视 0 基线——金账对账由
    商店波顶/结算屏可信读覆盖修正)。"""
    st = getattr(session, 'last_state', None)
    if st is None:
        return
    base = getattr(st, 'gold', 0) or 0
    st.gold = base + delta


def apply_op_effect(session, action: PrepAction | dict, *,
                    produced_by: str = 'PrepActionExecutor',
                    detail: str = '',
                    pending_buy_expect: object = None) -> list[dict]:
    """原子 op 的期望态推进(EXPECTED_STATE §3 表;两执行面同源入口)。

    返回效果列表 [{path, value, kind}](组合动作子动作效果上抛形态)。
    登记进 exec_state_of(session).expected_state;同时推进可计算的 session 字段本体
    (gold/owned/xp——xp 通道分道:XpLedger 是权威账本,本函数只在
    显式传 pending 时做簿记镜像,不双写)。
    显式不建模盲区(EXPECTED_STATE §6):``_handle_bench_full`` 席满急救
    (买经验×10 + 卖前几槽)不经执行器 → 不在登记面,该形态不一致由
    既有对账通道留证(声明而非遗漏)。
    """
    effects: list[dict] = []
    if session is None:
        return effects
    at_round = expected_round_key(session)

    def _reg(path: str, value: Any, kind: str,
             confirm_point: str = 'prep_obs', group_id: str = '') -> None:
        register_expected(session, ExpectedEntry(
            path=path, value=value, produced_by=produced_by,
            at_round=at_round, kind=kind,
            confirm_point=confirm_point, group_id=group_id))
        effects.append({'path': path, 'value': value, 'kind': kind})

    if isinstance(action, SellBench):
        bench, _dep = _session_tracked(session)
        bc = next((b for b in iter_occupied(bench) if b.slot == action.slot), None)
        fee = _char_fee(bc.char_id) if bc is not None else None
        if bc is not None and fee is not None:
            refund = sell_refund(bc.star, fee)
            _advance_gold(session, refund)
            _reg('gold', f'+{refund}(sell_refund {bc.star}星×{fee}费)',
                 'gold', confirm_point='shop_wave_top')
        elif bc is not None:
            _reg('gold', '+售价(待实读)', 'gold', confirm_point='shop_wave_top')
        if bc is not None:
            _reg(f'tracked_bench_chars[{action.slot}]', None, 'tracked',
                 group_id=f'sell-b{action.slot}-{at_round}')
    elif isinstance(action, SellDeployed):
        _bench, dep = _session_tracked(session)
        idx = (action.slot - 1 if action.row == 'front'
               else DEPLOYED_FRONT_CAPACITY + action.slot - 1)
        bc = dep[idx] if 0 <= idx < len(dep) else None
        fee = _char_fee(bc.char_id) if bc is not None else None
        if bc is not None and fee is not None:
            refund = sell_refund(bc.star, fee)
            _advance_gold(session, refund)
            _reg('gold', f'+{refund}(sell_refund {bc.star}星×{fee}费)',
                 'gold', confirm_point='shop_wave_top')
            for eq in (getattr(bc, 'equips', None) or []):
                _reg(f'owned[{eq}]', '+1(卖场上装备全额返还)', 'owned')
        elif bc is not None:
            _reg('gold', '+售价(待实读)', 'gold', confirm_point='shop_wave_top')
        if bc is not None:
            _reg(f'tracked_deployed[{idx}]', None, 'tracked',
                 group_id=f'sell-d{idx}-{at_round}')
    elif isinstance(action, DeployMove):
        # 位移推进本体由执行器 _track_move_deployed 承担(单一写者,防双写);
        # 本登记 = 期望态簿记(目标槽身份,覆盖点按身份匹配豁免位移)。
        bench, _dep = _session_tracked(session)
        bc = next((b for b in iter_occupied(bench)
                   if b.slot == action.from_slot), None)
        if bc is not None:
            _reg(f'deployed.{action.to_row}.{action.to_slot}', bc.char_id,
                 'tracked', group_id=f'deploy-{bc.char_id}-{at_round}')
    elif isinstance(action, LevelUp):
        # xp 分道:XpLedger 权威(锚点+轮界重锚);此处仅簿记镜像条目。
        led = getattr(exec_state_of(session), 'xp_expect_ledger', None)
        if led is not None and getattr(led, 'anchored', False):
            _reg('xp_ledger', f'lv{led.level} xp{led.xp_cur}',
                 'xp_ledger', confirm_point='prep_obs')
        _reg('gold', '-经验点击(待实读)' if not detail else f'-经验({detail})',
             'gold', confirm_point='shop_wave_top')
    elif isinstance(action, ClickSpheres):
        n = max(1, getattr(action, 'max_k', 1))
        _reg('pending_reward', f'球×{n}(待实读)', 'pending_reward')
    elif isinstance(action, PickBoxCard):
        chosen = ''
        for token in (detail or '').replace('选卡', ' ').split():
            chosen = token.strip()
            break
        if chosen:
            owned = list(getattr(session, 'last_owned_equips', None) or [])
            owned.append(chosen)
            session.last_owned_equips = owned
            _reg(f'owned[{chosen}]', '+1(武装箱选卡)', 'owned')
    elif isinstance(action, RunBuyPhase):
        # buy 分道:BuyExpect 载体原样,expected_state 仅挂载点统一。
        expect = pending_buy_expect or getattr(exec_state_of(session), 'pending_buy_expect', None)
        if expect is not None:
            _reg('buy_expect', expect, 'buy_expect')
    elif isinstance(action, dict):
        # 到账登记区(overlay 确认类;粗粒度 expected,{'op','item'} 形态)
        op = action.get('op', '')
        item = action.get('item', '')
        if op in ('ConfirmSupply', 'ConfirmBox') and item:
            owned = list(getattr(session, 'last_owned_equips', None) or [])
            owned.append(item)
            session.last_owned_equips = owned
            _reg(f'owned[{item}]', f'+1({op})', 'owned')
        elif op == 'ConfirmStrategy' and item:
            _reg(f'active_strategies[{item}]', '已选(效果走台账)',
                 'strategy')
        elif op == 'ConfirmTome' and item:
            owned = list(getattr(session, 'last_owned_equips', None) or [])
            owned.append(item)
            session.last_owned_equips = owned
            _reg(f'owned[{item}]', '+1(秘典)', 'owned')
        elif op == 'BuyCard':
            # 精确建模区 dict 形态(模拟/离线入口):走合成引擎推进 tracked
            _apply_buy_card(session, action, at_round, _reg)
        # 其余 dict op(Refresh/纯读/画面态)零登记——理由见 §3 D 区
    else:
        # 显式不更新理由(§3 铁律:无例外枚举):
        # - OpenBox/OpenTome:箱/典籍不消失(仅画面态,消耗在选卡确认);
        # - OpenShop(含 read_only)/EnsureShop*:画面态周转,零局状态变更;
        # - StartBattle:进战斗,hp/gold/streak 由结算屏覆盖点接管;
        # - RunDeploy/RunEquip:组合动作,子动作效果经各自原子通道登记;
        #   (RunEquip 装备分布期望态:CwOpEquipAll 逐件穿戴的 owned/角色 equips
        #   推进待装备分布接线批——本批登记缺口已记实现决策。)
        pass
    return effects


def _apply_buy_card(session, action: dict, at_round: str, _reg) -> None:
    """dict 形 BuyCard 的合成链推进(merge_simulate 单一引擎)。"""
    name = action.get('name', '')
    star = int(action.get('star', 1) or 1)
    k = int(action.get('k', 1) or 1)
    cost = int(action.get('cost', 0) or 0)
    bench, dep = _session_tracked(session)
    res = merge_simulate(bench, dep, name, star, k=k,
                         in_shop_count=action.get('in_shop_count'))
    if cost:
        _advance_gold(session, -cost * max(1, res.buy_k or 1))
        _reg('gold', f"-{cost * max(1, res.buy_k or 1)}(买牌×{res.buy_k})",
             'gold', confirm_point='shop_wave_top')
    group = f'buy-{name}-{at_round}'
    _reg(f'tracked_bench_chars[{name}@{star}星]', f'×{res.buy_k}(落点/合成链)',
         'merge_group' if res.chain else 'tracked', group_id=group)
    for step in res.chain:
        _reg(f'merge_chain[{step.name}:{step.from_star}->{step.to_star}]',
             f'落点={step.landing_kind}:{step.landing_slot} '
             f'继承={";".join(step.inherited_equips) or "无"}',
             'merge_group', group_id=group)


# ============================================================ 覆盖点 reconcile

#: diff 五分类(EXPECTED_STATE §5)标签
DIFF_MERGE_MODEL = 'merge_model'          # 合成落点/星级不符(引擎模型错)
DIFF_OP_EFFECT = 'op_effect_bug'          # apply_op_effect 实现错
DIFF_GAME_SIDE = 'game_side_change'       # 非 op 游戏侧自变
DIFF_EXOGENOUS = 'exogenous'              # 外生流(轮界差值,吸收不判罚)
DIFF_UNMODELED = 'unmodeled'              # 未建模行为
DIFF_PERCEPTION = 'perception'            # 识别缺陷


def reconcile_expected(session, coverage_point: str,
                       actual: dict[str, tuple[Any, bool]], *,
                       op: str = 'reconcile') -> list[dict]:
    """覆盖点对账(EXPECTED_STATE §2/§5;纯簿记,零决策行为)。

    Args:
        session: StrategySession(expected_state 容器宿主)。
        coverage_point: 覆盖点名('prep_obs'/'shop_wave_top'/'settlement')。
        actual: {path: (实读值, 可信)}——可信门(F5)由调用方按覆盖点声明
            (如备战观察点 gold 不可信 → 不进本 dict 即不覆盖不清账)。
            value=None = 该路径本帧未读到 → 条目保留不清账(宁缺勿造)。

    Returns:
        diff 行列表(空 = 全部可比项一致或无条目)。
    """
    store = getattr(exec_state_of(session), 'expected_state', None)
    if not store:
        return []
    diffs: list[dict] = []
    confirmed: list[str] = []
    for path, entry in list(store.items()):
        if entry.confirm_point != coverage_point:
            continue   # 条目绑覆盖点(F7):不可确认点透传
        if path not in actual:
            continue   # 本帧未读/字段族不可信 → 保留
        value, trusted = actual[path]
        if not trusted:
            continue
        if value is None:
            continue   # 本帧未实读 → 条目保留(宁缺勿造,不误清)
        if isinstance(entry.value, str) and '待实读' in entry.value:
            confirmed.append(path)   # 到账登记区:可信读即清账,不 diff
            continue
        if entry.kind == 'gold':
            # 金账条目 = 到账登记(delta 描述,非绝对值);精确金对账归
            # spend 账本既有通道(§3 #1「2星直出 → 金账对账暴露」口径),
            # expected_state 只做登记+可信读清账,不做绝对值 diff。
            confirmed.append(path)
            continue
        if value is None:
            continue
        if not _values_match(entry, value):
            # P4R4 缺陷③去重(第六局复盘):同条目只留证一次——重复 diff
            # (上一版漏了「diff 后清账」→ 下轮同覆盖点重报)静默清账;
            # 重新登记(last-wins 新对象 reported=False)即可重报。
            if getattr(entry, 'reported', False):
                confirmed.append(path)
                continue
            diffs.append(_record_diff(session, entry, value, op, coverage_point))
            entry.reported = True
        # P4R4 缺陷③主修:留证后同样清账(旧版只把一致项加 confirmed,
        # mismatch 条目滞留 → 下轮同覆盖点重复 diff)。实读是更新的事实,
        # 保留只会反复报同一 diff(对账是证据流,不是重试流)。
        confirmed.append(path)
    if confirmed:
        clear_expected(session, confirmed)
    return diffs


def _values_match(entry: ExpectedEntry, actual_value: Any) -> bool:
    """期望 vs 实读比对判据(身份寻址维度,EXPECTED_STATE §1)。

    - tracked 族:path 含槽位,value = 期望身份;实读含该身份(任意槽)
      即满足(身份匹配豁免位移——落点模型槽位差归组条目 diff,不在本判据
      误报);实读为 None/空 = 不评(调用侧已拦)。
    - 标量族:直接相等。
    """
    if entry.kind in ('tracked', 'merge_group'):
        want = str(entry.value)
        if isinstance(actual_value, str):
            return (not want or want in actual_value
                    or actual_value in want or want == actual_value)
        return True   # 结构化实读(槽位表)由专项对账通道(reconcile_tracking)判
    return entry.value == actual_value


def _record_diff(session, entry: ExpectedEntry, actual_value: Any,
                 op: str, coverage_point: str) -> dict:
    """diff 留证 + 分类(EXPECTED_STATE §5 五分类;xp 外生流吸收)。"""
    if entry.kind == 'xp_ledger':
        diff_class = DIFF_EXOGENOUS
    elif entry.kind in ('merge_group',):
        diff_class = DIFF_MERGE_MODEL
    elif entry.kind == 'tracked':
        diff_class = DIFF_PERCEPTION
    else:
        diff_class = DIFF_OP_EFFECT
    row = {
        'round': entry.at_round,
        'op': entry.produced_by,
        'reconcile_op': op,
        'coverage_point': coverage_point,
        'path': entry.path,
        'kind': entry.kind,
        'expected': _to_str(entry.value),
        'actual': _to_str(actual_value),
        'diff_class': diff_class,
    }
    _emit_evidence(row)
    log.warning(f'[cw!][expect] 覆盖点对账不一致({coverage_point}):'
                f'{entry.path} 期望[{row["expected"]}] 实读[{row["actual"]}]'
                f' → {diff_class}(expected_reconcile)')
    # 分类处置:外生流吸收进锚点(不判罚),其余条目保留待复核?
    # 裁决(EXPECTED_STATE §5):留证后条目一律清账——实读是更新的事实,
    # 保留会让后续帧反复报同一 diff(对账是证据流,不是重试流)。
    return row


def _to_str(v: Any) -> str:
    try:
        return str(getattr(v, 'summary', None) or v)
    except Exception:  # noqa: BLE001
        return '<unprintable>'
