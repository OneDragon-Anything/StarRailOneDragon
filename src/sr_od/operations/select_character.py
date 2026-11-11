"""角色详情画面 → 打开角色列表 → 选中指定角色 → 收起列表的 operation。

角色养成系列 op 第二步(与负责人对齐的四步分工):第一步进详情画面
(:class:`sr_od.operations.goto_character_detail.GotoCharacterDetail`),
本步选中目标角色;切等级画面与升级动作由后续 op 承担。

交互行为(2026-11-07 实机):
- 详情页左下「按钮-角色列表」打开列表浮层(左半网格,右半详情保留);
- 点网格格 = 选中 + 右侧详情同步切换,列表保持打开;
- ⚠️ 列表打开时左下同位置按钮变为「筛选规则」入口,不可再点列表按钮;
- 点详情页「点击区-详情空白」收起列表,选中保留。

找角色 = 复用逐光捡金编队识别链
(:func:`sr_od.application.treasures_lightward.obs.tl_team_obs.read_character_cells_by_level`,
本屏已实测 20/20 置信命中):等级底标 OCR 锚定位 + 整页头像模板匹配 +
裁片兜底,格子直接带识别中文名——按名字找格,无需自己匹配头像。

滚动遍历 = 末日幻影编队选人(op apocalyptic_shadow/team_fill)的同款标定与判定:
- 页签名(可见格识别名集合)重复 = 到底;首见页重扫一轮(锚 OCR 单帧漏卡);
- 回顶 = 快拖惯性 + 页签钳制验证(不验证会停在半路,顶部目标永久漏扫);
- ⚠️ 拖距吸附档位与本机鼠标 DPI/速度相关(换机需重标),本屏行距 158px
  与 AS 编队屏(165px)不同,400px 实测档位需随实机行为复核。

起点 = 角色详情画面(列表开/关均可,本 op 自行处理);终点 = 详情画面·列表
已收起·当前角色 = 目标角色。不在详情画面时显式失败(前置导航归调用方编排)。
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.application.treasures_lightward.obs.tl_team_obs import (
    AnchorCell,
    read_character_cells_by_level,
)
from sr_od.config.character_const import CHARACTER_LIST
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:

    from sr_od.context.sr_context import SrContext

_DETAIL_SCREEN: str = '角色-详情'
_LIST_SCREEN: str = '角色-列表'

# ---------------------------------------------------------------------------
# 列表滚动(角色-列表浮层;标定来源与边界见模块 docstring):
# 向下翻页 = 慢拖无惯性(快拖触发惯性跳页,禁用);本屏行距实测 158px
# (首行 y≈187,行序 187/343/502/657/820),拖 400px ≈ 2.5 行 → 吸 2 行,
# 一屏可见 5 行时重叠 3 行,防边界行单页可见的漏扫(AS 实证教训)。
_SCROLL_FROM: Point = Point(300, 850)
_SCROLL_TO: Point = Point(300, 530)
_SCROLL_DURATION: float = 0.5
# 回顶 = 快拖惯性(单次 800px/0.3s 滚约 4+ 页,到顶自动钳住),3 连拖后
# 以页签钳制验证到位(不验证会停半路——AS 回顶实测教训)
_TOP_FROM: Point = Point(300, 200)
_TOP_TO: Point = Point(300, 1000)
_TOP_DURATION: float = 0.3
_TOP_DRAG_COUNT: int = 3

# 名字前的装饰符(OCR 实测:详情角色名带星级装饰,如「☆姬子·启行」),
# 清洗后才能与列表卡识别名(无装饰)对上
_NAME_DECOR_CHARS: str = '☆★✦✧'

# 翻页停滞:连续见到重复页签的轮数 ≥ 此值 = 到底(空识别帧不计)
_BOTTOM_STAGNATION_MAX: int = 4


def normalize_cn_name(name: str) -> str:
    """角色名归一:间隔号两式统一为「·」,清名字装饰符与空白
    (识别名/入参两侧统一口径;实测详情名带「☆」装饰,不清则匹配恒失败)。"""
    name = name.replace('•', '·').replace(' ', '').strip()
    for ch in _NAME_DECOR_CHARS:
        name = name.replace(ch, '')
    return name


class SelectCharacterOp(SrOperation):
    """在角色详情画面打开角色列表,选中指定角色,收起列表。

    终点状态:角色-详情画面·详情 TAB·列表已收起·当前角色 = 目标角色。
    """

    def __init__(self, ctx: SrContext, cn_name: str):
        """
        :param ctx: 上下文
        :param cn_name: 目标角色中文名(如「姬子•启行」,间隔号两式均可;
            变体角色必须给列表卡全名——「丹恒•腾荒」≠「丹恒」)
        """
        self.cn_name: str = normalize_cn_name(cn_name)
        if next((c for c in CHARACTER_LIST if normalize_cn_name(c.cn) == self.cn_name), None) is None:
            raise ValueError(f'未知角色名: {cn_name}')
        SrOperation.__init__(self, ctx, op_name=gt('选择角色') + '-' + self.cn_name)

        self._need_top: bool = True        #: 下一步需先回列表顶部
        self._seen_sigs: set[str] = set()  #: 已见页签集合(到底判定)
        self._last_page_sig: str = ''      #: 上一轮页签(首见页重扫判定)
        self._stagnation: int = 0          #: 页签重复轮数(到底计数)

    #------------------- 名字工具 -------------------#

    def _cell_names(self, cell: AnchorCell) -> list[str]:
        """格子可判名字列表(归一化后):置信名在前,候选名随后。"""
        names: list[str] = []
        if cell.guess.char:
            names.append(normalize_cn_name(cell.guess.char))
        for name, _score in cell.guess.candidates:
            names.append(normalize_cn_name(name))
        return names

    def _page_sig(self, cells: list[AnchorCell]) -> str:
        """当前页签名 = 可见格识别名集合(翻页/到底/回顶钳制判定)。"""
        return '|'.join(sorted(filter(None, (c.guess.char for c in cells))))

    def _read_detail_name(self) -> str | None:
        """读右侧详情的角色名(读区-角色名 area OCR),归一化后返回。

        列表开着时右侧详情实时反映选中角色——找人循环用它验证点击生效。"""
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(_DETAIL_SCREEN, '读区-角色名')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        if not results:
            return None
        name = normalize_cn_name(str(results[0].data or ''))
        return name or None

    def _name_matched(self, name: str | None) -> bool:
        """OCR 名与目标名匹配:归一化后全等优先;LCS 以目标为 source
        (LCS 占目标名长度的比——OCR 串的噪声字符不应摊薄这个比)。"""
        if not name:
            return False
        if name == self.cn_name:
            return True
        return str_utils.find_by_lcs(self.cn_name, name, percent=0.85)

    #------------------- 节点图 -------------------#

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """入口核对:列表已开 → 直接找人;详情页 → 快路径判当前角色;否则失败。

        快路径:列表关着时右侧详情名 = 当前角色,已是目标则跳过开列表
        (zero-click,连续养成同一角色时最常见)。"""
        screen = self.last_screenshot

        if self.round_by_find_area(screen, _LIST_SCREEN, '标题-角色列表').is_success:
            return self.round_success(status='AT_LIST')

        if (self.round_by_find_area(screen, _DETAIL_SCREEN, '标题-角色详情').is_success
                and self.round_by_find_area(screen, _DETAIL_SCREEN, '按钮-属性详情').is_success):
            if self._name_matched(self._read_detail_name()):
                return self.round_success(status='ALREADY_TARGET')
            return self.round_success(status='AT_DETAIL')

        return self.round_fail('不在角色详情画面(前置:运行 前往角色详情 op)')

    @node_from(from_name='入口核对', status='AT_DETAIL')
    @operation_node(name='打开列表', node_max_retry_times=6)
    def open_list(self) -> OperationRoundResult:
        """详情页点左下「按钮-角色列表」打开列表浮层。

        until=列表标题:打开动画期点击落空时重入轮重试;重入轮列表已开
        (上轮点击成功)则 until 先行命中直接通过。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _DETAIL_SCREEN, '按钮-角色列表',
            until_find_all=[(_LIST_SCREEN, '标题-角色列表')],
            pre_delay=0.5, success_wait=1.5, retry_wait=1.5,
        )

    @node_from(from_name='入口核对', status='AT_LIST')
    @node_from(from_name='入口核对', status='ALREADY_TARGET')
    @node_from(from_name='打开列表')
    @operation_node(name='寻找并选中', node_max_retry_times=60)
    def find_and_select(self) -> OperationRoundResult:
        """循环节点:读选中名 → 回顶守卫 → 本页找目标 → 重扫/翻页。

        每轮先读右侧详情名(列表开着时实时反映选中角色):命中 = 已选中,
        直接去收列表(点格生效的出口收敛在这里)。"""
        if self._name_matched(self._read_detail_name()):
            return self.round_success(status='SELECTED', wait=1)

        image = self.last_screenshot

        # 回顶守卫:列表滚动位置不定,先回顶再遍历(顶部目标漏扫 = AS 实证)
        if self._need_top:
            return self._return_to_top()

        cells = read_character_cells_by_level(self.ctx, image, screen_name=_LIST_SCREEN)
        if not cells:
            # 空识别帧(滚动余动/展开动画)不参与任何判定,原样重读
            return self.round_wait('列表识别未就绪,重读', wait=1.5)

        # 本页找目标:置信名或候选名归一化后精确匹配(变体角色全名)
        hit = next((c for c in cells if self.cn_name in self._cell_names(c)), None)
        if hit is not None:
            self.ctx.controller.click(hit.center, press_time=0.15)
            log.info('选人: 本页点击 %s (%d,%d)',
                     self.cn_name, int(hit.center.x), int(hit.center.y))
            return self.round_wait(f'点击 {self.cn_name},下轮读名验证', wait=1.5)

        # 首见页重扫一轮:「等级」锚 OCR 单帧会漏卡(AS 实证 16 格只读出 14),
        # 重扫 = 重掷一次识别,防止把目标页落在身后
        sig = self._page_sig(cells)
        if sig != self._last_page_sig:
            self._last_page_sig = sig
            return self.round_wait('本页重扫(锚漏卡重掷)', wait=1)

        # 停滞判定 + 翻页
        if sig in self._seen_sigs:
            self._stagnation += 1
        else:
            self._stagnation = 0
            self._seen_sigs.add(sig)
        if self._stagnation >= _BOTTOM_STAGNATION_MAX:
            return self.round_fail(f'列表翻到底未找到 {self.cn_name}')
        self._last_page_sig = ''
        self.ctx.controller.drag_to(_SCROLL_TO, start=_SCROLL_FROM, duration=_SCROLL_DURATION)
        return self.round_wait('向下翻页', wait=2)

    def _return_to_top(self) -> OperationRoundResult:
        """回顶并验证到位:连拖后扫页签,相邻两次相同 = 列表钳住不再滚动。

        空识别帧(滚动余动中)不算钳制,继续拖。到位后重置遍历状态。"""
        prev_sig = ''
        for _round in range(6):
            for _ in range(_TOP_DRAG_COUNT):
                self.ctx.controller.drag_to(_TOP_TO, start=_TOP_FROM, duration=_TOP_DURATION)
            time.sleep(1.2)
            self.screenshot()
            cells = read_character_cells_by_level(self.ctx, self.last_screenshot,
                                                  screen_name=_LIST_SCREEN)
            sig = self._page_sig(cells)
            if sig and sig == prev_sig:
                break
            prev_sig = sig
        self._need_top = False
        self._stagnation = 0
        self._seen_sigs = set()
        self._last_page_sig = ''
        return self.round_wait('已回列表顶部(钳制验证通过)', wait=1)

    @node_from(from_name='寻找并选中', status='SELECTED')
    @node_from(from_name='入口核对', status='ALREADY_TARGET')
    @operation_node(name='收起列表', node_max_retry_times=6)
    def close_list(self) -> OperationRoundResult:
        """点详情页「点击区-详情空白」收起列表(选中保留,实机验证)。

        until=列表标题消失:收起动画期点击落空时重入轮重试。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _DETAIL_SCREEN, '点击区-详情空白',
            until_not_find_all=[(_LIST_SCREEN, '标题-角色列表')],
            pre_delay=0.5, success_wait=1, retry_wait=1.5,
        )

    @node_from(from_name='收起列表')
    @operation_node(name='收尾验证', node_max_retry_times=8)
    def settle(self) -> OperationRoundResult:
        """终点验证:属性详情按钮(详情 TAB 激活锚) + 读名 = 目标名。

        不用标题「角色详情」作锚:变体角色(姬子•启行等)详情页立绘特效
        常驻横穿标题区,特效帧 OCR 读不出标题(实测);读名区在右侧面板,
        不受立绘特效影响。重试预算拉长到 8 轮:选人后立绘重渲染慢,
        短预算会在特效期耗尽(首轮实测 4 轮即失败,但选中已生效)。"""
        screen = self.last_screenshot
        if (self.round_by_find_area(screen, _DETAIL_SCREEN, '按钮-属性详情').is_success
                and self._name_matched(self._read_detail_name())):
            return self.round_success()
        return self.round_retry('收尾-等待画面', wait=2)
