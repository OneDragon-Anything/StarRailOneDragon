"""卖出通道排除仲裁·统一装配 A(P78 卖出资格仲裁不变量)。

架构根:4 个卖出通道函数 × 9 个动作发出点 + 1 个投影读位的
排除装配此前在 7 个调用点各自手搓,共 5 种互不一致形态——同一架构根
在备战 F1(双攻击报告)与 entry 两处 funding 空装配(方案
v3 §2.9 新格 A)、P56 投影脱节(新格 B)反复发病。本模块把「不许卖谁」
收拢为单一入口 ``sell_exclusions``;通道保留「何时卖/卖多少/卖序」
(触发、止盈、排序、特有禁令),判据本体纯函数零改(B3 纪律,方案
v3 §3.2)。

落点声明(方案 v3 §3.1):不放 kernel、不放 criteria——A 消费策略器
会话态(StrategyState.v3_intention / 统一动作发出登记簿),kernel 输入纯度
禁反向依赖;criteria 判据本体 = 纯函数,排除集由消费位传入。

A 段构成(方案 v3 §2.2 三段式;**身份段已随统一让位优先级迭代 3.4
退役**——静态不许卖名单〔义务基座 ∪ 保护集 ∪ registry 核心 ∪ 乙分支
获取 ∪ 终局键集标签〕整段拆除,卖出取用改由统一让位序列
criteria/priority.sell_order 承载「谁后卖」,总纲 §2.5;本模块保留的
全部为循环防线,总纲 §2.4 保留项):

1. 窗口段:press 与 stall_protect 两类买入共簿登记
   {名 → (买因,登记轮)},活跃判据 = 登记轮 == 当前轮(与 T3 同界,
   P78-2b)。**排除面 = press 类**:垫保类的通道处置属通道对价段
   defer(T3 不升入排除,方案 v3 §2.2 第 3 段——垫保在凑息是绝对跳过、
   在 M4/funding 是降序放行 = 转化类,P78-5′ 四关系表「放行(已登记
   语义保持)」),经 ``stall_protect_active`` 视图喂 defer 参数;
   硬排除会杀死转化类放行 = 已登记语义破面。press 类无对价豁免(P78-1
   无条件下),全通道硬禁。current_round=None ⇒ 窗口段失效
   = INV 显式例外,方向 = 放行向(V2-09;三读端同源 state.round_num,
   轮号恒可得,None 为死分支防御位)。
2. L1 同轮硬面(r408「买后禁卖」
   不变量的载体化恢复):kernel ``GameState.round_fresh_buys`` 轮键事实集
   (``fresh_buys_sell_face`` 读端自治,全因类完备——每笔买入无条件
   写入且先于合成捷径分支)并入排除集;读端不消费
   ``current_round`` 形参(None 漏接入调用帧不再构成硬面放行 = 对 V2-09
   在本面的显式翻转,v1 缺口 C 结构性闭合)。carve-out:垫保类
   登记名集从硬面剔除(继续走 defer 通道,硬排除杀转化类放行 =
   P78-5′ 破面);换线孤儿清算卖 = 账闭合豁免语境
   (P78-2a「线账闭合」,不经硬面,检查器 ``line_switch_collapse``
   豁免键兜住)。
3. 种子年龄豁免(P78-7,身份族构件,全通道生效)与通道对价段
   (projection 视图 = 循环防线全资格面再并 T3 活跃集,P78-6 读端
   同源,M7)。旧身份段的 funding 筹资兜底豁免(P78-5 四条件,
   ``funding_hold_fallback``)随身份段退役整删——豁免对象(常规面
   禁卖的持有件)不再存在。

动作发出登记统一(/§3):``LaunchCause`` 闭集
{obligation, press, stall_protect}(hold 类随 C1 单卡核心与囤货臂
两买臂退役删除——3.4;登记闭集外值拒收),买入分支逐一映射
(``LAUNCH_CAUSE_BY_ARM``,定稿载体);T3 垫保簿与 ②(b) 压牌库簿
完全合一为单载体双视图(载体属性沿用 T3 簿名——执行侧 cw_op_deploy
鸭子类型读取(duck typing)契约在先,禁改名破契约)。生命周期四出口:卖出销 / 部署销 /
合成销(V2-05 新增)/ 轮界销;账闭合按五键分键承载(close_on_sell/
deploy/merge/round/switch)供矩阵断言可观测。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_card_identity import (
    is_engine_piece,
)
from sr_od.application.currency_war.kernel.cw_deploy_logic import (
    fresh_buys_sell_face,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    game_state_of,
)
from sr_od.application.currency_war.kernel.cw_intention import (
    locked_buy_membership,
)
from sr_od.application.currency_war.kernel.cw_merge_simulate import (
    merge_material_stale_names,
    same_star_count,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )

#: 卖出通道闭集(方案 v3 §3.1 + 迭代 2026-10-12 P78 五通道重映射)。
#: 新通道必须先在此登记再接入调用——枚举外值拒收(单一入口防线,防「新通道
#: 绕 A 手搓排除」的第五通道复发形态)。通道族谱(shop_session §5 承继
#: 清单 P78 行):interest = 节末凑息;m4_fuel = 备战域晶矿腾位/告警
#: 自救;m4_fuel 语义现由评估器 'ore_make_room'/'self_rescue' 场景承载;
#: line_switch 换线整合通道已随候选-锁定制停用撤档(line_and_upgrade
#: §1.6);shop_swap = 店内置换账通道已随六步流程整段替换退役(3.4,
#: SCENE_SPECS 同步);funding = 会话内筹资通道已随统一获取让位评估
#: 纳入统一管理时退役(roster-plane1-union design §2.2 第 4 项:金不足与席满
#: 同一评估,场景行与通道同批删除——阶段 2 偏差⑤预留点的兑现);
#: projection = 投影视图读端(P78-6 读端同源)。
SELL_CHANNELS: frozenset[str] = frozenset({
    'interest', 'm4_fuel', 'projection',
})

#: 买因闭集(买入分支 → 因果类映射的值域)。闭集外值
#: 拒收——新买入分支只有归入某因果类才合法(登记闭集强制,方案 v3 §5.3)。
#: hold 类已随 C1 单卡核心与囤货臂两买臂退役删除(3.4)。
LAUNCH_CAUSES: frozenset[str] = frozenset({
    'obligation', 'press', 'stall_protect',
})

#: 窗口段适用范围买因(P78 §2.2 第 2 段):压牌库与垫保两类,τ=同轮
#(登记轮==当前轮);obligation 类 τ=∞,由卖出/部署/合成/换线出口闭合,
#: 登记仅作账本观测面,不入窗口段排除。
WINDOW_LAUNCH_CAUSES: frozenset[str] = frozenset({'press', 'stall_protect'})

#: 买入分支 → 因果类全映射(定稿载体;方案 v3 §3.1 表;
#: 分支计数对现值校正见行内申报,12/13 为历史口径)。
#: 落写点的分支 = 窗口段两类(shop 动作发出点 _emit_buy 统一登记)+ ②(b)
#: 按 prio 两分显式传因;obligation 类的 M2 族产物由卖出/部署/合成/换线
#: 出口闭合(写点不覆盖行为),写点随矩阵批按需落——本表钉全映射防
#: 第 5 分支复发。hold 类行(core_single_card_buy 族/protection_hoard)
#: 已随两买臂退役删除(3.4);hub_option 期权行已随乙分支纳入统一管理时删除(P86)。
LAUNCH_CAUSE_BY_ARM: dict[str, str] = {
    'm2_line_member': 'obligation',
    'm2_locked_member': 'obligation',
    'm2_stockpile': 'obligation',
    'm2_merge_completion': 'obligation',
    # 序 1 扩展臂 ×2(11 号稿 §1 序 1 扩展臂条款,义务类):
    # 货架资格臂 = 单张买入估值的方向投资件(虚拟 top3 资格,τ=∞ 义务账,
    # 卖出资格走 P78 义务账期);冷启动臂 = 双空窗三羁绊 1 费件见即买
    # (义务可逆——1★ 全额退)。均无金线闸、见即买,席位检查走买入管线
    # 自带。
    'shelf_qualify_buy': 'obligation',
    'cold_start_buy': 'obligation',
    'dominance_buy': 'press',
    'm6_stockpile': 'press',
    # 泄金阶梯档 1(可上场非定向买;富余金 discretionary 面,同 M6/dominance
    # 因果类。档 1)。
    'press_buy_deployable': 'press',
    'ev_buy': 'press',
    # 序 2 场况插件买(迭代 2026-10-12-prep-shop-workflow-redesign 批
    # 3.6;板面羁绊差一人进下一档——获取后即上场的场景性增持,非义务
    # 非持有,归 press 类)。
    'scene_plugin_buy': 'press',
    # ②(b) 按 prio 两分(obligation/press),动作发出点显式传因覆写本行。
    'dead_gold_press_buy': 'press',
    'fuel_filler_stall': 'stall_protect',
    't3_unlocked_hemostat': 'stall_protect',
}


def launch_cause_of(reason: str) -> str | None:
    """买入分支名(CwActionBuyCardParam.reason)→ 因果类(LAUNCH_CAUSE_BY_ARM 查因;
    未映射分支 = None)。A4 硬闸:动作发出点
    ``_emit_buy`` 对 None 改抛错——静默跳过登记分支 = 新分支绕过登记与
    一切以字典为分支全集的穷举断言,抛错后该字典才是分支全集的硬地基;
    新分支必须先入映射表再可发出。"""
    return LAUNCH_CAUSE_BY_ARM.get(reason)


#: 统一动作发出登记簿载体属性(StrategyState 字段名)。沿用 T3 垫保簿旧名:
#: 执行侧 cw_op_deploy.prune_fuel_filler_deployed /
#: record_fuel_filler_held_postbuy 按鸭子属性读本名(属性契约级接入调用,
#: 禁 import 策略模块),改名 = 静默断供给(读 None → 部署销恒 0);
#: 语义已从 T3 专用簿升级为四因类登记簿,见 StrategyState 字段注释。
LAUNCH_REGISTRY_ATTR: str = 'cw4_fuel_filler_stall_buys'


def _counters_of(session: StrategySession) -> dict | None:
    """分键状态容器读口(缺状态容器 = 不计数,不静默造桶——计数面自带载体)。"""
    ct = getattr(state_of(session), 'cw4_counters', None)
    return ct if isinstance(ct, dict) else None


def _bump(counters: dict | None, key: str, n: int = 1) -> None:
    """分键累加(counters=None = 观测缺载体,零静默跳过)。"""
    if counters is not None:
        counters[key] = counters.get(key, 0) + n


def _registry_of(session: StrategySession) -> dict:
    """登记簿读口(dict 载体缺省就地建;旧 set 载体容忍在读端逐点处理)。"""
    st = state_of(session)
    reg = getattr(st, LAUNCH_REGISTRY_ATTR, None)
    if not isinstance(reg, dict):
        reg = {}
        setattr(st, LAUNCH_REGISTRY_ATTR, reg)
    return reg


def _entry_norm(value: object) -> tuple[str, int | None]:
    """登记值归一:新形态 (买因,轮);旧 T3 int 轮戳 → stall_protect
    (T3 值形态在先,归一只读不回写——就地改值会破坏既有测试/会话的
    载体观测面,值升级由写端自然完成)。"""
    if isinstance(value, tuple) and len(value) == 2:
        return str(value[0]), (int(value[1]) if value[1] is not None else None)
    if isinstance(value, int):
        return 'stall_protect', value
    return 'stall_protect', None


# ===== 动作发出登记 API(写端 + 四出口生命周期;/§3)=====


def register_launch(session: StrategySession,
                    name: str, *, cause: str, round_num: int,
                    star: int | None = None, cost: int | None = None,
                    ) -> bool:
    """买入动作发出登记(写端单一源;P78 §2.2 窗口段载体)。

    簿形态 = {名: (买因,登记轮)},同名重登记覆盖(最新买因胜——
    排除面按名判定,单名多笔并发登记以最近授权为准,同轮界同过期)。

    ``cause`` 闭集外值抛错(登记闭集强制)。
    (hold 类附类资格断言已随 hold 买因退役删除——3.4:hold 类买入 =
    C1 核心 + protection_hoard 两臂,均已退役;资格面 = 保护集 ∪
    registry 核心并集的身份判据随身份段退役消失。)

    返回登记是否落账(空名 = False;测试断言用)。
    """
    if not name:
        return False
    if cause not in LAUNCH_CAUSES:
        raise ValueError(
            f'未知买因 {cause!r}:合法闭集 = {sorted(LAUNCH_CAUSES)}'
            ' (新买因先登记 LAUNCH_CAUSES 再接线)')
    _registry_of(session)[name] = (cause, int(round_num))
    return True


def consume_on_sell(session: StrategySession, name: str) -> None:
    """出口①卖出销(账兑现):该名被任一通道实际卖出时销账,防同
    visit 内第二次命中。分键 close_on_sell(五键账闭合,方案 v3 §5.3)。
    容旧 set 载体(兼容未升级会话;旧形态无因类,不计分键)。"""
    if not name:
        return
    reg = getattr(state_of(session), LAUNCH_REGISTRY_ATTR, None)
    if isinstance(reg, dict):
        if name in reg:
            del reg[name]
            _bump(_counters_of(session), 'close_on_sell')
    elif isinstance(reg, set):
        reg.discard(name)


def prune_on_deploy(session: StrategySession, deployed_names: object) -> int:
    """出口②部署销(件离场闭合):上板名登记账移除(保护使命完成,
    P24/M1 同帧部署语义;漏销 = 后续误保面)。分键 close_on_deploy。
    返回销账数(测试断言用)。容旧 set 载体(仅成员摘除,不计分键
    ——旧载体无因类语义,计了也是假账)。"""
    reg = getattr(state_of(session), LAUNCH_REGISTRY_ATTR, None)
    if isinstance(reg, set):
        hit = {n for n in reg if n in set(deployed_names or ())}
        reg.difference_update(hit)
        return len(hit)
    if not isinstance(reg, dict) or not reg:
        return 0
    hit = [n for n in reg if n in set(deployed_names or ())]
    for n in hit:
        del reg[n]
    if hit:
        _bump(_counters_of(session), 'close_on_deploy', len(hit))
    return len(hit)


def consume_on_merge(session: StrategySession, name: str) -> int:
    """出口②′合成销(V2-05 新增;件离场闭合):同名 1★ 三张买入应用
    即合成 2★,登记的 1★ 副本离场——不销则同名再买 1★ 被过禁(≤1 轮
    有界)。分键 close_on_merge。返回销账数(测试断言用)。未接入调用
    窗口有界性:滞留 ≤1 轮,轮界销兜底(方案 v3 §3.1 申报)。"""
    if not name:
        return 0
    reg = getattr(state_of(session), LAUNCH_REGISTRY_ATTR, None)
    if isinstance(reg, dict) and name in reg:
        del reg[name]
        _bump(_counters_of(session), 'close_on_merge')
        return 1
    if isinstance(reg, set) and name in reg:
        reg.discard(name)
        return 1
    return 0


def active_window(session: StrategySession, current_round: int | None, *,
                  counters: dict | None = None) -> frozenset[str]:
    """窗口段读端(P78 §2.2 第 2 段;出口③轮界销,读端就地销账)。

    **排除面 = press 类**(硬禁;垫保的通道处置 = defer 对价,见模块
    docstring 第 2 段与 P78-5′ 四关系表)。两类共享轮界过期生命周期
    (本读端过期销账不分因类):press 类过期计 press_window_expired_
    round,stall_protect 类过期计 t3_protect_expired_round(键名零断
    链),账闭合键 close_on_round 合计(五键分键,方案 v3 §5.3)。
    current_round=None ⇒ 窗口段失效(V2-09:INV 显式例外,方向 =
    放行向;轮不可得帧登记全集按过期销账,T3 既有语义继承)。
    同帧多读端幂等:首个读端完成过期销账,后续读端见空集零重复计数。
    """
    return _expire_and_read(session, current_round,
                            face_causes=frozenset({'press'}),
                            counters=counters)


def stall_protect_active(session: StrategySession, current_round: int | None,
                         *, counters: dict | None = None,
                         ) -> frozenset[str]:
    """T3 垫保单类视图(stall_protect 因果类;defer 通道专用——垫保
    在凑息是绝对跳过、在 M4 是降序放行,通道对价语义,与窗口
    段排除是两个面。funding 通道随会话内筹资场景退役后,降序放行
    域 = m4_fuel 单通道)。press 类登记名不入本视图;轮界过期与本视图共享
    单点销账(两类一同过期,过期计数按因类分键,禁双读端重复计数)。"""
    return _expire_and_read(session, current_round,
                            face_causes=frozenset({'stall_protect'}),
                            counters=counters)


def _expire_and_read(session: StrategySession, current_round: int | None, *,
                     face_causes: frozenset[str],
                     counters: dict | None) -> frozenset[str]:
    """轮界过期(两类共簿共享)+ 因类过滤读(窗口段与 T3 视图单点)。

    旧裸 set 载体(轮戳缺失)= 轮界硬兜底整集失效并升级 dict(T3 先例
    mandate.py 既有语义平移)。obligation/hold 类登记不轮界过期
    (τ=∞,P78-2a),由卖出/部署/合成/换线出口闭合。
    ``counters=None`` = 读会话状态容器(state_of(session).cw4_counters;
    缺状态容器 = 不计数,窗口段诊断键经 sell_exclusions 读端照常暴露)。
    """
    if counters is None:
        counters = _counters_of(session)
    st = state_of(session)
    reg = getattr(st, LAUNCH_REGISTRY_ATTR, None)
    if reg is None:
        return frozenset()
    if not isinstance(reg, dict):
        # 旧 set 载体:整集过期销账后升级 dict(因类不可辨,按 T3 计)
        setattr(st, LAUNCH_REGISTRY_ATTR, {})
        _bump(counters, 't3_protect_expired_round', len(reg))
        _bump(counters, 'close_on_round', len(reg))
        return frozenset()
    rn = int(current_round) if current_round is not None else None
    expired = []
    for n, value in list(reg.items()):
        cause, seen = _entry_norm(value)
        if cause not in WINDOW_LAUNCH_CAUSES:
            continue   # obligation/hold 类 τ=∞,不轮界过期
        if rn is None or seen is None or seen != rn:
            del reg[n]
            expired.append(cause)
    if expired:
        _bump(counters, 'close_on_round', len(expired))
        _bump(counters, 't3_protect_expired_round',
              expired.count('stall_protect'))
        _bump(counters, 'press_window_expired_round',
              expired.count('press'))
    active = {n for n, value in reg.items()
              if _entry_norm(value)[0] in face_causes}
    return frozenset(active)


def _close_switched_obligations(session: StrategySession,
                                base: set[str]) -> None:
    """换线闭合读点(P78 §2.1 账闭合事件「线账闭合」;N6:撤销出口
    ①②③ 与换线同义同效):义务类登记名已不在义务基座 = 线账已闭合,
    登记账就地销账 + close_on_switch 分键。读点幂等(销账后不可再命中)。
    行为零面:义务类不入窗口段排除,本闭合纯账本观测(五键分键承载,
    方案 v3 §5.3)。"""
    reg = getattr(state_of(session), LAUNCH_REGISTRY_ATTR, None)
    if not isinstance(reg, dict) or not reg:
        return
    closed = 0
    for n in list(reg):
        cause, _seen = _entry_norm(reg[n])
        if cause == 'obligation' and n not in base:
            del reg[n]
            closed += 1
    if closed:
        _bump(_counters_of(session), 'close_on_switch', closed)


# ===== 义务镜像簿与换线孤儿证明(L1 carve-out 的证据载体)=====
# 为什么需要镜像簿:装配 A 身份段的换线闭合读点(``_close_switched_
# obligations``)会**就地销账**义务类登记——同帧更早的 A 读点(帧首
# 逻辑态读等)触发销账后,登记面不可再辨「曾义务」,L1 换线孤儿 carve-out
# 迟到读登记簿 = 永远扑空。义务买入镜像簿
# (scratch,轮戳)与登记账分离,跨销账存活 = 孤儿证明的载体(与
# shop 帧首 ``_sw_orphans`` 证明集同一依据)。
#
#: 义务类买入镜像簿 scratch 键(shop 动作发出点 _emit_buy 写,义务类登记
#: 落账同步落)。键常量原宿主 = shop.py(_SHOP_OBLIGATION_BOOK_KEY),
#: 上移本模块:L1 carve-out 与 shop 帧首孤儿证明读点必须同源
#: 同键(第二键 = 双源漂移面)。
_OBLIGATION_BOOK_KEY: str = 'shop_obligation_buy_rounds'


def obligation_book_of(session: StrategySession) -> dict:
    """义务类买入镜像簿读口(scratch 载体,局级生命周期;缺省就地建)。"""
    book = state_of(session).scratch.setdefault(_OBLIGATION_BOOK_KEY, {})
    return book if isinstance(book, dict) else {}


def line_switch_orphans_of(session: StrategySession, base: set[str],
                           round_num: int) -> frozenset[str]:
    """本轮线账闭合孤儿证明集(镜像簿 ∧ 登记轮 == 当前轮 ∧ 已出基座)。

    = 本轮义务登记名 ∧ 已出义务基座,两者合取即登记簿线账闭合事件
    (销账谓词单一源 = ``_close_switched_obligations`` 的「义务类 ∧
    ∉ 基座」;base 解析调用方须传 ``_resolve_base`` 同一解析)。bench
    在场义务件的轮内账闭合出口唯一 = 换线闭合(卖出销/部署销/合成销
    都以件离场为前提),合取不误标;跨轮名随轮戳剪枝(陈旧证明不洗白,
    )。读点幂等(剪枝只删 ≠ 当前轮的陈旧戳)。"""
    book = obligation_book_of(session)
    for _n in [k for k, v in book.items() if v != round_num]:
        del book[_n]
    return frozenset(n for n, v in book.items()
                     if v == round_num and n not in base)


def _autonomous_round(session: StrategySession) -> int | None:
    """读端自治轮号(黑板结构化:原 last_state 优先/
    shop_state_frame 兜底的双槽解析改状态容器 node 读口——与登记相位写端
    同源,设计件《商店黑板容器化方案》§2.4-2)。NodeKey 未定 = None
    (调用方按 fail-closed 方向处置:硬面不 carve)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        round_num_of,
    )
    node = game_state_of(session).node.value
    if node is None:
        return None
    return int(round_num_of(game_state_of(session)))


# ===== 种子年龄豁免登记簿(P78-7)=====


#: 种子获取名集的 StrategyState 载体属性名({名: (位面,获取轮)})。
#: duck-typed 属性契约(与 SEED_ACQUISITIONS_ATTR 同纪律):改名 = 静默断供给。
SEED_ACQUISITIONS_ATTR: str = 'cw4_seed_acquisitions'

#: 种子保护窗(轮)。【注·已登记裁定】判据表「种子 ≥2 轮不回卖
#: 0 容忍」与 L3 D5 检测器机械窗 ≤2 行同值——已登记设计裁定值
#: 非拟合(零调参,禁调)。
SEED_WINDOW_ROUNDS: int = 2


def seed_acquisition_eligible(name: str, star: int | None,
                              bench: object, deployed: object) -> bool:
    """种子获取资格谓词单一源(P78-7 种子定义;shop 动作发出点与测试同消费,
    禁调用侧手搓第二份)。

    = 1★(1★ 全额退是「往返净金 0」的前提,P76 甲;2★/3★ 往返非净 0
    且无 1★ 燃料通道可达,不在设计范围内,P78-7 星适用范围边界)∧ 引擎件
    (``is_engine_piece`` 注册表现算)∧ 购买时未持有(bench∪deployed
    无同名——发出时点等价读法,与 D5/selfcalc ``held_names_upto``
    的上一轮末口径同语义,±1 行漂移窗口径声明见 selfcalc docstring)。
    """
    if star is None or int(star) != 1:
        return False
    if not is_engine_piece(name):
        return False
    held = {getattr(b, 'char_id', '') or '' for b in (bench or [])
            if b is not None}
    held |= {getattr(d, 'char_id', '') or '' for d in (deployed or [])
             if d is not None}
    return name not in held


def _seed_registry_of(session: StrategySession) -> dict:
    """种子簿读口(dict 载体缺省就地建;与动作发出登记簿同载体纪律)。"""
    st = state_of(session)
    reg = getattr(st, SEED_ACQUISITIONS_ATTR, None)
    if not isinstance(reg, dict):
        reg = {}
        setattr(st, SEED_ACQUISITIONS_ATTR, reg)
    return reg


def register_seed_acquisition(session: StrategySession, name: str, *,
                              plane: int | None, round_num: int) -> bool:
    """种子获取登记(写端单一源;shop._emit_buy 动作发出点消费,P78-7)。

    簿形态 = {名: (位面,获取轮)},同名重登记覆盖(最新获取胜,与
    动作发出登记簿同语义)。空名/位面缺读拒登记(fail-closed:位面本地
    轮号跨位面重启,缺位面使窗界算术跨位面双向失真——过保护或假
    过期;与 hold 类缺读拒登记同纪律)。登记即计数键 ``seed_acquired``
    暴露(「种子过渡窗无暴露」申报自此闭合;窗口终结
    后残余观测面 = sim D5 检测器,相邻轮命中应归零)。
    """
    if not name or plane is None:
        return False
    _seed_registry_of(session)[name] = (
        int(plane),
        int(round_num),
    )
    _bump(_counters_of(session), 'seed_acquired')
    return True


def _seed_frame_axes(session: StrategySession) -> tuple[
        int | None, int | None, frozenset[str]]:
    """种子读端轴 (位面,轮号, bench 名集)。

    轴源 = session 状态容器(黑板结构化改道,设计件 §2.4-2):
    - **plane/round 轴 = gs.node**(NodeKey;权威写端 = 派生规则四条分支,
      段入口粒度对轮/位面恒安全);
    - **bench 轴 = gs.bench**(prep 帧观察值 + visit 内逻辑态直写)。原
      「双帧并集」的活性闭合语义由状态容器活值天然承载:逐动作逻辑态直写
      (卖出自上报 bench 域)使店内新鲜买入即时在席,
      last_state 段入口滞后窗与逻辑态帧 prep 语境滞留窗一并消亡——
      对抗审查发现 1(新鲜种子账被活性闭合在获取 visit 内就地销毁)的
      防线由状态容器活值续承。
    NodeKey 未定帧 plane/round = None;bench 未观察 = 空集,消费侧
    fail-closed。"""
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_entries_of,
    )
    _gs = game_state_of(session)
    node = _gs.node.value
    cur_plane = int(node.plane) if node is not None else None
    cur_round = int(node.round_num) if node is not None else None
    bench_names = {(u.char_id if (u := bench_slot_unit(b)) is not None
                    else '') or ''
                   for b in bench_entries_of(_gs)}
    return (cur_plane, cur_round, frozenset(bench_names))


def seed_exclusions(session: StrategySession,
                    current_round: int | None = None) -> frozenset[str]:
    """种子年龄豁免读端(P78-7;装配 A 身份族第五构件,全通道生效)。

    三重闭合(语义单一源;候选面在卖出通道物理谓词处自然收窄):
    1. **位面闭合**:仅取位面==当前位面的账——过渡阶段桥建账随位面
       终结(P2 换人自由 = 发展优先不变量 01_math_framework §8-2 要求
       该闭合存在;D5 行序跨面紧邻不漏报是检测器过近似,非生产闭合
       语义,P78-7 账闭合段);
    2. **窗界闭合**:当前轮 − 获取轮 > ``SEED_WINDOW_ROUNDS`` 的账过期
       就地销(过度禁卖 ≤2 轮有界可判读,P78-3 同型);
    3. **活性闭合**:名不在 bench 名集(双帧并集,见
       ``_seed_frame_axes``)的账就地销(卖出/部署/合成 = 件离场机械判,
       P78-7 账闭合①②;双侧证据皆缺才销,防单帧滞后误销新鲜账)。

    轮号优先消费形参(与 ``active_window`` 同槽同源 state.round_num),
    缺省时黑板帧自治。位面或轮不可得帧 = fail-closed 保持保护面;
    过度禁卖有界:账随写端覆盖与活性闭合自然收敛。读端幂等:闭合
    销账只发生一次。"""
    reg = getattr(state_of(session), SEED_ACQUISITIONS_ATTR, None)
    if not isinstance(reg, dict) or not reg:
        return frozenset()
    cur_plane, frame_round, bench_names = _seed_frame_axes(session)
    cur_round: int | None = (int(current_round)
                             if current_round is not None else frame_round)
    for n, value in list(reg.items()):
        seen_plane, seen_round = value if isinstance(value, tuple) \
            else (None, value)
        # 位面闭合:账位面非当前位面即出集;任一侧位面不可得帧保留账
        # (fail-closed),由窗界/活性闭合兜底。
        if cur_plane is not None and seen_plane is not None \
                and seen_plane != cur_plane:
            del reg[n]
            continue
        if cur_round is not None and seen_round is not None \
                and cur_round - int(seen_round) > SEED_WINDOW_ROUNDS:
            del reg[n]
            continue
        # 活性闭合:bench 现读无此名 = 件离场(卖出/部署/合成)。
        if bench_names and n not in bench_names:
            del reg[n]
    # loop 后剩余账 = 位面匹配(或位面不可得保守保留)∧ 窗内 ∧ 名在席。
    return frozenset(reg)


# ===== 持久获取账与死库存对退出判据(G-S1 退出通道;数学论证 =
# proofs/p96-dead-pair-exit-dominance-n3.md)=====


#: 持久获取账的 StrategyState 载体属性名({名: (位面,最新获取轮)})。
#: duck-typed 属性契约(与 SEED_ACQUISITIONS_ATTR 同纪律):改名 = 静默
#: 断供给。与统一动作发出登记簿(临时账,四出口销账)生命周期解耦——本账
#: 是素材对退出判据 (c) 的唯一轮读源,判据按动作发出登记簿读会恒 no-op
#: (press 对 R2 首个窗口即被轮界销,病灶对永不满足年龄条件)。
ACQUISITION_LEDGER_ATTR: str = 'cw4_acquisition_ledger'

#: 退出判据时域下界 N(proofs P96;design §2.1.4 载体闭集最大寿命推导,
#: 零新自由参数):意图载体闭集中瞬态窗的最大寿命 = 种子年龄窗已登记窗长
#: (``SEED_WINDOW_ROUNDS``)+1——N<3 会卖掉种子窗仍开的对(撕 P78-7
#: 保护面),N>3 保护无任何载体的意图(病灶本体);时钟起点 = 较晚成员
#: 的获取账登记轮(重基声明见 P96,非种子簿原义的种子获取轮)。
DEAD_PAIR_EXIT_MIN_AGE: int = SEED_WINDOW_ROUNDS + 1

#: 死库存对退出遥测键族(design §2.1.5;事件口径 C1 = 名×轮去重,见
#: ``dead_pair_exit_release``;键登记单一源 = 本清单与写点,禁消费位裸写):
#: - ``dead_pair_exit_released``:进入释放集的名数(释放评估量);
#: - ``dead_pair_exit_guard_kept_*``:素材对在位但未释放,按保留原因
#:   分子键 _k(义务基座成员)/_no_entry((c) 账覆盖缺口:缺登记/位面
#:   失配/轮号缺读——N2 拆分,窗内保留与账缺口暴露分键)/_young((c)
#:   真窗内 age<N)/_chain(3★ 链 1★ 分支保留)。(_identity 保留因
#:   分键已随身份段退役删除——3.4,身份段不再排除释放成员。)
DEAD_PAIR_EXIT_RELEASED_KEY: str = 'dead_pair_exit_released'
DEAD_PAIR_EXIT_KEPT_PREFIX: str = 'dead_pair_exit_guard_kept'


def _acq_ledger_of(session: StrategySession) -> dict:
    """持久获取账读口(dict 载体缺省就地建;与种子簿同载体纪律)。"""
    st = state_of(session)
    reg = getattr(st, ACQUISITION_LEDGER_ATTR, None)
    if not isinstance(reg, dict):
        reg = {}
        setattr(st, ACQUISITION_LEDGER_ATTR, reg)
    return reg


def register_acquisition(session: StrategySession, name: str, *,
                         plane: int | None, round_num: int,
                         star: int | None = None) -> bool:
    """获取账登记(写端单一源 = shop._emit_buy 动作发出点,与种子登记同位)。

    簿形态 = {名: (位面,最新获取轮)},同名重获取覆盖为最新轮——对时
    钟起点语义:素材对自「较晚成员获取」那刻才成立,覆盖写即天然取
    max(两获取轮)。全因类无条件写(A4 硬闸之后的活决策逐笔落账,不分
    买因),**星级覆盖 1★**(star≠1 拒登记:2★/3★ 成件非素材对成员,覆盖
    写会刷新在场 1★ 对的轮戳致晚释放——覆盖写覆盖定钉死,N1 规格)。
    空名/位面缺读拒登记(fail-closed,与种子簿同纪律)。位面本地轮号,
    账内条目恒同位面(跨位面条目由读端位面闭合清除)。

    闭合 = 读端惰性清扫(``dead_pair_exit_release`` 内):位面闭合 +
    全场域活性闭合,与动作发出登记簿四出口(轮界/换线/部署/合成销)解耦
    ——合成销语义注:合成补齐买入在动作发出点提前 return 不落本账,该名
    旧账由活性闭合(2★ 化后 1★ 对离场)就地销。
    """
    if not name or plane is None:
        return False
    if star is not None and int(star) != 1:
        return False
    _acq_ledger_of(session)[name] = (int(plane), int(round_num))
    return True


def dead_pair_exit_release(session: StrategySession,
                           k_members: tuple[str, ...],
                           bench: object, deployed: object,
                           current_round: int | None, *,
                           cap_hold: int | None = None,
                           counters: dict | None = None,
                           ) -> frozenset[str]:
    """死库存素材对释放集单点函数(判据 (a)(b)(c) 三合取,
    proofs P96)。四卖出通道消费位统一经本函数计算后传
    ``merge_guard_release`` 形参——判据本体单点,通道禁自算第二份。

    判据(name 入集 ⟺ 全部合取):
    (a) 素材对在位:``same_star_count(name, 1, bench, deployed) ≥ 2``
        (计数单一源 = kernel;宇宙 = ``merge_material_stale_names`` 同源);
    (b) name ∉ base——base = ``_resolve_base`` 输出(义务重买集真值:
        终局阵容锁定态 = 截断集 B′,未锁态 = k_members);``cap_hold`` 必须 与同位
        ``sell_exclusions`` 的 cap_hold 同一帧现读传入(与装配 A 身份段
        第 1 构件同参同源,N3 钉死;None = 保宽 fail-closed 端,kept_k
        虚增方向保守可判读);
    (c) 账位面 == 当前位面 ∧ 当前轮 − 获取账登记轮 ≥
        ``DEAD_PAIR_EXIT_MIN_AGE``。账形态 = {名: 最新获取轮},同名覆盖
        写使「两成员均有登记 ∧ max(两登记轮)」折叠为单条目读(覆盖写
        覆盖 1★,全因类买入逐笔落账时条目即较晚成员轮);缺登记/位面失配/
        轮号缺读 → 不入集(fail-closed 保守向)。已知边界(如实申报):
        混合获取对(一张买一张赠得)条目仅承买得张,轮戳早于成对轮,
        至多提前 N−1 轮释放(赠得为事件条件流低频,design §2.1.7-3 同族)。

    附带保守保留(不释放,按原因计数):3★ 链 1★ 分支——同名 2★ 在场
    (bench∪deployed 全场域,N4 钉死,漏保留 = 漏保护向)→ _chain。
    (kept_identity 保留因分键已随身份段退役删除——统一让位优先级迭代
    3.4:身份段不再排除任何释放成员,释放即可卖,观察位无对象。)

    ``bench``/``deployed`` = 当前帧全场域(与同位通道评估同一帧数据);
    兼容 None。活性闭合域 = bench∪deployed 全场域(单条分支上板的对账须
    活);观察缺读(双侧名集全空)不闭合(fail-closed,与种子簿同向)。
    ``current_round`` 优先消费形参(与 sell_exclusions 同槽同源);
    位面 = 黑板帧 node 自治读。

    遥测 = 事件口径 C1:**名×轮去重**(去重载体 = session 相位簿
    ``cw4_dead_pair_exit_frame``,同轮多通道重复评估/腾位环重试不重复
    计数;轮推进自动失效)——同轮商店/备战两域重复评估同名视为同一
    释放事件,判读按「名×轮」频次读。``counters`` None = 读会话状态容器。
    """
    st = state_of(session)
    ct = counters if counters is not None else _counters_of(session)
    _bench = [b for b in (bench or ()) if b is not None]
    _deployed = [d for d in (deployed or ()) if d is not None]
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )

    def _cid_of(x: object) -> str:
        u = bench_slot_unit(x) if getattr(x, 'kind', None) is not None else x
        return (getattr(u, 'char_id', '') or '') if u is not None else ''

    bench_names = {_cid_of(b) for b in _bench}
    deployed_names = {_cid_of(d) for d in _deployed}
    node = game_state_of(session).node.value
    cur_plane = int(node.plane) if node is not None else None
    cur_round = int(current_round) if current_round is not None else None

    # C1 相位去重簿(名×轮;跨轮/跨位面推进自动失效)
    phase = (cur_plane, cur_round)
    seen = getattr(st, 'cw4_dead_pair_exit_frame', None)
    if not isinstance(seen, dict) or seen.get('phase') != phase:
        seen = {'phase': phase, 'names': set()}
        st.cw4_dead_pair_exit_frame = seen
    counted: set[str] = seen['names']

    # 持久获取账惰性闭合(位面 + 全场域活性;与动作发出登记簿四出口解耦)
    reg = getattr(st, ACQUISITION_LEDGER_ATTR, None)
    if isinstance(reg, dict) and reg:
        held = bench_names | deployed_names
        for n, value in list(reg.items()):
            seen_plane, _seen_round = value if isinstance(value, tuple) \
                else (None, value)
            if cur_plane is not None and seen_plane is not None \
                    and seen_plane != cur_plane:
                del reg[n]      # 位面闭合:账随位面终结
                continue
            if held and n not in held:
                del reg[n]      # 活性闭合:卖出/部署/合成件离场机械判
    entries = reg if isinstance(reg, dict) else {}

    def _kept(key: str, name: str) -> None:
        """保留原因计数(C1:名×轮去重;计数与计算分离——每次调用
        都完整复算释放集,去重只覆盖计数面,多通道重复评估拿到同一集)。"""
        if name in counted:
            return
        counted.add(name)
        _bump(ct, f'{DEAD_PAIR_EXIT_KEPT_PREFIX}_{key}')

    _locked, base = _resolve_base(session, k_members, cap_hold=cap_hold)
    out: set[str] = set()
    for name in merge_material_stale_names(_bench, _deployed):
        if not name:
            continue
        if name in base:
            _kept('k', name)        # 义务基座成员:买家空集论证不成立面
            continue
        entry = entries.get(name)
        seen_plane, seen_round = entry if isinstance(entry, tuple) \
            else (None, None)
        if (cur_plane is None or cur_round is None
                or seen_plane is None or seen_round is None
                or seen_plane != cur_plane):
            _kept('no_entry', name)     # 账覆盖缺口(含缺读 fail-closed)
            continue
        if cur_round - int(seen_round) < DEAD_PAIR_EXIT_MIN_AGE:
            _kept('young', name)        # 真窗内:N 下界保护(测试②)
            continue
        if same_star_count(name, 2, _bench, _deployed) >= 1:
            _kept('chain', name)        # 3★ 链 1★ 分支保守保留(N4 全场域)
            continue
        out.add(name)
        if name not in counted:
            counted.add(name)
            _bump(ct, DEAD_PAIR_EXIT_RELEASED_KEY)
    return frozenset(out)


# ===== 装配 A(循环防线段:窗口段 + L1 同轮硬面 + 种子年龄豁免)=====


def _resolve_base(session: StrategySession,
                  k_members: tuple[str, ...],
                  cap_hold: int | None = None,
                  ) -> tuple[frozenset[str] | None, set[str]]:
    """义务基座解析单点(低-1 修复平移;基座 = 容量可行截断集 B')。

    终局阵容锁定态 = ``locked_buy_membership(ist, cap_hold=传参)`` 截断义务集
    B'(宽−窄成员 M2 不再义务重买),未锁态 = ``k_members``。
    ``cap_hold`` = 调用方从决策帧现读
    (``cw_intention.locked_buy_cap_hold(state)``;板面容量是帧事实,
    session 无公共权威链,禁加镜像读——显式传参是唯一合法通道),
    None = 保宽(fail-closed 零漂移端;无帧态调用位如兼容再出口)。
    返回 (锁定解析结果,基座集):解析结果供本模块内单点消费
    (换线闭合读点的基座对账),禁调用侧自选基座——基座 = M2 会重买的
    集合(R1 后 = B'),与 shop.py ``obligation_members`` 装配同一语义源
    = cw_intention.locked_buy_membership 截断口径。装配 A 身份段已随
    统一让位优先级迭代 3.4 退役,本解析残余消费 = 义务镜像簿的线账
    闭合对账与换线孤儿证明集(P96 (b) 判据的「义务重买集真值」基准,
    防释放 M2 会重买的素材对)。
    """
    st = state_of(session)
    locked = locked_buy_membership(
        getattr(st, 'v3_intention', None), cap_hold=cap_hold)
    base = set(locked) if locked is not None else set(k_members)
    return locked, base


def sell_exclusions(session: StrategySession,
                    k_members: tuple[str, ...], *, channel: str,
                    current_round: int | None = None,
                    cap_hold: int | None = None) -> frozenset[str]:
    """统一装配 A 单一入口(P78 INV 主不变量;/§3)。

    任何卖出通道的资格排除必须经本入口装配——「不许卖谁」独占于 A,
    消费位禁手搓排除集。全量形态 = **循环防线三构件**(总纲 §2.4 保留项):
    窗口段 ∪ L1 同轮硬面 ∪ 种子年龄豁免(P78-7);projection
    通道视图 = 上述全资格面再并 T3 活跃集(P78-6 读端同源/M7)。

    身份段退役申报(统一让位优先级迭代 3.4,dismantle §3):原第一段
    「义务基座 ∪ 保护集 ∪ registry 核心 ∪ 乙分支获取 ∪ 终局键集标签」
    整段拆除——卖出取用改由统一让位序列(priority.sell_order)承载
    「谁后卖」,身份排除不再存在;换线闭合读点(义务类登记账对账)迁入
    本函数(读端幂等,行为零面)。

    ``channel``:卖出通道标记(SELL_CHANNELS 闭集;枚举外值抛错)。
    ``current_round``:窗口段活跃判据轮号(M5 定稿;三读端同源
    state.round_num);None ⇒ 窗口段失效 = INV 显式例外,方向 = 放行向
    (V2-09)。**L1 同轮硬面不消费本形参**(读端自治 fail-closed,
    对 V2-09 的显式翻转);垫保 carve-out 在轮号不可得帧不剔除
    (fail-closed 方向 = 硬面保持全集)。
    ``cap_hold``:义务基座截断容量 = 调用方从
    决策帧现读 ``cw_intention.locked_buy_cap_hold(state)``;None = 保宽
    (fail-closed 零漂移端,无帧态调用位缺省)。
    """
    if channel not in SELL_CHANNELS:
        raise ValueError(
            f'未知卖出通道 {channel!r}:合法闭集 = {sorted(SELL_CHANNELS)}'
            ' (方案 v3 §3.1;新通道先登记 SELL_CHANNELS 再接线)')
    # 基座单次解析(换线闭合读点 + L1 换线孤儿证明集两消费共用;
    # 闭合读点原宿主 = identity_exclusions,随其退役迁入本函数)。
    _locked0, _base0 = _resolve_base(session, k_members, cap_hold=cap_hold)
    _close_switched_obligations(session, _base0)
    # L1 换线孤儿证明集读点:证据载体 = 义务
    # 镜像簿(轮戳跨销账存活,见 line_switch_orphans_of 节注),禁读
    # 登记簿——同帧更早的装配 A 读点已触发换线闭合就地销账,登记面
    # 不可再辨「曾义务」。base 解析与销账谓词同一(_resolve_base 单一
    # 源,禁调用侧自选)。轮号自治:消费位漏传轮号时从黑板帧
    # 解析;全缺 = 不 carve(fail-closed 方向:硬面保持全集)。
    _carve_round = (int(current_round) if current_round is not None
                    else _autonomous_round(session))
    _sw_orphans: frozenset[str] = frozenset()
    if _carve_round is not None:
        _sw_orphans = line_switch_orphans_of(session, _base0, _carve_round)
    excl: set[str] = set()
    if current_round is not None:
        excl |= active_window(session, current_round)
    # L1 同轮硬面(r408「买后禁卖」恢复):
    # 读源 = kernel fresh_buys 轮键事实集(全因类完备,见模块 docstring
    # L1 段);减两个 carve-out——
    # ① 垫保:stall_protect 登记活跃名从硬面剔除,继续走既有
    #    defer 通道(凑息绝对跳过/M4 降序放行 = 转化类放行
    #    保全,P78-5′ 已登记语义;funding 通道已随筹资场景退役,
    #    降序放行域 = m4_fuel 单通道);轮号不可得帧不剔除(fail-closed)。
    # ② 换线孤儿:孤儿清算 = 账闭合豁免语境,不经硬面。
    _t3 = (stall_protect_active(session, current_round)
           if current_round is not None else frozenset())
    _fresh = fresh_buys_sell_face(session)
    if _fresh:
        excl |= _fresh - _t3 - _sw_orphans
    # 种子年龄豁免(P78-7;全通道硬禁,无新增对价豁免):
    # 相邻轮种子回卖封口(同轮已由 L1 硬面覆盖;设计 0 容忍的
    # 生产落地,过渡窗加重面的治理)。三重闭合(位面/窗界/
    # 活性双帧并集)语义单一源 = seed_exclusions docstring。carve 语义
    # 按账闭合事件分界(P78-2a 族,对抗审查发现 2 修订):
    # ①换线孤儿 carve 保留 = 线账闭合清算语境:本轮义务买入出基座,
    #   其账已闭合(P78-2a),整合清算卖是已闭账位的清仓非活跃账抵消,
    #   必须照常发出并带 line_switch_collapse 证明标记(
    #   打标制;无此 carve 会把 seed18 整合标记卖堵死,reason_matrix
    #   TestLineSwitchOrphanSeed18 实证);
    # ②垫保 carve 不适用于种子面(初版曾 carve,对抗审查发现 2 打回):
    #   种子账活跃(无账闭合事件)时,同轮经 M4/funding 转化放行卖出 =
    #   P78-1 定义性抵消(同 visit 买种卖种,净金 0 而动作帧+P01 再遇
    #   窗双损;P78-1 对兜底豁免同样构成上界)——P78-5′ 对价分支要求通道
    #   产物「确定可用且可达成义务账」,刚开的桥建账被同帧作废、退款
    #   净 0 不达成任何账,两条分支皆不成立。非种子垫保件的 defer 转化
    #   放行语义零改(走 L1 的 _t3 carve,本行不动)。
    excl |= seed_exclusions(session, current_round) - _sw_orphans
    if channel == 'projection':
        # T3 活跃集并入投影视图(资格级 defer 的读端同源;通道侧
        # defer 参数不升入 A,判据本体零改——方案 v3 §2.8/M7)。
        excl |= stall_protect_active(session, current_round)
    return frozenset(excl)


def sell_hold_exclusions(session: StrategySession,
                         k_members: tuple[str, ...]) -> frozenset[str]:
    """凑息通道排除集兼容再出口(Z1)。

    生产消费位已全量迁移 ``sell_exclusions(channel='interest',
    current_round=...)``——本名保留 = 测试/外部引用零断链。

    Z1 身份面退役申报(统一让位优先级迭代 3.4):原身份面构成
    「保护集 ∪ registry 核心」随装配 A 身份段整段退役;动态买入登记
    (L1 同轮硬面)保留,语义 = 循环防线全资格面(无轮号 ⇒ 窗口段
    失效,V2-09 放行向例外)。

    旧 F1 终局阵容锁定清空语义已废除(P78-3:终局阵容锁定定型不是任何买因类的账闭合
    事件;漏口修法 = 轮界过期,随窗口段在 sell_exclusions 承载)——
    本出口不再消费动态登记、也不再清空旧载体。
    """
    return sell_exclusions(session, k_members, channel='interest')


# ===== 空板止损守卫(后态单条件判定,零自由参数)=====


#: 空板止损守卫拒因分键(单一源;判据函数拒帧计数与测试同消费,禁裸写)。
#: 设计出处 = supply_arbitration_design/DESIGN.md §6.4(v2
#: 应修-3 单条件后态判定版)+ 总图对账重审(reviews/出口族对账重审.md
#: 「现在可落:空板止损单件」行)。
EMPTY_BOARD_SELL_GUARD_KEY: str = 'empty_board_sell_guard'


def empty_board_sell_blocked(deployed: object, *,
                             counters: dict | None = None) -> bool:
    """空板止损守卫:待卖后 deployed 占用数为 0 ⇒ 拒卖(返回 True)。

    **后态单条件判定**(旧设计 §6.4 v2 应修-3):谓词输入 =
    该笔卖出执行后的上场占用数,而非卖出前的板面状态——前置形态对
    「从有板逐个卖穿到空」路径每次卖出瞬间恒假,最后一卖照常放行,
    守卫目标(不进空板态)失守;后态判定自然覆盖「板已空连卖 bench」
    与「卖掉仅存部署位」两类路径。现行策略面唯一卖类 = CwActionSellBenchParam(不
    改变 deployed)⇒ 后态占用数 = 现占用数(状态容器占用判定,
    占用数,禁 len);取后态形态是为覆盖未来卖 deployed 类通道
    的接入调用对账——消费位传「占用数减待卖件」即可,谓词本体零改。

    **数学地基(支配性结构判据,零自由参数)**:空板帧任意 bench 卖出
    相对不卖弱劣——1★ 全额退净金 0(P76 甲)+ 部署/合成期权损失 ≥0;
    2★+ 卖出净损金(P76 甲手续费)+ 期权损失。守卫非消费授权、零 hp、
    零动作发出点;拒因分键落 ``counters[EMPTY_BOARD_SELL_GUARD_KEY]``,
    禁静默。复合事务(M4 腾位/统一获取让位)卖出分支在空板帧同被覆盖 =
    资格面收窄 → 消费位走各自既有「无候选」诚实停摆路径(m2_retry_
    exhausted / bench_full / 空动作发出,先例 = P78-4 燃料资格收窄);
    恢复正路 = 部署(P24 零支出)与买面,守卫零覆盖。若观测证明腾位抑制
    代价超界,回 ADR 对表加显式豁免(闭集增项),禁消费位手搓绕行。

    ``deployed`` = 上场域(状态容器行域单位或任意可迭代表;None
    或占用数 0 均判拒——None = 缺读 fail-closed 拒,资格判据禁缺读
    放行)。占用数 = 状态容器占用判定(元素非 None 计 1;行域本身即紧凑
    占用序,benchchar-retirement P4 状态容器形)。``counters`` None = 不计数
    (谓词纯判读形态,测试用)。
    """
    occupied = sum(1 for d in (deployed or ()) if d is not None)
    if occupied > 0:
        return False
    if counters is not None:
        counters[EMPTY_BOARD_SELL_GUARD_KEY] = \
            counters.get(EMPTY_BOARD_SELL_GUARD_KEY, 0) + 1
    return True
