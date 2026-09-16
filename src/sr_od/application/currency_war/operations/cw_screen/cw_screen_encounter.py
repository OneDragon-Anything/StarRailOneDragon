
"""货币战争 遭遇节点 二选一处理 op(从主循环 ``CwLoop`` 拆出)。

检测「遭遇其一」+ 底部「选择」→ ``decide_encounter`` 选卡 → 点卡身选中 + 点选择确认。
2026-08-04 实测交互模型(见 ``docs/game/screens/currency_war_encounter.md``):
  点卡身(选中)→ 点选择(确认),**中间不要插空白点击**(会取消选中 → 死循环)。

✅ 分支刷新执行链:``decide_encounter`` 建议刷新(pick.refresh,全分支词缀克
  comp 时)→ OCR「剩余次数:N」>0 且本局未用 → 文本锚定点刷新圆钮 → **重读选项 →
  refresh_used=True 重新决策 → 按新决策选**。分支刷新能力 = 优势布局「分支刷新」授予
  (每局 1 次重置两卡难度/奖励;bwiki 优势布局表);session 级单次标志
  (``exec_state_of(session)._encounter_refresh_used``,与补给 ``_supply_refresh_used`` 同款)——
  发出刷新点击即置位,不等验效(点偏不重试,防重入反复尝试)。验效双通道
  已拆除(用户裁定 2026-09-10:动作 op 只管机械执行禁止验效,出处 = 验证
  违规清查报告 H1):点钮+固定等待后无条件重读,卡面未变时新观察=旧
  options,重决策结果天然等价,「刷没刷成」不判。
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
统一观察架构逐屏迁移首批(试点步骤 2;架构设计 §9.2 迁移步骤 4 + 开放
问题清单 B3「遭遇 = 带刷新链最复杂代表屏」):本类是 CwScreenOpBase 子类,
handle 顶部装配点分流(cw_game_ports 两端口完整在场 → 五段生命周期新路径;
缺省 None = 生产直连旧路径,handle 原序列,生产行为零变化 §9.1)。迁移
手法单一源 = CwScreenPrep 先例(验收评审):encounter_
refresh_used 写端收编 on_outcome 注册表(触发时点轴·发射型,§6.4-R-E
在册成员①;触发点 = ``_emit_refresh_click`` 两路径共用分派面,唯一性同
``_act_execute`` 先例);chosen_encounter 写端 = 选择 handler 单次逻辑写入
豁免(§2.2/§6.5-6 豁免面不扩散)留守重入裁决点写(pending 置位 =
``_act_execute`` 共享段头部,两路径同承;五段路径断链修,用户裁定
2026-09-14)。本屏 sim 腿 =
不适用(F11 例外清单:T5 前引擎无遭遇决策段),等价判据主承重 = 实机
在册行为锁 + 写入流对拍(锁面 = sr-od-test test_cw_obs_arch_event_screens.py)。
"""
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_game_ports import action_sink, observation_source
from sr_od.application.currency_war.kernel.cw_events import (
    EncounterOption,
    EncounterPick,
)
from sr_od.application.currency_war.kernel.cw_exec_state import exec_state_of
from sr_od.application.currency_war.obs.cw_node_obs import (
    read_encounter_options,
    read_encounter_refresh_count,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    ActionOutcome,
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )


@dataclass
class EncounterObservation:
    """遭遇屏观察 payload(五段之段1产物;试点步骤 2 实机转录形态)。

    - ``options``:候选卡读取(现役读链 ``read_encounter_options`` 产物);
    - ``refresh_left``:「剩余次数:N」入口稳定帧读数(分支刷新前置闸的
      语义事实;收编:原决策分支内现读识别函数上收入口观察,
      一次读,决策循环只消费本域;None = 读缺/未授予——失败安全按无刷新
      处理,读带注见 obs/cw_node_obs._REMAIN_RECT)。
    - ``screen``:稳定帧引用(刷新链执行半部的文本锚定位同帧同源读)——
      实机识别域载体,识别机制不出端口(架构设计 §2.1);sim 适配器落位
      时该域 = None 帧语义(T5 前 sim 腿不适用,F11 例外清单)。
    """

    options: list[EncounterOption]
    refresh_left: int | None = None
    screen: Any = None


class EncounterLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口,试点步骤 2)。

    内部复用现役读链(``CwScreenEncounter._observe_frame``:稳定帧时序 +
    选项读取)——识别机制(OCR/截图)不出端口(§2.1 契约三则)。sim
    实现 = T5 后辖域(引擎遭遇决策段接入),本批不建(F11 例外清单)。
    """

    def observe(self, op: 'CwScreenEncounter') -> EncounterObservation:
        return op._observe_frame()


class CwScreenEncounter(CwScreenOpBase):
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
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-遭遇节点')
        # 适配器位缺省装配(试点步骤 2;先例 = CwScreenPrep):观察口 = 实机
        # 适配器(现役读链封口);动作口 = None = 直连现役确认链
        # (``_confirm_default``,基类「None = 子类缺省实现自担」)——注入替位
        # = 构造后直接赋值(测试桩),sim 适配器 = T5 后辖域本批不建。
        self._observation_adapter = EncounterLiveObservationAdapter()
        # on_outcome 落地登记注册表(架构设计 §6.4;单一发射口,发射即触发
        # ——最严读法:两 fire 口合并,落地回执门退役):登记件
        # encounter_refresh_used(逐件申报面 EMIT_TRIGGERED_DECLARED)写端
        # 自 handle 内联位收编为注册表钩子(位置迁移语义不变,§6.5-4/
        # §6.5-6);触发点 = _emit_refresh_click(两路径共用分派面,恰触发
        # 一次——双计即计数毒化)。chosen_encounter = 选择 handler 单次
        # 逻辑写入豁免,不在收编面(§2.2)。
        self.register_outcome_hook(
            EncounterPick, self._on_refresh_emitted,
            name='encounter_refresh_used')
        # 确认已发待重入裁决的选卡(验证废除形态,用户裁定 2026-09-10):
        # (options, idx) 快照——确认点击发出后置位,下一轮重入由入口观察
        # 裁决(标识不在 = overlay 已关 = 选卡落地)→ 此刻才写 chosen_encounter
        #(出口验真通过才写的落地记录语义保持,时点后移一轮由重入承载)。
        self._confirm_pending: tuple[list[EncounterOption], int] | None = None

    def _on_refresh_emitted(self, _outcome: ActionOutcome) -> None:
        """encounter_refresh_used 写端(on_outcome 注册表·发射型钩子体;
        §6.4 收编行「遭遇刷新计数」)。原 handle 内联位逐位迁移:随刷新
        点击置位、不等验效(选择落地不置位;发射证据 refresh_click),
        单次逻辑写入(§3.4 申报豁免:自身动作事实),best-effort 记录面
        失败不阻塞。"""
        _match = self.ctx.cw_match
        if _match is None:
            return
        try:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                ChannelSig,
                game_state_of,
            )
            _gs = game_state_of(_match.session)
            _gs.write_logic(
                _gs.encounter_refresh_used,
                int(_gs.encounter_refresh_used.value or 0) + 1,
                produced_by='CwScreenEncounter',
                evidence='refresh_click',
                sig=ChannelSig(family='logic_action',
                               actor='CwScreenEncounter', mode='compute'))
        except Exception as e:   # noqa: BLE001  记录面失败不阻塞
            log.warning(f'[cw-encounter] 刷新计数记录失败(不阻塞): {e}')

    def _emit_refresh_click(self, session: 'StrategySession',
                            pick: EncounterPick) -> None:
        """刷新点击发射时点(单一发射口,发射即触发;§6.5-4 随点击置位不等
        验效)。防重入旗标 = 执行侧载体留守(非登记件);登记件写端经
        on_outcome 注册表触发——本方法 = 两路径(旧 handle / 五段循环)
        共用分派面,触发唯一性先例 = CwScreenPrep._act_execute。"""
        exec_state_of(session)._encounter_refresh_used = True
        self.fire_outcome_hooks(pick, evidence='refresh_click')

    def _observe_frame(self) -> EncounterObservation:
        """稳定帧观察链(实机适配器①封口内容):入口 2s 稳定期 → 重截 →
        选项读取 + 刷新剩余次数读(同一稳定帧一次读,payload
        携带语义事实;决策分支不再现读识别函数)。时序口径逐位保留(用户
        口述口径 #23,screen_flow_timing:入口帧可能在稳定期内,立即读
        难度卡有读缺风险)。"""
        time.sleep(2.0)
        screen = self.screenshot()
        _rd = read_encounter_refresh_count(self.ctx, screen)
        return EncounterObservation(
            options=read_encounter_options(self.ctx, screen),
            refresh_left=(_rd[0] if _rd is not None else None),
            screen=screen)

    def _try_refresh(self, screen) -> list[EncounterOption]:
        """点分支刷新圆钮 + 固定等待 + 重读选项(机械执行半;验效半已拆)。

        文本锚定位 = 执行前目标定位(执行实现层物理回答,读屏点先例 =
        prep_actions 执行器定位族):从传入帧同帧同源读「剩余次数:N」文本
        中心(与闸读数同帧,坐标与旧口径逐位一致),圆钮 = 文本左侧固定
        偏移。传入帧读缺 → 返回空表(调用方保留原候选照常选)。

        「刷没刷成」不判(用户裁定 2026-09-10:动作 op 只管机械执行禁止
        验证):点偏/无布局时重读=原 options,调用方基于新观察自然重决策
        结果天然等价;未生效治理归下一帧观察(发射即置位已拦重入,不重试)。
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
        """选卡落地记录面:出口验真通过后写 ``chosen_encounter``(设计
        边界注:值取本轮决策所用候选——刷后重读成功=刷后帧,读缺=原帧,
        与选卡决策同帧同源(旧 event_choice 遥测存证已随删除波 1 退役),
        低概率残旧接受
        §3.4.5 单选事件屏 chosen_* 写端;单次逻辑写入,§3.4 申报豁免)。

        守卫口径=事实落地选择记录(区别于 tome 的决策不可判不写式;先例结构沿用 CwScreenBookcard):候选未读到 / 无策略
        会话 / 决策越界 = 盲选 fallback,不写(None 保持「无记录」,防把
        盲选固化成假值)。值 = (难度档, 奖励文本),奖励文本 = 选中卡奖励
        带原文 join(未读到 = 空串;难度档恒为卡身份真值)。记录面失败不
        阻塞本轮成功(同刷新计数写端 try/except 口径)。"""
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

    @operation_node(name='遭遇节点', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        # 重入裁决(观察驱动,验证废除形态):上轮已发确认 → 本轮入口锚不在
        # = overlay 已关(选卡落地)→ 补写 chosen + success 交回;锚仍在 =
        # 确认未落地 → 清标志重走(计节点预算,重读重选)。两路径共用
        #(分流前挂,先于五段 lifecycle 的 observe 门)。
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
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = CwScreenPrep.run):
        # cw_game_ports 两端口完整在场(= 测试 harness 显式装配)→ 五段生命
        # 周期新路径;缺省 None = 生产直连旧路径(下方原序列,试点等价门
        # 通过前生产行为零变化)。判据用装配完整性(安装协议两端口成对),
        # 不新建开关机制(开关生命周期纪律,strategy-work §3)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        screen = self.last_screenshot
        # live 2026-08-15:改 id_mark area(标识-遭遇节点)—— OCR「遭遇其一」在截断帧(「遭遇其」)miss;
        # 独立屏实锤(返回备战界面右上,同补给/投资策略)。
        if not self.round_by_find_area(screen, CwScreenEncounter.SCREEN_NAME,
                                       '标识-遭遇节点', crop_first=False).is_success:
            return self.round_fail('非遭遇节点屏')
        # 用户口述口径(docs/game/currency_war/research/screen_flow_timing.md
        # #23,2026-09-02):遭遇节点右上「返回备战界面」出现后 2s 画面才稳定
        # ——入口帧可能在稳定期内,立即读难度卡有读缺风险(default 盲选左)。
        # 等 2s 重截稳定帧再读再决策(与 #3/#11 overlay 入口修复同型,时长按
        # 本屏用户口径 2s)。
        time.sleep(2.0)
        screen = self.screenshot()
        # (difficulty + comp 成型度:formed→高难度拿好奖励,未成型→低难度保生存)→ 选 idx。替代硬编码「选左」。
        options = read_encounter_options(self.ctx, screen)
        # 入口观察一次读(收编:刷新剩余次数归入口观察,决策分支
        # 只消费局部值——决策循环内不读屏,screen_op §1;旧路径与五段路径
        # 的 payload.refresh_left 同语义同帧)。
        _rd = read_encounter_refresh_count(self.ctx, screen)
        refresh_left = _rd[0] if _rd is not None else None
        match = self.ctx.cw_match
        idx, reason = 0, 'default(no-options/match)'
        pick = None
        _state = None   # 缺省占位(match/options 缺席时不消费;现役值源 = 容器单例)
        if match is not None and options:
            # 决策输入消费切换(迁移批次二):GameState 视图替 last_state 直读;
            # overlay 时 board 不可读 → 用上次备战快照(语义同旧,值源切 GameState)。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                game_state_of,
            )
            _state = game_state_of(match.session)
            _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
            pick = match.strategy.decide_encounter(options, _state, match.session, _cfg)
            if 0 <= pick.idx < len(options):
                idx = pick.idx
            reason = pick.reason
        # ===== 分支刷新执行链:建议刷新 → 有次数且未用 → 点钮 → 重读重决策 =====
        # 验效双通道已拆(用户裁定 2026-09-10 动作 op 禁验效,清查报告 H1):
        # 发射即置位 → 点钮+固定等待 → 无条件重读 → 带 refresh_used=True
        # 自然重决策。「刷没刷成」不判:卡面未变时新观察=旧 options,重决策
        # 结果天然等价;未生效治理归下一帧观察(防重入已拦,不重试)。
        refreshed = False
        if match is not None and pick is not None and pick.refresh:
            sess_used = getattr(exec_state_of(match.session), '_encounter_refresh_used', False)
            if sess_used:
                log.info('[cw-encounter] 建议刷新但本局已用(分支刷新每局1次)→ 按原评分选')
            elif refresh_left is None or refresh_left <= 0:
                log.info(f'[cw-encounter] 建议刷新但无剩余次数(读数={refresh_left})→ 按原评分选')
            else:
                # 发出点击即置位:优势布局每局只授 1 次,单次尝试语义与游戏
                # 规则对齐(点偏不重试,防「重入屏再试」的反复尝试)。防重入
                # 旗标留守 + 登记件经 on_outcome 注册表(发射型触发点,
                # 试点步骤 2 收编;两路径共用)。
                self._emit_refresh_click(match.session, pick)
                refreshed = True
                new_opts = self._try_refresh(screen)
                if new_opts:
                    options = new_opts
                    pick = match.strategy.decide_encounter(
                        new_opts, _state, match.session, _cfg, refresh_used=True)
                    if 0 <= pick.idx < len(new_opts):
                        idx = pick.idx
                    reason = pick.reason
        if refreshed:
            reason = f'{reason}+分支刷新'
        log.info(f'[cw-encounter] options={[(o.difficulty, o.rewards) for o in options]} '
                 f'pick=idx{idx} refreshed={refreshed} {reason}')
        # (event_choice 存证行已随 exogenous 流写入端退役删除——删除波 1。)
        # 动作执行(点卡选中 → 确认机械交回)经分派面(试点步骤 2;先例 =
        # CwScreenPrep 旧路径同经 _act_execute:注册表触发点唯一 + 未来
        # 落地型登记件两路径同享)。chosen 写端 = 确认发出后置 pending
        #(置位点 = ``_act_execute`` 共享段头部,两路径同承;五段路径断链
        # 修,用户裁定 2026-09-14),由 handle 顶部重入裁决承载(验证废除,
        # 出口验真语义时点后移)。
        return self._act_execute(pick, options, idx)

    def _act_execute(self, pick: EncounterPick | None,
                     options: list[EncounterOption], idx: int
                     ) -> OperationRoundResult:
        """动作执行分派面(五段之 act 端口分派;两路径共用)。注入动作
        适配器在场 → 经适配器机械执行(§6.2 端口,执行无返回);
        缺省 = 现役确认链直连(:meth:`_confirm_default`)。选择动作无落地
        登记件(chosen_encounter = 重入裁决承载的 write_logic 豁免),发射
        型 encounter_refresh_used 触发归 ``_emit_refresh_click``——本口
        不再收落地回执(原 progressed 门调用位已退役删除,防
        单一发射口下与刷新件混触双计)。

        pending 置位 = 本面共享段头部(用户裁定 2026-09-14 五段路径断链
        修):确认发出的选卡快照 (options, idx) 在此对两路径同承置位,
        下一轮重入由 handle 顶部裁决写 chosen_encounter——五段路径此前
        漏置位 → 裁决链断,chosen 错挂退役回执消费。"""
        self._confirm_pending = (options, idx)
        _adp = self._action_port()
        if _adp is not None:
            _adp.execute(self, pick)
            # 适配器替位桩(测试面)= 机械交回常量(端口无回执后的唯一形态)
            return self.round_success('确认已发(动作适配器机械交回)', wait=2.0)
        return self._confirm_default(idx)

    def _confirm_default(self, idx: int) -> OperationRoundResult:
        """现役确认链缺省执行体 → 薄委托(统一动作工厂批4:体迁
        ``cw_overlay_pick_action.EncounterPickOp``,经工厂 ``action_op_for``
        分派,替身缝保留;机械语义 docstring 随体:点卡选中(screen_info
        坐标缺失走历史实测兜底常量)→ 确认机械交回,验证废除——落地由
        handle 顶部重入裁决承载)。自身**不触发**注册表触发点(刷新发射
        归 ``_emit_refresh_click``,防双计)。"""
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_action import (
            OverlayPickExecEnv,
        )
        env = OverlayPickExecEnv(op=self)
        # 派发实例 = 生效选中下标的规范实例(决策半钳位后的 idx;策略 pick
        # 缺席/越界时本实例即唯一载体——工厂按类型解析,机械参数随实例)。
        action_op_for(EncounterPick(idx=idx)).execute(env)
        return env.round_result

    # ---- 五段生命周期(统一观察架构 §5.1;试点步骤 2,先例 = CwScreenPrep)----

    def lifecycle_observe(self
                          ) -> tuple[EncounterObservation,
                                     OperationRoundResult | None]:
        """段1 observe:画面身份门(标识-遭遇节点)→ 实机适配器①稳定帧
        观察(2s 稳定期 + 选项读取)。门失败 = round_fail 早退(旧 handle
        首闸逐位转录),后续段不执行。"""
        screen = self.last_screenshot
        # live 2026-08-15:改 id_mark area(标识-遭遇节点)—— OCR「遭遇其一」在截断帧(「遭遇其」)miss;
        # 独立屏实锤(返回备战界面右上,同补给/投资策略)。
        if not self.round_by_find_area(screen, CwScreenEncounter.SCREEN_NAME,
                                       '标识-遭遇节点', crop_first=False).is_success:
            return EncounterObservation(options=[]), self.round_fail('非遭遇节点屏')
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else self._observe_frame())
        return obs, None

    def lifecycle_decision_cycle(self, payload: EncounterObservation
                                 ) -> OperationRoundResult:
        """段3-5 单动作决策循环(架构设计 §5.1 后三段):decide
        (strategy_input_state → decide_encounter)→ 分支刷新链(
        发射点 = ``_emit_refresh_click``)→ act(分派面:点卡+确认机械交回;
        chosen 写端 = 确认发出置 pending,重入裁决承载,选择 handler 单次
        逻辑写入豁免 §2.2)→ on_outcome(注册表回执点)。生命周期无验证段
        (用户裁定 2026-09-10:动作未生效归动作层修可靠性,禁验证残段)。
        旧 handle 决策/刷新段逐位转录(试点步骤 2;chosen 豁免留守)。"""
        self._lifecycle_mark('decide')
        options = payload.options
        # (difficulty + comp 成型度:formed→高难度拿好奖励,未成型→低难度保生存)→ 选 idx。替代硬编码「选左」。
        match = self.ctx.cw_match
        idx, reason = 0, 'default(no-options/match)'
        pick = None
        _state = None   # 缺省占位(match/options 缺席时不消费;现役值源 = 容器单例)
        if match is not None and options:
            # 决策输入消费切换(迁移批次二):GameState 视图替 last_state 直读;
            # overlay 时 board 不可读 → 用上次备战快照(语义同旧,值源切 GameState)。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                game_state_of,
            )
            _state = game_state_of(match.session)
            _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
            pick = match.strategy.decide_encounter(options, _state, match.session, _cfg)
            if 0 <= pick.idx < len(options):
                idx = pick.idx
            reason = pick.reason
        # ===== 分支刷新执行链:建议刷新 → 有次数且未用 → 点钮 → 重读重决策 =====
        # 验效双通道已拆(同旧路径,清查报告 H1):发射即置位 → 点钮+固定
        # 等待 → 无条件重读 → 带 refresh_used=True 自然重决策。
        refreshed = False
        if match is not None and pick is not None and pick.refresh:
            sess_used = getattr(exec_state_of(match.session), '_encounter_refresh_used', False)
            if sess_used:
                log.info('[cw-encounter] 建议刷新但本局已用(分支刷新每局1次)→ 按原评分选')
            elif payload.refresh_left is None or payload.refresh_left <= 0:
                log.info(f'[cw-encounter] 建议刷新但无剩余次数(读数={payload.refresh_left})→ 按原评分选')
            else:
                # 发出点击即置位:发射型触发点两路径共用(见
                # _emit_refresh_click;语义口径同旧路径逐位)。
                self._emit_refresh_click(match.session, pick)
                refreshed = True
                new_opts = self._try_refresh(payload.screen)
                if new_opts:
                    options = new_opts
                    pick = match.strategy.decide_encounter(
                        new_opts, _state, match.session, _cfg, refresh_used=True)
                    if 0 <= pick.idx < len(new_opts):
                        idx = pick.idx
                    reason = pick.reason
        if refreshed:
            reason = f'{reason}+分支刷新'
        log.info(f'[cw-encounter] options={[(o.difficulty, o.rewards) for o in options]} '
                 f'pick=idx{idx} refreshed={refreshed} {reason}')
        # (event_choice 存证行已随 exogenous 流写入端退役删除——删除波 1。)
        # —— 段4 act(分派面;pending 置位 = 分派面共享段头部,两路径同承)
        #      + 段5 on_outcome(注册表回执点)
        self._lifecycle_mark('act')
        rs = self._act_execute(pick, options, idx)
        self._lifecycle_mark('on_outcome')
        # chosen 写端 = 重入裁决点承载(handle 顶部 pending 分支;五段路径
        # 断链修,用户裁定 2026-09-14:退役回执 ``rs.is_success`` 消费删除
        # ——round 成功态 = 轮次流转语义非动作落地回执(_overlay_confirm
        # 出口同口径),「确认已发」≠「已落地」,落地判定归下一帧重入观察)。
        return rs
