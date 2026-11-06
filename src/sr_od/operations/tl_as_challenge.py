"""末日幻影完整挑战(组合 op):编队选人 → 终焉公理装配 → 前往挑战 →
节点战斗推进(前进+秘技+开战) → 最终结算 → 返回选关。

拆分为多个可独立 ``run_operation`` 的 op(人类老莫 2026-11-06 指示:不同场景
用不同 op,挑战 op 组合它们):

- :class:`TlAsTeamFillOp` 编队选人:清空两/三行 + 按目标填 8/12 人
  (星启整页批量点卡,双节点逐人回验驱动);
  起点 = 末日幻影-编队,终点 = 编队屏(已填满)。
- :class:`TlAsAxiomEquipOp` 终焉公理装配:两行右端圆圈 → 弹窗选卡 → 装配效果;
  起点 = 编队屏(已填人),终点 = 编队屏(已装配)。
- :class:`TlAsBattleOp` 节点战斗推进:简报关闭 → 前进+秘技+开战 → 战斗等待 →
  节点结算推进 → 最终结算;起点 = 首领简报横幅或节点画面,终点 = 最终结算
  点「返回末日幻影」后。
- :class:`TlApocalypticShadowChallengeOp` 组合:入口多态 → 选人 → 装配 →
  前往挑战 → 战斗推进 → 返回选关。

前置:``GotoTreasuresLightward(TLMode.APOCALYPTIC_SHADOW)`` 到末日幻影选关屏;
难度选择不在本 op 内(自动化默认打当前可打的最高难度——3 星通关最高难度视同
通关全部前置难度,奖励由「快速通关」弹窗补发)。

编队交互模型(与虚构叙事编队的差异见各节点注释):

- 两行各 4 槽对应两个节点;点槽位语义按列表展开态分三种:收起态点槽位 =
  展开列表 + 选中该行;展开态点**当前选中行**的已入队槽位 = 移除该角色;
  展开态点**非选中行**槽位 = 不改编队、仅收起列表;
- 清空编队不靠垃圾桶(顶部垃圾桶在此屏无清空功能),用「点已入队槽位」逐个
  移除,由落位回验(行成员实读)驱动收敛;
- 行 boss 卡内的「坚防守备/阵地转移」等按钮 = **敌方特性条款查看入口**,
  点击仅弹说明、不改变任何装配(实机验证);真正的增益装配入口 = 行右端
  圆形按钮(编入角色后出现)→「终焉公理」弹窗(增益三选一,名称随期轮换,
  按位置选择后点「装配效果」,弹窗自动关闭);
- 「前往挑战」在校验不通过(编队不满 / 含不可用角色)时点击无反应——填充
  与装配节点保证到达时编队合法;修改已挑战编队会先弹「更换编队确认」;
- 「前往挑战」点击生效后先弹**首领简报横幅**(「点击空白处关闭」,不点也会
  自动消失)→ 节点画面(大世界,pc_alt 模式,左栏锚与忘却之庭节点画面同构,
  复用其 area);
- 两节点**逐个开战**:节点一战斗结束出节点结算页(积分明细 + 「前往节点二」)
  → 节点二简报横幅 → 节点二战斗 → 最终结算页(通关奖励 + 「返回末日幻影」);
- 节点画面开战顺序 = **前进接近 → 施放秘技 → 点击开战**(复用框架
  :class:`~sr_od.operations.technique.UseTechnique`;攻击型秘技施放即入战斗,
  增益型秘技施放后再点击开战);自动战斗由游戏继承上一次设置,op 不接管;
- 战斗以「剩余行动值」计分,行动值耗尽 = 低分结算,不视为失败流程。
"""

from __future__ import annotations

import re
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.treasures_lightward.obs.tl_team_obs import (
    AnchorCell,
    read_character_cells_by_level,
    read_team_waves,
)
from sr_od.config.character_const import CHARACTER_LIST
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.technique import UseTechnique

_SELECT_SCREEN: str = '末日幻影-选关'
_TEAM_SCREEN: str = '末日幻影-编队'
_BANNER_SCREEN: str = '末日幻影-首领简报'
_RESULT_SCREEN: str = '末日幻影-节点结算'
_AXIOM_SCREEN: str = '末日幻影-终焉公理'
_NODE_SCREEN: str = '忘却之庭-节点画面'  # 节点画面左栏锚(查看详情)与 FH 同构,复用其 area

#: 角色列表滚动拖动(向下翻页;本机实测标定 2026-11-06:400px/0.5s 慢拖 =
#: 精准 3 行、无惯性过冲、落定即识别清晰;快拖会触发惯性滚轮跳页,禁用。
#: ⚠️ 拖动手感与本机鼠标 DPI/速度相关,换机需重标)
_SCROLL_FROM: Point = Point(300, 850)
_SCROLL_TO: Point = Point(300, 450)
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

_ARC_AXIOM_AREAS: dict[int, str] = {
    1: '04-增益入口-行1',
    2: '04-增益入口-行2',
    3: '04-增益入口-行3',
}

_ARC_TRASH_AREA: str = '04-垃圾桶'


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
        waves = read_team_waves(self.ctx, screen, screen_name=_TEAM_SCREEN)
        if not waves:
            # 锚未读到 = 降级空列表,不等于编队已空(弹窗遮挡锚行会走到这);
            # 误判已空会跳过清队,行满导致填充死循环
            return self.round_retry('波次锚未读到(画面遮挡?),重读', wait=1.5)
        list_open = self.round_by_find_area(
            screen, _TEAM_SCREEN, '列表-角色列表页签').is_success

        # 找第一个有成员的槽位(行 0 基、槽 0 基)
        target: tuple[int, int] | None = None
        for r, wave in enumerate(waves):
            for s, member in enumerate(wave.members):
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
        waves_probe = read_team_waves(self.ctx, image, screen_name=_TEAM_SCREEN)
        if not waves_probe:
            return self.round_retry('波次锚未读到(画面遮挡?),重读', wait=1.5)
        if len(waves_probe) != len(self.teams):
            return self.round_fail(
                f'编队屏节点数 {len(waves_probe)} 与队伍数 {len(self.teams)} 不符:'
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

        # 找卡:星启 = 整页批量(见 _arc_fill_round);双节点 = 逐人找卡。
        cells = read_character_cells_by_level(self.ctx, image)
        if self._arc_mode:
            return self._arc_fill_round(image, cells, row_no)

        waves = read_team_waves(self.ctx, image, screen_name=_TEAM_SCREEN)
        if not waves:
            # 锚未读到的降级空列表不可当「成员为空」用(会误判落位失败死循环点卡)
            return self.round_retry('落位回验锚未读到,重读', wait=1.5)
        row_members = waves[row_no - 1].members if len(waves) >= row_no else []
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
        """固定快速大幅拖动回顶,不验证到位(人类老莫 2026-11-06 定案)。

        方向 = 手指自上而下拖(250→850)= 列表向上滚回顶部;列表天然止于
        顶部,拖过头无副作用。上滑方向是向后翻页(与 _page_down 同向),
        反着写会把「回顶」变成「冲向列表尾」(实机实证:回顶后首扫页签
        全是 4 星尾部角色)。单次大幅快拖惯性滚动约 4+ 页(本机实测),
        3 次任何起点都到顶。"""
        for _ in range(_TOP_DRAG_COUNT):
            self.ctx.controller.drag_to(
                _TOP_TO, start=_TOP_FROM, duration=_TOP_DURATION)
        self._need_top = False
        self._down_stagnation = 0
        self._seen_sigs = set()
        self._last_seek_sig = ''
        return self.round_wait('回列表顶部', wait=2)

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


class TlAsAxiomEquipOp(SrOperation):
    """终焉公理装配:两行右端圆圈 → 弹窗选卡 → 装配效果。起点 = 编队屏(已填人)。"""

    def __init__(self, ctx: SrContext, buff_slots: tuple[int, ...] | list[int] = (1, 1)):
        """
        Args:
            buff_slots: 每行装配的终焉公理增益序号(1 基,每行三选一;
                增益名称随期轮换不可锚定,按卡片位置选择)。
                2 项 = 双节点(01-03);3 项 = 星启三节点。默认 (1, 1)。
                接受 list(MCP JSON 反序列化产物),内部转 tuple。
        """
        SrOperation.__init__(self, ctx, op_name='末日幻影 终焉公理装配')
        buff_slots = tuple(buff_slots)
        if any(not 1 <= s <= 3 for s in buff_slots):
            raise ValueError(f'buff_slots 须为 1-3: {buff_slots}')
        if len(buff_slots) not in (2, 3):
            raise ValueError(f'buff_slots 需 2(双节点)或 3(星启)项: {buff_slots}')
        self._buff_slots: tuple[int, ...] = buff_slots
        # 增益入口分派按布局模式(星启 = 行尾「+」area,双节点 = 建档圆圈);
        # 星启判定 = 3 项增益,与 TlAsTeamFillOp 的 12 人判定同构
        self._arc_mode: bool = len(buff_slots) == 3
        self._row_idx: int = 0              #: 当前装配行(0 基)
        self._phase: str = 'open'           #: 装配子步:open 点圆圈 / select 点卡片 /
                                            # confirm 点装配效果 / closed 等弹窗关

    @operation_node(name='装配循环', is_start_node=True, node_max_retry_times=16)
    def _equip_loop(self) -> OperationRoundResult:
        """逐行装配指定增益进终焉公理(行增益入口 → 弹窗选卡 → 装配效果)。

        行内「敌方特性」条款按钮(坚防守备/阵地转移等)是机制查看入口,点击
        不改变装配(实机验证);增益入口分派:星启 = 行尾「+」按钮(x≈1826,
        y 与行同轴),双节点 = 建档「公理圆圈{row}」;增益名称随期轮换不可
        锚定,按位置 ``buff_slots``(1 基)选卡。装配生效后弹窗自动关闭回
        编队屏,以「装配效果」按钮消失为到达证据。"""
        row = self._row_idx + 1
        screen = self.last_screenshot
        in_axiom = self.round_by_find_area(screen, _AXIOM_SCREEN, '文本-选择增益行').is_success
        in_team = (self.round_by_find_area(screen, _TEAM_SCREEN, '标题-末日幻影行').is_success
                   and self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success)

        if self._phase == 'open':
            if in_axiom:
                self._phase = 'select'
                return self.round_wait('公理弹窗已开', wait=0.5)
            if in_team:
                if self._arc_mode:
                    # 星启:行尾「+」即终焉公理入口(编入角色前后形态一致,实测);
                    # 分派必须按布局模式——按行号比较会把 04 的行 2/3 错派到
                    # 01-03 圆圈坐标(该坐标在 04 无效,弹窗开不了死循环)
                    self._click_area_center(_TEAM_SCREEN, _ARC_AXIOM_AREAS[row])
                else:
                    self._click_area_center(_TEAM_SCREEN, f'按钮-公理圆圈{row}')
                self._phase = 'select'
                return self.round_wait(f'打开行{row}公理弹窗', wait=1.5)
            return self.round_retry('不在编队屏也非公理弹窗', wait=1.5)

        if self._phase == 'select':
            if not in_axiom:
                self._phase = 'open'
                return self.round_retry('公理弹窗未开,重开', wait=1.2)
            slot = self._buff_slots[self._row_idx]
            self._click_area_center(_AXIOM_SCREEN, f'卡片-增益{slot}')
            self._phase = 'confirm'
            return self.round_wait(f'行{row}选增益{slot}', wait=0.8)

        if self._phase == 'confirm':
            click = self.round_by_find_and_click_area(
                screen, _AXIOM_SCREEN, '按钮-装配效果', success_wait=1.2)
            if click.is_success:
                self._phase = 'closed'
                return self.round_wait(f'行{row}装配确认', wait=1.5)
            return self.round_retry('装配效果按钮未命中', wait=1)

        # closed:弹窗应已自动关闭,到达编队屏 = 装配生效
        if in_team:
            if self._row_idx < len(self._buff_slots) - 1:
                self._row_idx += 1
                self._phase = 'open'
                return self.round_wait(f'行{row}装配完成', wait=1)
            return self.round_success('装配完成', wait=1)
        if in_axiom:
            self._phase = 'confirm'
            return self.round_retry('弹窗未关,重按装配', wait=1.2)
        return self.round_retry('画面异常(既非编队屏也非公理弹窗)', wait=1.5)

    def _click_area_center(self, screen_name: str, area_name: str) -> None:
        """按建档 rect 中心点击(纯定位区;坐标单一真相源在 screen_info)。"""
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        rect = area.rect
        self.ctx.controller.click(
            Point((rect.x1 + rect.x2) // 2, (rect.y1 + rect.y2) // 2), press_time=0.15)


class TlAsBattleOp(SrOperation):
    """节点战斗推进(单循环):简报关闭 → 前进+秘技+开战 → 战斗等待 → 结算推进。

    起点 = 首领简报横幅(挑战发起后弹出)或节点画面(大世界);终点 = 最终
    结算页点「返回末日幻影」(STATUS_DONE)。单节点大循环按画面特征每轮
    重新分流(实机验证过的结构,避免子节点边冲突)。节点画面开战顺序 =
    前进接近 → 施放秘技(复用框架 :class:`UseTechnique`;攻击型秘技施放即
    入战斗,增益型秘技施放后下一轮点击开战)→ 点击画面中心开战。"""

    STATUS_DONE: ClassVar[str] = '最终结算完成'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='末日幻影 节点战斗')
        # 命名避开框架 Operation._current_node(执行期被赋为当前节点对象,撞名
        # 会让本记录被覆盖,日志打出对象 repr)
        self._brief_node_no: int = 0     #: 简报标题实读的当前节点号(1/2;简报外为 0)
        self._brief_pending: bool = False  #: 简报已确认待进节点画面(首战开战守卫)
        self._tech_used: bool = False    #: 当前节点秘技已施放(防增益型秘技重复施放;
                                         #  「前往节点二」推进时重置,新节点新秘技点)

    @operation_node(name='战斗循环', is_start_node=True, node_max_retry_times=720)
    def _battle_loop(self) -> OperationRoundResult:
        """单节点大循环,按画面特征每轮重新分流:

        1. 结算页 → 「前往节点二」(重置秘技标记)或「返回末日幻影」(STATUS_DONE);
        2. 首领简报横幅 → 实读节点号 + 点空白关闭;
        3. 节点画面(左栏「查看详情」;战斗中左栏被战斗 UI 替换故不误判):
           未施秘技 = 前进接近 + 施放秘技(攻击型施放即入战斗,本轮结束重新
           分流);已施 = 前进 + 点击画面中心开战;
        4. 其余 = 战斗中等待(每 5s 一轮;720 轮 ≈ 1 小时兜底,防异常卡死)。"""
        screen = self.last_screenshot

        if self.round_by_find_area(screen, _RESULT_SCREEN, '标题-挑战结束').is_success:
            if self.round_by_find_area(screen, _RESULT_SCREEN, '按钮-返回末日幻影').is_success:
                self.ctx.controller.click(Point(1240, 949), press_time=0.15)
                return self.round_success(TlAsBattleOp.STATUS_DONE, wait=2.5)
            # 「前往节点二/三」按钮同位(结算页布局恒定,文本随节点轮换)——
            # 统一按区域点击并重置秘技标记(新节点新秘技点)
            self.ctx.controller.click(Point(1243, 949), press_time=0.15)
            self._tech_used = False
            return self.round_retry('前往下一节点', wait=3)

        if self.round_by_find_area(screen, _BANNER_SCREEN, '提示-点击空白处关闭').is_success:
            # 简报标题区的「节点一/二/三」位置恒定(说明行数只影响下方区域),
            # 实读记入状态——节点流转的判定锚比结算页按钮文本更稳
            if self.round_by_find_area(screen, _BANNER_SCREEN, '标题-节点二行').is_success:
                self._brief_node_no = 2
                self._brief_pending = True
            elif self.round_by_find_area(screen, _BANNER_SCREEN, '标题-节点三行').is_success:
                self._brief_node_no = 3
                self._brief_pending = True
            elif self.round_by_find_area(screen, _BANNER_SCREEN, '标题-节点一行').is_success:
                self._brief_node_no = 1
                self._brief_pending = True
            self.ctx.controller.click(Point(960, 950), press_time=0.15)
            return self.round_retry(f'关闭首领简报(节点{self._brief_node_no})', wait=2.5)

        if self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success:
            self._brief_pending = False
            if not self._tech_used:
                # 未施秘技:前进接近后施放(攻击型秘技施放即入战斗,本轮结束
                # 重新分流走战斗等待;增益型下一轮走到点击开战分支)
                self.ctx.controller.move('w', press_time=2)
                tech_op = UseTechnique(self.ctx)
                tech_op.execute()
                self._tech_used = True
                return self.round_retry('施放秘技', wait=3)
            self.ctx.controller.move('w', press_time=2)
            self.ctx.controller.click(Point(960, 540), press_time=0.1)
            return self.round_retry(f'节点{self._brief_node_no} 发起战斗', wait=5)

        return self.round_wait('战斗进行中', wait=5)


class TlAsBattleExitOp(SrOperation):
    """退出当前节点战斗/结算态,回到末日幻影选关。

    背景:挑战链只覆盖「往前打」,弃赛/换队场景没有退出路径——只能等
    行动值自然耗尽(低分结算)或手动点击(禁用)。v1 覆盖结算态:节点结算页
    点「退出」回选关;最终结算页同位按钮文本轮换为「返回末日幻影」,同键
    处理。战斗内暂停退出(右上暂停 II → 结束战斗)待战斗帧建档后补(登记成待办:
    本地待办 AS 条)。起点 = 末日幻影-节点结算(「挑战结束」命中),终点 =
    末日幻影-选关。"""

    STATUS_DONE: ClassVar[str] = '退出完成'

    @operation_node(name='退出循环', is_start_node=True, node_max_retry_times=12)
    def _exit_loop(self) -> OperationRoundResult:
        """按画面分流:已在选关 = 完成;结算页点「退出」/「返回末日幻影」。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _SELECT_SCREEN, '标题-末日幻影行').is_success:
            return self.round_success(self.STATUS_DONE, wait=0.5)

        if self.round_by_find_area(screen, _RESULT_SCREEN, '标题-挑战结束').is_success:
            click = self.round_by_find_and_click_area(
                screen, _RESULT_SCREEN, '按钮-退出',
                until_not_find_all=[(_RESULT_SCREEN, '标题-挑战结束')],
                pre_delay=0.5, retry_wait=1.5)
            if click.is_success:
                return self.round_wait('点退出', wait=2)
            # 最终结算页无「退出」:同位按钮文本轮换为「返回末日幻影」
            click = self.round_by_find_and_click_area(
                screen, _RESULT_SCREEN, '按钮-返回末日幻影',
                until_not_find_all=[(_RESULT_SCREEN, '标题-挑战结束')],
                pre_delay=0.5, retry_wait=1.5)
            if click.is_success:
                return self.round_wait('返回末日幻影', wait=2)
            return self.round_retry('结算按钮未命中(确认弹窗?)', wait=1.5)

        return self.round_retry(
            '不在选关也不在结算页(战斗内退出 v2 候补:需战斗帧建档)', wait=2)


class TlApocalypticShadowChallengeOp(SrOperation):
    """末日幻影完整挑战(组合 op):选人 → 装配 buff → 前往挑战 → 战斗推进 → 返回选关。"""

    STATUS_SUCCESS: ClassVar[str] = '挑战成功'

    def __init__(self, ctx: SrContext, team_names: list[str],
                 buff_slots: tuple[int, ...] | list[int] = (1, 1)):
        """
        Args:
            team_names: 按行(节点)顺序拼接的角色中文名列表,8 人(2 行×4,
                双节点 01-03)或 12 人(3 行×4,星启 04);与脸库识别名一致,
                行 1 = 节点一队伍,以此类推。队伍须避开带警告标记的角色
                (命途/养成警告,如当期试用角色)——此类角色可落位,但「前往
                挑战」校验不通过(点击无反应)。
            buff_slots: 每行装配的终焉公理增益序号(1 基;增益名称随期轮换,
                按卡片位置选择)。2 项 = 双节点,3 项 = 星启。默认全 1。
        """
        SrOperation.__init__(self, ctx, op_name='末日幻影 挑战')
        self.fill_op = TlAsTeamFillOp(ctx, team_names)
        self.equip_op = TlAsAxiomEquipOp(ctx, buff_slots)
        self.battle_op = TlAsBattleOp(ctx)

    @operation_node(name='进入编队屏', is_start_node=True, node_max_retry_times=10)
    def _enter_team(self) -> OperationRoundResult:
        """从选关屏进编队屏;已在编队屏则直接通过。

        选关屏入口按钮随难度状态变形:未通关难度 = 中央「前往挑战」大按钮;
        已通关难度 = 节点分数卡下的「重新挑战」(两态同屏,前者消失)。
        首领简报横幅可见 = 挑战已发起(编队满员态进编队屏游戏会自动弹简报),
        返回 BANNER_UP 直连战斗推进,跳过填充/装配。节点画面(左栏「查看详情」)
        可见 = 挑战进行中,返回 BATTLE_ONGOING 直连战斗推进。"""
        screen = self.last_screenshot
        if (self.round_by_find_area(screen, _TEAM_SCREEN, '标题-末日幻影行').is_success
                and self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success):
            # 难度与目标人数匹配校验(星启 04 三行/双节点 01-03 两行,由
            # read_team_waves 锚行数实读)——不匹配在填充防御处显式失败
            return self.round_success()
        if self.round_by_find_area(screen, _BANNER_SCREEN, '提示-点击空白处关闭').is_success:
            return self.round_success('BANNER_UP')
        if self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success:
            return self.round_success('BATTLE_ONGOING')
        if self.round_by_find_area(
                screen, _SELECT_SCREEN, '按钮-更换编队确认').is_success:
            self.ctx.controller.click(Point(1165, 672), press_time=0.15)
            return self.round_retry('确认更换编队弹窗', wait=2.5)
        if self.round_by_find_area(screen, _SELECT_SCREEN, '按钮-更换编队').is_success:
            self.ctx.controller.click(Point(1748, 737), press_time=0.15)
            return self.round_retry('选关屏点更换编队', wait=2.5)
        if self.round_by_find_area(screen, _SELECT_SCREEN, '按钮-重新挑战').is_success:
            self.ctx.controller.click(Point(928, 890), press_time=0.15)
            return self.round_retry('选关屏点重新挑战', wait=2.5)
        if self.round_by_find_area(screen, _SELECT_SCREEN, '按钮-前往挑战').is_success:
            self.ctx.controller.click(Point(960, 841), press_time=0.15)
            return self.round_retry('选关屏点前往挑战', wait=2.5)
        return self.round_retry('画面异常(既非选关屏也非编队屏)', wait=1.5)

    @node_from(from_name='进入编队屏')
    @operation_node(name='编队选人', node_max_retry_times=8)
    def _fill(self) -> OperationRoundResult:
        """组合 :class:`TlAsTeamFillOp`(清空 + 填 8 人,落位回验驱动)。"""
        op_result = self.fill_op.execute()
        return self.round_by_op_result(op_result)

    @node_from(from_name='编队选人')
    @operation_node(name='终焉公理装配', node_max_retry_times=8)
    def _equip(self) -> OperationRoundResult:
        """组合 :class:`TlAsAxiomEquipOp`(两行圆圈 → 弹窗选卡 → 装配效果)。"""
        op_result = self.equip_op.execute()
        return self.round_by_op_result(op_result)

    @node_from(from_name='终焉公理装配')
    @operation_node(name='前往挑战', node_max_retry_times=10)
    def _start(self) -> OperationRoundResult:
        """点「前往挑战」→ 到达验证:首领简报横幅或节点画面出现。

        简报横幅不点击会在数秒内自动关闭进入节点画面,两种到达态都认;
        修改已挑战编队会先弹「更换编队确认」(与选关屏同名弹窗同构)。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _BANNER_SCREEN, '文本-首领特性').is_success:
            return self.round_success()
        if self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success:
            return self.round_success()
        if self.round_by_find_area(
                screen, _SELECT_SCREEN, '按钮-更换编队确认').is_success:
            self.ctx.controller.click(Point(1165, 672), press_time=0.15)
            return self.round_retry('确认更换编队弹窗', wait=2.5)
        if self.round_by_find_area(screen, _TEAM_SCREEN, '按钮-前往挑战').is_success:
            self.ctx.controller.click(Point(1577, 985), press_time=0.15)
            return self.round_retry('点击前往挑战', wait=2.5)
        return self.round_retry('画面异常(不在编队屏也未见简报)', wait=1.5)

    @node_from(from_name='前往挑战')
    @node_from(from_name='进入编队屏', status='BANNER_UP')
    @node_from(from_name='进入编队屏', status='BATTLE_ONGOING')
    @operation_node(name='战斗推进', node_max_retry_times=8)
    def _battle(self) -> OperationRoundResult:
        """组合 :class:`TlAsBattleOp`(简报 → 秘技开战 → 战斗 → 结算推进)。"""
        op_result = self.battle_op.execute()
        return self.round_by_op_result(op_result)

    @node_from(from_name='战斗推进', status=TlAsBattleOp.STATUS_DONE)
    @operation_node(name='返回选关', node_max_retry_times=12)
    def _click_back(self) -> OperationRoundResult:
        """最终结算点「返回末日幻影」已在战斗推进内点击;本节点处理快速通关
        奖励弹窗 → 选关屏。

        3 星通关最高难度时游戏弹「快速通关」补发前置难度奖励(确认 + 一层
        「点击空白处关闭」提示),两步都处理后到达选关屏。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _SELECT_SCREEN, '标题-末日幻影行').is_success:
            return self.round_success(TlApocalypticShadowChallengeOp.STATUS_SUCCESS)
        if self.round_by_find_area(
                screen, _SELECT_SCREEN, 'AFTER_BATTLE_QUICK_PASS_CONFIRM').is_success:
            self.ctx.controller.click(Point(960, 988), press_time=0.15)
            return self.round_wait('领取快速通关奖励', wait=2)
        click = self.round_by_find_and_click_area(
            screen, _RESULT_SCREEN, '按钮-返回末日幻影', success_wait=2)
        if click.is_success:
            return self.round_wait('返回末日幻影中', wait=2)
        return self.round_retry('等待返回按钮', wait=1.5)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.start_running()
    op = TlApocalypticShadowChallengeOp(
        ctx,
        ['姬子•启行', '瓦尔特', '知更鸟', '丹恒•腾荒', '黄泉', '卡芙卡', '黑天鹅', '灵砂'],
        (3, 3),
    )
    op.execute()


if __name__ == '__main__':
    __debug()
