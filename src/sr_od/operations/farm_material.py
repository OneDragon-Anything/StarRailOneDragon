"""缺料跳转刷取 operation(晋阶画面缺料 → 材料弹窗跳转副本 → 开拓力刷取)。

养成线 op 的材料补给侧(游戏跳转路径):起点 = 晋阶画面(光锥-等级提升,
调用方经 前往详情→选角色→切光锥→点强化 到达),从消耗材料栏实读缺料格,
经材料详情弹窗的游戏内「获取途径」跳转直达副本挑战画面,再委托
UseTrailblazePower(skip_transport=True) 完成选次数/配队/战斗——
导航真相源 = 游戏自己的跳转;静态表 MATERIAL_MISSIONS 只用于「该材料
有没有可刷副本」的预期校验与日志,不参与导航。

通用性(不同光锥/材料实测,样本 永恒之花/提纯以太/凝缩以太/永寿荣枝):
- 材料栏为固定 4 槽位(经验书+突破材料+信用点等),缺料判定只比
  「拥有/所需」数字,与材料名无关;材料名在弹窗打开后 OCR 一次,
  仅用于静态表核对与日志;
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

import re

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.challenge_mission.use_trailblaze_power import UseTrailblazePower
from sr_od.config.dungeon_drop_const import find_missions_by_material
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guide_def import GuideMission
from sr_od.operations.sr_operation import SrOperation

_ASCEND_SCREEN: str = '光锥-等级提升'
_POPUP_SCREEN: str = '材料-获取途径弹窗'
_CHALLENGE_SCREEN: str = '挑战副本'
_MATERIAL_CELL_COUNT: int = 4

#: 弹窗途径列表的 OCR 搜索区(x 固定;y 覆盖描述漂移后途径行可能出现的范围)
_POPUP_ROWS_RECT: Rect = Rect(793, 595, 1448, 790)

_COUNT_RE = re.compile(r'(\d+)\s*/\s*(\d+)')

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

    def _read_cell_count(self, cell_idx: int) -> tuple[int, int] | None:
        """读材料格的「拥有/所需」;OCR 无计数文本(空格)返回 None。

        crop_first 关闭:格内计数文字小,裁剪后检测器易漏字(ocr_service
        已知语义),全帧 OCR + rect 过滤实测可靠。"""
        area = self.ctx.screen_loader.get_area(_ASCEND_SCREEN, f'材料格-{cell_idx}')
        screen = self.screenshot()
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=False)
        for r in results:
            m = _COUNT_RE.search(str(r.data or ''))
            if m:
                return int(m.group(1)), int(m.group(2))
        return None

    def _scan_lacking_cell(self) -> int | None:
        """逐格扫描,返回第一个缺料格(拥有 < 所需)的下标;无缺料返回 None。"""
        for idx in range(1, _MATERIAL_CELL_COUNT + 1):
            count = self._read_cell_count(idx)
            if count is None:
                continue
            owned, needed = count
            log.info('材料格-%d: 拥有 %d / 所需 %d', idx, owned, needed)
            if owned < needed:
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
    def _match_expected_row(ocr_lines: list, missions: list[dict[str, str]]) -> object | None:
        """在弹窗途径 OCR 行里定位静态表预期的副本行,返回命中的 OCR 行。

        匹配口径:行文案同时含类别主干(「拟造花萼（赤）」→「拟造花萼」,
        其余类别取全名)与区域名;敌方掉落/合成类行不含【区域】自然落选
        (实机样本:永寿荣枝第一行=突破至均衡等级4后掉落,不可跳副本)。
        """
        for mission in missions:
            stem = _CATEGORY_STEM.get(mission['category'], mission['category'])
            for line in ocr_lines:
                text = str(line.data or '')
                if stem in text and mission['region'] in text:
                    return line
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
        """弹窗定材料 → 静态表预期 → OCR 定位副本途径行 → 点击跳转。"""
        self.material_name = self._read_popup_material_name()
        if not self.material_name:
            return self.round_fail('弹窗材料名 OCR 失败')
        missions = find_missions_by_material(self.material_name)
        if not missions:
            self._close_popup()
            return self.round_fail(
                status='MATERIAL_NO_DUNGEON',
                message=f'{self.material_name} 无可刷副本(途径均为敌方掉落/合成类)')
        screen = self.screenshot()
        ocr_lines = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=_POPUP_ROWS_RECT, crop_first=False)
        row = self._match_expected_row(ocr_lines, missions)
        if row is None:
            self._close_popup()
            return self.round_fail(
                f'{self.material_name}: 弹窗内未找到预期副本途径 {missions}')
        mission = self.ctx.guide_data.get_mission_by_guide_info(
            missions[0]['category'], missions[0]['mission'], missions[0]['region'])
        if mission is None:
            self._close_popup()
            return self.round_fail(
                f'指南数据无关卡 {missions[0]}(常量表与指南数据不同步,重跑生成器)')
        self.mission = mission
        center = row.center
        log.info('跳转: %s → %s(%s)', self.material_name, mission.unique_id,
                 str(row.data))
        self.ctx.controller.click(center)
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
