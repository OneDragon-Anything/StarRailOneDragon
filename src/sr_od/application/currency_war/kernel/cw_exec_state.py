"""货币战争 执行域领域模型与纯函数宿主(cw_exec_state;无状态面)。

本模块不承载跨调用状态——原执行层状态载体已整体退役,局内事实宿主 =
GameState(kernel/cw_game_state.py)。现辖三类领域函数:

- op 逻辑效果推进:``apply_op_effect``(两态制标准语义,ADR-0651);
- 槽位表领域模型:``BenchChar`` + bench/deployed 槽位语义 helpers 与
  物理(排,槽号)↔ 表下标换算(deployed_row_slot / deployed_idx_of
  互逆对);
- 位面节点序列台账访问:get_node_ledger / ledger_node_type /
  ledger_update_plane 与 fill_boss_by_position(台账值载体
  ``PlaneNodeLedger`` 住 kernel/cw_game_state.py,本模块运行时转发,
  保持既有 import 路径不断链)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log

# 台账值载体(运行时转发,非仅注解):类本体住 kernel/cw_game_state.py
# (宿主 = 容器非 Field 簿记 GameState.plane_node_sequences 所在模块),本模块
# 转发保持 cw_vocab 转出口与既有 import 路径不断链(消费面零改动的成立前提)。
# cw_game_state 模块级依赖不反向触达本模块
# (惰性 import 面),此模块级引入不成环。
from sr_od.application.currency_war.kernel.cw_game_state import (
    PlaneNodeLedger,
)

if TYPE_CHECKING:
    # 仅类型注解引用(项目规范;运行时按需惰性 import,守同仓懒加载惯例)。
    from sr_od.application.currency_war.kernel.cw_vocab import (
        CwAction,
    )


# ============================================================ op 逻辑效果推进
# (波 5b 自 kernel/cw_expected_state 迁入:模块名随期望态条目表概念退役,
# ADR-0651 两态制存续函数整体搬迁,零行为变化;消费点 = root prep_actions
# 执行器两处 + _overlay_confirm.register_confirm_arrival。
# ⚠️ 动作词表/合成引擎(cw_vocab/cw_merge_simulate)模块级 import 本模块
# (转出口),本模块对其依赖一律函数内惰性 import,模块级引入会成环——
# 沿用本仓懒加载惯例。)

def _session_tracked(session) -> tuple[list[BenchChar], list[BenchChar | None]]:
    # tracked 主账宿主 = 容器簿记 GameState.tracked_books
    #(kernel/cw_game_state.py;lazy import 防模块环,同 _advance_gold 惯例)。
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


def apply_op_effect(session, action: CwAction | dict, *,
                    produced_by: str = 'PrepActionExecutor',
                    detail: str = '',
                    skip_substate: bool = False) -> list[dict]:
    """原子 op 的逻辑效果推进(两态制标准语义,ADR-0651;两执行面同源入口)。

    按游戏规则把 op 的可推算效果**直接写 session 字段**(owned 增减/
    专项金腿),返回推进清单 [{path, value, kind}](组合动作子动作
    效果上抛形态,只含本函数实际写过的字段)。

    **卖出回金不在本口**(统一观察对账迭代 2026-09-16 归因批退役双记
    腿):SellBench/SellDeployed 的容器金账唯一写点 =
    :func:`apply_prep_action_logic` 对应分支(实机执行缝+投影双腿各记
    一次 +refund,实读倒挂 −2 实证);本口 SellDeployed 仅保留 owned
    装备回收腿(执行账单一写者,无投影对应物)。专项金腿存续面 =
    现金为王弃卡回金与 dict 形 BuyCard(无投影对应物,单写点)。

    ``skip_substate`` = 出战动作的免战跳过子态标记(StartBattleOp 经
    runner 包络上报;op 零 game state 直写)。True = 本次出战走「跳过」
    按钮(免战牌生效)→ 次数递减挂本口(上报时递减,非「验证落地后」
    ——出战 op 已零验证,T-286 出战域重设计)。

    显式不建模盲区(EXPECTED_STATE §6 原申报语义存续):``_handle_bench_full``
    席满急救(买经验×10 + 卖前几槽)不经执行器 → 不在推进面,该形态由
    观察覆盖兜底(声明而非遗漏)。
    """
    effects: list[dict] = []
    if session is None:
        return effects
    from sr_od.application.currency_war.kernel.cw_vocab import (
        ClickSpheres,
        SellDeployed,
        StartBattle,
        WearEquip,
    )

    def _eff(path: str, value, kind: str) -> None:
        effects.append({'path': path, 'value': value, 'kind': kind})

    if isinstance(action, SellDeployed):
        # (卖出回金容器唯一写点 = apply_prep_action_logic 对应分支,
        #  本口不记金防双记——实机 −2 倒挂实证;owned 装备回收腿 =
        #  执行账单一写者。)
        _bench, dep = _session_tracked(session)
        bc = dep[action.deployed_idx] \
            if 0 <= action.deployed_idx < len(dep) else None
        if bc is not None:
            for eq in (getattr(bc, 'equips', None) or []):
                _owned_add(session, eq)
                _eff(f'owned[{eq}]', '+1(卖场上装备全额返还)', 'owned')
    elif isinstance(action, WearEquip):
        # 穿戴原子(R2;发出即记账):本分支仅在执行器 emitted 门放行时
        # 可达(op 定位失败等未发出通道 emitted=False,整支跳过,无账可
        # 记);照常发出路径 = 机械执行零判效(用户裁定,落地判定归观察
        # 侧 reconcile),owned −1 + tracked 目标角色 +1。
        # WearEquip 是坐标参数化机械动作(row/slot = 画面物理槽位,词表
        # 定义);物理→下标换算单一函数 = deployed_idx_of(执行坐标边)。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            ChannelSig,
            game_state_of,
        )
        _gs_we = game_state_of(session)
        owned = list(_gs_we.equips.value or [])
        if action.item_name in owned:
            owned.remove(action.item_name)
            _gs_we.write_logic(_gs_we.equips, owned,
                               produced_by='PrepActionExecutor',
                               evidence=f'owned[{action.item_name}] -1(穿戴)',
                               sig=ChannelSig(family='logic_action',
                                              actor='PrepActionExecutor',
                                              screen='', mode='compute'))
            _eff(f'owned[{action.item_name}]', '-1(穿戴)', 'owned')
        idx = deployed_idx_of(action.row, action.slot)
        _bench, dep = _session_tracked(session)
        if 0 <= idx < len(dep) and dep[idx] is not None:
            dep[idx].equips = list(getattr(dep[idx], 'equips', None) or []) \
                + [action.item_name]
            _eff(f'deployed[{idx}].equips', f'+{action.item_name}(穿戴)',
                 'tracked')
    elif isinstance(action, StartBattle):
        # 进战斗:hp/gold/streak 由结算屏观察覆盖接管(原显式不推进理由
        # 升格为分支);唯一逻辑推进 = 免战牌跳过递减(上报时递减;标记
        # 由 StartBattleOp 经 runner 包络上报,op 零 game state 直写)。
        # 递减 best-effort 记录面:未登记(登记面缺位的局)→ consume_use
        # 返 None 零动作,与升级挂点同纪律(cw_effect_inventory.consume_use)。
        if skip_substate:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                game_state_of,
            )
            from sr_od.application.currency_war.kernel.cw_investments import (
                STRATEGY_EFFECTS,
            )
            _spec = STRATEGY_EFFECTS.get('免战牌')
            if _spec is not None:
                _left = game_state_of(session).effects.consume_use(_spec.id)
                if _left is not None:
                    _eff('effects[免战牌]', f'remaining_uses→{_left}(跳过上报递减)',
                         'effects')
                    log.info('[cw][battle] 免战牌跳过上报 → 次数递减(余 %s)', _left)
    elif isinstance(action, ClickSpheres):
        # 备战环随机收入申报窗(20260918-reconcile 第 9 例收口)。零推进
        # 语义不变:球金金额执行点不可推算(声明盲区),金账照旧不写——
        # 本分支只按载荷球数开「待吸收窗」,下一可信金读帧的正向差由
        # ``GameState._absorb_prep_sphere_income`` 精确吸收,店开帧收口
        #(机理与红线 = ``ExecBooks.prep_sphere_income_pending`` 字段注释;
        # pending_reward 无 session 字段载体,零推进原申报存续)。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            game_state_of,
        )
        game_state_of(session).exec_books.prep_sphere_income_pending += \
            len(action.points)
    elif isinstance(action, dict):
        # 确认类到账(dict 形态;{'op','item'}):owned 本体推进。
        # ConfirmStrategy 不在此推(active_strategies 本体追加 = handler
        # 确认成功后既有写点,cw_screen_invest_strategy)。
        op = action.get('op', '')
        item = action.get('item', '')
        if op in ('ConfirmSupply', 'ConfirmBox', 'ConfirmTome') and item:
            _owned_add(session, item)
            _eff(f'owned[{item}]', f'+1({op})', 'owned')
        elif op == 'ConfirmExpertCash':
            # 专家邀请函「现金为王」:弃卡取现金固定回金 +4 金账直推
            # (原 _overlay_confirm 内联 last_state 直推随链退役迁入本口,
            # 与 owned 确认族同一推进语义单一源;shop_wave_top 实读覆盖修正)。
            _advance_gold(session, 4, produced_by=produced_by)
            _eff('gold', '+4(现金为王弃卡回金)', 'gold')
        elif op == 'BuyCard':
            # dict 形 BuyCard(模拟/离线入口):合成引擎算购买数,金账
            # 逻辑推进;tracked 本体推进 = 执行器/调用方辖。
            _apply_buy_card(session, action, _eff)
    else:
        # 显式不推进理由(原 §3 铁律枚举,两态制下语义存续):
        # - OpenBox/OpenTome:箱/典籍不消失(仅画面态,消耗在选卡确认;
        #   OpenBox 2a 终结化后选卡 = 武装箱选择画面 op,零容器账);
        # - OpenShop(含 read_only):画面态周转,零局状态变更;
        # - LevelUp:经验/等级/金 = 容器逻辑态(apply_prep_action_logic
        #   LevelUp 分支,xp_apply_clicks + action.cost 直写单一源,
        #   批2b 翻转后金腿不经执行缝);
        # - SellBench:容器金/bench 逻辑态全归 apply_prep_action_logic
        #   (金腿双记退役,统一观察对账迭代 2026-09-16);
        # - DeployMove/SellDeployed:容器逻辑态 = apply_prep_action_logic
        #   扩域分支(金腿同上批退役);tracked 位移/摘除 = 执行器
        #   _track_* 单一写者;
        # - 工具原子(FurnaceUse 等):消耗/变换 = 视觉域逻辑态
        #   (_project_prep_obs 按 EQUIP_WRITE_SIDES 申报)+ 下一帧装备区
        #   读数覆盖;last_owned_equips 挂账面随对拍拆除不入本口;
        # - ClickSpheres:零金账推进(球金不可推算)+ 按载荷球数开点球金
        #   待吸收窗(本文件 ClickSpheres 分支申报);
        # - 买牌单元:tracked 本体推进 = 执行器/调用方辖(容器
        #   tracked_books 随动同步,mutate_bench_deployed 单口)。
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


@dataclass
class BenchChar:
    """备战栏/已上阵角色(= strategy/06 的 ``Unit``;加 ``equips``)。"""
    slot: int
    char_id: str = ""    # 角色id(SIFT/OCR 名);未知 ""
    faction: str = "?"   # 阵营
    star: int = 1        # 星级
    position_pref: str = "back"  # 命途定位 front/back(来自 get_role_position)
    # Sequence(快照拷贝语义落码(ADR-0465 §9):拷贝侧固化为 tuple;session/state
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
    """快照拷贝语义的元素拷贝(落码判据见 ADR-0465 §9):浅拷贝 + equips 固化
    为 tuple——快照帧与 session.tracked_*(就地写端=shop.py
    mutate_bench_deployed 星级/装备拼接、deploy_bench 装备覆盖)断开
    对象别名,「快照不在帧间存活」由机制保证而非消费纪律约定。
    保留理由 = 现役活消费方 = cw_game_state.py 部署装配 scratch 拷贝链。
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


def bench_occupied_slot_nos(bench: list[BenchChar | None]) -> list[int]:
    """占用槽号信息位集(槽号健康门输入;None 槽跳过)。

    [索引定义] 值 = BenchChar.slot 信息位(1 基物理槽号,ADR-0316);
    信息位恒为派生位,权威槽位 = 表下标(ADR-0605 §5.2)。"""
    return [b.slot for b in (bench or []) if b is not None]


def bench_slots_healthy(slot_nos: list[int]) -> bool:
    """槽号健康不变量单一源:占用槽号唯一 ∧ 全在 1..BENCH_CAPACITY。

    背景:SIFT 读/对账 churn 产生的槽号属无守卫数据(ADR-0646),
    违者不得固化为槽位表。消费方 = 对账写回门(kernel/cw_reconcile)、
    tracked 写点显影(prep_actions)。"""
    return (all(isinstance(s, int) and 1 <= s <= BENCH_CAPACITY
                for s in slot_nos)
            and len(set(slot_nos)) == len(slot_nos))


def bench_from_compact(chars: list[BenchChar]) -> list[BenchChar | None]:
    """紧缩序列 → 槽位表(顺序放置;BenchChar.slot 已带 1-based 物理槽号
    时按槽放置)。旧语料/紧缩构造入槽位模型的适配单一源。"""
    bench: list[BenchChar | None] = [None] * BENCH_CAPACITY
    for bc in chars:
        # 形状双源防御(ADR-0316 持久态契约):输入可能是 pad 态(定长 9 含
        # None,如 mutate_bench_deployed 就地 pad 后的 GameState.tracked_books.bench)
        # 或紧凑态(无 None)——两种形态都是本适配源的输入域,None 直接跳过。
        if bc is None:
            continue
        slot = bc.slot if 1 <= bc.slot <= BENCH_CAPACITY else None
        if slot is not None and bench[slot - 1] is None:
            bench[slot - 1] = bc
        else:
            # 冲突回退首空槽 = 归一修复(输入槽号重复/越界),非覆盖真值;
            # 但禁静默:重复槽号本应被写回健康门拒绝(cw_reconcile/prep_
            # actions),走到这里是门被绕过的信号,warning 显影供排障。
            _idx = bench_place(bench, bc)
            log.warning(f'[cw!] bench_from_compact 槽号冲突回退首空槽'
                        f'(输入槽号重复/越界,禁静默显影):'
                        f'slot={bc.slot} char={bc.char_id!r} → 实落槽'
                        f'{(_idx + 1) if _idx is not None else "无(席满丢弃)"}')
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


def iter_deployed_slots(deployed: list[BenchChar | None]):
    """迭代 (槽位下标, 占用角色) 对(滤 None)——deployed_idx 生成端用
    (索引 = 槽位下标,生成期=执行期恒稳,ADR-0392)。"""
    return ((i, d) for i, d in enumerate(deployed) if d is not None)
