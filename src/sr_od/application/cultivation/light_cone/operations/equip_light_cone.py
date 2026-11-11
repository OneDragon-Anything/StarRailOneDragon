"""替换光锥 operation(在替换列表画面上为当前角色装备指定光锥)。

角色养成系列的装备线 op:换光锥是配装调整动作(如刷材料前换辅助光锥)。
前置导航(进列表)由 `open_light_cone_replace.OpenLightConeReplaceOp`
承担,本 op 起点单一 = 光锥-替换列表画面,不在则显式失败。
交互链实机摸底:
- 替换界面:9 列卡片网格,分「与角色命途相符 / 不相符」两组;**卡片上
  没有光锥名**(名字仅选中后右侧对比栏可读);
- 选卡后右侧变对比布局(当前装备 → 新选中),底部出现「替换」按钮;
- 点「替换」**直接生效并自动回光锥 TAB,无确认弹窗** —— 替换是即时操作。

识别定位(图标模板的算法边界实测):
- 模板图(``assets/game_data/light_cone_icons``,348×408 斜置卡牌)经
  ``cv2_utils.feature_match`` 特征匹配可直接当模板(透明底合成白底转灰度;
  ``matchTemplate`` 像素比对不可用——重采样渲染差异使分数带重叠);
- 定位用**特征点落格投票**而非 Homography 框:实机卡面是斜置卡牌的中心
  裁剪构图,Homography 估计会被拉偏(实测偏差可达 120px);逐匹配点按
  「x 落列带 + y 聚簇(间隔 >100px 分行)」投票,目标卡格得票显著最高
  (实机 15:2 / 9:2),取最高票簇中心吸附列中心点击;
- 未命中滚动一屏重扫(拖拽,有界);滚动按下点必须锚在卡片内容上 —— 按在
  列表边缘/组头等空白带手势被游戏无视(实机对照实验 A/B/D);OCR 验证用
  右侧对比栏读区(名带形近变体,如「於/于」,fuzzy 匹配兜底)。

前置:光锥-替换列表(OpenLightConeReplaceOp 保证);起点不符显式失败。
⚠️ 装备即改变角色配装(即时生效),调用方须确认目标光锥正确;
allow_take_over=True 会抢走他人装备,须用户明确授权。
已知边界:「光锥建议排序」开着时,装备变化会触发列表实时重排 —— 刚完成
一次替换立刻再换下一把,重排动画期 SIFT 全部漏扫(实机复现:连续两次
换装第二次滚满预算判停),重跑即愈;调用方连续换装时在两次 op 之间留
数秒间隔或失败重试一次。
"""



from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen import screen_utils
from one_dragon.base.screen.screen_utils import FindAreaResultEnum
from one_dragon.utils import str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.equip_list_recognizer import LightConeReplaceRecognizer
from sr_od.operations.sr_operation import SrOperation

_LC_TAB_SCREEN: str = '角色-光锥'
_REPLACE_SCREEN: str = '光锥-替换'
# 画面级判定的判定范围(只判相关屏):画面判定一律用画面级,禁单区域命中当
# 画面判定 —— 两屏左上角标题「角色光锥 / 光锥替换」同位形近,单区域 OCR
# 相似度可互判命中,导致未点按钮即认定已在目标画面
_ENTRY_SCREENS: list[str] = [_LC_TAB_SCREEN, _REPLACE_SCREEN]

# 网格几何:9 列,实机卡列首中心 = 列表区 x1+72.5、列距恒 139px(锚点卡实测);
# 行位置随滚动变化,不预设行带 —— 由特征点 y 聚簇动态获得(见 grid_template_locate)
# 注:9 等分推导的列距 147.2 与实机 139 不符,误差随列号线性增长至末列 +68px
# (点击落卡右缘),已废弃。
_GRID_COLS: int = 9
# 每屏扫描的滚动拖拽总幅度:约 2 行卡位,避免跳行
_SCROLL_DRAG_PX: int = 300
# 滚动扫描的屏幕数上限(全列表多屏,防无限滚)
_SCAN_MAX_SCREENS: int = 12
# 验证选中连续不符次数达此值 → 转回重新定位(点击未生效/误配自愈)
_RESELECT_AFTER: int = 3
# 滚回列表顶:固定次数快速大范围拖拽(短 duration 甩动带惯性,单次位移≈
# 拖距 800px;光锥全列表实测总深 6000px+,10 次覆盖到顶有余量;顶部态的
# 多余拖拽被列表回弹吞掉,无害)—— 按 AGENTS §3 回顶规范,不做逐屏识别
# 判顶,识别留给后续扫描自然从顶部开始。
_RESET_TOP_DRAGS: int = 10
# 回顶拖拽几何:起点 y=50(上方窗口内)、终点 y=850(底部卡行带内)——
# 手指下滑 = 内容回卷露出顶部(标准触摸语义,drag_to 终点在前);
# 上滑 800px 的反向手势会向列表深处翻页,方向勿倒置。
_TOP_DRAG_END_Y: int = 850
_TOP_DRAG_PX: int = 800
_TOP_DRAG_DURATION: float = 0.2

# 滚动拖拽的按下锚点(y):实机对照实验(A/B/D 三组)证明拖拽手势只有在按下点
# 落在卡片内容上才被游戏识别 —— 按在列表边缘/组头等空白带会被无视(列表不动);
# 620 取卡行带(543-698)中心,列表在任意滚动位置时该 y 都大概率落在某行卡上,
# 即使偶发落空,判顶循环的「下一轮重判」会自然重试。
_DRAG_ANCHOR_Y: int = 620

# 首卡中心相对列表区 x1 的偏移 = 首卡 x1 偏移(3) + 半卡宽(69.5)
_CONE_FIRST_CENTER_OFFSET: float = 72.5
_CONE_COL_PITCH: float = 139.0


def _cone_col_centers(list_rect: Rect) -> list[float]:
    """列中心 = 首卡中心 + 139px 等距(实测列距恒定,与锚点卡矩形同源)。"""
    first_center = list_rect.x1 + _CONE_FIRST_CENTER_OFFSET
    return [first_center + _CONE_COL_PITCH * i for i in range(_GRID_COLS)]


class EquipLightConeOp(SrOperation):
    """在替换列表画面上为当前角色装备指定光锥,终点 = 光锥 TAB(读区已显示
    目标光锥;点「替换」后游戏自动回 TAB)。

    结果状态:ALREADY_EQUIPPED(目标已装备当前角色,幂等成功)/
    LIGHT_CONE_EQUIPPED(替换完成)。
    失败:不在替换列表画面 / 列表扫完未找到(未拥有或识别失败)/ 仅见被
    占用件(默认不抢语义,allow_take_over=True 可占用)。
    ⚠️ 替换即时生效,调用方须确认目标光锥正确;allow_take_over=True 会
    抢走他人装备改变其配装,须用户明确授权。
    """

    def __init__(self, ctx: SrContext, cone_name: str,
                 rank: int | None = None, level: int | None = None,
                 allow_take_over: bool = False):
        """
        :param ctx: 上下文
        :param cone_name: 目标光锥全名(如「行于流逝的岸」;须与光锥列表显示名
            一致)
        :param rank: 叠影数过滤(1-5,可选)——同名多副本时精确定位
        :param level: 等级过滤(1-80,可选)——进一步收窄候选
        :param allow_take_over: 允许占用他人已装备的件;False(默认)= 只装
            未装备件,目标全部被占用 → 显式失败;True 须用户明确授权
        """
        if rank is not None and not 1 <= rank <= 5:
            raise ValueError(f'rank {rank} 超出 1-5')
        if level is not None and not 1 <= level <= 80:
            raise ValueError(f'level {level} 超出 1-80')
        self.cone_name: str = cone_name
        self.rank: int | None = rank   #: 叠影过滤,None=不过滤
        self.level: int | None = level  #: 等级过滤,None=不过滤
        self.allow_take_over: bool = allow_take_over  #: 是否允许占用他人装备
        self._scan_screens: int = 0   #: 已扫描的屏幕数(滚动预算)
        self._candidate_idx: int = 0  #: 当前屏候选游标(点击验证失败后推进到下一候选)
        self._select_retries: int = 0  #: 验证选中连续不符次数(达阈值转回下一候选)
        self._seen_owned_match: bool = False  #: 扫描中见过符合过滤条件但被占用的件(失败信息依据)
        SrOperation.__init__(self, ctx, op_name=gt('替换光锥') + f'({cone_name})',
                             node_max_retry_times=24)

    #------------------- 识别辅助 -------------------#

    def _drag_scroll(self, toward_top: bool) -> None:
        """执行一次列表滚动拖拽(总幅 300px,按下点锚在卡片行内)。

        drag_to 参数序为 (end, start) —— 终点在前;向下翻页 = 手指上滑
        (终点在上),向顶部回卷 = 手指下滑(终点在下)。按下点必须在卡片
        内容上,手势才被游戏识别(见 _DRAG_ANCHOR_Y 注)。"""
        list_area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '区域-光锥列表')
        anchor_x = list_area.rect.center.x
        half = _SCROLL_DRAG_PX // 2
        if toward_top:
            self.ctx.controller.drag_to(
                Point(anchor_x, _DRAG_ANCHOR_Y + half), Point(anchor_x, _DRAG_ANCHOR_Y - half))
        else:
            self.ctx.controller.drag_to(
                Point(anchor_x, _DRAG_ANCHOR_Y - half), Point(anchor_x, _DRAG_ANCHOR_Y + half))

    def _read_name(self, screen_name: str, area_name: str) -> str | None:
        """OCR 读指定画面的名字读区,返回最相似的目标名判定由调用方做。"""
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        texts = [str(r.data) for r in results]
        idx = str_utils.find_in_list_with_fuzzy(self.cone_name, texts, cutoff=0.6)
        return texts[idx] if idx is not None else None

    #------------------- 节点图 -------------------#

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """入口核对:画面级判定在替换列表画面;目标已装备直接幂等成功。

        判定走画面级 id_mark 组合(见 _ENTRY_SCREENS 注):单区域命中在
        标题同位形近的场景不可靠。"""
        current = self.check_and_update_current_screen(
            self.last_screenshot, screen_name_list=[_REPLACE_SCREEN])
        if current != _REPLACE_SCREEN:
            return self.round_fail(f'不在替换列表画面(当前画面判定: {current});'
                                   f'先调 OpenLightConeReplaceOp 打开列表')
        # 幂等检查:未选卡时左栏显示当前装备——目标已装备当前角色直接成功,
        # 不被「不抢」语义排除
        if self._read_name(_REPLACE_SCREEN, '读区-当前光锥名') is not None:
            log.info('替换光锥: %s 已装备当前角色', self.cone_name)
            return self.round_success(status='ALREADY_EQUIPPED')
        return self.round_success(status='IN_REPLACE_SCREEN')

    @node_from(from_name='入口核对', status='ALREADY_EQUIPPED')
    @operation_node(name='已装备收尾')
    def already_equipped(self) -> OperationRoundResult:
        return self.round_success(status='ALREADY_EQUIPPED')

    @node_from(from_name='入口核对', status='IN_REPLACE_SCREEN')
    @operation_node(name='滚回列表顶部')
    def reset_to_top(self) -> OperationRoundResult:
        """滚回列表顶部:固定 5 次快速大范围拖拽(短 duration),不识别判顶。

        列表已在顶部时多余拖拽被回弹吞掉,无害;滚顶是否到位由后续扫描的
        识别结果兜底 —— 目标在前几屏却漏扫即滚顶不足,失败信息可定位。"""
        list_area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '区域-光锥列表')
        anchor_x = list_area.rect.center.x
        for _ in range(_RESET_TOP_DRAGS):
            self.ctx.controller.drag_to(
                Point(anchor_x, _TOP_DRAG_END_Y),
                Point(anchor_x, _TOP_DRAG_END_Y - _TOP_DRAG_PX),
                duration=_TOP_DRAG_DURATION)
        return self.round_success(status='AT_TOP', wait=0.5)

    @node_from(from_name='滚回列表顶部', status='AT_TOP')
    @node_from(from_name='验证选中', status='RESELECT')  # 选中验证连续不符 → 回退点下一个候选
    @operation_node(name='定位并选卡', node_max_retry_times=30)
    def find_and_select(self) -> OperationRoundResult:
        """SIFT 落格投票定位目标卡候选序列 → 逐个点击;屏内候选耗尽滚动重扫。

        候选按票降序 = 未被头像角标遮挡(未被装备)的件优先 —— 多件同名副本
        场景下避免抢走他人装备的件(见 grid_template_locate 模块 docstring)。
        每轮开头画面级判定:拖拽/误触退出列表立刻显式失败(重新打开后再调)。"""
        current = self.check_and_update_current_screen(
            self.last_screenshot, screen_name_list=[_REPLACE_SCREEN])
        if current != _REPLACE_SCREEN:
            return self.round_fail(f'替换列表已退出(当前画面判定: {current});'
                                   f'重新打开列表后再调用本 op')

        if self._scan_screens >= _SCAN_MAX_SCREENS:
            if self._seen_owned_match and not self.allow_take_over:
                return self.round_fail(f'滚动 {_SCAN_MAX_SCREENS} 屏,{self.cone_name} '
                                       f'仅见已被装备的件(allow_take_over=True 可占用)')
            return self.round_fail(f'滚动 {_SCAN_MAX_SCREENS} 屏未找到 {self.cone_name}'
                                   f'(未拥有或识别失败)')

        screen_img = self.screenshot()
        screen_info = self.ctx.screen_loader.get_screen(_REPLACE_SCREEN)
        out = LightConeReplaceRecognizer().recognize(self.ctx, screen_img, screen_info)
        items = (out or {}).get('items') or []
        cands = self._filter_candidates(items)
        if cands:
            log.info('替换光锥: 本屏命中 %d 件 %s(第 %d 屏)',
                     len(cands), [(it['cell'][0], it.get('owner'), it.get('rank'))
                                  for it in cands], self._scan_screens + 1)
        if self._candidate_idx >= len(cands):
            # 本屏候选耗尽(或整屏未命中) → 滚动下一屏
            self._drag_scroll(toward_top=False)
            self._scan_screens += 1
            self._candidate_idx = 0
            return self.round_retry('当前屏候选耗尽,滚动一屏重扫', wait=1)

        cand = cands[self._candidate_idx]
        cell = Rect(*cand['cell'])
        self.ctx.controller.click(cell.center)
        self._candidate_idx += 1
        self._select_retries = 0  # 重新点击后重置验证计数
        log.info('替换光锥: 点击候选 %d/%d rank=%s level=%s',
                 self._candidate_idx, len(cands), cand.get('rank'), cand.get('level'))
        return self.round_success(status='CLICKED', wait=1.2)

    def _filter_candidates(self, items: list[dict]) -> list[dict]:
        """识别清单 → 按入参过滤候选:名字必匹配;rank/level **读出且不符**
        才排除(逐卡 rank 靠 OCR,滚动扫描中部分帧读不出=未知——未知件保留
        但排在「确认匹配」件之后兜底);allow_take_over=False 时被占用件
        (owner≠None)整体排除——「尝试换但不抢」语义,True 时未装备件优先、
        已装备件兜底。"""
        cands = []
        for it in items:
            if it.get('cone') != self.cone_name:
                continue
            rank, level = it.get('rank'), it.get('level')
            if ((self.rank is not None and rank is not None and rank != self.rank)
                    or (self.level is not None and level is not None and level != self.level)):
                continue  # 明确不符
            if it.get('owner') is not None:
                self._seen_owned_match = True  # 符合过滤条件但被占用(ALL_OWNED 失败信息依据)
                if not self.allow_take_over:
                    continue
            known = ((self.rank is None or rank == self.rank)
                     and (self.level is None or level == self.level))
            cands.append((0 if known else 1, 0 if it.get('owner') is None else 1, it))
        cands.sort(key=lambda t: (t[0], t[1]))
        return [it for _k, _o, it in cands]

    @node_from(from_name='定位并选卡', status='CLICKED')
    @operation_node(name='验证选中', node_max_retry_times=10)
    def verify_selected(self) -> OperationRoundResult:
        """OCR 右侧对比栏选中名,与目标名 fuzzy 匹配(名带形近变体)。

        连续多次不符 = 点击未选中目标卡(定位误配或点击未生效),
        转回重新定位;立即重读等待对比栏刷新。"""
        if self._read_name(_REPLACE_SCREEN, '读区-选中光锥名') is not None:
            return self.round_success(status='SELECTED_MATCHED')
        self._select_retries += 1
        if self._select_retries >= _RESELECT_AFTER:
            return self.round_success(status='RESELECT')
        return self.round_retry('选中名与目标不符,重读', wait=1)

    @node_from(from_name='验证选中', status='SELECTED_MATCHED')
    @operation_node(name='确认替换', node_max_retry_times=6)
    def confirm_replace(self) -> OperationRoundResult:
        """画面级判定:已回 TAB 即替换生效;仍在替换界面则点「替换」按钮。

        点「替换」直接生效并自动回光锥 TAB,无确认弹窗;画面转移由下轮
        画面判定确认(直到判定为 TAB 才算替换完成)。"""
        current = self.check_and_update_current_screen(
            self.last_screenshot, screen_name_list=_ENTRY_SCREENS)
        if current == _LC_TAB_SCREEN:
            return self.round_success(status='BACK_TO_TAB')
        if current != _REPLACE_SCREEN:
            return self.round_fail(f'异常画面,无法确认替换(当前画面判定: {current})')
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _REPLACE_SCREEN, '按钮-替换') != FindAreaResultEnum.TRUE:
            return self.round_retry('未找到替换按钮', wait=2)
        self.ctx.controller.click(
            self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '按钮-替换').rect.center)
        return self.round_retry('已点击替换,等待回到光锥 TAB', wait=2)

    @node_from(from_name='确认替换')
    @operation_node(name='结果核对')
    def verify_result(self) -> OperationRoundResult:
        """回 TAB 后读光锥名读区做最终核对。"""
        if self._read_name(_LC_TAB_SCREEN, '读区-光锥名') is not None:
            log.info('替换光锥: %s 已装备当前角色', self.cone_name)
            return self.round_success(status='LIGHT_CONE_EQUIPPED', wait=0.5)
        return self.round_fail('替换后光锥名读区与目标不符(识别失败或替换未生效)')
