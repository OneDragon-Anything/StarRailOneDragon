"""货币战争 执行域领域模型与纯函数宿主(cw_exec_state;无状态面)。

本模块不承载跨调用状态——原执行层状态载体已整体停用,局内事实宿主 =
GameState(kernel/cw_game_state.py)。现覆盖三类领域函数:

- 确认族到账推进:``apply_confirm_effect``(两态制标准语义;
  原 apply_op_effect 动作类分支已并入各 op 自上报后瘦身);
- 槽位表领域模型:bench/deployed 槽位语义 helpers(benchchar-retirement
  P1 起状态容器原生:bench = ``BenchSlot | None`` 槽表;
  deployed 主域 = DeployedView 完整槽位表,3.2 随 tracked 第二账停用删除
  换算五函数——残余的下标→(排,排内槽号)固定双射由消费点内联算术承载,
  工作表桥 = cw_game_state.deployed_indexed_of_view/deployed_view_of_indexed);
  观察读链直产状态容器形状(obs/cw_identity_obs),本模块无换形适配层;
- 位面节点序列台账访问:get_node_ledger / ledger_node_type /
  ledger_update_plane 与 fill_boss_by_position(台账值载体
  ``PlaneNodeLedger`` 住 kernel/cw_game_state.py,本模块运行时转发,
  保持既有 import 路径不断链)。
"""
from __future__ import annotations

# 台账值载体(运行时转发,非仅注解):类本体住 kernel/cw_game_state.py
# (宿主 = 状态容器非 Field 簿记 GameState.plane_node_sequences 所在模块),本模块
# 转发保持 cw_vocab 转出口与既有 import 路径不断链(消费面零改动的成立前提)。
# cw_game_state 模块级依赖不反向触达本模块
# (惰性 import 面),此模块级引入不成环。
from sr_od.application.currency_war.kernel.cw_game_state import (
    BenchSlot,
    PlaneNodeLedger,
    Unit,
)

# ============================================================ 确认族到账推进
# (自 kernel/cw_expected_state 收拢;动作词表类分支已并入 op 自上报
# (kernel/cw_action_report),本口只剩 dict
# 确认族,消费点 = _overlay_confirm.register_confirm_arrival。
# ⚠️ 动作词表/合成引擎(cw_vocab/cw_merge_simulate)模块级 import 本模块
# (转出口),本模块对其依赖一律函数内惰性 import,模块级引入会成环——
# 沿用本仓懒加载惯例。)

def _session_seats(session) -> tuple[list, list]:
    # 席位主域读口(宿主 = GameState.bench/deployed 席位视图,kernel/
    # cw_game_state.py;lazy import 防模块环,同 _advance_gold 惯例)。
    # bench = list[BenchSlot | None] / deployed = 视图派生定长 10 工作表
    # (tracked 第二账停用,合成仿真自主域派生)。
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_view_slots_of,
        deployed_indexed_of_view,
        game_state_of,
    )
    _gs = game_state_of(session)
    return (list(bench_view_slots_of(_gs)),
            deployed_indexed_of_view(_gs.deployed.value))


def _advance_gold(session, delta: int, *,
                  produced_by: str = 'PrepActionExecutor') -> None:
    """op 逻辑效果的金账直推(last_state 链停用后宿主 = 状态容器单例):
    ``game_state_of(session).gold`` 经 logic_action 通道 write_logic
    (可为负;现值 None 视 0 基线——金账由商店波顶/结算屏可信读覆盖
    修正,以实际观察为准)。渠道面 = family='logic_action' + actor
    'PrepActionExecutor'(已登记;登记类属 = 动作 op 逻辑效果推进宿主,
    produced_by 携调用面标识留存证据)。
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
    """确认类到账 dict 的逻辑效果推进(原 ``apply_op_effect`` 瘦身改名;
    动作词表类分支已全量并入各 op 自上报
    (kernel/cw_action_report 函数族),本口只剩 dict 确认族;消费方 =
    ``_overlay_confirm.register_confirm_arrival``)。

    语义(逐行自原 dict 分支平移,零行为):
    - ``ConfirmBox``/``ConfirmTome`` 且 item 在场:
      owned +1(终态契约 §B:单一源 = gs.equips,现读-改写-回写;补给
      入栏/后果分支不读本口——写语义单点 =
      ``cw_action_report.pick_supply.report_action_pick_supply_param``);
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
    if op in ('ConfirmBox', 'ConfirmTome') and item:
        _owned_add(session, item)
        _eff(f'owned[{item}]', f'+1({op})', 'owned')
    elif op == 'ConfirmExpertCash':
        # 专家邀请函「现金为王」:弃卡取现金固定回金 +4 金账直推
        # (原 _overlay_confirm 内联 last_state 直推,现宿主 = 本口,
        # 与 owned 确认族同一推进语义单一源;shop_wave_top 实读覆盖修正)。
        _advance_gold(session, 4, produced_by=produced_by)
        _eff('gold', '+4(现金为王弃卡回金)', 'gold')
    elif op == 'CwActionBuyCardParam':
        # dict 形 CwActionBuyCardParam(模拟/离线入口):合成引擎算购买数,金账
        # 逻辑推进;tracked 本体推进 = 执行器/调用方覆盖。
        _apply_buy_card(session, payload, _eff)
    return effects


def _apply_buy_card(session, action: dict, _eff) -> None:
    """dict 形 CwActionBuyCardParam 的金账推进(merge_simulate 单一引擎算购买数;
    免费购买闸与买牌上报单点同构:免张数源 = 实扣张数,免费帧零金写零置位)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        ChannelSig,
        game_state_of,
        mark_gold_spent,
    )
    from sr_od.application.currency_war.kernel.cw_investments import (
        STRATEGY_EFFECTS,
    )
    from sr_od.application.currency_war.kernel.cw_merge_simulate import (
        merge_simulate,
    )
    name = action.get('name', '')
    star = int(action.get('star', 1) or 1)
    k = int(action.get('k', 1) or 1)
    cost = int(action.get('cost', 0) or 0)
    bench, dep = _session_seats(session)
    res = merge_simulate(bench, dep, name, star, k=k,
                         in_shop_count=action.get('in_shop_count'))
    bought = max(1, res.buy_k or 1)
    # 免费购买闸(降本增效,与买牌上报单点同闸同豁免):免张数源 =
    # 实扣张数(与扣金张数同一来源,超额部分由 helper 钳制;两入口零
    # 语义分叉的对齐口径)。递减 = 游戏侧事实,与金账观察无关,先于
    # 金写判定;全免帧零金写零置位。
    _free = 0
    _spec = STRATEGY_EFFECTS.get('降本增效')
    if _spec is not None:
        _free = game_state_of(session).effects.consume_uses_up_to(
            _spec.id, bought)
    _paid = bought - _free
    if cost and _paid > 0:
        _advance_gold(session, -cost * _paid)
        _free_tag = f',免费{_free}' if _free else ''
        _eff('gold', f"-{cost * _paid}(买牌×{res.buy_k}{_free_tag})",
             'gold')
        # 金币花费事件置位(存款回报条件输入,fields.md §3.3.9):付费帧
        # 才置位(免费帧零金变动不属花费事件,与买牌上报单点同豁免)。
        # dict 形买牌同属花费事件(回放/离线状态副本真值一致性;现役生产零
        # 调用)。sig 自构(actor='PrepActionExecutor' + mode='compute',
        # 对齐 _advance_gold 既有构形——本作用域无动作窗 _grp_sig)。
        mark_gold_spent(game_state_of(session),
                        produced_by='PrepActionExecutor',
                        sig=ChannelSig(family='logic_action',
                                       actor='PrepActionExecutor',
                                       mode='compute'))



# ============================================================
# 席位/槽位域 + 节点台账访问函数 + 布局转发:槽位表契约与节点序列台账的值宿主 =
# GameState.bench/deployed 席位视图 / plane_node_sequences(载体见
# cw_game_state.py);本模块保留领域常量/类型与三访问函数,见模块尾。
# ============================================================

BENCH_CAPACITY: int = 9  # 备战栏固定 9 槽(design doc 实测;不随等级变;激活期随容量
# 时限效果——节省工位窗内 kernel 容量域照 3(fields.md §3.2.5),本常量 = 策略侧
# 定长 9 基线消费面口径,分叉面 = 既有缺口不入容量建模批改动面)
# deployed 动作坐标系:定长 10 槽表——下标 0-3 = 前排槽 1-4、
# 4-9 = 后排槽 1-6。后排实际格数 = 6 + (cap−level) 值域 6-9(cw_back_layout
# 三信号裁决;上限 9 = 用户口述,board_structure.md)——超过 6 的
# 扩展格属画面布局域,超出动作坐标系不可寻址(主域视图可存 7-9 扩展
# 格,工作表桥按 6 截断在案)。
DEPLOYED_FRONT_CAPACITY: int = 4
DEPLOYED_BACK_CAPACITY: int = 6
DEPLOYED_CAPACITY: int = DEPLOYED_FRONT_CAPACITY + DEPLOYED_BACK_CAPACITY


# ===== bench 槽位语义 helpers(消费端唯一合法入口)=====


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

    状态容器原生形状(§2.1):元素 = ``BenchSlot | None``——None 洞(卖出/上阵
    置 None 不移位)与 ``kind='empty'`` 同为空槽。槽位信息位已停用(Unit.slot
    不再承载):权威槽位 = 表下标,落位归一分支为恒等
    (保留函数形状供调用方零改动;非 unit kind 原样落槽)。
    """
    for i, b in enumerate(bench):
        if b is None or b.kind == 'empty':
            bench[i] = slot
            return i
    return None


# (换算五函数 deployed_slot_no/deployed_row_slot/deployed_idx_of/
#  deployed_rows_to_indexed/deployed_indexed_to_rows 已停用:主域 = DeployedView 完整槽位表(下标直址),
#  工作表桥 = cw_game_state.deployed_indexed_of_view/deployed_view_of_
#  indexed;残余的下标→(排,排内槽号)固定双射(0-3=前排 1-4 /
#  4-9=后排 1-6)由消费点内联算术承载,消费面 = 卖场上阵 op 与遥测归档。)


def trailblazer_row_identity(char_id: str, to_row: str,
                             ) -> tuple[str, str | None] | None:
    """开拓者按排形态归一的身份核(单一源):换排 = 命途切换(char_id
    切目标排形态,faction 跟随首阵营)。返回 ``(新 char_id,首阵营或
    None)``;非开拓者/空名 → None(调用方保持原身份)。

    消费面 = :func:`trailblazer_row_unit`(Unit 状态容器原生唯一载体),
    归一口唯一(design §3 不变量 5;swap 与 deploy_move 两上报均经
    :func:`trailblazer_row_unit` 同源,哨兵 =
    test_faction_derivation_locks 开拓者形态归一节)。"""
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
    """开拓者换排形态归一(Unit 状态容器原生版):char_id 切目标排形态;
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
# 状态容器非 Field 簿记 ``GameState.plane_node_sequences``);
# 本模块保留三访问函数(get_node_ledger / ledger_node_type /
# ledger_update_plane)与 fill_boss_by_position——签名不变,消费面
# (cw_vocab 转出口 / cw_equip_wear_plan 直 import / obs 与各画面 op)
# 零改动。


def get_node_ledger(session: object) -> PlaneNodeLedger | None:
    """取状态容器节点台账(session None → None,调用方跳过)。

    宿主 = ``GameState.plane_node_sequences``(kernel/cw_game_state.py;
    非 Field 簿记,产生者 = 画面 op 采集/重读写入端)。状态容器每局新建 =
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
