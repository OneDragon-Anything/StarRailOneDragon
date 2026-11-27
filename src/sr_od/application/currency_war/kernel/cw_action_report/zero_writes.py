"""零写动作族上报集中件(状态容器零写,等观察覆盖)。

族策略:视觉域/转场/选择类动作的字段写语义 = 零(逐类函数体 =
三行委托 :func:`_report_zero_write`),集中一文件不逐类开文件
(无逐类专覆盖内容);包级 ``__getattr__`` 未命中落本模块(命名规约无
专项完备测试,现役锁 = 动作 op 注册表测试)。语义权威版本 = 各函数
docstring(自 cw_game_state 逐字迁移)。

**唯一非零写例外 = 占席件选卡上报的前置清槽步**(:func:`_clear_opened_slot`,
星徽秘典/武装箱选卡两件共用):占席件离席建模为「开件零写 + 选卡清槽」
两拍契约——开件上报(开典籍/开箱)零状态容器写、登记携被点开槽;选卡上报
消费登记取槽 logic 清该槽 = 离席单一写端。清槽四个出口(登记缺位 /
bench 未观察 / 槽不符 / 溢出告警在场实机口径)均零写仅披露。

工具原子七类(冶金炉/特权赋予卡/拆装扳手/精密拆装扳手/员工投影仪/
完美投影仪/好运令牌)不在零写族:上报升格为字段写(机械执行直接
上报写状态容器),分步实现权威版本 = 同包 ``tool_use``;包级 ``__getattr__``
命名规约解析具名模块先于本模块。
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace
from typing import TYPE_CHECKING, Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    BenchSlot,
    BenchView,
    ChannelSig,
    GameState,
    LogicOutcome,
    _emit_defect,
    _validate_sig,
    node_screen_now,
)
from sr_od.application.currency_war.kernel.cw_overlay_register import (
    KIND_SCREEN_NAMES,
    consume_screen_change,
    register_screen_change,
)
from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_overlay_register import (
        PendingScreen,
    )

#: 专家邀请函选卡·解锁名不可观察申报 kind(语义申报非缺陷;沿
#: cw_gain_chain.ENV_REROLL_DECL 先例不入 DEFECT_ 词表——解锁状态缺登记
#: 是观察数据缺口非运行缺陷,真值归观察覆盖,候选名观察建档批接入调用后
#: 本 kind 退役)。
EXPERT_UNLOCK_NAME_UNOBSERVED: str = 'pick_expert_name_unobserved'

#: 占席件选卡上报「被点开槽未清」语义申报 kind(非缺陷;沿
#: :data:`EXPERT_UNLOCK_NAME_UNOBSERVED` 先例不入 DEFECT_ 词表——真值归
#: 下一 heavy 实读覆盖,evidence 后缀区分出口,见
#: :func:`_clear_opened_slot`)。
PICK_OPEN_SLOT_UNCLEARED: str = 'pick_open_slot_uncleared'

# —— 转移动作声明构造(动作后果声明化详设 world-decl.md §2 表 #5/#9/
#    #10/#13-#17;画面档名字面值权威 = assets/game_data/screen_info 档名;
#    trigger 封闭集单一源 = sim 后端 advance 分派表键集,值零新词沿用
#    现役动作名)——
# 「返回节点屏」声明族按当前生效节点推导(单一源 = node_screen_now):
# 节点窗压住的底层屏随节点 kind 分档(遭遇/补给/boss 各归其档),硬编码
# 备战仅对 battle/reward 槽成立(改节点序列环境使 offer/overlay 落到
# 非备战槽,历史常量声明即漂移)。降级形态(生效序位缺位)回退备战档。

#(声明改底层屏):open_box 声明 next_screen 回归
# 底层屏——武装箱选择画面的出现事实改由登记(kind = box_card,上报内
# register)承载;trigger='open_box' 保留(backend 开箱采样过程仍挂触发分派)。


def _decl_bottom(gs: GameState, trigger: str,
                 slots: tuple[int, ...] = ()) -> WorldDecl:
    """底层屏声明构造(trigger 沿用动作名;next_screen = 当前节点屏,
    推导单一源 = ``node_screen_now``)。``slots`` = 占席件开件上报透传的
    被点开槽(备战栏物理槽 1 基单元素,``WorldDecl.slots`` 索引定义),
    其余动作缺省空元组(现调用零变)。"""
    return WorldDecl(next_screen=node_screen_now(gs), trigger=trigger,
                     slots=slots)

# —— 零写动作族(视觉域/转场/选择族:状态容器零写,消费真值归观察;
#    函数在场 = 包级命名规约 lazy 解析落点,
#    调用方统一入口不必分型)——


def _clear_opened_slot(gs: GameState, entry: PendingScreen | None,
                       kind: str, sig: ChannelSig,
                       produced_by: str) -> None:
    """占席件「选卡即离席」清槽(星徽秘典/武装箱选卡上报共用的唯一实现)。

    被点开槽 = 开件拍登记携带的 ``entry.slot``(备战栏物理槽 1 基快照,
    ``PendingScreen.slot`` 索引定义)→ 整表 logic 写、他槽原样保留
    (evidence ``pick_open_slot_clear``,写形同 kernel 上报 = 推算 →
    ``write_logic``)。槽件两态:无溢出告警 = ``BenchSlot(kind='empty')``;
    溢出告警在场 = 经包级注入槽 ``overflow_pick_resolver(gs)`` 取被腾槽
    终态——返回 None(实机缺省)**不写** bench 与 overflow 两字段、仅披露
    ``overflow_in_play``,bench 留原源由下一 heavy 实读承接真实终态
    (「点开消耗品 → 溢出件归位」仓内未实证——机制实证仅覆盖卖出路径,
    不写未证机制;归位/不归位两形态均 obs 覆盖 obs 静默)/ 返回槽件
    (sim 装配方注入 = empty 槽件;sim 无 bench 观察通道,不写即占席件
    永不离席 → 重发活锁)。

    四个不清槽出口均**零写仅披露**(kind = :data:`PICK_OPEN_SLOT_UNCLEARED`,
    evidence 后缀区分):登记缺位(``entry`` None 或 ``slot`` None——识别
    miss 窗内被外循环兜底清收走)/ bench 未观察 / 槽越界·该槽 None·
    kind ≠ 登记件 kind(决策陈旧/错槽帧/已被他路清;禁全 kind 清——
    「终身学习」跨位面累积多件同席合法,只清被点开的一枚)/ 溢出在场
    实机口径。

    签名校验前置:``write_logic`` 接受 logic_action/logic_hook 两族而
    ``_report_zero_write`` 只接受 logic_action,校验若后置则 logic_hook
    族 sig 下 bench 已写后才抛;生产 op 恒传 logic_action,一行前置消解。
    """
    _validate_sig(sig, ('logic_action',))

    def _disclose(suffix: str, actual: Any) -> None:
        _emit_defect(field_name='bench', expected=kind, actual=actual,
                     evidence=f'{PICK_OPEN_SLOT_UNCLEARED}:{suffix}',
                     sig=sig, kind=PICK_OPEN_SLOT_UNCLEARED)

    if entry is None or entry.slot is None:
        _disclose('no_entry', None)
        return
    idx = int(entry.slot) - 1
    view = gs.bench.value
    if view is None:
        _disclose('bench_unobserved', None)
        return
    cur = view.slots[idx] if 0 <= idx < len(view.slots) else None
    if cur is None or cur.kind != kind:
        _disclose('slot_kind_mismatch', None if cur is None else cur.kind)
        return
    if gs.overflow_warning.value:
        from sr_od.application.currency_war.kernel.cw_action_report import (
            overflow_pick_resolver,
        )
        new_slot = overflow_pick_resolver(gs)
        if new_slot is None:
            _disclose('overflow_in_play', kind)
            return
    else:
        new_slot = BenchSlot(kind='empty')
    slots = list(view.slots)
    slots[idx] = new_slot
    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))
    gs.write_logic(gs.bench, BenchView(slots=slots, capacity=view.capacity),
                   produced_by=produced_by, evidence='pick_open_slot_clear',
                   sig=_grp_sig)


def _report_zero_write(gs: GameState, param: Any, sig: ChannelSig,
                        note: str,
                        decl: WorldDecl | None = None) -> LogicOutcome:
    """零写动作统一实现(状态容器零写,等观察覆盖;applied=True = 动作受理,
    非拒绝)。转移类动作随附后果声明(构造义务 = 动作后果声明化迭代
    总纲 design.md §2.2 契约 2;非转移类 decl 缺省 None = 无声明可喂)。"""
    _validate_sig(sig, ('logic_action',))
    return LogicOutcome(applied=True, reason=note or 'zero_write',
                        world_decl=decl)



def report_action_open_tome_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """开秘密典籍上报:零写占位形态——状态容器零写,占席件仍占席(弹窗期
    典籍在席,选卡后才离席;离席归 ``report_action_pick_star_tome_param``
    选卡上报清槽);star_tome 登记携被点开槽 + applied 出口构造后果声明
    (trigger='open_tome',slots=(被点开槽,)——sim 无星徽弹窗呈现面、选卡拍
    不存在,sim 后端据此在开件拍代清席)。

    两拍契约(占席件开件-选卡):开件拍零写使弹窗瞬态窗逻辑态与游戏
    事实一致——弹窗识别 miss 使备战环重观察踩中弹窗期时,实读 tome 对
    logic tome 零失配;离席 durable 性由选卡拍 logic 清槽保证(全空备战栏
    形态不滞留——观察写端全空读 = 失读保旧)。可复核指针 =
    ``sr-od-test/test/sr_od/application/currency_war/kernel/cw_action_report/test_zero_writes.py``
    瞬态窗主剧本即复现锁。

    param 消费口径:本函数唯一 param 读 = ``param.slot`` 进登记载体与
    声明载体(非键域反查),零状态容器写语义不变(与零写族「函数体零读」
    口径的偏离显式申报;OpenBox 同形)。晶矿谓词保守偏置:弹窗期 bench
    席空数少计一席(少买不误买,方向保守),选卡清槽后即时修正;偏置窗
    ≈ 弹窗期(弹窗识别在场时备战环 bail 交外环,决策不插跑)。

    零拒单出口(零写族恒 applied=True,无 slot/kind 校验——错槽真值归
    heavy 实读对账)。slot 必填口径单一源 = 词表 ``CwActionOpenTomeParam``
    类 docstring。"""
    slot = int(param.slot)
    register_screen_change(
        gs, 'star_tome', KIND_SCREEN_NAMES['star_tome'],
        source='s6_click@open_tome', slot=slot)
    return _report_zero_write(gs, param, sig, 'zero_write(open_tome)',
                              decl=_decl_bottom(gs, 'open_tome',
                                                slots=(slot,)))



def report_action_open_box_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """开补给箱上报:零写占位形态——状态容器零写,占席件仍占席(弹窗期
    箱在席,选完才离席;离席归 ``report_action_pick_box_card_param`` 选卡
    上报清槽);box_card 登记携被点开槽 + applied 出口构造后果声明
    (open_box;武装箱选择画面出现;喂入与消费面 = ``cw_sim_ports.declare_world``
    / sim 后端 advance,声明 next_screen 语义 = 底层屏)。

    [记账路径总契约第八适用者](契约正文 = flow/action-op.md L32):
    零写占位形态——``param.slot`` 读入登记载体与声明载体(非键域反查),
    零状态容器写端 + box_card 登记 + 底层屏声明;与 OpenTome 同构(零键域
    零反查,总契约三条整族退化),零拒单出口(零写族恒 applied=True,无
    slot 校验——错槽真值归 heavy 实读对账)。slot 必填口径单一源 = 词表
    ``CwActionOpenBoxParam`` 类 docstring(None 语义已随参数面迁移批废除,
    现算归发出点 entry._consumable_open_action)。"""
    slot = int(param.slot)
    register_screen_change(
        gs, 'box_card', KIND_SCREEN_NAMES['box_card'],
        source='s6_click@open_box', slot=slot)
    return _report_zero_write(gs, param, sig, 'zero_write(open_box)',
                              decl=_decl_bottom(gs, 'open_box',
                                                slots=(slot,)))


# 工具族七上报(report_action_furnace_use_param / report_action_privilege_card_
# use_param / report_action_wrench_use_param / report_action_precision_wrench_
# use_param / report_action_staff_projector_use_param / report_action_perfect_
# projector_use_param / report_action_lucky_token_use_param)= 字段写形态,
# 单一源 = 同包 tool_use(冶金炉采样池 sim 同源 + 投影仪走获得链);包级
# ``__getattr__`` 命名规约解析具名模块先于本模块,直接 import 零写委托
# 的旧消费面已改直取具名模块。



def report_action_open_shop_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """开商店上报:画面态周转(开店事实由 shop payload 观察
    写入),状态容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(open_shop)')



def report_action_pick_event_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """选事件选项上报(CwActionPickEventParam 参数载体 + sim 脚本动作;
    策略器不发出),状态容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(pick_event)')

# report_action_pick_invest_param / report_action_pick_equip_param /
# report_action_pick_supply_param / report_action_pick_encounter_param
# 不在零写族(移具名模块):pick_equip / pick_supply = 分步→即时实现
# (同包具名模块);pick_invest 拆为
# pick_invest_strategy / pick_invest_env(即时上报形态:机械链发出即按
# 成功写完整结果,skills/sr-od-dev-currency-war/references/flow/action-op.md §1 增补 2;策略支整支走获得链
# gain_invest_strategy,环境支走 gain_invest_env);pick_encounter 在同包
# pick_encounter.py(发出即写 chosen_encounter,选择事实 =
# 动作执行时产生,用户裁定 2026-09-21)。包级 ``__getattr__`` 命名规约
# 解析具名模块先于本模块,直接 import 零写委托的旧消费面已改直取
# 具名模块。



def report_action_pick_megastar_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """盛会之星选择上报:状态容器零写。applied 出口构造后果声明(pick_megastar;
    返回当前节点屏,详设 world-decl.md §2 表 #10)。"""
    #(精确消费):选卡动作消费同 kind 登记
    # (实机和模拟器两边同一行代码;overlay 生命周期契约「实机消费·生命周期」)。
    consume_screen_change(gs, 'megastar')
    return _report_zero_write(gs, param, sig, 'zero_write(pick_megastar)',
                              decl=_decl_bottom(gs, 'pick_megastar'))



def report_action_pick_partner_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """列车同行伙伴选择上报:状态容器零写。applied 出口构造后果声明
    (纯转移返回当前节点屏,详设 world-decl.md §2 表 #13)。"""
    #(精确消费):选卡动作消费同 kind 登记
    # (实机和模拟器两边同一行代码;overlay 生命周期契约「实机消费·生命周期」)。
    consume_screen_change(gs, 'partner')
    return _report_zero_write(gs, param, sig, 'zero_write(pick_partner)',
                              decl=_decl_bottom(gs, ''))



def report_action_pick_star_tome_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """星徽秘典选择上报:选卡即离席——消费 star_tome 登记取被点开槽 logic
    清该槽(整表写、他槽不动;溢出告警在场实机口径不写让实读承接,
    :func:`_clear_opened_slot`)+ 零写委托。applied 出口构造后果声明(纯转移
    返回当前节点屏,详设 world-decl.md §2 表 #16)。"""
    #(精确消费):选卡动作消费同 kind 登记,回传条目携被点开槽
    # (实机和模拟器两边同一行代码;overlay 生命周期契约「实机消费·生命周期」)。
    entry = consume_screen_change(gs, 'star_tome')
    _clear_opened_slot(gs, entry, 'tome', sig,
                       produced_by='CwActionPickStarTomeParam')
    return _report_zero_write(gs, param, sig, 'zero_write(pick_star_tome)',
                              decl=_decl_bottom(gs, ''))



def report_action_pick_wish_trial_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """祈愿试炼选择上报:状态容器零写。applied 出口构造后果声明(纯转移
    返回当前节点屏,详设 world-decl.md §2 表 #15)。"""
    #(精确消费):选卡动作消费同 kind 登记
    # (实机和模拟器两边同一行代码;overlay 生命周期契约「实机消费·生命周期」)。
    consume_screen_change(gs, 'wish_trial')
    return _report_zero_write(gs, param, sig, 'zero_write(pick_wish_trial)',
                              decl=_decl_bottom(gs, ''))



def report_action_pick_box_card_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """武装箱选择上报:选卡即离席——消费 box_card 登记取被点开槽 logic
    清该槽(整表写、他槽不动;溢出告警在场实机口径不写让实读承接,
    :func:`_clear_opened_slot`)+ 零写委托。applied 出口构造后果声明
    (pick_box_card;选卡即终结返回当前节点屏,详设 world-decl.md §2 表 #9;
    装备入栏归 backend)。"""
    #(精确消费):选卡动作消费同 kind 登记,回传条目携被点开槽
    # (实机和模拟器两边同一行代码;overlay 生命周期契约「实机消费·生命周期」)。
    entry = consume_screen_change(gs, 'box_card')
    _clear_opened_slot(gs, entry, 'supply_box', sig,
                       produced_by='CwActionPickBoxCardParam')
    return _report_zero_write(gs, param, sig, 'zero_write(pick_box_card)',
                              decl=_decl_bottom(gs, 'pick_box_card'))



def report_action_pick_fortune_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """命运卜者强化三选一上报:状态容器零写。applied 出口构造后果声明
    (纯转移返回当前节点屏,详设 world-decl.md §2 表 #14)。"""
    #(精确消费):选卡动作消费同 kind 登记
    # (实机和模拟器两边同一行代码;overlay 生命周期契约「实机消费·生命周期」)。
    consume_screen_change(gs, 'fortune')
    return _report_zero_write(gs, param, sig, 'zero_write(pick_fortune)',
                              decl=_decl_bottom(gs, ''))



def report_action_pick_expert_invite_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """专家邀请函选卡上报:状态容器零写(现金为王回金 = dict 确认族通道)。
    applied 出口构造后果声明(纯转移返回当前节点屏,详设 world-decl.md
    表 #17)。

    专家解锁登记缺口申报:选中卡(idx≥0)对应的专家名不可观察
    (``expert_invite`` payload 只有羁绊解析无候选名;羁绊 → 名非唯一
    映射,如停云/青雀同仙舟)→ 只落 ``_emit_defect`` 语义申报一行
    (kind = :data:`EXPERT_UNLOCK_NAME_UNOBSERVED`,留存证据不停机),
    ``gs.unlocked_experts`` 解锁写端待候选名观察建档批接入调用;真值归观察
    覆盖(实机商店采样猜测分支在该通道解锁后仍按无专家猜,采样偏差由
    ``logic_rand_outcome`` 台账收束)。idx=-1(现金为王)= 无专家解锁,
    零申报。"""
    #(精确消费):选卡动作消费同 kind 登记
    # (实机和模拟器两边同一行代码;overlay 生命周期契约「实机消费·生命周期」)。
    consume_screen_change(gs, 'expert_invite')
    idx = getattr(param, 'idx', None)
    if isinstance(idx, int) and idx >= 0:
        _emit_defect(field_name='unlocked_experts', expected=None,
                     actual=(f'已选专家邀请函第 {idx} 卡(名字不可观察,'
                             '解锁登记待候选名观察建档)'),
                     evidence='pick_expert_invite:name_unobserved', sig=sig,
                     kind=EXPERT_UNLOCK_NAME_UNOBSERVED)
    return _report_zero_write(gs, param, sig, 'zero_write(pick_expert_invite)',
                              decl=_decl_bottom(gs, ''))



def report_action_synthesis_confirm_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """确认合成上报:状态容器零写——不写 ``synthesis_overlay``,也不写装备库存。
    「浮层已处理」由下一帧观察写成 ``'none'`` 或新的读数结构;在这里写逻辑态的话,
    点击没生效的下一帧(浮层仍在场)会落一条「修推算代码」的真失配缺陷行——点击没生效、
    再处置一次是设计明示的重试形态,不该记成 bug。合成产物需要可靠的装备名才能记账,
    框内图标识别只是参考读数,写错比不写糟;库存真值由下一帧全量观察覆盖。

    applied 出口构造后果声明:动作后仍在备战画面。``next_screen`` 直接写备战画面档名,
    不走 :func:`_decl_bottom`——那个函数按当前节点推导底层画面,点这颗按钮不改画面。"""
    return _report_zero_write(
        gs, param, sig, 'zero_write(synthesis_confirm)',
        decl=WorldDecl(next_screen='货币战争-备战', trigger=''))



def report_action_synthesis_cancel_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """取消合成上报:状态容器零写,理由与后果声明同确认合成
    (:func:`report_action_synthesis_confirm_param`)——材料不动,库存无变化。"""
    return _report_zero_write(
        gs, param, sig, 'zero_write(synthesis_cancel)',
        decl=WorldDecl(next_screen='货币战争-备战', trigger=''))



# —— 刷新建议三动作(遭遇/补给/投资):参数类已登记(CW_ACTION_TYPES)。
#    投资刷新已接入调用生产面(2026-10-19 用户裁定「sim 与实机一致提供刷新
#    次数」批):生产动作发出面 = 画面 op 刷新链自上报本函数取声明喂入
#    (``cw_sim_ports.declare_world``);遭遇/补给两函数仍零生产调用方
#    (在场 = 包级命名规约 lazy 解析落点,禁当死代码删除)。——



def report_action_refresh_node_options_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """遭遇刷新建议上报:刷新链 = 同访问重决策,状态容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(refresh_node_options)')



def report_action_refresh_supply_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """补给刷新建议上报:状态容器零写。"""
    return _report_zero_write(gs, param, sig, 'zero_write(refresh_supply)')



def report_action_refresh_invest_cards_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """投资逐卡刷新建议上报:状态容器零写(刷新真值归观察覆盖——刷后计数与
    候选由重入观察 report 落状态容器);applied 出口构造刷新状态副本声明(喂入与
    消费面 = ``cw_sim_ports.declare_world`` / sim 后端 advance 分派)。

    trigger 推导(依据 = ``gs.active_env`` ∨ ``gs.env_refresh_left`` 现值,
    三状态全 Sound——T-427 验收 F-1 修正:RunConfig.env_present 缺省
    False 是合法无环境支路配置,该局 active_env 恒空而固定日程策略 offer
    照常呈现计数,「环境选择恒先于策略 offer」的前提在该局不成立,单一
    active_env 依据会把策略刷新误派 env 分支造成静默活锁):
    - active_env 非空 = 投资策略屏 → 逐卡刷新(slots 原样透传,坐标系 =
      投资界面卡槽物理排位 0 基);
    - active_env 空 ∧ env_refresh_left 非 None = 投资环境选择屏(环境屏
      呈现写点 = 该字段唯一写端,在屏决策时点必已落值)→ 整组刷新
      (slots 哨兵,不逐槽消费);
    - active_env 空 ∧ env_refresh_left None = 无环境局策略屏 → 逐卡刷新。
    屏名内联声明:kernel→operations 反向 import 禁止,screen_info 档名
    同形内联(sim ``_SIM_KIND_TO_RING_LABEL`` 先例;权威 = screen_info 档)。"""
    if str(gs.active_env.value or '') \
            or gs.env_refresh_left.value is None:
        _trigger, _screen = 'refresh_invest_strategy', '货币战争-投资策略'
    else:
        _trigger, _screen = 'refresh_invest_env', '货币战争-投资环境'
    decl = WorldDecl(next_screen=_screen, trigger=_trigger,
                      slots=tuple(getattr(param, 'slots', ()) or ()))
    return _report_zero_write(gs, param, sig,
                              'zero_write(refresh_invest_cards)', decl=decl)



def report_action_obs_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """重观察上报(CwActionObsParam):本动作的状态容器更新通道 = 观察
    漏斗本体(宿主 heavy 观察链直写,观察边界对账),动作上报面零写;
    函数在场 = 包级命名规约 lazy 解析落点 + op 自上报回执统一形态。"""
    return _report_zero_write(gs, param, sig, 'zero_write(obs)')
