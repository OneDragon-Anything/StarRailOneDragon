"""背包-遗器列表 → 按意图(部位+套装)筛选并选中目标件(强化选件导航 op)。

装备养成线的前置导航(补全 EquipRelicEnhanceOp 的「选件导航由调用方保证」
边界):从意图(部位 + 可选套装)到背包-遗器列表选中指定件。交互链:
部位筛选行点目标部位 →(提供套装时)筛选漏斗开面板 → 套装「点击选择」开
筛选规则弹窗 → 按套装类别切 tab → OCR 扫行找套装名点行文本中心勾选 →
确认 → 列表网格逐卡点选并核对 → 终点 = 背包-遗器且目标件选中(底部
强化/重掷按钮可点),后续接 EquipRelicEnhanceOp(本 op 不执行强化)。

实测行为与语义(实机摸底见进展目录 recon/bag-relic-screen.md):
- 部位筛选行为纯图标(无文本无模板),坐标点击;点后列表刷新无强转移锚,
  漏筛由选卡后的件名核对拦截;
- 筛选规则弹窗「确认」后弹窗与筛选面板同时收起、列表已按筛选刷新,漏斗
  出现「筛选中」角标;
- 筛选面板开着时点列表卡不刷新右侧详情 —— 必须走完确认链再选卡;
- 弹窗滚动列表后点击系统性偏移一行 —— 只点 OCR 行文本中心(命中即给坐标);
- 弹窗列表滚动拖拽按人工实机标定参数(rect 高度 80% 处起手、上滑 220px、
  0.5s;见模块尾常量出处),拖拽后以行文本签名变化判定滚动生效,连续空滚
  快速失败;
- 背包筛选状态跨屏持久(替换列表继承):进入时已有「筛选中」角标属历史态,
  本 op 不清除,历史筛选与本 op 意图叠加时由件名核对诚实失败暴露。

前置:背包-遗器(调用方从大世界打开背包并切遗器页签保证;入口画面级判定,
不符显式失败)。main_stat 参数暂不实现:主属性选择弹窗未实机摸底(无
fixture 帧与交互证据),传入显式失败,候实机补档后按弹窗建档接链。
"""

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.mys.sr_codes import RELIC_POS_CN
from sr_od.mys.sr_relic_sets import _SET_BY_NAME
from sr_od.operations.sr_operation import SrOperation

_BAG_SCREEN: str = '背包-遗器'
_FILTER_SCREEN: str = '背包-遗器-筛选'
_RULE_SCREEN: str = '背包-遗器-筛选规则'

# 网格几何:8 列 5 行,首列/首行中心相对列表区 rect 偏移 + 等间距
# (实机 2026-11-11 摸底实测列中心 210/330/…/1050、行中心 260/425/…/920;
# 列表区 rect 见 screen_info「区域-遗器列表」,坐标系 = 列表区 rect 内像素)
_GRID_COL_OFFSET: int = 65
_GRID_COL_GAP: int = 120
_GRID_ROW_OFFSET: int = 60
_GRID_ROW_GAP: int = 165
_GRID_COLS: int = 8
# 选卡尝试上限(前两行):套装+部位筛选后首行即应命中,预算兜底历史筛选叠加
_MAX_CARD_TRIES: int = 16
# 弹窗套装列表滚动屏数上限(隧洞 34 套/位面 28 套,每屏约 10 行,预算留余量)
_SCAN_MAX_DRAGS: int = 8
# 弹窗列表滚动拖拽参数(人工实机标定,凭据:进展目录 evidence/live-verify-T4-select-bag.md):
# 起点 = 列表区 rect 高度 80% 处(实机有效起点 y=650 ≈ rect[405,712] 的 80%),
# 手指上滑 220px、时长 0.5s,连击三次滚动成功;首版 300px/起点贴 rect 底缘
# (y=708,可视行末之下)实机空滚八屏列表纹丝未动 —— 起点落在滚动区边缓、
# 拖距过大均偏离有效标定。x 取 rect 水平中心(两列行间缝隙,无行按压风险)。
_DIALOG_DRAG_Y_ANCHOR: float = 0.8
_DIALOG_DRAG_PX: int = 220
_DIALOG_DRAG_DURATION: float = 0.5
# 滚动生效判定:拖拽后相邻两轮列表行文本签名不变连续达此值 → 判滚动失效
# (防静默空滚烧尽滚动预算;签名按轮 OCR 现读,滚动生效时首行必换)。
_STALE_SCROLL_LIMIT: int = 2


class SelectBagRelicOp(SrOperation):
    """在背包-遗器按部位(+可选套装)筛选并选中首个匹配件,终点 = 背包-遗器。

    结果状态:SELECTED(目标件已选中,详情件名与意图一致;无套装意图时以
    底部强化/重掷按钮出现为选中证据)。失败:入口非背包-遗器 / 套装名不在
    常量表 / 套装无该部位件 / 弹窗内扫完未找到套装 / 选卡预算内件名核对
    全不符。
    """

    def __init__(self, ctx: SrContext, pos: int,
                 set_name: str | None = None,
                 main_stat: str | None = None):
        """
        :param pos: 部位号 1-6(1=头部 2=手部 3=躯干 4=脚部 5=位面球
            6=连结绳,与 SrRelicPieceDef.pos 同坐标系)。
        :param set_name: 目标套装官方全名(常量表 RELIC_SETS 内;None = 不筛
            套装,选中该部位列表首件)。筛选后选卡以「套装+部位确定的单件名」
            核对,防误选。
        :param main_stat: 主词条偏好——暂未实现(主属性选择弹窗未实机摸底),
            传入显式失败,候实机补档。
        """
        if pos not in (1, 2, 3, 4, 5, 6):
            raise ValueError(f'部位 pos={pos} 超出 1-6')
        if main_stat is not None:
            raise ValueError('main_stat 选件暂未实现:主属性选择弹窗未实机摸底,'
                             '候实机补档后再接入')
        self.pos: int = pos
        self.set_name: str | None = set_name
        if set_name is None:
            self._piece_name: str | None = None  #: 选卡核对期望件名(set_name 派生)
        else:
            set_def = _SET_BY_NAME.get(set_name)
            if set_def is None:
                raise ValueError(f'套装名 {set_name} 不在常量表(RELIC_SETS)')
            piece = next((p for p in set_def.pieces if p.pos == pos), None)
            if piece is None:
                raise ValueError(f'套装 {set_name} 无部位 {pos}({RELIC_POS_CN[pos]})的件')
            self._piece_name = piece.name
        self._drags_left: int = _SCAN_MAX_DRAGS  #: 弹窗列表剩余滚动次数(scan_set_row 消耗)
        self._last_rows: tuple[str, ...] | None = None  #: 上一轮列表行文本签名(滚动生效判定)
        self._stale_scrolls: int = 0  #: 拖拽后列表签名不变的连续轮数(达 _STALE_SCROLL_LIMIT 判失效)
        self._card_idx: int = 0  #: 选卡游标(网格行优先展开的格序号,0 基)
        SrOperation.__init__(
            self, ctx,
            op_name=gt('背包遗器选件') + f'({self._piece_name or RELIC_POS_CN[pos]})',
            node_max_retry_times=20)

    def _card_center(self, idx: int) -> Point:
        """第 idx 格(行优先展开)中心:列表区 rect + 网格偏移常量(见模块头)。"""
        list_area = self.ctx.screen_loader.get_area(_BAG_SCREEN, '区域-遗器列表')
        x1, y1 = list_area.rect.x1, list_area.rect.y1
        col = idx % _GRID_COLS
        row = idx // _GRID_COLS
        return Point(x1 + _GRID_COL_OFFSET + _GRID_COL_GAP * col,
                     y1 + _GRID_ROW_OFFSET + _GRID_ROW_GAP * row)

    def _read_detail_name(self) -> str | None:
        """右侧详情件名读区 OCR(单行);空读 = 无选中件。"""
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(_BAG_SCREEN, '读区-遗器名')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        texts = [str(r.data).strip() for r in results if str(r.data).strip()]
        return texts[0] if texts else None

    def _name_matches(self, read: str | None) -> bool:
        """选中件名与期望核对(set_name 提供时 fuzzy 比对,否则视为通过)。"""
        if self._piece_name is None:
            return True
        if read is None:
            return False
        return str_utils.find_in_list_with_fuzzy(
            self._piece_name, [read], cutoff=0.6) is not None

    #------------------- 节点图 -------------------#

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """入口画面级判定:仅接受背包-遗器(其他背包页签/异常画面显式失败)。"""
        current = self.check_and_update_current_screen(
            self.last_screenshot, screen_name_list=[_BAG_SCREEN])
        if current != _BAG_SCREEN:
            return self.round_fail(f'不在背包-遗器(当前画面判定: {current};'
                                   f'前置:大世界打开背包并切「遗器」页签)')
        return self.round_success(status='ON_BAG')

    @node_from(from_name='入口核对', status='ON_BAG')
    @operation_node(name='部位筛选', node_max_retry_times=6)
    def apply_pos_filter(self) -> OperationRoundResult:
        """点部位筛选行目标部位(纯图标坐标点击,EquipRelicOp 遗器位同款)。

        列表刷新无强转移锚(图标选中态无模板),漏筛由选卡件名核对拦截。"""
        area_name = f'部位筛选-{RELIC_POS_CN[self.pos]}'
        slot = self.ctx.screen_loader.get_area(_BAG_SCREEN, area_name)
        if slot is None:
            return self.round_fail(f'部位 area 缺档:{area_name}')
        self.ctx.controller.click(slot.rect.center)
        return self.round_success(status='POS_SET', wait=1)

    @node_from(from_name='部位筛选')
    @node_from(from_name='部位筛选', status='POS_SET')
    @operation_node(name='打开筛选面板', node_max_retry_times=8)
    def open_filter_panel(self) -> OperationRoundResult:
        """点筛选漏斗开面板(纯坐标点击);面板锚出现即成功,重复点击有
        关面板风险,故先查锚再点。无套装意图时跳过直达选卡。"""
        if self.set_name is None:
            return self.round_success(status='NO_FILTER')
        if self.round_by_find_area(self.last_screenshot,
                                   _FILTER_SCREEN, '标识-筛选方案').is_success:
            return self.round_success(status='PANEL_OPEN')
        funnel = self.ctx.screen_loader.get_area(_BAG_SCREEN, '按钮-筛选漏斗')
        self.ctx.controller.click(funnel.rect.center)
        return self.round_retry('已点击筛选漏斗,等待面板打开', wait=1.5)

    @node_from(from_name='打开筛选面板', status='PANEL_OPEN')
    @operation_node(name='打开套装弹窗', node_max_retry_times=8)
    def open_set_dialog(self) -> OperationRoundResult:
        """点套装「点击选择」开筛选规则弹窗(条区坐标点击);弹窗标题为锚,
        先查锚再点(防已开时重复点击弹层)。"""
        if self.round_by_find_area(self.last_screenshot,
                                   _RULE_SCREEN, '标题-筛选规则').is_success:
            return self.round_success(status='DIALOG_OPEN')
        bar = self.ctx.screen_loader.get_area(_FILTER_SCREEN, '按钮-套装选择')
        self.ctx.controller.click(bar.rect.center)
        return self.round_retry('已点击套装选择,等待筛选规则弹窗', wait=1.5)

    @node_from(from_name='打开套装弹窗', status='DIALOG_OPEN')
    @operation_node(name='切套装类别', node_max_retry_times=6)
    def switch_set_tab(self) -> OperationRoundResult:
        """位面饰品套装先切「位面饰品」tab(弹窗默认开在隧洞遗器,实测帧;
        隧洞套装免切)。tab 选中态无文本差异,切换是否生效由扫描结果验证
        ——扫完未找到即诚实失败。"""
        set_def = _SET_BY_NAME[self.set_name]
        if set_def.kind != 'ornament':
            return self.round_success(status='TAB_OK')
        return self.round_by_find_and_click_area(
            self.last_screenshot, _RULE_SCREEN, 'TAB-位面饰品',
            pre_delay=0.5, success_wait=1, retry_wait=2,
        )

    @node_from(from_name='切套装类别', status='TAB_OK')
    @node_from(from_name='切套装类别')
    @operation_node(name='扫描并勾选套装', node_max_retry_times=20)
    def scan_and_check_set(self) -> OperationRoundResult:
        """OCR 扫弹窗套装列表找目标套装 → 点行文本中心勾选(命中即给坐标,
        实测坑:滚动后点击系统性偏移一行,只点行文本中心)。未找到滚动一屏
        重扫;拖拽后行文本签名连续不变 = 滚动失效,达上限诚实失败(防静默
        空滚烧尽预算)。"""
        screen = self.screenshot()
        list_area = self.ctx.screen_loader.get_area(_RULE_SCREEN, '区域-套装列表')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=list_area.pc_rect, crop_first=False)
        texts = [str(r.data) for r in results]
        idx = str_utils.find_in_list_with_fuzzy(self.set_name, texts, cutoff=0.6)
        if idx is not None:
            row = results[idx].rect
            center = Point((row.x1 + row.x2) // 2, (row.y1 + row.y2) // 2)
            self.ctx.controller.click(center)
            log.info('背包选件: 勾选套装 %s (行中心 %d,%d)',
                     self.set_name, center.x, center.y)
            return self.round_success(status='ROW_CLICKED', wait=0.8)
        signature = tuple(sorted(t for t in texts if t.strip()))
        if self._last_rows is not None and signature == self._last_rows:
            self._stale_scrolls += 1
            if self._stale_scrolls >= _STALE_SCROLL_LIMIT:
                return self.round_fail(
                    f'弹窗列表滚动失效(连续 {_STALE_SCROLL_LIMIT} 次拖拽后'
                    f'列表内容未变化,停在 {signature[0] if signature else "?"} 等行)')
        else:
            self._stale_scrolls = 0
        self._last_rows = signature
        if self._drags_left <= 0:
            return self.round_fail(
                f'筛选规则弹窗滚动 {_SCAN_MAX_DRAGS} 屏未找到套装 {self.set_name}')
        rect = list_area.rect
        start = Point(rect.x1 + (rect.x2 - rect.x1) / 2,
                      rect.y1 + (rect.y2 - rect.y1) * _DIALOG_DRAG_Y_ANCHOR)
        # 手指上滑 = 列表向深处翻页(标准触摸语义,拖拽不用滚轮)
        self.ctx.controller.drag_to(
            Point(start.x, start.y - _DIALOG_DRAG_PX), start,
            duration=_DIALOG_DRAG_DURATION)
        self._drags_left -= 1
        return self.round_retry(f'未找到 {self.set_name},滚动一屏重扫', wait=1)

    @node_from(from_name='扫描并勾选套装', status='ROW_CLICKED')
    @operation_node(name='确认筛选', node_max_retry_times=6)
    def confirm_filter(self) -> OperationRoundResult:
        """点「确认」提交筛选;until = 弹窗标题消失(实测:确认后弹窗与
        筛选面板同时收起、列表按筛选刷新)。面板开着点卡不刷新详情,故必须
        走完本节点再选卡。"""
        return self.round_by_find_and_click_area(
            self.last_screenshot, _RULE_SCREEN, '按钮-确认',
            until_not_find_all=[(_RULE_SCREEN, '标题-筛选规则')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='确认筛选')
    @node_from(from_name='打开筛选面板', status='NO_FILTER')
    @node_from(from_name='部位筛选', status='POS_SET')
    @node_from(from_name='核对选中件名', status='NEXT_CARD')
    @operation_node(name='选卡', node_max_retry_times=24)
    def select_card(self) -> OperationRoundResult:
        """点选当前格卡片,读名核对拆到「核对选中件名」的新轮:详情面板
        刷新滞后于点击,点后同轮零间隔读名会读到上一卡的名字 → 下一轮
        才命中目标名时实际选中高亮已是下一卡(错位静默选错件,下游强化
        消耗真实材料);CLICKED(wait=1.2) 留出刷新间隔,读名前画面已
        settle(同族 equip_relic.py「定位并选卡→验证选中」同款拆分)。
        无套装意图时以底部强化/重掷按钮出现为选中证据(按钮位互斥,按
        文本区分——满级件无强化入口)。"""
        if self._card_idx >= _MAX_CARD_TRIES:
            return self.round_fail(
                f'选卡 {_MAX_CARD_TRIES} 格件名核对全不符'
                + (f'(期望 {self._piece_name})' if self._piece_name else '(无套装意图)'))
        if self._piece_name is None:
            screen = self.last_screenshot
            has_enhance = self.round_by_find_area(screen, _BAG_SCREEN, '按钮-强化').is_success
            has_reroll = self.round_by_find_area(screen, _BAG_SCREEN, '按钮-重掷').is_success
            if has_enhance or has_reroll:
                return self.round_success(status='SELECTED', wait=0.5)
            self._card_idx += 1
            return self.round_retry('底部无强化/重掷按钮(未有选中件),点下一格', wait=1)
        self.ctx.controller.click(self._card_center(self._card_idx))
        self._card_idx += 1
        return self.round_success(status='CLICKED', wait=1.2)

    @node_from(from_name='选卡', status='CLICKED')
    @operation_node(name='核对选中件名', node_max_retry_times=24)
    def verify_selected(self) -> OperationRoundResult:
        """新轮(画面已 settle)读详情件名与期望核对;不符推进下一格。
        预算语义不变:每格一次核对,格数上限 = _MAX_CARD_TRIES,耗尽
        诚实失败。"""
        read = self._read_detail_name()
        if self._name_matches(read):
            log.info('背包选件: 第 %d 格选中 %s', self._card_idx, read)
            return self.round_success(status='SELECTED', wait=0.5)
        return self.round_success(status='NEXT_CARD', wait=1)
