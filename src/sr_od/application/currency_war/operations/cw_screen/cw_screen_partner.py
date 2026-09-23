# 机制更正(2026-09-15 实机事故,详见 docs/game/screens/currency_war_choose_partner.md):
# 旧「选中态 gate」= 全屏 OCR 找「已选择」(LCS 阈值按关键词归一,3 字词与
# 本屏常驻的指令长句/「请选择强化角色」共享子序列「选择」即达 0.5)→ 本屏
# 恒误命中,op 恒跳过点选、对置灰确认钮原样重试 → P1-r1 十八连 fail 卡死
# (确认钮置灰被游戏拒绝)。本版废除选中态读数,改「点选候选 → 确认」脉冲 +
# overlay 关闭完成门(推进信号 = 标识消失,不依赖任何未实锤的选中态呈现);
# 未选中态正判定 = 建档「提示-请选择强化角色」区域命中(置灰伴随文案)。

"""货币战争 选择伙伴 overlay 处理 op(从主循环拆出)。

「选择伙伴」overlay 会挡住出战 → stall。OCR 候选阵营标签定位候选 → SIFT 立绘识别
真身 → decide_partner 按策略选 → 「点选候选 → 确认」脉冲(同轮先点选后确认,
确认被拒形态有界重试,见决策动作 node)→ overlay 关 = 完成门(标识消失)。

形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两段
直继承 SrOperation。观察 node = 入口门(标识-选择伙伴,miss = round_fail 交
回外循环重判)+ 候选观察一次读(OCR + SIFT 立绘识别真身,失败回落 label 名;
入口帧一次读,与现役决策体读同帧等价)→ ``report_screen_partner_obs`` 落
容器 ``partner_opts``(空候选不写,闸在 report 内)→ obs 挂实例属性进决策
node。决策动作 node = 重入裁决顶部(确认已发 → 标识不在 = overlay 已关
→ success 交回)→ 确认被拒守卫(未选中提示在场 × 脉冲上限 = 显式 fail)
+ 决策出口守卫(输入:候选空 fail / 返回契约 / 值域,op-layer.md §1.1
出口③ / §1.3;无 match 局外不设早退支,用户裁决 2026-09-22 全族删门)→
首轮决策一次定同一点位(chosen_partner = 选择点单次逻辑写入留守,动作事实
边界不进 report)→ 「点选候选 → 确认」脉冲链经工厂 → round_wait 循环。
本屏 sim 腿 = 不适用(sim 无对应画面段,事件浮层族即时落定),等价判据
主承重 = 实机行为锁(test_cw_partner_select_confirm_flow 选选流序/确认
被拒有界重试锁)。
"""
from pathlib import Path
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_events import PartnerOption
from sr_od.application.currency_war.kernel.cw_screen_report.partner import (
    CwScreenPartnerObs,
    report_screen_partner_obs,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionPickPartnerParam
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenPartner(SrOperation):
    """选择伙伴 overlay:OCR 候选 → decide_partner 选 → 「点选候选→确认」脉冲 → 标识消失 = 完成。"""

    # 候选阵营标签行 y 过滤带(候选 label 在 y~362;排除标题 64 / 指令 130 / 详情 445 / 确认 582)。
    # 实测(2026-08-06 1-7 节点):候选 label 护盾/能量 在 y≈362;放宽 [340,400] 容变。
    LABEL_CY_LO: ClassVar[int] = 340
    LABEL_CY_HI: ClassVar[int] = 400
    # 候选 x 过滤带(候选立绘在画面中央 overlay,~450-1550)。**必须过滤 x**:左侧备战面板阵营 label
    # (列车同行/能量/仙舟/213... 在 x~106)也落在候选 y 行 → 不滤 x 会把 board label 当候选 → 点错(2026-08-06
    LABEL_CX_LO: ClassVar[int] = 450
    LABEL_CX_HI: ClassVar[int] = 1550
    # 确认被拒脉冲上限:未选中提示持续在场时,「点选→确认」脉冲达到该次数即
    # 显式 round_fail 交外环重判(禁原样无限重试;2026-09-15 实机卡死形态的
    # 针对性防线。取值 < 节点预算 10,先于预算耗尽给出精确失败原因)。
    CONFIRM_REJECT_MAX: ClassVar[int] = 4
    # screen_info area 名(currency_war_partner.yml;坐标单一真相源)。
    A_CANDIDATE_STRIP: ClassVar[str] = '候选-卡区'
    A_UNSELECTED_HINT: ClassVar[str] = '提示-请选择强化角色'
    _EXCLUDE: ClassVar[set[str]] = {'选择伙伴', '攻略', '确认选择', '详情', '角色', '装备'}

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-列车同行')
        # 确认已发待重入裁决标志(验证废除形态):重入裁决见决策动作 node
        # 顶部(两步链的最终确认也置位,标识不在 = overlay 关 = 链完结;
        # 置位在 pick op 体内 = 确认发送时点)。
        self._confirm_pending: bool = False
        # 选定点位(本执行内一次决策缓存):重入轮复用同点位重点选,不重跑
        # SIFT/决策/session 写(单执行内点位稳定,防跨轮决策抖动换候选)。
        self._pick_point: Point | None = None
        # 生效选中下标缓存(决策轮随点位同步缓存,派发实例携真实 idx 供
        # 上报 param;[索引定义] 坐标系 = 候选 options 列表下标 0 基;
        # 取值时机 = 决策轮快照,脉冲轮复用)。
        self._pick_idx: int = 0
        # 「点选→确认」脉冲计数(确认被拒防线的有界重试预算,见 CONFIRM_REJECT_MAX)。
        self._confirm_pulses: int = 0
        # 观察结果(观察 node 产物,决策动作 node 消费;options = 入口帧一次读)
        # 与候选原始坐标(点位解析输入,不入 obs 契约)。
        self._obs: CwScreenPartnerObs | None = None
        self._cands: list[tuple[str, int, int]] = []

    def _read_candidates(self, screen) -> list[tuple[str, int, int]]:
        """OCR 候选 ``(阵营名, label center-x, label center-y)``,按 label 行 y 过滤 + 左→右排序。

        候选 label 是 2-4 字阵营名(护盾/能量/仙舟/列车同行...)在固定 y 行;排除标题/指令/详情等。
        """
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        opts: list[tuple[str, int, int]] = []
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            cx = mrl.max.center.x
            cy = mrl.max.center.y
            if (CwScreenPartner.LABEL_CY_LO <= cy <= CwScreenPartner.LABEL_CY_HI
                    and CwScreenPartner.LABEL_CX_LO <= cx <= CwScreenPartner.LABEL_CX_HI
                    and 2 <= len(text) <= 4 and text not in CwScreenPartner._EXCLUDE):
                opts.append((text, cx, cy))
        opts.sort(key=lambda t: t[1])
        return opts

    def _identify_portraits(self, screen, cands: list[tuple[str, int, int]]) -> list[str]:
        """r104:SIFT 立绘识别候选真身(portrait_plaza 库)→ 每候选 char_id(''=未识别)。

        候选立绘区 = label 上方大区域(立绘中心 ≈ label y-60,向上扩 ~200px);
        识别失败回落 label 流派名(旧行为)。真身识别让 decide_partner 的
        core_chars 匹配真正生效(此前 label 名恒不命中 → 恒 idx=0)。
        """
        try:
            from one_dragon.utils import os_utils
            from sr_od.application.currency_war.obs.currency_war_char_id import (
                identify_character,
                load_avatar_templates,
            )
            portrait_dir = Path(os_utils.get_path_under_work_dir(
                'assets', 'template', 'currency_war', 'portrait_plaza'))
            if not portrait_dir.is_dir():
                return [n for n, _cx, _cy in cands]
            templates = load_avatar_templates(portrait_dir)
            out: list[str] = []
            for _name, cx, cy in cands:
                # 立绘区:候选中心上方(立绘主体在 label 上方 ~40-260px 带)
                y1 = max(0, cy - 260)
                y2 = max(y1 + 40, cy - 30)
                x1 = max(0, cx - 110)
                x2 = min(screen.shape[1], cx + 110)
                crop = screen[y1:y2, x1:x2]
                if crop.size == 0:
                    out.append(_name)
                    continue
                cid, _inl = identify_character(crop, templates)
                out.append(cid if cid else _name)
            return out
        except Exception:   # noqa: BLE001  SIFT 失败回落 label 名(旧行为)
            return [n for n, _cx, _cy in cands]

    def _unselected_hint_present(self, screen) -> bool:
        """未选中态正判定:建档「提示-请选择强化角色」区域命中。

        该提示 = 确认钮置灰态的伴随文案(区域约束 OCR,rect 内无他词,无
        全屏 LCS 误匹配面)。选中态呈现在档材料零实拍(旧档「已选择文字 +
        高亮边框」记载经像素比对证伪,见 screen doc)→ 只把提示在场作
        「确定未选中」的正判定,选中与否不作读数判定 —— 推进语义由
        「点选→确认」脉冲 + overlay 关闭完成门承载。
        """
        return self.round_by_find_area(
            screen, '货币战争-列车同行', CwScreenPartner.A_UNSELECTED_HINT,
        ).is_success

    def _pick_point_for(self, cand: tuple[str, int, int]) -> Point | None:
        """候选点击点位:x = 候选 label 中心(运行时动态,随候选数分布),
        y = 建档「候选-卡区」带中心(坐标单一真相源)。区域缺失 = None,
        调用方显式失败(禁裸坐标兜底)。

        两帧实测(2026-09-15 事故帧 1-1 与 1-9 档 fixture)卡带 y≈165-440,
        带中心 y≈302 落立绘区内;旧 offset「label cy-60」实点 y≈315,恰在
        立绘底边(~307)下方卡体死区 —— 点击几何不可靠的根源之一,故 y
        改由建档带锚定,布局漂移可经 analyze_screen 对账暴露。
        """
        area = self.ctx.screen_loader.get_area(
            '货币战争-列车同行', CwScreenPartner.A_CANDIDATE_STRIP)
        if area is None or area.pc_rect is None:
            return None
        _name, cx, _cy = cand
        return Point(cx, (area.pc_rect.y1 + area.pc_rect.y2) // 2)

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口门 + 候选观察一次读 → report 落容器。

        门 miss = round_fail 早退(与现役首闸同 status,交回外循环重判)。
        门后候选一次读(OCR + SIFT 真身识别,失败回落 label 名)→
        ``report_screen_partner_obs``(空候选不写,闸在 report 内);
        match/gs 缺席的局外兜底路径跳过 report(report 跳写 = 容器写闸,
        与决策无关;无 match 局外不设早退支,用户裁决 2026-09-22 全族
        删门)。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(screen, '货币战争-列车同行', '标识-选择伙伴').is_success:
            return self.round_fail('非选择伙伴屏')
        cands = self._read_candidates(screen)
        _char_ids = self._identify_portraits(screen, cands) if cands else []
        obs = CwScreenPartnerObs(
            on_screen=True,
            options=[PartnerOption(idx=i, char_id=n)
                     for i, n in enumerate(_char_ids)],
            screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_partner_obs(_gs, obs)
        self._obs = obs
        self._cands = cands
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=10)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 确认被拒守卫 + 首轮决策一次 → 脉冲 → round_wait。

        重入裁决(观察驱动,验证废除形态):确认已发 → 标识不在 = overlay
        已关(两步链完结)→ success 交回;标识在 = 确认未落地 → 重走脉冲。

        每轮脉冲(机制出处 = 模块头更正注):
        1. 未选中提示在场(置灰实锤)∧ 脉冲已达上限 → 显式 fail(确认被拒
           形态有界重试,禁原样无限重试);
        2. 首轮决策一次(零参 decide,写槽已由 report 落容器;chosen 留守
           选择点)定同一点位;守卫①②③(候选空 = 具名 fail;返回
           None·词表外 = 具名 fail 含原值;越界 = AssertionError)先于决策
           与写端,零点击;无 match 局外不设早退支(用户裁决 2026-09-22
           全族删门);
        3. 提示在场(含重入轮)= 未选中实证 → 点候选卡(单选语义重点
           已选卡无反选面;提示不在 = 不重点选,防未知选中呈现被扰动);
        4. 点确认(mouse_move 防吞点击 + click);确认是否落地由下一轮
           重入裁决,不原地判选中态。"""
        screen = self.last_screenshot
        if self._confirm_pending:
            self._confirm_pending = False
            if not self.round_by_find_area(
                    screen, '货币战争-列车同行',
                    '标识-选择伙伴').is_success:
                return self.round_success(wait=2)
        unselected = self._unselected_hint_present(screen)
        if unselected and self._confirm_pulses >= CwScreenPartner.CONFIRM_REJECT_MAX:
            log.info('[cw-partner] 确认被拒形态:未选中提示持续在场 %s 轮 → 显式失败交外环',
                     self._confirm_pulses)
            return self.round_fail(
                '伙伴确认被拒(未选中提示持续在场,确认钮置灰;候选选中未生效)')
        if self._pick_point is None:
            cands = self._cands
            options = self._obs.options if self._obs is not None else []
            match = self.ctx.cw_match
            # 守卫①(决策输入,零点击零派发):候选空 = 在册显式失败(留守
            # round_fail;原常量 idx0 盲选派发退役)。
            if not options:
                return self.round_fail('伙伴屏无候选(OCR 未命中候选标签),禁兜底盲点')
            # 无 match 局外不设早退支(画面 op 不支持局外单独调用,op-layer.md
            # §1.1;用户裁决 2026-09-22 全族删门):单跑缺上下文沿正常链路
            # 在此失败即预期,禁回填此类单跑防御分支。
            # 守卫②(返回契约,op-layer §1.3):None/词表外 = 策略器 bug 具名
            # fail 留证(原 AttributeError 异常出口子径收编,消息含原值)。
            pick = match.strategy.decide_partner()
            if not isinstance(pick, CwActionPickPartnerParam):
                return self.round_fail(
                    f'decide_partner 决策无有效输出(词表外/None): {pick!r}')
            # 守卫③(值域,op-layer §1.3 守卫断言):越界 = 恒炸,禁钳位。
            # 界 = len(cands)(点击目标数组;options 与 cands 恒等长——obs options
            # 由 cands enumerate 生成,observe/_identify_portraits 三分支恒返
            # len==len(cands))。
            if not (0 <= pick.idx < len(cands)):
                raise AssertionError(
                    f'[cw-partner] pick idx 越界(策略器 bug,禁钳位): '
                    f'idx={pick.idx} len(cands)={len(cands)} pick={pick!r}')
            self._pick_idx = pick.idx
            log.info('[cw-partner] candidates=%s pick=idx%s %s',
                     [o.char_id for o in options], pick.idx, pick.reason)
            # 伙伴选择落容器 chosen_partner(gs 单一源,session 域无此写端;守卫
            # ①③已保证 options 非空且 idx 在界;点选前写 = 选择点,单次逻辑写入
            # 豁免面,与巨星 chosen_megastar 派发前写同款;fields.md §3.4 导语
            # 判定点在册)。
            if getattr(match, 'gs', None) is not None:
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    ChannelSig,
                )
                match.gs.write_logic(
                    match.gs.chosen_partner,
                    options[self._pick_idx].char_id or '',
                    produced_by='CwScreenPartner',
                    sig=ChannelSig(family='logic_action',
                                   actor='CwScreenPartner', mode='compute'))
            point = self._pick_point_for(cands[self._pick_idx])
            if point is None:
                return self.round_fail('伙伴屏建档缺失:候选-卡区(禁裸坐标兜底)')
            self._pick_point = point
        # 「点选候选 → 确认」脉冲链经注册表工厂派发(``cw_pick_partner_action.py::
        # CwActionPickPartnerOp``,机械链 + 自上报在动作 op 内)。
        # 决策半(确认被拒守卫/点位解析/chosen 写端)留守上方;选中态标记
        # 与脉冲计数宿主仍是本 op,经 env.op 消费。派发实例携真实选中
        # 下标(上报 param 即真实选择;脉冲轮复用缓存 idx)。
        # round_wait 推进循环(不烧节点重试预算;确认未落地轮重走脉冲,
        # 有界防线 = CONFIRM_REJECT_MAX)。
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self, idx=self._pick_idx, unselected=unselected)
        action_op_for(CwActionPickPartnerParam(idx=self._pick_idx), self.ctx,
                      _env).execute()
        return self.round_wait()
