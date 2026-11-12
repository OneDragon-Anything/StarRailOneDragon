import time

from cv2.typing import MatLike
from typing import ClassVar

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.context.sr_pc_controller import SrPcController
from sr_od.operations.interact import interact_utils
from sr_od.operations.sr_operation import SrOperation


class MoveInteract(SrOperation):
    """在大世界与指定交互点(人物/点位)交互:按交互按钮文字定位,按钮未出现时
    小步挪动绕圈触发交互,直到交互成功或挪动序列耗尽失败。
    起点:大世界(交互点附近);终点:大世界(交互已触发,可能进入对话/传送等后续画面)。
    """

    TRY_INTERACT_MOVE: ClassVar[str] = 'sssaaawwwdddsssdddwwwaaawwwaaasssdddwwwdddsssaaa'  # 分别往四个方向绕圈 走过的情况
    TRY_INTERACT_MOVE_2: ClassVar[str] = 'wwwaaasssdddwwwdddsssaaasssaaawwwdddsssdddwwwaaa'  # 分别往四个方向绕圈 走不到的情况

    def __init__(
        self,
        ctx: SrContext,
        cn: str,
        lcs_percent: float = -1,
        single_line: bool = False,
        no_move: bool = False,
        possible_ahead: bool = True,
    ):
        """
        :param ctx: 上下文
        :param cn: 交互按钮的中文文案(如「交谈」「进入」)
        :param lcs_percent: OCR 匹配阈值,-1 用交互工具默认值
        :param single_line: 确认交互文案只有一行时可缩小识别范围
        :param no_move: 不挪动触发交互(确信已站在交互点时用,如体力本/模拟宇宙事件点)
        :param possible_ahead: 可能已走过交互点(锄大地疾跑易走过)与走不到(无坐标事件)
            两种情况使用不同的绕圈序列
        """
        SrOperation.__init__(self, ctx, op_name=gt('交互 %s') % gt(cn))
        self.cn: str = cn
        self.lcs_percent: float = lcs_percent
        self.single_line: bool = single_line
        self.no_move: bool = no_move
        self.possible_ahead: bool = possible_ahead

        self.move_idx: int = 0

    @operation_node(name='画面识别', is_start_node=True, screenshot_before_round=False)
    def check_screen(self) -> OperationRoundResult:
        """
        在屏幕上找到交互内容进行交互
        :return: 操作结果
        """
        time.sleep(0.5)  # 稍微等待一下 可能交互按钮还没有出来

        screen = self.screenshot()
        word_pos = interact_utils.check_move_interact(self.ctx, screen, self.cn,
                                                      single_line=self.single_line,
                                                      lcs_percent=self.lcs_percent)

        if word_pos is None:  # 目前没有交互按钮 尝试挪动触发交互
            if not self.no_move and self.move_idx < len(MoveInteract.TRY_INTERACT_MOVE):
                if self.possible_ahead:
                    d = MoveInteract.TRY_INTERACT_MOVE[self.move_idx]
                else:
                    d = MoveInteract.TRY_INTERACT_MOVE_2[self.move_idx]
                self.ctx.controller.move(d)  # 不需要时间 相当于点按 小小移动一步
                self.move_idx += 1
                return self.round_wait()
            else:
                return self.round_fail()
        else:
            if self.ctx.controller.interact(word_pos.center,
                                            SrPcController.MOVE_INTERACT_TYPE):
                return self.round_success()

        return self.round_wait()