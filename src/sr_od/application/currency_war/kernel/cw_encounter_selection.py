"""货币战争 遭遇结算观测基建(环 + 经验表 + 兑现回调)+ 装填拨盘槽。

本模块 = 裁定 9(strategy-docs/04_survival_budget.md 判据来源裁定表第 9 行,
用户 2026-09-12 逐项确认)授权的敌方通道结算观测持久化基建:

- 结算观测环 :class:`SettlementRing` 与遭遇经验表 :class:`EncounterLog`
  (GameState 平级结构,生命周期 = 局);
- 结算行入环单一写端 :func:`record_settlement_row`(守卫抑制与残留排除
  两分支汇合后唯一入口;生产写端 = ``cw_screen_battle_wait``
  ``_cw_selection_write`` 环写位);
- 遭遇奖励兑现回调 :func:`claim_encounter_reward`(结算确认链挂点;
  记账语义,非选档策略)。

遭遇**选档判据本体**已迁策略层
``strategies/impl/mandate_v1/encounter_pick.py``(能力态直通形;宪法五:
判据值/序随策略本体驻策略层;判据语义正本 = strategy-docs/31 号稿)——
本模块不再含任何选档打分与标定判据面。窗口读口
``SettlementRing.last_normal_battles`` 与经验读口
``EncounterLog.tier_cleared`` 原样保留(迁移后消费方 = 策略层画面文件)。

**D_ENC_VARIANT 装填拨盘(本模块唯一标定槽;非选档判据)**:遭遇结算行
``difficulty_node`` 装填双态分支(``cw_screen_battle_wait``
``_cw_selection_write`` 直依此槽——裁定 9 持久化面自身的依赖):None =
未定案(普战行 observation 直装、遭遇行恒 None,保守前置形态);'i' =
装遭遇自身备战帧敌方难度读数;'ii' = 装前一普战写入值(carry 自证态;简报值无
容器入口,relay 白名单不含 enemy_difficulty,毒化四通道封闭)。定案批/
测试经 :func:`apply_calibration` 注入(只填 None 槽,幂等)。
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
    )
    from sr_od.application.currency_war.obs.cw_settlement_obs import (
        RoundOutcome,
    )

# ===== 装填拨盘槽(唯一标定槽;选档判据面已迁策略层,本槽仅剩装填语义)=====

#: D_enc 读点归属:'i'(遭遇自身备战帧)/'ii'(前一普战写入,carry 自证
#: 形态)/None = 未定案(装填保守前置:普战行 observation 直装、遭遇行
#: 恒 None)。拨动的是 D_enc 的**记账口径**;选档判据已不读它。
D_ENC_VARIANT: str | None = None

# ===== 注入面(装填拨盘定案批/测试的注入位;只填 None 槽,幂等)=====

_CALIBRATABLE = ('D_ENC_VARIANT',)


def apply_calibration(**kw: object) -> None:
    """标定值注入(只填 None 槽,幂等;生产注入单点 = 装填拨盘定案批)。

    非 None 现值不覆盖(重放/重跑安全);未知键名抛错(防拼写错静默丢
    注入)。测试注入也走本口(与策略层
    ``encounter_pick.apply_calibration`` 的 fill 双键注入口物理隔离,
    互不可见——两套标定面互不写入)。
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
    #: 战后小队 HP(RoundOutcome.hp_after 透传;None = 读缺/删失——
    #: 环写端现成持有该值,原丢弃改入行)。消费面 = 完胜判定「相邻两
    #: 结算帧 hp 差分」基准(cw_env_grants.check_env_deploy_lock_perfect:
    #: hp 只在结算与卡面效果处变化,相邻两结算帧间 hp 差 = 本场损血);
    #: 既有消费面(last_normal_battles/EncounterLog)不读本字段 = 新增
    #: 零扰。宁缺勿造:None 不参与判定。
    hp_after: int | None = None


class SettlementRing:
    """结算观测环(深度 10;窗口提取与兑现回调读源单一源)。

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
                                    else row.encounter_tier),
                    hp_after=(kept.hp_after if kept.hp_after is not None
                              else row.hp_after))
                return 'merged'
        self._rows.append(row)
        return 'ring'

    def last_normal_battles(self, n: int = 2) -> list[_RingRow]:
        """最近 n 个普通战斗行(窗口提取;不足 n = 返回实有行)。

        窗口读口保留面:现役消费方 = 策略层画面文件
        ``mandate_v1/encounter_pick.py``(κ_S 能力态窗口)。
        """
        return [r for r in self._rows if r.node_type == '普通战斗'][-n:]

    def last_row(self) -> _RingRow | None:
        """尾行(最近结算行;空环 None)。兑现回调双证第二腿读口
        (claim_encounter_reward:尾行 node_type = 本局节点类型入环真值;
        环写端在宿主结算读点位,先于结算确认 op 派发)。"""
        return self._rows[-1] if self._rows else None

    def last_two_rows(self) -> list[_RingRow]:
        """最近至多两行(时序旧→新,[-1] = 尾行;不足返回实有行)。
        消费面 = 完胜判定相邻帧 hp 差分基准(尾行 killed 判胜、前一行
        hp_after 为本场血量基准;cw_env_grants.check_env_deploy_lock_
        perfect 单一消费方)。"""
        return list(self._rows)[-2:]

    def __len__(self) -> int:
        return len(self._rows)


class EncounterLog:
    """遭遇经验表(本局全量遭遇行;环深不影响——环旋转不丢经验行)。

    其五/其六(Δ 无源档)的唯一可及通道:该档存在 killed=True 的
    历史遭遇行 → 可及(经验正证据;过线操作定义 = killed=True 无条件
    有效)。生命周期 = 局(跨局持久化待办另行立项)。
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
        """该难度档本局是否存在 killed=True 遭遇行(经验正证据)。

        读口保留面:现役消费方 = 策略层画面文件
        ``mandate_v1/encounter_pick.py``(其五/六经验档层)。"""
        return any(r.encounter_tier == tier and r.killed is True
                   for r in self._rows)


def game_start_reset(gs: GameState) -> None:
    """开局清空(生命周期 = 局)。

    孤儿态申报(迭代 2026-09-24-encounter-screen-strategy-migration
    design §2.1):全仓零调用——环/经验表的局生命周期实际由 GameState
    平级字段 default_factory 冷建承担(每局新容器,开局即空);本钩子 =
    生命周期设计意图的已登记保留面(显式复位口),不随判据迁移删除。
    """
    gs.settlement_ring.reset()
    gs.encounter_log.reset()


def record_settlement_row(gs: GameState, outcome: RoundOutcome, *,
                          plane: int, round_num: int, node_type: str,
                          difficulty_node: float | None,
                          encounter_tier: int | None,
                          residual: bool = False,
                          suppressed: bool = False) -> str:
    """结算行入环口(构造唯一点下游、 守卫两分支汇合后调用;单一写端)。

    - suppressed=True(守卫抑制形态:killed 非 False 的 1f 遥测行)
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
                   encounter_tier=encounter_tier,
                   hp_after=outcome.hp_after)
    verdict = gs.settlement_ring.offer(row)
    gs.encounter_log.append(row)
    return verdict


# ===== 遭遇奖励兑现回调(结算确认链挂点;迭代 2026-09-21-event-refresh-
# unify-supply-pick §2.4,attack3 X4/X7 + R1 复攻定案后形态, r2)=====

def claim_encounter_reward(gs: GameState) -> str:
    """遭遇奖励兑现(纯容器读零读屏;``CwOpSettleConfirm`` 确认点击后、
    推进上报前调——语义顺序 = 先记账后推进,并防御下一备战帧观察早到
    覆写 node 镜像;``report_node_advance`` 只推进 node_pos 不写镜像,
    推进前后调对读值无差别)。

    判据(design §2.4,attack3 X4/X7 + R1 定案):
    - 节点判遭遇 = **双证**——``gs.node`` 镜像(:func:`node_kind_of`,
      最近备战帧观察的下一节点类型,英文 token)== ``'encounter'``
      **∧** ``gs.settlement_ring`` 尾行 ``node_type == '遭遇'``(本局
      结算行入环真值;环写端 ``record_settlement_row`` 在宿主
      ``_record_round_outcome`` 环写位,先于确认 op 派发且在结算覆盖
      best-effort try 块之外。原「结算行 note」载体不可实现——note
      仅落 journal 行非容器域,attack3 R1 定案,落地取 ring 尾行);
      **假阴性申报(attack3 R4)**:双证存在同源面,镜像缺失遭遇局
      ring 行落 ``'普通战斗'`` → fail-closed 漏兑现(漏记非误记,
      方向安全,归观察可靠性治理);
    - 达标 = 容器结算域 ``progress_delta > 0`` **单判**(机制依据 =
      combat.md §3「遭遇奖励 = 伤害进度达标制,非清场制」;killed 不入
      判据:结算链 killed 为 progress 符号派生值——HP 对比兜底腿已删除,
       胜负判定必须在结算画面识别出来);``None`` = 删失不兑现;
    - ``chosen_encounter`` 在场 = 消费票。

    兑现 = 写 ``encounter_reward_claimed``(所选 (难度档,奖励文本),
    单槽逐遭遇覆盖)**并随即清 ``chosen_encounter``(单次消费;清除写
    = 同族 sig ``write_logic(None)``,actor 与兑现写一致,attack3 R3
    配对申报)**——一并收敛三条误兑现面:node 镜像残留(后续非遭遇局
    chosen 恒空)、驻留重入轮(重触发时 chosen 已空,天然幂等零标志)、
    结算覆盖 best-effort 失败的陈旧窗(上一场兑现已清 chosen,ring 腿
    又收掉大半;残余 = 本场覆盖失败 ∧ 上一场同为遭遇 ∧ 本场 chosen
    已写的低频组合,后果 = 语义账面脏行非资金操作,如实申报不设额外
    防线)。

    数值不直写(防双源):金币真值 = ``settle_truth`` 结算读数、随机
    4费角色 = bench 观察(以实际观察为准);本记录 = 语义账面(现役消费面 =
    审计投影唯一,策略器收益对账读端待办——attack3 R5)。

    Returns: 归因串('not-encounter'/'ring-mismatch'/'not-qualified'/
    'no-chosen'/'claimed')。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        ChannelSig,
        node_kind_of,
    )
    if node_kind_of(gs) != 'encounter':
        return 'not-encounter'
    _tail = gs.settlement_ring.last_row()
    if _tail is None or _tail.node_type != '遭遇':
        return 'ring-mismatch'
    _st = gs.settlement.value
    if _st is None or _st.progress_delta is None \
            or int(_st.progress_delta) <= 0:
        return 'not-qualified'
    _chosen = gs.chosen_encounter.value
    if not isinstance(_chosen, tuple) or not _chosen:
        return 'no-chosen'
    _sig = ChannelSig(family='logic_action',
                      actor='CwOpSettleConfirm', mode='compute')
    gs.write_logic(gs.encounter_reward_claimed,
                   (int(_chosen[0]), str(_chosen[1])),
                   produced_by='CwOpSettleConfirm', sig=_sig)
    gs.write_logic(gs.chosen_encounter, None,
                   produced_by='CwOpSettleConfirm', sig=_sig)
    return 'claimed'
