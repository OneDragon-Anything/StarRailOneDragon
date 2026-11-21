"""货币战争 主角光环选择 op(1+N;迭代 2026-11-20-cw-p0-chain design
§2.3 op4,**消费既有 CwSelectProtagonist 不改本体**)。

位面末 BOSS 战前强制选择:选光环卡 → 拖主角 → 确认三步(经
CwSelectProtagonist),做完锚定回备战,交回主循环。

形态(观察/决策/动作/判效):

- 观察 node = 入口门(标识-主角光环标题,miss = round_fail 交回主循环)
  + 光环名一次读(**观察标准化门**两段转换:①形变归一后对注册表
  ``data/cw_spot_lights.py`` 精确匹配;②不中 ``lcs_resolve_strict`` 相似
  匹配〔次高分差拒判,阈值常量住本 op〕;转换失败 = 观察失败 round_fail
  早退交外环重读,禁带病上报)+ 光环卡中心(档 area 中心)与预览卡拖拽
  源点(**几何产点**,见常量申报)→ report 落 ``aura_select_opts``/
  ``aura_select_opts_xy``/``aura_select_preview_xy``;obs 经 report 写入
  后即弃,op 内零观察数据副本(白话禁令)。
- 决策 = op 内固定规则 v1(常量化,**策略钩子升级位声明**:光环认知决策
  归后续策略批,消费既有 ``aura_select_opts`` 零参读,升级批零 game state
  改动):``aura_side='left'``(= idx 0)+ 前排第一张预览卡(=
  ``aura_select_preview_xy`` idx 0)。
- 动作 node = ``CwSelectProtagonist(self.ctx, aura_side, source_x,
  source_y).execute()`` 原样消费(点卡选中/拖入主角槽/微距确认三步;
  拖拽源零参读坐标伴随域,op 零内部识别;**不改本体**——既有拖拽偶发
  被吞缺陷由消费方重试包装吸收,本体修复归缺陷批)。
- 判效 node = 回备战标志在场 ∧ 光环屏标题 miss 双锚(**非 until 原语
  承载**——until 系 area 点击原语专属,本 op 动作经子 op execute 非点击
  原语);判效 miss(确认未生效)= 回动作 node 换抓点重试 ≤3(换抓点
  语义 = 优先同卡换点、跨卡取下一候选点如实申报——落位主角随重试漂移,
  v1 固定决策仅约束首发;功能无害:非适配角色放置无阻拦),超限
  round_fail 交外环(CwScreenPartner 脉冲形态:确认是否落地由下一轮
  验证)。判效双锚过 = 选择落地:按末次抓点槽写 ``aura_slot``
  (动作上报 ``report_action_aura_select_param`` 单一写函数,与备战帧
  光标观察同字段互证;抓点落后排越值域跳写交观察收尾)。
  **不消费「按钮-返回备战界面」**(放弃 = 主角未选 = 堵主线
  持续,fail 交外环如实暴露)。
"""
from __future__ import annotations

from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_spot_lights import SPOT_LIGHTS
from sr_od.application.currency_war.kernel.cw_action_report.aura_select import (
    report_action_aura_select_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_obs_core import (
    lcs_resolve_strict,
)
from sr_od.application.currency_war.kernel.cw_screen_report.aura_select import (
    CwScreenAuraSelectObs,
    report_screen_aura_select_obs,
)
from sr_od.application.currency_war.operations.actions.cw_select_protagonist import (
    CwSelectProtagonist,
)
from sr_od.application.currency_war.operations.cw_operation_base import (
    CwOperation,
)
from sr_od.context.sr_context import SrContext

_SCREEN: str = '货币战争-主角光环选择'
A_TITLE: str = '标识-主角光环标题'
A_CARD_L: str = '卡-左光环'
A_CARD_R: str = '卡-右光环'
#: 分诊/判效跨档锚(回备战标志;area 在备战档)。
A_PREP_BACK: str = '备战标识-购买经验'

#: 状态词(判效 → 动作的换抓点重试路由键;两处消费逐字同源)。
STATUS_VERIFY_MISS: str = '判效miss,回动作换抓点'

#: 光环域标准注册表名(82 条 SpotLight.name,plaza 官方口径镜像;
#: 观察标准化门适用,design §2.8)。
_AURA_NAMES: list[str] = [x.name for x in SPOT_LIGHTS]
#: LCS 相似解析阈值/歧义分差(值沿 cw_screen_bookcard 同款先例 0.75/0.15;
#: 注册表 4-6 字名为主,1 字误读 4 字名恰过阈)。
_LCS_THRESHOLD: float = 0.75
_LCS_AMBIGUITY_MARGIN: float = 0.15


class CwScreenAuraSelect(CwOperation):
    """主角光环选择:读光环 → 固定规则 v1(left+前排第一)→ 三步链(经
    CwSelectProtagonist)→ 判效回备战。
    起点:货币战争-主角光环选择;终点:选择完成,画面回货币战争-备战
    (交回主循环)。
    消耗:确认后本位面主角绑定生效(不可逆;光环随位面重选)。

    :param ctx: 框架上下文(MCP 反射协议字段)。
    """
    # —— 预览卡几何产点常量(存疑 7 消解裁定;单帧标定 = 归档帧
    #    screenshot_20261119_205441_649975 裁剪回读:前排 4 卡实测中心
    #    789/890/990/1090 vs 公式 795/895/995/1095、后排 6 槽实测
    #    694..1194 vs 公式 695..1195,全 ≤5px;OCR 名牌不可行〔预览卡无
    #    文本,帧证同帧 OCR 只读得角标数字〕、模板匹配不可行〔头像各异
    #    无通用模板〕,落几何公式)——
    #: 布局带中点 x(= 槽-中央主角槽 area 中心 x,布局以中央槽对称)。
    PREVIEW_MID_X: ClassVar[int] = 945
    #: 相邻槽中心距(前/后排同距)。
    PREVIEW_SLOT_GAP: ClassVar[int] = 100
    #: 前排/后排行中心 y(帧证标定;玩家卡目测 640/745 为旧估值)。
    FRONT_ROW_Y: ClassVar[int] = 620
    BACK_ROW_Y: ClassVar[int] = 762
    #: 前排/后排槽位容量(部署布局固定结构:前排 4 + 后排 6;空骨架槽
    #: 上的候选点 = 拖拽被吞形态,由换抓点重试自然跳过——部署 <5 形态
    #: 未采样,重试预算边界如实申报交实机验证)。
    FRONT_SLOTS: ClassVar[int] = 4
    BACK_SLOTS: ClassVar[int] = 6
    #: 右半部抓取偏移(读法定义的一部分,产点即含——抓预览卡中心
    #: 3 试 2 败、抓右半部成功,玩家卡四局实证;动作零现算)。
    GRAB_RIGHT_OFFSET: ClassVar[int] = 20
    #: 同卡换抓点额外右移(重试序列候选 2;二次拖拽换点语义)。
    GRAB_ALT_OFFSET: ClassVar[int] = 15
    # 判效 miss 换抓点重试上限(重试序列:同卡换点 → 跨卡下一候选点;
    # 落位主角随重试漂移,v1 固定决策仅约束首发,design §2.3 申报)。
    VERIFY_RETRY_MAX: ClassVar[int] = 3

    def __init__(self, ctx: SrContext):
        CwOperation.__init__(self, ctx, op_name='货币战争-主角光环选择')
        # 换抓点尝试序号(动作 node 每次进入消费后 +1;0 = 首发,
        # 1/2/3 = 重试序列位,见 _grab_point_for)。
        self._attempt: int = 0
        # 判效 miss 计数(判效 node 累计,超 VERIFY_RETRY_MAX fail;
        # 实例级,单 op 生命周期)。
        self._verify_misses: int = 0
        # 末次抓点预览下标(行主序;动作 node 每次进入经 _grab_point_for
        # 更新,None = 动作未发;选择记账消费——判效过后按它落 aura_slot,
        # 下标 0-3 = 前排槽 1-4(与 aura_select_preview_xy 坐标系同源申报),
        # ≥4 = 后排越值域跳写)。
        self._last_grab_idx: int | None = None

    def _normalize_aura_name(self, raw: str) -> str:
        """观察标准化门两段转换(域级单一实现住本 op,机制同
        cw_screen_bookcard._standardize_card_factions):
        ①形变归一(空白剥离)后注册表精确匹配;
        ②不中 ``lcs_resolve_strict`` 相似匹配(次高分差拒判);
        两段皆不中 ∨ 歧义 = 转换失败返回 ''(调用方观察失败早退,
        禁带病上报)。两槽独立解析,重复名合法面不判失败
        (左右为两个独立展示槽非互斥候选集,design §2.3 边界登记)。"""
        word = ''.join((raw or '').split())
        if not word:
            return ''
        if word in _AURA_NAMES:
            return word
        return lcs_resolve_strict(
            word, _AURA_NAMES,
            threshold=_LCS_THRESHOLD,
            ambiguity_margin=_LCS_AMBIGUITY_MARGIN)

    def _read_aura_name(self, screen, area_name: str) -> str:
        """光环名读盘:卡 area 内 OCR 取 y 最小 item(图标无文本,名字 =
        卡内首个文本 item;效果全文在名字带之下,帧证 205441)→ 标准化门
        两段转换;空读/转换失败 = ''(调用方观察失败早退)。"""
        si = self.ctx.screen_loader.get_screen(_SCREEN)
        rect = None
        if si is not None:
            area = next((a for a in si.area_list
                         if a.area_name == area_name), None)
            if area is not None:
                rect = area.pc_rect
        if rect is None:
            return ''
        items = [it for it in self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=rect, crop_first=False)
            if (it.data or '').strip()]
        if not items:
            return ''
        top = min(items, key=lambda t: t.y + t.h // 2)
        return self._normalize_aura_name(top.data)

    def _preview_points(self) -> list[tuple[int, int]]:
        """预览卡拖拽源点产点(几何公式,行主序:前排从左到右,随后后排;
        产点含右半部抓取偏移——读法定义的一部分,动作零现算;
        ``aura_select_preview_xy`` 的写端产点规则,坐标系申报住
        cw_game_state 字段注释,本 op 零第二定义处)。"""
        pts: list[tuple[int, int]] = []
        for i in range(CwScreenAuraSelect.FRONT_SLOTS):
            cx = (CwScreenAuraSelect.PREVIEW_MID_X
                  + (i - (CwScreenAuraSelect.FRONT_SLOTS - 1) / 2)
                  * CwScreenAuraSelect.PREVIEW_SLOT_GAP)
            pts.append((int(cx) + CwScreenAuraSelect.GRAB_RIGHT_OFFSET,
                        CwScreenAuraSelect.FRONT_ROW_Y))
        for i in range(CwScreenAuraSelect.BACK_SLOTS):
            cx = (CwScreenAuraSelect.PREVIEW_MID_X
                  + (i - (CwScreenAuraSelect.BACK_SLOTS - 1) / 2)
                  * CwScreenAuraSelect.PREVIEW_SLOT_GAP)
            pts.append((int(cx) + CwScreenAuraSelect.GRAB_RIGHT_OFFSET,
                        CwScreenAuraSelect.BACK_ROW_Y))
        return pts

    def _aura_centers(self) -> list[tuple[int, int]] | None:
        """光环卡中心(档 area 中心,左 = idx 0;观察时取出进载荷——
        位置固定仍须上报,商店五槽位先例);任一 area 缺失 = None
        (观察失败早退)。"""
        si = self.ctx.screen_loader.get_screen(_SCREEN)
        if si is None:
            return None
        centers: list[tuple[int, int]] = []
        for name in (A_CARD_L, A_CARD_R):
            area = next((a for a in si.area_list
                         if a.area_name == name), None)
            if area is None or area.pc_rect is None:
                return None
            c = area.pc_rect.center
            centers.append((int(c.x), int(c.y)))
        return centers

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口门 + 光环名标准化门 + 几何产点 → report → 动作。

        门 miss = round_fail 交回主循环重判;光环名任一槽转换失败 =
        观察失败 round_fail 早退交外环重读(禁带病上报——门全域语义);
        档 area 缺失(卡中心取不出)= 观察失败同格。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(screen, _SCREEN, A_TITLE).is_success:
            return self.round_fail('非主角光环选择屏')
        left = self._read_aura_name(screen, A_CARD_L)
        right = self._read_aura_name(screen, A_CARD_R)
        if not left or not right:
            return self.round_fail(
                f'光环名标准化失败(left={left!r} right={right!r},'
                f'观察失败交外环重读)')
        centers = self._aura_centers()
        if centers is None:
            return self.round_fail('光环卡中心取不出(档 area 缺失,交外环)')
        obs = CwScreenAuraSelectObs(
            on_screen=True, aura_left=left, aura_right=right,
            aura_centers=centers, preview_points=self._preview_points(),
            screen=screen)
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_screen_aura_select_obs(gs, obs)
        log.info('[cw-aura] 光环观察 left=%s right=%s(标准化后),'
                 '预览产点 %d 个', left, right, len(obs.preview_points))
        return self.round_success('光环已读,交动作三步链', wait=0)

    @node_from(from_name='观察')
    @node_from(from_name='判效', status=STATUS_VERIFY_MISS)
    @operation_node(name='动作')
    def act(self) -> OperationRoundResult:
        """三步链原样消费 CwSelectProtagonist(点卡 → 拖主角 → 微距确认;
        **不改本体**),拖拽源 = ``aura_select_preview_xy`` 零参读 +
        换抓点序列(首发 idx 0;重试 1 = 同卡换点 +ALT_OFFSET,
        重试 2+ = 跨卡下一候选点——落位主角随重试漂移如实申报)。
        坐标伴随域缺席/越界 = 守卫断言显式报错(禁钳位禁回退)。"""
        grab = self._grab_point_for(self._attempt)
        log.info('[cw-aura] 三步链 attempt=%s 拖拽源=%s(v1 固定 left+前排第一)',
                 self._attempt, grab)
        CwSelectProtagonist(self.ctx, 'left', int(grab.x),
                            int(grab.y)).execute()
        self._attempt += 1
        return self.round_success('三步链已发,交判效', wait=0.3)

    def _grab_point_for(self, attempt: int) -> Point:
        """换抓点序列:attempt 0 = preview_xy[0](首发,v1 固定决策位);
        1 = 同卡换点(idx 0 点右移 GRAB_ALT_OFFSET——二次拖拽换点);
        ≥2 = 跨卡下一候选点起递进(attempt 2 → idx 1,attempt 3 → idx 2
        ——落位主角随重试漂移面,功能无害)。坐标伴随域缺席 =
        AssertionError 显式报错(消费守卫契约)。"""
        gs = game_state_from_ctx(self.ctx)
        pts = list(gs.aura_select_preview_xy.value or []) \
            if gs is not None else []
        if not pts:
            raise AssertionError(
                '[cw-aura] aura_select_preview_xy 缺席(观察未上报,禁回退)')
        idx = 0
        extra = 0
        if attempt == 1:
            extra = CwScreenAuraSelect.GRAB_ALT_OFFSET
        elif attempt >= 2:
            idx = min(attempt - 1, len(pts) - 1)
        self._last_grab_idx = idx
        x, y = pts[idx]
        return Point(int(x) + extra, int(y))

    def _report_aura_slot(self) -> None:
        """选择记账:判效双锚过后光环归属槽写 logic(动作上报单一函数
        ``report_action_aura_select_param``;落点 = 末次抓点槽——换抓点
        重试漂移如实记账,与备战帧光标观察同字段同语义互证)。
        抓点落后排 = 越前排查值域跳写交观察收尾(现役重试预算内不可达,
        防御面如实申报);局外(gs 缺席)= 零写,同观察上报口径。"""
        gs = game_state_from_ctx(self.ctx)
        if gs is None or self._last_grab_idx is None:
            return
        if self._last_grab_idx >= CwScreenAuraSelect.FRONT_SLOTS:
            log.info('[cw-aura] 末次抓点 idx=%d 落后排,越 aura_slot 前排'
                     '值域跳写(交下一备战帧观察收尾)', self._last_grab_idx)
            return
        report_action_aura_select_param(
            gs, self._last_grab_idx + 1,
            sig=ChannelSig(family='logic_action', actor='CwScreenAuraSelect',
                           screen=_SCREEN, mode='compute'))

    @node_from(from_name='动作')
    @operation_node(name='判效')
    def verify(self) -> OperationRoundResult:
        """回备战标志在场 ∧ 光环屏标题 miss 双锚(**非 until 原语承载**,
        见模块 docstring);miss = 换抓点重试(状态词边回动作),超限
        fail 交外环。转场动画等待由 CwSelectProtagonist 确认节点的
        wait=2 承载,本 node 查询即转场后帧。不消费「按钮-返回备战
        界面」(放弃 = 主角未选 = 堵主线持续)。"""
        screen = self.last_screenshot
        back = self.round_by_find_area(screen, '货币战争-备战', A_PREP_BACK,
                                       crop_first=False).is_success
        aura_gone = not self.round_by_find_area(
            screen, _SCREEN, A_TITLE, crop_first=False).is_success
        if back and aura_gone:
            self._report_aura_slot()
            return self.round_success('已回备战(判效双锚过,交回主循环)',
                                      wait=2.0)
        self._verify_misses += 1
        if self._verify_misses > CwScreenAuraSelect.VERIFY_RETRY_MAX:
            return self.round_fail(
                f'光环确认未生效(判效双锚 miss,换抓点重试'
                f'>{CwScreenAuraSelect.VERIFY_RETRY_MAX}次耗尽交外环)')
        log.info('[cw-aura] 判效 miss(back=%s aura_gone=%s)重试 %s/%s',
                 back, aura_gone, self._verify_misses,
                 CwScreenAuraSelect.VERIFY_RETRY_MAX)
        return self.round_success(STATUS_VERIFY_MISS, wait=1.0)
