"""货币战争 投资环境经济估值(单一入口;2026-09-12 invest-env 迭代,design.md §2.2.3)。

职责:把 ``cw_investments.ENV_ECONOMY`` 的整局经济通道折成**金等价期望**
``(expected_gold, resolved)``——resolved=False = fail-closed(未入模/估算参数
缺失/CI 方向不闭合/剩余期望为 0),消费端按无经济通道处理(design §2.3 门 3:
``resolved ∧ expected_gold > 0`` 才进经济域带;fail-closed 恒返 (0.0, False),
半值禁出,防消费端误读)。

**剩余价值口径**(design §2.2.3):从 bs 当前位面/轮次起算到局终——开局选卡
= 全局期望,局内重发环境 = 剩余期望,同一函数自然覆盖。当前位面已确定到达
(权恒 1.0,零参数),严格未来位面权 = 估算注册表 P(位面可达)(全局无条件
到达率;条件化 P(可达|已至当前) 更准,样本切片归数据批,v1 取无条件值 =
条件值的下界,低估不高估)。

**宪法对账**(design §2.5):A 类 = 【注】游戏定义值(cw_invest_data 原文直读)
+ 【推】位面到达加权;B/C 类 = 【拟】估算(值+CI+来源+截止,fail-closed 门);
零位面字面量(位面仅作通道索引/到达权重键,宪法第 2 条);无开关(回滚
git revert,strategy-work §3)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_investments import get_env

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_board_state import BoardState

# XP↔金兑换率(用户裁定 2026-09-08 暂定 1:1;design §2.2.3——定谳推翻改这一处,
# 按「未证即退役」处置该折算)
XP_GOLD_RATE: float = 1.0

# 估算参数键约定:位面到达 = plane_arrival_p{位面}(P2/P3;design §2.2.4
# 需估参数清单「P(位面 2/3 可达)」)。3.2 结构在册、值缺省 → 相关通道
# fail-closed;3.3 数据批落表后自动恢复。
_PLANE_ARRIVAL_KEY = 'plane_arrival_p{}'

# 取卡序→位面结构映射(k 1 基;策略大师通道 P(第 k 张策略可取) 的位面归属)。
# 【推】结构:k1 = 开局取卡(entry 流程固定,局首)、k2 = P1 中段首取卡
# (screen_flow_timing #11:1-3 节点完成后)、k3 = P2 前段(63 局
# decisions.jsonl 观测拼版主位 (2,2);sim 注入日程 SIM_STRATEGY_PICK_SCHEDULE
# 同源观察——注释引用不 import,kernel 禁依 sim)。
# 基线取卡基数 = 本表长度【推·效果原文序数】(details/env-value-models.md
# §2.2.2:头彩点名「第一个投资策略」/尾彩点名「第三个投资策略」→ 固定取卡集
# 基数 3;策略大师/联席的 3-5 节点「额外」取卡不计——策略域价值非经济通道,
# design §2.2.1)。
# design §2.2.3 的「位面节点表中的投资策略节点序」在本模块的承载面 = 本表:
# 节点行注册表(cw_node_reader 战斗/补给/遭遇/奖励四模板 + boss 位置判)无
# invest 槽型——取卡是绑定节点进入的 overlay 事件,不在节点行圆槽内,禁伪装
# 节点表直读;本表即「取卡结构」单一源,演化(实采定位)只改此处。
_STRATEGY_PICK_PLANES: tuple[int, ...] = (1, 1, 2)


@dataclass(frozen=True)
class EconomyEstimate:
    """【拟】估算参数(design.md §2.2.4 注册表条目形;00_framework 数字三形态)。

    ci 两端点参与 fail-closed 方向检验:端点重算 expected_gold ≤ 0(金期望
    方向翻转)→ resolved=False。source/cutoff = 数据来源与统计截止申报
    (数据批义务,design §2.2.4)。
    """
    value: float
    ci: tuple[float, float]
    source: str
    cutoff: str


#: 估算注册表(3.2 空表在册 = 位面到达率与 B/C 参数 3.3 数据批落表前的
#: 显式缺参态;消费面(缺参 → resolved=False)由 env_economy_value 承载,
#: E2 锁按注入口径验证,不依赖本表现值)。
ENV_ECONOMY_ESTIMATES: dict[str, EconomyEstimate] = {}


def _current_plane_round(bs: BoardState) -> tuple[int, int]:
    """当前(位面, 轮次)。

    开局环境帧的 bs = 裸 BoardState 桩(cw_screen_invest_env 直构),node
    未写 → 按局首 (1, 1) 语义评估:env 3 选 1 消费帧中 node 缺读只发生在
    开局桩形(design §2.3 门 3 消费位),剩余口径的局首退化 = 全局期望。
    """
    node = bs.node.value
    if node is None:
        return (1, 1)
    return (int(node.plane), int(node.round_num))


def _arrival_weight(plane: int, cur_plane: int) -> tuple[float, float, float] | None:
    """位面从当前帧起的可达权 ``(点值, CI低, CI高)``;缺参 → None(fail-closed)。

    当前位面已确定到达(权恒 1,零参数);既往位面权 0;严格未来位面 =
    估算注册表 P(位面可达),CI 端点夹 [0,1] 后供方向检验。
    """
    if plane < cur_plane:
        return (0.0, 0.0, 0.0)
    if plane == cur_plane:
        return (1.0, 1.0, 1.0)
    est = ENV_ECONOMY_ESTIMATES.get(_PLANE_ARRIVAL_KEY.format(plane))
    if est is None:
        return None

    def _clamp(v: float) -> float:
        return min(1.0, max(0.0, float(v)))

    return (_clamp(est.value), _clamp(est.ci[0]), _clamp(est.ci[1]))


def env_economy_value(name: str, bs: BoardState) -> tuple[float, bool]:
    """环境经济通道金等价期望(单一入口;design.md §2.2.3)。

    返回 ``(expected_gold, resolved)``;resolved=False = fail-closed
    (未入模 / 估算参数缺失 / CI 方向不闭合 / B/C 通道公式未落 / 剩余期望
    为 0),消费端按无经济通道处理。

    通道(design §2.2.1 A 类四条,值全部为注册表游戏定义【注】):
    - gold_instant:选卡当场一次性金(零参数,精确);
    - gold_per_plane_start:每位面开局金 × 位面可达权(剩余口径:既往位面
      不计;当前位面仅在开局轮(轮次 ≤ 1)可领——位面开局发放发生在轮 1 之前);
    - xp_after_level:节点数 × 每节点 XP × XP_GOLD_RATE(「升 8 必然发生」
      假设在册,v1 全额,不随剩余位面折扣——假设本身已承担心);
    - gold_per_strategy_coef:``Σ_k coef×(k−1)×P(第 k 张策略可取)``,k = 剩余
      取卡序(已持有数起、基线取卡基数止),P(k) = 取卡所在位面的可达权
      (_STRATEGY_PICK_PLANES 结构表)。

    fail-closed 门(design §2.2.4 参数级):所有消费参数按 CI 两端点重算
    expected_gold,任一端点 ≤ 0(金期望方向翻转/含 0)→ resolved=False。
    结构性注记:A 类精确通道带参数无关分量(如增发货币位面 1 权恒 1)时,
    CI 含 0 的参数**不会**触发翻转——方向仍被确定分量钉住,这正是参数级门
    的语义(不确定度只辖参数依赖部分);E2 锁的翻转构造因此走「全部剩余
    期望都参数依赖」的帧(策略大师 held=2 后唯一剩余取卡在位面 2)。
    """
    env = get_env(name)
    if env is None or env.economy is None:
        return (0.0, False)
    eff = env.economy
    if (eff.gold_after_refreshes is not None or eff.refresh_cost_after is not None
            or eff.reward_node_bonus != 0.0):
        # B/C 通道在表而估值公式未落(3.3 数据批):fail-closed,禁静默零值
        # 当 resolved(消费端按无经济通道处理,退裸分——缺参消化口径,
        # landing §3.2「B/C 参数 3.3 落表前按 resolved=False 消化缺参」)。
        return (0.0, False)

    cur_plane, cur_round = _current_plane_round(bs)
    acc = [0.0, 0.0, 0.0]   # (点值, CI低, CI高)
    params_missing = False

    def _acc(term: tuple[float, float, float]) -> None:
        acc[0] += term[0]
        acc[1] += term[1]
        acc[2] += term[2]

    # 通道 1:选卡当场一次性金(精确,零参数)
    if eff.gold_instant:
        _acc((float(eff.gold_instant), float(eff.gold_instant), float(eff.gold_instant)))
    # 通道 2:位面开局金(增发货币;元组下标 = 位面−1)
    for _idx, _g in enumerate(eff.gold_per_plane_start):
        if not _g:
            continue
        _plane = _idx + 1
        if _plane < cur_plane or (_plane == cur_plane and cur_round > 1):
            continue   # 既往位面/本位面开局已过 → 该笔发放不可再领
        _w = _arrival_weight(_plane, cur_plane)
        if _w is None:
            params_missing = True
            continue
        _acc((_g * _w[0], _g * _w[1], _g * _w[2]))
    # 通道 3:XP 通道(成功经验;假设与折算率见 schema/模块注)
    if eff.xp_after_level is not None:
        _nodes, _per_xp = eff.xp_after_level[1], eff.xp_after_level[2]
        _xg = _nodes * _per_xp * XP_GOLD_RATE
        _acc((_xg, _xg, _xg))
    # 通道 4:策略大师(Σ_k coef×(k−1)×P(k);k = 剩余取卡序,1 基)
    if eff.gold_per_strategy_coef:
        _held = len(bs.active_strategies.value or [])
        for _k in range(_held + 1, len(_STRATEGY_PICK_PLANES) + 1):
            _w = _arrival_weight(_STRATEGY_PICK_PLANES[_k - 1], cur_plane)
            if _w is None:
                params_missing = True
                continue
            _gain = eff.gold_per_strategy_coef * (_k - 1)
            _acc((_gain * _w[0], _gain * _w[1], _gain * _w[2]))

    if params_missing:
        return (0.0, False)
    if acc[1] <= 0.0 or acc[2] <= 0.0:
        # fail-closed 门:CI 任一端点重算 ≤ 0 = 金期望方向不闭合(design §2.2.4)
        return (0.0, False)
    return (acc[0], True)
