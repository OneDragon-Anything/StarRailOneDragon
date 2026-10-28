"""货币战争 投资环境经济通道折算(策略层估值;自 kernel/cw_env_economy.py 迁入)。

归属(宪法五:框架层只留游戏原始真值,衍生估值归策略层):本模块承载
**策略层的衍生估值**——把 ``cw_investments.ENV_ECONOMY`` 的整局经济通道
折成金等价期望。kernel 侧只留游戏原始真值 ``cw_investments.ENV_ECONOMY``
(通道结构 = 游戏效果原文的结构化,【注】);``ENV_ECONOMY_PENDING_
MODELING`` 亦驻本模块(下方「待建模」已登记段)——「留 kernel 不迁」系
早期过时表述,以代码体为准。语义正本 = strategy-docs/28_invest_env_
screen.md §2 现金分行;迁移批的删除面对照

迁入改造(迁移迭代 3.1):
- 删 ``ECON_VALUE_NORM`` 域带归一:现金分直接按金等价计,不再进 111-119
  带;治理校验随之删除「域带上界越界」项(无域带则该项无语义);
- ``gold_after_refreshes`` 系(长线利好/二手市场)不走运行时条件分支——
  不读 ``gs.effects`` 刷新计数、不消费 refresh_p/refresh_after 估算参数,
  改为拍值注册(:data:`_GOLD_AFTER_REFRESHES_FIXED`;拍值锚定 =
  docs/develop/sr_od/application/currency_war/proofs/p97-refresh-budget.md
  §7 消费契约,下称 P97 §7;历史频率参数 refresh_total_ge20_p/
  refresh_paid_ge30_p 随拍值注册停用,P97 §7);
- 其余 A/B/C 通道公式、fail-closed 门、估算注册表、C 类治理校验原样保留。

职责:经济通道折成**金等价期望** ``(expected_gold, resolved)``——
resolved=False = fail-closed(未入模/估算参数缺失/CI 方向不闭合/剩余期望
为 0),消费端按无经济通道处理(28 号稿 §1:``resolved ∧ expected_gold
> 0`` 才计现金分;fail-closed 恒返 (0.0, False),半值禁出,防消费端误读)。

**剩余价值口径**(沿原 kernel 模块):从 gs 当前位面/轮次起算到局终——
开局选卡 = 全局期望,局内重发环境 = 剩余期望,同一函数自然覆盖。当前
位面已确定到达(权恒 1.0,零参数),严格未来位面权 = 估算注册表
P(位面可达)(全局无条件到达率;条件化 P(可达|已至当前) 更准,样本切片
归数据批,v1 取无条件值 = 条件值的下界,低估不高估)。

**通道分型**(沿原 kernel 模块):
- A 类精确:游戏定义值直算(增发货币/蓝海/成功经验/策略大师);
- B 类拍值:公式结构游戏定义(长线利好/二手市场),估值按拍值注册
  (P97 §7 消费契约;原「概率/期望参数进估算注册表」形态随拍值停用);
- C 类估算:效果无数值(「掉落更多战利品」),每奖励节点期望增益进估算
  注册表(经济过热/经济严重过热;当前零有效估计 → fail-closed)。

**宪法对账**:A 类 = 【注】游戏定义值(cw_invest_data 原文直读)+ 【推】
位面到达加权;C 类 = 【拟】估算(值+CI+来源+截止,fail-closed 门);拍值
= 用户裁定的平价实现形态(P97 §7「证明归证明,实现拍平价」);零位面
字面量(位面仅作通道索引/到达权重键);无开关(回滚 git revert,
strategy-work §3)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_investments import (
    ENV_POOL_REWRITE,
    get_env,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import GameState

# XP↔金兑换率(用户裁定 2026-09-08 暂定 1:1;28 号稿 §1 统一标尺锚——
# 「1 分 := 1 金等价」的 XP 侧承载。定案推翻改这一处,按「未证即停用」
# 处置该折算)
XP_GOLD_RATE: float = 1.0

# ===== 估算参数键约定(单一源;数据批 = tools/cw/env_economy_estimates.py)=====
# 位面到达 = plane_arrival_p{位面}(P2/P3;原 invest-env 迭代需估参数①)。
_PLANE_ARRIVAL_KEY = 'plane_arrival_p{}'
# C 类扑满化增益 = reward_node_bonus_{变体}(原 invest-env 迭代需估参数③)。
_REWARD_BONUS_KEY = 'reward_node_bonus_{}'

# (刷新分布两参数键 refresh_{scope}_ge{阈值}_p / refresh_{scope}_after{阈值}_e
#  随 gold_after_refreshes 拍值注册停用,不再约定——P97 §7 消费契约;
#  tools 重采脚本的对应重采面归 3.2 随 kernel 删除面一并处理。)

# C 类环境 → 增益参数变体映射(单一源;新 C 类环境先落映射再落参,漏映射
# 由 _validate_estimates_governance 炸出——否则参数查询恒 miss,通道静默
# fail-closed 变哑炮)。
_REWARD_BONUS_VARIANTS: dict[str, str] = {
    '经济过热': 'normal',
    '经济严重过热': 'super',
}

# 奖励节点槽位结构先验(【拟】对局档案众数结构,数据截至 2026-09-12;样本量与
# 槽位变异性申报 = invest-env data-batch-estimates 详设)。
# (位面,轮次) 1 基;P3 结构零样本不计 = 视界保守低估(模板已登记后补)。
_REWARD_SLOTS: tuple[tuple[int, int], ...] = ((1, 1), (1, 2), (1, 8), (2, 6))

# 取卡序→位面结构映射(k 1 基;策略大师通道 P(第 k 张策略可取) 的位面归属)。
# 【推】结构:k1 = 开局取卡(entry 流程固定,局首)、k2 = P1 中段首取卡
# (screen_flow_timing #11:1-3 节点完成后)、k3 = P2 前段(63 局
# decisions.jsonl 观测拼版主位 (2,2);旧 sim 注入日程
# SIM_STRATEGY_PICK_SCHEDULE 同源观察——该日程已删除(随sim 重做)面停用,
# 取卡时点 = 投资策略 offer 固定轮次日程,正本 = sim-design.md §2.2)。
# 基线取卡基数 = 本表长度【推·效果原文序数】(效果原文:
# 头彩点名「第一个投资策略」/尾彩点名「第三个投资策略」→ 固定取卡集
# 基数 3;策略大师/联席的 3-5 节点「额外」取卡不计——策略域价值非经济
# 通道,不入本折算)。
# 原 kernel 模块「位面节点表中的投资策略节点序」承载面 = 本表:节点行注册表
# (cw_node_reader 战斗/补给/遭遇/奖励四模板 + boss 位置判)无 invest 槽型
# ——取卡是绑定节点进入的 overlay 事件,不在节点行圆槽内,禁伪装节点表
# 直读;本表即「取卡结构」单一源,演化(实采定位)只改此处。
_STRATEGY_PICK_PLANES: tuple[int, ...] = (1, 1, 2)

# ===== gold_after_refreshes 拍值注册(28 号稿 §2 现金分行;用户裁定
# 2026-09-23「证明归证明,实现拍平价」)=====
# 键 = 环境注册表规范名,值 = 无条件计的金等价价值。可达性已由 P97 证明确
# 立,不读局内刷新计数(gs.effects.refresh_total/refresh_paid 不消费)、
# 不做按阵容预算分支(唯一例外阵容景元仙舟按拍值平摊 = 「拍一个价值」
# 语义的接受面,P97 §7)。改拍值先重跑 P97 脚本
# (tools/cw/proofs/p97_refresh_budget_check.py,P97 §7 消费契约)。
#: 二手市场 = 30:阈值 20 次总刷新,P97 实证 20/20 阵容可达 → 全局兑现,
#: 价值 = 返金 30(用户拍定);
#: 长线利好 = 50:阈值 30 次付费刷新,P97 均值 60.5 次/19-20 阵容可达 →
#: 价值 ≈ 返金 20 + 过阈值节省 ×(均值 60.5−30)≈ 50(裁决窗确认的建议值)。
_GOLD_AFTER_REFRESHES_FIXED: dict[str, float] = {
    '二手市场': 30.0,
    '长线利好': 50.0,
}


@dataclass(frozen=True)
class EconomyEstimate:
    """【拟】估算参数(原 invest-env 迭代注册表条目形;00_framework 数字三形态)。

    ci 两端点参与 fail-closed 方向检验:端点重算 expected_gold ≤ 0(金期望
    方向翻转)→ resolved=False。source/cutoff = 数据来源与统计截止申报
    (数据批义务;重采 = 重跑 tools/cw/env_economy_estimates.py 后手工更新
    本表,值只落代码不自动回写)。
    """
    value: float
    ci: tuple[float, float]
    source: str
    cutoff: str


#: 估算注册表(值/CI/来源/截止 = 2026-09-12 数据批,样本与滤波规则见
#: details/data-batch-estimates.md——完成局 n=114、Wilson 95% 区间、
#: 比例值 4 位舍入)。**不落参数申报**(零样本/零有效估计,禁拍值;缺位 =
#: 相关通道 fail-closed,补数据缩区间后自动恢复):
#: - reward_node_bonus_normal/super:扑满局已登记(经济过热 ×7 + 经济严重过热
#:   ×1)但遥测无扑满战利品独立字段,奖励轮收支差分混入备战净支出,增益不可
#:   分离 → 经济过热/经济严重过热 fail-closed(补采建议见口径文档)。
#: (refresh_total_ge20_p / refresh_paid_ge30_p 随 gold_after_refreshes 拍值
#: 注册停用,不再登记——P97 §7 消费契约。)
ENV_ECONOMY_ESTIMATES: dict[str, EconomyEstimate] = {
    # —— 位面到达率(原 invest-env 迭代需估参数①;完成局命中 110/114 与 10/114)——
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
}

# 「待建模」已登记(原 invest-env 迭代:显式区别于「漏登记」):有经济语义、
# v1 无参数化模型的环境。已登记即消费端恒 (0.0, False)(fail-closed);不入
# ENV_ECONOMY(无通道字段可装,双登记由 _validate_estimates_governance 拒绝);
# 补出参数化模型后迁 ENV_ECONOMY 并落参。表内含两类条目:待建模(候迁出)
# 与已定案按 0(用户裁定,永驻本表,消费端语义相同)——以条目文案为准。
ENV_ECONOMY_PENDING_MODELING: dict[str, str] = {
    # 刷新概率结构翻倍:概率面已在 cw_shop_odds 已登记,金等价参数化缺失
    '轮岗': '刷新概率结构翻倍(概率面 cw_shop_odds 在册);金等价参数化缺失',
    # 估值按 0 定案:2★ 商店价结构已定谳(merge_mechanics §2.6 ×3 实付),
    # sim 直出分支已建(kernel ENV_SHOP_TWO_STAR_DEAL_PROB,占位概率禁入估值)
    '人才下沉': '估值按 0 处理(2026-10-16 用户裁定:2★ 直出收益不计入现金分;'
                'sim 占位概率 ENV_SHOP_TWO_STAR_DEAL_PROB 禁入估值)——系定案,非待建模',
}

# 假设/机制实采的待验证登记(原 invest-env 迭代假设登记行的验证项已登记;实采定案前按
# 已登记假设建模,证伪即按各条处置改)。
ENV_ECONOMY_PENDING_VERIFICATION: dict[str, str] = {
    # 增发货币通道按「晶矿自动开启」建模;晶矿开启是玩家动作面(战技点契约
    # 「打开20个晶矿后」为存在玩家动作的佐证),自动与否未实采。证非自动 →
    # bot 具备开矿动作前 gold_per_plane_start 通道应 fail-closed(届时改
    # env_economy_value 的该通道前置)。
    '增发货币晶矿自动开启':
        'gold_per_plane_start 按晶矿自动开启建模(未实采);'
        '证非自动 → bot 具备开矿动作前该通道 fail-closed',
}


def _current_plane_round(gs: GameState) -> tuple[int, int]:
    """当前(位面,轮次)。

    开局环境帧的 gs = 裸 GameState 桩(cw_screen_invest_env 直构),node
    未写 → 按局首 (1, 1) 语义评估:env 3 选 1 消费帧中 node 缺读只发生在
    开局桩形(原 invest-env 迭代门 3 消费位),剩余口径的局首退化 = 全局
    期望。
    """
    node = gs.node.value
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


def env_economy_value(name: str, gs: GameState) -> tuple[float, bool]:
    """环境经济通道金等价期望(单一入口;签名与原 kernel 模块一致,
    复用预留见 28 号稿 §5)。

    返回 ``(expected_gold, resolved)``;resolved=False = fail-closed
    (未入模 / 估算参数缺失 / CI 方向不闭合 / 剩余期望为 0),消费端按无
    经济通道处理。

    **品质改写分派**(沿原 kernel 模块 3.6,details/env-value-models.md
    §2.2.5):name ∈ ENV_POOL_REWRITE 且条目带估值语义字段
    (``rewrite_quality`` 或 ``offer_structure`` 非空)→
    :func:`_pool_rewrite_value`(层 E ΔV 公式,读
    STRAT_POOL_ECON_MEANS/OFFER_QUALITY_DIST,任一缺参 fail-closed,v1
    恒然——受限通道 μ_E 非单调,层 E 转正须过准入门后落参);纯数量
    事实条目(仅挂点/刷新/难度豁免字段,如联席决策数量通道、T-46 策略
    大师 direct 挂点)不属层 E,落穿下方 A/B/拍值/C 通道公式——分派判据
    与 ``cw_investments._validate_env_pool_rewrite`` 互斥闸语义化豁免同源
    (估值语义字段非空才算估值结构,用户裁定 2026-10-26),防策略大师
    同键共存形态被层 E 分派遮蔽通道 4 消费。其余 name → A/B/拍值/C
    通道公式。单一入口契约不变(策略卡现金分**不走**本函数——策略屏现金
    流卡走策略层 ``strategy_economy.strategy_economy_value`` 新入口,通道
    公式分立,契约形态与折算约定复用;28 号稿 §5 与 29 号稿 §2.1);
    ENV_ECONOMY 与 ENV_POOL_REWRITE 构建期互斥已语义化豁免(同键共存
    合法性见 cw_investments._validate_env_pool_rewrite)。

    通道(值除注明外全部为注册表游戏定义【注】):
    - gold_instant:选卡当场一次性金(零参数,精确);
    - gold_per_plane_start:每位面开局金 × 位面可达权(剩余口径:既往位面
      不计;当前位面仅在开局轮(轮次 ≤ 1)可领——位面开局发放发生在轮 1 之前;
      晶矿自动开启假设见 ENV_ECONOMY_PENDING_VERIFICATION 已登记条);
    - xp_after_level:节点数 × 每节点 XP × XP_GOLD_RATE(「升 8 必然发生」
      假设已登记,v1 全额,不随剩余位面折扣——假设本身已承担心);
    - gold_per_strategy_coef:``Σ_k coef×k×P(第 k 张策略可取)``,k = 剩余
      取卡序 1 基(含本张口径,用户裁定 2026-10-26:第 k 张到手 = 含本张
      已持有 k,发 coef×k,首张 coef×1;已持有数起、基线取卡基数止),
      P(k) = 取卡所在位面的可达权(_STRATEGY_PICK_PLANES 结构表);
    - gold_after_refreshes(拍值):按 :data:`_GOLD_AFTER_REFRESHES_FIXED`
      无条件计(28 号稿 §2 现金分行;P97 §7 消费契约——不读 gs.effects 刷新计数、
      不消费 refresh_p/refresh_after 估算参数,刷价节省项已并入拍值);
      拍值表缺登记(新 gold_after_refreshes 环境漏拍)= fail-closed,
      防静默按 0 计入;
    - reward_node_bonus(C 类):字段 = 通道在场哨兵(1.0),每奖励节点期望
      增益真值+CI 在估算注册表(按 _REWARD_BONUS_VARIANTS 变体分键);期望 =
      增益 × 剩余期望奖励节点数(_REWARD_SLOTS 槽位结构 × 位面到达权)。

    fail-closed 门(参数级):所有消费参数按 CI 两端点重算 expected_gold,
    任一端点 ≤ 0(金期望方向翻转/含 0)→ resolved=False。
    结构性注记:A 类精确通道带参数无关分量(如增发货币位面 1 权恒 1)时,
    CI 含 0 的参数**不会**触发翻转——方向仍被确定分量钉住,这正是参数级门
    的语义(不确定度只覆盖参数依赖部分)。
    """
    _rw = ENV_POOL_REWRITE.get(name)
    if _rw is not None and (_rw.rewrite_quality or _rw.offer_structure):
        return _pool_rewrite_value(name, gs)
    env = get_env(name)
    if env is None or env.economy is None:
        return (0.0, False)
    eff = env.economy
    cur_plane, cur_round = _current_plane_round(gs)
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
    # 通道 4:策略大师(Σ_k coef×k×P(k);k = 剩余取卡序 1 基,含本张口径
    # = 第 k 张到手发 coef×k、首张 coef×1,用户裁定 2026-10-26)
    if eff.gold_per_strategy_coef:
        _held = len(gs.active_strategies.value or [])
        for _k in range(_held + 1, len(_STRATEGY_PICK_PLANES) + 1):
            _w = _arrival_weight(_STRATEGY_PICK_PLANES[_k - 1], cur_plane)
            if _w is None:
                params_missing = True
                continue
            _gain = eff.gold_per_strategy_coef * _k
            _acc((_gain * _w[0], _gain * _w[1], _gain * _w[2]))
    # 通道 5:刷新阈值返金(拍值注册,无条件计;28 号稿 §2/P97 §7 消费契约
    # 见 env_economy_value docstring)
    if eff.gold_after_refreshes is not None:
        _fixed = _GOLD_AFTER_REFRESHES_FIXED.get(env.name)
        if _fixed is None:
            params_missing = True
        else:
            _acc((_fixed, _fixed, _fixed))
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
        # fail-closed 门:CI 任一端点重算 ≤ 0 = 金期望方向不闭合
        return (0.0, False)
    return (acc[0], True)


def _validate_estimates_governance() -> None:
    """估算治理构建校验(import 即炸;迁移迭代 3.1 迁入改造后保留两项):

    ① C 类哨兵条目必须有变体键映射(漏映射 = 参数查询恒 miss,通道静默
    fail-closed 变哑炮);② 「待建模」已登记环境必须真实存在(∈
    INVESTMENT_ENVS)且不与 ENV_ECONOMY 双登记(单一环境只落一个估值口径)。
    (原「ECON_VALUE_NORM 域带上界越界」项随域带归一删除——现金分直接按
    金等价计,无上界语义可守。)
    """
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


_validate_estimates_governance()


# ===== 品质改写型层 E(ΔV 公式;自 kernel/cw_env_economy.py 原样迁入)=====
# ΔV(R) = Σ_{k ∈ picks(R)} [ μ_E(q_R; H_k) − Σ_q π_offer,k(q) · μ_E(q; H_k) ]
# 层 E = 改写后取卡金流期望相对无改写 offer 的抬升(受限直接金流/XP 通道;
# 明确排除刷新族/利息档覆写/合成卖价/血本位等行为依赖通道,排除集清单 =
# 详设 §2.2.2 econ_gold_v1 定义)。**转正判定的当前态 = fail-closed**:受限
# 通道实测 μ_E 不随品质单调(银 3.31 > 金 2.42),直入现金分会产出病态序;
# 转正准入门 = ①全通道重算(排除集补参)+ ②序一致性检验,两条件缺一不入
# (详设 §2.2.2)。数据批已执行判定:第 1 条完成,第 2 条未过(全通道 μ_E
# 点估计 银≥金 残差未翻转)→ 两参数表维持哨兵不落,本段行为零变化;判定
# 依据、读数与回炉候选 = invest-env 迭代 layer-e-promotion-batch 详设(git
# 历史可溯),重采入口 = tools/cw/env_pool_rewrite_estimates.py。
# 消费端(resolved ∧ expected_gold > 0)自动承载准入门第 2 条方向自洽。

#: 取卡序 k(1 基,同 StrategyPoolRewrite.rewrite_picks 坐标系)→ 取卡后剩余
#: 节点视界 H_k。【拟·实采】档案取卡选定事件经 terminal_ts 时间夹逼到轮,
#: 全局节点号按结构日程 P1=9/P2=7/P3=9 先验(总 25;P2=7 = economy.md §10.2
#: 位面典型节点表 + boss@p2r7 档案实证),H = 25 − 已完成节点数:H_1=23
#: (落点 79/80 局在 P1 r3)、H_2=15(63/66 局在 P2 r2);取卡序 3 的有效
#: 样本 n=3 低于注册门 20 → 哨兵不落,时代/尾彩通道因 H_3 缺参 fail-closed。
#: 样本面 = 净帧普通口径(扑满过热局整局剔除,对齐「148 总/140 普通」采样
#: 面裁定)。重采入口 = tools/cw/env_pool_rewrite_estimates.py(实采定位
#: 演化只改本表;口径与样本量 = invest-env 迭代 layer-e-promotion-batch 详设
#: (git 历史可溯))。v1 已登记值 24 系日程回退口径(9+9+9)下的参照值,被本
#: 实采取代。
_STRAT_PICK_HORIZONS: dict[int, int] = {1: 23, 2: 15}

#: μ_E per (品质,视界):品质子池受限通道金流均值(【拟】,EconomyEstimate
#: 四元组;键第二维 = H_k,公式 μ_E(q; H) 视界入参化的直接承载)。品质键 =
#: 注册表品质名('棱彩'/'金'/'银')。
#: **不落参数申报(转正数据批判定:准入门未过)**:全通道重算与序一致性
#: 检验已执行(重采入口 = tools/cw/env_pool_rewrite_estimates.py)——
#: 第 1 条(全通道补参)完成,第 2 条未过:全通道 μ_E 点估计 银≥金 残差
#: (H=23 +0.015 / H=15 +0.100,净帧口径,深居卡池抽样噪声,成对差值 CI 全
#: 含 0),按详设 §2.2.2 裁决维持 fail-closed,本表继续哨兵不落;序一致性
#: 复过且取卡序 3 视界/π 缺位补齐后随批落参。缺位 = 恒 fail-closed,时代/
#: 头彩/尾彩维持零现金分(现行为零变化)。
STRAT_POOL_ECON_MEANS: dict[tuple[str, int], EconomyEstimate] = {}

#: π_offer per 取卡序:无改写环境时第 k 次取卡的 offer 品质分布(【拟】;
#: 键 = k 1 基,值 = 品质 → EconomyEstimate。「未解析」份额不单列建模,
#: 入式前按已知三品质份额归一,归一口径随数据批申报)。缺位该 k =
#: 缺参 fail-closed。**不落参数申报(与 μ 表同判,准入门未过)**:k=1/k=2
#: 归一读数在案(银/金/棱彩 = 0.302/0.506/0.193 与 0.306/0.471/0.223,
#: 净帧匹配 99/70 帧组),取卡序 3 有效帧组 n=3 哨兵不落;落参时机 =
#: STRAT_POOL_ECON_MEANS 表注所述准入门复过之后,两表同批。
OFFER_QUALITY_DIST: dict[int, dict[str, EconomyEstimate]] = {}


def _pool_rewrite_value(name: str, gs: GameState) -> tuple[float, bool]:
    """品质改写型层 E 增量期望(ΔV;入口 = env_economy_value 分派)。

    ΔV(R) = Σ_{k ∈ picks(R)} [ μ_E(q_R; H_k) − Σ_q π_offer,k(q) · μ_E(q; H_k) ]

    - rewrite_quality 空(银·金·彩 = 结构改写/联席决策 = 数量通道)= 无层 E
      语义 → 结构性 fail-closed(非缺参:即使参数表全满也 False——数量通道
      不折金与 A 类策略大师同口径,价值由立场分承载);
    - 缺参 fail-closed:H_k / μ_E(q_R, H_k) / π_offer,k / μ_E(q, H_k) 任一
      查表 miss → (0.0, False)(v1 恒然:两参数表空);
    - CI 端点传播:基线项 Σ π·μ = 非负因子乘积和,端点 = Σ 端点积(单调
      区间,既有通道 P×E 端点同口径);ΔV_k = μ_R − base 区间差
      [μ_R.lo − base.hi, μ_R.hi − base.lo];多项 picks 端点相加(同号区间
      相加精确);
    - 方向门:CI 任一端点 ≤ 0 → (0.0, False)(与 A/B/C 通道同门;消费端
      28 号稿 §1 再加 expected_gold > 0——白银时代即使转正也因 ΔV ≤ 0
      落回零现金分,方向自洽)。

    gs 参数:层 E v1 用全局先验视界(_STRAT_PICK_HORIZONS),不做剩余口径
    条件化(H_k 随当前帧修正 = 转正数据批的参数化面);gs 保留于签名 =
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
