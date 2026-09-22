"""盛会之星画面 op(事件 overlay 族一画面一文件 = ``cw_screen_*.py``,
本文件 = 巨星;入口门由主循环身份分发承担,处理本体 = 画面 op 真身)。

形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两段
直继承 SrOperation。观察 node = 节点完成门(``_in_node``,miss = round_success
交回外循环,选中标记复位副作用在门内)+ 候选观察(懒读保真:仅「本访问将
选择」即未选中时读候选;确认访问不重读,迁移不增加读屏)→
``report_screen_megastar_obs`` 落容器 ``megastar_opts`` → obs 挂实例属性进
决策 node。决策动作 node = 节点完成复检(每轮新帧,overlay 消失 = 完成)→
决策从容器零参读 → 「选中 → 确认」链经 ``CwActionPickMegastarOp`` 派发
(pick-op-unify 批:候选选中半迁入动作 op,``env.need_select`` 驱动)→
round_wait 循环推进(不烧节点重试预算;不收敛 = 策略 bug 响亮暴露,无防御
上限)。``chosen_megastar`` = 选择点单次逻辑写入留守决策面(动作事实边界,
不进 report);选中旗标宿主 = 策略器 StrategyState(经 kernel strategy_state_of
None-safe 通道,执行层不冷建)。本屏 sim 腿 = 不适用(sim 无对应画面段,
事件浮层族即时落定),等价判据主承重 = 实机在册行为锁。

出口语义(选中半访问):候选空 = 具名 round_fail 零盲发,返回词表外/
None = 具名 round_fail,idx 越界 = 守卫断言 AssertionError——守卫均在
派发前、零点击;无 match/gs = 局外交回(零决策零点击,正本形态);名字
转换失败 = 观察层 round_fail(转换门 = ``obs/cw_megastar_obs.py`` 的
``standardize_megastar_options``)。

**玩法机制(米游社 wiki content/6239 + 实机日志/截图核实,2026-08-07)**:
盛会之星 = 阵营羁绊;「巨星」= 选 1 名盛会之星角色当巨星,给全队独特 buff。
触发 = 羁绊激活时弹出(非固定节点),一局可多次 → 选中标记不能跨节点保持。
dispatch 是 OCR 反应式(主循环 0b 检测「盛会之星」就接)→ 不管何时弹都接得住。
本节点 = 「选巨星候选 → 确认」,确认 = 纯机械单发(用户裁定 2026-09-14):
确认未落地归下一帧重入裁决,节点循环单确认自愈;「请选择强化角色」
文本 = 确认钮旁伴随文案,禁据它判步。候选点击坐标 = 观察上报随选项
一并落容器 ``megastar_opts[idx].xy``(选择坐标观察上报,规范 =
op-layer.md §1.1;动作 op 按下标自容器取点,本 op 零坐标现算;候选
兜底常量宿主 = ``obs/cw_megastar_obs.py``)。确认钮 = 建档
``currency_war_megastar.按钮-确认选择``(动作 op 执行体
``round_by_find_and_click_area`` 查找点击,全族统一)。
"""

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_screen_report.megastar import (
    CwScreenMegastarObs,
    report_screen_megastar_obs,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import (
    strategy_state_of,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickMegastarParam,
)
from sr_od.application.currency_war.obs.cw_megastar_obs import (
    read_megastar_options,
    standardize_megastar_options,
)
from sr_od.application.currency_war.operations.cw_screen.cw_flow_const import (
    CW_OVERLAY_SETTLE_S,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenMegastar(SrOperation):
    """盛会之星:候选立绘 → decide_megastar 选巨星 + 确认(旧巨星节点执行器内联)。

    节点完成门 = 「仍在巨星 overlay?」(标识-盛会之星);确认未落地 =
    下一帧门复检自愈(动作链 bug 归动作层修,不加验证段)。单动作确认
    形态(关态稳定基线语义 = ADR-0264)。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-巨星节点')
        # 观察结果(观察 node 产物,决策动作 node 消费;options 懒读门槛见
        # ``observe`` 注:仅「本访问将选择」即未选中时填充)。
        self._obs: CwScreenMegastarObs | None = None
        # 生效选中下标缓存(决策轮现算,派发实例携真实 idx 供上报 param;
        # [索引定义] 坐标系 = 候选 options 列表下标 0 基;取值时机 = 决策
        # 轮快照,确认轮复用)。
        self._pick_idx: int = 0

    def _in_node(self, screen) -> bool:
        # 巨星 overlay = 「盛会之星」独有标题(标题 area 位置区分,非全屏
        # LCS,防多屏共享词误匹配)。
        still_in = self.round_by_find_area(screen, '货币战争-盛会之星', '标识-盛会之星', crop_first=False).is_success
        # megastar 一局可能多次(每次持有盛会之星角色触发,见类 docstring),flag 不能跨节点保持 True。
        # 节点完成即复位:经 kernel strategy_state_of None-safe 通道,状态
        # 对象缺席跳过写(禁执行层触发 impl state_of 的 None 冷建装配语义)。
        if not still_in:
            _match = self.ctx.cw_match
            if _match is not None:
                _st = strategy_state_of(_match.session)
                if _st is not None:
                    _st.megastar_clicked = False
        return still_in

    @staticmethod
    def _clicked_of(match: object) -> bool:
        """选中标记读侧防御(局级旗标,跨 re-dispatch 持久;原实例态在重派时
        重置 → re-click toggle 反选 → confirm 无候选卡死)。读侧 getattr:
        状态对象缺席(None)或异型缺字段退 False(经 kernel strategy_state_of
        通道,禁 getattr session 猜宿主/禁 impl state_of 冷建)。"""
        return (getattr(strategy_state_of(match.session),
                        'megastar_clicked', False)
                if match else False)

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """节点完成门 + 候选观察上报(懒读保真)。

        门 miss = overlay 消失 / 进了下一节点 → 节点完成,交还外层
        (含 ``_in_node`` 选中标记复位副作用,须在门内)。在门内 → 仅
        「本访问将选择」(未选中)才读候选;确认访问不重读(迁移不增加
        读屏)→ ``report_screen_megastar_obs`` 写 ``megastar_opts``
        (空候选不写,闸在 report 内);无 match/gs = 局外,零读屏零上
        报交回(正本 = op-layer.md §1.1「画面 op 不支持局外单独调用」,
        本屏特形 = 懒读先例屏零读延伸);名字标准化转换门住本 node 选中
        半读链(规范 = 同节「观察标准化门」)。"""
        screen = self.last_screenshot
        if not self._in_node(screen):
            return self.round_success('巨星节点完成(已离开本节点画面)',
                                      wait=CW_OVERLAY_SETTLE_S)
        _match = self.ctx.cw_match
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is None:
            # 局外(无对局上下文)= 零读屏零上报交回:决策必不发生时读
            # 无消费方(懒读先例屏的结构延伸);终局出口 = act 局外交回臂。
            return self.round_success('局外交回(无 match/gs;零读屏零上报)')
        clicked = self._clicked_of(_match)
        options = [] if clicked else read_megastar_options(self.ctx, screen)
        if not clicked:
            # 观察标准化门:候选名零转换禁入容器(op-layer.md §1.1);转换
            # 失败 = 观察失败,零写零上报交回重观察重读(禁带病上报)。
            standardized = standardize_megastar_options(options, _gs)
            if standardized is None:
                log.warning('[cw-megastar] 观察标准化门失败:候选转换不到'
                            '规范名(零写零上报,交回重观察)')
                return self.round_fail(
                    f'[cw-megastar] 候选名标准化转换失败(零写零上报,交回'
                    f'重观察):候选原值={[o.char_id for o in options]!r}')
            options = standardized
        obs = CwScreenMegastarObs(in_node=True, options=options, screen=screen)
        report_screen_megastar_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=8)
    def act(self) -> OperationRoundResult:
        """节点完成复检 + 单动作(选候选 ∨ 确认)+ round_wait 循环推进。

        每轮 node runner 新帧复检节点完成门(round_wait 不计节点预算,
        不收敛 = 策略实现 bug 响亮暴露,无防御上限);确认未落地由下一轮
        门复检自愈。出口语义(选中半访问):候选空 = 具名 round_fail 零
        盲发,返回词表外/None = 具名 round_fail,idx 越界 = 守卫断言
        AssertionError——守卫均在派发前、零点击;无 match/gs = 局外交回
        (零决策零点击,正本形态);名字转换失败 = 观察层 round_fail
        (标准化转换门住观察 node)。"""
        screen = self.last_screenshot
        if not self._in_node(screen):
            return self.round_success('巨星节点完成(已离开本节点画面)',
                                      wait=CW_OVERLAY_SETTLE_S)
        _match = self.ctx.cw_match
        if _match is None or getattr(_match, 'gs', None) is None:
            # 局外(无对局上下文)= 零决策零点击 round_success 终结交回;
            # 判式宽度 = match/gs 双缺(对齐投资环境在飞双判;遭遇为含空候选
            # 的三判特形,空候选臂本屏走守卫① fail 不折入;正本 = screens/
            # op-layer.md §1.1「画面 op 不支持局外单独调用」)
            return self.round_success('局外交回(无 match/gs;零决策零点击)')
        _fail = self._do_action()
        if _fail is not None:
            return _fail
        return self.round_wait(wait=1.5)

    def _do_action(self) -> OperationRoundResult | None:
        """单动作体:决策 + chosen 写端留守 + 「选中 → 确认」链经工厂。

        候选选中点击在 ``CwActionPickMegastarOp``(``env.need_select``
        驱动),本方法只决策与写端——``chosen_megastar`` 写端与选中
        旗标留守(单次逻辑写入豁免面;派发前写 = 选择点,写点 → 点选
        窗口内无读者)。确认轮(已选中)只发确认。"""
        _match = self.ctx.cw_match
        need_select = not self._clicked_of(_match)
        if need_select:
            options = self._obs.options if self._obs is not None else []
            # 守卫① 决策输入:候选空 = 具名 fail 零盲发(op-layer.md §1.1 出口③)。
            if not options:
                return self.round_fail(
                    '[cw-megastar] 决策无有效输出零盲发(候选空 options=0)')
            # 零参决策(写槽已由 report 落容器 megastar_opts;决策调用形态不变)。
            # 守卫② 返回契约:词表外/None = 具名 fail 含原值留证(注解的运行期执行)。
            pick = _match.strategy.decide_megastar()
            if not isinstance(pick, CwActionPickMegastarParam):
                return self.round_fail(
                    f'decide_megastar 决策无有效输出(词表外/None): {pick!r}')
            # 守卫③ 值域:越界 = 断言恒炸禁钳位(op-layer.md §1.3;断言臂经框架异常路径计节点预算)。
            if not (0 <= pick.idx < len(options)):
                raise AssertionError(
                    f'[cw-megastar] pick idx 越界(策略器 bug,禁钳位): '
                    f'idx={pick.idx} len(options)={len(options)} pick={pick!r}')
            self._pick_idx = pick.idx
            log.info(f'[cw-megastar] candidates={[o.char_id for o in options]} pick=idx{pick.idx} {pick.reason}')
            if _match is not None:
                # 置位经 kernel strategy_state_of(None-safe 不冷建):状态
                # 对象缺席跳过写(局级:跨 re-dispatch 持久,session.md
                # §2.4 B1 定案的宿主级语义)。
                _st = strategy_state_of(_match.session)
                if _st is not None:
                    _st.megastar_clicked = True
                # 巨星选择落容器 chosen_megastar(gs 单一源,session 域无此
                # 写端;桩无 gs = 跳过写)。chosen_* = 动作事实边界:留守
                # 选择点,不进 report。
                if getattr(_match, 'gs', None) is not None:
                    from sr_od.application.currency_war.kernel.cw_game_state import (
                        ChannelSig,
                    )
                    _match.gs.write_logic(
                        _match.gs.chosen_megastar,
                        options[pick.idx].char_id or '',
                        produced_by='CwScreenMegastar',
                        sig=ChannelSig(family='logic_action',
                                       actor='CwScreenMegastar',
                                       mode='compute'))
        # 「选中(need_select)→ 确认」链经工厂(选中半迁入动作 op;
        # 候选点击坐标 = 动作 op 内自容器 megastar_opts[param.idx].xy 取,
        # 选择坐标观察上报收敛;确认钮 = 动作 op 执行体 round_by_find_and_click_area
        # 查找点击,全族统一)。
        # 派发:上报 param 携真实选中下标(取点/取名键单一源);env 零机械
        # 下标零坐标传参(env.idx 已退役停喂);确认轮复用缓存 idx。
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self,
                                  need_select=need_select)
        action_op_for(CwActionPickMegastarParam(idx=self._pick_idx), self.ctx,
                      _env).execute()
        return None
