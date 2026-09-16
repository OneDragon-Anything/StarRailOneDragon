"""货币战争 遭遇选档判定核(E-2 暗装落码)。

设计正本 = docs/develop/sr_od/application/currency_war/changes/
2026-09-12-encounter-selection/details/encounter-criterion-spec.md(对抗审定稿)。
本模块 = 遭遇分支选档的现役单一源;历史 EV 候选核
(strategies/impl/mandate_v1/encounter.py)已搁置让位、保留禁删。

**暗装语义(模块级契约)**:三常量(f_min/g/Δ_t)与两组定谳(进度条语义、
D_enc 读点归属)全部走本模块常量区的 None 槽——None = 未标定/未定谳 =
判据不可评 = 恒暗装(最低档 + 零刷新,与现行 fail 向行为逐位一致)。
E-3 标定批经 :func:`apply_calibration` 注入(只填 None 槽,幂等);测试经
:func:`reset_calibration` 清场。本常量区与 mandate_v1.audit.provisional
的 EV 核双槽(ENCOUNTER_G_GOLD/ENCOUNTER_DSTAT_MAP)**物理隔离**——
两套标定面互不写入,防把新判据标定值误注给已搁置核(反之亦然)。

**读点两假设(D_enc)**:遭遇节点的旗牌读值来源未定谳——(i) 遭遇节点自身
备战帧(旗牌已含 −4〔持卡时〕与档位加成)或 (ii) 前一普通战斗节点备战帧
写入值(Δ_t 取净值)。``D_ENC_VARIANT`` 为拨盘:None = 未定谳(只认
observation 现场读,最保守);'ii' = 放行 carry 自证态(容器自身历史写入,
简报值无容器入口——relay 白名单不含 enemy_difficulty,毒化四通道封闭)。
``D_ENC_VARIANT`` 拨动的是 D_enc 的**记账口径**,与线族选择(卡态轴)正交。
"""
from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_events import (
        EncounterOption,
        EncounterPick,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
    )
    from sr_od.application.currency_war.obs.cw_settlement_obs import (
        RoundOutcome,
    )

# ===== 常量区(f_min/g/Δ_t 注册落点;E-3 标定批注入单一源)=====

#: 可及性比值阈值 scaling(D_win)/scaling(D_enc(t)) ≥ f_min;值域申报
#: = (0, 1](比值阈值语义)。None = 未标定 → 暗装。
F_MIN: float | None = None
#: 指数底数(HP = c·g^D 模型的 g,旧口径 1.052,CI 缺口如实申报)。
#: 客户端配置表查表命中后升为在册口径。None = 未标定 → 暗装。
G_BASE: float | None = None
#: 档位 → Δ_t(难度增量)。判据语义 = 净值(读点判 (ii) 时:档位加成 +
#: 连胜增量 + 窗间品质/特殊加成增量 + 持卡时遭遇 −4 的净值,由 E-3 按
#: 选档结果标定,本表存标定结果);读点判 (i) 时 Δ_t 退出判据(不消费)。
#: None = 未标定 → 暗装(判 (i) 形态下不要求本表)。
DELTA_T: dict[int, float] | None = None
#: 进度条填充方向定谳:'forward'(红=已推进)/'inverted'(红=未完成,判据量
#: 改 1−fill)/None = 未定谳 → 暗装。
PROGRESS_BAR_DIRECTION: str | None = None
#: 进度条语义定谳:'node'(节点内归一,1/2 阈值论证前提)/'plane'(位面
#: 累计,败局 fill 分级证据不采信)/None = 未定谳 → 暗装。
BAR_SEMANTICS: str | None = None
#: D_enc 读点归属:'i'(遭遇自身备战帧)/'ii'(前一普战写入,carry 自证
#: 形态)/None = 未定谳 → 暗装(只认 observation 现场读的保守前置形态)。
D_ENC_VARIANT: str | None = None

#: 遭遇行 difficulty_node 装填变体(与 D_ENC_VARIANT 同拨盘、E-2 双态实现):
#: None = 未定谳(遭遇行 difficulty_node 装 None);'i' = 装遭遇自身备战帧
#: 旗牌(observation 态);'ii' = 装前一普战写入值(observation/carry 自证态)。

# ===== 注入面(E-3 标定批单一注入口;只填 None 槽,幂等)=====

_CALIBRATABLE = ('F_MIN', 'G_BASE', 'DELTA_T', 'PROGRESS_BAR_DIRECTION',
                 'BAR_SEMANTICS', 'D_ENC_VARIANT')


def apply_calibration(**kw: object) -> None:
    """标定值注入(只填 None 槽,幂等;生产注入单点 = E-3 标定批)。

    非 None 现值不覆盖(重放/重跑安全);未知键名抛错(防拼写错静默丢注入)。
    测试注入也走本口(与 mandate_v1.audit.calibration 的 EV 核注入面
    物理隔离,互不可见)。
    """
    import sys
    mod = sys.modules[__name__]
    for k, v in kw.items():
        if k not in _CALIBRATABLE:
            raise KeyError(f'cw_encounter_selection.apply_calibration: '
                           f'未知标定键 {k!r}(合法键 = {_CALIBRATABLE})')
        if getattr(mod, k) is None:
            setattr(mod, k, v)


def reset_calibration() -> None:
    """全槽清 None(测试 fixture 清场用;生产禁调)。"""
    import sys
    mod = sys.modules[__name__]
    for k in _CALIBRATABLE:
        setattr(mod, k, None)


# ===== 结算观测环 + 遭遇经验表(GameState 平级新结构;生命周期 = 局)=====

#: 环深 10 = 窗口 2 行 + 同位面极端夹行 7 + 工程余量(论证 = spec §8 环行
#: 模型;跨位面叠加形态需求可达 12 > 10 → 窗口 < 2 行 → 不足态,fail-closed
#: 安全降级)。
SETTLEMENT_RING_DEPTH: int = 10


@dataclass
class _RingRow:
    """环行 = RoundOutcome 的判据消费子集(浅拷贝语义;不回写观测半)。"""
    plane: int
    round_num: int
    node_type: str
    killed: bool | None
    progress_fill_ratio: float | None
    difficulty_node: float | None
    encounter_tier: int | None


class SettlementRing:
    """结算观测环(深度 10;判据与经验层读源单一源)。

    - 只收产结算屏节点行(普通战斗/遭遇/boss/巨星/精英/奖励;补给零行);
    - 同场去重合并:键 = (plane, round_num),后到行缺字段不覆盖先行行
      已有值(1f 遥测行 + 3b 全写行两路合并语义);
    - 深度旋转淘汰最旧行(deque maxlen);
    - 生命周期 = 局:开局 :meth:`reset` 清空(relaunch 残留行由写入端
      residual 排除判据拦截,不入环)。
    """

    def __init__(self) -> None:
        self._rows: deque[_RingRow] = deque(maxlen=SETTLEMENT_RING_DEPTH)

    def reset(self) -> None:
        """开局清空(生命周期 = 局)。"""
        self._rows.clear()

    def offer(self, row: _RingRow) -> str:
        """入环(去重合并)→ 归因:'ring'(新行)/'merged'(同键合并)。"""
        for i, old in enumerate(reversed(self._rows)):
            if old.plane == row.plane and old.round_num == row.round_num:
                j = len(self._rows) - 1 - i
                kept = self._rows[j]
                self._rows[j] = _RingRow(
                    plane=kept.plane, round_num=kept.round_num,
                    node_type=kept.node_type,
                    killed=kept.killed if kept.killed is not None else row.killed,
                    progress_fill_ratio=(kept.progress_fill_ratio
                                         if kept.progress_fill_ratio is not None
                                         else row.progress_fill_ratio),
                    difficulty_node=(kept.difficulty_node
                                     if kept.difficulty_node is not None
                                     else row.difficulty_node),
                    encounter_tier=(kept.encounter_tier
                                    if kept.encounter_tier is not None
                                    else row.encounter_tier))
                return 'merged'
        self._rows.append(row)
        return 'ring'

    def last_normal_battles(self, n: int = 2) -> list[_RingRow]:
        """最近 n 个普通战斗行(窗口提取;不足 n = 返回实有行)。"""
        return [r for r in self._rows if r.node_type == '普通战斗'][-n:]

    def __len__(self) -> int:
        return len(self._rows)


class EncounterLog:
    """遭遇经验表(本局全量遭遇行;环深不影响——环旋转不丢经验行)。

    其五/其六(Δ 无源档)的唯一可及通道:该档存在 killed=True 的
    历史遭遇行 → 可及(经验正证据;过线操作定义 = killed=True 无条件
    有效)。生命周期 = 局(跨局持久化挂账另行立项)。
    """

    def __init__(self) -> None:
        self._rows: list[_RingRow] = []

    def reset(self) -> None:
        """开局清空。"""
        self._rows.clear()

    def append(self, row: _RingRow) -> None:
        if row.node_type == '遭遇':
            self._rows.append(row)

    def tier_cleared(self, tier: int) -> bool:
        """该难度档本局是否存在 killed=True 遭遇行(经验正证据)。"""
        return any(r.encounter_tier == tier and r.killed is True
                   for r in self._rows)


def selection_state_of(gs: GameState) -> tuple[SettlementRing, EncounterLog]:
    """读取局的观测环与经验表(GameState 平级字段;dataclass 字段自带实例)。"""
    return gs.settlement_ring, gs.encounter_log


def game_start_reset(gs: GameState) -> None:
    """开局清空(生命周期 = 局;RunLoop handle_init 或首结算时调)。"""
    gs.settlement_ring.reset()
    gs.encounter_log.reset()


def record_settlement_row(gs: GameState, outcome: RoundOutcome, *,
                          plane: int, round_num: int, node_type: str,
                          difficulty_node: float | None,
                          encounter_tier: int | None,
                          residual: bool = False,
                          suppressed: bool = False) -> str:
    """结算行入环口(构造唯一点下游、W239 守卫两臂汇合后调用;单一写端)。

    - suppressed=True(W239 守卫抑制形态:killed 非 False 的 1f 遥测行)
      → 不入环。守卫抑制是防毒设计(保留现状),被抑制形态的缺口由
      E-3 离线对账的对齐率量测覆盖(留痕标记行随 hook 落盘,缺省关)。
    - residual=True(relaunch 残留结算屏行)→ 不入环(跨局污染排除;
      判定值来自结算处理入口一次判定后落存的标志,禁二次调用判定——
      ``_mark_relaunch_residual`` 带首见副作用,重复调用恒 False)。
    - 其余 → 去重合并入环;遭遇行同步入经验表。

    Returns: 归因串('suppressed'/'residual-dropped'/'ring'/'merged')。
    """
    if suppressed:
        return 'suppressed'
    if residual:
        return 'residual-dropped'
    row = _RingRow(plane=plane, round_num=round_num, node_type=node_type,
                   killed=outcome.killed,
                   progress_fill_ratio=outcome.progress_fill_ratio,
                   difficulty_node=difficulty_node,
                   encounter_tier=encounter_tier)
    verdict = gs.settlement_ring.offer(row)
    gs.encounter_log.append(row)
    return verdict


# ===== E-1:奖励 tiebreak 映射表(词表 → 偏好档;预注册映射无价值数值)=====

#: 偏好档序(小 = 优):钻 > 装备(含工具,同档不加细分) > 金币 > 未映射(末档)。
_REWARD_TIER_DIAMOND = 0
_REWARD_TIER_EQUIP = 1
_REWARD_TIER_GOLD = 2
_REWARD_TIER_UNMAPPED = 3
#: 「未映射」即末档(降级分支:奖励预览缺失/空集卡落此档;档位并列降级
#: 比较器 = (difficulty 主序, reward_tier 次序),随映射表一并定义)。
REWARD_TIER_LAST = _REWARD_TIER_UNMAPPED


def reward_tier(text: str) -> int:
    """奖励预览文本 → tiebreak 偏好档(纯函数;词表单一源 = 三注册表并集)。

    序(spec §6):文本命中钻石注册表 → 钻档;命中装备注册表(含工具类,
    工具与装备同档不加细分)→ 装备档;含「金币」字面 → 金币档;映射不到
    (含空文本/奖励预览缺失)→ 末档。E-3 全量采样顺带验证装备段序。
    """
    from sr_od.application.currency_war.data.cw_equipment_data import (
        EQUIPMENT_ROSTER,
    )
    from sr_od.application.currency_war.obs.cw_node_obs import (
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


# ===== 判据本体(κ_S 能力态 + 双值可及性 + 暗装门)=====

#: 删失归态的 fill 阈值(节点内归一语义 (a) 的对称中点;条语义/方向未定谳
#: 前该分支不激活——fill 删失分支独立成立)。
_FILL_EDGE_THRESHOLD = 0.5


@dataclass
class _Diagnostics:
    """决策诊断(E-3 配对采集通道;journal 行经 pick.reason 透传)。"""
    d_enc_value: float | None = None
    d_enc_source: str | None = None
    live_gate: str = 'not-evaluated'
    dark_reason: str | None = None


def _kappa_state(w1: bool | None, w2: bool | None,
                 fill_old: float | None, fill_new: float | None) -> str:
    """窗口两场 → 能力态('足量'/'边缘'/'不足';spec §2 三态表)。

    w1/w2 = 窗口两场 killed(None = 删失,三重兜底后仍未知);fill2 = 较新
    一场的 fill(边缘 1/2 分支用;条语义+方向未定谳前该分支不激活,fill
    只走删失分支)。删失优先于 fill 分支(整场按删失计)。
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
        # other is False(败局):fill 分支仅在 (a)+forward 定谳后激活
        fill_defeat = fill_old if other is w1 else fill_new
        if (BAR_SEMANTICS == 'node' and PROGRESS_BAR_DIRECTION == 'forward'
                and fill_defeat is not None
                and fill_defeat < _FILL_EDGE_THRESHOLD):
            return '不足'
        return '边缘'
    return '不足'   # 两场全败(wins == 0 且非全删失)


def _d_enc_snapshot(gs: GameState) -> tuple[float | None, str | None]:
    """决策读点:D_enc 口读值 + live 判别子结果(读点 = GameState 现存值)。

    判别子(未定谳前置形态)= source=='observation' ∧ 值非空;判 (ii) 后
    切换 carry 自证形态(observation/carried 自证链均过——简报值无容器
    入口,毒化四通道封闭)。门不过 → (None, source)。
    """
    f = gs.enemy_difficulty
    v = f.value
    if v is None:
        return None, f.source
    if f.source == 'observation':
        return float(v), f.source
    if D_ENC_VARIANT == 'ii' and f.source in ('carried', 'prior'):
        return float(v), f.source   # carry 自证形态(ii);prior 仍拒(非自证链)
    return None, f.source


def decide_encounter(options: list[EncounterOption], gs: GameState,
                     *, refresh_used: bool = False,
                     tiebreak: Callable[[str], int] = reward_tier,
                     ) -> EncounterPick:
    """遭遇分支选档判定(现役单一源;暗装优先,fail-closed)。

    门序(任一不过 → 暗装):常量槽(f_min/g/进度条双定谳/读点定谳;判 (ii)
    另要求 Δ_t)→ 窗口(观测环最近 2 个普通战斗行,< 2 = 不足态)→ D_win
    (窗口行 difficulty_node 现场读,None 行不候选,无可作用行 = 弃权)→
    D_enc 读点门。全过 → 可及集 = {t | g^(D_win − D_enc(t)) ≥ f_min}(其
    五/六走经验档层交集:经验表该档存在 killed=True 行 → 可及)。

    选档:可及集按 difficulty 主序取最高【拟·档位↑⇒奖励价值↑,E-3 采样
    验证;失败降级为 tiebreak 全序】;同档并列按 tiebreak 映射(钻>装备>
    金币>末档)。可及集空 → 刷新逃生阀(本局未用才建议);已用/不可刷新
    → 最低档。暗装 = 最低档 + 零刷新(reason 带门诊断,e3-simple 归因串)。
    """
    from sr_od.application.currency_war.kernel.cw_events import (
        EncounterPick,
    )
    diag = _Diagnostics()
    diag.d_enc_value, diag.d_enc_source = _d_enc_snapshot(gs)

    def _dark(why: str) -> EncounterPick:
        diag.dark_reason = why
        return EncounterPick(
            idx=_lowest_idx(options), refresh=False,
            reason=f'e3-simple|dark-install:{why}'
                   f'|d_enc={diag.d_enc_value}({diag.d_enc_source})'
                   f'|live={diag.live_gate}')

    if F_MIN is None:
        return _dark('f_min-uncalibrated')
    if G_BASE is None:
        return _dark('g-uncalibrated')
    if BAR_SEMANTICS is None or PROGRESS_BAR_DIRECTION is None:
        return _dark('bar-semantics-undecided')
    if D_ENC_VARIANT is None:
        diag.live_gate = 'pre-verdict-observation-only'
        return _dark('d_enc-readpoint-undecided')
    if D_ENC_VARIANT == 'ii' and DELTA_T is None:
        return _dark('delta_t-uncalibrated')
    diag.live_gate = ('pass-observation' if diag.d_enc_value is not None
                      else f'rejected({diag.d_enc_source})')

    ring, log = selection_state_of(gs)
    window = ring.last_normal_battles(2)
    if len(window) < 2:
        # 窗口不足(含跨位面叠加形态):不足态 = 可及集空,刷新阀仍可用
        # (fail-closed 最低档;非暗装全同),无窗口行则无 D_win 可查。
        if not refresh_used:
            return EncounterPick(idx=_lowest_idx(options), refresh=True,
                                 reason='e3-simple|refresh-valve:window-insufficient')
        return _dark('window-insufficient-refresh-used')
    w_new, w_old = window[1], window[0]
    kappa = _kappa_state(w_old.killed, w_new.killed,
                         w_old.progress_fill_ratio, w_new.progress_fill_ratio)
    if kappa == '不足':
        # 刷新逃生阀:∅ 唯一触发判据(三态同口径:不足/边缘/足量下可及档
        # 全为 Δ 无源档且经验无正证据);本局未用才建议。
        if not refresh_used:
            return EncounterPick(idx=_lowest_idx(options), refresh=True,
                                 reason='e3-simple|refresh-valve:kappa-不足')
        return _dark('kappa-不足-refresh-used')
    d_win = w_new.difficulty_node
    if d_win is None:
        d_win = w_old.difficulty_node
    if d_win is None:
        return _dark('d_win-no-live-row')

    d_enc_raw = diag.d_enc_value
    if d_enc_raw is None:
        return _dark('d_enc-gate-rejected')
    # 边缘态:天花板 = 其二(缺口最近出现过,无余量论证,保守向);足量不设限
    cap = 2 if kappa == '边缘' else 6

    reachable: list[tuple[int, EncounterOption]] = []
    for opt in options:
        t = opt.difficulty
        if t > cap:
            continue
        if t <= 4:
            # D_enc(t):判 (i) = 直读真值(Δ_t 退出);判 (ii) = 净值(Δ_t 注入)
            d_enc_t = (d_enc_raw if D_ENC_VARIANT == 'i'
                       else d_enc_raw + float(DELTA_T.get(t, 0.0)))
            if g_ratio(d_win, d_enc_t) >= F_MIN:
                reachable.append((t, opt))
        else:
            # 其五/六(Δ 无源档):经验档层交集——本局该档存在 killed=True 遭遇行
            if log.tier_cleared(t):
                reachable.append((t, opt))
    if not reachable:
        if not refresh_used:
            return EncounterPick(idx=_lowest_idx(options), refresh=True,
                                 reason='e3-simple|refresh-valve:empty-reachable')
        return _dark('empty-reachable-refresh-used')
    # 主序:difficulty 最高;同档并列 → tiebreak 映射(小 = 优)
    best_t = max(t for t, _o in reachable)
    cands = [(o, tiebreak('/'.join(o.rewards)))
             for t, o in reachable if t == best_t]
    pick_opt = min(cands, key=lambda p: (p[1], p[0].idx))[0]
    return EncounterPick(idx=pick_opt.idx, refresh=False,
                         reason=(f'e3-simple|pick:t{best_t}'
                                 f'|kappa={kappa}|d_win={d_win}'
                                 f'|d_enc={d_enc_raw}({diag.d_enc_source})'))


def g_ratio(d_win: float, d_enc: float) -> float:
    """可及性比值 g^(D_win − D_enc)(指数模型化简形;G_BASE None 时抛错
    ——调用方门序保证不触)。"""
    if G_BASE is None:
        raise ValueError('g_ratio: G_BASE 未标定(门序违例)')
    return G_BASE ** (d_win - d_enc)


def _lowest_idx(options: list[EncounterOption]) -> int:
    """最低档下标(暗装/刷新阀的机械执行目标;并列取先读支)。"""
    if not options:
        return 0
    return min(range(len(options)), key=lambda i: options[i].difficulty)
