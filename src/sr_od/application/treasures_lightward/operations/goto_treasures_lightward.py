"""任意画面 → 逐光捡金分类入口/对应玩法画面的导航 operation。

设计(2026-11-04 与负责人对齐):
- 前置链共用:判定当前画面 → 在入口链上(大世界/星际和平指南/指南-逐光捡金/逐光捡金/编队屏)就从所在位置接续;
  不在链上先跑 :class:`BackToNormalWorldPlus` 回大世界,再走 大世界→指南→逐光捡金tab→分类页。
- 分类页节点按 mode 显式点左侧目标分类(默认选中项两次实测不同,勿依赖默认态),
  之后按 mode 分叉到各自的「点入口按钮→到达验证」节点。
- 到达验证锚:忘却之庭=选关混沌回忆视图双锚(FH_TITLE+标题-混沌回忆行)+紊流弹窗处理;
  虚构叙事=新期开场页(点开启故事)→选关(PF_TITLE);末日幻影=新期开场页(点前往挑战)
  →选关(标题+难度条双锚);异相仲裁=目标画面未建档,点击入口按钮后显式失败并登记成待办。
- 起点已在选关/编队屏且目标非忘却之庭时,经右上关闭X 退回大世界,再走手机菜单链
  (左上菜单图标→菜单屏指南图标)进指南——不走右上指南快捷按钮(车厢场景无此按钮)。

画面证据:docs/game/screens/{指南-逐光捡金,逐光捡金,忘却之庭-编队}.md(2026-11-04 实机建档)。
英文名依据国际服官方译名:逐光捡金=Treasures Lightward,忘却之庭=Forgotten Hall,
虚构叙事=Pure Fiction,末日幻影=Apocalyptic Shadow,异相仲裁=Anomaly Arbitration(Fandom wiki)。
"""

from enum import Enum

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_SELECT_SCREEN: str = '逐光捡金'
_CATEGORY_SCREEN: str = '指南-逐光捡金'
_GUIDE_SCREEN: str = '星际和平指南'
_TEAM_SCREEN: str = '忘却之庭-编队'
_MENU_SCREEN: str = '菜单'


class TLMode(Enum):
    """逐光捡金的目标玩法类型(分类页左侧四类,「最近更新」仅为快捷入口不在此列)。"""

    FORGOTTEN_HALL = 'forgotten_hall'
    PURE_FICTION = 'pure_fiction'
    APOCALYPTIC_SHADOW = 'apocalyptic_shadow'
    ANOMALY_ARBITRATION = 'anomaly_arbitration'


# 分类页:mode → 左侧分类条目 area
_CATEGORY_AREA: dict[TLMode, str] = {
    TLMode.FORGOTTEN_HALL: '分类-忘却之庭',
    TLMode.PURE_FICTION: '分类-虚构叙事',
    TLMode.APOCALYPTIC_SHADOW: '分类-末日幻影',
    TLMode.ANOMALY_ARBITRATION: '分类-异相仲裁',
}

# 分类页:mode → 选中后右面板的入口按钮 area(到达动作的点击目标)
_ENTER_AREA: dict[TLMode, str] = {
    TLMode.FORGOTTEN_HALL: '按钮-传送-卡片式',
    TLMode.PURE_FICTION: '按钮-传送-卡片式',
    TLMode.APOCALYPTIC_SHADOW: '按钮-传送-卡片式',
    TLMode.ANOMALY_ARBITRATION: '按钮-前往挑战-异相仲裁',
}

# 分类页:mode → category_select 的选中验证(右面板入口按钮出现=选中生效)
_ENTER_STATUS: dict[TLMode, str] = {
    TLMode.FORGOTTEN_HALL: 'ENTER_FORGOTTEN_HALL',
    TLMode.PURE_FICTION: 'ENTER_PURE_FICTION',
    TLMode.APOCALYPTIC_SHADOW: 'ENTER_APOCALYPTIC_SHADOW',
    TLMode.ANOMALY_ARBITRATION: 'ENTER_ANOMALY_ARBITRATION',
}


class GotoTreasuresLightward(SrOperation):
    """导航到逐光捡金指定玩法的入口画面。

    - FORGOTTEN_HALL:终点=忘却之庭选关界面·混沌回忆视图·无弹窗(紊流更新弹窗自动关闭)。
    - PURE_FICTION:终点=虚构叙事选关画面(PF_TITLE;新期「开启故事」自动点击,分支待实测)。
    - APOCALYPTIC_SHADOW / ANOMALY_ARBITRATION:目标画面未建档(登记成待办),点击入口按钮后显式失败。
    """

    def __init__(self, ctx: SrContext, mode: TLMode | str):
        """
        :param ctx: 上下文
        :param mode: 目标玩法类型(枚举或枚举值字符串,如 'forgotten_hall')
        """
        self.mode: TLMode = mode if isinstance(mode, TLMode) else TLMode(mode)
        SrOperation.__init__(self, ctx, op_name=gt('前往逐光捡金') + '-' + self.mode.value)

    @operation_node(name='识别当前画面', is_start_node=True, node_max_retry_times=5)
    def classify(self) -> OperationRoundResult:
        """按 入口链画面 优先级识别当前位置,分流到对应接续节点。

        判序:紊流弹窗(模态盖底,先于底屏锚)→ 编队屏 → 选关 → 分类页 → 指南 → 大世界。
        逐光捡金用 FH_TITLE 判(三视图共用标题行,回忆视图也算在链上,由收尾节点切回)。
        AT_TREASURES 按模式分叉:FORGOTTEN_HALL 直接选关收尾;其余模式选关不是终点,
        需先关闭选关回大世界再走 指南→分类页 重入(2026-11-05 实测:选关界面无到分类
        页的直达出口,右上关闭X 是唯一出口,落点=进入前的场景,可能为列车车厢)。
        """
        screen = self.last_screenshot

        if self.round_by_find_area(screen, _SELECT_SCREEN, 'NODE_FIRST_CLICK_EMPTY').is_success:
            status = 'AT_TREASURES' if self.mode == TLMode.FORGOTTEN_HALL else 'AT_TREASURES_OTHER'
            return self.round_success(status=status)
        if self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success:
            status = 'AT_TEAM' if self.mode == TLMode.FORGOTTEN_HALL else 'AT_TEAM_OTHER'
            return self.round_success(status=status)
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'FH_TITLE').is_success:
            status = 'AT_TREASURES' if self.mode == TLMode.FORGOTTEN_HALL else 'AT_TREASURES_OTHER'
            return self.round_success(status=status)
        if self.round_by_find_area(screen, _CATEGORY_SCREEN, '标识-标题-逐光捡金').is_success:
            return self.round_success(status='AT_CATEGORY')
        if self.round_by_find_area(screen, _GUIDE_SCREEN, 'TAB-逐光捡金').is_success:
            return self.round_success(status='AT_GUIDE')
        if self.round_by_find_area(screen, '菜单', '开拓等级').is_success:
            return self.round_success(status='AT_MENU')
        if self.round_by_find_area(screen, '大世界', '角色图标').is_success:
            return self.round_success(status='AT_WORLD')
        return self.round_success(status='OFF_PATH')

    @node_from(from_name='识别当前画面', status='OFF_PATH')
    @operation_node(name='回大世界', node_max_retry_times=3)
    def back_to_world(self) -> OperationRoundResult:
        """不在入口链上:交给兜底 op 回大世界(其内含公告/各玩法退出分支)。

        延迟导入:BackToNormalWorldPlus 模块级导入会级联拉起货币战争全图,
        本 op 的导入不应被其传递依赖绑架(该图任何文件语法态变化都会波及)。"""
        from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus

        op = BackToNormalWorldPlus(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_success(status='AT_WORLD', wait=1)
        return self.round_retry(wait=2)

    @node_from(from_name='识别当前画面', status='AT_TEAM')
    @operation_node(name='编队返回选关', node_max_retry_times=6)
    def team_back(self) -> OperationRoundResult:
        """编队屏 → 返回箭头 → 选关(此跳无紊流弹窗,FH_TITLE 单锚验证转移——
        三视图共用,回忆视图帧也命中,不要求混沌回忆行)。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _TEAM_SCREEN, '按钮-返回箭头',
            until_find_all=[(_SELECT_SCREEN, 'FH_TITLE')],
            pre_delay=0.5, success_wait=1.5, retry_wait=1.5,
        )

    @node_from(from_name='识别当前画面', status='AT_TREASURES_OTHER')
    @node_from(from_name='识别当前画面', status='AT_TEAM_OTHER')
    @operation_node(name='非忘却之庭回大世界', node_max_retry_times=6)
    def leave_for_world(self) -> OperationRoundResult:
        """非 FH 模式:从选关/编队屏经右上关闭X 退出到大世界(2026-11-05 实测
        关闭X 是选关唯一出口;编队屏先点返回箭头到选关再由本节点处理选关出口)。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _TEAM_SCREEN, '按钮-返回箭头').is_success:
            self.round_by_find_and_click_area(
                screen, _TEAM_SCREEN, '按钮-返回箭头', success_wait=1.5)
            return self.round_retry('编队先回选关', wait=1.5)
        result = self.round_by_find_and_click_area(
            screen, _SELECT_SCREEN, '按钮-关闭X',
            until_find_all=[('大世界', '角色图标')],
            pre_delay=0.5, success_wait=2, retry_wait=2,
        )
        if result.is_success:
            return self.round_success(status='AT_WORLD')
        return result

    @node_from(from_name='识别当前画面', status='AT_WORLD')
    @node_from(from_name='回大世界')
    @node_from(from_name='非忘却之庭回大世界')
    @operation_node(name='大世界打开菜单', node_max_retry_times=6)
    def open_phone_menu(self) -> OperationRoundResult:
        """大世界(含列车车厢)经左上手机图标打开电话菜单。

        不走右上指南快捷按钮:2026-11-05 实测退出选关的落点可能是列车车厢,
        车厢右上无指南按钮(且车厢与开阔大世界在 screen_info 里同为
        「大世界-普通」无法区分),手机菜单链在任何大世界场景都可用。
        大世界为锁光标场景,点击需按住 Alt(锁光标场景点击规范)。
        先判后点:重试轮菜单可能已被上轮点击打开,再点手机图标会点中
        菜单内同位置的「狸狸通信」图标(2026-11-05 实机踩坑)。"""
        from one_dragon.base.geometry.point import Point

        screen = self.last_screenshot
        if self.round_by_find_area(screen, _MENU_SCREEN, '开拓等级').is_success:
            # 菜单打开动画约 1 秒级:过短的下节点截图会落在动画帧,OCR 点击落空
            return self.round_success(wait=1.5)

        si = self.ctx.screen_loader.get_screen('大世界-普通')
        rect = None
        if si is not None:
            area = next((a for a in si.area_list if a.area_name == '左上图标-菜单'), None)
            rect = area.pc_rect if area is not None else None
        if rect is None:
            return self.round_fail('大世界-普通 缺少 左上图标-菜单 area')
        center = Point((rect.x1 + rect.x2) // 2, (rect.y1 + rect.y2) // 2)
        self.ctx.controller.click(center, press_time=0.15, pc_alt=True)
        return self.round_wait('等待菜单打开', wait=1.5)

    @node_from(from_name='大世界打开菜单')
    @node_from(from_name='识别当前画面', status='AT_MENU')
    @operation_node(name='菜单进指南', node_max_retry_times=6)
    def menu_to_guide(self) -> OperationRoundResult:
        """菜单屏点指南图标 → 星际和平指南。

        用全屏 OCR 找「指南」而非固定坐标:菜单会因「玩法更新」等新增条目
        动态重排(固定 rect 被挤位点中相邻图标);菜单屏内「指南」文字仅此
        一处,lcs 0.9 无误匹配风险。
        点击后验证转移:菜单打开动画期内点击会落空——round_by_ocr_and_click
        只回报点击动作成功、无 until 验证,落空后下节点在菜单屏找不到指南页
        tab 整链失败(实机复现);菜单屏锚(开拓等级)消失=指南页已打开,
        未消失视为落空,round_retry 交由本节点重试。"""
        screen = self.last_screenshot
        result = self.round_by_ocr_and_click(
            screen, '指南', lcs_percent=0.9,
            success_wait=1.5, retry_wait=1.5,
        )
        if not result.is_success:
            return result
        confirm_screen = self.screenshot()
        if self.round_by_find_area(confirm_screen, _MENU_SCREEN, '开拓等级').is_success:
            return self.round_retry('指南点击落空(菜单屏未关闭)', wait=1.5)
        return self.round_success(wait=1.5)

    @node_from(from_name='菜单进指南')
    @node_from(from_name='识别当前画面', status='AT_GUIDE')
    @operation_node(name='指南切逐光捡金tab', node_max_retry_times=6)
    def guide_to_category(self) -> OperationRoundResult:
        """指南切到逐光捡金 tab。

        先短路判已在目标 tab:指南记住上次激活 tab,逐光捡金重入时该 tab 常已
        激活——激活态图标变宽移位,收紧的模板 rect 命不中(实机复现),而此时
        分类页标题直接可见,无需点击。
        tab 图标位随激活 tab 宽度微移,area 已按实测收紧到第 4 图标位。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _CATEGORY_SCREEN, '标识-标题-逐光捡金').is_success:
            return self.round_success(status='AT_CATEGORY', wait=0.5)
        return self.round_by_find_and_click_area(
            screen, _GUIDE_SCREEN, 'TAB-逐光捡金',
            until_find_all=[(_CATEGORY_SCREEN, '标识-标题-逐光捡金')],
            pre_delay=0.5, success_wait=1.5, retry_wait=1.5,
        )

    @node_from(from_name='指南切逐光捡金tab')
    @node_from(from_name='识别当前画面', status='AT_CATEGORY')
    @operation_node(name='分类页选目标', node_max_retry_times=6)
    def category_select(self) -> OperationRoundResult:
        """显式点目标分类(不依赖默认选中态),以右面板入口按钮出现=选中生效。"""
        screen = self.last_screenshot
        result = self.round_by_find_and_click_area(
            screen, _CATEGORY_SCREEN, _CATEGORY_AREA[self.mode],
            until_find_all=[(_CATEGORY_SCREEN, _ENTER_AREA[self.mode])],
            pre_delay=0.3, success_wait=1, retry_wait=1,
        )
        if result.is_success:
            return self.round_success(status=_ENTER_STATUS[self.mode])
        return result

    @node_from(from_name='分类页选目标', status='ENTER_FORGOTTEN_HALL')
    @operation_node(name='忘却之庭进选关', node_max_retry_times=8)
    def fh_enter(self) -> OperationRoundResult:
        """点总览混沌回忆卡的传送。传送后可能弹紊流更新弹窗(压暗底屏,选关锚不可测),
        故本节点不设 until——到达验证与弹窗处理由 选关收尾 节点负责。"""
        screen = self.last_screenshot
        result = self.round_by_find_and_click_area(
            screen, _CATEGORY_SCREEN, '按钮-传送-卡片式',
            pre_delay=0.5, retry_wait=2,
        )
        if result.is_success:
            return self.round_success(wait=2.5)
        return result

    @node_from(from_name='忘却之庭进选关')
    @node_from(from_name='编队返回选关')
    @node_from(from_name='识别当前画面', status='AT_TREASURES')
    @operation_node(name='选关收尾', node_max_retry_times=12)
    def select_settle(self) -> OperationRoundResult:
        """选关到达验证:紊流弹窗→点空白;回忆视图→切回混沌回忆;双锚干净→成功。"""
        screen = self.last_screenshot

        if self.round_by_find_area(screen, _SELECT_SCREEN, 'NODE_FIRST_CLICK_EMPTY').is_success:
            self.round_by_click_area(screen, _SELECT_SCREEN, 'NODE_FIRST_CLICK_EMPTY')
            return self.round_retry('选关-紊流弹窗', wait=1.5)

        if (self.round_by_find_area(screen, _SELECT_SCREEN, '章节名-天艟求仙迷航录').is_success
                or self.round_by_find_area(screen, _SELECT_SCREEN, '章节名-永屹之城遗秘').is_success):
            self.round_by_click_area(screen, _SELECT_SCREEN, '切换器-混沌回忆')
            return self.round_retry('选关-回忆视图切回', wait=1.5)

        if (self.round_by_find_area(screen, _SELECT_SCREEN, 'FH_TITLE').is_success
                and self.round_by_find_area(screen, _SELECT_SCREEN, '标题-混沌回忆行').is_success):
            return self.round_success()

        return self.round_retry('选关-等待画面', wait=1.5)

    @node_from(from_name='分类页选目标', status='ENTER_PURE_FICTION')
    @operation_node(name='虚构叙事进入', node_max_retry_times=8)
    def pf_enter(self) -> OperationRoundResult:
        """卡片式传送与忘却之庭总览卡同位共用。新期可能先弹「开启故事」,由收尾节点处理(待实测)。"""
        screen = self.last_screenshot
        result = self.round_by_find_and_click_area(
            screen, _CATEGORY_SCREEN, '按钮-传送-卡片式',
            pre_delay=0.5, retry_wait=2,
        )
        if result.is_success:
            return self.round_success(wait=2.5)
        return result

    @node_from(from_name='虚构叙事进入')
    @operation_node(name='虚构叙事收尾', node_max_retry_times=12)
    def pf_settle(self) -> OperationRoundResult:
        """到达验证:新期先落「虚构叙事-开场」介绍页(点开启故事)→ 选关(PF_TITLE)。

        2026-11-05 实测:新期(取象为文)传送后先进开场页,右下「开启故事」。
        开场页判定必须双锚(标题+已更新标签):开场页与选关的标题文本同文同位
        (虚构叙事),单标题锚在选关帧也命中 → 会把选关误判成开场页无限点空按钮。"""
        screen = self.last_screenshot
        if (self.round_by_find_area(screen, '虚构叙事-开场', '标题-虚构叙事行').is_success
                and self.round_by_find_area(screen, '虚构叙事-开场', '标签-已更新').is_success):
            self.round_by_find_and_click_area(screen, '虚构叙事-开场', '按钮-开启故事')
            return self.round_retry('虚构叙事-开场页点开启故事', wait=2.5)
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'PF_NEW_START').is_success:
            self.round_by_find_and_click_area(screen, _SELECT_SCREEN, 'PF_NEW_START')
            return self.round_retry('虚构叙事-开启故事', wait=2)
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'PF_TITLE').is_success:
            return self.round_success()
        return self.round_retry('虚构叙事-等待画面', wait=1.5)

    @node_from(from_name='分类页选目标', status='ENTER_APOCALYPTIC_SHADOW')
    @operation_node(name='末日幻影进入', node_max_retry_times=8)
    def as_enter(self) -> OperationRoundResult:
        """卡片式传送,落点为「末日幻影-开场」介绍页(2026-11-05 实测),由收尾节点处理。"""
        screen = self.last_screenshot
        result = self.round_by_find_and_click_area(
            screen, _CATEGORY_SCREEN, '按钮-传送-卡片式',
            pre_delay=0.5, retry_wait=2,
        )
        if result.is_success:
            return self.round_success(wait=2.5)
        return result

    @node_from(from_name='末日幻影进入')
    @operation_node(name='末日幻影收尾', node_max_retry_times=12)
    def as_settle(self) -> OperationRoundResult:
        """到达验证:开场介绍页(点前往挑战)→ 选关(标题+难度条双锚)。

        开场页判定双锚(标题+已更新):开场页与选关标题同文同位,同 pf_settle。"""
        screen = self.last_screenshot
        if (self.round_by_find_area(screen, '末日幻影-开场', '标题-末日幻影行').is_success
                and self.round_by_find_area(screen, '末日幻影-开场', '标签-已更新').is_success):
            self.round_by_find_and_click_area(screen, '末日幻影-开场', '按钮-前往挑战')
            return self.round_retry('末日幻影-开场页点前往挑战', wait=2.5)
        if (self.round_by_find_area(screen, '末日幻影-选关', '标题-末日幻影行').is_success
                and self.round_by_find_area(screen, '末日幻影-选关', '难度-01').is_success):
            return self.round_success()
        return self.round_retry('末日幻影-等待画面', wait=1.5)

    @node_from(from_name='分类页选目标', status='ENTER_ANOMALY_ARBITRATION')
    @operation_node(name='异相仲裁进入', node_max_retry_times=4)
    def aa_enter(self) -> OperationRoundResult:
        """异相仲裁目标画面未建档(登记成待办):点击前往挑战后显式失败,到达验证待建档后补。"""
        screen = self.last_screenshot
        result = self.round_by_find_and_click_area(
            screen, _CATEGORY_SCREEN, '按钮-前往挑战-异相仲裁',
            pre_delay=0.5, retry_wait=2,
        )
        if result.is_success:
            return self.round_fail('异相仲裁目标画面未建档,到达验证待建档后补')
        return result
