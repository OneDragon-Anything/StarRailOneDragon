"""货币战争 执行域领域模型与纯函数宿主(cw_exec_state;无状态面)。

本模块不承载跨调用状态——原执行层状态载体已整体退役,局内事实宿主 =
GameState(kernel/cw_game_state.py)。现辖三类领域函数:

- 确认族到账推进:``apply_confirm_effect``(两态制标准语义,ADR-0651;
  原 apply_op_effect 动作类分支随动作 op 重组批④ 收编 op 自上报后瘦身);
- 槽位表领域模型:bench/deployed 槽位语义 helpers(benchchar-retirement
  P1 起容器原生:bench = ``BenchSlot | None`` 槽表、deployed = ``Unit | None``
  下标槽表 + 容器行域↔下标派生对)与物理(排,槽号)↔ 表下标换算
  (deployed_row_slot / deployed_idx_of 互逆对);观察读链直产容器形状
  (obs/cw_identity_obs),本模块无换形适配层;
- 位面节点序列台账访问:get_node_ledger / ledger_node_type /
  ledger_update_plane 与 fill_boss_by_position(台账值载体
  ``PlaneNodeLedger`` 住 kernel/cw_game_state.py,本模块运行时转发,
  保持既有 import 路径不断链)。
"""
from __future__ import annotations

# 台账值载体(运行时转发,非仅注解):类本体住 kernel/cw_game_state.py
# (宿主 = 容器非 Field 簿记 GameState.plane_node_sequences 所在模块),本模块
# 转发保持 cw_vocab 转出口与既有 import 路径不断链(消费面零改动的成立前提)。
# cw_game_state 模块级依赖不反向触达本模块
# (惰性 import 面),此模块级引入不成环。
from sr_od.application.currency_war.kernel.cw_game_state import (
    BenchSlot,
    PlaneNodeLedger,
    Unit,
)

# ============================================================ 确认族到账推进
# (波 5b 自 kernel/cw_expected_state 迁入;动作 op 重组批④ 瘦身改名:
# 动作词表类分支收编 op 自上报(kernel/cw_action_report),本口只剩 dict
# 确认族,消费点 = _overlay_confirm.register_confirm_arrival。
# ⚠️ 动作词表/合成引擎(cw_vocab/cw_merge_simulate)模块级 import 本模块
# (转出口),本模块对其依赖一律函数内惰性 import,模块级引入会成环——
# 沿用本仓懒加载惯例。)

def _session_tracked(session) -> tuple[list, list]:
    # tracked 主账宿主 = 容器簿记 GameState.tracked_books
    #(kernel/cw_game_state.py;lazy import 防模块环,同 _advance_gold 惯例)。
    # P1 起元素形状 = bench: BenchSlot | None / deployed: Unit | None(§2.3)。
    from sr_od.application.currency_war.kernel.cw_game_state import (
        game_state_of,
    )
    books = game_state_of(session).tracked_books
    return list(books.bench or []), list(books.deployed or [])


def _advance_gold(session, delta: int, *,
                  produced_by: str = 'PrepActionExecutor') -> None:
    """op 逻辑效果的金账直推(last_state 链退役后宿主 = 容器单例):
    ``game_state_of(session).gold`` 经 logic_action 通道 write_logic
    (可为负;现值 None 视 0 基线——金账由商店波顶/结算屏可信读覆盖
    修正,观察赢)。渠道面 = family='logic_action' + actor
    'PrepActionExecutor'(在册;登记类属 = 动作 op 逻辑效果推进宿主,
    produced_by 携调用面标识留证)。
    """
    try:
        from sr_od.application.currency_war.kernel.cw_game_state import (
            ChannelSig,
            game_state_of,
        )
        gs = game_state_of(session)
        base = gs.gold.value
        gs.write_logic(gs.gold, int(base or 0) + int(delta),
                       produced_by=produced_by,
                       evidence='op_effect_gold_delta',
                       sig=ChannelSig(family='logic_action',
                                      actor='PrepActionExecutor',
                                      mode='compute'))
    except Exception:   # noqa: BLE001  逻辑推进不阻塞执行链(观察覆盖兜底)
        pass


def _owned_add(session, item: str) -> None:
    """owned 库存逻辑推进:+1 件(选卡/确认到账类;终态契约 §B:单一源 =
    gs.equips,现读-改写-回写)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        ChannelSig,
        game_state_of,
    )
    _gs = game_state_of(session)
    owned = list(_gs.equips.value or [])
    owned.append(item)
    _gs.write_logic(_gs.equips, owned, produced_by='PrepActionExecutor',
                    evidence=f'owned[{item}] +1',
                    sig=ChannelSig(family='logic_action',
                                   actor='PrepActionExecutor',
                                   screen='', mode='compute'))


def apply_confirm_effect(session, payload: dict, *,
                         produced_by: str = 'PrepActionExecutor',
                         detail: str = '') -> list[dict]:
    """确认类到账 dict 的逻辑效果推进(原 ``apply_op_effect`` 瘦身改名,
    动作 op 重组批④:动作词表类分支已全量收编各 op 自上报
    (kernel/cw_action_report 函数族),本口只剩 dict 确认族;消费方 =
    ``_overlay_confirm.register_confirm_arrival``)。

    语义(逐行自原 dict 分支平移,零行为):
    - ``ConfirmSupply``/``ConfirmBox``/``ConfirmTome`` 且 item 在场:
      owned +1(终态契约 §B:单一源 = gs.equips,现读-改写-回写);
    - ``ConfirmExpertCash``:现金为王弃卡取现金固定回金 +4 金账直推;
    - ``CwActionBuyCardParam``(dict 形,模拟/离线入口):合成引擎算
      购买数,金账逻辑推进;
    - 其余/未知 op = 零推进(显式不建模面,原 else-pass 语义存续:
      ConfirmStrategy 本体追加归 handler 确认成功后既有写点;
      ConfirmMegastar/ConfirmPartner chosen_* 写端 = 各 handler)。

    返回推进清单 [{path, value, kind}](本函数实际写过的字段;
    best-effort 记录面)。"""
    effects: list[dict] = []
    if session is None or not isinstance(payload, dict):
        return effects

    def _eff(path: str, value, kind: str) -> None:
        effects.append({'path': path, 'value': value, 'kind': kind})

    op = payload.get('op', '')
    item = payload.get('item', '')
    if op in ('ConfirmSupply', 'ConfirmBox', 'ConfirmTome') and item:
        _owned_add(session, item)
        _eff(f'owned[{item}]', f'+1({op})', 'owned')
    elif op == 'ConfirmExpertCash':
        # 专家邀请函「现金为王」:弃卡取现金固定回金 +4 金账直推
        # (原 _overlay_confirm 内联 last_state 直推随链退役迁入本口,
        # 与 owned 确认族同一推进语义单一源;shop_wave_top 实读覆盖修正)。
        _advance_gold(session, 4, produced_by=produced_by)
        _eff('gold', '+4(现金为王弃卡回金)', 'gold')
    elif op == 'CwActionBuyCardParam':
        # dict 形 CwActionBuyCardParam(模拟/离线入口):合成引擎算购买数,金账
        # 逻辑推进;tracked 本体推进 = 执行器/调用方辖。
        _apply_buy_card(session, payload, _eff)
    return effects


def _apply_buy_card(session, action: dict, _eff) -> None:
    """dict 形 CwActionBuyCardParam 的金账推进(merge_simulate 单一引擎算购买数)。"""
    from sr_od.application.currency_war.kernel.cw_merge_simulate import (
        merge_simulate,
    )
    name = action.get('name', '')
    star = int(action.get('star', 1) or 1)
    k = int(action.get('k', 1) or 1)
    cost = int(action.get('cost', 0) or 0)
    bench, dep = _session_tracked(session)
    res = merge_simulate(bench, dep, name, star, k=k,
                         in_shop_count=action.get('in_shop_count'))
    if cost:
        _advance_gold(session, -cost * max(1, res.buy_k or 1))
        _eff('gold', f"-{cost * max(1, res.buy_k or 1)}(买牌×{res.buy_k})",
             'gold')



# ============================================================
# 席位/槽位跟踪域 + 节点台账访问函数 + 布局转发(原 kernel/cw_state.py
# 候裁9 词汇迁入):槽位表契约与节点序列台账的值宿主 =
# GameState.tracked_books / plane_node_sequences(容器簿记,载体见
# cw_game_state.py);本模块保留领域常量/类型与三访问函数,见模块尾。
# ============================================================

BENCH_CAPACITY: int = 9  # 备战栏固定 9 槽(design doc 实测;不随等级变)
# deployed 槽位语义(ADR-0392):定长 10 槽表——下标 0-3 = 前排槽 1-4、
# 4-9 = 后排槽 1-6。后排实际格数 = 6 + (cap−level) 值域 6-9(cw_back_layout
# 三信号裁决,ADR-0385;上限 9 = 用户口述,board_structure.md)——超过 6 的
# 扩展格属画面布局域,不进本表示(表长恒 10;取舍与理由见 ADR-0392
# 「后排布局档取舍」节,扩展格 7-9 的跟踪缺口在 9 档可达后常规化,扩板另案)。
DEPLOYED_FRONT_CAPACITY: int = 4
DEPLOYED_BACK_CAPACITY: int = 6
DEPLOYED_CAPACITY: int = DEPLOYED_FRONT_CAPACITY + DEPLOYED_BACK_CAPACITY


# ===== bench 槽位语义 helpers(ADR-0316;消费端唯一合法入口)=====


def bench_slot_unit(slot: BenchSlot | None) -> Unit | None:
    """BenchSlot → 内嵌 Unit 的解包读口(§2.4 字段映射约定的读法单一源):
    ``kind='unit'`` 且内嵌非空 → 该 Unit;占位件(kind ∈ tome/bookcard/
    supply_box)/空槽/None 洞 → None。身份(char_id)/星级/装备/槽号
    信息位的消费面统一经本口解包,禁消费点各自内联 kind 判断。"""
    if slot is None or slot.kind != 'unit':
        return None
    return slot.unit


def bench_place(bench: list[BenchSlot | None], slot: BenchSlot) -> int | None:
    """放入首个空槽(买入落位语义);无空槽返回 None(=bench_full 拒)。

    容器原生形状(§2.1):元素 = ``BenchSlot | None``——None 洞(卖出/上阵
    置 None 不移位,ADR-0316)与 ``kind='empty'`` 同为空槽。放置时归一
    单位槽号信息位 ``slot.unit.slot = 下标+1``(物理槽位 1-9,frozen
    replace 新构造;非 unit kind 原样落槽)。
    """
    for i, b in enumerate(bench):
        if b is None or b.kind == 'empty':
            bench[i] = _slot_normalized_at(slot, i)
            return i
    return None


def _slot_normalized_at(slot: BenchSlot, idx: int) -> BenchSlot:
    """BenchSlot 落位到下标 idx 的归一构造(unit 槽号信息位 = idx+1)。"""
    if slot.kind == 'unit' and slot.unit is not None:
        from dataclasses import replace
        return replace(slot, unit=replace(slot.unit, slot=idx + 1))
    return slot


def bench_occupied_slot_nos(bench: list[BenchSlot | None]) -> list[int]:
    """占用槽号信息位集(槽号健康门输入;None 槽跳过)。

    [索引定义] 值 = Unit.slot 信息位(1 基物理槽号,ADR-0316);
    信息位恒为派生位,权威槽位 = 表下标(ADR-0605 §5.2)。"""
    return [slot.unit.slot for slot in (bench or [])
            if slot is not None and slot.kind == 'unit'
            and slot.unit is not None]


def bench_slots_healthy(slot_nos: list[int]) -> bool:
    """槽号健康不变量单一源:占用槽号唯一 ∧ 全在 1..BENCH_CAPACITY。

    背景:SIFT 读/对账 churn 产生的槽号属无守卫数据(ADR-0646),
    违者不得固化为槽位表。消费方 = 对账写回门(kernel/cw_reconcile)、
    tracked 写点显影(prep_actions)。"""
    return (all(isinstance(s, int) and 1 <= s <= BENCH_CAPACITY
                for s in slot_nos)
            and len(set(slot_nos)) == len(slot_nos))


# ===== deployed 槽位语义 helpers(ADR-0392;消费端唯一合法入口)=====


def deployed_slot_no(idx: int) -> int:
    """槽位下标 → 排内 1-based 槽号信息位(0-3→前排 1-4;4-9→后排 1-6)。"""
    return idx - DEPLOYED_FRONT_CAPACITY + 1 if idx >= DEPLOYED_FRONT_CAPACITY \
        else idx + 1


def deployed_row_slot(idx: int) -> tuple[str, int]:
    """deployed 槽位表下标 → (物理排, 排内槽号)(执行坐标边换算单一函数;
    unified-action-factory 批2b 换算收口:容器下标 → 画面物理槽位的换算
    全仓仅此一处,消费方 = 执行器拖点定位/判读显示)。

    [索引定义] idx = deployed 槽位表下标 0-9(ADR-0392;0-3 前/4-9 后);
    返回 slot = 排内 1 基画面槽号(前排 1-4 / 后排 1-6)。
    """
    return ('front' if idx < DEPLOYED_FRONT_CAPACITY else 'back',
            deployed_slot_no(idx))


def deployed_idx_of(row: str, slot_no: int) -> int:
    """物理 (排, 排内槽号) → deployed 槽位表下标(执行坐标边换算单一函数;
    与 :func:`deployed_row_slot` 互逆,tracked 同步物理↔下标换算收拢点)。

    [索引定义] row ∈ 'front'|'back';slot_no = 排内 1 基画面槽号;返回
    槽位表下标(front: slot−1 / back: 4+slot−1,ADR-0392)。
    """
    return (slot_no - 1 if row == 'front'
            else DEPLOYED_FRONT_CAPACITY + slot_no - 1)


def deployed_rows_to_indexed(front_row: list[Unit] | None,
                             back_row: list[Unit] | None,
                             ) -> list[Unit | None]:
    """容器行域(front_row/back_row)→ deployed 下标工作表(§2.1「10 槽表
    语义保留在需要处按行下标派生」的容器原生派生单一源;P1 消费面 =
    上报函数族/sim 的工作副本构造,元素即行内 Unit 对象,零中间形)。
    Unit.slot = 行内 1 基画面槽号(信息位)定位,缺席(0)按占用
    序顺延兜底(与旧紧缩构造兼容)。两行全未观察(None)→ [None]×10。"""
    out: list[Unit | None] = [None] * DEPLOYED_CAPACITY

    def _place(units: list[Unit], base: int, span: int) -> None:
        cursor = base
        for u in (units or []):
            s = int(getattr(u, 'slot', 0) or 0)
            idx = (s - 1 + base) if s >= 1 else -1
            if not (base <= idx < base + span) or out[idx] is not None:
                while cursor < base + span and out[cursor] is not None:
                    cursor += 1
                idx = cursor if cursor < base + span else -1
                cursor += 1
            if idx >= 0:
                out[idx] = u

    _place(list(front_row or []), 0, DEPLOYED_FRONT_CAPACITY)
    _place(list(back_row or []),
           DEPLOYED_FRONT_CAPACITY, DEPLOYED_BACK_CAPACITY)
    return out


def deployed_indexed_to_rows(dep: list[Unit | None] | None,
                             ) -> tuple[list[Unit], list[Unit]]:
    """:func:`deployed_rows_to_indexed` 的逆派生:下标工作表 → 容器行域
    (紧缩列表;Unit.slot 信息位归一 = 落位排内槽号)。行成员与槽号由
    下标派生(§2.1 排归属由下标派生口径)。"""
    front: list[Unit] = []
    back: list[Unit] = []
    from dataclasses import replace
    for i, u in enumerate(dep or []):
        if u is None:
            continue
        _no = deployed_slot_no(i)
        placed = replace(u, slot=_no) if u.slot != _no else u
        (front if i < DEPLOYED_FRONT_CAPACITY else back).append(placed)
    return front, back


def trailblazer_row_identity(char_id: str, to_row: str,
                             ) -> tuple[str, str | None] | None:
    """开拓者按排形态归一的身份核(单一源):换排 = 命途切换(char_id
    切目标排形态,faction 跟随首阵营)。返回 ``(新 char_id, 首阵营或
    None)``;非开拓者/空名 → None(调用方保持原身份)。

    消费面 = :func:`trailblazer_row_unit`(Unit 容器原生唯一载体),
    归一口唯一(design §3 不变量 5;swap 与 deploy_move 两上报均经
    :func:`trailblazer_row_unit` 同源,哨兵 =
    test_cw_trailblazer_stance_normalization)。"""
    from sr_od.application.currency_war.data.cw_chars import (
        get_char,
        is_trailblazer,
        trailblazer_form,
    )
    if char_id and is_trailblazer(char_id):
        cid = trailblazer_form(char_id, to_row)
        _tc = get_char(cid)
        fac = (_tc.factions[0]
               if (_tc is not None and _tc.factions) else None)
        return cid, fac
    return None


def trailblazer_row_unit(unit: Unit, to_row: str) -> Unit:
    """开拓者换排形态归一(Unit 容器原生版):char_id 切目标排形态;
    非开拓者原样返回(frozen replace 新构造)。"""
    from dataclasses import replace
    ident = trailblazer_row_identity(str(unit.char_id or ''), to_row)
    return replace(unit, char_id=ident[0]) if ident is not None else unit

# ===== 位面节点序列台账(session 级权威表) ================================
# 权威依据(用户口述,最高权威):位面内节点类型与数量**只有投资环境选择能改变**
# (变异位唯一)→ 同一位面内节点序列是常量,可以「进位面时读一次建档 + 投资环境
# 选完后重读刷新」,此后每帧备战画面**查表**得当前节点类型,逐帧识别降级为校验。
# 旧逐帧识别的三类噪声(标签出现在即将到来节点下方 / 高亮态 Hu 不匹配 / 商店
# 遮挡坏帧)因此只影响校验票,不再直接污染决策输入。
#
# 台账值载体 :class:`PlaneNodeLedger` 住 kernel/cw_game_state.py(宿主 =
# 容器非 Field 簿记 ``GameState.plane_node_sequences``,载体解散迭代迁入);
# 本模块保留三访问函数(get_node_ledger / ledger_node_type /
# ledger_update_plane)与 fill_boss_by_position——签名不变,消费面
# (cw_vocab 转出口 / cw_equip_wear_plan 直 import / obs 与各画面 op)
# 零改动。


def get_node_ledger(session: object) -> PlaneNodeLedger | None:
    """取容器节点台账(session None → None,调用方跳过)。

    宿主 = ``GameState.plane_node_sequences``(kernel/cw_game_state.py;
    非 Field 簿记,产生者 = 画面 op 采集/重读写入端)。容器每局新建 =
    台账天然清零,无惰性建面(缺省即空账)。读写全经本函数与
    :func:`ledger_node_type`,消费点禁直摸载体字段。
    """
    if session is None:
        return None
    from sr_od.application.currency_war.kernel.cw_game_state import (
        game_state_of,
    )
    return game_state_of(session).plane_node_sequences


def ledger_node_type(session: object, plane: int | None,
                     round_num: int | None) -> str | None:
    """查表:当前位面第 ``round_num`` 轮的节点类型(1-based round → 0-based 下标)。

    表缺 / 位面轮越界 / 该位次未识别(None)→ None(调用方退逐帧识别链,
    **不猜**)。boss 位在序列里存 'boss' token(写入端按「首领=位面最后节点」
    位置先验回填,与既有 boss 语义门同源)。
    """
    ledger = get_node_ledger(session)
    if ledger is None or not plane or not round_num:
        return None
    seq = ledger.seq_by_plane.get(int(plane))
    if not seq:
        return None
    idx = int(round_num) - 1
    if not 0 <= idx < len(seq):
        return None
    return seq[idx]


def ledger_update_plane(session: object, plane: int, seq: list[str | None],
                        source: str) -> bool:
    """按位合并写入一位面的序列(**同位次新非 None 覆盖,None 保旧**)。

    合并而非覆盖的原因:备战行/详情条的 past 与 boss 位识别恒 None(Hu 不对
    当前/过去/头像生效)→ 整表覆盖会把已识别位洗成 None;逐位合并让多位面
    多时点的读数渐进拼出全序列(投资环境变异位由最新的非 None 读数天然覆盖)。
    序列变长(如环境加节点)时右侧扩展。返回是否有实际变化(判读用)。
    """
    ledger = get_node_ledger(session)
    if ledger is None or not plane or not seq:
        return False
    old = ledger.seq_by_plane.get(int(plane)) or []
    n = max(len(old), len(seq))
    merged: list[str | None] = []
    changed = False
    for i in range(n):
        new_v = seq[i] if i < len(seq) else None
        old_v = old[i] if i < len(old) else None
        v = new_v if new_v is not None else old_v
        merged.append(v)
        if v != old_v:
            changed = True
    ledger.seq_by_plane[int(plane)] = merged
    if changed or ledger.seq_source.get(int(plane)) != source:
        ledger.seq_source[int(plane)] = source
    return changed


def fill_boss_by_position(seq: list[str | None]) -> list[str | None]:
    """序列副本的最右 None 位回填 'boss'(位置先验:首领 = 位面最后节点)。

    只在 boss 位经详情条「首领节点」标签验证过的写入端调用(CwScreenPlaneIntel);
    备战行重读等未经标签验证的写入端不回填(boss 位在备战行为 past 态,
    回填无依据)。原序列不动,返回副本。
    """
    out = list(seq)
    if out and out[-1] is None:
        out[-1] = 'boss'
    return out
