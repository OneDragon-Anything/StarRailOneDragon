"""货币战争 执行层状态载体(ExecState;session.md as-designed §2.4/§5.5)。

职责来源裁定(用户 2026-09-06):session 只承载观察数据;**动作执行与
画面 op 运行产生的状态**(拖拽失败计数/发射连败/防重入标志/对账期望账/
同轮买卖互斥事实账)归执行侧——产生者 = op/执行侧代码,不是读屏采集。
落点 = 局容器 ``CurrencyWarMatch.exec_state``(生命周期 = 一局,与
session 同建同灭;``megastar_candidate_clicked`` 按 session.md §2.4 B1
定案必须落局容器级,不留实施批裁量)。

访问口(设计 §5.5「执行侧载体访问口注入 kernel」候选的实现面):
- 框架/ops 直通口 = ``ctx.cw_match.exec_state``(局容器 dataclass 字段,
  构造即存在);
- 无 ctx 面(kernel 判据层 / 策略器 / sim / 遥测只读) =
  :func:`exec_state_of`(session 旁表解析——kernel 不 getattr session
  猜宿主,一律经本定义口)。旁表绑定单一源 =
  ``CurrencyWarMatch.__post_init__``(局容器构造即把自身 exec_state
  绑到 session);裸构造 session(测试/sim 注入)首访时惰性建
  (生命周期随 session 对象,见下「桩面存储」)。

桩面存储(不可弱引用对象,SimpleNamespace 测试桩族):把 ExecState
**作为属性挂在 session 对象自身**——生命周期随对象同灭,无旁表条目
可泄漏;属性不可写的对象(__slots__ 类族)退回 id() 键普通 dict 兜底
(量极小,进程内驻留)。id 兜底不承载可弱引用对象:T-25 定谳的
「桩 GC 后 id 复用 → 新 session 拿旧 ExecState 串号假红」根因即
id 键条目永不清理,挂对象属性后该串号通道不复存在。
"""
from __future__ import annotations

import weakref
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_prep_actions import (
        PrepAction,
    )

_EXEC_BY_SESSION: weakref.WeakKeyDictionary[object, ExecState] = \
    weakref.WeakKeyDictionary()
#: 桩面兜底第二级:属性不可写对象(__slots__ 族)的 id() 键普通 dict。
#: 挂对象属性(第一级)不可行时才落此表;条目量极小,进程内驻留。
#: 不用于可弱引用对象(走弱引用表),也不用于属性可写的桩(挂对象自身)。
_EXEC_BY_SESSION_ID: dict[int, ExecState] = {}
#: 桩面第一级:ExecState 挂 session 对象自身的属性名(生命周期随对象;
#: 前缀命名空间化防撞宿主属性)。
_EXEC_STATE_ATTR = '_cw_exec_state'


def _bind_stub(session: object, exec_state: ExecState) -> None:
    """不可弱引用对象的绑定:挂对象自身属性;属性不可写才退 id 兜底。"""
    try:
        setattr(session, _EXEC_STATE_ATTR, exec_state)
    except (AttributeError, TypeError):   # __slots__ 等属性只读对象
        _EXEC_BY_SESSION_ID[id(session)] = exec_state


def bind_exec_state(session: object, exec_state: ExecState) -> ExecState:
    """局首绑定(session → 当局执行侧载体;幂等覆写)。单一调用点 =
    ``CurrencyWarMatch.__post_init__``;测试/sim 特殊装配可显式调。

    session 注解 object(非 StrategySession)是如实声明:桩面走
    SimpleNamespace 族(见模块头「桩面存储」),本口按弱引用/属性双路径
    鸭子类型解析,不要求宿主具体类型。"""
    try:
        _EXEC_BY_SESSION[session] = exec_state
    except TypeError:   # 不可弱引用对象(测试桩)→ 挂对象自身
        _bind_stub(session, exec_state)
    return exec_state


def exec_state_of(session: object) -> ExecState:
    """执行层状态访问口(无 ctx 面唯一合法通道;禁 getattr session 猜宿主)。

    session 为 None → 无宿主,返回**一次性**空载体(不缓存不共享——
    None 的 id 恒定,缓存即「全局共享哑载体」跨调用串染;正常调用方
    上游守卫,本口不抛以保 best-effort 观测面不炸)。裸 session(未绑
    局容器)→ 惰性建独立载体(生命周期随 session 对象,见模块头
    「桩面存储」;sim/测试语义 = 会话级执行态)。
    """
    if session is None:
        return ExecState()
    try:
        ex = _EXEC_BY_SESSION.get(session)
    except TypeError:   # 不可弱引用对象(测试桩)
        ex = getattr(session, _EXEC_STATE_ATTR, None)
        if ex is None:
            ex = ExecState()
            _bind_stub(session, ex)
        return ex
    if ex is None:
        ex = ExecState()
        _EXEC_BY_SESSION[session] = ex
    return ex


@dataclass
class ExecState:
    """一局的执行层状态(27 具名(含 _pending_chosen_supply)
    2;生命周期/防重入语义逐字段自原宿主平移,值域与缺省一致——载体每局
    新建即天然清零)。账外收编账本 = ADR-0563「落位裁量」节。

    生命周期分级(迁移核对判据:落点生命周期 ≥ 原生命周期,session.md
    §7.2-3):局级(失败记忆/互斥账/bail 计数/tracked 账/期望账)、跨环
    (发射连败)、节点/visit(防重入/期望覆盖)、环级(defer 门——
    生命周期分级纠偏见 ADR-0642:唯一复位 = 战斗结算写端,环入口清零
    无写点)。
    """

    # 腾席链 DeployMove 失败记忆(char_id → 失败计数)。拖拽被拒 → 跳过
    # 重试同目标(拖失败不消费 bench,下轮还在)。局级。
    deploy_fail_counts: dict = field(default_factory=dict)
    # 装备拖拽失败记忆((装备名, 角色名) → 失败计数)。连续失败
    # ≥2 次 = 该落点对拉黑。局级。
    equip_drag_fail_counts: dict = field(default_factory=dict)
    # 出战发射连败计数(prep_actions._start_battle 写;跨环重入存活——
    # 环级计数随 Director 重建清零,挡不住 round_fail → 外环重入)。
    # 达 PrepActionExecutor.LAUNCH_DEAD_LIMIT → 停机留证(cw_launch_dead)。
    launch_dead_streak: int = 0
    # 巨星 handler 点击执行防重入。**必须局容器级**(防 new CwScreenMegastar
    # instance 重置 instance flag → re-click toggle 反选 → 卡死;落 op
    # 实例 = 每次新建实例清零 = 原始事故复发,session.md §2.4 B1 定案)。
    megastar_candidate_clicked: bool = False
    # 补给刷新 1 次已用(跨 handler 实例持久;发出刷新点击即置位,不等
    # 验效,防重入反复尝试)。节点级(screen_op.md §8.4 裁执行侧)。
    _supply_refresh_used: bool = False
    # 遭遇分支刷新 1 次已用(同款跨 handler 语义)。节点级。
    _encounter_refresh_used: bool = False
    # 投资策略逐卡刷新已发射槽集(ADR-0600 §3.3;发射即记不等验效,同款防重入;
    # [索引定义] 坐标系: 策略屏画面槽位下标左→右 0-2,与 PickEvent.
    #             refresh_slots 同源;取值时机: 执行期,发射点击即 add)。
    # 复位 = visit 起点单点(CwScreenInvestStrategy 实例首帧入口锚验通过后
    # clear——同 visit 重入不清保防重入,跨 visit 新实例必清防陈旧集泄入)。
    # 「可否再刷」权威判定 = 逐卡计数现读(cw_node_obs reader),本集唯一
    # 职责 = 同 visit 防重入(双保险不同源,观察赢规则照常辖)。
    _invest_refresh_used_slots: set[int] = field(default_factory=set)
    # 奖励球留置计数码(纠偏 = ADR-0642/T-297,覆写两处失实:①注释曾
    # 宣称「门=2 防空转环」——全库无任何比较消费点;②「环级——Director
    # 每次环入口清零」——无环级清零写点,唯一复位 = 战斗结算
    # cw_screen_battle_wait.py 写端)。DeferSpheres 全库零发射者,字段
    # 保留候死词汇清理批,退役需随删 director 两消费分支 + 复位点。
    # 框架流程侧。
    defer_count: int = 0
    # star 回退停机钩子计数(char → 连续回退次数;连续 2 节点回退 = 真识别
    # 问题 → 停机保画面排查;读回恢复即清零)。执行侧停机钩子载体。
    star_regression_count: dict[str, int] = field(default_factory=dict)
    # BailToOuter 同因计数(局级,环重建不清零——ping-pong 诊断;≥3 记
    # [cw!])。流程侧。
    bail_reason_counts: dict[str, int] = field(default_factory=dict)
    # 执行侧跟踪账(随动更新;双账断言 screen_op.md §2.3(ii))。两账形状
    # 契约 = pad 态定长槽表**含 None**(ADR-0316/0392;tracked_bench_chars
    # T-308 后=reconcile 写回经 bench_from_compact 重建的槽位表,恒 pad 态;
    # tracked_deployed = deployed_from_compact 写回/mutate 入口 pad_deployed
    # 的定长 10 槽表)——注解按契约含 None(T-308 落地审义务,G2 全闭环)。
    tracked_bench_chars: list[BenchChar | None] = field(default_factory=list)
    tracked_deployed: list[BenchChar | None] = field(default_factory=list)
    # bench 布局代次(T-308 S3 churn 事件通道,最小面)。[索引定义] 坐标系
    # = 单调递增计数器(非槽位号、非下标);取值时机 = reconcile 纠漂写回期
    # 递增(kernel/cw_reconcile,唯一写点)/ 投影播种期快照(每段入口观察)+
    # 单动作循环每动作消费前现读检差(cw_op_buy_cards,唯一消费点)。命中 =
    # 布局已重排,在飞动作的 bench_idx 代际失效 → 序列决策契约截断+按 tracked
    # 重播种+重入决策。当前架构 reconcile 均在 visit 外跑,visit 内恒不变
    #(S2+S1 后纯未来防御:防 visit 中段未来引入读屏/对账点时布局变化
    # 无人知晓)。局级生命周期(载体每局新建即天然清零)。
    bench_layout_epoch: int = 0
    # —— 同轮买卖互斥事实账本(r408;随 cw_round_ledger 宿主迁出)——
    # 同轮轮键(决策层轮键重置段维护);register_round_sold 带轮键自校验。
    v2_round_key: tuple | None = None
    # 同轮已卖集(engine_seed 对集内卡名禁买,防「卖→见未持有→买回」缩幅
    # 永动机)。恢复局空集 = 守卫缺位窗口(单轮轮键,下轮自愈;session.md
    # §3.2 评级「中」,恢复轮判读义务 6.2-4)。
    v2_round_sold: set[str] = field(default_factory=set)
    # 买牌单元期望态(cw_screen_prep.BuyExpect)。坐标系 = 哪次购买:一次
    # RunBuyPhase 单元购买意图的「单元执行后应然态」。取值时机 = 购买意图
    # 落账——shop.py 单元收尾写入;消费 = 主环下一轮 heavy 定型帧对账后清
    # None,跨单元不残留。None = 无挂起期望。
    pending_buy_expect: object = None
    # 经验期望账本(cw_screen_prep.XpLedger;纯记账+对账,零决策)。
    # None = 本局未锚定(账本未建)。
    xp_expect_ledger: object = None
    # (期望态条目表容器 expected_state 已随 ADR-0651 两态制废除——
    #  ExpectedEntry 登记/覆盖点 diff 对账整套拆除;op 逻辑效果 =
    #  cw_expected_state.apply_op_effect 直接写 session 字段。)
    # 备战单轮最后动作签名(账外收编:备战单轮 op 写,外循环无进展守卫
    # 读;None = 无在途动作签名)。
    last_prep_action_sig: tuple | None = None
    # —— 账外补充·第二波(实施批收尾扫描按 §6.1 收编的执行侧动态属性,
    # 写端 = 画面 op/发射位,原挂 session 属历史宿主错位)——
    # 补给绕行已完成(节点内一次性)。
    _supply_detour_done: bool = False
    # 补给选定暂存(§3.4.5 chosen_supply 出口验真后写端的中转载体)。
    # 写点 = CwScreenSupplyNode._do_action 选定列确认时(真选分支;兜底
    # 点卡/刷新轮不写 = 真选守卫);清点 = 出口验真(标识-补给阶段消失)
    # 写入 GameState 后取走,及重入轮入口(上轮确认未落地即弃,防陈旧
    # 选跨轮/跨节点误写)。节点级生命周期——下一补给节点选定即覆盖,不
    # 跨节点消费;None = 无挂起选定。
    _pending_chosen_supply: tuple[str, str, bool] | None = None
    # 备战挂起对账单元队列(单元收尾逐个清)。
    cw_prep_pending_accts: list = field(default_factory=list)
    # 接管采集已完成(节点内一次性)。
    cw_takeover_collect_done: bool = False
    # 接管采集重试计数。
    cw_takeover_tries: int = 0
    # fenced 臂上一帧状态(deploy 写读)。
    cw4_swap_arm_on: object = None
    # 备战环 StartBattle 发射结果(F3/T-174,ADR-0610)。True = 本环发射
    # 且验证成功;False = 发射但验证失败(「备战环返回 success=True
    # status=…验证失败…」形态——1-1 冻结局实证该形态曾使 0j 恢复链预算
    # 每环被误复位,预算形同虚设);None = 本环未发射(缺省)。写入端 =
    # cw_screen_prep 备战单轮执行记账处(StartBattle 是终结动作,每环至多
    # 一写);消费端 = cw_loop 备战环出口 on_result 的 0j 预算复位判定,
    # 读后即清防跨环残留。环级生命周期。
    last_prep_battle_launch_ok: bool | None = None
    # —— 账外补充·第三波(session 动态属性锚点收编,逐波清单 =
    # ADR-0563「落位裁量」节第三波)——
    # 轮内新鲜度排除载体(ADR-0530 立项;ADR-0611 §3-1 定谳为 L1 卖侧闩
    # 「本轮已买」半边,与 v2_round_sold「已卖」半边同族互斥账)。
    # 键式 = {'phase': (plane, round_num), 'names': set[str]},相位失配 =
    # 跨轮整体作废(读取零销账,无逐名生命周期面);None = 本局未登记。
    # 写点 = shop._emit_buy 全部 BuyCard 发射位 + sim/engine_p1 决策帧,
    # 经 cw_deploy_logic.record_fresh_buy 单口;读端 = fresh_buys_of
    # (换出守卫)+ fresh_buys_sell_face(L1 卖侧闩,fail-closed)。
    cw4_swap_fresh_buys: dict | None = None
    # 位面节点序列台账(cw_state.PlaneNodeLedger;备战帧查表与逐帧校验的
    # 去重/豁免状态,[索引定义] 坐标系 = seq_by_plane 键为 1-based 位面号,
    # 序列下标 0-based = 该位面第 i+1 轮,取值时机 = 写入端整行重读快照,
    # 定义详注在载体类头)。写入端 = 画面 op 三处(CwScreenPlaneIntel
    # 位面详情 / CwScreenInvestEnv 环境重读 / CwScreenPrep 备战节点行),
    # 经 cw_state.get_node_ledger / ledger_update_plane 单口;读端 =
    # cw_state.ledger_node_type(kernel 判据 + 遥测 recorder)。
    # None = 本局未建(读口惰性建)。
    plane_node_ledger: PlaneNodeLedger | None = None
    # 恢复局旗标(D2 live 接线;R1 缺口承接,判定方案 R3 规则六)。True =
    # 本局为恢复对局(新 match 但游戏在中局续跑)——弹窗腿在派生 hist 空时
    # 禁用不猜(防把恢复局首弹窗误推断成开局节点 1),消化后备战帧腿 A 权威
    # 接管。写端 = cw_loop 恢复检测两确认点(_iter==1 战斗帧恢复检测 /
    # 备战帧 resume_candidate 确认,``_mark_session_resumed`` 单口);读端 =
    # cw_observation._feed_board_state(经 observe_screen_context(resumed=…)
    # 进派生规则,读值不落旗标——一次性会话语义,非消费即清)。session 级
    # 生命周期:新 match 新执行态 = 缺省 False(正常新局恒 False,开局推断
    # 合法不受误伤)。
    cw_resumed_match: bool = False


# ============================================================ op 逻辑效果推进
# (波 5b 自 kernel/cw_expected_state 迁入:模块名随期望态条目表概念退役,
# ADR-0651 两态制存续函数整体搬迁,零行为变化;消费点 = root prep_actions
# 执行器两处 + _overlay_confirm.register_confirm_arrival。
# ⚠️ 动作词表/合成引擎依赖一律函数内惰性 import:cw_state 模块级反向
# import 本模块(exec_state_of),模块级引入会成环——沿用本仓懒加载惯例。)

def _char_fee(name: str) -> int | None:
    """角色招募费(注册表单一源);未知 → None(回金不可算 → 不推字段,
    观察帧覆盖兜底)。"""
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
    """last_state.gold 逻辑推进(可为负;None 视 0 基线——金账由商店波顶/
    结算屏可信读覆盖修正,观察赢)。"""
    st = getattr(session, 'last_state', None)
    if st is None:
        return
    base = getattr(st, 'gold', 0) or 0
    st.gold = base + delta


def _owned_add(session, item: str) -> None:
    """last_owned_equips 逻辑推进:+1 件(选卡/确认到账类)。"""
    owned = list(getattr(session, 'last_owned_equips', None) or [])
    owned.append(item)
    session.last_owned_equips = owned


def apply_op_effect(session, action: PrepAction | dict, *,
                    produced_by: str = 'PrepActionExecutor',
                    detail: str = '') -> list[dict]:
    """原子 op 的逻辑效果推进(两态制标准语义,ADR-0651;两执行面同源入口)。

    按游戏规则把 op 的可推算效果**直接写 session 字段**(gold delta/
    owned 增减),返回推进清单 [{path, value, kind}](组合动作子动作
    效果上抛形态,只含本函数实际写过的字段)。回金不可算(角色费未知/
    无 tracked 身份)→ 不推字段、不挂账,观察帧覆盖兜底(ADR-0651:
    推算不了不是挂账理由)。

    显式不建模盲区(EXPECTED_STATE §6 原申报语义存续):``_handle_bench_full``
    席满急救(买经验×10 + 卖前几槽)不经执行器 → 不在推进面,该形态由
    观察覆盖兜底(声明而非遗漏)。
    """
    effects: list[dict] = []
    if session is None:
        return effects
    from sr_od.application.currency_war.kernel.cw_prep_actions import (
        PickBoxCard,
        SellBench,
        SellDeployed,
    )
    from sr_od.application.currency_war.kernel.cw_vocab import (
        DEPLOYED_FRONT_CAPACITY,
        iter_occupied,
        sell_refund,
    )

    def _eff(path: str, value, kind: str) -> None:
        effects.append({'path': path, 'value': value, 'kind': kind})

    if isinstance(action, SellBench):
        bench, _dep = _session_tracked(session)
        bc = next((b for b in iter_occupied(bench) if b.slot == action.slot), None)
        fee = _char_fee(bc.char_id) if bc is not None else None
        if bc is not None and fee is not None:
            refund = sell_refund(bc.star, fee)
            _advance_gold(session, refund)
            _eff('gold', f'+{refund}(sell_refund {bc.star}星×{fee}费)', 'gold')
    elif isinstance(action, SellDeployed):
        _bench, dep = _session_tracked(session)
        idx = (action.slot - 1 if action.row == 'front'
               else DEPLOYED_FRONT_CAPACITY + action.slot - 1)
        bc = dep[idx] if 0 <= idx < len(dep) else None
        fee = _char_fee(bc.char_id) if bc is not None else None
        if bc is not None and fee is not None:
            refund = sell_refund(bc.star, fee)
            _advance_gold(session, refund)
            _eff('gold', f'+{refund}(sell_refund {bc.star}星×{fee}费)', 'gold')
            for eq in (getattr(bc, 'equips', None) or []):
                _owned_add(session, eq)
                _eff(f'owned[{eq}]', '+1(卖场上装备全额返还)', 'owned')
    elif isinstance(action, PickBoxCard):
        chosen = ''
        for token in (detail or '').replace('选卡', ' ').split():
            chosen = token.strip()
            break
        if chosen:
            _owned_add(session, chosen)
            _eff(f'owned[{chosen}]', '+1(武装箱选卡)', 'owned')
    elif isinstance(action, dict):
        # 确认类到账(dict 形态;{'op','item'}):owned 本体推进。
        # ConfirmStrategy 不在此推(active_strategies 本体追加 = handler
        # 确认成功后既有写点,cw_screen_invest_strategy)。
        op = action.get('op', '')
        item = action.get('item', '')
        if op in ('ConfirmSupply', 'ConfirmBox', 'ConfirmTome') and item:
            _owned_add(session, item)
            _eff(f'owned[{item}]', f'+1({op})', 'owned')
        elif op == 'BuyCard':
            # dict 形 BuyCard(模拟/离线入口):合成引擎算购买数,金账
            # 逻辑推进;tracked 本体推进 = 执行器/调用方辖。
            _apply_buy_card(session, action, _eff)
    else:
        # 显式不推进理由(原 §3 铁律枚举,两态制下语义存续):
        # - OpenBox/OpenTome:箱/典籍不消失(仅画面态,消耗在选卡确认);
        # - OpenShop(含 read_only)/EnsureShop*:画面态周转,零局状态变更;
        # - StartBattle:进战斗,hp/gold/streak 由结算屏观察覆盖接管;
        # - RunDeploy/RunEquip:组合动作,tracked 本体推进 = 执行器
        #   (_sync_tracking_after_sell/_track_move_deployed 单一写者);
        # - LevelUp:经验账本推进 = CwScreenPrep._xp_apply_levelup
        #   (XpLedger 通道);金账点击数不可推算 → 观察覆盖兜底;
        # - DeployMove:tracked 位移 = 执行器 _track_move_deployed;
        # - ClickSpheres:pending_reward 无 session 字段载体,零推进;
        # - RunBuyPhase:BuyExpect 载体走 exec_state.pending_buy_expect
        #   独立通道(shop.py 买组收尾写,heavy 定型帧消费)。
        pass
    return effects


def _apply_buy_card(session, action: dict, _eff) -> None:
    """dict 形 BuyCard 的金账推进(merge_simulate 单一引擎算购买数)。"""
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
# 候裁9 词汇迁入(原 kernel/cw_state.py;T-7 W8 定谳记录第 1 归宿):
# 席位/槽位跟踪域 + 节点台账 + 布局转发。宿主依据 = ExecState 自申报
# tracked_bench_chars/tracked_deployed 定长槽表契约与 plane_node_ledger。
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


@dataclass
class BenchChar:
    """备战栏/已上阵角色(= strategy/06 的 ``Unit``;加 ``equips``)。"""
    slot: int
    char_id: str = ""    # 角色id(SIFT/OCR 名);未知 ""
    faction: str = "?"   # 阵营
    star: int = 1        # 星级
    position_pref: str = "back"  # 命途定位 front/back(来自 get_role_position)
    # Sequence(快照拷贝语义落码(ADR-0465 §9):TurnState 快照拷贝侧固化为 tuple;session/state
    # 活对象仍 list)——读点(deploy_bench 装备校验/reconcile 配对)均为
    # Sequence 消费,写端仅 session/state 活对象(list 语义保留)。
    equips: list[str] | tuple[str, ...] = field(default_factory=list)
    # 占槽物品标记(部署伪槽修复批 ②,防线字段;B1 返工=显式标记形态):
    # True = 该槽画面是物品(箱/典籍/书册卡/揭示卡等)非角色。坐标系 =
    # 备战栏 1-based slot(与 slot 字段同系);取值时机 = 部署装配期快照;
    # 写入端 = 部署装配点(cw_op_deploy.assemble_bench_list 构造时显式写),
    # 识别来源 = obs 单一源精确档(cw_identity_obs.bench_item_slots
    # fuzzy=False)的命中产出;obs 未命中的槽位恒 False(缺省),与本字段
    # 无关的 char_id='' 不触发(kernel 对 True 恒 held、拒因 'item_slot',
    # 「照旧上」fail-open 语义不涉本字段)。sim 不产伪槽:缺省 False 零差。
    is_item_slot: bool = False


def snapshot_copy(bc: BenchChar) -> BenchChar:
    """TurnState 快照语义的元素拷贝(落码判据见 ADR-0465 §9):浅拷贝 + equips 固化
    为 tuple——视图/快照帧与 session.tracked_*(就地写端=shop.py
    mutate_bench_deployed 星级/装备拼接、deploy_bench 装备覆盖)断开
    对象别名,「快照不在帧间存活」由机制保证而非消费纪律约定。
    成本已量化(ADR-0465 §9):每次 decide_prep ~19 元素 ×6 字段 <20µs,
    占帧预算 <0.1%。隔离锁=test_cw_migration_budget_authority(迁移哨兵)。"""
    from dataclasses import replace
    return replace(bc, equips=tuple(bc.equips or ()))


def rebuild_deployed_from_board(board: dict[str, int], back_max: int = 6,
                               max_count: int | None = None) -> list[BenchChar | None]:
    """从 board(OCR 阵营计数真值)重建 ``deployed`` 槽位表(ADR-0392;下标
    0-3=前排/4-9=后排,按 position_pref 路由落槽)→ ``deployed_count()``
    对齐实际阵上数。

    旧 ``read_game_state`` 不填 deployed → 恒 ``[]`` → 所有门失效,本 helper 从 board
    重建 deployed。
    max_count(= level)cap —— 多羁绊角色在 board 多阵营计数(大丽花=击破+盛会之星算 2),
    sum(board) > 实际 deployed(level)→ deployed_count 虚高 → _saving_for_interest + bench-space 门
    **误触**(board 没满却当满 → 不买 target 到 bench → 被 block)。cap at level = 实际 deployed 上限。
    """
    compact: list[BenchChar] = []
    back_left = back_max
    for faction, count in board.items():
        for _ in range(count):
            if max_count is not None and len(compact) >= max_count:
                return deployed_from_compact(compact)
            pref = "back" if back_left > 0 else "front"
            if back_left > 0:
                back_left -= 1
            compact.append(BenchChar(slot=0, faction=faction, star=1,
                                     position_pref=pref))
    return deployed_from_compact(compact)


# ===== bench 槽位语义 helpers(ADR-0316;消费端唯一合法入口)=====


def iter_occupied(bench: list[BenchChar | None]):
    """迭代占用槽(滤 None)——bench 迭代单一源,禁止裸 ``for b in bench``。"""
    return (b for b in bench if b is not None)


def bench_occupied(bench: list[BenchChar | None]) -> int:
    """bench 占用槽数(容量判据单一源,禁止 ``len(bench)``)。"""
    return sum(1 for b in bench if b is not None)


def bench_place(bench: list[BenchChar | None], bc: BenchChar) -> int | None:
    """放入首个空槽(买入落位语义);无空槽返回 None(=bench_full 拒)。

    放置时归一 ``bc.slot = 下标+1``(物理槽位 1-9,与 live 读链
    ``read_bench_chars`` 的 1-based 槽号同坐标系)。
    """
    for i, b in enumerate(bench):
        if b is None:
            bc.slot = i + 1
            bench[i] = bc
            return i
    return None


def pad_bench(bench: list[BenchChar | None]) -> list[BenchChar | None]:
    """pad None 到定长 BENCH_CAPACITY(就地补足,返回同引用)。"""
    while len(bench) < BENCH_CAPACITY:
        bench.append(None)
    return bench


def bench_from_compact(chars: list[BenchChar]) -> list[BenchChar | None]:
    """紧缩序列 → 槽位表(顺序放置;BenchChar.slot 已带 1-based 物理槽号
    时按槽放置)。旧语料/紧缩构造入槽位模型的适配单一源。"""
    bench: list[BenchChar | None] = [None] * BENCH_CAPACITY
    for bc in chars:
        # 形状双源防御(ADR-0316 持久态契约):输入可能是 pad 态(定长 9 含
        # None,如 mutate_bench_deployed 就地 pad 后的 exec_state_of(session).tracked_bench_chars)
        # 或紧凑态(无 None)——两种形态都是本适配源的输入域,None 直接跳过。
        if bc is None:
            continue
        slot = bc.slot if 1 <= bc.slot <= BENCH_CAPACITY else None
        if slot is not None and bench[slot - 1] is None:
            bench[slot - 1] = bc
        else:
            bench_place(bench, bc)
    return bench


# ===== deployed 槽位语义 helpers(ADR-0392;消费端唯一合法入口)=====


def iter_occupied_deployed(deployed: list[BenchChar | None]):
    """迭代占用槽(滤 None)——deployed 迭代单一源,禁止裸 ``for d in deployed``。"""
    return (d for d in deployed if d is not None)


def deployed_occupied(deployed: list[BenchChar | None]) -> int:
    """deployed 占用槽数(容量判据单一源,禁止 ``len(deployed)``——定长下
    len 恒 DEPLOYED_CAPACITY)。"""
    return sum(1 for d in deployed if d is not None)


def deployed_slot_no(idx: int) -> int:
    """槽位下标 → 排内 1-based 槽号信息位(0-3→前排 1-4;4-9→后排 1-6)。"""
    return idx - DEPLOYED_FRONT_CAPACITY + 1 if idx >= DEPLOYED_FRONT_CAPACITY \
        else idx + 1


def deployed_place(deployed: list[BenchChar | None], bc: BenchChar) -> int | None:
    """放入指定排的首个空槽(上场落位语义):position_pref='front' → 前排区
    0-3,'back' → 后排区 4-9(ADR-0392);放置时归一 ``bc.position_pref``、
    ``bc.slot``(排内 1-based 槽号信息位)与实际落位下标一致。首选排满时
    落全局首个空槽兜底,兜底跨排时 pref 随落位改写(写端治本,ADR-0605
    §5.2:sell_recorded 通道解析键 = deployed_idx→(排,槽号) 固定双射换算
    后按条目 pref/slot 命中,信息位与下标错位必漏匹配误归 unexplained;
    权威槽位 = 下标,信息位恒为派生,与 _apply_row_to_char 换排归一同向)。
    兜底保持「合法动作必成功」(旧行为 append 不看排,排容量门在上游)。
    无任何空槽返回 None。入口防御 pad(短列表=紧缩前缀,兼容旧构造;
    同 mutate_bench_deployed 的 pad_bench 入口防御)。
    """
    pad_deployed(deployed)
    lo, hi = ((0, DEPLOYED_FRONT_CAPACITY) if bc.position_pref == 'front'
              else (DEPLOYED_FRONT_CAPACITY, DEPLOYED_CAPACITY))
    for rng in (range(lo, hi), range(DEPLOYED_CAPACITY)):
        for i in rng:
            if deployed[i] is None:
                bc.position_pref = ('front' if i < DEPLOYED_FRONT_CAPACITY
                                    else 'back')
                bc.slot = deployed_slot_no(i)
                deployed[i] = bc
                return i
    return None


def pad_deployed(deployed: list[BenchChar | None]) -> list[BenchChar | None]:
    """pad None 到定长 DEPLOYED_CAPACITY(就地补足,返回同引用;紧缩前缀
    顺延占用 0..n-1——旧紧缩构造兼容,ADR-0392)。"""
    while len(deployed) < DEPLOYED_CAPACITY:
        deployed.append(None)
    return deployed


def deployed_from_compact(chars: list[BenchChar]) -> list[BenchChar | None]:
    """紧缩序列 → 槽位表(按 position_pref 路由落槽)。旧语料/紧缩构造入
    槽位模型的适配单一源(None 直接跳过——形状双源防御,同 bench_from_compact)。"""
    deployed: list[BenchChar | None] = [None] * DEPLOYED_CAPACITY
    for bc in chars:
        if bc is None:
            continue
        deployed_place(deployed, bc)
    return deployed


def _apply_row_to_char(bc: BenchChar, to_row: str) -> None:
    """记录实际站位 + 开拓者换排形态归一(DeployMove/动作 v2 单一源)。

    拖到另一排 = 命途切换(前台记忆/后台欢愉),羁绊随之变 → char_id
    同步换成目标排形态,faction 跟随首阵营(下游 board/装备计算自然对)。
    """
    bc.position_pref = to_row
    from sr_od.application.currency_war.data.cw_chars import get_char as _get_char
    from sr_od.application.currency_war.data.cw_chars import (
        is_trailblazer,
        trailblazer_form,
    )
    if bc.char_id and is_trailblazer(bc.char_id):
        bc.char_id = trailblazer_form(bc.char_id, to_row)
        _tc = _get_char(bc.char_id)
        if _tc is not None and _tc.factions:
            bc.faction = _tc.factions[0]

# ===== 位面节点序列台账(session 级权威表) ================================
# 权威依据(用户口述,最高权威):位面内节点类型与数量**只有投资环境选择能改变**
# (变异位唯一)→ 同一位面内节点序列是常量,可以「进位面时读一次建档 + 投资环境
# 选完后重读刷新」,此后每帧备战画面**查表**得当前节点类型,逐帧识别降级为校验。
# 旧逐帧识别的三类噪声(标签出现在即将到来节点下方 / 高亮态 Hu 不匹配 / 商店
# 遮挡坏帧)因此只影响校验票,不再直接污染决策输入。


@dataclass
class PlaneNodeLedger:
    """本局 per-plane 节点序列台账 + 逐帧校验的去重/豁免状态。

    宿主:``ExecState.plane_node_ledger``(kernel/cw_exec_state.py;经
    :func:`get_node_ledger` 惰性建。载体生命周期 = 一局,无跨局污染)。
    """

    #: 键 = 位面号(1-based);值 = 节点类型序列,**下标 i(0-based)= 该位面第 i+1 轮**
    #: 的类型 token(battle/supply/encounter/reward/boss,与
    #: ``cw_node_reader.NodeSlot.node_type`` / ``CwSimFrame.node_type`` 同词汇表;
    #: None = 该位次未识别占位,合并时被后续非 None 读数覆盖)。
    #: 取值时机:写入端每次整行重读时快照(见各写入端);读端 = 备战帧查
    #: ``seq[round_num - 1]``。
    #: 写入端:①位面详情采集(CwScreenPlaneIntel,进位面时的两源互证产物);
    #: ②投资环境选择完成后重读备战节点行(CwScreenInvestEnv,变异窗后的权威刷新)。
    seq_by_plane: dict[int, list[str | None]] = field(default_factory=dict)

    #: 每序列的写入来源('plane_detail' = 位面详情采集 / 'prep_row' = 备战节点行),
    #: 判读侧区分表值的采集通道用(位面详情=彩色渲染态全量,备战行=含 past 遮挡)。
    seq_source: dict[int, str] = field(default_factory=dict)

    #: 位面 → 位面详情底部明文「敌人难度 N」参考值。**只存参考**——生产难度
    #: 主源 = 备战旗牌两级管线(ADR-0449),本字段供离线对拍/缺口排查。
    difficulty_ref: dict[int, int] = field(default_factory=dict)

    #: 投资环境变异窗豁免截止(time.monotonic 时刻;0.0 = 无窗)。窗内查表与
    #: 逐帧校验的不一致**不落**缺陷台账——环境选择到节点行重读之间节点行
    #: 正在合法变异(用户口述:投资环境是唯一变异源),不一致是预期而非识别错误。
    #: 写入端:CwScreenInvestEnv 确认前开窗、重读刷新台账后关窗(置 0)。
    env_grace_until: float = 0.0

    #: 已落过缺陷的 (plane, round) 键集(逐帧校验每帧都会跑,同一不一致只落一行)。
    defect_seen: set[str] = field(default_factory=set)


def get_node_ledger(session: object) -> PlaneNodeLedger | None:
    """取执行侧载体上的台账,无则惰性建(None session → None,调用方跳过)。

    宿主 = ``ExecState.plane_node_ledger``(产生者 = 画面 op 采集/重读
    写入端,归执行侧载体;读写全经本函数与 :func:`ledger_node_type`,
    消费点禁直摸载体字段)。
    """
    if session is None:
        return None
    ex = exec_state_of(session)
    ledger = ex.plane_node_ledger
    if ledger is None:
        ledger = PlaneNodeLedger()
        ex.plane_node_ledger = ledger
    return ledger


def ledger_node_type(session: object, plane: int | None,
                     round_num: int | None) -> str | None:
    """查表:当前位面第 ``round_num`` 轮的节点类型(1-based round → 0-based 下标)。

    表缺 / 位面轮越界 / 该位次未识别(None)→ None(调用方退逐帧识别链,
    **不猜**)。boss 位在序列里存 'boss' token(写入端按「首领=位面最后节点」
    位置先验回填,与既有 boss 语义门同源)。
    """
    ledger = (None if session is None
              else exec_state_of(session).plane_node_ledger)
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


def iter_deployed_slots(deployed: list[BenchChar | None]):
    """迭代 (槽位下标, 占用角色) 对(滤 None)——deployed_idx 生成端用
    (索引 = 槽位下标,生成期=执行期恒稳,ADR-0392)。"""
    return ((i, d) for i, d in enumerate(deployed) if d is not None)
