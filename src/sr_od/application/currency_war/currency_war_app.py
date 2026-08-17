# 已 live 验(整局跑通多场 D-74~D-79 + 2026-08-12:EnterCW→StartMatch→RunLoop→结算→lobby 全 lifecycle 自主;_in_match resume 多锚含战斗/挑战成功/挑战结束,中间态接手不卡 entry)

from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.application.currency_war import currency_war_const
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.currency_war_run_record import CurrencyWarRunRecord
from sr_od.application.currency_war.operations.battle_loop import CurrencyWarRunLoop
from sr_od.application.currency_war.operations.entry.enter_currency_war import (
    EnterCurrencyWar,
)
from sr_od.application.currency_war.operations.entry.start_currency_war_match import (
    StartCurrencyWarMatch,
)
from sr_od.application.sr_application import SrApplication
from sr_od.context.sr_context import SrContext


class CurrencyWarApp(SrApplication):
    """货币战争应用。纯代码自主打完整局(无 LLM,实机验证):

    大世界 → 货币战争大厅(`EnterCurrencyWar`)→ 开始对局到备战(`StartCurrencyWarMatch`)
    → 对局循环到结束(`CurrencyWarRunLoop`:备战 买/升等级/deploy/出战 + 多类事件 + 结算回大厅)。

    **中间态接手(,2026-08-04)**:app 不再总从大世界线性起 —— 各入口 op 先检测当前态,
    已在 CW(大厅/对局中)就跳过 enter/start、直接进 loop。故 bot crash/重启/手动接管后,
    从任何态(大世界 / 大厅 / 备战 / 事件 / 战斗 / 结算)重跑 app 都能 resume,不卡 entry。

    naive 策略 + 购买经验升等级,实测赢下位面 1、打完整两位面局(输位面 2 boss)。
    打赢更高难度需 Strategy 精修(羁绊/经济/deploy 智能化,见 design.md)。
    """

    STATUS_AT_LOBBY: ClassVar[str] = EnterCurrencyWar.STATUS_AT_LOBBY

    # 对局中态 OCR 锚点(备战 / 事件 overlay / 战斗 / 结算)—— 命中任一 = 已在对局里,跳过 enter+start
    _IN_MATCH_KEYWORDS: ClassVar[tuple[str, ...]] = (
        '购买经验', '备战阶段', '投资策略', '投资环境', '补给阶段',
        '遭遇其一', '盛会之星', '出战', '挑战结束', '挑战成功', '请选择投资',
        '总伤害', '敌方行动中', '我方行动中',  # 战斗屏(对局中,防 _in_match 漏判 → 重进大厅卡,2026-08-12)
        '简易武装箱',  # 节点武装箱弹窗(盖底层屏,OCR 只见弹窗文字;M19 停机重启曾漏判 → 误走 enter 链「返回普通大世界」连点关掉弹窗,2026-08-15)
        '星徽秘典', '返回投资策略选择',   # 星徽秘典道具详情弹窗(盖投资策略/备战,M34 实锤:OCR 只见弹窗文字 → _in_match 漏判 → enter 链循环点右上角[overlay 的返回位]8min);返回投资策略选择=备战屏对局中独有右上按钮
        '挑战失败',   # 挑战失败终局结算屏(对局评价/下一步;M42 实锤 2026-08-16:M41 战败后 app 重启,_in_match 漏判 → 误走 enter 链「返回普通大世界」循环点右上角;loop 3b「返回货币战争」同收局)
    )

    # ⚖️ 治本(2026-08-17,M19/M34/M42 关键词补丁链的结构替代):对局中态检测升级为
    # **screen_info 画面匹配**(货币战争- 前缀 − 大厅态白名单)——新对局画面建档即自动生效,
    # 不再靠事后补关键词(每漏一个新屏 = enter 链「返回普通大世界」死循环 ~8min)。
    # 关键词保留为 fallback(id_mark 未全中的半开/过渡帧)。
    _CW_PREFIX: ClassVar[str] = '货币战争-'
    _LOBBY_STATE_SCREENS: ClassVar[frozenset[str]] = frozenset({
        '货币战争-大厅', '货币战争-模式选择',
        '货币战争-攻略列表', '货币战争-攻略详情', '货币战争-攻略图例',
        '货币战争-攻略码输入弹窗', '货币战争-保存阵容弹窗',
        '货币战争-装备追踪弹窗', '货币战争-阵容编辑',
    })

    @classmethod
    def in_match_screen_names(cls, screen_info_list) -> list[str]:
        """对局中态屏名(screen_info 全集过滤:货币战争- 前缀 − 大厅态白名单)。

        module 级可测;新对局画面建档(命名带前缀)自动进列表——M54 类
        「新屏漏判 → enter 链死循环」结构性消除。
        """
        return [si.screen_name for si in screen_info_list
                if si.screen_name.startswith(cls._CW_PREFIX)
                and si.screen_name not in cls._LOBBY_STATE_SCREENS]

    def __init__(self, ctx: SrContext):
        SrApplication.__init__(
            self, ctx, currency_war_const.APP_ID,
            op_name=gt('货币战争', 'game'),
            run_record=CurrencyWarRunRecord(ctx.current_instance_idx),
        )

    def _at_lobby(self, screen) -> bool:
        """已在货币战争大厅(「创业指南」大厅独有锚点,lobby screen_info area)。"""
        return self.round_by_find_area(screen, EnterCurrencyWar.LOBBY_SCREEN, '标识-创业指南').is_success

    def _in_match(self, screen) -> bool:
        """已在货币战争对局中(备战/事件/战斗/结算任一态)。

        双层:①screen_info 画面匹配(治本,新屏建档即生效);②关键词 fallback(半开/过渡帧)。
        """
        # 大厅不是对局中态:防 _IN_MATCH_KEYWORDS 短词(如「出战」)round_by_ocr 默认 lcs 0.5
        # 误匹配大厅文字(「货币战争」含「战」→「出战」1/2=0.5 命中)→ _start_match 误判已在对局 →
        # 跳过 start 交 loop → loop 见大厅「创业指南」→ 误「对局结束」2.4s 空跑(2026-08-06 实跑)。
        if self._at_lobby(screen):
            return False
        # ① 画面匹配层:已建档对局屏(备战系/事件系/战斗系/结算系/警告系/难度确认)。
        # 难度确认 = start 流已开对局(点开始后),归对局中。
        _in_match_screens = self.in_match_screen_names(self.ctx.screen_loader.screen_info_list)
        if _in_match_screens:
            try:
                from one_dragon.base.screen.screen_utils import get_match_screen_name
                if get_match_screen_name(self.ctx, screen, screen_name_list=_in_match_screens) is not None:
                    return True
            except Exception:  # noqa: BLE001  画面匹配失败退关键词层,不阻塞启动
                pass
        # ② 关键词 fallback(历史行为保留):真在对局时这些锚点 OCR 干净 4/4 命中。
        return any(self.round_by_ocr(screen, kw, lcs_percent=0.8).is_success for kw in self._IN_MATCH_KEYWORDS)

    @operation_node(name='进入货币战争大厅', is_start_node=True)
    def _enter_lobby(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if self._at_lobby(screen) or self._in_match(screen):
            return self.round_success('已在 CW(大厅/对局中),跳过 enter')
        op = EnterCurrencyWar(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='进入货币战争大厅')
    @operation_node(name='开始对局到备战阶段')
    def _start_match(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if self._in_match(screen):
            return self.round_success('已在对局中,跳过 start 交 loop')
        op = StartCurrencyWarMatch(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='开始对局到备战阶段')
    @operation_node(name='对局循环到结束')
    def _run_loop(self) -> OperationRoundResult:
        _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
        op = CurrencyWarRunLoop(self.ctx, max_rounds=_cfg.max_rounds)
        return self.round_by_op_result(op.execute())
