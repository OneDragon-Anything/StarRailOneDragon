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

**通道分型**(design §2.2.1):
- A 类精确:游戏定义值直算(增发货币/蓝海/成功经验/策略大师);
- B 类使用模型:公式结构游戏定义,概率/期望参数进估算注册表(长线利好/
  二手市场;刷新分布参数数据批 = tools/cw/env_economy_estimates.py);
- C 类估算:效果无数值(「掉落更多战利品」),每奖励节点期望增益进估算
  注册表(经济过热/经济严重过热;当前零有效估计 → fail-closed 裸分维持)。

**宪法对账**(design §2.5):A 类 = 【注】游戏定义值(cw_invest_data 原文直读)
+ 【推】位面到达加权;B/C 类 = 【拟】估算(值+CI+来源+截止,fail-closed 门);
零位面字面量(位面仅作通道索引/到达权重键,宪法第 2 条);无开关(回滚
git revert,strategy-work §3)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_investments import (
    ENV_POOL_REWRITE,
    get_env,
)
from sr_od.application.currency_war.kernel.cw_vocab import REFRESH_COST_BASE

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import GameState

# XP↔金兑换率(用户裁定 2026-09-08 暂定 1:1;design §2.2.3——定谳推翻改这一处,
# 按「未证即退役」处置该折算)
XP_GOLD_RATE: float = 1.0

# ===== 估算参数键约定(单一源;数据批 = tools/cw/env_economy_estimates.py)=====
# 位面到达 = plane_arrival_p{位面}(P2/P3;design §2.2.4 需估参数清单①)。
_PLANE_ARRIVAL_KEY = 'plane_arrival_p{}'
# 刷新阈值概率 = refresh_{scope}_ge{阈值}_p(design §2.2.4 需估参数②的
# P(达 20)/P(达 30));scope ∈ {total, paid} 对齐统一 state 计数载体:
# total = 累计全部刷新(total_refresh_count,二手市场「商店刷新20次后」)、
# paid = 累计付费刷新(paid_refresh_count,长线利好「花费金币进行30次刷新」)。
# 数据批口径 = 逐局 RefreshShop 动作计数,cost>0 记付费
# (细则 = changes/2026-09-12-invest-env/details/data-batch-estimates.md)。
_REFRESH_P_KEY = 'refresh_{}_ge{}_p'
# 刷新条件后继期望 = refresh_{scope}_after{阈值}_e = E[(N−阈值)+ | N≥阈值]
# (design §2.2.4 需估参数②的 E(达 30 后继刷新次数);长线利好刷价节省项用)。
_REFRESH_AFTER_KEY = 'refresh_{}_after{}_e'
# C 类扑满化增益 = reward_node_bonus_{变体}(design §2.2.4 需估参数③)。
_REWARD_BONUS_KEY = 'reward_node_bonus_{}'

# C 类环境 → 增益参数变体映射(单一源;新 C 类环境先落映射再落参,漏映射
# 由 _validate_estimates_governance 炸出——否则参数查询恒 miss,通道静默
# fail-closed 变哑炮)。
_REWARD_BONUS_VARIANTS: dict[str, str] = {
    '经济过热': 'normal',
    '经济严重过热': 'super',
}

# 奖励节点槽位结构先验(【拟】对局档案众数结构,数据批 2026-09-12;样本量与
# 槽位变异性申报 = changes/2026-09-12-invest-env/details/data-batch-estimates.md)。
# (位面, 轮次) 1 基;P3 结构零样本不计 = 视界保守低估(模板在册后补)。
_REWARD_SLOTS: tuple[tuple[int, int], ...] = ((1, 1), (1, 2), (1, 8), (2, 6))

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
    (数据批义务,design §2.2.4;重采 = 重跑 tools/cw/env_economy_estimates.py
    后手工更新本表,值只落代码不自动回写)。
    """
    value: float
    ci: tuple[float, float]
    source: str
    cutoff: str


#: 估算注册表(design.md §2.2.4;值/CI/来源/截止 = 2026-09-12 数据批,样本与
#: 滤波规则见 details/data-batch-estimates.md——完成局 n=114、Wilson 95% 区间、
#: 比例值 4 位舍入)。**不落参数申报**(零样本/零有效估计,禁拍值;缺位 =
#: 相关通道 fail-closed 裸分维持,补数据缩区间后自动恢复):
#: - refresh_paid_after30_e:E[(N−30)+ | N≥30] 条件子样本 n=0,条件期望无定义
#:   → 长线利好 fail-closed(refresh_paid_ge30_p 点值 0 本身也已钉死方向);
#: - reward_node_bonus_normal/super:扑满局在册(经济过热 ×7 + 经济严重过热
#:   ×1)但遥测无扑满战利品独立字段,奖励轮收支差分混入备战净支出,增益不可
#:   分离 → 经济过热/经济严重过热 fail-closed(补采建议见口径文档)。
ENV_ECONOMY_ESTIMATES: dict[str, EconomyEstimate] = {
    # —— 位面到达率(design §2.2.4 需估参数①;完成局命中 110/114 与 10/114)——
    'plane_arrival_p2': EconomyEstimate(
        value=0.9649, ci=(0.9132, 0.9863),
        source='对局档案遥测 146 局(完成局 114)endgame.plane_reached;'
               ' tools/cw/env_economy_estimates.py,Wilson 95%',
        cutoff='2026-09-12'),
    'plane_arrival_p3': EconomyEstimate(
        value=0.0877, ci=(0.0483, 0.1540),
        source='对局档案遥测 146 局(完成局 114)endgame.plane_reached;'
               ' tools/cw/env_economy_estimates.py,Wilson 95%',
        cutoff='2026-09-12'),
    # —— 刷新次数分布(design §2.2.4 需估参数②;只落有消费通道的键)——
    'refresh_total_ge20_p': EconomyEstimate(
        value=0.0088, ci=(0.0016, 0.0480),
        source='对局档案逐局 RefreshShop 动作计数(完成局 114;总口径);'
               ' tools/cw/env_economy_estimates.py,Wilson 95%',
        cutoff='2026-09-12'),
    'refresh_paid_ge30_p': EconomyEstimate(
        value=0.0, ci=(0.0, 0.0326),
        source='对局档案逐局 RefreshShop 动作计数(完成局 114;付费口径'
               ' cost>0,零命中); tools/cw/env_economy_estimates.py,Wilson 95%',
        cutoff='2026-09-12'),
}

# 「待建模」在册(design §2.2.4:显式区别于「漏登记」):有经济语义、v1 无
# 参数化模型的环境。在册即消费端恒 (0.0, False)(fail-closed);不入
# ENV_ECONOMY(无通道字段可装,双登记由 _validate_estimates_governance 拒绝);
# 补出参数化模型后迁 ENV_ECONOMY 并落参。
ENV_ECONOMY_PENDING_MODELING: dict[str, str] = {
    # 刷新概率结构翻倍:概率面已在 cw_shop_odds 在册,金等价参数化缺失
    '轮岗': '刷新概率结构翻倍(概率面 cw_shop_odds 在册);金等价参数化缺失',
    # 商店 2 星概率提升:需先查证 2★ 商店价结构,未查证不入(design §2.2.1)
    '人才下沉': '商店 2 星概率提升;需先查证 2★ 商店价结构,未查证不入',
}

# 假设/机制实采挂账(design §2.2.1 假设登记行的验证项在册;实采定谳前按
# 在册假设建模,证伪即按各条处置改)。
ENV_ECONOMY_PENDING_VERIFICATION: dict[str, str] = {
    # 增发货币通道按「晶矿自动开启」建模;晶矿开启是玩家动作面(战技点契约
    # 「打开20个晶矿后」为存在玩家动作的佐证),自动与否未实采。证非自动 →
    # bot 具备开矿动作前 gold_per_plane_start 通道应 fail-closed(届时改
    # env_economy_value 的该通道前置)。
    '增发货币晶矿自动开启':
        'gold_per_plane_start 按晶矿自动开启建模(未实采);'
        '证非自动 → bot 具备开矿动作前该通道 fail-closed',
}


def _current_plane_round(bs: GameState) -> tuple[int, int]:
    """当前(位面, 轮次)。

    开局环境帧的 bs = 裸 GameState 桩(cw_screen_invest_env 直构),node
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


def _remaining_reward_nodes(cur_plane: int, cur_round: int) -> float | None:
    """当前帧起的剩余期望奖励节点数(C 类通道视界因子);到达缺参 → None。

    槽位结构 = _REWARD_SLOTS 众数先验:未来位面槽按位面到达权折算,当前
    位面只数轮次 ≥ 当前的槽(含当前轮 = 本节点正在兑现)。位面内槽位变异
    (众数外的合法偏离,见口径文档)不建模,v1 申报。
    """
    total = 0.0
    for _p, _r in _REWARD_SLOTS:
        if _p < cur_plane or (_p == cur_plane and _r < cur_round):
            continue
        _w = _arrival_weight(_p, cur_plane)
        if _w is None:
            return None
        total += _w[0]
    return total


def env_economy_value(name: str, bs: GameState) -> tuple[float, bool]:
    """环境经济通道金等价期望(单一入口;design.md §2.2.3)。

    返回 ``(expected_gold, resolved)``;resolved=False = fail-closed
    (未入模 / 估算参数缺失 / CI 方向不闭合 / 剩余期望为 0),消费端按无
    经济通道处理。

    **品质改写分派**(3.6,details/env-value-models.md §2.2.5):name ∈
    ENV_POOL_REWRITE → :func:`_pool_rewrite_value`(层 E ΔV 公式,读
    STRAT_POOL_ECON_MEANS/OFFER_QUALITY_DIST,任一缺参 fail-closed,
    v1 恒然——受限通道 μ_E 非单调,层 E 转正须过准入门后落参);其余
    name → 下方 A/B/C 通道公式。单一入口契约不变(design §2.2.3;
    ENV_ECONOMY 与 ENV_POOL_REWRITE 构建期互斥,一个 name 至多落一个
    估值结构,cw_investments._validate_env_pool_rewrite 收全)。

    通道(design §2.2.1;值除注明外全部为注册表游戏定义【注】):
    - gold_instant:选卡当场一次性金(零参数,精确);
    - gold_per_plane_start:每位面开局金 × 位面可达权(剩余口径:既往位面
      不计;当前位面仅在开局轮(轮次 ≤ 1)可领——位面开局发放发生在轮 1 之前;
      晶矿自动开启假设见 ENV_ECONOMY_PENDING_VERIFICATION 在册条);
    - xp_after_level:节点数 × 每节点 XP × XP_GOLD_RATE(「升 8 必然发生」
      假设在册,v1 全额,不随剩余位面折扣——假设本身已承担心);
    - gold_per_strategy_coef:``Σ_k coef×(k−1)×P(第 k 张策略可取)``,k = 剩余
      取卡序(已持有数起、基线取卡基数止),P(k) = 取卡所在位面的可达权
      (_STRATEGY_PICK_PLANES 结构表);
    - gold_after_refreshes(B 类):P(累计刷新达阈值)× 返金。付费/总分型 =
      refresh_cost_after 在场判(在场 = 长线利好「花费金币进行30次刷新」付费
      阈值,读 bs.paid_refresh_count;否则 = 二手市场总阈值,读
      bs.total_refresh_count)。计数 ≥ 阈值 → P=1(选中即触发按立即结算
      建模,未实采;开局桩形计数恒 0 不达);计数 None(未读)按 0(起始
      计数)。v1 用整局分布参数不按当前计数条件化——局内重发帧系统性高估,
      申报为近似(主要消费帧 = 开局三选一,整局参数即精确口径),条件化
      参数化归后续数据批;
    - refresh_cost_after(B 类刷价节省项,仅付费变价通道):P(达阈值) ×
      (基价−新价) × E(达阈值后继刷新次数)(_REFRESH_AFTER_KEY 条件期望);
    - reward_node_bonus(C 类):字段 = 通道在场哨兵(1.0),每奖励节点期望
      增益真值+CI 在估算注册表(按 _REWARD_BONUS_VARIANTS 变体分键);期望 =
      增益 × 剩余期望奖励节点数(_REWARD_SLOTS 槽位结构 × 位面到达权)。

    fail-closed 门(design §2.2.4 参数级):所有消费参数按 CI 两端点重算
    expected_gold,任一端点 ≤ 0(金期望方向翻转/含 0)→ resolved=False。
    结构性注记:A 类精确通道带参数无关分量(如增发货币位面 1 权恒 1)时,
    CI 含 0 的参数**不会**触发翻转——方向仍被确定分量钉住,这正是参数级门
    的语义(不确定度只辖参数依赖部分);E2 锁的翻转构造因此走「全部剩余
    期望都参数依赖」的帧(策略大师 held=2 后唯一剩余取卡在位面 2)。
    """
    if name in ENV_POOL_REWRITE:
        return _pool_rewrite_value(name, bs)
    env = get_env(name)
    if env is None or env.economy is None:
        return (0.0, False)
    eff = env.economy
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
    # 通道 5:B 类刷新阈值(gold_after_refreshes;付费/总分型见 docstring)
    if eff.gold_after_refreshes is not None:
        _th, _refund = eff.gold_after_refreshes
        _scope = 'paid' if eff.refresh_cost_after is not None else 'total'
        _count = (bs.paid_refresh_count if _scope == 'paid'
                  else bs.total_refresh_count).value
        _cur = int(_count or 0)
        if _cur >= _th:
            _pw: tuple[float, float, float] | None = (1.0, 1.0, 1.0)
        else:
            _p = ENV_ECONOMY_ESTIMATES.get(_REFRESH_P_KEY.format(_scope, _th))
            _pw = None if _p is None else (_p.value, _p.ci[0], _p.ci[1])
        if _pw is None:
            params_missing = True
        else:
            _acc((_pw[0] * _refund, _pw[1] * _refund, _pw[2] * _refund))
            # 刷价节省项(仅付费变价通道;E(后继刷新) = 条件期望注册表参数;
            # 项 CI = P 端点 × E 端点,非负因子乘积的单调区间)
            if eff.refresh_cost_after is not None:
                _save = REFRESH_COST_BASE - eff.refresh_cost_after[1]
                _e = ENV_ECONOMY_ESTIMATES.get(
                    _REFRESH_AFTER_KEY.format(_scope, _th))
                if _e is None:
                    params_missing = True
                else:
                    _acc((_pw[0] * _save * _e.value,
                          _pw[1] * _save * _e.ci[0],
                          _pw[2] * _save * _e.ci[1]))
    # 通道 6:C 类扑满化增益(reward_node_bonus 哨兵;变体分键见 docstring)
    if eff.reward_node_bonus:
        _variant = _REWARD_BONUS_VARIANTS.get(env.name)
        _b = (ENV_ECONOMY_ESTIMATES.get(_REWARD_BONUS_KEY.format(_variant))
              if _variant else None)
        _nodes = _remaining_reward_nodes(cur_plane, cur_round)
        if _b is None or _nodes is None:
            params_missing = True
        else:
            _acc((_b.value * _nodes, _b.ci[0] * _nodes, _b.ci[1] * _nodes))

    if params_missing:
        return (0.0, False)
    if acc[1] <= 0.0 or acc[2] <= 0.0:
        # fail-closed 门:CI 任一端点重算 ≤ 0 = 金期望方向不闭合(design §2.2.4)
        return (0.0, False)
    return (acc[0], True)


# 经济域带归一上界(design §2.3;3.5 汇合集成消费:域带 =
# ECON_ENGINE_BAND_BASE + SPAN × min(value, NORM)/NORM)。取整注册推导:
# 2026-09-12 数据批落地参数下,ENV_ECONOMY 全环境开局期望最大 = 成功经验 36
# (3×12×XP_GOLD_RATE=1.0;次大 = 增发货币 14.77)→ 取整上界 40。域界非拍值:
# 越界(重采推高参数/XP_GOLD_RATE 改判)由 _validate_estimates_governance
# 构建校验炸出,强制重新注册本上界。
ECON_VALUE_NORM: float = 40.0


def _validate_estimates_governance() -> None:
    """估算治理构建校验(import 即炸;design §2.2.4/§2.3):

    ① C 类哨兵条目必须有变体键映射(漏映射 = 参数查询恒 miss,通道静默
    fail-closed 变哑炮);② 「待建模」在册环境必须真实存在(∈
    INVESTMENT_ENVS)且不与 ENV_ECONOMY 双登记(单一环境只落一个估值口径);
    ③ ECON_VALUE_NORM 值域上界:任一经济环境开局期望 > NORM = 注册表演化
    越界(重采推高/折算率改判)→ 炸出强制重新注册(design §2.3「越界值
    注册表校验炸出」)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import GameState
    from sr_od.application.currency_war.kernel.cw_investments import (
        ENV_ECONOMY,
        INVESTMENT_ENVS,
    )

    for _env_name, _eff in ENV_ECONOMY.items():
        if _eff.reward_node_bonus and _env_name not in _REWARD_BONUS_VARIANTS:
            raise ValueError(
                f"C 类哨兵条目缺变体映射(参数查询将恒 miss):{_env_name!r}")
    for _name in ENV_ECONOMY_PENDING_MODELING:
        if _name not in INVESTMENT_ENVS:
            raise ValueError(f"待建模在册孤儿键(注册表无此环境):{_name!r}")
        if _name in ENV_ECONOMY:
            raise ValueError(f"待建模环境与 ENV_ECONOMY 双登记:{_name!r}")
    _bs = GameState(schema_version=1)
    for _env_name in ENV_ECONOMY:
        _v, _ok = env_economy_value(_env_name, _bs)
        if _ok and _v > ECON_VALUE_NORM:
            raise ValueError(
                f"经济环境开局期望越 ECON_VALUE_NORM 上界({ECON_VALUE_NORM}):"
                f"{_env_name!r} = {_v:.4f}——注册表演化,重新取整注册上界")


_validate_estimates_governance()


# ===== 品质改写型层 E(ΔV 公式;2026-09-12 invest-env 迭代 3.6,
# details/env-value-models.md §2.2.2/§2.2.5)=====
# ΔV(R) = Σ_{k ∈ picks(R)} [ μ_E(q_R; H_k) − Σ_q π_offer,k(q) · μ_E(q; H_k) ]
# 层 E = 改写后取卡金流期望相对无改写 offer 的抬升(受限直接金流/XP 通道;
# 明确排除刷新族/息档覆写/合成卖价/血本位等行为依赖通道,排除集清单 =
# 详设 §2.2.2 econ_gold_v1 定义)。**转正判定的当前态 = fail-closed**:受限
# 通道实测 μ_E 不随品质单调(银 3.31 > 金 2.42),直入域带会产出病态序;
# 转正准入门 = ①全通道重算(排除集补参)+ ②序一致性检验,两条件缺一不入
# (详设 §2.2.2)。数据批已执行判定:第 1 条完成,第 2 条未过(全通道 μ_E
# 点估计 银≥金 残差未翻转)→ 两参数表维持哨兵不落,本段行为零变化;判定
# 依据、读数与回炉候选 = changes/2026-09-12-invest-env/details/
# layer-e-promotion-batch.md,重采入口 = tools/cw/env_pool_rewrite_estimates.py。
# 消费端(design §2.3 门 3 的 resolved ∧ expected_gold > 0)自动承载准入门
# 第 2 条方向自洽。

#: 取卡序 k(1 基,同 StrategyPoolRewrite.rewrite_picks 坐标系)→ 取卡后剩余
#: 节点视界 H_k。【拟·实采】档案取卡选定事件经 terminal_ts 时间夹逼到轮,
#: 全局节点号按结构日程 P1=9/P2=7/P3=9 先验(总 25;P2=7 = economy.md §10.2
#: 位面典型节点表 + boss@p2r7 档案实证),H = 25 − 已完成节点数:H_1=23
#: (落点 85/86 局在 P1 r3)、H_2=15(69/72 局在 P2 r2);取卡序 3 的有效
#: 样本 n=3 低于注册门 20 → 哨兵不落,时代/尾彩通道因 H_3 缺参 fail-closed。
#: 重采入口 = tools/cw/env_pool_rewrite_estimates.py(实采定位演化只改本表;
#: 口径与样本量 = changes/2026-09-12-invest-env/details/
#: layer-e-promotion-batch.md)。v1 在册值 24 系日程回退口径(9+9+9)下的
#: 参照值,被本实采取代。
_STRAT_PICK_HORIZONS: dict[int, int] = {1: 23, 2: 15}

#: μ_E per (品质, 视界):品质子池受限通道金流均值(【拟】,EconomyEstimate
#: 四元组,总纲 §2.2.4 注册表条目形同构;键第二维 = H_k,公式 μ_E(q; H)
#: 视界入参化的直接承载)。品质键 = 注册表品质名('棱彩'/'金'/'银')。
#: **不落参数申报(转正数据批判定:准入门未过)**:全通道重算与序一致性
#: 检验已执行(重采入口 = tools/cw/env_pool_rewrite_estimates.py;口径/
#: 样本量/读数 = changes/2026-09-12-invest-env/details/
#: layer-e-promotion-batch.md)——第 1 条(全通道补参)完成,第 2 条未过:
#: 全通道 μ_E 点估计 银≥金 残差(H=23 +0.010 / H=15 +0.097,深居卡池抽样
#: 噪声,成对差值 CI 全含 0),按详设 §2.2.2 裁决维持 fail-closed,本表
#: 继续哨兵不落;序一致性复过且取卡序 3 视界/π 缺位补齐后随批落参。
#: 缺位 = 恒 fail-closed,时代/头彩/尾彩维持裸分(现行为零变化)。
STRAT_POOL_ECON_MEANS: dict[tuple[str, int], EconomyEstimate] = {}

#: π_offer per 取卡序:无改写环境时第 k 次取卡的 offer 品质分布(【拟】;
#: 键 = k 1 基,值 = 品质 → EconomyEstimate。「未解析」份额不单列建模,
#: 入式前按已知三品质份额归一,归一口径随数据批申报)。缺位该 k =
#: 缺参 fail-closed。**不落参数申报(与 μ 表同判,准入门未过)**:k=1/k=2
#: 归一读数在案(银/金/棱彩 = 0.302/0.498/0.199 与 0.305/0.457/0.238,
#: 净流匹配 105/76 帧组),取卡序 3 有效帧组 n=3 哨兵不落;落参时机 =
#: STRAT_POOL_ECON_MEANS 表注所述准入门复过之后,两表同批。
OFFER_QUALITY_DIST: dict[int, dict[str, EconomyEstimate]] = {}


def _pool_rewrite_value(name: str, bs: GameState) -> tuple[float, bool]:
    """品质改写型层 E 增量期望(ΔV;入口 = env_economy_value 分派,§2.2.5)。

    ΔV(R) = Σ_{k ∈ picks(R)} [ μ_E(q_R; H_k) − Σ_q π_offer,k(q) · μ_E(q; H_k) ]

    - rewrite_quality 空(银·金·彩 = 结构改写/联席决策 = 数量通道)= 无层 E
      语义 → 结构性 fail-closed(非缺参:即使参数表全满也 False——数量通道
      不折金与 A 类策略大师同口径 §2.2.4,价值由裸分承载);
    - 缺参 fail-closed:H_k / μ_E(q_R, H_k) / π_offer,k / μ_E(q, H_k) 任一
      查表 miss → (0.0, False)(v1 恒然:两参数表空);
    - CI 端点传播:基线项 Σ π·μ = 非负因子乘积和,端点 = Σ 端点积(单调
      区间,既有通道 P×E 端点同口径);ΔV_k = μ_R − base 区间差
      [μ_R.lo − base.hi, μ_R.hi − base.lo];多项 picks 端点相加(同号区间
      相加精确);
    - 方向门:CI 任一端点 ≤ 0 → (0.0, False)(与 A/B/C 通道同门;消费端
      design §2.3 门 3 再加 expected_gold > 0——白银时代即使转正也因
      ΔV ≤ 0 落回裸分,方向自洽)。

    bs 参数:层 E v1 用全局先验视界(_STRAT_PICK_HORIZONS),不做剩余口径
    条件化(H_k 随当前帧修正 = 转正数据批的参数化面);bs 保留于签名 =
    单一入口契约形态一致,当前帧信息供转正批条件化使用。
    """
    rw = ENV_POOL_REWRITE[name]
    if not rw.rewrite_quality:
        return (0.0, False)
    acc = [0.0, 0.0, 0.0]
    for _k in rw.rewrite_picks:
        _h = _STRAT_PICK_HORIZONS.get(_k)
        if _h is None:
            return (0.0, False)
        _mu_r = STRAT_POOL_ECON_MEANS.get((rw.rewrite_quality, _h))
        _pi_k = OFFER_QUALITY_DIST.get(_k)
        if _mu_r is None or _pi_k is None:
            return (0.0, False)
        _base = [0.0, 0.0, 0.0]
        for _q, _pi in _pi_k.items():
            _mu_q = STRAT_POOL_ECON_MEANS.get((_q, _h))
            if _mu_q is None:
                return (0.0, False)
            _base[0] += _pi.value * _mu_q.value
            _base[1] += _pi.ci[0] * _mu_q.ci[0]
            _base[2] += _pi.ci[1] * _mu_q.ci[1]
        acc[0] += _mu_r.value - _base[0]
        acc[1] += _mu_r.ci[0] - _base[2]
        acc[2] += _mu_r.ci[1] - _base[1]
    if acc[1] <= 0.0 or acc[2] <= 0.0:
        return (0.0, False)
    return (acc[0], True)
