"""光锥叠影 operation(消耗同名光锥副本提升叠影阶)。

交互链(2026-11-10 实机全链摸底,画面机制详见 docs/game/screens/光锥-等级提升.md):
替换列表选中主件 → 右下「强化」→ 光锥-等级提升 → 左列「叠影」TAB → 叠影视图。
材料放置二态机制:点材料槽 → 顶部同名候选行(新获光锥默认锁定);锁定件点击 =
仅预览(右侧开详情面板,「等级」行右侧锁标点击 = 解锁,无二次确认);解锁件
点击 = 置入(候选卡 ⊖ 角标 + 右侧文案「叠影后效果」+ 叠影按钮亮白)。
点「叠影」→「提示」确认弹窗(按钮 y 随文案浮动,区域 OCR 定位)→ 结果横幅
「光锥叠影 叠影X阶➔Y阶」→ 点空白关闭,回叠影视图(槽清空、下阶段阶数更新)。

叠影规则(用户裁定):合成后阶数 = 主件阶数 + 各材料阶数(加法);材料经验
等级不继承。本 op 单次运行 = 置入 material_count 件材料 + 合成一次,多次
提升由调用方重复运行。主件身份在入口按「选中光锥名」OCR 校验,不符显式失败。

⚠️ 不可逆 + 隐式解锁:confirm_merge=True 时真实消耗同名副本;被消耗副本若
处于锁定态会被自动解锁(游戏强制要求,解锁无独立确认)。**调用方发起前必须
向用户说明并获同意**,本 op 不代替调用方做这个确认。

前置:光锥-替换 列表打开且目标主件已选中,或已在 光锥-等级提升(任意子视图);
起点不符显式失败。终点:合成后停在叠影视图(主件阶数已提升)。
"""

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_REPLACE_SCREEN: str = '光锥-替换'
_ASCEND_SCREEN: str = '光锥-等级提升'
# 确认弹窗/结果横幅是全屏模糊覆盖层(父屏锚全糊),拆独立 screen 记 area
_DIALOG_SCREEN: str = '光锥-等级提升-提示弹窗'
_BANNER_SCREEN: str = '光锥-等级提升-叠影结果横幅'
# 主件身份校验的 OCR 相似度下限(全角标点/数字后缀的容差)
_NAME_LCS_RATIO: float = 0.6
# 合成确认弹窗「确认」按钮的区域 OCR 相似度
_CONFIRM_BTN_LCS: float = 0.8


class SuperimposeLightConeOp(SrOperation):
    """对已选中的主件光锥执行一次叠影合成,终点 = 叠影视图(阶数已提升)。

    结果状态:MERGED(合成完成)/ NEED_AUTH(未授权,停在可叠影视图、
    未消耗)/ MAXED_OR_UNKNOWN(叠影视图无「下阶段效果」,满阶或形态未知)/
    失败(入口/选件/材料链路任一步未达成,消息带现场)。

    前置契约见模块 docstring;主件由调用方在替换列表中预先选中。
    """

    def __init__(self, ctx: SrContext, cone_name: str,
                 material_count: int = 1, confirm_merge: bool = False):
        """
        :param ctx: 上下文
        :param cone_name: 主件光锥名(替换列表须已选中该件;用于入口校验,
            防止合错主件——叠影视图本身不显示光锥名)
        :param material_count: 置入材料件数(1 = 阶数 +材料阶;多件 = 一次
            加多阶,>1 为实验路径:候选行多件连放未实测)。上限 4(材料槽数)
        :param confirm_merge: 是否真实执行消耗性合成。False = 走到可叠判定
            即停(不放置材料不消耗);True = 置入材料并点叠影。
            **True 前调用方必须向用户说明并获同意**
        """
        if material_count < 1 or material_count > 4:
            raise ValueError(f'material_count 须在 1~4(材料槽数),实际 {material_count}')
        self.cone_name: str = cone_name
        self.material_count: int = material_count
        self.confirm_merge: bool = confirm_merge
        SrOperation.__init__(self, ctx, op_name=gt('光锥叠影') + f'({cone_name} x{material_count})',
                             node_max_retry_times=20)
        self._placed: int = 0            #: 已置入材料件数(材料放置循环进度)
        self._unlock_attempted: bool = False  #: 当前候选是否已试过解锁路径
        self._banner_seen: bool = False  #: 结果横幅已出现(关闭后凭此判成功)

    #------------------- 识别辅助 -------------------#

    def _selected_cone_matches(self) -> tuple[bool, str]:
        """替换列表右侧「选中光锥名」OCR 与预期主件名比对(LCS 容差)。

        :return: (是否匹配, OCR 原文;OCR 空返回 (False, ''))"""
        area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '读区-选中光锥名')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=self.last_screenshot, rect=area.pc_rect, crop_first=True)
        for r in results:
            text = str(r.data or '').strip()
            if not text:
                continue
            lcs = str_utils.longest_common_subsequence_length(text, self.cone_name)
            if lcs / max(1, len(self.cone_name)) >= _NAME_LCS_RATIO:
                return True, text
            return False, text
        return False, ''

    #------------------- 节点图 -------------------#

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """入口核对:画面 ∈ {替换列表, 等级提升}。

        替换列表须已选中目标主件(OCR 校验)后点「强化」进等级提升;
        已在等级提升(任意子视图)直接进入 TAB 切换。"""
        current = self.check_and_update_current_screen(
            self.last_screenshot, screen_name_list=[_REPLACE_SCREEN, _ASCEND_SCREEN])
        if current == _ASCEND_SCREEN:
            return self.round_success(status='ON_ASCEND')
        if current != _REPLACE_SCREEN:
            return self.round_fail(f'不在替换列表/等级提升(画面判定: {current});'
                                   f'前置:替换列表选中主件,或打开等级提升')
        matched, ocr_text = self._selected_cone_matches()
        if not matched:
            return self.round_fail(f'替换列表选中件不是 {self.cone_name}'
                                   f'(选中光锥名 OCR: "{ocr_text}");先选中正确主件')
        log.info('光锥叠影: 主件校验通过(%s),点强化进等级提升', ocr_text)
        result = self.round_by_find_and_click_area(
            self.last_screenshot, _REPLACE_SCREEN, '按钮-强化',
            until_find_all=[
                (_ASCEND_SCREEN, '标题-光锥详情'),
                (_ASCEND_SCREEN, 'TAB-叠影'),
            ],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )
        if result.is_success:
            return self.round_success(status='ON_ASCEND', wait=1)
        return result

    @node_from(from_name='入口核对', status='ON_ASCEND')
    @operation_node(name='切叠影页', node_max_retry_times=6)
    def open_superimpose_tab(self) -> OperationRoundResult:
        """左列「叠影」TAB → 叠影视图(转移证据 = 「消耗材料」标签出现)。"""
        if self.round_by_find_area(self.last_screenshot,
                                   _ASCEND_SCREEN, '文本-消耗材料').is_success:
            return self.round_success(status='ON_SUPERIMPOSE', wait=0.5)
        result = self.round_by_find_and_click_area(
            self.last_screenshot, _ASCEND_SCREEN, 'TAB-叠影',
            until_find_all=[(_ASCEND_SCREEN, '文本-消耗材料')],
            pre_delay=0.5, success_wait=1.2, retry_wait=2,
        )
        if result.is_success:
            return self.round_success(status='ON_SUPERIMPOSE', wait=0.5)
        return result

    @node_from(from_name='切叠影页', status='ON_SUPERIMPOSE')
    @operation_node(name='可叠判定')
    def check_mergeable(self) -> OperationRoundResult:
        """「下阶段效果」存在 = 可再叠;不存在 = 满阶或形态未知,显式失败。

        confirm_merge=False 到此为止(不放置材料不消耗),NEED_AUTH 交上层
        走授权后重跑。"""
        if self.round_by_find_area(self.last_screenshot,
                                   _ASCEND_SCREEN, '文本-下阶段效果').is_success:
            if not self.confirm_merge:
                return self.round_fail('NEED_AUTH:可叠影,但 confirm_merge=False '
                                       '未授权消耗;授权后重跑(op 不会预放置材料)')
            return self.round_success(status='CAN_MERGE')
        return self.round_fail('MAXED_OR_UNKNOWN:叠影视图无「下阶段效果」'
                               '(已满阶 5,或满阶形态与建档假设不符),不执行合成')

    @node_from(from_name='可叠判定', status='CAN_MERGE')
    @operation_node(name='放置材料', node_max_retry_times=30)
    def place_materials(self) -> OperationRoundResult:
        """逐件放置材料(self._placed 计进度,round_retry 重入推进)。

        每件三步:点槽 → 点候选 → 判置入(未置入 = 锁定件,解锁后重点)。
        候选格序号 = 已置入数 + 1(已置入件带 ⊖ 且不复用)。"""
        idx = self._placed + 1
        screen = self.last_screenshot

        # 置入判定:右侧文案变「叠影后效果」= 第 idx 件已置入
        if self._unlock_attempted and self.round_by_find_area(
                screen, _ASCEND_SCREEN, '文本-叠影后效果').is_success:
            self._placed += 1
            self._unlock_attempted = False
            log.info('光锥叠影: 第 %d 件材料已置入', self._placed)
            if self._placed >= self.material_count:
                return self.round_success(status='PLACED', wait=0.5)
            return self.round_retry('置入完成,继续下一件', wait=1)

        if not self._unlock_attempted:
            # 点槽进入候选选择态 → 点第 idx 个候选
            self.round_by_click_area(_ASCEND_SCREEN, f'材料槽-叠影-{idx}', pre_delay=0.3)
            result = self.round_by_find_and_click_area(
                self.last_screenshot, _ASCEND_SCREEN, f'候选格-{idx}',
                until_find_all=[(_ASCEND_SCREEN, '按钮-当前收起')],
                pre_delay=0.3, success_wait=1, retry_wait=1.5,
            )
            if not result.is_success:
                return result
            self._unlock_attempted = True
            return self.round_retry('候选已点,判置入/解锁', wait=1)

        # 锁定件:点击只开详情预览不置入 → 点详情面板锁标解锁,再重点候选
        log.info('光锥叠影: 第 %d 个候选为锁定件,解锁后重点', idx)
        self.round_by_click_area(_ASCEND_SCREEN, '按钮-解锁详情锁标', pre_delay=0.3)
        self.round_by_click_area(_ASCEND_SCREEN, f'候选格-{idx}', pre_delay=0.3)
        return self.round_retry('解锁完成,重判置入', wait=1)

    @node_from(from_name='放置材料', status='PLACED')
    @operation_node(name='执行合成', node_max_retry_times=20)
    def do_merge(self) -> OperationRoundResult:
        """flat loop:结果横幅 → 关闭收尾;确认弹窗 → 点确认;裸叠影视图 → 点叠影。

        「提示」弹窗按钮 y 随文案浮动(稀有度较高/较低变体),按弹窗区域
        OCR 定位「确认」点击;3 星材料可能无弹窗直达横幅,由分类顺序天然覆盖。"""
        screen = self.last_screenshot

        # ① 结果横幅在 → 点空白关闭
        if self.round_by_find_area(screen, _BANNER_SCREEN, '文本-光锥叠影横幅').is_success:
            self._banner_seen = True
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_BANNER_SCREEN, '区域-结果横幅空白').rect.center)
            return self.round_retry('横幅已点,等关闭', wait=1.5)

        # ② 横幅已出现过且现已消失 = 合成完成收尾
        if self._banner_seen:
            if self.round_by_find_area(screen,
                                       _ASCEND_SCREEN, '文本-下阶段效果').is_success:
                log.info('光锥叠影: 合成完成(%s +%d 件材料),回到叠影视图',
                         self.cone_name, self.material_count)
                return self.round_success(status='MERGED', wait=1)
            return self.round_retry('横幅已关,等叠影视图恢复', wait=1.5)

        # ③ 确认弹窗(区域 OCR 定位「确认」,按钮 y 随文案浮动)
        dialog_area = self.ctx.screen_loader.get_area(_DIALOG_SCREEN, '区域-提示弹窗')
        result = self.round_by_ocr_and_click(screen, '确认', area=dialog_area,
                                             lcs_percent=_CONFIRM_BTN_LCS)
        if result.is_success:
            log.info('光锥叠影: 确认弹窗已确认')
            return self.round_retry('已确认,等结果横幅', wait=2)

        # ④ 裸叠影视图(弹窗未弹/已关) → 点叠影按钮
        if self.round_by_find_area(screen, _ASCEND_SCREEN, '按钮-叠影确认').is_success:
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '按钮-叠影确认').rect.center)
            return self.round_retry('已点叠影,等弹窗/横幅', wait=2)

        return self.round_retry('等待界面反馈', wait=2)
