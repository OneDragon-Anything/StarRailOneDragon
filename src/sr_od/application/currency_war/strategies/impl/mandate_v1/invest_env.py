"""投资环境画面策略(mandate_v1;宪法六「一画面一策略文件」首批兑现)。

设计依据 = docs/develop/sr_od/application/currency_war/changes/
2026-09-23-invest-env-strategy-migration/design.md §2.2/§2.6/§2.7/§2.8/§2.9
(下称 design §);评分模型 = 「统一加法标尺」——单位 = 分,**1 分 :=
1 金等价**(归一化约定,非语义拍值;XP 折算沿 env_economy.XP_GOLD_RATE
承载),取代旧 kernel 的多标尺层次压制(裸分/送卡档/阵营 floor/经济域带
各标尺不可比,全靠层次常数定先后——迁移动机,design §1)。

总分公式(design §2.2)::

    总分 = 现金分 + 方向分 + 赠卡分 + 立场分 + 转向轴加分

- 现金分 = env_economy.env_economy_value(resolved ∧ > 0 才计,fail-closed
  恒 0);
- 方向分 = line_value.line_value(概念股/邀请;design §2.4);
- 赠卡分 = gift_value 具名口径(ENV_GIFTS)+ 概念股随机阵营口径(design §2.5);
- 立场分 = :data:`STANCE_SCORE`(design §2.6 表 3,【拍】形态,每行带理由;
  宪法五:策略立场归策略层,合法性来自裁定本身);
- 转向轴 = user-priority + :data:`STEERING_PRIORITY_BONUS`(软偏好,立场
  系数,压不过 S 线方向分 = 「用户点名是偏好不是支配」);user-forbid =
  排除出候选(design §2.8)。

argmax 取最高,平分取先。禁选(env_forbid 命中)与自拆台(:func:`_counters_dot`,
design §2.8)= 排除出候选。

刷新判据(design §2.7):建议刷 = 帧内存在禁选槽 ∨ 帧最好总分 <
:data:`REFRESH_THRESHOLD`;次数闸 = ``gs.env_refresh_left ≥ 1``。

输出契约(design §2.9)::func:`decide` 返回纯值 dataclass
(:class:`InvestEnvDecision` / :class:`RefreshSuggestion`),不含动作词表
——动作包装(CwActionPickInvestEnvParam/CwActionRefreshInvestCardsParam)
留 flow。本文件随迁移迭代 3.1 落地,阶段内零调用方(flow 接线 = 3.2,
与 kernel 删除面同一 commit 原子切换,新旧不并存)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_comps import (
    AFFIX_MECHANIC_MAP,
    COMP_LIBRARY,
    MECHANIC_COUNTERS,
)
from sr_od.application.currency_war.kernel.cw_game_state import GameState
from sr_od.application.currency_war.kernel.cw_investments import (
    ENV_ECONOMY,
    ENV_GIFTS,
    INVESTMENT_ENVS,
    get_env,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.env_economy import (
    env_economy_value,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.gift_value import (
    GIFT_TIER_SCORE,
    named_gift_value,
    random_faction_gift_value,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.line_value import (
    LINE_STRENGTH_SCORE,
    line_value,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.currency_war_config import (
        CurrencyWarConfig,
    )


# ===== 输出契约(design §2.9:纯值 dataclass,不含动作词表)=====

@dataclass(frozen=True)
class InvestEnvDecision:
    """选卡决策。

    idx = options 容器下标(0 基;候选序 = 调用方传入序,取值时机 =
    本帧决策期快照);reason = 归因串(总分与四组件分解,仅观测)。
    """
    idx: int
    reason: str


@dataclass(frozen=True)
class RefreshSuggestion:
    """刷新建议(动作包装 CwActionRefreshInvestCardsParam 留 flow;
    handler 的 obs.refresh 现读闸 + 容器 env_refresh_left 对照闸原样,
    op 层零改动,design §2.7 输出契约)。"""
    reason: str


# ===== 转向轴与自拆台(design §2.8)=====

#: user-priority 软偏好分(固定偏好分,立场系数;design §2.8——软偏好,
#: 压不过 S 线方向分 100,「用户点名是偏好不是支配」)。
STEERING_PRIORITY_BONUS: float = 30.0

#: 自拆台板面阈值:上阵羁绊计数中 持续伤害+减益 ≥ 2(沿旧口径
#: kernel/cw_events.py decide_event on_dot;板面 = gs.board 现读)。
BOARD_DOT_COUNT_THRESHOLD: int = 2

#: 本策略阵容的机械属性面(与 kernel ``MECHANIC_COUNTERS`` 值域对齐):
#: 板面以 DoT/减益为主派时,克制这些机制的候选 = 自拆台,排除。
#: 集合本身是策略侧立场(「我们在玩什么」);「某选项是否克制某机制」
#: 的事实判定 = kernel 表(design §2.8)。
_DOT_PUNISHED_MECHS: frozenset[str] = frozenset({'DoT', '减益'})


def _counters_dot(opt: str) -> bool:
    """选项名是否克制 DoT/减益主派(事实判定,kernel 表调用;design §2.8)。

    选项名 → ``AFFIX_MECHANIC_MAP`` 机制 tag → ``MECHANIC_COUNTERS`` 克制
    属性,与旧 kernel ``_opt_counters_dot`` 同构(子串包含匹配保留 OCR
    容错语义;未知名不命中 = 不排除)。
    """
    for affix, tag in AFFIX_MECHANIC_MAP.items():
        if affix in opt and not _DOT_PUNISHED_MECHS.isdisjoint(
                MECHANIC_COUNTERS.get(tag, ())):
            return True
    return False


# ===== 立场分表(design §2.6 表 3;【拍】形态,每行带理由)=====

@dataclass(frozen=True)
class StanceRow:
    """立场分表行。

    score = 立场分(统一标尺上的量,分差有含义——「分值思维」,design
    §2.2 加法合法前提);reason = 裁定理由(表的裁决记录,落地 3.1
    裁决窗过目 = 验收凭据)。
    """
    score: float
    reason: str


#: 环境立场分表(design §2.6 表 3 全量):仅登记「无机械成分」环境
#: (判定 = 无阵营 ∧ 不在 ENV_GIFTS ∧ 不在 ENV_ECONOMY——这些环境的
#: 价值不含任何可推导成分,纯立场)+ 表 3 点名的零值机械环境(经济过热/
#: 经济严重过热,C 类通道零有效估计时现金分 fail-closed=0,补参后自动进
#: 现金分,立场行仅登记 0)。表外环境立场恒 0(有机械成分的环境立场本就
#: 不入表);覆盖由 :func:`_validate_stance_coverage` 构建期兜底:无机械
#: 成分条目必须在表,缺失 import 即炸。
STANCE_SCORE: dict[str, StanceRow] = {
    # —— 时代族 6 条(用户裁定 2026-09-23:品质重排只是换随机方式,
    # 整体期望不变;宪法三辖危险信号反应时机、非计分义务,记 0 不违宪)——
    '彩虹时代': StanceRow(0.0, '品质重排只是换随机方式,整体期望不变(用户裁定 2026-09-23)'),
    '黄金时代': StanceRow(0.0, '品质重排只是换随机方式,整体期望不变(用户裁定 2026-09-23)'),
    '白银时代': StanceRow(0.0, '品质重排只是换随机方式,整体期望不变;「难度不加」安全向小增益一并归零(用户裁定 2026-09-23)'),
    '头彩': StanceRow(0.0, '品质重排只是换随机方式,整体期望不变(用户裁定 2026-09-23)'),
    '尾彩': StanceRow(0.0, '品质重排只是换随机方式,整体期望不变(用户裁定 2026-09-23)'),
    '银·金·彩': StanceRow(0.0, '品质重排只是换随机方式,整体期望不变;「刷新+2」一并归零(用户裁定 2026-09-23)'),
    # —— C 类经济(现金通道零有效估计,现金分 fail-closed=0;补参后自动
    # 进现金分,立场行登记 0)——
    '经济过热': StanceRow(0.0, 'C 类通道零有效估计,现金分 fail-closed=0;补参后自动进现金分'),
    '经济严重过热': StanceRow(0.0, 'C 类通道零有效估计,现金分 fail-closed=0;补参后自动进现金分'),
    # —— 待建模在册(ENV_ECONOMY_PENDING_MODELING 维持;建模落地自动进现金分)——
    '轮岗': StanceRow(0.0, '待建模在册维持(金等价参数化缺失);建模落地自动进现金分'),
    '人才下沉': StanceRow(0.0, '待建模在册维持(2★ 商店价结构未查证);建模落地自动进现金分'),
    # —— 强度类立场(宪法一确认义务:涉强度效果按硬闸门义务用户过目后
    # 生效;确认动作 = 落地 3.1 裁决窗对表 1-3 过目)——
    '进化算法': StanceRow(40.0, '每节点叠 4% 强度+2% 减伤,成长型;宪法一禁强度建模,纯立场。量级锚:20 节点累积接近一条 A 线方向分的量级'),
    # —— 数量/结构通道(策略域不折金,立场承载)——
    '联席决策': StanceRow(25.0, '2-6 额外一次投资策略三选一(数量通道,策略域不折金)'),
    '劳务派遣合同': StanceRow(15.0, '出售/合成触发金,无通道字段(防错装校验在册拒绝建模),折算挂账'),
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
    '粗星佩佩': StanceRow(10.0, '小规则增益量级;逐条重拍留实机判读后'),
    '三星佩佩': StanceRow(10.0, '小规则增益量级;逐条重拍留实机判读后'),
    '敌后破坏': StanceRow(10.0, '小规则增益量级;逐条重拍留实机判读后'),
}

_STANCE_ZERO = StanceRow(0.0, '表外环境立场恒 0')


# ===== 构建期校验(import 即炸;design §2.9)=====

def _validate_stance_coverage() -> None:
    """立场表覆盖校验:无机械成分条目必须在表;表键必须真实在册。

    - 无机械成分判定(design §2.9)= 无阵营 ∧ 不在 ENV_GIFTS ∧ 不在
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
    """系数表键完备校验:线强度档分覆盖阵容库全部强度档;赠卡档分覆盖
    档位机器全部四档(design §2.9;缺键 = 对应线/卡静默零分 → import 即炸)。"""
    _lib_tiers = {c.strength for c in COMP_LIBRARY}
    _missing_line = _lib_tiers - set(LINE_STRENGTH_SCORE)
    if _missing_line:
        raise ValueError(
            f"线强度档分缺键(COMP_LIBRARY 出现未登记强度档):{sorted(_missing_line)}")
    _gift_tiers = {'core', 'shared', 'transition', 'off'}
    _missing_gift = _gift_tiers - set(GIFT_TIER_SCORE)
    if _missing_gift:
        raise ValueError(
            f"赠卡档分缺键(gift_hit_tier 档域未登记):{sorted(_missing_gift)}")


_validate_stance_coverage()
_validate_coefficient_tables()


# ===== 总分组件(design §2.2 加法公式)=====

def _components(name: str, gs: GameState, locked_comp: str,
                demoted_endgame: bool,
                evicted: frozenset[str]) -> tuple[float, float, float, float]:
    """单环境四组件 (现金, 方向, 赠卡, 立场);未注册名 → 全 0(OCR 形变)。

    - 现金分:resolved ∧ > 0 才计,fail-closed 恒 0(design §2.2/§2.3);
    - 方向分适用面 = 概念股/邀请(design §2.4);契约/特邀专家只计赠卡;
    - 概念股额外加随机阵营赠卡分(「白得该阵营角色」;「找牌概率提高」
      「初始简易装备」v1 不计 = 申报低估向,design §2.4);
    - 立场分:表行缺省 0(表外环境立场不入表,design §2.6 表 3)。
    """
    cash, resolved = env_economy_value(name, gs)
    cash_v = cash if (resolved and cash > 0) else 0.0
    env = get_env(name)
    faction = env.faction if env is not None else ''
    _dir = 0.0
    if env is not None and env.category in ('概念股', '邀请'):
        _dir = line_value(faction, locked_comp, demoted_endgame, evicted)
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
    构建期派生(全 83 条均值,design §2.7)与运行时评分共用同一无轴基线,
    保证「阈值 = 同一口径的均值」。
    """
    _cash, _dir, _gift, _stance = _components(
        name, gs, locked_comp, demoted_endgame, frozenset(evicted))
    return _cash + _dir + _gift + _stance


#: 刷新阈值 = 全部 83 条环境总分的均值,构建期由注册表+系数+立场表派生为
#: 常量(单一源 = 表,不手维护数字;表改则阈值自动随动,design §2.7)。
#: 依据:重掷免费,重掷后帧最好的期望 ≥ 单抽期望 = 全表均值(实际
#: E[max of 3] > 均值,取均值 = 保守向,不高估重掷收益)。不取「下三分之一
#: 分位」——立场 0 值条目多,分位阈值会沉到 0 附近令判据失效,均值对 0 值
#: 堆积稳健。派生用裸 GameState 桩(schema_version=1,node 未写 = 开局帧,
#: 桩形模式沿 kernel/cw_env_economy 治理校验先例)。
def _derive_refresh_threshold() -> float:
    """全注册表无轴总分的均值(构建期一次)。"""
    _gs = GameState(schema_version=1)
    return sum(option_total(_n, _gs) for _n in INVESTMENT_ENVS) / len(INVESTMENT_ENVS)


REFRESH_THRESHOLD: float = _derive_refresh_threshold()


# ===== 决策入口(design §2.9)=====

def decide(options: list[str], gs: GameState, locked_comp: str,
           demoted_endgame: bool, evicted: frozenset[str] | set[str],
           config: CurrencyWarConfig) -> InvestEnvDecision | RefreshSuggestion:
    """投资环境 3 选 1 决策(纯值出口;flow 包装动作词表,design §2.9)。

    - options = 屏上候选名列表(容器序);locked_comp/demoted_endgame/
      evicted 与现役 kernel 调用的三参同源(flow 意向状态直通,design
      §2.9「意向解析留 flow」);
    - 禁选(env_forbid 命中,子串匹配与白名单一致)与自拆台(板面
      持续伤害+减益 ≥ 2 时克制 DoT/减益的候选)= 排除出候选;
    - 建议刷 = 排除槽存在 ∨ 帧最好总分 < REFRESH_THRESHOLD,且次数闸
      ``gs.env_refresh_left ≥ 1``;建议刷成立 → RefreshSuggestion,
      否则 → InvestEnvDecision(argmax 取最高,平分取先)。
    """
    env_priority = list(getattr(config, 'env_priority', []) or [])
    env_forbid = list(getattr(config, 'env_forbid', []) or [])
    if not options:
        # 空候选帧(观察层失约形态;旧 kernel decide_event 同输入返回
        # option_idx=0 的退化行为,本函数镜像防炸,不引入新语义)
        return InvestEnvDecision(idx=0, reason='empty-frame: 无候选退化')
    evicted = frozenset(evicted)
    # 板面 DoT/减益计数单帧单读(评分循环外取一次快照,沿旧机器纪律)
    board = gs.board.value or {}
    on_dot = sum(board.get(_f, 0) for _f in ('持续伤害', '减益')) \
        >= BOARD_DOT_COUNT_THRESHOLD

    scores: list[float] = []
    steers: list[float] = []
    components: list[tuple[float, float, float, float]] = []
    excluded: list[bool] = []
    for _opt in options:
        _cash, _dir, _gift, _stance = _components(
            _opt, gs, locked_comp, demoted_endgame, evicted)
        _steer = STEERING_PRIORITY_BONUS if any(
            _p in _opt for _p in env_priority) else 0.0
        _excluded = any(_p in _opt for _p in env_forbid) \
            or (on_dot and _counters_dot(_opt))
        scores.append(_cash + _dir + _gift + _stance + _steer)
        steers.append(_steer)
        components.append((_cash, _dir, _gift, _stance))
        excluded.append(_excluded)

    best_idx = _argmax_first(scores, excluded)
    if best_idx < 0:
        # 全排除退化帧(禁选/自拆台覆盖全体):排除规则失去选择面,沿旧
        # 机器退化行为取全体 argmax 最不负分者(kernel decide_event 全禁帧
        # 现状退化);design §2.2 的 argmax 语义在此帧的延展,非独立拍值。
        best_idx = _argmax_first(scores, [])
        best_reason = ('all-excluded-fallback '
                       + _breakdown(best_idx, scores, steers, components))
    else:
        best_reason = _breakdown(best_idx, scores, steers, components)

    forbidden_slot = any(excluded)
    if forbidden_slot or scores[best_idx] < REFRESH_THRESHOLD:
        # 次数闸 = gs.env_refresh_left ≥ 1(design §2.7)。Field 读数 None
        # = 观察写端读缺跳写(未观察到剩余次数),次数 ≥ 1 无法确证 →
        # 不建议刷(保守向:漏一次建议优于虚发动作;handler 侧 obs.refresh
        # 现读闸 + 容器对照闸原样,建议刷最终仍由 handler 双闸裁定)。
        refresh_left = gs.env_refresh_left.value
        if refresh_left is not None and refresh_left >= 1:
            if forbidden_slot:
                return RefreshSuggestion(reason='refresh: 禁选槽存在')
            return RefreshSuggestion(
                reason=f'refresh: 帧最好总分 {scores[best_idx]:.0f}'
                       f' < 阈值 {REFRESH_THRESHOLD:.1f}')
    return InvestEnvDecision(idx=best_idx, reason=best_reason)


def _argmax_first(scores: list[float],
                  excluded: list[bool]) -> int:
    """argmax 取最高,平分取先(design §2.2);excluded 槽不入竞争。

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
               components: list[tuple[float, float, float, float]]) -> str:
    """归因串:总分 + 四组件分解 + 转向轴(仅观测,进 reason)。"""
    _cash, _dir, _gift, _stance = components[idx]
    return (f'pick total={scores[idx]:.0f}'
            f' cash={_cash:.0f} dir={_dir:.0f} gift={_gift:.0f}'
            f' stance={_stance:.0f} steer={steers[idx]:.0f}')
