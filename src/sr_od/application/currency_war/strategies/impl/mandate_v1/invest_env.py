"""投资环境画面策略(mandate_v1;宪法六「一画面一策略文件」首批兑现)。

设计权威版本 = strategy-docs/28_invest_env_screen.md(本文件是其代码承载面,
「下称 28 号稿」,节号即该篇节号);评分模型 = 「统一加法标尺」——单位 =
分,**1 分 := 1 金等价**(归一化约定,非语义拍值;XP 折算沿
env_economy.XP_GOLD_RATE 承载),取代旧 kernel 的多标尺层次压制(裸分/
送卡档/阵营 floor/经济域带各标尺不可比,全靠层次常数定先后——迁移动机,
)。

总分公式(28 号稿 §1)::

    总分 = 现金分 + 方向分 + 赠卡分 + 立场分 + 转向轴加分

- 现金分 = env_economy.env_economy_value(resolved ∧ > 0 才计,fail-closed
  恒 0);
- 方向分组件恒 0(strength/方向分链整线下线,28 号稿 §2 方向分行废止,
  环境方向差异由赠卡分/立场分承载);
- 赠卡分 = gift_value 具名口径(ENV_GIFTS)+ 概念股随机阵营口径(28 号稿
  §2 赠卡分行);
- 立场分 = :data:`STANCE_SCORE`(【拍】形态,每行带理由;
  宪法五:策略立场归策略层,合法性来自裁定本身);
- 转向轴 = user-priority + :data:`STEERING_PRIORITY_BONUS`(软偏好,立场
  系数,压不过 S 线方向分 = 「用户点名是偏好不是支配」);user-forbid =
  排除出候选(28 号稿 §3)。

argmax 取最高,平分取先。禁选(env_forbid 命中)与阵容冲突出域 =
排除出候选(28 号稿 §3);选卡克制(counters_dot 硬排除迁移,
2026-11-03-unified-line-scoring design §3.2/§7)= 克制基准线主派的
候选减 :data:`cw_line_scales.COUNTER_PICK_PENALTY`(纯加权;环境名
不含词缀注册名族,该分量现行恒 0——机制与策略屏同源,判据不双源)。

阵容冲突护栏(changes/2026-10-17-invest-direction-guard,下称「护栏设计」
§2.2/§2.4):出域槽(候选环境有阵容指向且与冲突基准零交)并入既有
excluded 槽位表通道(禁选/自拆台同路)——次数闸过先建议刷新,闸尽落选时
出域已排除,全出域帧走既有 all-excluded 回退(不制造空选);基准空帧
(无指向持有 ∧ 未锁定)护栏不辖,行为与无护栏逐位一致。基准语义与
策略侧(:mod:`invest_strategy` ``_conflict_basis``)同款,两屏生产模块
平行不共享(沿本包两屏文件不互相 import 的既有结构)。

刷新判据(28 号稿 §4):建议刷 = 帧内存在禁选槽 ∨ 帧最好总分 <
:data:`REFRESH_THRESHOLD`;次数闸 = ``gs.env_refresh_left ≥ 1``。

输出契约(28 号稿 §4)::func:`decide` 返回纯值 dataclass
(:class:`InvestEnvDecision` / :class:`RefreshSuggestion`),不含动作词表
——动作包装(CwActionPickInvestEnvParam/CwActionRefreshInvestCardsParam)
留 flow(flow ``_decide_invest`` kind='env' 分支);:func:`decide_pick` =
同一评分基线的纯选卡口(flow 同帧去重 memo 命中后的落选卡入口;为 sim
复用预留)。本文件是投资环境选卡评序的单一源(flow 直调;
kernel 侧 env 评估机器(裸分/送卡档/阵营 floor/经济域带/环境帧刷新判据)
不复存在)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_comps import get_comp
from sr_od.application.currency_war.kernel.cw_game_state import GameState
from sr_od.application.currency_war.kernel.cw_investments import (
    ENV_ECONOMY,
    ENV_GIFTS,
    INVESTMENT_ENVS,
    env_faction_scope,
    get_env,
    strategy_faction_scope,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.env_economy import (
    env_economy_value,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.gift_value import (
    GIFT_TIER_SCORE,
    named_gift_value,
    random_faction_gift_value,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.line_select import (
    anchor_line_of,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.pick_common import (
    STEERING_PRIORITY_BONUS,
    counter_pick_penalty,
    punished_mechs_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.currency_war_config import (
        CurrencyWarConfig,
    )


# ===== 输出契约(28 号稿 §4:纯值 dataclass,不含动作词表)=====

@dataclass(frozen=True)
class InvestEnvDecision:
    """选卡决策。

    idx = options 列表下标(0 基;候选序 = 调用方传入序,取值时机 =
    本帧决策期快照);reason = 归因串(总分与四组件分解,仅观测)。
    margin = 次名分量遥测(pick-margin-telemetry design §2.2-1 键形
    ``{runner_up, runner_up_total, margin}``,值源 = 决策评分帧 scores
    列表[含转向轴],禁用 option_total;竞争域仅 1 候选 → 三键 null;
    空候选帧不落值 None;仅观测,决策面零消费)。
    """
    idx: int
    reason: str
    margin: dict | None = field(default=None, kw_only=True)


@dataclass(frozen=True)
class RefreshSuggestion:
    """刷新建议(动作包装 CwActionRefreshInvestCardsParam 留 flow;
    handler 的 obs.refresh 现读闸 + 状态容器 env_refresh_left 对照闸原样,
    op 层零改动,28 号稿 §4 输出契约)。"""
    reason: str


# ===== 转向轴与自拆台(28 号稿 §3;共用单一源 = pick_common)=====

# 两屏共用判据已显式抽离共用模块(宪法六「共用判据显式抽离」):
# 转向轴常数与自拆台阈值/克制判定单一源 = mandate_v1/pick_common.py,
# 下方名字 = 该模块 re-export(本文件内引用与既有测试/判读面零改名)。


# ===== 立场分表(28 号稿 §2 立场分行;【拍】形态,每行带理由)=====

@dataclass(frozen=True)
class StanceRow:
    """立场分表行。

    score = 立场分(统一标尺上的量,分差有含义——「分值思维」,design
    §2.2 加法合法前提);reason = 裁定理由(表的裁决记录,经用户裁定窗过目)。
    """
    score: float
    reason: str


#: 环境立场分表(28 号稿 §2 立场分行 全量):登记「无机械成分」环境
#: (判定 = 无阵营 ∧ 不在 ENV_GIFTS ∧ 不在 ENV_ECONOMY——这些环境的
#: 价值不含任何可推导成分,纯立场)+ 表 3 点名的零值机械环境(经济过热/
#: 经济严重过热,C 类通道零有效估计时现金分 fail-closed=0,补参后自动进
#: 现金分,立场行仅登记 0)。**机械环境保留立场行合法**(校验单方向强制:
#: 无机械成分必须在表,机械成员入表不拦)——已登记先例:火药味/特权阶级
#: (权重 10.0,起决定作用)与三星佩佩/粗星佩佩(0.0,用户裁定 2026-10-15);防按「机械成员
#: 不入表」旧口径误删起决定作用的行。表外环境立场恒 0(有机械成分的环境立场本就
#: 不入表);覆盖由 :func:`_validate_stance_coverage` 构建期兜底:无机械
#: 成分条目必须在表,缺失 import 即炸。
STANCE_SCORE: dict[str, StanceRow] = {
    # —— 时代族 6 条(用户裁定 2026-09-23:品质重排只是换随机方式,
    # 整体期望不变;宪法三覆盖危险信号反应时机、非计分义务,记 0 不违宪)——
    '彩虹时代': StanceRow(0.0, '品质重排只是换随机方式,整体期望不变(用户裁定 2026-09-23)'),
    '黄金时代': StanceRow(0.0, '品质重排只是换随机方式,整体期望不变(用户裁定 2026-09-23)'),
    '白银时代': StanceRow(0.0, '品质重排只是换随机方式,整体期望不变;「难度不加」安全向小增益一并归零(用户裁定 2026-09-23)'),
    '头彩': StanceRow(0.0, '品质重排只是换随机方式,整体期望不变(用户裁定 2026-09-23)'),
    '尾彩': StanceRow(0.0, '品质重排只是换随机方式,整体期望不变(用户裁定 2026-09-23)'),
    '银·金·彩': StanceRow(0.0, '槽位品质承诺+刷新资源的策略侧价值未建模,保持 0 分(零分基调用户裁定 2026-09-23;槽位映射 2026-10-19 卡面即真值定谳,重评归策略调优批)'),
    # —— C 类经济(现金通道零有效估计,现金分 fail-closed=0;补参后自动
    # 进现金分,立场行登记 0)——
    '经济过热': StanceRow(0.0, 'C 类通道零有效估计,现金分 fail-closed=0;补参后自动进现金分'),
    '经济严重过热': StanceRow(0.0, 'C 类通道零有效估计,现金分 fail-closed=0;补参后自动进现金分'),
    # —— 待建模已登记(ENV_ECONOMY_PENDING_MODELING 维持;建模落地自动进现金分)——
    '轮岗': StanceRow(0.0, '待建模在册维持(金等价参数化缺失);建模落地自动进现金分'),
    # —— 定案按 0(用户裁定 2026-10-16,非待建模;PENDING 表登记语义见条目文案)——
    '人才下沉': StanceRow(0.0, '估值按 0(2026-10-16 用户裁定);2★ 直出 sim 分支已建'
                          '(kernel 注册表占位 0.2,禁入估值)'),
    # —— 强度类立场(宪法一确认义务:涉强度效果按硬闸门义务用户过目后
    # 生效;确认动作 = 用户裁定窗对表 1-3 过目)——
    '进化算法': StanceRow(40.0, '每节点叠 4% 强度+2% 减伤,成长型;宪法一禁强度建模,纯立场。量级锚:20 节点累积接近一条 A 线方向分的量级'),
    # —— 数量/结构通道(策略域不折金,立场承载)——
    '联席决策': StanceRow(25.0, '2-6 额外一次投资策略三选一(数量通道,策略域不折金)'),
    '劳务派遣合同': StanceRow(15.0, '卡面效果 = 随机星徽 + 每首领节点发对应羁绊随机角色(流程侧已建模);资产价值不入估值分,折算挂账'),
    '人身意外险': StanceRow(15.0, '首领节点前加补给阶段(生存向,发展优先姿态下中性偏正)'),
    '英雄登场': StanceRow(15.0, '白得 2 星 5 费但 19 节点后才可上场(延迟兑现折扣)'),
    '命运礼物': StanceRow(15.0, '惊喜盒 12 节点倒计时,内容随机'),
    '过剩经费': StanceRow(10.0, '补给阶段角色带两件装备'),
    '火药味': StanceRow(10.0, '开局 2 个简易武装箱(装备域价值未建模)'),
    # —— 小规则增益族(效果异质但量级均为「小规则增益」;逐条重拍留实机
    # 判读后)——
    '深井角斗场': StanceRow(10.0, '小规则增益量级;逐条重拍留实机判读后'),
    '特权阶级': StanceRow(10.0, '小规则增益量级;逐条重拍留实机判读后'),
    '红钻贵族': StanceRow(10.0, '小规则增益量级;逐条重拍留实机判读后'),
    '蓝钻贵族': StanceRow(10.0, '小规则增益量级;逐条重拍留实机判读后'),
    '人才引进': StanceRow(10.0, '小规则增益量级;逐条重拍留实机判读后'),
    '战争边疆': StanceRow(10.0, '小规则增益量级;逐条重拍留实机判读后'),
    '战力飙升': StanceRow(10.0, '小规则增益量级;逐条重拍留实机判读后(宪法一:强度立场,用户过目后生效)'),
    '战力提升': StanceRow(10.0, '小规则增益量级;逐条重拍留实机判读后(宪法一:强度立场,用户过目后生效)'),
    '人才储备': StanceRow(10.0, '小规则增益量级;逐条重拍留实机判读后'),
    '专家研讨会': StanceRow(10.0, '小规则增益量级;逐条重拍留实机判读后'),
    '粗星佩佩': StanceRow(0.0, '用户裁定 2026-10-15:效果无法估计,拍 0(掉落分支零建模后无独立可估计价值)'),
    '三星佩佩': StanceRow(0.0, '用户裁定 2026-10-15:召唤填充位,无阵营/流派,星徽佩戴分支不建模'),
    '敌后破坏': StanceRow(10.0, '小规则增益量级;逐条重拍留实机判读后'),
}

_STANCE_ZERO = StanceRow(0.0, '表外环境立场恒 0')


# ===== 构建期校验(import 即炸;28 号稿 §2)=====

def _validate_stance_coverage() -> None:
    """立场表覆盖校验:无机械成分条目必须在表;表键必须真实已登记。

    - 无机械成分判定(28 号稿 §2 立场分行)= 无阵营 ∧ 不在 ENV_GIFTS ∧ 不在
      ENV_ECONOMY:这些环境的价值不含任何可推导成分,立场表是唯一分值
      载体,缺行 = 环境静默零分 → import 即炸(注册表演化防线,沿
      ENV_ECONOMY/ENV_GIFTS 孤儿键校验先例);
    - 表键孤儿(注册表无此环境,版本改名后漏跟)→ 同样炸出。
    """
    for _name, _env in INVESTMENT_ENVS.items():
        _mechanical = bool(_env.faction) or _name in ENV_GIFTS \
            or _name in ENV_ECONOMY
        if not _mechanical and _name not in STANCE_SCORE:
            raise ValueError(
                f"立场分表缺行(无机械成分环境必须有立场行):{_name!r}")
    for _name in STANCE_SCORE:
        if _name not in INVESTMENT_ENVS:
            raise ValueError(f"立场分表孤儿键(注册表无此环境):{_name!r}")


def _validate_coefficient_tables() -> None:
    """系数表键完备校验:赠卡档分覆盖档位机器全部四档(28 号稿 §2 赠卡分行;
    缺键 = 对应卡静默零分 → import 即炸)。线强度档分已随 strength 字段/
    LINE_STRENGTH_SCORE 整链下线移除(方向分组件归零)。"""
    _gift_tiers = {'core', 'shared', 'transition', 'off'}
    _missing_gift = _gift_tiers - set(GIFT_TIER_SCORE)
    if _missing_gift:
        raise ValueError(
            f"赠卡档分缺键(gift_hit_tier 档域未登记):{sorted(_missing_gift)}")


_validate_stance_coverage()
_validate_coefficient_tables()


# ===== 总分组件(28 号稿 §1 加法公式)=====

def _components(name: str, gs: GameState, locked_comp: str,
                demoted_endgame: bool,
                evicted: frozenset[str]) -> tuple[float, float, float, float]:
    """单环境四组件 (现金,方向,赠卡,立场);未注册名 → 全 0(OCR 形变)。

    - 现金分:resolved ∧ > 0 才计,fail-closed 恒 0(28 号稿 §1/§2);
    - 方向分组件恒 0(strength/LINE_STRENGTH_SCORE 整链下线,28 号稿 §2
      方向分行废止——环境选卡不区分「利好的线强不强」,概念股/邀请的
      方向差异由赠卡分/立场分承载);
    - 概念股额外加随机阵营赠卡分(「白得该阵营角色」;「找牌概率提高」
      「初始简易装备」v1 不计 = 申报低估向);
    - 立场分:表行缺省 0(表外环境立场不入表,28 号稿 §2 立场分行)。
    """
    cash, resolved = env_economy_value(name, gs)
    cash_v = cash if (resolved and cash > 0) else 0.0
    env = get_env(name)
    faction = env.faction if env is not None else ''
    _dir = 0.0
    gift = named_gift_value(name, evicted)
    if env is not None and env.category == '概念股' and faction:
        gift += random_faction_gift_value(faction, evicted)
    stance = STANCE_SCORE.get(name, _STANCE_ZERO).score
    return cash_v, _dir, gift, stance


def option_total(name: str, gs: GameState,
                 locked_comp: str = '', demoted_endgame: bool = False,
                 evicted: frozenset[str] | set[str] = frozenset()) -> float:
    """单环境总分 = 现金 + 方向 + 赠卡 + 立场(不含转向轴)。

    转向轴(priority/forbid)是用户本局配置,不入本函数——刷新阈值的
    构建期派生(全 83 条均值,28 号稿 §4)与运行时评分共用同一无轴基线,
    保证「阈值 = 同一口径的均值」。
    """
    _cash, _dir, _gift, _stance = _components(
        name, gs, locked_comp, demoted_endgame, frozenset(evicted))
    return _cash + _dir + _gift + _stance


#: 刷新阈值 = 全部 83 条环境总分的均值,构建期由注册表+系数+立场表派生为
#: 常量(单一源 = 表,不手维护数字;表改则阈值自动随动,28 号稿 §4)。
#: 依据:重掷免费,重掷后帧最好的期望 ≥ 单抽期望 = 全表均值(实际
#: E[max of 3] > 均值,取均值 = 保守向,不高估重掷收益)。不取「下三分之一
#: 分位」——立场 0 值条目多,分位阈值会沉到 0 附近令判据失效,均值对 0 值
#: 堆积稳健。派生用裸 GameState 桩(schema_version=1,node 未写 = 开局帧,
#: 桩形模式沿同批治理校验先例)。
def _derive_refresh_threshold() -> float:
    """全注册表无轴总分的均值(构建期一次)。"""
    _gs = GameState(schema_version=1)
    return sum(option_total(_n, _gs) for _n in INVESTMENT_ENVS) / len(INVESTMENT_ENVS)


REFRESH_THRESHOLD: float = _derive_refresh_threshold()


# ===== 决策入口(28 号稿 §4)=====

def _conflict_basis(gs: GameState, locked_comp: str,
                    demoted_endgame: bool) -> frozenset[str]:
    """冲突基准(护栏设计 §2.2;与策略侧 invest_strategy._conflict_basis
    同款语义,两屏平行实现——基准语义单一源 = 护栏设计 §2.2,代码双份
    沿两屏文件不互相 import 的包结构):

    - 锁定帧(locked_comp 非空 ∧ 非降格)= 锁线 Comp.factions——锁定 =
      终局方向裁定完成,历史误持不入基;
    - 未锁定帧 = 已持有投资的指向并集(环境 + 策略,持有 append-only →
      基准单调不减,出域判定只收紧);降格帧锁线不入基,回持有基
      (降格 = 终局方向暂席,与模块既有 demoted 语义同构);
    - 锁线名不可解析(OCR 漂移/非阵容名)→ 空集;基准空 = 护栏不辖,
      行为与无护栏逐位一致。全部指向集查询经 kernel 归一口径
      (``env_faction_scope``/``strategy_faction_scope`` 内先
      ``normalize_invest_name``,持有名 OCR 形变不静默漏拦)。
    """
    if locked_comp and not demoted_endgame:
        lc = get_comp(locked_comp)
        return frozenset(lc.factions) if lc is not None else frozenset()
    basis: set[str] = set()
    env_name = gs.active_env.value or ''
    if env_name:
        basis |= env_faction_scope(env_name)
    for name in (gs.active_strategies.value or []):
        basis |= strategy_faction_scope(name)
    return frozenset(basis)


def _score_frame(options: list[str], gs: GameState, locked_comp: str,
                 demoted_endgame: bool, evicted: frozenset[str],
                 env_priority: list[str],
                 env_forbid: list[str],
                 basis: frozenset[str]) -> tuple[list[float], list[float],
                                                 list[tuple[float, ...]],
                                                 list[bool]]:
    """帧评分一次(选卡/刷新两入口共享,禁二次评分;选卡基准线/受克
    属性集循环外单帧单读,沿旧机器纪律):
    返回 (总分含转向轴,转向加分,五组件,排除标记)。

    basis = 冲突基准(护栏设计 §2.2,调用方入口算好传入):出域槽
    (候选环境有指向且与基准零交,§2.4)并入 excluded 槽位表——与禁选
    同通道,禁选槽触发建议刷与全排除回退两条既有路径原样复用,
    零新出口形态。克制减分(counters_dot 硬排除迁移,design §3.2/§7)
    = 组件分量:环境名不含词缀注册名族,该分量现行恒 0——机制与策略屏
    同源(基准线 = :func:`line_select.anchor_line_of`),判据不双源。"""
    anchor = anchor_line_of(gs, locked_comp, demoted_endgame)
    punished = punished_mechs_of(anchor)
    scores: list[float] = []
    steers: list[float] = []
    components: list[tuple[float, ...]] = []
    excluded: list[bool] = []
    for _opt in options:
        _cash, _dir, _gift, _stance = _components(
            _opt, gs, locked_comp, demoted_endgame, evicted)
        _steer = STEERING_PRIORITY_BONUS if any(
            _p in _opt for _p in env_priority) else 0.0
        _counter = float(counter_pick_penalty(_opt, punished))
        # 出域标记(护栏设计 §2.3 规则表):基准非空 ∧ 候选有指向 ∧ 与
        # 基准零交;通用环境(指向集空)与基准空帧恒不标记
        _scope = env_faction_scope(_opt)
        _off = bool(basis) and bool(_scope) and not (_scope & basis)
        _excluded = any(_p in _opt for _p in env_forbid) or _off
        scores.append(_cash + _dir + _gift + _stance + _steer + _counter)
        steers.append(_steer)
        components.append((_cash, _dir, _gift, _stance, _counter))
        excluded.append(_excluded)
    return scores, steers, components, excluded


def _runner_up_margin(options: list[str], scores: list[float],
                      best_idx: int, excluded: list[bool]) -> dict:
    """次名分量收集(纯观测,pick-margin-telemetry design §2.2-1;与
    胜者同一竞争域——``excluded`` 传实际排除表 = 竞争域,全排除退化帧
    由调用方传空表 = 全体域,与 argmax 的域选择同一逻辑)。

    次名 = 域内除胜者外的首个最高分(平分取先,与 :func:`_argmax_first`
    的严格大于语义同构,禁另立排序);域内不足 2 候选 → 三键 null 形态。
    只读现值算差,不参与任何决策(argmax 与域过滤逻辑逐行不动)。"""
    runner = -1
    for i in range(len(scores)):
        if i == best_idx or (i < len(excluded) and excluded[i]):
            continue
        if runner < 0 or scores[i] > scores[runner]:
            runner = i
    if runner < 0:
        return {'runner_up': None, 'runner_up_total': None, 'margin': None}
    return {'runner_up': options[runner], 'runner_up_total': scores[runner],
            'margin': scores[best_idx] - scores[runner]}


def _pick_decision(options: list[str], scores: list[float],
                   steers: list[float],
                   components: list[tuple[float, ...]],
                   excluded: list[bool]) -> InvestEnvDecision:
    """评分帧 → 选卡决策(argmax 取最高,平分取先;全排除退化帧对全体
    候选(含被禁)取 argmax 最不负分者——28 号稿 §3 退化帧形态,reason
    标 all-excluded-fallback 供判读)。margin = 竞争域次名(全排除退化
    帧按全体域取,reason tag 已携退化标记供判读)。"""
    best_idx = _argmax_first(scores, excluded)
    if best_idx < 0:
        best_idx = _argmax_first(scores, [])
        return InvestEnvDecision(
            idx=best_idx,
            reason='all-excluded-fallback '
                   + _breakdown(best_idx, scores, steers, components),
            margin=_runner_up_margin(options, scores, best_idx, []))
    return InvestEnvDecision(
        idx=best_idx, reason=_breakdown(best_idx, scores, steers, components),
        margin=_runner_up_margin(options, scores, best_idx, excluded))


def decide_pick(options: list[str], gs: GameState, locked_comp: str,
                demoted_endgame: bool, evicted: frozenset[str] | set[str],
                config: CurrencyWarConfig) -> InvestEnvDecision:
    """纯选卡决策(无刷新判据;与 :func:`decide` 同一评分基线)。

    独立成口的原因:decide 是纯函数,flow 同帧去重 memo 命中(handler
    刷新闸全败后的重调,28 号稿 §4「建议帧首调发建议、紧随重调落选卡」)
    时再调 decide 仍返建议——落选卡走本口,同一评分基线保证零选卡漂移。
    冲突基准在此入口算好(护栏设计 §2.2,:func:`_conflict_basis`)传入
    评分帧,出域槽排除与 :func:`decide` 同基线。"""
    env_priority = list(getattr(config, 'env_priority', []) or [])
    env_forbid = list(getattr(config, 'env_forbid', []) or [])
    if not options:
        # 空候选帧(观察层失约形态;旧 kernel decide_event 同输入返回
        # option_idx=0 的退化行为,本函数镜像防炸,不引入新语义)
        return InvestEnvDecision(idx=0, reason='empty-frame: 无候选退化')
    basis = _conflict_basis(gs, locked_comp, demoted_endgame)
    scores, steers, components, excluded = _score_frame(
        options, gs, locked_comp, demoted_endgame, frozenset(evicted),
        env_priority, env_forbid, basis)
    return _pick_decision(options, scores, steers, components, excluded)


def decide(options: list[str], gs: GameState, locked_comp: str,
           demoted_endgame: bool, evicted: frozenset[str] | set[str],
           config: CurrencyWarConfig) -> InvestEnvDecision | RefreshSuggestion:
    """投资环境 3 选 1 决策(纯值出口;flow 包装动作词表,28 号稿 §4)。

    - options = 屏上候选名列表(状态容器序);locked_comp/demoted_endgame/
      evicted = 意向状态三参同源直通(flow 解析后传入,28 号稿 §2.9
      「意向解析留 flow」);
    - 禁选(env_forbid 命中,子串匹配与白名单一致)与阵容冲突出域槽
      (护栏设计 §2.4,基准 = :func:`_conflict_basis`)= 排除出候选
      (excluded 槽位表同通道);克制减分为组件分量(见 :func:`_score_frame`
      docstring,counters_dot 硬排除迁移);
    - 建议刷 = 排除槽存在 ∨ 帧最好总分 < REFRESH_THRESHOLD,且次数闸
      ``gs.env_refresh_left ≥ 1``;建议刷成立 → RefreshSuggestion,
      否则 → InvestEnvDecision(argmax 取最高,平分取先;全排除退化帧
      走既有 all-excluded 回退,不制造空选)。
    """
    env_priority = list(getattr(config, 'env_priority', []) or [])
    env_forbid = list(getattr(config, 'env_forbid', []) or [])
    if not options:
        # 空候选帧(观察层失约形态;旧 kernel decide_event 同输入返回
        # option_idx=0 的退化行为,本函数镜像防炸,不引入新语义)
        return InvestEnvDecision(idx=0, reason='empty-frame: 无候选退化')
    basis = _conflict_basis(gs, locked_comp, demoted_endgame)
    scores, steers, components, excluded = _score_frame(
        options, gs, locked_comp, demoted_endgame, frozenset(evicted),
        env_priority, env_forbid, basis)
    # forbidden_slot 含出域槽(护栏出域并入 excluded 通道,§2.4——
    # 出域占槽应刷掉换本线方向机会,与禁选槽同路同形,零新出口形态)
    forbidden_slot = any(excluded)
    if forbidden_slot or max(scores) < REFRESH_THRESHOLD:
        # 次数闸 = gs.env_refresh_left ≥ 1(28 号稿 §4)。Field 读数 None
        # = 观察写端读缺跳写(未观察到剩余次数),次数 ≥ 1 无法确证 →
        # 不建议刷(保守向:漏一次建议优于虚发动作;handler 侧 obs.refresh
        # 现读闸 + 状态容器对照闸原样,建议刷最终仍由 handler 双闸裁定)。
        refresh_left = gs.env_refresh_left.value
        if refresh_left is not None and refresh_left >= 1:
            if forbidden_slot:
                return RefreshSuggestion(reason='refresh: 禁选槽存在')
            return RefreshSuggestion(
                reason=f'refresh: 帧最好总分 {max(scores):.0f}'
                       f' < 阈值 {REFRESH_THRESHOLD:.1f}')
    return _pick_decision(options, scores, steers, components, excluded)


def _argmax_first(scores: list[float],
                  excluded: list[bool]) -> int:
    """argmax 取最高,平分取先(28 号稿 §1);excluded 槽不入竞争。

    全部被排除 → 返回 -1(调用方决定退化路径)。
    """
    best = -1
    for i, s in enumerate(scores):
        if i < len(excluded) and excluded[i]:
            continue
        if best < 0 or s > scores[best]:
            best = i
    return best


def _breakdown(idx: int, scores: list[float], steers: list[float],
               components: list[tuple[float, ...]]) -> str:
    """归因串:总分 + 五组件分解 + 转向轴(仅观测,进 reason;克制减分
    环境名族现行恒 0,分量保留与策略屏同形)。"""
    _cash, _dir, _gift, _stance, _counter = components[idx]
    return (f'pick total={scores[idx]:.0f}'
            f' cash={_cash:.0f} dir={_dir:.0f} gift={_gift:.0f}'
            f' stance={_stance:.0f} steer={steers[idx]:.0f}'
            f' counter={_counter:.0f}')
