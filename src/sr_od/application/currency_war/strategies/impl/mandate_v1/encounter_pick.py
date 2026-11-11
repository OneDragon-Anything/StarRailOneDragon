"""遭遇画面策略(mandate_v1;宪法六「一画面一策略文件」兑现)。

画面 = 货币战争-遭遇节点(选难度档二选一 + 每局一次分支刷新)。决策本体
= 能力态直通形:κ_S 三态表 + 边缘态天花板 + 经验档层 + 奖励序数 tiebreak
+ 刷新阀,判据语义单一源 = 正本
strategy-docs/31_encounter_screen.md(§1 裁定登记 / §2 决策结构;
立场值单一源 = 本文件立场常量区)。
可及性比值分支(g^(D_win−D_enc) ≥ f_min)已停用(P64:敌方难度读数→敌难度静态映射
不可标定)——能力态直接判,t ≤ 4 档零标定可及;其五/六(Δ 无源档)走
经验档层交集。

本文件 = 遭遇判据线载体(宪法五:换一套策略实现会要不同的值/序,故判据
值/序随本体驻策略层):立场常量区(【拍】登记)、fill 双定案槽、
reward_tier 档序、三态表均在本文件。生产接入调用 = flow.decide_encounter
直调本文件 :func:`decide`(kernel 侧判据面已迁出删除,31 号稿 §1
迁移注记)。

窗口口径 = 结算观测环最近 2 个普通战斗行(普战口径;奖励/遭遇/boss 行
不入窗,31 号稿 §2.1 窗口口径裁定)。刷新闸内嵌:读
``gs.encounter_refresh_left`` 剩余语义(None = 未观察 → 不可刷,
fail-closed),不设 refresh_used 参。

输出契约:纯值 dataclass(:class:`EncounterPickDecision` /
:class:`EncounterRefreshSuggestion`),不含动作词表——动作包装留 flow
(照 supply/invest_env 同构,便于直测与 sim 复用预留)。
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_events import (
        EncounterOption,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
    )

# ===== 立场常量区(【拍】登记表:两闸门值集中一处,值单一源在代码)=====
# 形态依据 = 31 号稿 §1 章程修订:偏好型闸门量按「闸门位立场值」登记(登记即
# 立场、零拟合零观测,不经【拟】纪律);非注入面(apply_calibration 不覆盖),
# 重拍 = 直接编辑本区(None → 过目值),commit 即过目凭据。两值已过目
# 批准(2026-09-24,同一裁决门;用户备注:暂定值,实机遥测累积后重拍,
# 重拍触发器 = 遭遇帧判读积累)。
# 任一常量置 None = 立场未过目 → :func:`decide` 走重拍回退态:恒最低档
# 零刷新,reason = 'e3-simple|dark-fallback:stance-unconfirmed'
# (fail 向显式保守缺省,非标定型暗装;31 号稿 §1 立场登记)。

#: 边缘态可及难度天花板:κ_S = 边缘时难度档 t ≤ 本值才可及(保守向:
#: 能力缺口最近出现过、无余量论证)。
EDGE_CAP: int | None = 2

#: 奖励偏好序过目闸:True = 下方 reward_tier 档序(钻 0 < 装备 1 <
#: 金币 2 < 末档 3,小 = 优)已过目批准。重拍改序 = 编辑档序常量并更新
#: 本登记(commit = 过目凭据)。
REWARD_ORDER_APPROVED: bool | None = True

# ===== fill 双定案槽 + 策略层注入面(随三态表连体迁;31 号稿 §4 fill 双槽)=====

#: 进度条填充方向定案:'forward'(红=已推进)/'inverted'(红=未完成,判据量
#: 改 1−fill)/None = 未定案 → fill 分支不激活(照旧 fail-closed)。
PROGRESS_BAR_DIRECTION: str | None = None
#: 进度条语义定案:'node'(节点内归一,1/2 阈值论证前提)/'plane'(位面
#: 累计,败局 fill 分级证据不采信)/None = 未定案 → fill 分支不激活。
BAR_SEMANTICS: str | None = None

#: 删失归态的 fill 阈值(节点内归一语义 (a) 的对称中点;条语义/方向未定案
#: 前该分支不激活——fill 删失分支独立成立)。双槽定案注入后成活闸门数字,
#: 注入批须按【拟】纪律登记(31 号稿 §4 申报义务)。
_FILL_EDGE_THRESHOLD = 0.5

#: 策略层注入口合法键 = fill 双键(与 kernel 侧仅收 D_ENC_VARIANT 的
#: 注入口物理隔离,两套标定面互不写入;31 号稿 §4 注入位)。
_CALIBRATABLE = ('PROGRESS_BAR_DIRECTION', 'BAR_SEMANTICS')


def apply_calibration(**kw: object) -> None:
    """fill 双槽定案值注入(只填 None 槽,幂等;生产注入单点 = E-3 标定批)。

    非 None 现值不覆盖(重放/重跑安全);未知键名抛错(防拼写错静默丢
    注入,也防误注入 kernel 侧 D_ENC_VARIANT 键——两注入口互不可见)。
    测试清场经 :func:`reset_calibration`。
    """
    mod = sys.modules[__name__]
    for k, v in kw.items():
        if k not in _CALIBRATABLE:
            raise KeyError(f'encounter_pick.apply_calibration: '
                           f'未知标定键 {k!r}(合法键 = {_CALIBRATABLE})')
        if getattr(mod, k) is None:
            setattr(mod, k, v)


def reset_calibration() -> None:
    """fill 双槽清 None(测试 fixture 清场用;生产禁调)。"""
    mod = sys.modules[__name__]
    for k in _CALIBRATABLE:
        setattr(mod, k, None)


# ===== κ_S 能力态三态表(窗口两场 killed → 足量/边缘/不足)=====

def _kappa_state(w1: bool | None, w2: bool | None,
                 fill_old: float | None, fill_new: float | None) -> str:
    """窗口两场 → 能力态('足量'/'边缘'/'不足';31 号稿 §2.2 三态表)。

    / = 窗口两场 killed(None = 删失);fill 分支 = 恰一胜时败局侧的
    进度填充率降档(进度条双定案前不激活——照旧 fail-closed,fill 只走
    删失分支)。删失优先于 fill 分支(整场按删失计)。
    """
    if w1 is None and w2 is None:
        return '不足'
    if w1 is True and w2 is True:
        return '足量'
    wins = (w1 is True) + (w2 is True)
    if wins == 1:
        # 恰一胜:另一场 = 败局(fill 分支)或删失 → 边缘;败局 fill<1/2 → 不足;
        # 另一场 killed 删失 → 边缘(删失局)。败局侧 fill 按败局在场场次取。
        other = w2 if w1 is True else w1
        if other is None:
            return '边缘'
        # other is False(败局):fill 分支仅在 (a)+forward 定案后激活
        fill_defeat = fill_old if other is w1 else fill_new
        if (BAR_SEMANTICS == 'node' and PROGRESS_BAR_DIRECTION == 'forward'
                and fill_defeat is not None
                and fill_defeat < _FILL_EDGE_THRESHOLD):
            return '不足'
        return '边缘'
    return '不足'   # 两场全败(wins == 0 且非全删失)


# ===== 奖励 tiebreak 映射(E-1;词表 → 偏好档,预注册映射无价值数值)=====

#: 奖励偏好档序(小 = 优):钻 > 装备(含工具,同档不加细分) > 金币 >
#: 未映射(末档)。序的过目登记 = 立场常量区 REWARD_ORDER_APPROVED。
_REWARD_TIER_DIAMOND = 0
_REWARD_TIER_EQUIP = 1
_REWARD_TIER_GOLD = 2
_REWARD_TIER_UNMAPPED = 3


def reward_tier(text: str) -> int:
    """奖励预览文本 → tiebreak 偏好档(纯函数;词表单一源 = 三注册表并集)。

    序(31 号稿 §2.4):文本命中钻石注册表 → 钻档;命中装备注册表(含工具
    类,同档不加细分)→ 装备档;含「金币」字面 → 金币档;映射不到(含
    空文本/奖励预览缺失)→ 末档。钻石检测集单一源 =
    kernel/cw_obs_core.DIAMOND_EQUIP_NAMES(游戏装备真值,读数域共用)。
    """
    from sr_od.application.currency_war.data.cw_equipment_data import (
        EQUIPMENT_ROSTER,
    )
    from sr_od.application.currency_war.kernel.cw_obs_core import (
        DIAMOND_EQUIP_NAMES,
    )
    t = (text or '').strip()
    if not t:
        return _REWARD_TIER_UNMAPPED
    if any(d in t for d in DIAMOND_EQUIP_NAMES):
        return _REWARD_TIER_DIAMOND
    if t in EQUIPMENT_ROSTER:
        return _REWARD_TIER_EQUIP
    if '金币' in t:
        return _REWARD_TIER_GOLD
    return _REWARD_TIER_UNMAPPED


# ===== 输出契约(纯值 dataclass,不含动作词表)=====

@dataclass(frozen=True)
class EncounterPickDecision:
    """选档决策。

    [索引定义] idx = options 列表下标(0 基;坐标系 = 调用方传入候选序
                左→右 = 画面卡列序,与选项 ``EncounterOption.idx`` 同一
                坐标系;取值时机 = 本帧决策期快照,恒稳);reason = 归因串
                (31 号稿 §2.6 格式与因词封闭枚举,仅观测)。
    """
    idx: int
    reason: str


@dataclass(frozen=True)
class EncounterRefreshSuggestion:
    """分支刷新建议(每局 ≤1 次;动作包装 CwActionRefreshNodeOptionsParam
    留 flow,次数闸已内嵌 :func:`decide`)。"""
    reason: str


# ===== 决策本体(判据值/序单一源;31 号稿 §2 决策结构)=====

def _lowest_idx(options: list[EncounterOption]) -> int:
    """最低档下标(fail 向/重拍回退态的机械执行目标;并列取输入序先)。"""
    if not options:
        return 0
    return min(range(len(options)), key=lambda i: options[i].difficulty)


def _empty_reachable_frame(options: list[EncounterOption], gs: GameState,
                           why: str
                           ) -> EncounterPickDecision | EncounterRefreshSuggestion:
    """可及集空帧的刷新阀(fail-closed;31 号稿 §2.5):剩余 ≥1 → 建议刷;
    None(未观察)/0(刷尽)→ 落最低档。闸内嵌读 ``gs.encounter_refresh_left``
    剩余语义(全域规范 = screens/op-layer.md §1.4)。"""
    left = gs.encounter_refresh_left.value
    if left is not None and left >= 1:
        return EncounterRefreshSuggestion(
            reason=f'e3-simple|refresh-valve:{why}')
    return EncounterPickDecision(
        idx=_lowest_idx(options),
        reason=f'e3-simple|dark-fallback:{why}')


def decide(options: list[EncounterOption], gs: GameState,
           ) -> EncounterPickDecision | EncounterRefreshSuggestion:
    """遭遇选档决策(能力态直通形;纯值出口,flow 包装动作词表)。

    决策序(31 号稿 §2):立场过目门 → 窗口提取(最近 2 普战行,<2 =
    窗口不足独立态)→ κ_S 三态(不足 → 阀)→ 可及集(cap 过滤在前;
    t ≤ 4 能力态直判,t ≥ 5 经验档层交集)→ 空集 → 阀 → 选档
    (difficulty 最高主序,同档 tiebreak 档序小 = 优,仍并列输入序先)。

    - options = 屏上候选(gs.encounter payload 槽序,左→右 = 画面卡列序);
    - 空候选帧 → idx=0 no-options(纯函数定义完备;现役观察层守卫——
      读不到标题返空列表零点击——下不可达);
    - 签名最小:无阵容意向参(词缀轴是死输入,难度轴按能力态);
      无 refresh_used 参(刷新次数闸内嵌读状态容器剩余语义)。
    """
    if not options:
        return EncounterPickDecision(idx=0, reason='no-options')
    if EDGE_CAP is None or REWARD_ORDER_APPROVED is None:
        # 立场未过目 → 重拍回退态:恒最低档零刷新(窗口/κ_S 不评估)
        return EncounterPickDecision(
            idx=_lowest_idx(options),
            reason='e3-simple|dark-fallback:stance-unconfirmed')
    ring = gs.settlement_ring
    log = gs.encounter_log
    window = ring.last_normal_battles(2)
    if len(window) < 2:
        # 窗口不足独立态(数据不足 ≠ 能力不足,与 κ_S「不足」分因可判读)
        return _empty_reachable_frame(options, gs, 'window-insufficient')
    w_new, w_old = window[1], window[0]
    kappa = _kappa_state(w_old.killed, w_new.killed,
                         w_old.progress_fill_ratio, w_new.progress_fill_ratio)
    if kappa == '不足':
        return _empty_reachable_frame(options, gs, 'kappa-不足')
    # 可及集:cap 过滤在前(边缘态下 t ≥ 3 全排除,含其五/六;足量态
    # cap = 6 = 档位值域上界,与判据权威版本逐位同构,不简化为无判定)
    cap = EDGE_CAP if kappa == '边缘' else 6
    reachable: list[EncounterOption] = []
    for opt in options:
        t = opt.difficulty
        if t > cap:
            continue
        if t <= 4:
            # t ≤ 4:能力态直接判(比值分支停用,零标定可及)
            reachable.append(opt)
        elif log.tier_cleared(t):
            # 其五/六(Δ 无源档):经验正证据 = 本局该档存在 killed=True
            # 遭遇行(遭遇奖励 = 伤害进度达标制,killed=True 蕴含达标,
            # 方向安全;过线操作定义 = killed=True 无条件有效)
            reachable.append(opt)
    if not reachable:
        return _empty_reachable_frame(options, gs, 'empty-reachable')
    # 选档主序:difficulty 最高;同档并列 → tiebreak 档序(小 = 优);
    # 仍并列 → 输入序先(EncounterOption.idx = 画面卡列序)
    best_t = max(o.difficulty for o in reachable)
    cands = [(o, reward_tier('/'.join(o.rewards)))
             for o in reachable if o.difficulty == best_t]
    pick_opt = min(cands, key=lambda p: (p[1], p[0].idx))[0]
    return EncounterPickDecision(
        idx=pick_opt.idx,
        reason=f'e3-simple|pick:t{best_t}|kappa={kappa}')
