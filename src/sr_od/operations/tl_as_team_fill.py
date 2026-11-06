"""末日幻影编队选人:清空编队 + 按目标填 8/12 人(落位回验/整页批量驱动)。

模式从死循环排查沉淀(详见各节点注释):锚驱动列表识别 / 跳过已落位目标
(**点击已在编队中的角色 = 将其移除**) / 页签名集合到底判定 / 星启整页
批量点卡(不逐人回验,点击位置由识别给出)。

起点 = 末日幻影-编队屏;终点 = 编队屏(已填满)。
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils, os_utils
from one_dragon.utils.log_utils import log
from sr_od.application.treasures_lightward.obs.tl_team_obs import (
    AnchorCell,
    read_character_cells_by_level,
    read_team_nodes,
)
from sr_od.config.character_const import CHARACTER_LIST
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:

    from sr_od.context.sr_context import SrContext

_TEAM_SCREEN: str = '末日幻影-编队'

#: 角色列表滚动拖动(向下翻页)。**本机实测**:列表滚动带按行吸附,拖距与
#: 位移非线性——拖 320px 实测滚 1 行(相邻页重叠 3 行),拖 400px 滚 2 行
#: (重叠 1 行)。重叠 2 行以上才防漏扫:可视区首尾各有一行裁切盲区,重叠
#: 不足时边界行只在单页完整可见,识别失败即永久漏扫(星启找波提欧实证:
#: 400px 翻页跳行丢卡,遍历 4 屏页签无它)。取 320px = 重叠 3 行(人类老莫
#: 定案:重叠 2 行就够,取档留余量);吸附机制天然吸收 DPI 漂移。
#: 慢拖 0.5s 无惯性过冲(快拖触发惯性跳页,禁用)。
#: ⚠️ 吸附档位与本机鼠标 DPI/速度相关,换机需重标。
_SCROLL_FROM: Point = Point(300, 850)
_SCROLL_TO: Point = Point(300, 530)
_SCROLL_DURATION: float = 0.5

#: 回顶拖动(手指自上而下;单次 800px/0.3s 快拖 = 惯性滚动约 4+ 页,
#: 列表到顶自动钳住,连拉 3 次任何起点都到顶)
_TOP_FROM: Point = Point(300, 200)
_TOP_TO: Point = Point(300, 1000)
_TOP_DURATION: float = 0.3
_TOP_DRAG_COUNT: int = 3

#: 编队行槽位 1 点击点(展开列表 + 选中该行;放大标定实测填充态头像圆心——
#: 空槽菱形与填充头像同位,行 1 (1025,396) / 行 2 (1025,678))
_ROW_SLOT_POINTS: dict[int, Point] = {
    1: Point(1025, 396),
    2: Point(1025, 678),
}

#: 全部槽位点击点(清空用,行内左→右;圆心距约 82px)
_SLOT_POINTS: list[list[Point]] = [
    [Point(1025, 396), Point(1108, 396), Point(1190, 396), Point(1273, 396)],
    [Point(1025, 678), Point(1108, 678), Point(1190, 678), Point(1273, 678)],
]

# --------------------------------------------------------------------------
# 星启(难度04,三节点)布局:交互坐标已建档进 screen_info「末日幻影-编队」
# (area 名 04- 前缀:04-行N槽位1 / 04-增益入口-行N / 04-垃圾桶 / 04-星启模式
# 标签 id_mark),坐标单一真相源在 screen_info,op 经 area 中心点击。
# 交互语义实测结论(写这些分支的依据):
# - 行槽位剪影点击(收起态) = 展开选人列表 + 选中该行;展开态点当前选中行
#   已入队槽位 = 移除角色;点他行槽位 = 仅收起列表;
# - 列表卡点击语义:未入队角色的卡 = 加入当前选中行首个空槽;**已入队角色
#   的卡 = 把该角色移出队伍**(加/移开关,非无效点击)——重复点同一张卡会
#   反复加/移,找卡与点卡重试都必须避开带标记的卡;
# - 行尾「+」按钮 = 该行终焉公理弹窗入口(编入角色前后形态一致);
# - 顶部垃圾桶一键清空全部三行+增益;右上箭头在 04 = 关闭编队屏(不可当收起);
# - 槽位像素判空在 04 布局不可用(V/特征数/模板三方案实测无区分度),列表卡
#   「队伍N」标记只用于找卡排除已入队卡(标记框中心实测落在本卡头像区
#   锚推导 90x95 矩形内,与邻卡矩形不重叠;点已入队卡 = 移出)。清空 =
#   选人前无条件按一次顶部「清空编队」按钮(2026-11-06 定案),不做标记
#   计数判定;点卡不做逐人落位回验(点击位置由识别给出,点对即落位)。
#   标记长在列表卡上,收起或翻页后不可见——按页计数曾致假「已空」与点对
#   也判失败的重试死循环,禁用。
# --------------------------------------------------------------------------
_ARC_ROW_SLOT_AREAS: dict[int, str] = {
    1: '04-行1槽位1',
    2: '04-行2槽位1',
    3: '04-行3槽位1',
}

_ARC_TRASH_AREA: str = '04-垃圾桶'

#: 遍历取证截图目录(.debug 已 gitignore;每次填充运行覆盖式新建序号文件)。
_DIAG_SHOT_DIR: Path = Path(os_utils.get_work_dir()) / '.debug' / 'temp' / 'as_fill_diag'


class TlAsTeamFillOp(SrOperation):
    """编队选人:清空两行 + 按目标填 8 人。起点 = 末日幻影-编队屏。"""

    def __init__(self, ctx: SrContext, team_names: list[str]):
        SrOperation.__init__(self, ctx, op_name='末日幻影 编队选人')
        if len(team_names) not in (8, 12):
            raise ValueError(f'末日幻影需 8 人(双节点)或 12 人(星启三节点): {len(team_names)}')
        if len(set(team_names)) != len(team_names):
            raise ValueError(f'末日幻影角色须互不相同: {team_names}')
        per_row = 4
        self._arc_mode: bool = len(team_names) == 12  #: 星启三节点布局(坐标/清空/回验分派)
        self.teams: list[list[str]] = [
            team_names[i:i + per_row]
            for i in range(0, len(team_names), per_row)
        ]
        for names in self.teams:
            for name in names:
                if next((c for c in CHARACTER_LIST if c.cn == name), None) is None:
                    raise ValueError(f'未知角色名: {name}')
        self._row_idx: int = 0            #: 当前填充的行(0 基)
        self._char_idx: int = 0           #: 当前行填到第几个(0 基)
        self._row_selected: bool = False  #: 目标行已选中(点卡前置守卫)
        self._awaiting_expand: bool = False  #: 已点槽位等待列表展开复验
        self._need_top: bool = True       #: 下一步需先滚回列表顶部
        self._down_stagnation: int = 0    #: 向下翻页停滞计数
        self._seen_sigs: set[str] = set() #: 本次搜索已见页签集合(到底判定)
        self._last_seek_sig: str = ''     #: 上一轮扫描页签名(新页首帧判定)
        # 当前页的扫描帧缓存(每页最多留 3 帧;坐标系 = 全图 1080p;
        # 写入时机 = 每轮扫描入栈,翻页/回顶/换行清空)
        self._page_frames: list[list[AnchorCell]] = []
        self._clear_slot: tuple[int, int] | None = None  #: 清空游标(行 0 基,槽 0 基)
        self._shot_seq: int = 0          #: 遍历取证截图序号(运行内递增)
        self._arc_cleared: bool = False  #: 星启清空已验证(列表卡无「队伍N」标记)

    def _diag_shot(self, tag: str) -> None:
        """每轮列表扫描落一张当前帧(逐页截图,人类老莫指定遍历取证)。

        为什么:页签日志只有识别名集合,「目标找不到」时无法区分
        「列表没遍历到那页」与「该页识别漏卡」;逐页截图把每一页真实
        画面留档,与页签对账即可定位漏识别/漏遍历。"""
        self._shot_seq += 1
        safe_tag = re.sub(r'[\\/:*?"<>|]', '_', tag)
        path = _DIAG_SHOT_DIR / f'{self._shot_seq:03d}_{safe_tag}.png'
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2_utils.save_image(self.last_screenshot, path)
        log.info('AS遍历截图: %s', path.name)

    @operation_node(name='清空编队', is_start_node=True, node_max_retry_times=24)
    def _clear_teams(self) -> OperationRoundResult:
        """确认在编队屏并清空两行(点已入队槽位逐个移除)。

        AS 垃圾桶无清空功能;移除语义依赖列表展开态(见模块 docstring),
        本节点按实读行成员驱动,每轮点一个目标槽位,由回验收敛。"""
        screen = self.last_screenshot
        if not (self.round_by_find_area(screen, _TEAM_SCREEN, '标题-末日幻影行').is_success
                and self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success):
            return self.round_fail('不在末日幻影编队屏(前置:选关点前往挑战)')
        if self._arc_mode:
            # 星启:选人前无条件按一次「清空编队」按钮(一键全清,人类老莫
            # 2026-11-06 定案:不做标记计数判定,按完即走)
            self._click_area_center(_TEAM_SCREEN, _ARC_TRASH_AREA)
            return self.round_success('已按清空编队', wait=2)
        nodes = read_team_nodes(self.ctx, screen, screen_name=_TEAM_SCREEN)
        if not nodes:
            # 锚未读到 = 降级空列表,不等于编队已空(弹窗遮挡锚行会走到这);
            # 误判已空会跳过清队,行满导致填充死循环
            return self.round_retry('节点锚未读到(画面遮挡?),重读', wait=1.5)
        list_open = self.round_by_find_area(
            screen, _TEAM_SCREEN, '列表-角色列表页签').is_success

        # 找第一个有成员的槽位(行 0 基、槽 0 基)
        target: tuple[int, int] | None = None
        for r, node in enumerate(nodes):
            for s, member in enumerate(node.members):
                if member.char or member.candidates:
                    target = (r, s)
                    break
            if target is not None:
                break
        if target is None:
            return self.round_success('编队已空', wait=1)

        r, s = target
        point = _SLOT_POINTS[r][s]
        self.ctx.controller.click(point, press_time=0.15)
        log.info('AS清空: 点行%d槽%d (列表展开=%s)', r + 1, s + 1, list_open)
        # 展开态且该行为选中行 = 移除;否则本点击只做展开/收起,下一轮实读继续
        return self.round_wait(f'点行{r + 1}槽{s + 1}', wait=1.2)

    @node_from(from_name='清空编队')
    @operation_node(name='填充循环', node_max_retry_times=160)
    def _fill_loop(self) -> OperationRoundResult:
        """逐行填充:行选中守卫 → 星启整页批量点卡 / 双节点逐人找卡。

        星启 = 每次识别把当前行剩余目标在本页可见的连续前缀段一次点完
        (0.5s/次),点完回顶继续,不做逐人落位回验(点击位置由识别给出,
        点对即落位);带标记的卡绝不点。双节点 = 行成员名字匹配回验 +
        逐人找卡(实机验证过的路径)。行选中守卫:收起态点目标行槽位 =
        展开+选中;跨行切换点下一行槽位(清空后槽位全空无移除风险)。"""
        image = self.last_screenshot
        if self._row_idx >= len(self.teams):
            return self.round_success('填充完成', wait=1)

        # 难度布局防御:锚行数与队伍数不符 = 编队屏难度与目标不符(01-03 双行 /
        # 星启 04 三行),显式失败提示选对难度。
        nodes_probe = read_team_nodes(self.ctx, image, screen_name=_TEAM_SCREEN)
        if not nodes_probe:
            return self.round_retry('节点锚未读到(画面遮挡?),重读', wait=1.5)
        if len(nodes_probe) != len(self.teams):
            return self.round_fail(
                f'编队屏节点数 {len(nodes_probe)} 与队伍数 {len(self.teams)} 不符:'
                f'请让选关屏选中的难度与目标角色数匹配(8 人=01-03,12 人=星启)')

        row_no = self._row_idx + 1
        if self._char_idx >= len(self.teams[self._row_idx]):
            # 批量点卡一轮可能点完整行,游标越界 = 行完成待推进
            # (星启;双节点逐人推进不会越界,守卫对两者都安全)
            return self._advance_row(row_no)
        target = self.teams[self._row_idx][self._char_idx]
        row_slot_point = self._row_slot_point(row_no)

        # 列表展开态判定用「角色列表」页签(展开态独有锚;锚文本须与收起态同
        # 区域的「首领攻略」零公共子序列,短锚「等级」与其 LCS 达 0.5 会假命中):
        # 角色卡识别(read_character_cells_by_level)在展开动画帧会整帧空识别,
        # 据此判收起态会误点收起箭头(该坐标在收起态 = 关闭编队屏),流程发散。
        list_open = self.round_by_find_area(
            image, _TEAM_SCREEN, '列表-角色列表页签').is_success

        # 行选中守卫(星启简化版):清空后全部槽位为空,点任何行槽位都无移除
        # 风险,统一「点目标行槽位 → 复验展开」收敛:
        # 收起态点 = 展开+选中;展开态且目标行=选中行 = 空槽无操作(选中已正确);
        # 展开态且目标行≠选中行 = 收起列表,下轮再点 = 展开+选中。
        # (双节点版本保留原三步守卫:展开态收起走右上箭头,该语义已实机验证。)
        if not self._row_selected:
            if self._awaiting_expand:
                if list_open:
                    self._row_selected = True
                    self._need_top = True
                    self._awaiting_expand = False
                    return self.round_wait(f'行 {row_no} 展开复验通过', wait=0.5)
                self.ctx.controller.click(row_slot_point, press_time=0.15)
                return self.round_wait(f'选中行 {row_no}(重试)', wait=1.5)
            self.ctx.controller.click(row_slot_point, press_time=0.15)
            self._awaiting_expand = True
            return self.round_wait(f'选中行 {row_no}(待展开复验)', wait=1.5)

        # 星启回验与找卡都依赖列表展开(「队伍N」标记在列表卡上,收起态列表
        # 不可见 → 标记恒 0、找卡空识别,双向死循环)——收起态先点目标行槽位
        # 展开(收起态语义 = 展开+选中,不移除角色)。
        if self._arc_mode and not list_open:
            self.ctx.controller.click(row_slot_point, press_time=0.15)
            return self.round_wait('展开列表(回验/找卡前置)', wait=1.5)

        # 清空防线(星启):垃圾桶点击无到达验证(点了无弹窗、槽位判空在此布局
        # 不可用),清空失败会带着残留编队填充——已入队卡的找卡排除会让目标
        # 「找不到」死路。用列表卡「队伍N」标记计数验证:标记 >0 = 未清空,
        # 重按垃圾桶直至列表无标记(见 _team_tag_boxes 的标记识别区)。
        if self._arc_mode and not self._arc_cleared:
            tags = self._team_tag_boxes(image)
            if tags:
                self._click_area_center(_TEAM_SCREEN, _ARC_TRASH_AREA)
                return self.round_retry(
                    f'编队未清空(列表仍有{len(tags)}个队伍标记),重按垃圾桶', wait=2)
            self._arc_cleared = True
            return self.round_wait('清空验证通过(列表无队伍标记)', wait=0.5)

        # 找卡:星启 = 整页批量(见 _arc_fill_round);双节点 = 逐人找卡。
        cells = read_character_cells_by_level(self.ctx, image)
        self._diag_shot(
            f'行{row_no}找{target}_stagnation{self._down_stagnation}')
        if self._arc_mode:
            return self._arc_fill_round(image, cells, row_no)

        nodes = read_team_nodes(self.ctx, image, screen_name=_TEAM_SCREEN)
        if not nodes:
            # 锚未读到的降级空列表不可当「成员为空」用(会误判落位失败死循环点卡)
            return self.round_retry('落位回验锚未读到,重读', wait=1.5)
        row_members = nodes[row_no - 1].members if len(nodes) >= row_no else []
        members_dbg = [f'{m.char or "?"}[{"|".join(n for n, _ in m.candidates)}]'
                       for m in row_members]
        log.info('AS填充回验: 行%d 成员=%s 目标=%s', row_no, members_dbg, target)
        if self._member_has(row_members, target):
            log.info('AS填充: 行%d %s 已落位', row_no, target)
            return self._advance_after_hit(target, row_no)
        return self._seek_and_click(cells, target, row_no)

    def _seek_and_click(self, cells: list[AnchorCell], target: str,
                        row_no: int) -> OperationRoundResult:
        """双节点找卡:回顶守卫 → 当前页找目标 → 点卡 → 无匹配翻页。"""
        if self._need_top:
            return self._return_to_top()

        # 名字精确匹配:变体卡(丹恒•腾荒/姬子•启行)是独立角色,前缀/分隔符
        # 模糊匹配会把不同角色误当目标——队伍名必须给列表卡的全名。
        hit: AnchorCell | None = None
        for cell in cells:
            if target in self._cell_names(cell):
                hit = cell
                break
        if hit is not None:
            self.ctx.controller.click(hit.center, press_time=0.15)
            log.info('AS填充: 行%d 点 %s', row_no, target)
            return self.round_wait(f'点击 {target}', wait=1)
        return self._page_down(cells, target, row_no)

    def _return_to_top(self) -> OperationRoundResult:
        """回顶并**验证到位**:循环「拖→扫页签」直到页签钳住不变。

        为什么必须验证:3 连快拖的惯性量随列表位置/内容高度浮动,
        「固定 3 拖不验证」实测有时停中部有时到顶——不到顶就开遍历,
        顶部带目标(最近使用序的编队成员)永久扫不到(海瑟音实证)。
        到顶判据 = 相邻两次扫描页签相同(列表钳住不再滚动);
        空识别帧(余动中)不算钳制,继续拖。"""
        prev_sig = ''
        for _round in range(6):
            for _ in range(_TOP_DRAG_COUNT):
                self.ctx.controller.drag_to(
                    _TOP_TO, start=_TOP_FROM, duration=_TOP_DURATION)
            time.sleep(1.2)
            self.screenshot()
            sig = self._scan_page_sig()
            if sig and sig == prev_sig:
                break
            prev_sig = sig
        self._need_top = False
        self._down_stagnation = 0
        self._seen_sigs = set()
        self._last_seek_sig = ''
        return self.round_wait('回列表顶部(已验证)', wait=1)

    def _scan_page_sig(self) -> str:
        """同步截图并返回当前页签名(回顶钳制判定用)。"""
        cells = read_character_cells_by_level(self.ctx, self.last_screenshot)
        return self._page_sig(cells)

    def _page_down(self, cells: list[AnchorCell], target: str,
                   row_no: int) -> OperationRoundResult:
        """当前页无目标:页签停滞判定 + 向下翻页(同页 4 次 = 到底 = fail)。"""
        sig = self._page_sig(cells)
        if not sig:
            # 空识别帧(滚动未停/展开动画)不参与停滞计数——快回顶后的首帧
            # 常撞滚动余动,烧光停滞预算会把「没读完」误判成「到底」
            return self.round_wait('列表识别未就绪,不计停滞', wait=1.5)
        log.info('AS填充诊断: 找 %s 行%d stagnation=%d 页签=%s',
                 target, row_no, self._down_stagnation, sig[:80])
        if sig in self._seen_sigs:
            self._down_stagnation += 1
        else:
            self._down_stagnation = 0
            self._seen_sigs.add(sig)
        if self._down_stagnation >= 4:
            return self.round_fail(f'列表到底未找到 {target}')
        # 本机标定:慢拖 400px/0.5s = 精准 3 行无过冲(见 _SCROLL_* 常量注释);
        # 落定即识别清晰,wait 2s 留渲染余量
        self._last_seek_sig = ''
        self.ctx.controller.drag_to(
            _SCROLL_TO, start=_SCROLL_FROM, duration=_SCROLL_DURATION)
        return self.round_wait('向下翻页', wait=2)

    @staticmethod
    def _page_sig(cells: list) -> str:
        """当前页签名(可见格识别名集合,用于翻页/到顶判定)。

        cells 元素为带 .guess 的识别单元(AnchorCell 鸭子兼容)。"""
        return '|'.join(sorted(
            filter(None, (
                c.guess.char or (c.guess.candidates[0][0] if c.guess.candidates else '')
                for c in cells
            ))
        ))

    def _advance_after_hit(self, target: str, row_no: int) -> OperationRoundResult:
        """落位推进游标(仅双节点):行内下一角色 → 跨行(点右上收起箭头)
        → 全部完成。星启走 _arc_fill_round 的批量推进,不经此方法。"""
        self._char_idx += 1
        self._need_top = True
        if self._char_idx >= 4:
            self._char_idx = 0
            self._row_idx += 1
            self._row_selected = False
            if self._row_idx < len(self.teams):
                self.ctx.controller.click(Point(1862, 68), press_time=0.15)
                return self.round_wait(f'行 {row_no} 填充完成,切下一行', wait=1.2)
            return self.round_success('填充完成', wait=1)
        return self.round_wait(f'{target} 已落位', wait=0.8)

    def _row_slot_point(self, row_no: int) -> Point:
        """行槽位 1 点击点:从 screen_info area 读中心(坐标单一真相源;
        星启 = 04-行N槽位1,双节点 = 01-03 布局 area「槽位N头像-1」的
        等效点击位按历史标定暂留常量,偿清归 op 硬编码清理批)。"""
        if self._arc_mode:
            return self._arc_area_center(_ARC_ROW_SLOT_AREAS[row_no])
        return _ROW_SLOT_POINTS[row_no]

    def _arc_area_center(self, area_name: str) -> Point:
        """星启交互点坐标从 screen_info area 读 rect 中心(单一真相源)。"""
        rect = self.ctx.screen_loader.get_area(_TEAM_SCREEN, area_name).rect
        return Point((rect.x1 + rect.x2) // 2, (rect.y1 + rect.y2) // 2)

    def _click_area_center(self, screen_name: str, area_name: str) -> None:
        """按建档 rect 中心点击(纯定位区;坐标单一真相源在 screen_info)。"""
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        rect = area.rect
        self.ctx.controller.click(
            Point((rect.x1 + rect.x2) // 2, (rect.y1 + rect.y2) // 2), press_time=0.15)

    #: 「队伍N」标记匹配:须「队伍」紧跟数字(双保险第二道)。
    _TEAM_TAG_PAT: ClassVar[re.Pattern] = re.compile(r'^队伍\s*\d')

    #: 「队伍N」标记识别区 = 列表展开态的角色卡区(x 40-600 / y 190-970)。
    #: 限定区域是第一道防线:顶部横幅「队伍发生变动…」(右侧节点卡区)与
    #: boss 卡区文字天然排除在裁片外;数字后缀正则为第二道。
    _TEAM_TAG_ZONE: ClassVar[tuple[int, int, int, int]] = (40, 190, 600, 970)

    def _team_tag_boxes(self, image) -> list[Point]:
        """列表卡区内全部「队伍N」标记框中心(全图坐标;裁片结果加区域偏移)。"""
        x1, y1, x2, y2 = self._TEAM_TAG_ZONE
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=image[y1:y2, x1:x2])
        return [
            Point(x1 + r.x + r.w / 2, y1 + r.y + r.h / 2)
            for r in results if self._TEAM_TAG_PAT.match((r.data or '').strip())
        ]

    @staticmethod
    def _point_in_rect(p: Point, rect: Rect) -> bool:
        """点是否在矩形内(闭边界)。"""
        return rect.x1 <= p.x <= rect.x2 and rect.y1 <= p.y <= rect.y2

    @staticmethod
    def _merge_cells(frames: list[list[AnchorCell]]) -> list[AnchorCell]:
        """同页多帧格子并集:「等级」锚 OCR 单帧随机漏卡(16 格单帧实测可只
        读出 14),帧间漏的格子不同,并集近似全量。位置近重合(±12px)视为
        同一格,无结论格被后续有结论帧覆盖。"""
        merged: list[AnchorCell] = []
        for frame in frames:
            for cell in frame:
                hit = next((m for m in merged
                            if abs(m.center.x - cell.center.x) <= 12
                            and abs(m.center.y - cell.center.y) <= 12), None)
                if hit is None:
                    merged.append(cell)
                elif hit.guess.char is None and cell.guess.char is not None:
                    merged[merged.index(hit)] = cell
        return merged

    def _arc_fill_round(self, image, cells: list[AnchorCell],
                        row_no: int) -> OperationRoundResult:
        """星启整页批量填人单轮(人类老莫 2026-11-06 定案:不逐人回验)。

        每次识别把当前行剩余目标中「本页可见的连续前缀段」按队伍顺序一次
        点完(0.5s/人),点完回顶继续——点击位置由识别给出,点对即落位。
        顺序必须严格跟随队伍序:列表卡点击落进当前选中行首个空槽,跳名
        点击会把人落进前面目标的槽位错位。带标记的卡绝不点击:列表卡点击
        是加/移开关,点已入队角色的卡会把人移出队伍;队首目标只剩带标记
        命中 = 已入队(重复生效的点击),跳过游标不点。"""
        tag_centers = self._team_tag_boxes(image)

        def badged(cell: AnchorCell) -> bool:
            return cell.rect is not None and any(
                self._point_in_rect(p, cell.rect) for p in tag_centers)

        def find_cell(name: str) -> list[AnchorCell]:
            """该名字在本页的全部命中(置信命中排前)。"""
            hits = [c for c in cells if name in self._cell_names(c)]
            hits.sort(key=lambda c: c.guess.char != name)
            return hits

        # ① 搜索前置:回列表顶部(固定快速大幅上拖,见 _return_to_top)
        if self._need_top:
            return self._return_to_top()

        # ② 队首目标只剩带标记命中 = 已入队,跳过游标不点(点 = 移出)
        row_targets = self.teams[self._row_idx]
        while self._char_idx < len(row_targets):
            head_hits = find_cell(row_targets[self._char_idx])
            if not head_hits or not all(badged(c) for c in head_hits):
                break
            log.info('AS星启填充: 行%d %s 已带标记,跳过', row_no,
                     row_targets[self._char_idx])
            self._char_idx += 1

        # ③ 行完成 → 切下一行 / 全部完成
        if self._char_idx >= len(row_targets):
            return self._advance_row(row_no)

        # ④ 本页连续前缀段批量点卡(严格按队伍顺序)
        batch: list[AnchorCell] = []
        for name in row_targets[self._char_idx:]:
            hits = [c for c in find_cell(name) if not badged(c)]
            if not hits:
                break
            batch.append(hits[0])
        if batch:
            clicked: list[str] = []
            for cell in batch:
                self.ctx.controller.click(cell.center, press_time=0.15)
                clicked.append(row_targets[self._char_idx])
                self._char_idx += 1
                time.sleep(0.5)  #: 点击响应垫(选人点击瞬时生效,防连点丢帧)
            self._need_top = True
            log.info('AS星启填充: 行%d 点 %s', row_no, '、'.join(clicked))
            return self.round_wait(f'行{row_no} 点卡{len(batch)}人', wait=0.5)

        # ⑤ 本页无剩余目标前缀:首见页先原页重扫一轮再翻——「等级」锚 OCR
        # 单帧会漏卡(实机:目标所在页 16 格单帧只读出 14,目标格子不存在
        # → 前缀断 → 直接翻页会把目标页落在身后),重扫 = 重掷一次识别
        sig = self._page_sig(cells)
        if sig != self._last_seek_sig:
            self._last_seek_sig = sig
            return self.round_wait('本页重扫(锚漏卡重掷)', wait=1)
        return self._page_down(cells, row_targets[self._char_idx], row_no)

    def _advance_row(self, row_no: int) -> OperationRoundResult:
        """星启行完成推进:游标复位 + 点下一行槽位(收起+重选中,由行守卫
        复验展开);最后一行 = 填充完成。"""
        self._char_idx = 0
        self._row_idx += 1
        self._row_selected = False
        self._need_top = True
        if self._row_idx < len(self.teams):
            self._click_area_center(
                _TEAM_SCREEN, _ARC_ROW_SLOT_AREAS[self._row_idx + 1])
            return self.round_wait(f'行 {row_no} 填充完成,切下一行', wait=1.2)
        return self.round_success('填充完成', wait=1)

    @staticmethod
    def _cell_names(cell) -> list[str]:
        """格子可判名字列表:置信名在前,候选第一名在后。"""
        names: list[str] = []
        if cell.guess.char:
            names.append(cell.guess.char)
        if cell.guess.candidates:
            names.append(cell.guess.candidates[0][0])
        return names

    @staticmethod
    def _member_has(members: list, name: str) -> bool:
        """落位回验:成员的置信名或候选集含目标名即算落位。"""
        for m in members:
            if m.char == name:
                return True
            if any(n == name for n, _ in m.candidates):
                return True
        return False
