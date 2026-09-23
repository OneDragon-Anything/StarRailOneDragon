
"""货币战争 遭遇节点 二选一处理 op(从主循环 ``CwLoop`` 拆出)。

检测「遭遇其一」+ 底部「选择」→ ``decide_encounter`` 选卡 → 点卡身选中 + 点选择确认。
2026-08-04 实测交互模型(见 ``docs/game/screens/currency_war_encounter.md``):
  点卡身(选中)→ 点选择(确认),**中间不要插空白点击**(会取消选中 → 死循环)。

✅ 分支刷新执行链(刷新 = 终结动作,用户裁定 2026-09-21,全域规范 =
  ``op-layer.md`` §1.4):``decide_encounter`` 建议刷新(全分支词缀克
  comp 时)∧ 剩余闸放行 → 文本锚定点刷新圆钮一次 + 2s 固定等待 →
  ``round_success`` 终结交回外循环 → 重进 = 入口重建(新选项由入口观察
  现读承载)。**访问内零重读、零二次覆盖写、零重决策、零新增读屏点**。
  分支刷新能力 = 优势布局「分支刷新」授予(每局 1 次重置两卡难度/奖励;
  bwiki 优势布局表)。**刷新闸 = 剩余语义观察真值**(同裁定):闸读源 =
  容器 ``node_screen_refresh.encounter_refresh_left``(观察 node 同帧
  「剩余次数:N」读数经 report 摄入,读缺跳写);剩余 ≤0 或 None =
  拒绝 → 重调一次决策按原评分选(单轮内有界)。原 per-visit 位与「已用」
  计数读闸随剩余闸退役(考古走 git)。
  活锁方向安全:建议刷新 → 放行 → 终结(访问结束)∨ 拒绝 → 重调一次
  落选卡 → 确认链;两分支都终结访问或落选卡,``round_wait`` 循环面对
  刷新建议不再存在。
  ⚠️ **词缀读数未接线**:``read_encounter_options`` 的 affixes 恒空(选项卡面
  UI 不显词缀;词缀住「货币战争-敌人信息浮层」覆盖层——已建档,chips OCR
  实测可读,读数通道就绪)→ decide_encounter 的全克判定当前恒不触发,
  接线消费待后续批。

✅ Stage C2 已接:``decide_encounter``(按 comp 成型度选:未成型→低难保生存 /
  成型+词缀利→高难拿奖励 / 全分支克→刷新换批;用 pick.idx 选卡,**非默认选左**)。
  ⚠️ affix 避开分支 N/A(选项 UI 不显词缀,战后才显)。
坐标(screen_info 化债):卡身/选择经 ``cw_obs_core.area_center`` 读 screen_info
  ``currency_war_encounter``(``遭遇卡-其一/其二`` + ``按钮-选择``);缺失才用兜底常量。
  档案帧回验:sr-od-test/screens/货币战争-遭遇节点/default.webp 上 标识-遭遇节点 /
  按钮-选择 均 conf≈0.999 命中。卡身 rect center 未单独实锤(历史实测点 (665,500)/(1288,550)
  保留作兜底;rect 覆盖同卡身带)。

形态(迭代 2026-09-18-screen-op-flat-report;3.3 扩围修订 = 迭代
2026-09-21-event-refresh-unify-supply-pick):观察 node + 决策动作 node
两段直继承 SrOperation。观察 node = 画面身份门(标识-遭遇节点,miss =
round_fail 交回外循环重判)→ 门命中即用 node runner 帧一次读(候选 +
剩余次数,同帧同源;**入口 2s 稳定期已删**,用户裁定 2026-09-21:原
「返回备战界面出现后 2s 才稳定」口径废弃,见 screen_flow_timing.md #23
supersession 注;候选读缺的失败安全 = act 空候选零点击终结交回重读,
禁盲选确认——选卡确认不可逆消耗本节点)→ ``report_screen_encounter_obs``
落容器 ``encounter`` + ``encounter_refresh_left``(空候选整函数早退不写
含 left,闸在 report 内;match/gs 缺席的局外兜底路径跳过 report)→ obs +
刷新文本锚点挂实例属性进决策 node。决策动作 node = 零参决策(候选自
容器槽)+ **派发即终结**(投资两屏/补给 3.1 同形态,重入裁决已退役):
刷新 = 点钮一次 + 2s → ``round_success`` 终结交回 / 选卡 = 派发确认链
(机械链 + ``chosen_encounter`` 即时上报在动作 op 内)→ ``round_success``
终结交回 / 空候选 = 零点击终结交回重读——三出口均终结访问,
``round_wait`` 循环面对刷新建议不存在。决策返回词表外/None = 具名
round_fail 零盲发;pick idx 越界 = 守卫断言 AssertionError;两守卫均在
派发前、零点击(口径 = ``screens/encounter.md`` §2)。确认未生效 =
代码 bug,overlay 残留由外循环按当前画面重识别重派(修法 = 点击链
可靠性)。
``chosen_encounter`` 写端 = 动作侧即时上报(kernel/cw_action_report/
pick_encounter.py,发射即写;确认未生效窗内为暂态意图值由重派覆盖自愈,
奖励兑现回调的消费防线 = 兑现后清 chosen 单次消费,见 kernel/
cw_encounter_selection.py::claim_encounter_reward)。sim 腿:刷新链不
适用(sim 无遭遇刷新执行面,design §2.3 申报);遭遇选档决策有 sim
消费段(M16),判据等价承重 = kernel 判据函数 + 实机在册行为锁。
"""
import time
from typing import TYPE_CHECKING, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
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
    pass


class CwScreenEncounter(SrOperation):
    """遭遇节点二选一:decide_encounter 选卡(必要时先分支刷新)→ 点卡选中 + 选择确认。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-遭遇节点'   # screen_info 画面(currency_war_encounter.yml)
    # 分支刷新圆钮 = 「剩余次数:N」文本左侧固定偏移。归档帧
    # sr-od-test/screens/货币战争-遭遇节点/default.webp CV 双法实测:圆钮 ≈(671,899)、
    # 文本锚中心 ≈(771,899) → 偏移 = -100px;偏移错 → 刷新未命中,终结交回后
    # 外循环重进 = 入口重建重读,失败安全。
    _REFRESH_BTN_DX: ClassVar[int] = -100

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-遭遇节点')
        # 观察结果(观察 node 产物,决策动作 node 消费;options 空 = 读缺)。
        self._obs: CwScreenEncounterObs | None = None
        # 刷新文本锚点(观察 node 产物;read_encounter_refresh_count 返回
        # 的「剩余次数:N」文本中心 (x,y);读缺 = None,刷新臂走闸拒绝面)。
        self._refresh_point: tuple[int, int] | None = None

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """画面身份门 + node runner 帧一次读 → report 落容器。

        门 miss = round_fail 早退交回外循环重判(现役首闸同 status)。
        门命中即用 node runner 帧一次读(候选 + 剩余次数,同帧同源;
        用户裁定 2026-09-21 入口 2s 稳定期删除,原时序口径见
        screen_flow_timing.md #23 supersession 注;候选读缺的失败安全 =
        act 空候选零点击终结交回重读)→ ``report_screen_encounter_obs``
        落容器 ``encounter`` + ``encounter_refresh_left``(空候选不写,
        闸在 report 内)。"""
        screen = self.last_screenshot
        # live 2026-08-15:改 id_mark area(标识-遭遇节点)—— OCR「遭遇其一」在截断帧(「遭遇其」)miss;
        # 独立屏实锤(返回备战界面右上,同补给/投资策略)。
        if not self.round_by_find_area(screen, CwScreenEncounter.SCREEN_NAME,
                                       '标识-遭遇节点', crop_first=False).is_success:
            return self.round_fail('非遭遇节点屏')
        _rd = read_encounter_refresh_count(self.ctx, screen)
        obs = CwScreenEncounterObs(
            options=read_encounter_options(self.ctx, screen),
            refresh_left=(_rd[0] if _rd is not None else None),
            screen=screen)
        self._refresh_point = _rd[1] if _rd is not None else None
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_encounter_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=10)
    def act(self) -> OperationRoundResult:
        """零参决策 + 三出口派发即终结(重入裁决已退役)。

        出口三语义(op-layer §1.1 出口①,投资两屏/补给 3.1 同形态):
        ①刷新 = 点钮一次 + 2s → round_success 终结交回;②选卡 = 派发
        确认链(机械链 + chosen_encounter 即时上报在动作 op 内)→
        round_success 终结交回;③空候选 = 零点击终结交回重读
        (attack3 X2:候选读缺禁盲选派发——选卡确认不可逆消耗本节点,
        与刷新闸数据不一致分支同构)。决策返回词表外/None = 具名
        round_fail 零盲发;pick idx 越界 = 守卫断言 AssertionError;
        两守卫均在派发前、零点击。确认未生效 = 代码 bug,overlay
        残留由外循环按当前画面重识别重派;三出口均终结访问,无跨轮
        循环载体。"""
        obs = self._obs
        options = obs.options if obs is not None else []
        match = self.ctx.cw_match
        if not options:
            # 空候选 = 零点击终结交回(重读由外循环重进承载;禁盲选——
            # 选卡确认不可逆消耗本节点)。
            log.info('[cw-encounter] 候选读缺(options=%d)'
                     ' → 零点击终结交回重读', len(options))
            return self.round_success('候选读缺,零点击终结交回重读',
                                      wait=1.5)
        # 无 match 局外不设早退支(画面 op 不支持局外单独调用,op-layer.md
        # §1.1):缺上下文沿正常链路在此失败即预期,禁回填此类单跑防御分支。
        gs = match.gs
        # 刷新剩余闸读源 = 容器 encounter_refresh_left(观察轮 report
        # 摄入的同帧读数;None = 未观察/读缺,≤0 = 已刷尽)。
        _left = gs.encounter_refresh_left.value
        act = match.strategy.decide_encounter()
        if isinstance(act, CwActionRefreshNodeOptionsParam) \
                and not (_left is not None and int(_left) > 0
                         and self._refresh_point is not None):
            # 对照闸拒绝(与 kernel 刷新闸同源同值;本面 = 读缺/锚点缺
            # 不一致兜底)→ 重调一次决策按原评分选(单轮内有界)。
            log.info('[cw-encounter] 建议刷新但剩余闸拒绝(left=%r)'
                     ' → 重调按原评分选', _left)
            act = match.strategy.decide_encounter()
            if isinstance(act, CwActionRefreshNodeOptionsParam):
                # 重调仍建议刷新 = 闸数据不一致面,零点击终结交回
                #(外循环重进 = 入口重建重试观察,不空转本节点预算)。
                log.warning('[cw-encounter] 重调仍建议刷新(闸数据不一致)'
                            ' → 零点击终结交回(外循环重进重试观察)')
                return self.round_success(
                    '刷新闸数据不一致,零点击终结交回(外循环重进重建入口)',
                    wait=1.5)
        if isinstance(act, CwActionRefreshNodeOptionsParam):
            # 刷新 = 终结动作(op-layer.md §1.4):文本锚定点圆钮一次
            # + 2s 固定等待 → round_success 终结交回。零重读、零二次
            # 覆盖写、零重决策——新选项由外循环重进后的入口观察现读
            # 承载。点偏/无布局 → 交回后重进重读,失败安全。
            target = Point(
                self._refresh_point[0] + CwScreenEncounter._REFRESH_BTN_DX,
                self._refresh_point[1])
            log.info('[cw-encounter] 建议刷新 → 圆钮@(%d,%d)(文本锚定)'
                     ' 点钮一次后终结交回', target.x, target.y)
            self.ctx.controller.mouse_move(target)   # 防吞点击(截图前移光标)
            self.ctx.controller.click(target)
            # 用户口述口径(#23,2026-09-02):遭遇屏刷新后 2s 画面稳定
            # ——等满 2s 再交回(固定等待归产生动画的操作,非判效轮询;
            # docs/game/currency_war/research/screen_flow_timing.md)。
            time.sleep(2.0)
            return self.round_success(
                '分支刷新已点,本访问终结交回(外循环重进重建入口)',
                wait=1.5)
        # 守卫①(返回契约,op-layer.md §1.1 出口③):决策无有效输出
        #(词表外/None)= 具名 fail 零盲发;消息含策略器原值 repr = 留证
        #(不另加独立日志行,round_fail 消息经框架节点状态日志落盘)。
        if not isinstance(act, CwActionPickEncounterParam):
            return self.round_fail(
                f'decide_encounter 决策无有效输出(词表外/None): {act!r}')
        # 守卫②(值域,op-layer.md §1.3):idx 越界 = 策略器 bug,守卫断言
        # 响亮暴露,禁钳位——动作 op 执行即发出点击链,越界放行会确认
        # 错卡(不可逆),必须拦在派发前。
        if not (0 <= act.idx < len(options)):
            raise AssertionError(
                f'[cw-encounter] pick idx 越界(策略器 bug,禁钳位): '
                f'idx={act.idx} len(options)={len(options)} act={act!r}')
        log.info(f'[cw-encounter] options={[(o.difficulty, o.rewards) for o in options]} '
                 f'pick=idx{act.idx} {act.reason}')
        # 选卡 = 派发即终结:确认链(点卡选中 → 确认)机械半 + chosen_
        # encounter 即时上报(发射即写)在动作 op 内,派发后本访问
        # round_success 终结交回(落地判定归观察侧;重入裁决已退役)。
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
            OverlayPickExecEnv,
        )
        env = OverlayPickExecEnv(op=self)
        # 直发策略产实例(无重建无钳位,idx/reason 单一源 = 策略产值,
        # 流程侧零值域改写):词表外/None = 具名 fail 零盲发(守卫①),
        # idx 越界 = 守卫断言(守卫②),两守卫均在派发前、零点击;
        # 空候选零点击终结交回为另一条合规路径。
        action_op_for(act, self.ctx, env).execute()
        return self.round_success('遭遇选卡确认链已派发,本访问终结交回',
                                  wait=2.0)
