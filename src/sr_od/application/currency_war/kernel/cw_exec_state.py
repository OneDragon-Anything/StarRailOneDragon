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
    from sr_od.application.currency_war.kernel.cw_state import BenchChar

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
    """一局的执行层状态(22 具名 = 清册 16 + 账外第二波 6;生命周期/
    防重入语义逐字段自原 session 字段平移,值域与缺省一致——载体每局
    新建即天然清零)。账外收编账本 = ADR-0563「落位裁量」节。

    生命周期分级(迁移核对判据:落点生命周期 ≥ 原生命周期,session.md
    §7.2-3):局级(失败记忆/互斥账/bail 计数/tracked 账/期望账)、跨环
    (发射连败)、节点/visit(防重入/期望覆盖)、环级(defer 门,Director
    环入口清零语义保留在写端)。
    """

    # 腾席链 DeployMove 失败记忆(char_id → 失败计数)。拖拽被拒 → 跳过
    # 重试同目标(拖失败不消费 bench,下轮还在)。局级。
    deploy_fail_counts: dict = field(default_factory=dict)
    # 装备拖拽失败记忆((装备名, 角色名) → 失败计数;dd-015)。连续失败
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
    # 遭遇分支刷新 1 次已用(dd-004;同款跨 handler 语义)。节点级。
    _encounter_refresh_used: bool = False
    # 投资策略逐卡刷新已发射槽集(ADR-0600 §3.3;发射即记不等验效,同款防重入;
    # [索引定义] 坐标系: 策略屏画面槽位下标左→右 0-2,与 PickEvent.
    #             refresh_slots 同源;取值时机: 执行期,发射点击即 add)。
    # 复位 = visit 起点单点(CwScreenInvestStrategy 实例首帧入口锚验通过后
    # clear——同 visit 重入不清保防重入,跨 visit 新实例必清防陈旧集泄入)。
    # 「可否再刷」权威判定 = 逐卡计数现读(cw_node_obs reader),本集唯一
    # 职责 = 同 visit 防重入(双保险不同源,观察赢规则照常辖)。
    _invest_refresh_used_slots: set[int] = field(default_factory=set)
    # 奖励球留置计数(环级——Director 每次环入口清零,清零语义在写端;
    # 策略/框架经 DeferSpheres +1;门=2 防空转环)。框架流程侧。
    defer_count: int = 0
    # star 回退停机钩子计数(char → 连续回退次数;连续 2 节点回退 = 真识别
    # 问题 → 停机保画面排查;读回恢复即清零)。执行侧停机钩子载体。
    star_regression_count: dict[str, int] = field(default_factory=dict)
    # BailToOuter 同因计数(局级,环重建不清零——ping-pong 诊断;≥3 记
    # [cw!])。流程侧。
    bail_reason_counts: dict[str, int] = field(default_factory=dict)
    # 执行侧跟踪账(随动更新;双账断言 screen_op.md §2.3(ii))。tracked_
    # bench_chars 形状契约(ADR-0316):买牌后 mutate_bench_deployed 就地
    # pad 成定长 9 槽**含 None**;tracked_deployed 为槽位表。
    tracked_bench_chars: list[BenchChar] = field(default_factory=list)
    tracked_deployed: list[BenchChar] = field(default_factory=list)
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
    # 期望态容器(W971 EXPECTED_STATE FINAL v3.1,P4):尚未被实读覆盖确认
    # 的期望态条目表(path → ExpectedEntry)。写者 = apply_op_effect(两执行
    # 面同源)+ 登记口;读者 = reconcile_expected(覆盖点)+ 遥测快照。
    # None = 未初始化(惰性建,兼容旧回放构造);正式容器由登记口置 dict。
    expected_state: dict[str, object] | None = None
    # 备战单轮最后动作签名(账外收编:备战单轮 op 写,外循环无进展守卫
    # 读;None = 无在途动作签名)。
    last_prep_action_sig: tuple | None = None
    # —— 账外补充·第二波(实施批收尾扫描按 §6.1 收编的执行侧动态属性,
    # 写端 = 画面 op/发射位,原挂 session 属历史宿主错位)——
    # 补给绕行已完成(节点内一次性)。
    _supply_detour_done: bool = False
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

