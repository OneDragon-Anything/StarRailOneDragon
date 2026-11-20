"""货币战争 奇遇对话 op(1+N 特殊流程多 node;迭代 2026-11-20-cw-p0-chain
design §2.2)。

奇遇对话屏 = 伙伴立卡 + 对话气泡 + 右下箭头(多例奇遇共用同一布局,
公共锚 = 箭头模板;伙伴名随局可变不可作 mark)。本 op 完成「对话推进
循环 → 分诊 →(偶发)奇遇选择卡两段式」,做完切屏落点随奇遇而异
(备战 / 茶歇页 / 新对话段),交回主循环重判。

形态(观察 + 对话推进 + 分诊 + 两段式 = 1+N 特殊流程多 node,
screen-op.md §1「同画面子态的 node 归属」——推进/两段式为互斥子态
各一 node):

- 观察 node = 入口门(标识-对话箭头模板,miss = round_fail 交回主循环)
  + 伙伴名一次读(读区-伙伴卡区,读不到 = None)+ obs report
  (card_options 空——卡未在场,report 读缺跳写)。
- 对话推进 node = 点箭头 + until_not 箭头消失(对话尽判效锚;点空白
  无效——玩家卡明示只点箭头),循环有界 DIALOG_MAX(失败治理出口:
  对话不收敛/箭头反复复现 = 失败态,非健康推进截断)。
- 分诊 node = 箭头 miss 后四出口(备战标志 = 奇遇完成;茶歇标题 = 交回
  主循环派茶歇 op——触发链由主循环分发自然衔接,op 内不跳转;奇遇卡 =
  两段式;箭头复现 = 回推进)+ 全 miss round_wait 等过渡帧自愈
  (连续 miss 超限 = 失败治理出口)。
- 两段式 node = 重入顶部先查生效判据(奇遇卡消失 ∨ 箭头复现 = 生效交回
  主循环——防陈帧误点:round_wait 重跑整个节点函数,字面序会先跑本段
  识别读陈帧、再按陈坐标误点底层画面真实控件)→ 本段识别〔读屏例外③〕
  读卡选项并同帧 report → 固定规则决策(复用
  cw_screen_tea_break.pick_option_idx,R2/R2b 排除必要——教学局样本含
  HP 降到 1 负面卡与「返回」退出卡)→ 点卡(零参读坐标)→ 卡上确认钮
  出现 = 选中生效 → 点卡上确认(执行期现读:确认钮 y 随选中卡浮动,
  帧证 120117,非固定控件不建常量)→ round_wait 重入查生效。

上报段:伙伴名写 ``adventure_partner_name``、卡选项写
``adventure_card_opts``/``adventure_card_opts_xy``(同门同帧同序等长,
读缺跳写);obs 经 report 写入后即弃,决策与点击按 idx 零参读 game
state,op 内零观察数据副本(白话禁令)。
"""
from __future__ import annotations

from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.matcher.ocr.ocr_match_result import OcrMatchResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_screen_report.adventure_dialog import (
    CwScreenAdventureDialogObs,
    report_screen_adventure_dialog_obs,
)
from sr_od.application.currency_war.operations.cw_operation_base import (
    CwOperation,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_tea_break import (
    pick_option_idx,
)
from sr_od.context.sr_context import SrContext

_SCREEN: str = '货币战争-奇遇对话'
A_ARROW: str = '标识-对话箭头'
A_PARTNER_STRIP: str = '读区-伙伴卡区'
A_CARD_STRIP: str = '读区-奇遇卡按钮区'
A_CARD_CONFIRM: str = '按钮-卡上确认'
#: 分诊出口识别锚(跨档:备战标志 / 茶歇标题)。
A_PREP_BACK: str = '备战标识-购买经验'
A_TEA_TITLE: str = '标识-茶歇标题'

#: 状态词(分诊 → 推进/两段式的路由键;两处消费逐字同源,常量化防漂移)。
STATUS_ADVANCE: str = '箭头复现,回对话推进'
STATUS_CARD: str = '奇遇选择卡在场,进两段式'


class CwScreenAdventureDialog(CwOperation):
    """奇遇对话:点箭头推进对话 → 分诊 → 奇遇卡两段式(若在)→ 交回主循环。
    起点:货币战争-奇遇对话(对话页);终点:奇遇完成(落点随奇遇而异,
    交回主循环重判)。

    :param ctx: 框架上下文(MCP 反射协议字段)。
    """
    # 对话推进页数帽(失败治理出口:现役样本对话均短,超限 = 对话不收敛/
    # 箭头反复复现的失败态,交外环响亮暴露;design §2.2 上限性质裁定)。
    DIALOG_MAX: ClassVar[int] = 20
    # 分诊全 miss(过渡帧)连续容忍上限,超限 = 失败治理出口交外环。
    TRIAGE_MISS_MAX: ClassVar[int] = 5
    # 两段式进入次数帽(首发 1 + 重试 3;含确认被吞/拖卡未生效形态,
    # CwScreenPartner CONFIRM_REJECT_MAX 同族有界防线)。
    CARD_ATTEMPT_MAX: ClassVar[int] = 4
    # 选项卡 y 聚合阈值(卡内选项行距 ~68-75,卡间隙实测 92;取 80 居中,
    # 帧证 = 120053 三选一〔518→610 差 92 拆开〕/120117 确认态;与
    # cw_screen_tea_break.BRANCH_MERGE_Y 同口径同值——卡形同构)。
    CARD_MERGE_Y: ClassVar[int] = 80

    def __init__(self, ctx: SrContext):
        CwOperation.__init__(self, ctx, op_name='货币战争-奇遇对话')
        # 对话推进页数计数(advance 每次进入 +1;失败治理出口,见 DIALOG_MAX)。
        self._dialog_steps: int = 0
        # 分诊全 miss 连续计数(triage 自环重入累计;命中任一出口即复位语义
        # ——节点直接离开自环,计数随实例废弃)。
        self._triage_misses: int = 0
        # 两段式进入计数(首发 + 重试;CARD_ATTEMPT_MAX 有界)。
        self._card_attempts: int = 0

    def _read_items(self, screen, area_name: str) -> list[OcrMatchResult]:
        """读区 OCR 直调(list 形态;与 cw_screen_tea_break._read_items
        同签名等价实现)。"""
        si = self.ctx.screen_loader.get_screen(_SCREEN)
        rect = None
        if si is not None:
            area = next((a for a in si.area_list
                         if a.area_name == area_name), None)
            if area is not None:
                rect = area.pc_rect
        if rect is None:
            return []
        return self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=rect, crop_first=False)

    def _read_partner_name(self, screen) -> str | None:
        """伙伴名 OCR(读区-伙伴卡区):取带内 y 最小的中文短词 item
        (名牌在立绘下方,帧证 120053「姬奇猫」y≈783);读不到 = None
        (report 跳写)。"""
        items = [it for it in self._read_items(screen, A_PARTNER_STRIP)
                 if (it.data or '').strip()]
        words = [it for it in items if 2 <= len(it.data.strip()) <= 6]
        if not words:
            return None
        return min(words, key=lambda t: t.y + t.h // 2).data.strip()

    def _read_card_units(self, screen
                         ) -> list[tuple[str, tuple[int, int, int, int]]]:
        """奇遇选择卡选项单元(y 聚合,阈值 CARD_MERGE_Y;文本 = 卡内 item
        依序拼接,点击框 = 聚合包围盒——中心落卡体,与茶歇分支态同口径)。

        两道单元过滤(帧证 = 归档帧离线实读):
        - 「确认」短词 item 剔除:卡上确认钮词面(选中态展开后钮出现在
          选中条内,帧证 120117)不是选项内容——不剔会把确认词拼进选中卡
          文本,重入轮 report 覆盖后 R2 词面决策失真;
        - 首行长度过滤:选项卡首行 = 短词标题(≤8 字,三例样本 2-5 字),
          对话气泡长句(>8 字)落在「读区-奇遇卡按钮区」与气泡重叠带的
          item 丢弃——防对话页气泡被误判为卡选项(箭头 miss 过渡帧场景)。"""
        items = [it for it in self._read_items(screen, A_CARD_STRIP)
                 if (it.data or '').strip()
                 and not ('确认' in (it.data or '').strip()
                          and len((it.data or '').strip()) <= 4)]
        items.sort(key=lambda t: t.y + t.h // 2)
        groups: list[list[OcrMatchResult]] = []
        for it in items:
            cy = it.y + it.h // 2
            if (groups and cy - (groups[-1][-1].y + groups[-1][-1].h // 2)
                    <= CwScreenAdventureDialog.CARD_MERGE_Y):
                groups[-1].append(it)
            else:
                groups.append([it])
        units: list[tuple[str, tuple[int, int, int, int]]] = []
        for grp in groups:
            head = (grp[0].data or '').strip()
            if len(head) > 8:
                continue   # 首行长句 = 对话气泡,非选项卡
            text = ''.join(t.data or '' for t in grp)
            box = (min(t.x for t in grp), min(t.y for t in grp),
                   max(t.x + t.w for t in grp), max(t.y + t.h for t in grp))
            units.append((text, box))
        return units

    def _report(self, screen, partner_name: str | None,
                card_units: list[tuple[str, tuple[int, int, int, int]]]) -> None:
        """上报段:obs 经 report 写 game state(读缺跳写闸在 report 内);
        obs 构造即弃零副本(白话禁令)。两类构造点共用本口(观察 node 卡
        未在场 = 空列表;两段式 node 本段识别 = 填充)。"""
        obs = CwScreenAdventureDialogObs(
            on_screen=True, partner_name=partner_name,
            card_options=list(card_units), screen=screen)
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_screen_adventure_dialog_obs(gs, obs)

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口门(箭头模板)+ 伙伴名一次读 + obs report → 对话推进。

        门 miss = round_fail 交回主循环重判(选择卡页无箭头不命中本档,
        主循环身份分发自然不进本 op——分诊的卡出口只经推进后到达)。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, _SCREEN, A_ARROW).is_success:
            return self.round_fail('非奇遇对话屏(箭头锚未命中)')
        partner = self._read_partner_name(screen)
        self._report(screen, partner, [])
        return self.round_success('对话页入口,交对话推进', wait=0)

    @node_from(from_name='观察')
    @node_from(from_name='分诊', status=STATUS_ADVANCE)
    @operation_node(name='对话推进', node_max_retry_times=10)
    def advance(self) -> OperationRoundResult:
        """点箭头推进一页;until_not 箭头消失 = 对话尽判效锚。

        翻页后新页箭头复现 = until 不满足再点(每成功轮推一页);最后一页
        点完箭头不再出现 = 成功交分诊。页数帽 = 失败治理出口(DIALOG_MAX)。"""
        self._dialog_steps += 1
        if self._dialog_steps > CwScreenAdventureDialog.DIALOG_MAX:
            return self.round_fail(
                f'对话推进超限(>{CwScreenAdventureDialog.DIALOG_MAX}页,'
                f'箭头反复复现交外环)')
        rr = self.round_by_find_and_click_area(
            self.last_screenshot, _SCREEN, A_ARROW,
            until_not_find_all=[(_SCREEN, A_ARROW)],
            success_wait=1.0, retry_wait=0.8)
        if rr.is_success:
            return self.round_success('箭头已消失(对话尽),交分诊', wait=0.5)
        return rr

    @node_from(from_name='对话推进')
    @operation_node(name='分诊', node_max_retry_times=10)
    def triage(self) -> OperationRoundResult:
        """箭头 miss 后四出口 + 全 miss 过渡帧自愈(design §2.2 分诊节点):
        备战标志 = 奇遇完成;茶歇标题 = 交回主循环(下帧派茶歇 op,op 内
        不跳转);奇遇卡 = 两段式;箭头复现 = 回推进;全 miss = round_wait
        原样重跑本节点(过渡帧自愈),连续超限 = 失败治理出口。
        本 node 只建两条精确 status 边(奇遇卡/箭头复现)——奇遇完成/茶歇
        交回两出口 = 带自定义 status 的 SUCCESS 无精确边命中,op 以该
        状态成功结束交回主循环(建兜底自环边会让 SUCCESS 回本节点无限
        循环)。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, '货币战争-备战', A_PREP_BACK,
                                   crop_first=False).is_success:
            return self.round_success('奇遇完成,已回备战(交回主循环)', wait=0.5)
        if self.round_by_find_area(screen, '货币战争-幕后茶歇', A_TEA_TITLE,
                                   crop_first=False).is_success:
            return self.round_success('奇遇完成,切茶歇页(交回主循环派茶歇 op)',
                                      wait=0.5)
        card_units = self._read_card_units(screen)
        if card_units:
            self._report(screen, None, card_units)
            return self.round_success(STATUS_CARD, wait=0)
        if self.round_by_find_area(screen, _SCREEN, A_ARROW,
                                   crop_first=False).is_success:
            return self.round_success(STATUS_ADVANCE, wait=0)
        self._triage_misses += 1
        if self._triage_misses > CwScreenAdventureDialog.TRIAGE_MISS_MAX:
            return self.round_fail(
                f'分诊连续全 miss(>{CwScreenAdventureDialog.TRIAGE_MISS_MAX}帧'
                f',过渡帧不收敛交外环)')
        return self.round_wait('分诊全 miss(过渡帧),等下一帧重跑', wait=0.8)

    @node_from(from_name='分诊', status=STATUS_CARD)
    @operation_node(name='两段式', node_max_retry_times=10)
    def card_phase(self) -> OperationRoundResult:
        """奇遇选择卡两段式:点卡选中 → 点卡上确认执行。

        重入顶部先查生效判据(奇遇卡消失 ∨ 箭头复现 = 生效交回主循环)
        ——round_wait 重跑整个节点函数,不按节点体清单字面序实现(字面序
        会在成功路径上先跑本段识别读陈帧、再按陈坐标误点底层画面真实
        控件,design §2.2 重入次序定稿申报)。未生效 = 进入计数 +1(超限
        fail 交外环)→ 本段识别〔例外③〕同帧 report → 零参读决策产 idx
        → 点卡 → 卡上确认钮在场 = 选中生效 → 现读确认钮中心点执行 →
        round_wait 原样重跑查生效;确认钮未在场 = 选中未生效,round_wait
        重入重走整链(gs 未变 idx 恒定,重点同卡幂等)。本 node 无出边
        (生效 success 即访问终态交回主循环——带 status 的 SUCCESS 走
        自环兜底边 = 无限循环,故生效重查只用 round_wait 不建自环边)。"""
        screen = self.last_screenshot
        card_gone = not self._read_card_units(screen)
        arrow_back = self.round_by_find_area(screen, _SCREEN, A_ARROW,
                                             crop_first=False).is_success
        if card_gone or arrow_back:
            return self.round_success('两段式生效(卡消失/箭头复现),交回主循环',
                                      wait=0.5)
        self._card_attempts += 1
        if self._card_attempts > CwScreenAdventureDialog.CARD_ATTEMPT_MAX:
            return self.round_fail(
                f'两段式超限(>{CwScreenAdventureDialog.CARD_ATTEMPT_MAX}次进入'
                f',卡未消失交外环)')
        units = self._read_card_units(screen)
        if not units:
            return self.round_fail('两段式卡选项读缺(交外环)')
        self._report(screen, None, units)
        opts = self._gs_opts()
        idx = pick_option_idx(opts)
        if idx is None:
            return self.round_fail(f'卡选择无合规项(opts={opts!r})')
        pt = self._gs_point(idx, len(opts))
        self.ctx.controller.mouse_move(pt)
        self.ctx.controller.click(pt)
        log.info('[cw-adventure] 点卡 idx=%s %s @%s', idx, opts[idx], pt)
        selected = self.round_by_find_area(
            self.screenshot(), _SCREEN, A_CARD_CONFIRM, success_wait=0.8)
        if not selected.is_success:
            return self.round_wait('点卡未生效(卡上确认钮未现),重入重走',
                                   wait=1.0)
        confirm_pt = self._read_card_confirm_point(self.screenshot())
        if confirm_pt is None:
            return self.round_wait('卡上确认钮现读失败,重入重走', wait=1.0)
        self.ctx.controller.mouse_move(confirm_pt)
        self.ctx.controller.click(confirm_pt)
        return self.round_wait('卡上确认已发,重入查生效判据', wait=1.2)

    def _read_card_confirm_point(self, screen) -> Point | None:
        """卡上确认钮执行期现读:「按钮-卡上确认」识别域内「确认」词面
        item rect 中心(钮 y 随选中卡浮动,帧证 120117——非固定控件,
        常量不可行、非观察期快照不进 game state,执行期现读承载)。"""
        si = self.ctx.screen_loader.get_screen(_SCREEN)
        rect = None
        if si is not None:
            area = next((a for a in si.area_list
                         if a.area_name == A_CARD_CONFIRM), None)
            if area is not None:
                rect = area.pc_rect
        if rect is None:
            return None
        for it in self.ctx.ocr_service.get_ocr_result_list(
                image=screen, rect=rect, crop_first=False):
            if '确认' in (it.data or ''):
                return Point(int(it.x + it.w // 2), int(it.y + it.h // 2))
        return None

    def _gs_opts(self) -> list[str]:
        """game state 卡选项文本零参读(缺席 = 空表,决策产出 None 显式失败)。"""
        gs = game_state_from_ctx(self.ctx)
        if gs is None:
            return []
        return list(gs.adventure_card_opts.value or [])

    def _gs_point(self, idx: int, opts_len: int) -> Point:
        """game state 卡坐标伴随域按 idx 取点(守卫断言禁钳位,
        机制同 cw_screen_tea_break._gs_point)。"""
        gs = game_state_from_ctx(self.ctx)
        pts = list(gs.adventure_card_opts_xy.value or []) \
            if gs is not None else []
        if len(pts) != opts_len or not (0 <= idx < len(pts)):
            raise AssertionError(
                f'[cw-adventure] 坐标伴随域失配(禁钳位): idx={idx} '
                f'len(xy)={len(pts)} len(opts)={opts_len}')
        x, y = pts[idx]
        return Point(int(x), int(y))
