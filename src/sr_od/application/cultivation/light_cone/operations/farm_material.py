"""缺料跳转刷取 operation(晋阶画面缺料 → 材料弹窗跳转副本 → 开拓力刷取)。

养成线 op 的材料补给侧(游戏跳转路径):起点 = 晋阶画面(光锥-等级提升,
调用方经 前往详情→选角色→切光锥→点强化 到达),从消耗材料栏实读缺料格,
经材料详情弹窗的游戏内「获取途径」跳转直达副本挑战画面,再委托
UseTrailblazePower(skip_transport=True) 完成选次数/配队/战斗——
导航真相源 = 游戏自己的跳转;静态表 MATERIAL_MISSIONS 只用于「该材料
有没有可刷副本」的预期校验与日志,不参与导航。

通用性(不同光锥/材料实测,样本 永恒之花/提纯以太/凝缩以太/永寿荣枝):
- 材料栏为固定 4 槽位(经验书+突破材料+信用点等),缺料判定用计数条
  颜色统计:「拥有数」不足时变红、「所需数」恒白(实机放大样本确认),
  红色主导像素达标即缺——OCR 不可用(红字漏读,实测全帧只读出白字
  「15」丢红字「0」);材料名在弹窗打开后 OCR 一次,仅用于静态表核对
  与日志;
- 弹窗途径行的 Y 随描述长度漂移(短描述行1 y≈632,长描述 y≈655),
  固定行位不可用——按静态表预期(类别主干+区域)OCR 定位带【区域】的
  行再点其中心;
- 静态表无可刷副本的材料(途径均为敌方掉落/合成类,如实机样本永寿荣枝)
  → 关弹窗显式失败,不盲跳。

前置:光锥-等级提升 晋阶画面(材料栏可见,列表未遮挡)。终点 =
UseTrailblazePower 战斗收尾状态。

⚠️ 真实资源消耗:times × mission.power 开拓力(花萼 10/虚影·余响 30/
隧洞 40),发起前必须向用户说明并获同意。全链实机验证见进度记录
(1 次花萼×10 实跑通过)。
"""

import time

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from one_dragon.utils.str_utils import find_best_match_by_difflib
from sr_od.challenge_mission.use_trailblaze_power import UseTrailblazePower
from sr_od.config.dungeon_drop_const import (
    MATERIAL_MISSIONS,
    find_missions_by_material,
)
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guide_def import GuideMission
from sr_od.operations.sr_operation import SrOperation

_ASCEND_SCREEN: str = '光锥-等级提升'
_POPUP_SCREEN: str = '材料-获取途径弹窗'
_CHALLENGE_SCREEN: str = '挑战副本'
_MATERIAL_CELL_COUNT: int = 4

#: 弹窗途径列表的 OCR 搜索区(x 固定;y 覆盖描述漂移后途径行可能出现的范围)
_POPUP_ROWS_RECT: Rect = Rect(793, 595, 1448, 790)

#: 缺料判定阈值:计数条暗带内红色主导像素数下限。实测「拥有数」红字
#: ≈52 px,充足格(白字/紫底)为 0(样本:惊魂夜 50 突破四格)
_LACKING_RED_PIXEL_MIN: int = 20
#: 计数条暗带 = 建档区底部的子带:距区底 [2, 24] px(文字行实测 y≈891-913)
_COUNT_STRIP_Y_FROM_BOTTOM: tuple[int, int] = (2, 24)

#: 弹窗途径列表的拖动重扫上限(来源多的材料预期行可能在视口下方)
_MAX_ROW_SCROLLS: int = 3
#: 列表内拖动:起点在下终点在上 = 内容上移露出下方行(不用滚轮,按负责人要求)
_ROW_DRAG_START: Point = Point(1120, 750)
_ROW_DRAG_END: Point = Point(1120, 620)

#: 类别名 → 弹窗行文案的类别主干(行文案不带「（赤）/（金）」后缀)
_CATEGORY_STEM: dict[str, str] = {
    '拟造花萼（赤）': '拟造花萼',
    '拟造花萼（金）': '拟造花萼',
}


class FarmMaterialOp(SrOperation):
    """把晋阶画面上第一个缺料材料跳转到副本并刷 times 次。

    结果状态:FARMED(刷取完成)/ NO_LACKING(材料栏无缺料,无需刷取)/
    MATERIAL_NO_DUNGEON(缺料材料无可刷副本,途径均为掉落/合成类)。

    ⚠️ times × mission.power 开拓力为真实消耗,调用方发起前须获用户同意。
    """

    def __init__(self, ctx: SrContext, times: int, team_num: int = 0,
                 support: str | None = None):
        """
        :param ctx: 上下文
        :param times: 计划挑战次数(>0;超过单次上限部分由 UseTrailblazePower
            按副本类型分批)
        :param team_num: 配队编号(0 = 游戏内当前配队)
        :param support: 支援角色 id,None = 不用
        """
        if times <= 0:
            raise ValueError(f'times 必须 > 0, 得到 {times}')
        self.times: int = times
        self.team_num: int = team_num
        self.support: str | None = support
        #: 扫描出的缺料格下标——坐标系 = 材料格-1..N 的建档序号(画面固定
        #: 槽位,生成期建档);取值时机 = 运行期扫描
        self.lacking_cell_idx: int | None = None
        #: 弹窗 OCR 出的材料名(核对静态表与日志用)
        self.material_name: str | None = None
        #: 解析出的目标关卡(委托 UseTrailblazePower 用)
        self.mission: GuideMission | None = None
        SrOperation.__init__(self, ctx, op_name=f'{gt("缺料跳转刷取")}×{times}',
                             node_max_retry_times=8)

    #------------------- 识别辅助 -------------------#

    def _cell_lacking(self, cell_idx: int) -> bool:
        """单格缺料判定:计数条暗带内「拥有数」红色主导像素达标。

        红色主导 = R 显著高于 G/B 且亮度足够(截图为 RGB 口径,双捕获
        路径均 BGRA2RGB);槽位紫底 B≥R、白字三通道相近,均不满足。
        途径同名判定无关本函数:所需数恒白,任何材料通用。"""
        area = self.ctx.screen_loader.get_area(_ASCEND_SCREEN, f'材料格-{cell_idx}')
        rect = area.rect
        strip = self.screenshot()[rect.y2 - _COUNT_STRIP_Y_FROM_BOTTOM[1]:
                                  rect.y2 - _COUNT_STRIP_Y_FROM_BOTTOM[0],
                                  rect.x1: rect.x2].astype(int)
        r, g, b = strip[:, :, 0], strip[:, :, 1], strip[:, :, 2]
        red_dominant = (r - b > 40) & (r - g > 40) & (r > 170)
        return int(red_dominant.sum()) >= _LACKING_RED_PIXEL_MIN

    def _scan_lacking_cell(self) -> int | None:
        """逐格检测,返回第一个缺料格下标;无缺料返回 None。"""
        for idx in range(1, _MATERIAL_CELL_COUNT + 1):
            if self._cell_lacking(idx):
                return idx
        return None

    def _read_popup_material_name(self) -> str | None:
        """弹窗标题材料名 OCR。"""
        area = self.ctx.screen_loader.get_area(_POPUP_SCREEN, '读区-材料名')
        screen = self.screenshot()
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        for r in results:
            text = str(r.data or '').strip()
            if text:
                return text
        return None

    @staticmethod
    def _match_expected_row(
            ocr_lines: list, missions: list[dict[str, str]]) -> tuple[object, dict[str, str]] | None:
        """在弹窗途径 OCR 行里定位静态表预期的副本行,返回 (命中行, 对应条目)。

        匹配口径:行文案同时含类别主干(「拟造花萼（赤）」→「拟造花萼」,
        其余类别取全名)与区域名;敌方掉落/合成类行不含【区域】自然落选
        (实机样本:永寿荣枝第一行=突破至均衡等级4后掉落,不可跳副本)。
        """
        for mission in missions:
            stem = _CATEGORY_STEM.get(mission['category'], mission['category'])
            for line in ocr_lines:
                text = str(line.data or '')
                if stem in text and mission['region'] in text:
                    return line, mission
        return None

    def _resolve_material_key(self, ocr_name: str) -> str | None:
        """OCR 材料名 → 静态表键:精确优先,OCR 误读时 difflib 模糊兜底。

        材料名是弹窗标题固定位置读出(实证 3 样本同位),但 OCR 可能误读
        单字导致精确查表落空——模糊匹配容忍单字误差,仍不中返回 None
        (表外材料或误读过甚,由调用方显式失败)。"""
        if ocr_name in MATERIAL_MISSIONS:
            return ocr_name
        idx = find_best_match_by_difflib(ocr_name, list(MATERIAL_MISSIONS.keys()))
        if idx is None:
            return None
        return list(MATERIAL_MISSIONS.keys())[idx]

    def _locate_and_click_expected_row(self, missions: list[dict[str, str]]) -> tuple[object, dict[str, str]] | None:
        """可见区定位预期途径行并点击;不可见则列表内拖动重扫(有界)。

        来源多的材料预期行可能在视口下方(弹窗内容区可滚动),每轮未命中
        拖动一次露出下方行;超过拖动上限仍未命中返回 None。拖动用
        controller.drag_to(负责人要求不用滚轮)。"""
        for scroll_round in range(_MAX_ROW_SCROLLS + 1):
            screen = self.screenshot()
            lines = self.ctx.ocr_service.get_ocr_result_list(
                image=screen, rect=_POPUP_ROWS_RECT, crop_first=False)
            matched = self._match_expected_row(lines, missions)
            if matched is not None:
                row, _ = matched
                log.info('途径行命中: %s', str(row.data))
                self.ctx.controller.click(row.center)
                return matched
            if scroll_round < _MAX_ROW_SCROLLS:
                self.ctx.controller.drag_to(_ROW_DRAG_END, start=_ROW_DRAG_START, duration=0.5)
                time.sleep(1)  # 拖动后列表滚动稳定
        return None

    #------------------- 节点图 -------------------#

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=3)
    def check_entry(self) -> OperationRoundResult:
        """入口核对:须在晋阶画面(材料栏可见)。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _ASCEND_SCREEN, '文本-可提升至').is_success:
            return self.round_success()
        return self.round_fail('不在光锥晋阶画面(前置:前往详情→选角色→切光锥→点强化)')

    @node_from(from_name='入口核对')
    @operation_node(name='扫描缺料格')
    def scan_lacking(self) -> OperationRoundResult:
        """逐格读「拥有/所需」,定位第一个缺料格。"""
        idx = self._scan_lacking_cell()
        if idx is None:
            return self.round_fail(status='NO_LACKING')
        self.lacking_cell_idx = idx
        return self.round_success()

    @node_from(from_name='扫描缺料格')
    @operation_node(name='打开材料弹窗')
    def open_popup(self) -> OperationRoundResult:
        """点缺料格打开材料详情弹窗(until=弹窗锚出现)。"""
        return self.round_by_find_and_click_area(
            self.last_screenshot, _ASCEND_SCREEN, f'材料格-{self.lacking_cell_idx}',
            until_find_all=[(_POPUP_SCREEN, '文本-获取途径')],
            pre_delay=0.5, success_wait=1, retry_wait=1.5)

    @node_from(from_name='打开材料弹窗')
    @operation_node(name='解析并跳转')
    def resolve_and_jump(self) -> OperationRoundResult:
        """弹窗定材料 → 静态表预期 → 定位副本途径行(必要时拖动重扫) → 点击跳转。"""
        self.material_name = self._read_popup_material_name()
        if not self.material_name:
            return self.round_fail('弹窗材料名 OCR 失败')
        material_key = self._resolve_material_key(self.material_name)
        if material_key is None:
            self._close_popup()
            return self.round_fail(
                f'{self.material_name}: 无法匹配已知材料(OCR 误读或静态表外材料)')
        missions = find_missions_by_material(material_key)
        if not missions:
            self._close_popup()
            return self.round_fail(
                status='MATERIAL_NO_DUNGEON',
                message=f'{material_key} 无可刷副本(途径均为敌方掉落/合成类)')
        matched = self._locate_and_click_expected_row(missions)
        if matched is None:
            self._close_popup()
            return self.round_fail(
                f'{material_key}: 弹窗内未找到预期副本途径 {missions}(含拖动重扫)')
        row, mission_entry = matched
        mission = self.ctx.guide_data.get_mission_by_guide_info(
            mission_entry['category'], mission_entry['mission'], mission_entry['region'])
        if mission is None:
            self._close_popup()
            return self.round_fail(
                f'指南数据无关卡 {mission_entry}(常量表与指南数据不同步,重跑生成器)')
        self.mission = mission
        log.info('跳转: %s → %s(%s)', material_key, mission.unique_id, str(row.data))
        return self.round_success('已点击途径行,落点核对交给下一节点')

    @node_from(from_name='解析并跳转')
    @operation_node(name='落点核对')
    def verify_landing(self) -> OperationRoundResult:
        """落点核对:跳转应直达挑战副本画面(未到则重试等待)。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _CHALLENGE_SCREEN, '挑战按钮').is_success:
            return self.round_success()
        return self.round_retry('未到挑战副本画面', wait=2)

    @node_from(from_name='落点核对')
    @operation_node(name='刷取材料')
    def farm(self) -> OperationRoundResult:
        """委托 UseTrailblazePower(免传送):选次数→配队→战斗收尾全复用。"""
        op = UseTrailblazePower(self.ctx, self.mission, self.team_num,
                                self.times, support=self.support,
                                skip_transport=True)
        return self.round_by_op_result(op.execute())

    #------------------- 非节点辅助 -------------------#

    def _close_popup(self) -> None:
        """关材料弹窗(失败路径收尾用;点不到不追)。"""
        area = self.ctx.screen_loader.get_area(_POPUP_SCREEN, '按钮-关闭')
        self.ctx.controller.click(area.rect.center)
