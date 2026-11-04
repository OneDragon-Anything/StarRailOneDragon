"""升级连锁值回调宿主(level 域写尾回调;C-回调同构成员,契约权威版本 =
``cw_faction_callbacks.py`` 模块头:回调挂「字段值变更」非动作,判据只看
值从什么变成什么,观察写零回调,logic/logic_rand 两逻辑通道同经,调用点
单一 = ``GameState._write_logic_frame`` 的 level 分支尾)。

为什么(单一调度):升级真跨级时跟随发生的三块连锁——①商业间谍信号 +
模拟器商店分支;②节节高升 2★ 角色发放;③升级窗口达成位记录——曾经
只挂「买经验上报」一个动作口(fields.md 节节高升条旧登记「触发面 = 升级
上报回调唯一」),任意其它经验来源(节点基础经验/窗口发放/选卡即时等)
把等级推上去时连锁不发生。收敛为「一个值回调 + 两个经验入账函数」后:
逻辑写经验(grant_xp/买经验上报)经 level 写尾自动进本调度器,观察写经验
(模拟器域)统一经 ``settle_xp_observe`` 显式调本调度器——连锁对任意经验
来源生效(设计稿:迭代 2026-09-23-invest-effects-calc T-432)。

调度器守卫(全列,任一命中即返回):old_level None(种子写/首写,镜像
``on_enemy_affixes_logic_write`` 的 old None 防误触发);new <= old(降级/
同值——观察纠偏、重放、错账全挡,只认升格跨级)。满级帽不需专门守卫:
推进算子自带帽封顶,值域上不存在越帽升格写。

内部序(单源,两个经验入账函数共享):信号置位(无条件,实机和模拟器
两边——反映真实游戏行为)→ 声明队列写入(仅模拟器装配时,live 不构造
——live 端口未装配 = no-op,杜绝 live 队列陈积被后续上报误读出的脏声明)
→ gift 分支(持有判定 + 模拟器门)→ 锚记录。异常语义:零内吞,沿调用
栈上抛——tick 语境被 ``tick_effect_boundary`` 的 try/except 吞 Exception
记 warning(既有 best-effort 语义的延伸),上报语境异常上抛(op 侧链断)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_game_state import ChannelSig
from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
    )

#: spy 世界分支声明的下一画面档(备战;与旧上报口构造值同源,零变化)。
_SPY_DECL_NEXT_SCREEN: str = '货币战争-备战'


def _levelup_gift_sig(gs: GameState) -> ChannelSig:
    """gift 发放写入的渠道③签名(构造沿 ``cw_game_state._bridge_sig`` 形;
    家族 = logic_hook,actor = 本宿主——gift 内部字段写(获得链入席/
    上阵)从买经验上报的 logic_action 族签名改挂本自有族,journal 按
    family 归类,消费面排查申报 = 测试仓 test_sim_levelup_gift 零直接
    family 断言)。"""
    return ChannelSig(family='logic_hook', actor='CwLevelupCallbacks',
                      mode='compute',
                      group_id=f'hook:CwLevelupCallbacks@{gs.write_seq + 1}')


def on_level_up_change(gs: GameState, old_level: int | None,
                       new_level: int, source: str) -> None:
    """升级连锁调度器(level 值变更回调,任意经验源升级的唯一连锁入口;
    固定位置参数——回调族纪律)。

    调用点两处:①``GameState._write_logic_frame`` level 分支尾(逻辑写
    经验自动覆盖:买经验上报 / grant_xp);②``settle_xp_observe`` 跨级
    显式调(模拟器观察笔经验结算——观察口本身零回调,连锁挂在「结算」
    上,非挂在观察写上)。

    三块连锁序(见模块头):信号置位(幂等布尔)→ spy 世界分支声明
    入簿记队列(模拟器门)→ 节节高升 2★ 发放(持有判定 + 模拟器门,
    连跳按中间等级序列逐级,费用随各自等级)→ 升级窗口达成位记录
    (内部自判条目已登记 ∧ 未记录 ∧ 等级达标,零旁路条件安全)。
    """
    if old_level is None:
        return
    old_l = int(old_level)
    new_l = int(new_level)
    if new_l <= old_l:
        return
    from sr_od.application.currency_war.kernel.cw_gain_effects import (
        apply_level_up_char_gift,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        _record_lv8_window_start,
        enqueue_levelup_world_decl,
        mark_shop_randomized_pending,
    )
    from sr_od.application.currency_war.kernel.cw_investments import (
        level_up_gift_active,
        spy_on_level_up_active,
    )
    # 连锁①spy:信号置位无条件(实机真刷店,信号供重开位读真牌面);
    # 声明只进簿记队列(队列消费面 = 上报尾读取 + 模拟器 advance 尾排空,
    # 双消费点取走即清;槽注申报写端唯一)。
    if spy_on_level_up_active(gs) > 0:
        mark_shop_randomized_pending(gs)
        from sr_od.application.currency_war.sim.cw_sim_ports import (
            sim_backend_installed,
        )
        if sim_backend_installed():
            enqueue_levelup_world_decl(gs, WorldDecl(
                next_screen=_SPY_DECL_NEXT_SCREEN,
                trigger='spy_shop_refresh'))
    # 连锁②gift:连跳逐级(费用档随各自达成等级);live 未装配 = 零采样
    # 零写,实机该角色由游戏引擎发放,bench 重观察自然吸收(在卷定谳)。
    if level_up_gift_active(gs):
        from sr_od.application.currency_war.sim.cw_sim_ports import (
            sim_backend_installed,
        )
        if sim_backend_installed():
            apply_level_up_char_gift(
                gs, levels=list(range(old_l + 1, new_l + 1)),
                sig=_levelup_gift_sig(gs))
    # 连锁③锚:升级窗口达成位(结算时点记锚 = 跨级当拍生效位;xp-only
    # 帧无升格不进本调度器,迟到达纠偏仍由买经验上报尾与发放桥每拍复检
    # 两既有挂点承载)。
    _record_lv8_window_start(gs)


def take_levelup_world_decl(gs: GameState) -> WorldDecl | None:
    """声明簿记队列取走头部(消费口一:买经验上报尾读取;取走即清,
    None = 空)。余项(防御形态:同栈多跨级双声明时上报只取走本动作
    自己的那笔)留待模拟器 advance 尾统一排空,消费点纪律见容器槽注。"""
    queue = gs.pending_levelup_world_decls
    if not queue:
        return None
    return queue.pop(0)
