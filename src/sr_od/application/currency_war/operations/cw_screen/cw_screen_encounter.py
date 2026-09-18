
"""货币战争 遭遇节点 二选一处理 op(从主循环 ``CwLoop`` 拆出)。

检测「遭遇其一」+ 底部「选择」→ ``decide_encounter`` 选卡 → 点卡身选中 + 点选择确认。
2026-08-04 实测交互模型(见 ``docs/game/screens/currency_war_encounter.md``):
  点卡身(选中)→ 点选择(确认),**中间不要插空白点击**(会取消选中 → 死循环)。

✅ 分支刷新执行链:``decide_encounter`` 建议刷新(全分支词缀克 comp 时)→
  OCR「剩余次数:N」>0 且本局未用 → 文本锚定点刷新圆钮 → **重读选项 →
  重读候选再调 report(二次覆盖写)→ 重新决策 → 按新决策选**。分支刷新能力 =
  优势布局「分支刷新」授予(每局 1 次重置两卡难度/奖励;bwiki 优势布局表);
  「本局未用」判定源 = 容器 ``node_screen_refresh.encounter_refresh_used``
  计数读端(>0 = 已用)——**计数写端随画面 op 基类退役**(刷新计数记账出辖,
  由动作 op 会话承接;本 op 只保留读端闸,不写计数)。验效双通道已拆除
  (用户裁定 2026-09-10:动作 op 只管机械执行禁止验效,出处 = 验证违规清查
  报告 H1):点钮+固定等待后无条件重读,卡面未变时新观察=旧 options,重决策
  结果天然等价,「刷没刷成」不判。
  ⚠️ **触发源缺位挂账**:``read_encounter_options`` 的 affixes 恒空(卡面 UI 不显词缀,
  词缀在未建档的「敌方信息覆盖层」里)→ decide_encounter 的全克判定当前恒不触发,
  本执行链就绪但待词缀读数通道建立后才可能开火(设计约束)。

✅ Stage C2 已接:``decide_encounter``(按 comp 成型度选:未成型→低难保生存 /
  成型+词缀利→高难拿奖励 / 全分支克→刷新换批;用 pick.idx 选卡,**非默认选左**)。
  ⚠️ affix 避开分支 N/A(选项 UI 不显词缀,战后才显)。
坐标(screen_info 化债):卡身/选择经 ``cw_obs_core.area_center`` 读 screen_info
  ``currency_war_encounter``(``遭遇卡-其一/其二`` + ``按钮-选择``);缺失才用兜底常量。
  档案帧回验:sr-od-test/screens/货币战争-遭遇节点/default.webp 上 标识-遭遇节点 /
  按钮-选择 均 conf≈0.999 命中。卡身 rect center 未单独实锤(历史实测点 (665,500)/(1288,550)
  保留作兜底;rect 覆盖同卡身带)。

形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两段
直继承 SrOperation。观察 node = 画面身份门(标识-遭遇节点,miss = round_fail
交回外循环重判)+ 入口 2s 稳定期 + 稳定帧一次读(候选 + 剩余次数,同帧同源)
→ ``report_screen_encounter_obs`` 落容器 ``encounter``(空候选不写,闸在
report 内;match/gs 缺席的局外兜底路径跳过 report)→ obs 挂实例属性进决策
node。决策动作 node = 重入裁决顶部(确认已发 → 锚不在 = overlay 已关 = 选卡
落地 → 此刻才写 ``chosen_encounter`` + success 交回;锚在 = 未落地 → 清标志
重走)→ 零参决策(候选自容器槽)+ 分支刷新链(见上;per-visit 位
``encounter_refreshed_in_visit`` 置位留守决策面:首调前置段写 False、建议
处置完毕写 True 抑制再建议)→ 点卡 + 确认 → ``round_wait`` 循环推进(不烧
节点重试预算;不收敛 = 策略 bug 响亮暴露,无防御上限)。``chosen_encounter``
= 动作事实边界,留守重入裁决点写(候选未读到 / 无策略会话 / 决策越界 =
盲选 fallback 不写)。本屏 sim 腿 = 不适用(sim 引擎无遭遇决策段),等价
判据主承重 = 实机在册行为锁。
"""
import time
from typing import TYPE_CHECKING, Any, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_events import (
    EncounterOption,
)
from sr_od.application.currency_war.kernel.cw_screen_report.encounter import (
    CwScreenEncounterObs,
    report_screen_encounter_obs,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickEncounterParam,
    CwActionRefreshNodeOptionsParam,
)
from sr_od.application.currency_war.obs.cw_node_obs import (
    read_encounter_options,
    read_encounter_refresh_count,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )


class CwScreenEncounter(SrOperation):
    """遭遇节点二选一:decide_encounter 选卡(必要时先分支刷新)→ 点卡选中 + 选择确认。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-遭遇节点'   # screen_info 画面(currency_war_encounter.yml)
    # 遭遇卡卡身中心。左卡=遭遇其一(难度低,金币×2);右卡=遭遇其四(难度高,随机4费角色×3)。
    # 常量=screen_info 缺失兜底;首选 area_center('遭遇卡-其一/其二')。
    CARD_LEFT: ClassVar[Point] = Point(665, 500)
    CARD_RIGHT: ClassVar[Point] = Point(1288, 550)
    # 底部「选择」按钮中心(未选中卡时灰置禁用,选中后才可点)。常量=兜底;首选 area_center('按钮-选择')。
    SELECT_BTN: ClassVar[Point] = Point(1082, 898)
    # 分支刷新圆钮 = 「剩余次数:N」文本左侧固定偏移。归档帧
    # sr-od-test/screens/货币战争-遭遇节点/default.webp CV 双法实测:圆钮 ≈(671,899)、
    # 文本锚中心 ≈(771,899) → 偏移 = -100px;偏移错 → 刷新未命中,重读=原
    # options,重决策结果天然等价(照常选卡)。
    _REFRESH_BTN_DX: ClassVar[int] = -100

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-遭遇节点')
        # 确认已发待重入裁决的选卡快照 (options, idx)——确认点击发出后置位,
        # 下一轮决策动作 node 顶部由重入裁决查锚:锚不在 = overlay 已关(选卡
        # 落地)→ 此刻才写 chosen_encounter(出口验真通过才写的落地记录语义,
        # 时点由重入承载)。
        self._confirm_pending: tuple[list[EncounterOption], int] | None = None
        # 观察结果(观察 node 产物,决策动作 node 消费;options 空 = 读缺)。
        self._obs: CwScreenEncounterObs | None = None

    def _decide_encounter_action(
            self, options: list[EncounterOption], refresh_left: int | None,
            screen: Any) -> tuple:
        """零参决策 + 分支刷新链(决策面;观察轮已由 report 落容器首写槽)。

        刷新链分屏形态 = 同访问二次「读得=覆盖」:刷后重读候选经
        ``report_screen_encounter_obs`` 二次覆盖写(容器终值 = 刷后候选)。
        per-visit 位 ``gs.encounter_refreshed_in_visit`` = 首调前置段写
        False、建议处置(刷新发射 / 闸拒绝)后重决策发起前同步直写 True
        ——fail-loud;写 True 扩展点 = 闸拒绝分支,语义 = 本访问刷新面已
        处置禁再建议。刷新计数只读(写端出辖,读端闸 = 容器计数 >0)。
        Returns: (选卡动作|None, idx, reason, refreshed)。"""
        match = self.ctx.cw_match
        idx, reason = 0, 'default(no-options/match)'
        act = None
        refreshed = False
        if match is None or not options \
                or getattr(match, 'gs', None) is None:
            return act, idx, reason, refreshed
        gs = match.gs
        from sr_od.application.currency_war.kernel.cw_game_state import (
            ChannelSig,
        )

        def _sig() -> ChannelSig:
            return ChannelSig(family='logic_action',
                              actor='CwScreenEncounter', mode='compute')
        gs.write_logic(gs.encounter_refreshed_in_visit, False,
                       produced_by='CwScreenEncounter', sig=_sig())
        act = match.strategy.decide_encounter()
        if isinstance(act, CwActionRefreshNodeOptionsParam):
            # ===== 分支刷新执行链:建议刷新 → 有次数且未用 → 点钮 → 重读重决策 =====
            # 验效双通道已拆(用户裁定 2026-09-10 动作 op 禁验效,清查报告 H1):
            # 点钮+固定等待 → 无条件重读 → per-visit 位置 True 自然重决策。
            _used = int(gs.encounter_refresh_used.value or 0) > 0
            if _used:
                log.info('[cw-encounter] 建议刷新但本局已用(分支刷新每局1次)→ 按原评分选')
            elif refresh_left is None or refresh_left <= 0:
                log.info(f'[cw-encounter] 建议刷新但无剩余次数(读数={refresh_left})→ 按原评分选')
            else:
                # 优势布局每局只授 1 次,单次尝试语义与游戏规则对齐(点偏不
                # 重试,防「重入屏再试」的反复尝试)。计数写端出辖:发射即
                # +1 的容器计数由动作 op 会话承接,本链只点钮不记账。
                refreshed = True
                new_opts = self._try_refresh(screen)
                if new_opts:
                    options = new_opts
                    # 刷后重读候选 = 二次覆盖写(report 同形;refresh_left
                    # = 观察稳定帧同帧读数,本域仅观察面携带,report 不消费)。
                    report_screen_encounter_obs(gs, CwScreenEncounterObs(
                        options=list(options), refresh_left=refresh_left,
                        screen=screen))
            # 建议处置完毕(发射或拒绝)→ 置位抑制 + 重调取「按原评分选」
            #(选卡判据与刷新建议互斥单发后的等价形态)。
            gs.write_logic(gs.encounter_refreshed_in_visit, True,
                           produced_by='CwScreenEncounter', sig=_sig())
            act = match.strategy.decide_encounter()
            if isinstance(act, CwActionRefreshNodeOptionsParam):
                # 防御:置位后重调仍返回建议(策略未消费 per-visit 位)→
                # 不再循环,按无决策处理(失败安全)。
                act = None
        if isinstance(act, CwActionPickEncounterParam):
            if 0 <= act.idx < len(options):
                idx = act.idx
            reason = act.reason
        return act, idx, reason, refreshed

    def _try_refresh(self, screen) -> list[EncounterOption]:
        """点分支刷新圆钮 + 固定等待 + 重读选项(机械执行半;验效半已拆)。

        文本锚定位 = 执行前目标定位(执行实现层物理回答,读屏点先例 =
        prep_actions 执行器定位族):从传入帧同帧同源读「剩余次数:N」文本
        中心(与闸读数同帧,坐标与旧口径逐位一致),圆钮 = 文本左侧固定
        偏移。传入帧读缺 → 返回空表(调用方保留原候选照常选)。

        「刷没刷成」不判(用户裁定 2026-09-10:动作 op 只管机械执行禁止
        验证):点偏/无布局时重读=原 options,调用方基于新观察自然重决策
        结果天然等价;未生效治理归下一帧观察。
        Returns: 刷新后现读候选(读缺 = 空列表,调用方保留原候选照常选)。
        """
        _rd = read_encounter_refresh_count(self.ctx, screen)
        if _rd is None:
            return []
        target = Point(_rd[1][0] + CwScreenEncounter._REFRESH_BTN_DX, _rd[1][1])
        log.info(f'[cw-encounter] 建议刷新 → 圆钮@({target.x},{target.y})(文本锚定)')
        self.ctx.controller.mouse_move(target)   # bug#1 缓解
        self.ctx.controller.click(target)
        # 用户口述口径(#23,2026-09-02):遭遇屏刷新后 2s 画面稳定——
        # 原 1.2s 会在重掷尾帧读卡(读缺帧,白重读一次)。等满 2s 再重读
        # (固定等待归产生动画的操作,非判效轮询)。
        time.sleep(2.0)
        return read_encounter_options(self.ctx, self.screenshot())

    def _record_chosen(self, session: 'StrategySession | None',
                       options: list[EncounterOption], idx: int) -> None:
        """选卡落地记录面:重入裁决出口写 ``chosen_encounter``(动作事实
        边界:值在「确认已落地」重入观察后才可信,留守裁决点不进 report)。

        守卫口径=事实落地选择记录:候选未读到 / 无策略
        会话 / 决策越界 = 盲选 fallback,不写(None 保持「无记录」,防把
        盲选固化成假值)。值 = (难度档, 奖励文本),奖励文本 = 选中卡奖励
        带原文 join(未读到 = 空串;难度档恒为卡身份真值)。记录面失败不
        阻塞本轮成功。"""
        if session is None or not options or not (0 <= idx < len(options)):
            return
        try:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                ChannelSig,
                game_state_of,
            )
            _opt = options[idx]
            _gs = game_state_of(session)
            _gs.write_logic(_gs.chosen_encounter,
                            (_opt.difficulty, '/'.join(_opt.rewards)),
                            produced_by='CwScreenEncounter',
                            sig=ChannelSig(family='logic_action',
                                           actor='CwScreenEncounter',
                                           mode='compute'))
        except Exception as e:   # noqa: BLE001  记录面失败不阻塞
            log.warning(f'[cw-encounter] chosen_encounter 记录失败(不阻塞): {e}')

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """画面身份门 + 稳定帧一次读 → report 落容器。

        门 miss = round_fail 早退交回外循环重判(现役首闸同 status)。
        门后入口 2s 稳定期(用户口述口径
        docs/game/currency_war/research/screen_flow_timing.md #23,
        2026-09-02:遭遇节点右上「返回备战界面」出现后 2s 画面才稳定
        ——入口帧可能在稳定期内,立即读难度卡有读缺风险)→ 重截稳定帧
        → 候选 + 剩余次数一次读(同帧同源)→ ``report_screen_encounter_
        obs`` 落容器 ``encounter``(空候选不写,闸在 report 内)。"""
        screen = self.last_screenshot
        # live 2026-08-15:改 id_mark area(标识-遭遇节点)—— OCR「遭遇其一」在截断帧(「遭遇其」)miss;
        # 独立屏实锤(返回备战界面右上,同补给/投资策略)。
        if not self.round_by_find_area(screen, CwScreenEncounter.SCREEN_NAME,
                                       '标识-遭遇节点', crop_first=False).is_success:
            return self.round_fail('非遭遇节点屏')
        time.sleep(2.0)
        screen = self.screenshot()
        _rd = read_encounter_refresh_count(self.ctx, screen)
        obs = CwScreenEncounterObs(
            options=read_encounter_options(self.ctx, screen),
            refresh_left=(_rd[0] if _rd is not None else None),
            screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_encounter_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=10)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 零参决策 + 分支刷新链 → 点卡 + 确认 → round_wait。

        重入裁决(观察驱动,验证废除形态):上轮已发确认 → 本轮锚不在 =
        overlay 已关(选卡落地)→ 补写 chosen_encounter + success 交回;
        锚在 = 确认未落地 → 清标志重走(重选重确认)。循环推进 = round_wait
        (不烧节点重试预算;不收敛 = 策略 bug 响亮暴露,无防御上限)。"""
        if self._confirm_pending is not None:
            _opts, _idx = self._confirm_pending
            self._confirm_pending = None
            if not self.round_by_find_area(
                    self.last_screenshot, CwScreenEncounter.SCREEN_NAME,
                    '标识-遭遇节点', crop_first=False).is_success:
                self._record_chosen(
                    self.ctx.cw_match.session if self.ctx.cw_match is not None else None,
                    _opts, _idx)
                return self.round_success('遭遇节点选卡已确认(重入观察裁决)',
                                          wait=2.0)
        obs = self._obs
        options = obs.options if obs is not None else []
        refresh_left = obs.refresh_left if obs is not None else None
        screen = obs.screen if obs is not None else None
        pick, idx, reason, refreshed = self._decide_encounter_action(
            options, refresh_left, screen)
        if refreshed:
            reason = f'{reason}+分支刷新'
        log.info(f'[cw-encounter] options={[(o.difficulty, o.rewards) for o in options]} '
                 f'pick=idx{idx} refreshed={refreshed} {reason}')
        # 确认已发 → pending 置位(落地判定归下一轮重入裁决)→ 确认链机械
        # 交回(体迁 cw_overlay_pick_action.CwActionPickEncounterOp,工厂
        # 3 参形态;验关轮次结果不消费,round_wait 推进循环)。
        self._confirm_pending = (options, idx)
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_action import (
            OverlayPickExecEnv,
        )
        env = OverlayPickExecEnv(op=self)
        # 派发实例 = 生效选中下标的规范实例(决策半钳位后的 idx;策略 pick
        # 缺席/越界时本实例即唯一载体——工厂按类型解析,机械参数随实例)。
        action_op_for(CwActionPickEncounterParam(idx=idx), self.ctx, env).execute()
        return self.round_wait(wait=1)
