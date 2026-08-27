
"""货币战争 补给节点 RunNode(从 ``HandleSupply`` 升级为节点生命周期 owner)。

补给阶段 = 动态 N 选 1 装备 + 确认(通常 4 选 1;「全都要」类效果减 2 列、「人身意外险」类
加补给阶段可增列,augment 改写下实测 3-5 不等——历史「3 选 1」「实测 5」均为特例表述,
列数以 read_supply_options 实际识别为准,禁写死)。RunNode 化后:每轮**验证**"还在补给屏?"
(关键词在)→ 点卡身 +
确认 → ``round_retry``;overlay 消失(关键词没了)= 节点完成 → ``round_success``;超预算(点不动)
→ FAIL bail(**不无限烧**,旧 HandleSupply 盲单发失败也回 success → flat loop 无限 round_wait 烧预算)。

动作(T#99 已接 decide_supply):``read_supply_options`` OCR 每列(角色+装备)→ ``decide_supply`` 按
target_comp.key_equips 契合 + 装备通用价值选最优列 → 点该列卡身 + 确认。读不到选项 → CARD_BODY 兜底。
钻(红/蓝=基本赢)视觉判定 + has_diamond 待补;supply 无刷新按钮(decide_supply 传 refresh_used=True)。

T#103:确认按钮进 screen_info(货币战争-补给 按钮-确认);卡身点击点由 read_supply_options 按列返回。
"""
import time
from pathlib import Path
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war import cw_telemetry
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_node_obs import read_supply_options
from sr_od.application.currency_war.cw_observation import read_game_state
from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.cw_telemetry import set_last_supply_pick
from sr_od.application.currency_war.operations.run_nodes.run_node import RunNode
from sr_od.context.sr_context import SrContext

# W308 停机钩子 sentinel flag 路径(模块常量仅为测试可指 tmp_path,非运行时开关;
# 钩子整段删除时一并删)
SUPPLY_STOP_HOOK_FLAG = Path('.debug/temp/currency_war/supply_stop_hook.flag')


class RunSupplyNode(RunNode):
    """补给节点:点卡身选中 + 确认,**验证 overlay 消失**才完成。

    W306b 补给备战状态采集 detour(每节点一次,先于选择流程):补给轮不驻留
    备战画面(overlay 选完直接下一节点),战斗结算后状态/补给前的板面是数据
    真空。流程 = 点「返回备战界面」→ 停 1-2 帧等画面稳定 → 显式记一条
    **采集性返回**决策快照(actions=[],phase='supply_detour',非购买轮语义,
    防判读把该轮当购买轮)→ 从备战点「返回补给阶段」重进 overlay → 继续
    原选择流程。顺序采用「先采集后进入」的安全序:重进后 overlay 的选择进度
    是否保留未实证(W306b 时禁实机),但采集已先行完成,进度丢失只是选择重启、
    不丢数据;若后续实机确认进度保留,可改为「先选后采」省一次往返。
    """

    CARD_BODY: ClassVar[Point] = Point(900, 550)  # 补给卡 body 不开对话(沿用 HandleSupply)
    # 刷新按钮(图标式,VLM 判定 + refresh_ui_samples.jsonl 多局稳定坐标;2026-08-17)
    REFRESH_BTN: ClassVar[Point] = Point(974, 854)
    # detour 参数:回备战后等画面稳定 + 重进重试上限(全部失败则本轮不做选择,
    # 交还下轮 _in_node 判定——防备战屏盲点)
    DETOUR_SETTLE_S: ClassVar[float] = 1.5
    REENTER_TRIES: ClassVar[int] = 3

    def __init__(self, ctx: SrContext):
        RunNode.__init__(self, ctx, op_name='货币战争-补给节点')
        self._refresh_used = False   # r1 review#1:节点实例态(只刷一次;游戏规则补给可刷 1 次)

    @operation_node(name='补给节点', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        # ===== [停机钩子·临时,W308;观察完成后整段删除:本钩子方法+handle 内调用+flag 写入] =====
        result = self._supply_stop_hook()
        if result is not None:
            return result
        # ===== [停机钩子·临时,W308 结束] =====
        return self._run_node()

    def _supply_stop_hook(self) -> OperationRoundResult | None:
        """[停机钩子·临时捕获类(按 od-dev-stop-hooks §2.1),观察完成后删本段。

        W308 目的:补给节点**基础金币奖励真值未知**(选补给后给不给基础金、给多少)
        → 下次实机遇补给画面即停机保画面,人工经 MCP 观察选中补给前后金币数定谳。
        触发 = 补给阶段画面锚命中(复用既有 screen_info「货币战争-补给/标识-补给阶段」
        id_mark 判定,不新造识别);无条件触发,无开关无参数(项目约定)。
        动作:save_screenshot 存证 + flag 文件(三要素见内容)+ stop_running(代码直调,
        不经 MCP)+ 返回 round_wait 不做任何 click,画面原样保持供观察。
        flag 路径收成模块常量仅为测试可指 tmp_path,非运行时开关。
        """
        screen = self.screenshot()
        if not self._in_node(screen):   # 前置门:补给画面锚命中才触发,防过渡帧伪触发
            return None
        shot_path = self.save_screenshot(prefix='supply_stop_hook')
        # 轮次上下文 best-effort(last_state 可能缺,None 不阻塞)
        _state = None
        try:
            _match = getattr(self.ctx, 'cw_match', None)
            _state = getattr(getattr(_match, 'session', None), 'last_state', None)
        except Exception:   # noqa: BLE001
            pass
        _ctx_txt = (f"plane={getattr(_state, 'plane', '?')} round={getattr(_state, 'round_num', '?')} "
                    f"gold={getattr(_state, 'gold', '?')}(选前)") if _state is not None else 'last_state 不可得'
        SUPPLY_STOP_HOOK_FLAG.parent.mkdir(parents=True, exist_ok=True)
        SUPPLY_STOP_HOOK_FLAG.write_text(
            'HOOK-STOP(W308 补给停机钩子):识别到补给阶段画面(op 入口、任何 click 前)。\n'
            f'触发时间: {time.strftime("%Y-%m-%d %H:%M:%S")} {time.tzname}\n'
            f'轮次上下文: {_ctx_txt} 截图: {shot_path}\n'
            '处理步骤: run 已 STOP(bot 停了,游戏画面仍在)。人工经 MCP 观察金币数——'
            '先记录选中前金币,再手动点一张补给卡+确认,再读选中后金币,即可确定基础金奖励真值;\n'
            '删除条件: 观察完成(基础金有/无与数值已记档)→ 删本 flag 文件 + 整段删除钩子'
            '(run_supply_node._supply_stop_hook + handle 内调用),重启 MCP server 后恢复实跑。\n',
            encoding='utf-8')
        log.info('[cw-hook][supply-stop] 补给画面锚命中 → 停机保画面(W308 观察基础金币;'
                 '截图 %s flag %s)', shot_path, SUPPLY_STOP_HOOK_FLAG)
        if self.ctx.run_context is not None:
            self.ctx.run_context.stop_running()
        return self.round_wait(status='W308 补给停机钩子触发:已停机保画面,待人工观察基础金币')

    def _in_node(self, screen) -> bool:
        # 还在补给屏 = 标识-补给阶段 area 命中(位置区分,非全屏 LCS:防「补给阶段」与「备战阶段」共享「阶段」误匹配)。
        return self.round_by_find_area(screen, '货币战争-补给', '标识-补给阶段', crop_first=False).is_success

    def _should_supply_detour(self, match) -> bool:
        """本补给节点还没做过 detour?优先 session 态(跨外环重建存活,
        同 _supply_refresh_used 惯例),无 match 退实例态。"""
        if match is not None:
            return not getattr(match.session, '_supply_detour_done', False)
        return not getattr(self, '_detour_done', False)

    def _mark_supply_detour(self, match) -> None:
        if match is not None:
            match.session._supply_detour_done = True
        else:
            self._detour_done = True

    def _supply_detour_collect(self, match) -> bool:
        """W306b detour 本体:回备战 → 采集快照 → 重进 overlay。全部 best-effort,
        返回 False = 无法回到补给界面(调用方放弃本轮动作)。"""
        # ① 返回备战界面(area 已建:currency_war_supply 按钮-返回备战界面)
        rs = self.round_by_find_and_click_area(
            self.screenshot(), '货币战争-补给', '按钮-返回备战界面', success_wait=1.5)
        if rs is None or not rs.is_success:
            log.warning('[cw-supply] detour:「返回备战界面」点击 miss → 放弃本次采集')
            return False
        time.sleep(RunSupplyNode.DETOUR_SETTLE_S)
        # ② 显式采集性返回快照(标记 phase='supply_detour';actions=[] 非购买轮)
        try:
            _snap_screen = self.screenshot()
            _state = read_game_state(self.ctx, _snap_screen)
            cw_telemetry.record_decision(
                _state, target_comp='', candidate_scores={}, eval_breakdown={},
                actions=[], gold_point=True,
                extra={'phase': 'supply_detour'})
            log.info('[cw-supply] detour 备战快照已落盘 p%sr%s hp=%s gold=%s',
                     getattr(_state, 'plane', '?'), getattr(_state, 'round_num', '?'),
                     getattr(_state, 'hp', '?'), getattr(_state, 'gold', '?'))
        except Exception as e:   # noqa: BLE001  观测不阻塞对局
            log.warning('[cw-supply] detour 快照记录失败(不阻塞): %s', e)
        # ③ 重进 overlay(先采集后进入,见类注;备战屏「按钮-返回补给阶段」area 已建)
        for i in range(RunSupplyNode.REENTER_TRIES):
            rr = self.round_by_find_and_click_area(
                self.screenshot(), '货币战争-备战', '按钮-返回补给阶段',
                success_wait=1.5)
            time.sleep(RunSupplyNode.DETOUR_SETTLE_S)
            if rr is not None and rr.is_success and self._in_node(self.screenshot()):
                log.info('[cw-supply] detour 完成:回到补给界面(第 %d 次尝试)', i + 1)
                return True
        log.warning('[cw-supply] detour:%d 次重进均未回到补给界面', RunSupplyNode.REENTER_TRIES)
        return False

    def _do_action(self, screen) -> None:
        # T#99 接 decide_supply:OCR 补给选项(每列=角色+装备)→ 策略按 target_comp.key_equips 契合 + 装备
        # 通用价值选(替代盲点 CARD_BODY)。钻识别双通道 ✅(SIFT 主+文本兜底,cw_node_obs)。
        # 刷新按钮 ✅ 实锤(2026-08-17 VLM 判建档图 + refresh_ui_samples 多局数据:图标按钮
        # @≈(974,854),「剩余次数:1」——补给可刷 1 次;旧注释「无刷新按钮」作废,OCR 钩子
        # 找不到是因为按钮是**图标**非文字)。钻重刷链激活:无钻+未刷 → 点刷新重掷。
        match = self.ctx.cw_match
        # W306b:首次进入先做备战状态采集 detour(detour 后用新帧读选项;
        # 恢复失败 → 本轮不做任何选择动作,防在备战屏盲点卡身)
        if self._should_supply_detour(match):
            self._mark_supply_detour(match)
            if not self._supply_detour_collect(match):
                return
            screen = self.screenshot()
        opts = read_supply_options(self.ctx, screen)
        # r2 review#2:实例态在外环每次新建 RunSupplyNode 下失效 → 挂 match.session
        # (正式字段,非 Optional)读;r10 review#3:getattr 兜底删(拼错字段名会静默
        # False 掩盖接线错误)。无 match 退实例态(测试/离线路径)。
        _refresh_used = match.session._supply_refresh_used if match is not None else self._refresh_used
        target = RunSupplyNode.CARD_BODY
        reason = 'no-options(CARD_BODY 兜底)'
        refresh_target = None
        if match is not None and opts:
            _state = match.session.last_state or GameState()
            _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
            pick = match.strategy.decide_supply(
                [o for o, _ in opts], _state, match.session, _cfg,
                refresh_used=_refresh_used)
            if pick.refresh and not _refresh_used:   # 只刷一次(r1#1+r2#2:session 级)
                refresh_target = RunSupplyNode.REFRESH_BTN
                self._refresh_used = True
                match.session._supply_refresh_used = True
                reason = pick.reason
            elif 0 <= pick.idx < len(opts):
                target = opts[pick.idx][1]
                reason = pick.reason
                # W306:选定+确认时点暂存选择快照(角色/装备/钻;refreshed=刷新
                # 是否已用),供 overlay 消失后 battle_loop 合成 supply 行消费。
                # W306c:附**实际识别到的选项清单**(动态列数,不假定结构)——
                # 合成行与逐列内容对拍/漏读审计数据源。
                _opt = opts[pick.idx][0]
                set_last_supply_pick(_opt.char, _opt.equip, _opt.has_diamond,
                                     refreshed=_refresh_used,
                                     options=[{'char': o.char, 'equip': o.equip,
                                               'has_diamond': o.has_diamond}
                                              for o, _p in opts])
            log.info('[cw-supply] options=%s pick=idx%s %s click@(%d,%d)',
                     [(o.char, o.equip, o.has_diamond) for o, _ in opts], pick.idx, reason, target.x, target.y)
        else:
            log.info('[cw-supply] opts=%d match=%s → CARD_BODY 兜底', len(opts), match is not None)
        # bug#1 缓解:click 前 mouse_move 到目标(零移动),防 before_screenshot 移光标 → click 落空。
        if refresh_target is not None:
            self.ctx.controller.mouse_move(refresh_target)
            self.ctx.controller.click(refresh_target)
            time.sleep(0.6)   # 等重掷动画;下一轮 loop 重新读选项
            return
        self.ctx.controller.mouse_move(target)
        self.ctx.controller.click(target)
        time.sleep(0.6)
        # 确认(supply 按钮-确认 area;T#103 area 化)
        self.round_by_find_and_click_area(self.screenshot(), '货币战争-补给', '按钮-确认', success_wait=1.5)


