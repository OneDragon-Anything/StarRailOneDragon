"""跃迁页状态读取 op —— 导航到跃迁页,读当前池名/池类型/星琼/票数,零消耗。

职责:任意画面起点 → 跃迁页 → 读右上货币栏与左上池名 → 可选回大世界收摊。
纯观察类:不触碰「跃迁1次/跃迁10次」消耗控件(抽卡属高消耗决策,bot 永不
代点,见 skills/sr-od-game-consume 消耗红线)。

画面事实(建档见 ``docs/game/screens/跃迁.md``,2026-11-12 六池实机走查):
- 当前池名在左上固定位置(文本-当前池名 100,30-480,100),卡池列表数量随
  版本变,但池名/标签/货币栏位置固定 —— 池子数量不定不影响本 op 读数;
- 标签区(330,170-530,212)文本即池类型:「角色活动跃迁」/「光锥活动跃迁」/
  「XX联动跃迁」/「常驻跃迁」;
- 货币栏两种形态:活动池 = 跃迁进度(N/3200,万象和鸣入口) + 专票数量 +
  星琼数量;常驻池 = 星票数量 + 星琼数量(无进度条)。两种形态由池类型分流
  读取,不在错误形态下读另一个 area(活动池态下星票 area 会扫到专票数字
  左半,读了必错);
- 联动池(Fate[UBW]联动跃迁)票种与角色池同(星轨专票),归活动池读法。
"""

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils, str_utils
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state.common_screen_state import is_normal_in_world

_WARP_SCREEN: str = '跃迁'
_NORMAL_WORLD: str = '大世界-普通'

POOL_TYPE_CHARACTER: str = 'character'
"""角色活动跃迁(含联动池之外的活动角色池)"""
POOL_TYPE_CONE: str = 'cone'
"""光锥活动跃迁"""
POOL_TYPE_COLLAB: str = 'collab'
"""联动跃迁(如 Fate[UBW];票种与角色池同,读法同活动池)"""
POOL_TYPE_REGULAR: str = 'regular'
"""常驻跃迁(官方英文 Regular Warp,池名 Stellar Warp;星票;无标签时不能直接
判常驻,须读到标签文本)"""
POOL_TYPE_UNKNOWN: str = 'unknown'
"""标签区无可识别文本(画面未加载完成/新池型)"""

_AREA_POOL_NAME: str = '文本-当前池名'
_AREA_POOL_LABEL: str = '文本-角色活动跃迁标签'
_AREA_JADE: str = '货币-星琼数量'
_AREA_SPECIAL_PASS: str = '货币-星轨专票数量'
_AREA_RAIL_PASS: str = '货币-星票数量'
_AREA_PROGRESS: str = '货币-跃迁进度'

_COUNT_OCR_SCALE: float = 3.0
"""数量型 area 的 OCR 放大倍数——单字符数字在原始分辨率下检出失败,3 倍实测可读(2 倍无效)"""

# 标签文本 → 池类型:按关键子串匹配(OCR 对 Fate[UBW] 前缀可能乱码,子串稳)
_LABEL_KEYWORDS: list[tuple[str, str]] = [
    ('角色活动跃迁', POOL_TYPE_CHARACTER),
    ('光锥活动跃迁', POOL_TYPE_CONE),
    ('联动跃迁', POOL_TYPE_COLLAB),
    ('常驻跃迁', POOL_TYPE_REGULAR),
]


def parse_pool_type(label_text: str | None) -> str:
    """标签区 OCR 文本 → 池类型常量。

    :param label_text: 标签区 OCR 原文(可能为 None = area 无文本)
    :return: POOL_TYPE_* 常量;无可识别关键词返回 unknown
    """
    if not label_text:
        return POOL_TYPE_UNKNOWN
    for keyword, pool_type in _LABEL_KEYWORDS:
        if keyword in label_text:
            return pool_type
    return POOL_TYPE_UNKNOWN


def parse_count(text: str | None) -> int | None:
    """货币数量区 OCR 文本 → 非负整数;无数字返回 None。

    OCR 常见噪声:星琼数量尾部混入「+」(充值按钮)、专票票面反光产生杂字符。
    """
    if not text:
        return None
    return str_utils.get_positive_digits(text, err=None)


def parse_progress(text: str | None) -> str | None:
    """跃迁进度区 OCR 文本 → 「N/M」原样(N/M 是万象和鸣活动进度,非纯数字)。

    空文本(常驻池无进度条)返回 None。
    """
    if not text:
        return None
    cleaned = text.strip()
    return cleaned if '/' in cleaned else None


def _area_text(ctx: SrContext, screen, screen_name: str, area_name: str) -> str | None:
    """读画面建档 area 内的 OCR 文本(空 = None)。

    多行结果按识别序拼接(左上池名分两行「跃迁」/「愚戏众星」,只取首条会丢池名)。
    """
    area = ctx.screen_loader.get_area(screen_name, area_name)
    ocr_result_list = ctx.ocr_service.get_ocr_result_list(screen, rect=area.rect)
    if len(ocr_result_list) == 0:
        return None
    return ''.join(result.data for result in ocr_result_list)


def _area_count_text(ctx: SrContext, screen, screen_name: str, area_name: str) -> str | None:
    """读数量型 area(纯数字):两层取数——全图 OCR+rect 过滤 → 3 倍放大裁剪 OCR 兜底。

    引擎边界(实测):det 对孤立单字符(个位数票数如「7」)在全图检出漏检,
    裁剪小图的 det 响应又随输入尺寸浮动——两种路径互补,先走稳定路径
    (全图过滤,多位数恒定),null 再走放大兜底(个位数部分检出,3 倍实测
    优于 2 倍);仍 None 由调用方容错(读数 null 不阻塞,精确值以游戏内为准)。
    """
    area = ctx.screen_loader.get_area(screen_name, area_name)
    ocr_result_list = ctx.ocr_service.get_ocr_result_list(screen, rect=area.rect)
    if len(ocr_result_list) > 0:
        return ''.join(result.data for result in ocr_result_list)
    cropped = cv2_utils.crop_image_only(screen, area.rect)
    big = cv2_utils.scale_image(cropped, scale=_COUNT_OCR_SCALE)
    raw = ctx.ocr.run_ocr(big)
    if len(raw) == 0:
        return None
    return ''.join(raw.keys())


class ReadWarpStatusOp(SrOperation):
    """导航到跃迁页并读取抽卡资产状态(池名/池类型/星琼/专票/星票/进度),
    可选回大世界收摊,结果经运行结果 data 返回。
    起点:任意可控画面;终点:大世界(back_to_world=True)/跃迁页(False)。
    消耗:零 —— 只读不点消耗控件(高消耗画面下的零消耗承诺)。

    结果状态:
    - ``WARP_STATUS``:读数完成,``OperationResult.data`` 携带:
      ``pool_name``(左上全名,如「跃迁 愚戏众星」)/ ``pool_type``
      (POOL_TYPE_* 常量)/ ``stellar_jade``(星琼)/ ``special_pass``
      (星轨专票,活动池,官方英文 Star Rail Special Pass)/ ``rail_pass``
      (星轨通票,常驻池,官方英文 Star Rail Pass)/ ``warp_progress``
      (「N/M」万象和鸣进度,活动池;None = 无);
    失败:画面无法到达跃迁页、跃迁页货币区读数全空(画面异常)。
    消耗:零 —— 本 op 只读不点消耗控件。
    """

    def __init__(self, ctx: SrContext, back_to_world: bool = True):
        """
        :param ctx: 上下文
        :param back_to_world: 读完是否点关闭回大世界(True = 收摊干净交接;
            连续读数场景可传 False 留在跃迁页)
        """
        self._back_to_world: bool = back_to_world
        self._status_data: dict[str, str | int | None] | None = None
        """读池与货币节点的结果(终点「回大世界」节点透传给 OperationResult.data)"""
        SrOperation.__init__(self, ctx, op_name=gt('读取跃迁状态'),
                             node_max_retry_times=20)

    @operation_node(name='前往跃迁页', is_start_node=True)
    def go_to_warp(self) -> OperationRoundResult:
        """画面分发:跃迁页(画面级判定)→ 读数;大世界 → 点跃迁入口;其他 → 回大世界重判。

        大世界判定不用画面级:大世界/大世界-普通均无 id_mark,check_and_update
        限定列表对无锚屏恒 None —— 用惯例函数 is_normal_in_world(角色图标 area,
        与 BackToNormalWorldPlus 同款);goto 也不可用(其内部全库精准匹配认不出
        无锚起点),改直接点「按钮-跃迁」(area.pc_alt 自动处理锁光标)+until
        验证到跃迁页。回大世界分支必须 retry 重入本节点 —— 子 op 成功转
        round_success 后无匹配出边,op 提前终结(2026-11-12 实测)。
        """
        if self.check_and_update_current_screen(
                screen_name_list=[_WARP_SCREEN]) == _WARP_SCREEN:
            return self.round_success(status='AT_WARP', wait=0.5)
        if is_normal_in_world(self.ctx, self.last_screenshot):
            return self.round_by_find_and_click_area(
                self.last_screenshot, _NORMAL_WORLD, '按钮-跃迁',
                until_find_all=[(_WARP_SCREEN, '文本-查看详情')],
                success_wait=2, retry_wait=2)
        op = BackToNormalWorldPlus(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_retry('已回大世界,重新判定画面', wait=1)
        return self.round_fail(f'回大世界失败: {op_result.status}')

    @node_from(from_name='前往跃迁页', status='AT_WARP')
    @operation_node(name='读池与货币')
    def read_status(self) -> OperationRoundResult:
        """读左上池名/标签区池类型/货币栏数量,组装结果 data。

        票数按池类型分流读(见模块 docstring 两种货币栏形态);星琼两形态
        同位。标签区读不出文本时 fail(防把加载中误判成常驻池)。
        """
        screen = self.last_screenshot
        pool_name = _area_text(self.ctx, screen, _WARP_SCREEN, _AREA_POOL_NAME)
        label_text = _area_text(self.ctx, screen, _WARP_SCREEN, _AREA_POOL_LABEL)
        pool_type = parse_pool_type(label_text)
        if pool_type == POOL_TYPE_UNKNOWN:
            return self.round_retry('标签区无可识别文本(画面未加载完成?),等待重试', wait=1.5)

        jade = parse_count(_area_count_text(self.ctx, screen, _WARP_SCREEN, _AREA_JADE))
        if jade is None:
            return self.round_retry('星琼数量读数失败(货币区未加载完成?),等待重试', wait=1.5)

        special_pass: int | None = None
        rail_pass: int | None = None
        progress: str | None = None
        if pool_type == POOL_TYPE_REGULAR:
            rail_pass = parse_count(
                _area_count_text(self.ctx, screen, _WARP_SCREEN, _AREA_RAIL_PASS))
        else:
            special_pass = parse_count(
                _area_count_text(self.ctx, screen, _WARP_SCREEN, _AREA_SPECIAL_PASS))
            progress = parse_progress(
                _area_text(self.ctx, screen, _WARP_SCREEN, _AREA_PROGRESS))

        data: dict[str, str | int | None] = {
            'pool_name': pool_name,
            'pool_type': pool_type,
            'stellar_jade': jade,
            'special_pass': special_pass,
            'rail_pass': rail_pass,
            'warp_progress': progress,
        }
        # 终点节点(回大世界)的 round 结果才是 OperationResult 的数据源,
        # 读数 data 存成员变量供其透传(终点 round_success 不带 data = 调用方拿到 null)
        self._status_data = data
        return self.round_success(status='WARP_STATUS', data=data, wait=0.5)

    @node_from(from_name='读池与货币', status='WARP_STATUS')
    @operation_node(name='回大世界')
    def back_to_world(self) -> OperationRoundResult:
        """点跃迁页右上关闭回大世界(back_to_world=False 时跳过,留在跃迁页)。

        until 用大世界角色图标验证转移:点了 ≠ 关掉了,防止在错误画面交接。
        本节点是终点,读数 data 在此透传给 OperationResult。
        """
        if not self._back_to_world:
            return self.round_success(status='STAY_WARP', data=self._status_data, wait=0.5)
        result = self.round_by_find_and_click_area(
            self.last_screenshot, _WARP_SCREEN, '按钮-关闭',
            until_find_all=[(_NORMAL_WORLD, '右上图标-角色详情')],
            success_wait=1.5, retry_wait=1.5)
        if result.is_success:
            # find_and_click 自己的结果不带读数 data,终点在此透传
            return self.round_success(status=result.status, data=self._status_data, wait=0.5)
        return result
