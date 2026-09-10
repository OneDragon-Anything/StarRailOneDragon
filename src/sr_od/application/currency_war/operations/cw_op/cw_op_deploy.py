# ⚠️ 本文件**拖拽机制已验证**(2026-08-13:中心拖+hold0,推翻 avatar 假设(原 ADR-0100,文件已删,见 ADR-0120);统一走 DragCwChar.drag_char);
# 其余部署逻辑(CV 占用 / SIFT 身份 / cap 门 / off-target 卖)仍待逐画面 review。

"""货币战争 部署 op(备战阶段:bench 角色 → 舞台空槽)。

**部署逻辑(``_deploy_deterministic``,活跃路径)**:CV ``slot_occupied`` 知 bench / 前排 / 后排占用 → 每个
有角色的备战槽按**角色前后台属性**(``Character.position_pref()``,cw_chars 注册表)拖到对应排的空槽(target
阵营先)→ 验「源备战槽空了」=成功。**角色拖拽统一走 ``DragCwChar.drag_char``**(中心拖 + hold_time=0,2026-08-13
实测推翻 avatar 假设(原 ADR-0100,文件已删,见 ADR-0120);avatar 偏移 / 长按全是旧错诊)。off-target deployed 挡 target 上场时,先
``_sell_offtarget_deployed`` 卖 off-target 腾位(卖拖拽同样走 drag_char)。

**槽位坐标**:screen_info「货币战争-备战」(备战栏 9 / 前排 4 / 后排 N),经 ``_row_centers`` 读全部已建模
``{prefix}-N`` area。**后排 N 按 cap 差公式选档**(ADR-0385 口述「后台格数 = 6+(cap−level)」,
``_back_row_centers`` → ``cw_back_layout.select_back_layout`` 单一入口;旧 level 驱动已废),
``_row_centers`` 自动跟上(读全,不硬编码)。
"""
import time
from typing import TYPE_CHECKING, ClassVar

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_chars import get_char
from sr_od.application.currency_war.kernel.cw_exec_state import exec_state_of
from sr_od.application.currency_war.kernel.cw_launch_admission import (
    DEPLOY_FENCE as _DEPLOY_FENCE,
)
from sr_od.application.currency_war.kernel.cw_launch_admission import (
    offtarget_sell_allowed,
    protect_names_of,  # noqa: F401  re-export 兼容(测试/既有消费路径)
)
from sr_od.application.currency_war.kernel.cw_strategy_session import strategy_state_of
from sr_od.application.currency_war.obs.currency_war_char_id import (
    AvatarTemplates,
    load_avatar_templates,
)
from sr_od.application.currency_war.obs.currency_war_cv import slot_occupied
from sr_od.application.currency_war.obs.cw_identity_obs import (
    bench_item_slots,
    read_bench_chars,
    read_deployed_chars,
)
from sr_od.application.currency_war.obs.cw_observation import (
    arbitrate_deployed_count,
    read_deploy_cap_debounced,
    read_deployed_count,
)
from sr_od.application.currency_war.operations.decision_frame_hooks import (
    save_decision_frame,
)
from sr_od.application.currency_war.operations.dev.drag_cw_char import DragCwChar
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )


def record_fuel_filler_held_postbuy(session: 'StrategySession',
                                    held: list[tuple[str, str]]) -> int:
    """出口③闭环分键(N3,17 号稿 §7.2;可离线测)。

    出口③买入的垫件,在后续部署帧被围栏 held 留 bench 时计
    ``fuel_filler_stall_held_postbuy``(strategy_state_of(session).cw4_counters;零静默)。
    held 名单+拒因 = kernel 围栏语义单一源(N2:
    cw_deploy_logic.select_deployments_reasoned)在执行时刻的现读重建,
    本函数只做计数回流,不重建围栏语义(C2 落点声明:不新建策略→op
    反向依赖)。买入登记源 = ``session.cw4_fuel_filler_stall_buys``
    (出口③发射位买入时写入的名集;发射位随两核实门放行后接线,本
    消费口先行闭环)。异常升高 = 预检语义与部署帧态系统性漂移,回炉
    预检时点(不改阈值,查语义)。

    **出口③授权定性(N4 定稿,17 号稿 §7.3,随批写死;发射位 docstring
    与 ADR 禁回退「支配性/无条件/净成本=0」旧措辞)**:出口③ = 「净
    成本 ≤1 金(注册表派生界:Δ息 = ⌊g/10⌋−⌊(g−cost)/10⌋ ∈ {0,1},
    cost ≤5、息帽 5)的有界成本结构改善授权,零自由参数;严格支配
    (净成本=0)仅 Δ息=0 帧(cost 不跨 10 金档)成立」。

    返回计数增量(测试断言用)。
    """
    buys = getattr(strategy_state_of(session), 'cw4_fuel_filler_stall_buys', None)
    # 载体两形态兼容:dict(名→登记轮号,T3 同轮保留批升级)或旧裸 set;
    # 成员判定语义一致(键/元素名集)。
    if not isinstance(buys, (dict, set)) or not buys:
        return 0
    counters = getattr(strategy_state_of(session), 'cw4_counters', None)
    n = 0
    for name, reason in held:
        if name in buys:
            n += 1
            if isinstance(counters, dict):
                counters['fuel_filler_stall_held_postbuy'] = \
                    counters.get('fuel_filler_stall_held_postbuy', 0) + 1
            log.warning('[cw!][deploy] 出口③垫件部署帧被 held(拒因=%s,'
                        'name=%s)→ held_postbuy 闭环分键', reason or '(未知)',
                        name)
    return n


def prune_fuel_filler_deployed(session: 'StrategySession',
                               deployed_names: list[str]) -> int:
    """T3 同轮保留集「部署即销」(生命周期出口①;属性契约级接线,
    同 record_fuel_filler_held_postbuy 的消费形态——op 层经 duck-typed
    属性读集,不 import 策略模块,不建策略→op 反向依赖)。

    登记名上板(主排序循环 / P24 残余补部署)后保护使命完成,从
    ``session.cw4_fuel_filler_stall_buys``(名→登记轮号 dict)移除;
    漏销 = 后续帧误保面。旧 set 载体仅成员摘除(无轮戳,读端轮界兜底
    自会清)。返回销账数(测试断言用)。
    """
    buys = getattr(strategy_state_of(session), 'cw4_fuel_filler_stall_buys', None)
    if not isinstance(buys, (dict, set)) or not buys:
        return 0
    _on_board = set(deployed_names or ())
    hit = [n for n in list(buys) if n in _on_board]
    for n in hit:
        if isinstance(buys, set):
            buys.discard(n)
        else:
            buys.pop(n, None)
    return len(hit)


# ===== 执行侧配方底线门遥测键(ADR-0564;键族前缀 deploy_exec_,与既有
# 键族零交集;全键写入 strategy_state cw4_counters,经局终快照链与 sim
# 轮差分零新增管道自动携带)=====
# - deploy_exec_held_<reason>:每 execute 一次(一 execute 一 RunDeploy,
#   无需帧去重),从 kernel 计划拒因(_held_reasons)逐 distinct reason 计
#   ——计划时拒因,与发射侧 deploy_emit_held_<reason> 同粒度对读;
# - deploy_exec_r288_skip_ctx_open/closed:主拖拽循环门命中与 P24 过滤
#   剔除各计一次,按当前帧豁免武装布尔分桶(M4 漂移显影键)。
DEPLOY_EXEC_HELD_PREFIX: str = 'deploy_exec_held_'
DEPLOY_EXEC_R288_SKIP_CTX_OPEN: str = 'deploy_exec_r288_skip_ctx_open'
DEPLOY_EXEC_R288_SKIP_CTX_CLOSED: str = 'deploy_exec_r288_skip_ctx_closed'


def _bump_r288_skip_counter(session: 'StrategySession',
                            lock_conflict: bool) -> None:
    """r288 门执行侧命中分桶计数(ADR-0564 M4 漂移显影键;best-effort)。

    漂移键成因注:「发射帧豁免开、执行帧关」的唯一成因 = 意向状态机
    自身(武装布尔 locked_line_recipe_floor_conflict 只读
    ist.locked_comp,不读 bench;供给是豁免闭合条件,不是武装位输入)
    ——skip_ctx_open > 0 = 决策⇔执行间隙内意向翻转(清空/换线),归因
    锚指向意向状态机事件流,不指向 bench 供给变化。
    """
    try:
        counters = getattr(strategy_state_of(session), 'cw4_counters', None)
        if isinstance(counters, dict):
            key = (DEPLOY_EXEC_R288_SKIP_CTX_OPEN if lock_conflict
                   else DEPLOY_EXEC_R288_SKIP_CTX_CLOSED)
            counters[key] = counters.get(key, 0) + 1
    except Exception:   # noqa: BLE001  遥测 best-effort,不阻塞部署
        pass

def residual_fill_plan(held: list, front_empty: list, back_empty: list,
                       bench_pos: dict, bench_cid: dict,
                       deployed_cids: set, cap: int | None,
                       deployed_count: int) -> list[tuple[int, str, int]]:
    """P24 残余补部署计划(纯函数,可离线测;dd-016)。

    主排序循环结束后空槽仍存在(cap 未满)且散牌留置(``_held``)非空时,
    对留置散牌生成补部署计划——判据 = P24 残余补部署支配定理:空 cap 槽上
    任意合法单位 ΔEV≥0(「有羁绊的板 > 空槽」;复盘 g_20260902_181254
    修复项 E 的部署层落点)。ADR-0130 散牌留 bench 与配方围栏辖「选谁优先」
    语义,不支配「空槽 vs 空板」。

    返回 ``[(bench_idx, to_row, slot_idx)]``——``slot_idx`` = 对应排行点位列表
    的 0-based 下标(主循环 ``front_empty``/``back_empty`` 同域,执行侧
    ``row_pts[slot_idx]`` 取拖点、``slot_idx+1`` 即物理槽号)。守卫照搬主循环:
    - 同名禁双(5.1.7):``bench_cid[i]`` 已在 ``deployed_cids`` → 跳过
      (游戏拒收同名,局14 藿藿 5 连败实证——dup 是 3合1 素材不是可上阵件);
    - cap 动态:``deployed_count`` + 已计划数达 ``cap`` → 停(cap=None 不设门,
      拖到游戏拒即真值,同主循环 5.1.8 口径);
    - 选排按 ``bench_pos``(position_pref),首选排无空槽 fallback 另一排,
      两排皆满停。
    """
    plan: list[tuple[int, str, int]] = []
    fe = list(front_empty)
    be = list(back_empty)
    for i in held:
        cid = bench_cid.get(i)
        if cid and cid in deployed_cids:
            continue   # 同名禁双(dup 留 bench 待 3合1)
        if cap is not None and cap > 0 and deployed_count + len(plan) >= cap:
            break   # cap 满,动态停(同主循环)
        pref = bench_pos.get(i, 'back')
        row = pref
        slot = next((s for s in (fe if pref == 'front' else be)), None)
        if slot is None:
            row = 'back' if pref == 'front' else 'front'
            slot = next((s for s in (be if pref == 'front' else fe)), None)
            if slot is None:
                break   # 两排皆满
        (fe if row == 'front' else be).remove(slot)
        plan.append((i, row, slot))
    return plan


def assemble_bench_list(bench_occ: list, bench_cid: dict, bench_pos: dict,
                        item_slots_exact: set[int]) -> list:
    """部署装配点(占槽物品修复批 B1 返工:**显式标记形态**,落地审裁决修法一)。

    bench_occ(0-based 像素占用)→ BenchChar 列表;obs 精确档
    (``bench_item_slots`` fuzzy=False)命中的槽位**照常装配**并显式写
    ``is_item_slot=True``——kernel select_deployments 恒拒逻辑由此真实
    激活(kernel 单点裁决,防线不再是死代码)。物品槽 SIFT 不可读 →
    char_id='' faction='?':本标记与 char_id 无关,身份来源 = 排除集
    显式产出,非「空 id 推断」(「照旧上」fail-open 语义不涉本路径)。
    可离线直测(锁 = test_cw_deploy_pseudo_slot 写入端存在性锁)。
    """
    from sr_od.application.currency_war.kernel.cw_state import BenchChar
    out: list = []
    for _bi in bench_occ:
        _cid_b = bench_cid.get(_bi, '')
        _ch_b = get_char(_cid_b) if _cid_b else None
        out.append(BenchChar(
            slot=_bi + 1, char_id=_cid_b,
            faction=(_ch_b.factions[0]
                     if _ch_b is not None and _ch_b.factions else '?'),
            position_pref=bench_pos.get(_bi, 'back'),
            is_item_slot=(_bi + 1) in item_slots_exact))
    return out


def r288_hold_now(main_fac: str, deployed_fac: dict[str, int],
                  on_board_cids: set[str], bench_list: list,
                  lock_conflict: bool) -> bool:
    """op 侧配方底线门适配器(判定单一源 = kernel.recipe_floor_holds,
    ADR-0564;主拖拽循环与 P24 fill 过滤两消费点共用,禁第三判定副本)。

    拖拽逐件落地增量真值(``deployed_fac``/``on_board_cids`` 现值)在
    调用方维护,本适配器只做共享判定 + 供给惰性计算(armed 才算)。

    :param main_fac: 件的主阵营(与 kernel 内 bench_fac 同源口径;
        '' = 未识别,门恒不辖)。
    :param deployed_fac: 运行阵营档现值(入口快照 + 拖拽逐件增量)。
    :param bench_list: 全量 bench(BenchChar 列表;供给谓词遍历用)。
    """
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        recipe_floor_holds as _holds,
    )
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        xianzhou_supply_exists as _supply,
    )
    return _holds(
        main_fac,
        deployed_fac.get('列车同行', 0),
        deployed_fac.get('仙舟', 0),
        lock_conflict,
        _supply(bench_list, on_board_cids) if lock_conflict else False)


def filter_fill_plan_by_floor(fill_plan: list[tuple[int, str, int]],
                              bench_fac: dict[int, str],
                              deployed_fac: dict[str, int],
                              on_board_cids: set[str],
                              bench_list: list,
                              lock_conflict: bool,
                              ) -> list[tuple[int, str, int]]:
    """P24 fill 计划的配方底线门过滤(与主循环同消费 r288_hold_now,
    ADR-0564;纯函数可离线测)。

    kernel 留 bench 的列车件不得经 P24 补部署绕回上板——豁免语境下
    计划层(装配段武装)与执行门层经同一判定函数自动同值,无第二副本。
    """
    return [(fi, row, slot) for (fi, row, slot) in fill_plan
            if not r288_hold_now(bench_fac.get(fi, ''), deployed_fac,
                                 on_board_cids, bench_list, lock_conflict)]


def exclude_system_units(chars: list) -> list:
    """剔除系统单位(ADR-0281 件4):cost==0 的 roster 特殊召唤单位(狸小虎/狸小龙/
    佩佩类)恒最右、**不可拖** —— 重排/换排/卖出等一切拖拽候选一律剔除(拖必失败,
    游戏拒 → 3 次重试白烧;选中态光效还可能假成功)。char_id 未知/不在 roster → 保留
    (未知单位保持旧行为,由识别侧钩子管)。"""
    out = []
    for d in chars:
        ch = get_char(d.char_id) if getattr(d, 'char_id', '') else None
        if ch is not None and ch.cost == 0:
            continue
        out.append(d)
    return out


# offtarget_sell_allowed / protect_names_of 已迁 kernel.cw_launch_admission
# (模块顶 re-export,实现单一源;判据 docstring 随迁,见彼处)。
# fenced_swap_arm_of / swap_arm_deployed_count 已迁 kernel.cw_deploy_logic
# (与 form_progress 消费同址;kernel 谓词 select_swap_plan 需直调本判据,
# 判据驻 operations 桶 = 非法依赖边/第三源,迁移批单一源收口)。本模块
# 顶 re-export,既有消费路径(生产 deploy 卖出臂/锁测试)零迁移。
from sr_od.application.currency_war.kernel.cw_deploy_logic import (  # noqa: E402,I001  re-export 位 = 原函数定义位(消费路径零迁移)
    fenced_swap_arm_of,  # noqa: F401  re-export 兼容
    swap_arm_deployed_count,  # noqa: F401
)


def _note_deployed_count_divergence(ctx: SrContext, screen: MatLike, source: str,
                                    paddle_n: int | None, cv_n: int) -> None:
    """deployed 计数双源分歧/失读退化留证 + 分键(板满门仲裁触发时;best-effort 不抛)。

    两类事件同键计数:
    - 结构性分歧(paddle 与 CV 差 >1,已取低值仲裁);
    - paddle 失读退化帧(``paddle_n=None``,单源 CV 向板满侧行动,申报防静默)。
    证据层(obs_conflicts 原始行)+ 裁决事件层(defect 台账独立分键
    ``DEFECT_KIND_DEPLOYED_COUNT_2SRC``,不一致率按该 kind 计数)。
    """
    try:
        from sr_od.application.currency_war.kernel.cw_observe import (
            obs_conflict,
        )
        if paddle_n is not None:
            obs_conflict(
                'deployed_count_2src',
                {'paddle_x': paddle_n, 'cv_occupied': cv_n},
                'spread>1', screen,
                verdict=('已仲裁-取低值(paddle X=游戏计数器真值 vs CV 占用;'
                         '规则见 cw_observation.arbitrate_deployed_count;'
                         '实机停机局实证 CV 幻影占用合法化 no-op;'
                         '同局 ≥3 次排期修 CV 占用源/后排布局档)'),
                source=source)
        else:
            obs_conflict(
                'deployed_count_2src',
                {'paddle_x': None, 'cv_occupied': cv_n},
                'paddle 失读', screen,
                verdict=('退化申报-paddle 双帧失读,单源 CV 行动(向板满侧;'
                         '仲裁语义失效,重读一帧未救回;频发则排期修 paddle 读链)'),
                source=source)
    except Exception:   # noqa: BLE001  留证 best-effort,不阻塞部署
        pass
    try:
        from sr_od.application.currency_war.telemetry.defects import (
            record_deployed_count_2src_divergence,
        )
        record_deployed_count_2src_divergence(paddle_n, cv_n, source)
    except Exception:   # noqa: BLE001
        pass


class CwOpDeploy(SrOperation):
    """备战阶段:bench 角色 → 舞台空槽(CV 占用 + SIFT 身份 + position_pref 选排;拖拽走 DragCwChar.drag_char)。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-备战'
    STATUS_DEPLOYED: ClassVar[str] = '已部署角色'
    STATUS_NOOP: ClassVar[str] = '无部署可做(计划空,bench为合法稳态)'
    STATUS_NO_BENCH: ClassVar[str] = '备战栏无角色'
    STATUS_NO_SCREEN: ClassVar[str] = '未加载货币战争-备战 screen_info'
    # 失败状态具名常量(ADR-0601 §4;禁散字符串,判读侧可分键)——
    # 消费面 = run_record/_run_composite detail 判读与 prep_no_progress
    # 停机留证归因。命中即「计划-现读失配/执行环境失配」暴露信号。
    STATUS_EVENT_OVERLAY: ClassVar[str] = \
        '事件overlay在场(执行环境失配,重判归分发层)'
    STATUS_BOARD_FULL_MISMATCH: ClassVar[str] = \
        '板满失配(执行位现读 deployed≥cap 而 RunDeploy 已派发)'
    STATUS_PHANTOM_FULL_BOARD: ClassVar[str] = \
        '幻影满板矛盾帧(CV 采样无空槽 ∧ 仲裁值未达 cap)'
    STATUS_LANDED_NONE: ClassVar[str] = \
        '部署未落地(计划非空但 placed=0,失败帧已存证)'
    # T-174 新增(ADR-0610,dd-037 契约:出口状态可区分,判读侧分键):
    # 出口不变量断言失败具名状态(成功出口 DEPLOYED/NOOP 收尾复验 +
    # NO_BENCH 早退点复验「上阵 ≥1 ⇒ 前排≥1」,不过时的 fail 形态;
    # 三出口辖域见 ADR-0610 §2.1)+ 板满失配窄豁免成功具名状态
    # (与 STATUS_DEPLOYED/STATUS_NOOP/各 fail 形态判读侧可分)。
    STATUS_FRONT_INVARIANT_FAIL: ClassVar[str] = \
        '前排空修复失败(出口不变量:上阵≥1⇒前排≥1)'
    STATUS_ROWFIX_RECOVERED: ClassVar[str] = \
        '满板前排空(场内换排修复)'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-部署角色')

    def _row_centers(self, prefix: str) -> list[Point]:
        """从 screen_info 读**全部** ``{prefix}-N`` 区域中心(按 N 升序)。

        数量 = screen_info 已建模数(不硬编码):前排 4 / 备战栏 9 / 后排按
        ``_back_row_centers`` 选档(cap 差公式,ADR-0385;**别假设
        「后排-」只有 6 个**——档前缀由调用方传入)。
        """
        si = self.ctx.screen_loader.get_screen(CwOpDeploy.SCREEN_NAME)
        if si is None:
            return []
        pts: list[tuple[int, Point]] = []
        pfx = f'{prefix}-'
        for a in si.area_list:
            if a.area_name.startswith(pfx) and a.pc_rect is not None:
                try:
                    n = int(a.area_name[len(pfx):])
                except ValueError:
                    continue
                pts.append((n, a.pc_rect.center))
        pts.sort(key=lambda t: t[0])
        return [p for _, p in pts]

    def _session_level(self) -> int | None:
        """session 等级链 → None(无 session)。

        布局选档的 level 源(ADR-0281:后排槽数 level 驱动,cap 与布局无关)。
        **单一源转调**(15 号稿批 C/T-8:与 ``cw_identity_obs._session_level``
        原为同逻辑双拷贝,合一后语义无分叉;authoritative 位传导见
        ``cw_back_layout.resolve_back_slots`` 的 level_trusted 形参)。
        """
        from sr_od.application.currency_war.obs.cw_identity_obs import (
            _session_level as _single_source,
        )
        return _single_source(self.ctx)

    def _level_trusted(self) -> bool | None:
        """level authoritative 位(15 号稿 §3.2①/T-8):单一源 =
        ``cw_identity_obs._level_trusted``(session.last_state.level_readable);
        None = 未声明(布局公式通道维持现行为)。"""
        from sr_od.application.currency_war.obs.cw_identity_obs import (
            _level_trusted as _single_source,
        )
        return _single_source(self.ctx)

    def _back_row_centers(self) -> list[Point]:
        """ADR-0385:后排槽位按 **cap 差公式** 选档(口述「后台格数=6+(cap−level)」)。

        ``select_back_layout`` 单一入口(cap=read_deploy_cap 直读,level=session
        等级链);7 格档未建档保守 8 格超集 + 留证。旧 level≥7→8 格模型
        (ADR-0281)归因错误已废——run 26(lv8 无召唤物局)按 8 格坐标拖
        不存在的 7/8 号格 + 幻影空位把部署卡死在 bench = 崩坏根因①。
        **布局未知态写面**(15 号稿 §3.2④/T-7)→ ``[]``:后排部署跳过
        (单帧与冻结帧同语义——冻结=写类止损,单帧=宁缺勿造;JSONL 留证
        在 resolve 侧)。
        """
        from sr_od.application.currency_war.obs.cw_back_layout import (
            select_back_layout,
        )
        _n, _pfx = select_back_layout(self.ctx, self.last_screenshot,
                                      level=self._session_level(),
                                      level_trusted=self._level_trusted())
        if _n is None:
            log.info('[cw-deploy] 布局未知态 → 后排部署跳过(写类冻结语义,'
                     '§3.2④)')
            return []
        return self._row_centers(_pfx)

    @operation_node(name='部署备战栏角色', is_start_node=True)
    def deploy(self) -> OperationRoundResult:
        si = self.ctx.screen_loader.get_screen(CwOpDeploy.SCREEN_NAME)
        if si is None:
            log.warning('[cw-deploy] 未加载「货币战争-备战」screen_info,跳过部署')
            return self.round_fail(status=CwOpDeploy.STATUS_NO_SCREEN)
        # 窗口防线执行断言(ADR-0601 §3 D1,同 E1 形态):
        # 派发间隙(宿主入口观察 → 本 op 执行)overlay 弹出 = 执行环境失配,
        # 如实 round_fail 交回重判——禁旧 success-skip 把「弃执行」记成成功
        # (闩置位/部署实际没做,吞分发)。「overlay 弹出重判」归分发层
        #(cw_loop 0 系 overlay 分支先于备战链 + 宿主入口 overlay 防线为
        # 第一道);本检查降级为窗口期第二道执行断言,不升 guard_screen
        #(deploy 派发不带回环守卫,test_cw_t163_popup_dispatch 边界申报锁
        # 语义不变)。
        for _scr, _area in (('货币战争-盛会之星', '标识-盛会之星'),
                            ('货币战争-列车同行', '标识-选择伙伴'),
                            ('货币战争-祈愿试炼', '标识-祈愿试炼')):
            if self.round_by_find_area(self.last_screenshot, _scr, _area, crop_first=False).is_success:
                log.warning(f'[cw!][deploy] 事件 overlay({_scr})在 → 执行断言 fail(重判归分发层)')
                return self.round_fail(
                    f'{CwOpDeploy.STATUS_EVENT_OVERLAY}({_scr})')

        bench = self._row_centers('备战栏')
        save_decision_frame(self, 'deploy', self.last_screenshot)   # 识别完成点原始帧留证(部署仲裁基准)
        front = self._row_centers('前排')
        templates = self._get_templates()   # W209:先载模板(布局选档/身份读都要;缓存 ctx)
        # ADR-0385:后排槽位按 **cap 差公式** 选档(select_back_layout 单一
        # 入口,与 read_deployed_chars 同源)——旧 level≥7→8 格模型归因错误
        # (ADR-0281),run 26 lv8 无召唤物局按 8 格坐标拖不存在的 7/8 号格 +
        # 幻影空位(393/1529 段恒无人)假「板未满」→ 白拖重试把部署卡死在 bench。
        back = self._back_row_centers()
        if len(bench) == 0:
            # F1.5 出口不变量第三出口复验(T-174 收口,ADR-0610 §2.1):
            # 「success ⇒ 前排≥1」承诺辖 NO_BENCH 早退——bench 槽未建模
            # (识别退化)而板上有角色、前排空时,旧代码在此以合法稳态
            # 蒙混 success,发射链拿到 success 即出战 → 游戏拒「前台区域
            # 无角色」(与 1-1 冻结同型,从另一未覆盖出口复发)。front 在
            # 上方识别完成点已算出,零重复计算;不过 = 同既有出口断言形态
            # 具名 fail。前排槽也未建模时谓词内放行(识别退化态断言不辖,
            # 见 _front_ok_now)。
            if not self._front_ok_now(front, back):
                log.warning('[cw!] [deploy] NO_BENCH 出口不变量断言失败:'
                            '板上有角色而前排空 → round_fail 交回')
                return self.round_fail(CwOpDeploy.STATUS_FRONT_INVARIANT_FAIL)
            log.info('[cw-deploy] 备战栏无槽坐标,跳过')
            return self.round_success(CwOpDeploy.STATUS_NO_BENCH)

        # deployed-lock(doc gameplay:78)是误判,deployed 可卖(用户实机确认 gold 增加)。
        _match = self.ctx.cw_match
        _board = (_match.session.last_state.board
                  if (_match is not None and _match.session is not None
                      and _match.session.last_state is not None) else None)
        # r120(断层①修复:配方从不成型的执行层根因):deploy 的 target 判定原读
        # strategy_state_of(session).target_comp(终局 comp)——双轨期预囤的框架件(藿藖/卡芙卡=仙舟)
        # 不是终局 comp 的阵营/core → deploy-swap 当 off-target 卖(局35 r7 卡芙卡
        # 被卖 4 次实证)+「target 先」排序不认 → 板面配方永不成型(P1 通关全靠
        # 人口硬扛)。修:双轨期走 decision_target 单一入口(=配方伪 comp),
        # 框架件成为部署一等公民——与买/卖两侧 r72「三侧单一源」对齐(deploy
        # 侧此前是缺口)。
        # swap 面输入装配单一源(kernel.assemble_swap_plan_inputs):发射面
        # (mandate M1″)与执行面(本函数)同函数同参——本侧装配源 =
        # last_state滞后帧 + SIFT 读面(本函数这条链,ADR-0530 装配源契约);
        # target 视图(双轨口径)/fenced 臂/保护域派生全在装配函数内,
        # 禁自写第二份。装配不可得(None)= 按未装配处理(臂关/空保护,
        # 原语义保守侧)。
        from sr_od.application.currency_war.kernel.cw_deploy_logic import (
            assemble_swap_plan_inputs as _aswap,
        )
        _sess = _match.session if _match is not None else None
        _swap_ctx = None
        if _sess is not None:
            _tracked_n = swap_arm_deployed_count(
                _board, getattr(exec_state_of(_sess), 'tracked_deployed', None))
            _swap_ctx = _aswap(
                _sess,
                state=_sess.last_state,
                deployed=[],      # 板满喂入走 tracked 真读口径(上方计数)
                bench=[],
                cap=None,         # 执行侧不消费谓词 cap 门,只取视图/臂态
                deployed_n=_tracked_n,
                front_slots=len(front), back_slots=len(back))
        # —— 换阵卖出臂前提(F1 执行面消费;T-167 发射-执行接缝合拢)——
        # 判定单一源 = kernel cw_deploy_logic 合取支函数族(与发射面 M1″
        # 同一谓词,禁第二份口径;fw_carry 口径收口=含,依据见
        # target_view_char_is)。旧「装配不可得退型第二份目标视图派生」
        # 随之拆除(硬约束,登记 = ADR-0534「修订(T-167)」节:只消费装配 ctx 字段——ctx None ⟺
        # last_state None ⟹ _board None,旧退型派生在此形态本就消费不到)。
        # 快路负判(与旧 _has_offtarget 同式同读数,行为逐位同旧):
        # 板面阵营计数全在视图内 ⇒ 任一注册件羁绊∩视图≠∅ ⇒ 全部被
        # swap_sell_exclusion_reason target_keep ⇒ 合取③必假——这是 ③ 的
        # 必然假形态提前短路(省 bench/deployed 两次 SIFT 读),非第二口径
        # (board OCR 漏读阵营帧的短板与旧门相同,未扩大)。
        _board_all_tgt = bool(
            _board and _swap_ctx is not None and _swap_ctx.target_factions
            and all(f in _swap_ctx.target_factions for f in _board))
        from sr_od.application.currency_war.kernel.cw_deploy_logic import (
            bench_target_count,
            evolution_swap_arm_trigger,
            swap_realizable,
            target_view_present,
        )
        if (target_view_present(_swap_ctx) and not _board_all_tgt
                and templates is not None and _sess is not None):
            # D-10:卖 off-target deployed 给 bench target 腾位(替一次性
            # sell-all;自收敛:板全 target → 快路负判停)。守卫(D-3):
            # bench 有目标视图件才卖(有更好的要换上);无则留 off-target
            # bodies(> 空板)。
            # 合取②:bench 目标视图件计数(kernel 单一源,含 fw_carry
            # 收口)——计数即 1:1 替换上限(与旧 _bench_tgt_n 同语义)。
            _bench_chars = read_bench_chars(self.ctx, self.last_screenshot,
                                            templates)
            # 演进降级换血臂 bench 域分轨重算(ADR-0614):装配喂入 bench=[]
            #(上方装配块注,执行侧装配源 = last_state 滞后帧),本侧域 =
            # SIFT 现读——与逐件判定(swap_sell_exclusion_reason 的
            # bench=/deployed= 覆盖参)及合取②③同域。谓词单一源 =
            # evolution_swap_arm_trigger(发射⇔执行同值,禁分轨态);
            # 域内覆写只影响本卖出臂的资格判定面,装配产物其余字段不动。
            _swap_ctx.evolution_swap_armed = evolution_swap_arm_trigger(
                _swap_ctx.membership, _bench_chars,
                locked=_swap_ctx.locked, fp=_swap_ctx.fp,
                board_full=_swap_ctx.board_full)
            _bench_tgt_n = bench_target_count(_swap_ctx, bench=_bench_chars)
            if _bench_tgt_n > 0:
                # 合取③:板上存在其资格臂下可卖的 off-target 件(逐件
                # 单一判定 = swap_sell_exclusion_reason;SIFT 现读域喂入,
                # 读一次与卖出臂共用,免重读)。
                _dep_read = exclude_system_units(
                    read_deployed_chars(self.ctx, self.last_screenshot,
                                        templates))
                _swap_ok, _swap_why = swap_realizable(
                    _swap_ctx, bench=_bench_chars, deployed=_dep_read)
                if _swap_ok:
                    # 换阵卖出义务臂(板满换阵死锁修复:线成型 fp=1.00 后
                    # W209 熔断仍护旧线 fenced 件——旧线阵营件被保留 →
                    # sold 0/2 → RunDeploy 单签名三环守卫停机)。臂态来源
                    # = 装配 ctx.fenced_on(fp 单一源 form_progress,与发射
                    # 面 M1″ 同装配同值)。三合取谓词全真才进本臂——发射⇔
                    # 执行分轨态被结构性关闭(T-167 F1;无方向幻影部署
                    # run_20260908_210431 的执行侧根除位)。新线 core∪shared
                    # 经 protect_names 继续保护(P41② 禁卖护栏不因换阵解除)。
                    _fenced_arm = bool(_swap_ctx.fenced_on)
                    _protect: frozenset[str] = _swap_ctx.protect_names
                    _arm_prev = getattr(exec_state_of(_match.session), 'cw4_swap_arm_on', None)
                    if _arm_prev is not None and _arm_prev != _fenced_arm:
                        log.info('[cw-deploy] 换阵卖出义务臂状态变化: %s → %s'
                                 '(fp/部署数逐环重评,开合抖动可观测)',
                                 _arm_prev, _fenced_arm)
                    exec_state_of(_match.session).cw4_swap_arm_on = _fenced_arm
                    if _fenced_arm:
                        log.info('[cw-deploy] 换阵卖出义务臂开启:线成型 fp=1.00 ∧ 板满 '
                                 f'∧ bench target={_bench_tgt_n} → off-line 引擎/配方件'
                                 '让位可卖(新线 core∪shared 仍保护)')
                    # m1p 执行侧归因:读发射位 pending(本帧 m1p 换血臂)后即清
                    #(一次消费;缺省 None = 非 m1p 帧,卖出计 regular 键零漂移)
                    _m1p_arm = getattr(strategy_state_of(_sess), 'cw4_m1p_arm_pending', None)
                    strategy_state_of(_sess).cw4_m1p_arm_pending = None
                    _n = self._sell_offtarget_deployed(
                        front, back, set(_swap_ctx.target_factions), templates,
                        max_sell=_bench_tgt_n,
                        target_cores=set(_swap_ctx.target_cores),
                        fenced_offline_sellable=_fenced_arm,
                        protect_names=_protect, swap_ctx=_swap_ctx,
                        bench_chars=_bench_chars, m1p_arm=_m1p_arm,
                        deployed_chars=_dep_read)
                    log.info(f'[cw-deploy] deploy-swap:sell {_n} off-target deployed(留 target,1:1 替换上限={_bench_tgt_n})'
                             f' 腾位; bench target={_bench_tgt_n}/{len(_bench_chars)} → redeploy 集中')
                else:
                    log.info('[cw-deploy] deploy-swap 跳过:板上无其资格臂下可卖'
                             '的 off-target 件(%s;逐件拒因见卖出单一判定,F1 合取③)'
                             '——发射面同谓词本环已弃权,零幻影', _swap_why)
            else:
                log.info('[cw-deploy] deploy-swap 跳过:bench 无目标视图件(留 off-target bodies;'
                         ' 根因=buy 未买 target / economy 未攒金升级;F1 合取②)')
        _placed, _plan_empty, _gate_fail = self._deploy_deterministic(
            bench, front, back, templates)   # D-7:CV 确定性部署(CV 占用 + position_pref 选排)
        if _gate_fail is not None:
            # F2 板满失配窄豁免(T-174,ADR-0610):「仲裁真满板 ∧ 前排 4 槽
            # 全空 ∧ 后排有人(非系统单位)」= 合法的场内换排工作形态——
            # 双源仲裁取低值(paddle=游戏计数器权威)已使「板满」为可信真值,
            # 失配实质 = 发射位谓词违约(0j 无条件派发重部署),不是帧不可信
            #(ADR-0601 §5 辖域修订);此形态执行场内换排修复,让 0j 恢复链
            # 第一次真正可达 r250 场内前排保证。
            if _gate_fail == CwOpDeploy.STATUS_BOARD_FULL_MISMATCH and \
                    self._rowfix_front_empty_recoverable(
                        front, back, templates):
                self._bump_cw4_counter('board_full_front_empty_rowfix')
                log.info('[cw-deploy] 板满失配豁免(board_full_front_empty_'
                         'rowfix):仲裁真满板 ∧ 前排全空 ∧ 后排有人 → '
                         '场内换排修复(恢复需要 ∧ 拖拽可行的恰覆盖形态)')
                try:
                    self._fix_misplaced_rows(front, back, templates)
                except Exception as e:   # noqa: BLE001  修复失败走复验 fail
                    log.debug('[cw-deploy] 豁免路径换排修复失败(不阻塞复验): %s', e)
                # 复验时点 = 修复拖后特效/overlay 稳定后(同收尾整队等待口径;
                # 过 = 新具名成功状态交回,0j 链直接再出战;不过 = 维持原闸
                # fail 语义交回重判,持续无进展由守卫停机留证兜底)。
                time.sleep(2.0)
                if self._front_ok_now(front, back):
                    log.info('[cw-deploy] 板满失配豁免:换排修复后前排 ≥1 ✓')
                    return self.round_success(
                        CwOpDeploy.STATUS_ROWFIX_RECOVERED, wait=1)
                log.warning('[cw!] [deploy] 板满失配豁免:换排修复后前排仍空 '
                            '→ round_fail 交回(修复不可达,守卫兜底)')
                return self.round_fail(_gate_fail)
            # 失配闸命中帧立即 return(ADR-0601 §5;T-174 修订辖域:速报
            # 语义对幻影满板与「满板∧前排有人」形态不变——此帧上的换排纠正
            # = 对坏帧做真实状态变更拖拽放大失配;「板满∧前排空∧后排有人」
            # 的恢复形态已由上方窄豁免承接,ADR-0610)。如实速报 round_fail
            # 交回分发层重判,收敛责任 = cw_loop 环级无进展守卫(同签名计数
            # + 停机留证),op 侧禁自建第二份失败记忆/停出。
            return self.round_fail(_gate_fail)
        self._reconcile_tracking(templates)   # D-12(3.3.2):deploy 后 SIFT 真实身份纠 tracking 漂(观测回路)
        # r241 换排纠正(用户实锤:三月七被兜底强推前排,后续永不被挪回):
        # deploy 只管 bench→场,场内错排(pref=back 在前排/fallback 遗留)无人纠正
        # → 兜底一旦发生就永久错排。此处扫 read_deployed_chars,错排者拖回正排。
        try:
            self._fix_misplaced_rows(front, back, templates)
        except Exception as e:   # noqa: BLE001  纠正失败不阻塞部署
            log.debug('[cw-deploy] 换排纠正失败(不阻塞): %s', e)

        # ⚠️ 拖完整队等待:末次 drag 的羁绊特效/升星 overlay(盛会之星/
        # 圣杯/银狼升级)可能仍在播 → 后续读(heavy state/SIFT/equip)被遮挡污染。
        # 用户口述口径(docs/game/currency_war/research/screen_flow_timing.md
        # #10,2026-09-02):拖动触发羁绊阶段变更时角色头顶徽章动画 ~2s
        #(2026-08-16 口述的 1.5s 是低估;最后一个动作是拖动 → 等满 2s 再识别)。
        time.sleep(2.0)
        log.info('[cw-deploy] 拖完')

        # F1.5 出口不变量断言(T-174,ADR-0610):op 成功出口的承诺 =
        # 「上阵 ≥1 ⇒ 前排 ≥1」,现读时点 = 本 2.0s 整队等待之后(r241/
        # r250 拖后各有 1.2s 特效等待,特效/overlay 中读占用 = 假阴假阳
        # 双向风险)。覆盖全部成功出口:STATUS_DEPLOYED 与 STATUS_NOOP
        # (NOOP = bench 空、板上有人的合法稳态,同样不允许「板有人而
        # 前排空」地成功返回);读法与 0j 恢复链 _front_ok 同源。
        if not self._front_ok_now(front, back):
            log.warning('[cw!] [deploy] 出口不变量断言失败:上阵 ≥1 而前排空 '
                        '(修复失败) → round_fail 交回')
            return self.round_fail(CwOpDeploy.STATUS_FRONT_INVARIANT_FAIL)

        # r132 装备读时机(穿戴侧盲区修复;原以 decisions 行携带为目的,行写入
        # 已随删除波 1 退役,读时机保留——tracking 链是部署决策的活输入):
        # deploy 后此处是**全量读时机**(画面稳定/正对
        # 备战)——读 equipped below icon 并写 exec_state_of(session).tracked_deployed[].equips,
        # 后续决策快照自动携带。best-effort,失败不阻塞。
        try:
            self._snapshot_equips_into_tracking()
        except Exception as e:   # noqa: BLE001  采集失败不影响部署
            log.debug('[cw-deploy] equips 采集失败(不阻塞): %s', e)

        # dd-037 契约硬化:no-op 与真实部署在返回状态上可区分——
        # ① 计划空且 0 落地 = 合法稳态(bench 留置),STATUS_NOOP(非「已部署角色」,
        #    不再把空计划伪装成部署成功);② 计划非空但 placed=0 = 真失败,round_fail
        #    (交框架失败链,不再 ✓ 蒙混);③ placed>0 = 真部署,STATUS_DEPLOYED。
        # ④ 入口失配闸命中(ADR-0601 §3)= 具名失配状态 round_fail,且在闸
        #    返回点**立即 return**(见 _deploy_deterministic 调用后分支)——
        #    先于①②③判定,闸返回恒 placed=0,不会被 NOOP 分支吞掉。
        if _placed == 0:
            if _plan_empty:
                # 文案口径(T-167 连带修正):「发射方同源谓词抑制」
                # 指 F1 换阵可兑现谓词——不可兑现形态(无方向/无 bench
                # 目标件/无可卖 off-target)发射面已弃权,RunDispatch 只会
                # 由真实部署意图(M1′/达标臂)派发,本 no-op 是其合法稳态。
                log.info('[cw-deploy] 无部署可做(计划空,候选全被规则留 bench;'
                         'dd-037:no-op 状态,F1 同源谓词已抑制不可兑现发射)')
                return self.round_success(CwOpDeploy.STATUS_NOOP, wait=1)
            return self.round_fail(CwOpDeploy.STATUS_LANDED_NONE)
        return self.round_success(CwOpDeploy.STATUS_DEPLOYED, wait=1)

    def _fix_misplaced_rows(self, front: list, back: list,
                            templates: AvatarTemplates | None) -> None:
        """r241 场内换排纠正 + r250 场内前排保证(T-174 后置,ADR-0610)。

        r241:pref=back 却在前排(或反之)→ 拖回正排(兜底强推遗留的永久
        错排)。**禁清空前排守卫**:front→back 纠正若会把前排拖空则跳过
        ——出战硬要求前排非空。守卫计数 = **调用内动态维护**(T-174 F1.1):
        初值 = 下方 ``_scr_fix`` 单帧采样的前排占用数,此后每次 front→back
        纠正拖拽完成 −1、back→front 完成 +1,守卫判定一律读该动态计数;
        **禁循环内对静态帧重采样判定**——「前排 2 个 pref=back」形态(真实
        可达:前排保证强转 1 个 + 后排满 fallback 落 1 个,或 comp 覆盖改变
        pref)下静态读法两次移动各自看到计数 2 → 双双放行 → 前排清空 =
        复发 T-174 停机根因且逃过单前角色帧的锁(方案审 F-1,配套锁 L1b)。
        收敛性:守卫只禁清空移动,后排 pref=front 角色先入前排(动态计数
        上升)后,被跳角色下次调用即可归位——两种处理序均 ≤2 次调用收敛;
        全部署集合无 pref=front 角色时 pref=back 角色留前排 = 游戏硬要求。
        r250(用户局实锤「前台区域无角色,无法出战」卡 12min):全部角色在
        后排+前排完全空 → 游戏拒出战。**后置**(T-174 F1.2,ADR-0610):
        r241 循环纠正完所有错排后再补,前排仍空 ∧ 后排有人 → 挪一个后排
        (真 pref=front 优先,否则第一个,系统单位剔除照旧)到前排 1——无论
        空前排来自哪个路径(纠正产生/拖拽失败遗留/卖出臂清前排/外部状态),
        函数出口都满足不变量。后置补位的候选/占用读数 = 函数头 deployed
        读数,依据结构不变量「补位触发 ⟺ r241 未产生任何涉及前排的完成
        移动」(``_front_occ == 0`` ⟹ 初值前排空 ∧ 无 back→front 完成)——
        该分支下函数头读数与终态一致,不漂移(方案 F-3);若未来在补位前
        新增涉及前排的拖拽,须改为补位前单帧重读。"""
        if templates is None:
            return
        _all_deployed = read_deployed_chars(self.ctx, self.screenshot(), templates)
        # ADR-0281 件4:系统单位剔除统一走 exclude_system_units(r250 场内版此前取
        # back_chars[0] 可能选中狸猫 → 拖必失败白烧重试)。
        deployed = exclude_system_units(_all_deployed)
        if not deployed:
            return
        # r241 原逻辑:错排者归位(空槽采样两排共用单帧:逐槽 screenshot 会在
        # 推导内截 ~10-12 次全屏白烧延迟,且各槽判定撕裂自不同帧;与
        # 补部署段 _scr_fill 同款单帧纪律)
        _scr_fix = self.screenshot()
        front_empty = [i for i, c in enumerate(front)
                       if not slot_occupied(_scr_fix, int(c.x), int(c.y))]
        back_empty = [i for i, c in enumerate(back)
                      if not slot_occupied(_scr_fix, int(c.x), int(c.y))]
        moved = 0
        _skip_invariant = 0
        # 禁清空前排守卫计数(T-174 F1.1,ADR-0610):调用内动态维护,见 docstring。
        _front_occ = len(front) - len(front_empty)
        for d in deployed:
            ch = get_char(d.char_id) if d.char_id else None
            if ch is None:
                continue   # 系统单位(cost==0)已在函数头统一剔除(ADR-0281 件4)
            # 登记挂账(T-174,ADR-0610):want = 注册表 position_pref,
            # 不消费 comp char_positions 覆盖(ADR-0139;部署主循环
            # _bench_pos 吃覆盖)——覆盖与注册表冲突的 comp 存在「部署按
            # 覆盖上前排 → 本循环按注册表拖回后排」的口径双源,本批守卫
            # 不改该判定(守卫只禁清空移动),该形态以错排残留面出现,
            # 后续批收口。
            want = ch.position_pref()
            cur = d.position_pref or 'back'
            if want == cur:
                continue    # 排对了
            # 错排:目标排的空槽
            if want == 'front':
                if not front_empty:
                    continue
                ti = front_empty.pop(0)
                dst = front[ti]
                _row_cn = '前'
            else:
                # 后排满先跳过(无槽可拖,与守卫无关)——置于守卫判定之前,
                # 防「前排 1 人 ∧ 后排满」形态把 back-full 跳过误计入守卫
                # 分键的归因噪声(落地审 F-C,行为零差:两路径都不拖)。
                if not back_empty:
                    continue
                # 守卫辖域 = front→back(唯一能减前排占用的移动,ADR-0610):
                # 计数将到 0(本移动完成后前排空)即跳过——出战硬要求前排
                # 非空 > 站位偏好,与 r250 前排保证同一原则。
                if _front_occ <= 1:
                    _skip_invariant += 1
                    log.info(f'[cw-deploy] 换排纠正:{d.char_id} front排{d.slot}'
                             f' → 后排被守卫拦下(禁清空前排:出战硬要求,'
                             f'当前排占用={_front_occ})')
                    continue
                ti = back_empty.pop(0)
                dst = back[ti]
                _row_cn = '后'
            src_row = front if cur == 'front' else back
            if not (1 <= d.slot <= len(src_row)):
                continue
            src = src_row[d.slot - 1]
            if DragCwChar.drag_char(self, src, dst):
                moved += 1
                _front_occ += 1 if want == 'front' else -1
                log.info(f'[cw-deploy] 换排纠正:{d.char_id} {cur}排{d.slot}'
                         f' → {_row_cn}排{ti + 1}(pref={want}) ✓')
                time.sleep(1.2)    # 特效等待(同 drag 后约定)
            else:
                log.info(f'[cw-deploy] 换排纠正:{d.char_id} 拖3次未动,跳过')
                # 槽没占住,回收
                (front_empty if want == 'front' else back_empty).insert(0, ti)
        if _skip_invariant:
            # 守卫拦截分键零静默(T-174,ADR-0610;best-effort,无载体静默跳过)
            self._bump_cw4_counter('rowfix_skip_front_invariant', _skip_invariant)
        # r250 前排保证(场内版,后置;T-174 F1.2,ADR-0610):前排仍空 +
        # 后排有人 → 挪一(出战硬要求 > 站位偏好)。候选/占用读数 =
        # 函数头 deployed 读数(结构不变量见 docstring)。
        if _front_occ == 0 and back and front:
            back_chars = [d for d in deployed
                          if (d.position_pref or 'back') == 'back']
            if back_chars:
                # 优先真 front(pref)在后排的;否则第一个后排
                cand = next(
                    (d for d in back_chars
                     if get_char(d.char_id) is not None
                     and get_char(d.char_id).position_pref() == 'front'),
                    back_chars[0])
                ch = get_char(cand.char_id) if cand.char_id else None
                if ch is not None and 1 <= cand.slot <= len(back):
                    src = back[cand.slot - 1]
                    dst = front[0]
                    if DragCwChar.drag_char(self, src, dst):
                        moved += 1
                        log.info(f'[cw-deploy] 前排保证(场内 r250,后置):'
                                 f'{cand.char_id} 后排{cand.slot}'
                                 f' → 前排1(前排空,出战硬要求) ✓')
                        time.sleep(1.2)   # 特效等待(同 drag 后约定)
        if moved:
            log.info(f'[cw-deploy] 换排纠正完成: {moved} 个角色归位')
            self._reconcile_tracking(templates)   # 换排后 tracking 再纠一次

    def _bump_cw4_counter(self, key: str, n: int = 1) -> None:
        """cw4_counters 分键 best-effort 计数(T-174,ADR-0610)。

        与 _bump_r288_skip_counter 同形态:无 session/无 dict 载体时静默
        跳过(观测面不阻塞执行);键写入 strategy_state.cw4_counters,经
        局终快照链自动携带。
        """
        try:
            _sess = (self.ctx.cw_match.session
                     if (self.ctx.cw_match is not None
                         and self.ctx.cw_match.session is not None) else None)
            _counters = getattr(strategy_state_of(_sess), 'cw4_counters',
                                None) if _sess else None
            if isinstance(_counters, dict):
                _counters[key] = _counters.get(key, 0) + n
        except Exception:   # noqa: BLE001  遥测 best-effort
            pass

    def _front_ok_now(self, front: list, back: list) -> bool:
        """出口不变量现读(T-174 F1.5,ADR-0610):上阵 ≥1 时前排占用 ≥1。

        CV 占用现读(front+back 全槽扫描,fresh 帧);与 0j 恢复链
        ``_front_ok`` 同源(currency_war_cv.slot_occupied)。返回 False =
        「板有人而前排空」(不变量破);整板空 = 不变量前提不适用(合法
        稳态放行);前排槽未建模 = 识别退化态,断言不辖(交下游防线)。
        已知残留:DD-030 幻影占用族可使「真板空」帧误判有人 → 假
        round_fail(有界:环重试 → 守卫兜底;双源仲裁缓解挂账 ADR-0610)。
        """
        if not front:
            return True   # 前排槽未建模(识别退化态)不辖
        scr = self.screenshot()
        front_occ = any(slot_occupied(scr, int(p.x), int(p.y)) for p in front)
        if front_occ:
            return True
        return not any(slot_occupied(scr, int(p.x), int(p.y)) for p in back)

    def _rowfix_front_empty_recoverable(self, front: list, back: list,
                                        templates: AvatarTemplates | None) -> bool:
        """F2 窄豁免条件现读(T-174,ADR-0610):前排 4 槽全空 ∧ 后排至少
        1 个非系统单位(拖拽修复可行)。

        三条件合取的另外一支在调用点:门值 = STATUS_BOARD_FULL_MISMATCH
        (闸内双源仲裁取低值已使「板满」为可信真值,ADR-0601 §5 修订辖域;
        幻影满板门值永不豁免——负锁 L4b)。fresh 帧现读,不消费闸命中帧。
        身份读不可得(templates=None)→ False:无法确证修复可行就不豁免,
        诚实 round_fail(守卫停机留证是正确出口)。
        """
        if templates is None or not front:
            return False
        scr = self.screenshot()
        if any(slot_occupied(scr, int(p.x), int(p.y)) for p in front):
            return False   # 前排有人 → 豁免窄度红线:维持原闸 fail 语义
        deployed = exclude_system_units(
            read_deployed_chars(self.ctx, scr, templates))
        return any((d.position_pref or 'back') == 'back' for d in deployed)

    def _snapshot_equips_into_tracking(self) -> None:
        """读当前画面已上阵装备 → 回写 exec_state_of(session).tracked_deployed 的 equips 字段。"""
        _match = self.ctx.cw_match
        if _match is None or _match.session is None:
            return
        from sr_od.application.currency_war.kernel.cw_bench_equips import (
            EQUIPS_CONSISTENCY_ERRORS,
            assert_equips_consistency,
        )
        from sr_od.application.currency_war.obs.cw_equipment import (
            ensure_equip_tm_templates,
        )
        from sr_od.application.currency_war.obs.cw_identity_obs import read_row_equipped
        equip_grays = ensure_equip_tm_templates(self.ctx)
        if equip_grays is None:
            return
        scr = self.last_screenshot
        front_eq = read_row_equipped(self.ctx, scr, equip_grays, '前排', 4)
        # W209b 补漏(编排者验收发现):装备快照原固定「后排」6 格,从不随布局
        # 选档——真 8 格局(召唤物)漏读扩展带 7/8 且槽位错位一格(c.slot 来自
        # 8 档编号 vs 「后排」rect = 8 档 2-7 位)→ equips 挂错人。改同源
        # select_back_layout(双通道,ADR-0385)。
        from sr_od.application.currency_war.obs.cw_back_layout import (
            select_back_layout as _sel_bl,
        )
        _bk_n, _bk_pfx = _sel_bl(self.ctx, scr, level=self._session_level(),
                                 level_trusted=self._level_trusted())
        if _bk_n is None:
            # 布局未知态写类冻结(§3.2④/T-7):tracked 后排 equips 写入停
            # (前排快照不受影响;错向档读数写入 = 毒化 tracked 底座)。
            log.info('[cw-deploy] 布局未知态 → tracked 后排 equips 写入冻结')
            back_eq = None
        else:
            back_eq = read_row_equipped(self.ctx, scr, equip_grays, _bk_pfx, _bk_n)
        tracked = _match.exec_state.tracked_deployed
        _n = 0
        for c in tracked:
            slot = getattr(c, 'slot', None)
            if slot is None:
                continue
            if c.position_pref != 'front' and back_eq is None:
                continue   # 冻结面:后排写入停(§3.2④)
            eq = (front_eq if c.position_pref == 'front' else back_eq).get(slot, [])
            if eq:
                # C6 装备对账(契约 2,W38):deployed 侧画面可读 → 与账面交叉校验,
                # 不一致告警留痕(禁静默用账;哨兵停机留证归后续实机运维批),
                # 然后画面真值覆盖(deployed 侧画面 = truth,tracking 是 bench 侧单一源)。
                try:
                    assert_equips_consistency(c, eq, source='deploy_bench.snapshot')
                except EQUIPS_CONSISTENCY_ERRORS as e:   # R4-2:元组单一源(上游演化只改那处)
                    log.warning('[cw!] %s(账本漂移,画面真值覆盖)', e)
                c.equips = list(eq)
                _n += len(eq)
        if _n:
            log.info('[cw-deploy] equips 采集:tracked %d 件写入(决策快照将携带)', _n)

    def _deploy_deterministic(self, bench: list[Point], front: list[Point], back: list[Point],
                              templates: AvatarTemplates | None) -> tuple[int, bool, str | None]:
        """D-7 确定性部署:CV 知占用 → 每个有角色的备战槽按**角色前后台属性**(position_pref)拖到对应排的
        空槽(target 阵营先)→ CV 验「源备战槽空了」=成功。

        返回 ``(placed, plan_empty, gate_fail)``(dd-037 契约 + ADR-0601 §4 扩展):
        placed = 落点验证过的实际上阵数;plan_empty = 主计划为空(kernel 选人
        无上场候选)——调用方据此区分 no-op(合法稳态)与「计划非空却 0 落地」
        (真失败),两者返回状态可区分;gate_fail = 入口失配闸具名状态
        (D2:板满失配/幻影满板,非 None = 调用方须 round_fail 上报),
        None = 未命中失配闸。

        **5.1.6(2026-08-12,live 观察 2)**:按 ``Character.position_pref()``(cw_chars 注册表)选排 ——
        前台角色→前排空槽、后台/flex 角色→后排空槽;对应排满才 fallback 另一排(避免不上场)。
        替旧「targets 一锅 pop(0) 前排优先」(不看角色属性 → 前台角色被拖后排 / 后台角色被拖前排 → 放错排
        无效果)。flex 默认 back(``position_pref`` 语义,后排槽多)。

        D-8 接身份:排序(target 先)+ position_pref(选排)都用 SIFT ``read_bench_chars`` 读 bench 身份 →
        ``get_char`` 查注册表。SIFT 未命中的 bench 角色 → 当 rest(pref 默认 back,照常 deploy,只不优先)。
        D-10:fresh screenshot(``self.screenshot()``)看 post-sell 状态(_sell_offtarget_deployed 腾出的空槽)。
        CV 验源槽空同时覆盖 place + swap(swap 时被换下角色回 bench,源槽仍空)。
        """
        scr = self.screenshot()
        _match = self.ctx.cw_match
        _sess = (_match.session if (_match is not None and _match.session is not None) else None)
        # 5.1.8 deploy_cap(live 发现 drag 白拖根因 = cap 满,2026-08-12):deployed(CV front_occ+back_occ 实测阵上)
        # ≥ level(cap,D-19「cap=level」)→ 板满,bench 角色上不了 → 不拖(留 bench;防 drag 被拒源槽占 placed=0 白拖
        # + 用户 live 观察 bug4「未考虑上限」)。⚠️ CV 占用可幻影虚高(实机停机局实证:备战环
        # CV 幻影占用合法化 no-op → 同签名零推进,DD-030 停机)——deployed 计数现走双源仲裁
        #(见下方 arbitrate_deployed_count 注),不再直采 CV。
        # cap 真值优先 read_deploy_cap(OCR X/Y 的 Y,含宝钻/诅咒加成);读不到 fallback level(D-19 cap≈level)。
        # ⚠️ level≠cap 场景(诅咒-1 / 宝钻+1):用 level 会误判 cap 未满 → 白拖(D-53 注 level=cap 无加成,但加成时偏)。
        # r60(2026-08-18 用户实锤「明明随便上填空位也可以」):cap 低读 = 部署阻塞(lv5 真值被
        # paddle 失读/last_state 毒化成 3 → 板满假判 → 2 人留 bench,11:56:24 实锤)。cap 误差
        # 两个方向不对称:低读阻塞上阵(战力真空,贵)/高读多拖一次被游戏拒(源槽弹回,重试停,便宜)。
        # r64 review P1 修(语义分层):**paddle 直读 = 权威**(屏幕 X/Y 显示的就是真 cap,含
        # 诅咒-1/宝钻+1 —— 读到时直用,max 会把诅咒降级吃掉);**失读才 max 兜底**(单调链
        # last_level_obs[_resolve_level 维护已防毒化] vs last_state.level 取大 —— 低读阻塞
        # 上阵的代价 > 高读白拖一次,不对称取舍)。
        # ADR-0395:cap 直读同时驱 板满门 + 布局公式通道(select_back_layout
        # 复用 _cap)=「读数→行动」高危点——瞬态低读(cap<level 域外,过渡帧旧值
        # 残影 run 27 型)→ 板满假判 → 留 bench 战力真空(r60 实证,贵方向);
        # 改走域防抖读(ADR-0286:域外重读一帧,仍域外 → None → 走下方失读
        # max 兜底链,不在单帧瞬态值上行动;高读白拖一次被游戏拒 = 便宜方向不变)。
        _cap = read_deploy_cap_debounced(self.ctx, scr, self._session_level())
        # ADR-0385:入场帧(收起商店 1s 过渡)选档可能按旧帧退基线;此处
        # fresh 帧按 **cap 差公式** 重建 back 布局(select_back_layout 单一入口,
        # cap 复用上面现读值——口述「后台格数=6+(cap−level)」)。
        # ⚠️ 重绑**必须先于**下方占用采样(布局档对账批):后排槽坐标按所选档
        # 变化,旧序「back_empty 按旧档采样 → len(back) 按新档」混两套坐标系,
        # CV 占用计数系统性偏移 = 后排幻影占用的候选机制。全部占用读数统一在
        # **最终布局**上采。
        from sr_od.application.currency_war.obs.cw_back_layout import (
            select_back_layout as _sel_bl,
        )
        _n2, _pfx2 = _sel_bl(self.ctx, scr, level=self._session_level(),
                             cap=_cap, level_trusted=self._level_trusted())
        if _pfx2:
            back = self._row_centers(_pfx2)
        if _cap is None:
            _lv_chain = (getattr(_sess, 'last_level_obs', 0)
                         if _sess is not None else 0) or 0
            _lv_state = (_sess.last_state.level
                         if (_sess is not None and _sess.last_state is not None) else None)
            _cap_candidates = [c for c in (_lv_chain, _lv_state) if c is not None and c > 0]
            if _cap_candidates:
                _cap = max(_cap_candidates)
                log.info(f'[cw-deploy] cap paddle 失读 → 单调链={_lv_chain} state={_lv_state}'
                         f' 取 max={_cap}(低读阻塞上阵 > 高读白拖,r60/r64)')
            else:
                log.info('[cw-deploy] cap 全源失读 → None(不设板满门,拖到游戏拒即真值)')
        # 占槽物品识别(部署伪槽修复批 ①;B1 返工后为**标记形态**:物品槽
        # 照常进装配,由装配点显式写 is_item_slot=True → kernel 恒拒,
        # 单点裁决)。消费 obs 单一源精确档(bench_item_slots fuzzy=False,
        # 泛扫描模糊判据**不给**部署面——误排真角色=战力真空,贵方向;
        # 方案 A1)。返回 1-based,bench_occ 为 0-based,装配点显式 +1 对齐。
        # 读不到(无 screen_info 的退化 ctx,离线/测试)→ 标记集空 = 退回
        # 旧行为(缺省开,不阻塞部署)。
        try:
            _item_slots_exact: set[int] = bench_item_slots(
                self.ctx, scr, fuzzy=False)
        except Exception:   # noqa: BLE001  识别退化 = 旧行为(不拦部署)
            _item_slots_exact = set()
            log.warning('[cw!] [deploy] 占槽物品排除集读取失败 → 退纯像素'
                        '占用/零标记(screen_info 缺失退化态,降级可见)')
        if _item_slots_exact:
            log.info(f'[cw-deploy] 占槽物品识别(精确档):slots={sorted(_item_slots_exact)}')
        bench_occ = [i for i, c in enumerate(bench) if slot_occupied(scr, int(c.x), int(c.y))]
        front_empty = [i for i, c in enumerate(front) if not slot_occupied(scr, int(c.x), int(c.y))]
        back_empty = [i for i, c in enumerate(back) if not slot_occupied(scr, int(c.x), int(c.y))]
        if not bench_occ:
            log.info(f'[cw-deploy] deterministic: bench_occ={bench_occ} → 无 bench 角色')
            # 契约补全(ADR-0601 §4):bench 空 = 合法稳态 NOOP 的输入形态,
            # 返回须满足 3 元组签名 (placed, plan_empty, gate_fail)——
            # (0, True, None) = 0 落地/计划空/未命中失配闸;少返第三元会
            # 在调用点三元解包处 ValueError(三审 C1 实证,行为锁堵漏)。
            return 0, True, None
        # deployed 计数双源仲裁(观测仲裁批):CV 占用(front+back 实测)
        # 只是像素推断源,「板满」是高危读→行动点(本函数内**全部**板满早退
        # 都必须经仲裁值,含下方两道)。仲裁规则与代价不对称依据 =
        # ``cw_observation.arbitrate_deployed_count``(取低值 fail-closed
        # 向部署侧;分歧告警带沿用 spread>1 留证判据,不拍新阈值)。
        # paddle 单帧漏读在案(stylized 数字 det 间歇漏,同 gold 读链救援先例)
        # → 重截一帧重读一次;仍失读 = 退化帧(CV 单源,向板满侧行动),
        # 不静默:留证分键(见 note helper)。
        _deployed_cv = (len(front) - len(front_empty)) + (len(back) - len(back_empty))
        _paddle_x = read_deployed_count(self.ctx, scr)
        if _paddle_x is None:
            try:
                _paddle_x = read_deployed_count(self.ctx, self.screenshot())
            except Exception:   # noqa: BLE001  重截失败按失读处理
                _paddle_x = None
        _deployed, _count_divergent = arbitrate_deployed_count(
            _paddle_x, _deployed_cv)
        if _count_divergent and _paddle_x is not None:
            _note_deployed_count_divergence(
                self.ctx, scr, 'deploy_cap_gate', _paddle_x, _deployed_cv)
        elif _paddle_x is None:
            # paddle 失读退化帧:仲裁语义失效(单源=CV,向板满侧行动),
            # 显式申报防静默(P3;重读一次后仍失读才到此)。
            log.info('[cw-deploy] deployed paddle 双帧失读 → 退化单源 CV 计数'
                     f'({_deployed_cv});板满门按 CV 行动(向板满侧 fail,'
                     '留证分键申报)')
            _note_deployed_count_divergence(
                self.ctx, scr, 'deploy_cap_gate_paddle_missing', None, _deployed_cv)
        if _cap is not None and _cap > 0:
            if _deployed >= _cap:
                # 计划-现读失配执行断言(ADR-0601 §3 D2 三分之一):发射位谓词
                # (_deployable 含 cap 围栏,kernel 单源)正常时板满帧不会派
                # RunDeploy——命中即发射面读与执行面读失配(谓词 bug 或派发
                # 窗口期板面变化),如实 fail 交回重判;禁旧 (0, True) 伪装
                # plan_empty 合法稳态把失配吞成 NOOP。批内动态停(拖拽循环内
                # _cap_stopped 截断)是另一类:执行细节机械安全边界,保留
                # 不动(C4 裁决的区分判据:截断剩余 ≠ 跳过整批)。
                log.warning(f'[cw!][deploy] 板满失配:deployed={_deployed}(双源仲裁) '
                            f'≥ cap={_cap} 而 RunDeploy 已派发 → 执行断言 fail'
                            f'(front空={len(front_empty)} back空={len(back_empty)})')
                return 0, False, CwOpDeploy.STATUS_BOARD_FULL_MISMATCH
        if not front_empty and not back_empty:
            # 幻影满板矛盾帧执行断言(ADR-0601 §3 D2 三分之二;P1 闭死升级):
            # CV 采样占满全部槽但仲裁值未达 cap(或 cap 失读)= 采样结构性
            # 失真——「派发认为可部署」与「现读无空槽」矛盾,如实 fail 暴露
            #(分歧留证已由上方仲裁分支落账),禁旧 (0, True) 伪装合法稳态。
            log.warning(f'[cw!][deploy] 幻影满板矛盾帧:CV 采样无空槽但仲裁值 '
                        f'deployed={_deployed}(cv={_deployed_cv})未达板满 → '
                        f'执行断言 fail(矛盾帧交回重观察)')
            return 0, False, CwOpDeploy.STATUS_PHANTOM_FULL_BOARD
        # r70 过渡框架并进 deploy target 集(双轨期):框架牌 = 当前阶段的「临时 target」,
        # 否则保血资产(三月七/藿藿/饮月)被判 off-target 散牌留 bench → 白板挨打
        # (r70 审计「买了→不上场→被卖」三侧断裂的 deploy 侧)。定型后 framework 已清空,
        # 集合退化为原 target-only 行为。装配单一源 = kernel.deploy_target_sets
        # (发射侧 mandate._deployable 同款消费,dd-037 禁两侧各写一份)。
        from sr_od.application.currency_war.kernel.cw_deploy_logic import (
            deploy_target_sets as _deploy_target_sets,
        )
        _tgt, _fw_carry = _deploy_target_sets(
            (strategy_state_of(_sess).target_comp if _sess is not None else None),
            (getattr(strategy_state_of(_sess), 'transition_framework', '')
             if _sess is not None else ''))
        # D-8:bench 身份走 SIFT(read_bench_chars,plaza 官方立绘库可靠)→ 真实羁绊(target 排序)+ position_pref
        # (5.1.6 选排)。两者都从 get_char 注册表查(SIFT 只给 char_id,BenchChar.position_pref 默认 "back"
        # 不可信 → 必查注册表)。无 target 也要读身份(选排需要),不再 _tgt gate。
        _bench_id: dict[int, set[str]] = {}   # bench_idx(0-based) → 该角色羁绊集合
        _bench_pos: dict[int, str] = {}       # bench_idx(0-based) → "front"/"back"(角色 position_pref)
        _bench_cid: dict[int, str] = {}       # bench_idx(0-based) → char_id(5.1.7 去重)
        if templates is not None:
            for bc in read_bench_chars(self.ctx, scr, templates):
                ch = get_char(bc.char_id) if bc.char_id else None
                if ch is not None and 1 <= bc.slot <= len(bench):
                    _bench_id[bc.slot - 1] = set(ch.factions) | set(ch.flows)
                    _bench_pos[bc.slot - 1] = ch.position_pref()
                    _bench_cid[bc.slot - 1] = bc.char_id
        # ADR-0139:comp 特定站位覆盖命途默认(爻光必后台/万敌独前排——攻略实证,同 _pick_deploy_row 语义)
        if (_sess is not None and strategy_state_of(_sess).target_comp is not None
                and strategy_state_of(_sess).target_comp.char_positions):
            for bi2, cid2 in list(_bench_cid.items()):
                if cid2 in strategy_state_of(_sess).target_comp.char_positions:
                    _bench_pos[bi2] = strategy_state_of(_sess).target_comp.char_positions[cid2]
            log.info(f'[cw-deploy] bench 身份(SIFT):{ {i: sorted(b) for i, b in _bench_id.items()} }'
                     f' pos={_bench_pos} tgt={sorted(_tgt)}')
        # 5.1.7 同角色去重(live 观察 3,场上同角色只 1):read_deployed_chars → deployed char_id;
        # bench 角色已 deployed → deploy 循环跳过(避免场上重复角色 + 买/部署同名)。
        _deployed_cids: set[str] = set()
        _deployed_fac: dict[str, int] = {}   # r288 配方底线仲裁用
        if templates is not None:
            _deployed_cids = {bc.char_id for bc in read_deployed_chars(self.ctx, scr, templates) if bc.char_id}
            if _deployed_cids:
                log.info(f'[cw-deploy] deployed 身份(5.1.7 去重):{sorted(_deployed_cids)}')
            # 已上场角色的阵营档(多阵营角色每阵营 +1,同板面 OCR 口径)
            # r361b(review B 修:口径统一):补 flows——补档键按
            # factions+flows 全羁绊判档。计数单一源 =
            # kernel.deployed_bond_counts(与发射侧 mandate._deployable
            # 同款装配)。
            from sr_od.application.currency_war.kernel.cw_deploy_logic import (
                deployed_bond_counts as _deployed_bond_counts,
            )
            _deployed_fac = _deployed_bond_counts(_deployed_cids)
        # dd-037:选人/围栏/排序单一源 = kernel.select_deployments。此前 op 内
        # 复写一份 tgt/rest 切分 + 散牌围栏 + 点火排序,与
        # kernel 纯函数双源——run 20260904_28xx 局11 停机形态:配方底线规则只在
        # 执行方 drag 循环里,发射方(决策核)不知道 → 空计划 RunDeploy 被报
        # ✓「已部署角色」→ 同签名零推进环(G3 守卫停机)。收敛后本 op 只做
        # 输入装配(SIFT 现读身份)+ 拖拽执行;拖拽循环内的动态守卫(fresh
        # 复查/动态 cap/逐件 r288 仲裁/落点验证)保留作运行时防线。
        _cores = (strategy_state_of(_sess).target_comp.core_chars
                  if (_sess is not None and strategy_state_of(_sess).target_comp is not None) else None) or []
        _board_in = dict(_sess.last_state.board
                         if (_sess is not None and _sess.last_state is not None)
                         else {}) or {}
        try:
            from sr_od.application.currency_war.kernel.cw_intention import (
                locked_faction_scope as _lfs,
            )
            _locked_fac = _lfs(getattr(strategy_state_of(_sess), 'v3_intention', None)) \
                or frozenset()
        except Exception:   # noqa: BLE001 —— 围栏兜底 best-effort
            _locked_fac = frozenset()
        # 锁定线语境豁免武装布尔(配方底线门,ADR-0564):同 _locked_fac
        # 兜底形态(fail-closed 关豁免)。装配段/主循环/P24 三消费点经
        # 本布尔同帧同值——装配段漏武装 = kernel 计划层仍 held 列车件
        # (order 不含)→ 豁免在执行侧静默失效,恰回「零痕迹」形态。
        try:
            from sr_od.application.currency_war.kernel.cw_intention import (
                locked_line_recipe_floor_conflict as _rf_conflict,
            )
            _rf_lock_conflict = _rf_conflict(
                getattr(strategy_state_of(_sess), 'v3_intention', None))
        except Exception:   # noqa: BLE001  同 _locked_fac 兜底:fail-closed
            _rf_lock_conflict = False
        from sr_od.application.currency_war.kernel.cw_deploy_logic import (
            select_deployments_reasoned as _sel_dep,
        )
        # 拖拽循环内 r288 动态仲裁仍按主阵营判件(与 kernel 内 bench_fac 同源口径)
        _bench_fac: dict[int, str] = {}
        for _bi2, _cid2 in _bench_cid.items():
            _c2 = get_char(_cid2) if _cid2 else None
            if _c2 is not None and _c2.factions:
                _bench_fac[_bi2] = _c2.factions[0]
        # 装配单一源(B1 返工):物品槽照常进装配并显式 is_item_slot=True,
        # kernel 恒拒由此真实激活(写入端存在性锁 = test_cw_deploy_pseudo_slot)。
        _bench_list: list = assemble_bench_list(
            bench_occ, _bench_cid, _bench_pos, _item_slots_exact)
        _up_rel, _held_rel, _held_reasons = _sel_dep(
            _bench_list, deployed_cids=set(_deployed_cids),
            deployed_fac=dict(_deployed_fac), board=_board_in,
            cap=(_cap if _cap is not None and _cap > 0 else 10 ** 6),
            target_factions=_tgt, target_cores=set(_cores),
            fw_carry=_fw_carry, locked_factions=_locked_fac,
            recipe_floor_lock_exempt=_rf_lock_conflict)
        order = [bench_occ[_k] for _k in _up_rel]
        _held = [bench_occ[_k] for _k in _held_rel]
        if _held:
            log.info(f'[cw-deploy] 留 bench(kernel 围栏/底线/去重/cap,dd-037):'
                     f'slots={[bench_occ[_k] + 1 for _k in _held_rel]}')
        # N3 闭环分键(17 号稿 §7.2):出口③买入的垫件在部署帧被围栏 held
        # 留 bench 时计数——消费 kernel 单一源拒因(N2),执行侧现读重建
        # 回流遥测(C2 落点声明,不新建策略→op 反向依赖)。买入登记源 =
        # session.cw4_fuel_filler_stall_buys(出口③发射位买入时写入的名集;
        # 发射位随两核实门放行后接线,本消费口先行闭环)。
        _ff_buys = getattr(strategy_state_of(_sess), 'cw4_fuel_filler_stall_buys', None)
        if isinstance(_ff_buys, (dict, set)) and _ff_buys:
            record_fuel_filler_held_postbuy(
                _sess,
                [(_bench_list[_k].char_id or '', _held_reasons.get(_k, ''))
                 for _k in _held_rel])
        # 执行侧计划拒因分键(ADR-0564;每 execute 一次,无需帧去重):
        # kernel 计划时拒因逐 distinct reason 计,与发射侧
        # deploy_emit_held_<reason> 同粒度对读(计划非空帧的拒因面;
        # best-effort,无状态容器时静默跳过)。
        _exec_counters = getattr(strategy_state_of(_sess), 'cw4_counters',
                                 None) if _sess is not None else None
        if isinstance(_exec_counters, dict):
            for _er in set(_held_reasons.values()):
                _ek = DEPLOY_EXEC_HELD_PREFIX + _er
                _exec_counters[_ek] = _exec_counters.get(_ek, 0) + 1
        # P86 乙臂行权显影(攻击 r1 发现1 面③;正本 §4.3-1):乙臂获取
        # 名集读端消费——本部署轮被围栏放行上场的名 ∈ 获取名集时按笔计
        # deployed_from_hub(行权走通用凑档路径的观测面,非新增授权;
        # 鸭子读属性契约同 cw4_fuel_filler_stall_buys 先例,禁改名破契约;
        # 策略侧读口 = sell_gate.hub_acquired_names_of 同一载体;
        # best-effort,无载体静默跳过)。
        if _sess is not None and isinstance(_exec_counters, dict):
            _hub_held = getattr(strategy_state_of(_sess),
                                'cw4_hub_acquired_names', None)
            if isinstance(_hub_held, list) and _hub_held:
                _dep_hub = {(_bench_list[_k].char_id or '')
                            for _k in _up_rel} & set(_hub_held)
                for _hn in sorted(_dep_hub):
                    _exec_counters['deployed_from_hub'] = \
                        _exec_counters.get('deployed_from_hub', 0) + 1
        log.info(f'[cw-deploy] deterministic: bench_occ={bench_occ} 上场序={order}'
                 f' front空={len(front_empty)} back空={len(back_empty)}')
        placed = 0
        _skipped = 0   # 合法跳过(去重/配方底线/源槽已空)≠ 上阵失败
        _cap_stopped = False
        # P4R 返工(1-1 事故):主循环原为 `for bi in order`,而「前排保证
        # (重排)」分支在迭代中 order.remove/insert 后 continue——for 迭代器
        # 语义是**前进**,被移到已过下标的元素永远不会被 yield(零日志、
        # 零 skipped、分母不变 = 「placed=2/6(跳过0) 且后续件无尝试日志」
        # 的静默跳过形态)。改下标显式推进 + 重排后**原地重处理当前位**
        #(原注释假设的重处理语义只有下标循环才成立)。
        _pending = list(order)
        _oi = 0
        while _oi < len(_pending):
            bi = _pending[_oi]
            _oi += 1
            # live 2026-08-15(match5 根因终定位):起始 cap 检查只做一次 —— 循环中途 deployed 达 cap 后
            # 游戏拒收后续 drag(单位弹回 = 「源槽未变」连环假失败 + 每槽 3×2s 白烧)。每槽动态复查。
            if _cap is not None and _cap > 0:
                # 动态复查同走仲裁值(入口双源仲裁的 _deployed + 已验证
                # 落地数;不再用 CV 幻影占用重算,依据同入口仲裁注)。
                _deployed_now = _deployed + placed
                if _deployed_now >= _cap:
                    log.info(f'[cw-deploy] 板满 cap(动态停):deployed={_deployed_now} ≥ cap={_cap}'
                             f' placed={placed} → 剩余 bench 角色留 bench(不白拖)')
                    _cap_stopped = True
                    break
            # ⚖️ 同名在场禁双(5.1.7,全局不变量;原语义档 kernel/cw_deploy_seat 已随
            # 死码批删除——不变量存活载体=board_unique_key/select_deployments
            # (cw_deploy_logic),执行层此处直查 char_id 集合为同源投影)。
            _cid = _bench_cid.get(bi)
            if _cid and _cid in _deployed_cids:
                log.info(f'[cw-deploy] 去重(5.1.7,不变量存活载体 board_unique_key 同源):'
                         f'bench槽{bi+1}({_cid}) 已 deployed,跳过')
                _skipped += 1
                continue
            # r288 配方底线门(局23/24 连续实锤:锁 jizi 线列车 3 档吃板
            # 挤掉仙舟,仙舟 2→1 → r3-r4 battle -13×2):仙舟基础线优先
            # 仲裁——门判定单一源 = kernel.recipe_floor_holds(经
            # r288_hold_now 适配器;档值单源 RECIPE_FLOOR_TRAIN_CAP/
            # XZ_BASE)。锁定线语境豁免(ADR-0564,显式推翻本门旧注释
            # 「锁线路径的线内件上板也要守配方底线」的辖域):豁免武装帧
            # ∧ 本帧无有效仙舟供给 → 门让位;门本体与供给保留条款不变
            # (bench 有真供给时照拦,供给先上)。动态防线价值保留:
            # _deployed_fac/_deployed_cids 含拖拽逐件落地增量现值。
            _fac = _bench_fac.get(bi, '')
            if _fac == '列车同行' and r288_hold_now(
                    _fac, _deployed_fac, set(_deployed_cids), _bench_list,
                    _rf_lock_conflict):
                log.info(f'[cw-deploy] 配方底线(r288):列车'
                         f'{_deployed_fac.get("列车同行", 0)}档+仙舟'
                         f'{_deployed_fac.get("仙舟", 0)}→列车件留bench'
                         f'(ctx={"锁定豁免 armed" if _rf_lock_conflict else "默认"}'
                         f',供给在场时豁免闭合)')
                _skipped += 1
                _bump_r288_skip_counter(_sess, _rf_lock_conflict)
                continue
            # live 2026-08-15(match4 deploy storm 根因):起始帧 slot_occupied 瞬时假阳(商店关闭/卖出
            # 动画残影 → 对空槽白烧 3×2s drag 重试)。每槽 drag 前 fresh 复查占用,空 → 跳过。
            if not slot_occupied(self.screenshot(), int(bench[bi].x), int(bench[bi].y)):
                log.info(f'[cw-deploy] deterministic: bench槽{bi+1} fresh 复查空(起始帧假阳/已上阵) → 跳过')
                _skipped += 1
                continue
            # 5.1.6:按角色 position_pref 选排(前台→前排、后台/flex→后排);对应排满 fallback 另一排(避免不上场)。
            pref = _bench_pos.get(bi, 'back')   # SIFT 漏读身份 → 默认 back(后排槽多 6 > 前排 4,安全)
            # 前排保证(出战要求,5.1.6 补;2026-08-16 修正用户实锤):pref=back 但前排完全空(无角色)
            # → 强制前排(出战硬要求前排有角色)。⚠️ 旧实现"当前队首 back 强转前排"错在**没看后续
            # 队列**——M47 22:32 实锤:target 先行把三月七(back)排队首,而队列后面就有真理医生/
            # 乱破(真 front),旧逻辑强转三月七去前排、真 front 也进前排 → back 角色错占前排位。
            # 修正:前排全空时**先重排**(剩余 order 中 pref=front 角色提到当前位前),无 front
            # 候选才强转当前 back 角色。
            if pref == 'back' and len(front_empty) == len(front):
                _later_front = next(
                    (j for j in _pending[_oi:]
                     if _bench_pos.get(j, 'back') == 'front'
                     and _bench_cid.get(j) not in _deployed_cids),
                    None)
                if _later_front is not None:
                    _pending.remove(_later_front)
                    _pending.insert(_oi - 1, _later_front)
                    _oi -= 1   # 原地重处理当前位(现在是真 front;下标循环才有的语义)
                    log.info(f'[cw-deploy] 前排保证(重排): 真front槽{_later_front + 1} 提前'
                             f'(当前槽{bi + 1}为back不强转)')
                    continue
                pref = 'front'
                log.info(f'[cw-deploy] 前排保证:bench槽{bi+1}(pref=back)→ 强制前排(前排空且队列无front候选)')
            if pref == 'front':
                chosen, chosen_pts, fallback, fallback_pts = front_empty, front, back_empty, back
            else:
                chosen, chosen_pts, fallback, fallback_pts = back_empty, back, front_empty, front
            if not chosen:
                if not fallback:
                    # P4R 返工:原静默 break(1-1 事故「3-6 件无尝试日志」的
                    # 排查盲点之一)——终止必须带证据日志,否则无法与迭代器
                    # 跳过/白拖失败区分。
                    log.warning(f'[cw!] [deploy] 两排皆满,无槽可拖 → 终止'
                                f'(未处理 {[s + 1 for s in _pending[_oi:]]};'
                                f'front占={len(front) - len(front_empty)}'
                                f'/back占={len(back) - len(back_empty)})')
                    break
                chosen, chosen_pts = fallback, fallback_pts
            ti = chosen.pop(0)
            dst = chosen_pts[ti]
            src = bench[bi]
            _row_cn = '前' if chosen_pts is front else '后'
            # 5.1.9 重诊(2026-08-13 实测推翻 ADR-0100):整张卡可拖 —— 从**卡中心**拖 + 按下即移(hold_time=0)
            # 即拾取上阵(实测:中心 drag 飞霄 → 上阵 ✓)。avatar/左上星标/hold1s 全是旧错诊(详情=click 触发非
            # mouseDown;drag=按下+移动;左上小圆是星标非头像)。**拖拽统一走 ``DragCwChar.drag_char``**(中心拖
            # + hold0 + retry + 验源槽像素变),本处不再内联 drag_to。
            if DragCwChar.drag_char(self, src, dst):
                # P4R 落点验证(1-1 事故「前排1 ✓」假成功根因):源槽像素变
                # ≠ 上阵成功——拖拽可能实际落后台/无效位(游戏拒收弹回或落
                # 点无效),出战即「前台区域无角色」。目标槽 ~2s 内出现占用
                # 才计 placed;未验出 = 无效拖拽,回收目标槽 + 存证。
                if self._wait_slot_occupied(dst, 2.0):
                    placed += 1
                    # 5.1.7 补(2026-08-13):同轮 drag 成功 → 刚 deploy 的角色入去重集,
                    # 防 bench 同角色 2 张时第 2 张重复 drag(场上已有该角色 → 上场失败)。
                    if _cid:
                        _deployed_cids.add(_cid)
                    # r288:成功上场同步阵营档(配方底线仲裁的状态源)
                    # r363b(review B-2 修):增量口径对齐初始快照——该角色
                    # **全部**羁绊(factions+flows)各 +1(旧只计第一阵营,
                    # 多阵营角色上阵后与真实板面漂移,r288 门错判风险)。
                    _bonds_all = (_bench_id.get(bi) or ())
                    for _f2 in _bonds_all:
                        _deployed_fac[_f2] = _deployed_fac.get(_f2, 0) + 1
                    if _match is not None and getattr(_match, 'bench_slot_map', None):
                        _gone = next((n for n, s in _match.bench_slot_map.items() if s == bi + 1), None)
                        if _gone is not None:
                            del _match.bench_slot_map[_gone]
                    # ⚠️ 拖后特效等待(用户 2026-08-16 实证):拖上场会触发羁绊特效/升星 overlay
                    # (盛会之星/圣杯/银狼升级等)遮挡画面 —— 紧跟的下个 drag/CV 验槽/SIFT 读全被
                    # 污染。每个成功 drag 后等 1.2s 让特效播完/overlay 稳定(下轮 loop/director
                    # 的事件 overlay 检测再接管真正的交互型 overlay)。
                    time.sleep(1.2)
                    _fb = ' (fallback)' if (pref == 'front') != (_row_cn == '前') else ''
                    log.info(f'[cw-deploy] deterministic: bench槽{bi+1}(pref={pref}) → {_row_cn}排{ti+1} ✓{_fb}'
                             f' (落点已验)')
                else:
                    import contextlib
                    with contextlib.suppress(Exception):
                        self.save_screenshot(
                            prefix=f'deploy_landing_fail_slot{bi + 1}')
                    chosen.insert(0, ti)   # 目标槽没占住,回收给下个角色
                    log.warning(f'[cw!] [deploy] deterministic: bench槽{bi+1} → '
                                f'{_row_cn}排{ti+1} 源槽已变但落点 2s 未验出占用'
                                f' → 判无效拖拽(1-1 事故形态;失败帧已存证)')
            else:
                # live 2026-08-15(match4 根因):drag_char 的 before 帧取自 retry 循环外,成功验证可滞后;
                # 失败后 fresh 复查源槽 —— 已空 = 实际拖成(验证滞后)计 placed;仍占 = 真失败。
                # P4R 落点验证补:源空 + 落点也未占用 = 无效拖拽(单位丢失/弹回,
                # 同 1-1 事故形态)→ 不计 placed,存证。
                time.sleep(0.3)
                if not slot_occupied(self.screenshot(), int(src.x), int(src.y)):
                    if self._wait_slot_occupied(dst, 2.0):
                        placed += 1
                        if _cid:
                            _deployed_cids.add(_cid)
                        _bonds_all = (_bench_id.get(bi) or ())
                        for _f2 in _bonds_all:
                            _deployed_fac[_f2] = _deployed_fac.get(_f2, 0) + 1
                        if _match is not None and getattr(_match, 'bench_slot_map', None):
                            _gone = next((n for n, s in _match.bench_slot_map.items() if s == bi + 1), None)
                            if _gone is not None:
                                del _match.bench_slot_map[_gone]
                        time.sleep(1.2)   # 拖后特效等待(同上)
                        log.info(f'[cw-deploy] deterministic: bench槽{bi+1} fresh 复查源槽已空'
                                 f' + 落点已验 → 判拖成(验证滞后)')
                    else:
                        import contextlib
                        with contextlib.suppress(Exception):
                            self.save_screenshot(
                                prefix=f'deploy_landing_fail_slot{bi + 1}')
                        chosen.insert(0, ti)
                        log.warning(f'[cw!] [deploy] deterministic: bench槽{bi+1} 源槽已空'
                                    f' 但落点未验出占用 → 判无效拖拽(源变≠上阵;'
                                    f'失败帧已存证)')
                else:
                    log.info(f'[cw-deploy] deterministic: bench槽{bi+1}(pref={pref}) → {_row_cn}排{ti+1}'
                             f' 拖3次源槽未变,跳过(失败帧存证)')
                    import contextlib
                    with contextlib.suppress(Exception):
                        self.save_screenshot(prefix=f'deploy_fail_slot{bi + 1}')
                    chosen.insert(0, ti)   # 目标槽没占住,回收给下个角色
        # P24 残余补部署(dd-016):主排序完成后空槽仍在(cap 未满)且散牌
        # 留置非空 → 按计划补上。判据 = P24 残余补部署支配定理(空 cap 槽上
        # 任意合法单位 ΔEV≥0;复盘 g_20260902_181254 修复项 E:r2-r4 板 3/4
        # 空槽不上人)。计划 = 纯函数 residual_fill_plan(同名禁双/cap 门/
        # 选排 fallback 守卫与其内注释同源);执行侧每拖前 fresh 复查占用
        # (主循环同款,防起始帧假阳)。
        if _held:
            # B1 返工连带面:kernel 恒拒的物品槽不得经 P24 补部署绕回上板
            # (held 名单内剔除,同下方 r288 底线辖 fill 段先例)。
            _held_fill = [_hi for _hi in _held
                          if (_hi + 1) not in _item_slots_exact]
            # fill 输入重采样(1-1 事故:主循环排满 cap 后 P24 把 kernel 明确
            # 留 bench 的留置件反复往满员板拖,游戏以人口上限不足拒收;根因
            # = fill 拿到的容量输入是入口快照而非主循环后真值):
            # - 计数:_deployed 是入口仲裁快照(此后不刷新),主循环增量只有
            #   placed(只数落点验证成功件)→ 传 _deployed+placed,与上方
            #   动态板满门同式,自然排尽/cap-stop break 两条退出路径同式覆盖;
            #   cap 计数禁改走 CV 占用(DD-030 幻影占用面)。
            # - 槽位:主循环的 front_empty/back_empty 虽是别名活值(chosen
            #   pop/insert 原地变异),但「源槽已变+落点未验出→判无效」的
            #   insert 回收会把实际已落位槽记成空(幻影空槽→fill 指向已占槽
            #   白拖)→ fresh 帧按主循环同款列表推导重采两排(最终布局档,
            #   延续 862-865 占用统一采样纪律)。禁按 placed 扣减现有列表
            #   ——列表已被主循环原地扣减,再扣=双扣减,dd-016 静默修死。
            _scr_fill = self.screenshot()
            _fe_fill = [i for i, c in enumerate(front)
                        if not slot_occupied(_scr_fill, int(c.x), int(c.y))]
            _be_fill = [i for i, c in enumerate(back)
                        if not slot_occupied(_scr_fill, int(c.x), int(c.y))]
            log.info(f'[cw-deploy] 补部署输入重采样: front空={_fe_fill} '
                     f'back空={_be_fill} deployed={_deployed}+placed={placed}')
            _fill_plan = residual_fill_plan(
                _held_fill, _fe_fill, _be_fill, _bench_pos, _bench_cid,
                _deployed_cids, _cap, _deployed + placed)
            # r288 底线对 fill 段同样辖(dd-037):kernel 留 bench 的列车件
            # (列车≥2 档 ∧ 仙舟<3 基础线)不得经 P24 补部署绕回上板——
            # 补部署只覆盖「散牌留 bench」的填位语义,不覆盖配方底线仲裁。
            # 过滤纯函数化(ADR-0564):与主循环同消费 r288_hold_now,
            # 豁免语境下计划层与执行门层同帧同值,无第二副本。
            _fill_plan_n0 = len(_fill_plan)
            _fill_plan = filter_fill_plan_by_floor(
                _fill_plan, _bench_fac, _deployed_fac, set(_deployed_cids),
                _bench_list, _rf_lock_conflict)
            for _ in range(_fill_plan_n0 - len(_fill_plan)):
                _bump_r288_skip_counter(_sess, _rf_lock_conflict)
            for _fi, _frow, _fslot in _fill_plan:
                _fpts = front if _frow == 'front' else back
                if _fslot >= len(_fpts):
                    continue   # 计划越界防御(布局档中途变化)
                if not slot_occupied(self.screenshot(), int(bench[_fi].x), int(bench[_fi].y)):
                    _skipped += 1
                    continue   # fresh 复查空(已上阵/假阳),同主循环语义
                if DragCwChar.drag_char(self, bench[_fi], _fpts[_fslot]) \
                        and self._wait_slot_occupied(_fpts[_fslot], 2.0):
                    placed += 1
                    _fcid = _bench_cid.get(_fi)
                    if _fcid:
                        _deployed_cids.add(_fcid)
                    time.sleep(1.2)   # 拖后特效等待(主循环同款)
                    log.info(f'[cw-deploy] 补部署(dd-016/P24): bench槽{_fi + 1} → '
                             f'{"前" if _frow == "front" else "后"}排{_fslot + 1} ✓(落点已验)')
                elif DragCwChar.drag_char(self, bench[_fi], _fpts[_fslot]):
                    # 第一段 drag 真、落点未验出 → 与主循环同款判无效(不计 placed)
                    log.warning(f'[cw!] [deploy] 补部署(dd-016): bench槽{_fi + 1} 落点'
                                f'未验出占用 → 判无效拖拽(源变≠上阵)')
                else:
                    log.info(f'[cw-deploy] 补部署(dd-016): bench槽{_fi + 1} 拖3次源槽未变,跳过')
        # r349(局38 判读):合法跳过(去重/配方底线/源槽已空)≠ 上阵失败——
        # 旧 `placed < len(order)` 把「target 已在场,bench 同名拷贝被去重」
        # 误报 [cw!] 假警报(placed=0/2,局38 01:29 实证)。分母扣除跳过数。
        # P4R:警告附未处理件枚举(1-1 事故「3-6 件无尝试日志」的排障盲点补齐)。
        if placed + _skipped < len(order) and not _cap_stopped:
            log.warning(f'[cw!] [deploy] 上阵不全: placed={placed}/'
                        f'{len(order) - _skipped}(跳过{_skipped};失败帧已存证)')
        log.info(f'[cw-deploy] deterministic 完成: placed={placed}/{len(order) - _skipped}'
                 f'(跳过{_skipped})')
        # T3 同轮保留集「部署即销」(生命周期出口①):主排序 + P24 补部署
        # 上板的名(含被保垫件经保护活到部署帧后的上板转化)从保留集销账,
        # 防后续帧误保。属性契约级接线(与 held 显影同形态,无策略 import)。
        prune_fuel_filler_deployed(_sess, _deployed_cids)
        # 失败记忆单一源(ADR-0601 §3 C4):同签名 0 落地的失败记忆归分发层
        # (cw_loop PREP_NO_PROGRESS_ROUNDS + prep_no_progress_tick 同签名
        # 计数 + 停机留证),op 侧不再自持第二份熔断计数;placed=0 且计划
        # 非空 → 节点 STATUS_LANDED_NONE round_fail 如实上报。
        return placed, not order, None

    def _wait_slot_occupied(self, pt: Point, timeout_s: float = 2.0) -> bool:
        """落点验证原语(P4R 返工):目标槽 ~timeout_s 内出现占用 = 上阵落地。

        判据 = drag 后对比**目标槽**占用(旧判据只验 bench 源槽像素变——
        1-1 事故:源槽已变、单位实际落后台/无效位 → 「前排1 ✓」假成功 →
        出战被游戏拒「前台区域无角色」)。事件驱动轮询(od-dev-write-operation
        「点了≠成了」),命中即返;超时 False(调用方判无效拖拽)。
        """
        deadline = time.monotonic() + timeout_s
        while True:
            if slot_occupied(self.screenshot(), int(pt.x), int(pt.y)):
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.3)

    def _get_templates(self) -> AvatarTemplates | None:
        """加载 avatar SIFT 模板(缓存到 ctx.cw_avatar_templates,首次 load 后复用)。"""
        cached = getattr(self.ctx, 'cw_portrait_templates', None)
        if cached is not None:
            return cached
        base = get_project_root() / 'assets/template'
        portrait_dir = base / 'currency_war' / 'portrait_plaza'   # 官方立绘库(plaza 烘焙;唯一库,旧手采库已删 2026-08-17)
        if not portrait_dir.is_dir():
            log.warning(f'[cw-deploy] 立绘库目录不存在 {portrait_dir},退非身份 deploy')
            return None
        templates = load_avatar_templates(portrait_dir)
        self.ctx.cw_portrait_templates = templates
        log.info(f'[cw-deploy] 加载 {len(templates)} 个 avatar 模板(缓存 ctx)')
        return templates

    def _record_fenced_preserve(self, d: object, bonds: set[str]) -> None:
        """W209 撤销操作证据留存(纯观测,零行为变更;复用 defect_ledger)。

        从卖出循环提出:fenced 件被拒保留时记一笔(单一判定路径与退型
        路径共用,落账失败不拦部署)。
        """
        try:
            from sr_od.application.currency_war.telemetry.undo_evidence import (
                record_sell_breaker_preserved,
            )
            record_sell_breaker_preserved(
                char_id=getattr(d, 'char_id', '') or '',
                reason='fence:' + ','.join(sorted(bonds & _DEPLOY_FENCE)),
                channel='deploy_offtarget')
        except Exception as _ev_err:   # 兜底日志:留证落账失败不拦部署
            log.warning(f'[cw-deploy] 卖出熔断留证落账失败(不拦):{_ev_err}')

    def _sell_offtarget_deployed(self, front: list[Point], back: list[Point],
                                 target_factions: set[str], templates: AvatarTemplates | None,
                                 max_sell: int = 99, target_cores: set[str] | None = None,
                                 fenced_offline_sellable: bool = False,
                                 protect_names: frozenset[str] = frozenset(),
                                 swap_ctx: object | None = None,
                                 bench_chars: list | None = None,
                                 m1p_arm: str | None = None,
                                 deployed_chars: list | None = None) -> int:
        """D-10:卖 deployed 中的 **off-target** 单位(留 target),给 bench target 腾位。

        SIFT ``read_deployed_chars`` 识别 deployed 身份 → off-target(羁绊 ∌ target)拖出售区。
        target 单位保留(替旧 sell-all 毁掉板上 target)。卖数 ≤ ``max_sell``(**1:1 替换上限** = bench
        target 数,保证每个卖出被一个 target 补上,板大小稳定;防 bench target 少却卖光 off-target → 板缩 HP 崩)。
        ⚠️ ``read_deployed_chars`` 首用(deployed SIFT 身份未单验,D-4 验的是占用);日志详记识别结果供核实,
        首跑即验证 —— 若身份错(误卖 target / 漏卖 off-target)据日志回退。

        :param deployed_chars: 调用位预读的 deployed 域覆盖(F1 换阵可兑现
            谓词在门位已读一次;传入免重读,同帧同域,SIFT 识别零二义);
            None = 本函数自读(旧路径,防御缺省)。

        逐件单一判定(``swap_ctx`` 消费;ADR-0534 §4,docs/develop/currency_war/
        decisions/0534-swap-transition-arm.md):swap_ctx 在场时,每个卖出候选经
        kernel ``swap_sell_exclusion_reason``
        同一判定函数逐件定价——排除族(buy_membership/fresh_buy/membership_unreadable,
        ADR-0530 语义不变)∪ 资格族(per-piece fenced 可卖性 = fenced_on ∨ 转型臂资格;
        **禁退化为标量 fenced_on 喂入**——标量形态正是 fp<1.00 帧新资格族整体不可达的
        缺口根源,ADR-0534 §4)。资格族拒因(engines_guard/merge_material_guard/star_guard/
        target_keep/fenced_arm_closed/fp_unreadable)在执行侧遥测逐件显影(分键
        ``deploy_swap_sell_rejected_*``),转型帧拒卖零静默;``fenced_arm_closed`` 且
        fenced 件保留 W209 撤销留证。``star``/``bench_chars``/deployed 现读喂入判定
        函数(星级/合成素材全场域计数需要现读域;发射侧用 ctx 帧域,同函数同判)。
        swap_ctx 不可得(last_state 缺,装配未跑)时退旧路径(标量 fenced +
        排除链静默关闭)——与缺读禁卖不对称,在册遗留缺口原样继承未扩大
        (排除静默关闭态的收紧候裁另案,ADR-0534 §4)。

        ``m1p_arm`` = 发射位透传的 m1p 换血臂(transition/formed/base;
        None = 非 m1p 帧):每件实际卖出按此归因计数
        ``sell_offtarget_arm_{arm}`` / ``sell_offtarget_regular``
        (观测分键,消费读后即清,不改卖出行为)。
        """
        deployed = deployed_chars if deployed_chars is not None else (
            exclude_system_units(
                read_deployed_chars(self.ctx, self.last_screenshot, templates)
            ) if templates else [])
        _sell = Point(70, 846)
        sold = 0
        _excluded_n = 0
        _sess = (self.ctx.cw_match.session
                 if (self.ctx.cw_match is not None
                     and self.ctx.cw_match.session is not None) else None)
        _counters = getattr(strategy_state_of(_sess), 'cw4_counters', None) if _sess else None
        _cands: list[tuple[tuple, object, set[str]]] = []
        for d in deployed:
            if sold >= max_sell:
                break
            ch = get_char(d.char_id) if d.char_id else None
            if ch is None:
                continue   # 系统单位(cost==0)已在入口剔除(ADR-0281 件4)
            bonds = set(ch.factions) | set(ch.flows)
            if swap_ctx is not None:
                # 逐件单一判定(排除族∪资格族;与 M1″ 发射面同函数,ADR-0534 §3)
                from sr_od.application.currency_war.kernel.cw_deploy_logic import (
                    swap_sell_exclusion_reason as _sser,
                )
                _rej = _sser(d.char_id or '', swap_ctx,
                             star=getattr(d, 'star', None),
                             bench=bench_chars, deployed=deployed)
                if _rej:
                    if _rej in ('buy_membership', 'fresh_buy',
                                'membership_unreadable'):
                        _excluded_n += 1
                        if isinstance(_counters, dict):
                            _key = f'deploy_swap_sell_excluded_{_rej}'
                            _counters[_key] = _counters.get(_key, 0) + 1
                        log.info(f'[cw-deploy] swap 卖出排除({_rej}):'
                                 f'{d.char_id} → 保留(义务集∪新鲜度统一排除,'
                                 'P60 对账;ADR-0530)')
                    else:
                        # 资格族拒因逐件显影(转型帧拒卖零静默,ADR-0534 §4)
                        if isinstance(_counters, dict):
                            _key = f'deploy_swap_sell_rejected_{_rej}'
                            _counters[_key] = _counters.get(_key, 0) + 1
                        log.info(f'[cw-deploy] swap 卖出拒({_rej}):{d.char_id}'
                                 f'({sorted(bonds & _DEPLOY_FENCE)}) → 保留'
                                 '(单一判定函数逐件拒因,转型臂同函数)')
                        if _rej == 'fenced_arm_closed' and bonds & _DEPLOY_FENCE:
                            self._record_fenced_preserve(d, bonds)
                    continue
                _cands.append(((1, 0 if getattr(d, 'star', 1) <= 1 else 1),
                               d, bonds))
                continue
            # 退型路径(swap_ctx 不可得):标量 fenced + 排除链静默(旧语义)
            if not offtarget_sell_allowed(d.char_id, bonds, target_factions,
                                          target_cores or set(),
                                          fenced_offline_sellable=fenced_offline_sellable,
                                          protect_names=protect_names):
                if bonds & _DEPLOY_FENCE:
                    # ADR-0386 振荡熔断:引擎/配方体系件保留(与围栏同源反向禁卖;
                    # 换阵卖出义务臂开启时 off-line fenced 件已让位,走不到这里)
                    log.info(f'[cw-deploy] off-target 卖出熔断:{d.char_id}'
                             f'({sorted(bonds & _DEPLOY_FENCE)}) 是引擎/配方体系件'
                             f' → 保留(买/演进层目标源与终局 target 分歧时禁互踩)')
                    self._record_fenced_preserve(d, bonds)
                continue
            _rank: tuple = (1, 0 if getattr(d, 'star', 1) <= 1 else 1)
            _cands.append((_rank, d, bonds))
        if _excluded_n:
            log.info(f'[cw-deploy] deploy-swap 排除显影:{_excluded_n} 个候选'
                     '被义务集/新鲜度排除保留(分键 deploy_swap_sell_excluded_*)')
        for _rank, d, bonds in _cands:
            if sold >= max_sell:
                break
            row = front if d.position_pref == 'front' else back
            if not (1 <= d.slot <= len(row)):
                continue
            # W209e 装备资产观测(run 26 取实锤:off-target 卖出通道不查装备
            # 价值、不留装备去向——简易装备全穿在卡芙卡/千冶·刃/风堇身上,
            # 这批人被卖出 → 装备随人消失(owned 5 件 → 2 工具),分配池干涸
            # 全盲)。卖出前记装备去向留痕(等价卖出回收 = 装备回 owned;
            # 装备价值进卖出决策是更大的决策面,记 ADR-0387 待裁决,本批先
            # 观测)。d.equips 由 _snapshot_equips_into_tracking 维护。
            _eq = list(getattr(d, 'equips', None) or ())
            if _eq:
                log.warning('[cw!][deploy] off-target 卖出携带装备:%s 穿着'
                            ' %s 随卖出离场(ADR-0387 观测;若非预期=装备资产'
                            '流失,卖出决策该查装备价值)',
                            d.char_id, sorted(_eq))
            src = row[d.slot - 1]
            if DragCwChar.drag_char(self, src, _sell):
                sold += 1
                # m1p 驱动归因分键(39 跳登记:sell-offtarget 闭环哪几次属
                # m1p 驱动不可辨):发射位透传臂(transition/formed/base)
                # 计 sell_offtarget_arm_{arm},非 m1p 帧计 regular。
                # 只计数不改卖出行为,零策略语义。
                if m1p_arm:
                    _sell_key = f'sell_offtarget_arm_{m1p_arm}'
                else:
                    _sell_key = 'sell_offtarget_regular'
                if isinstance(_counters, dict):
                    _counters[_sell_key] = _counters.get(_sell_key, 0) + 1
                log.info(f'[cw-deploy] sell-offtarget:{d.char_id}({sorted(bonds)}) @'
                         f'{"前" if d.position_pref == "front" else "后"}排{d.slot} → 出售区 ✓ '
                         f'(源槽变;m1p_arm={m1p_arm or "-"})')
            else:
                log.info(f'[cw-deploy] sell-offtarget:{d.char_id} 拖3次源槽未变,跳过')
        if deployed:
            log.info(f'[cw-deploy] read_deployed_chars={[(d.char_id, d.position_pref, d.slot) for d in deployed]};'
                     f' sold {sold}/{max_sell} off-target (target_factions={sorted(target_factions)})')
        return sold

    def _reconcile_tracking(self, templates: AvatarTemplates | None) -> None:
        """D-12(3.3.2 · 观测回路):deploy 后用 SIFT 身份 + ``read_star`` 实机星级 重置 session.tracking。

        根因:deploy op 视觉拖拽不调 ``mutate_bench_deployed`` → tracking 滞留(已上场在 bench / 已卖在 deployed)
        → 下轮 buy 用漂移 tracking 错。本方法:deploy 后(SIFT 准)读真实 bench/deployed 身份重置 tracking。

        ⚠️ 2026-08-12:star 用 ``identify_slots`` 的 ``read_star`` 实机金星(非旧 tracking pool 保留)。旧逻辑「保留
        旧 star(SIFT star 恒1)」注释过期 —— read_star 已接(commit 672aa838,identify_slots L159 读实机金星)。
        用户:假设 star 识别对(read_star 实机 > simulate 推算;且 simulate _merge 只看 bench,3合1 是全场
        deployed+bench+买)。read_star 1星验过,2星逻辑同(数金星)。

        2026-08-16(观察冲突审计 P0 #12):改调公共 ``cw_reconcile.reconcile_tracking`` ——
        旧实现直接覆盖无空读守卫(M14 实锤的过渡帧双空读会污染 tracking;守卫此前只在
        director 版),同语义两处强弱不一是 bug 温床;统一后另接 obs_conflict 证据链。
        """
        if templates is None:
            return
        _match = self.ctx.cw_match
        if _match is None or _match.session is None:
            return
        # 布局未知态写类冻结(15 号稿 §3.2④/T-7):reconcile 是整表采新覆写,
        # 后排身份缺读帧(未知态 read_deployed_chars 只返前排)会把 back 缺读
        # 当「板空」写进 tracked = 错向毒化底座 → 未知史在案(任一未知帧,
        # 单帧/冻结同停)整表对账跳过,已知帧(计数清零)自动恢复。
        from sr_od.application.currency_war.obs.cw_back_layout import (
            back_layout_unknown_streak,
        )
        if back_layout_unknown_streak() >= 1:
            log.info('[cw-deploy] 布局未知态在案 → tracking 整表对账跳过'
                     '(写类冻结,§3.2④)')
            return
        scr = self.screenshot()   # fresh post-deploy
        real_bench = read_bench_chars(self.ctx, scr, templates)
        real_deployed = read_deployed_chars(self.ctx, scr, templates)
        from sr_od.application.currency_war.kernel.cw_reconcile import (
            reconcile_tracking,
        )
        reconcile_tracking(_match.session, real_bench, real_deployed, scr,
                           source='deploy_bench', ctx=self.ctx)
