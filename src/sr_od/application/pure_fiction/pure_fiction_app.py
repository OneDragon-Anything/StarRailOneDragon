"""虚构叙事独立应用:导航 → 编队屏 → 随机选人 → 挑战 → 回大世界。

与末日幻影 app 同构的四段式编排(设计依据 = 末日幻影迭代设计稿,差异):
- 无探测规模节点(虚构叙事固定 2 节点 8 人);
- 选关→编队屏 = 点「纸鹤-关卡01」(最高已解锁关卡建模仅 01,增益装配由
  组合 op 内的战意效果单选 + 荒腔走板三选一按位置兜底);
- 无领奖段(期次奖励领取 op 未建模,挂账);
- 挑战失败「列表到底未找到 X」同款换人重选韧性(共享 random_team)。

选人策略为随机占位(用户裁定 2026-11-16),真策略接缝在共享 random_team。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.operation.application_run_record import AppRunRecord
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.application.pure_fiction import pure_fiction_const
from sr_od.application.pure_fiction.pure_fiction_config import PureFictionConfig
from sr_od.application.sr_application import SrApplication
from sr_od.application.treasures_lightward.operations.goto_treasures_lightward import (
    GotoTreasuresLightward,
    TLMode,
)
from sr_od.application.treasures_lightward.operations.pure_fiction.challenge import (
    TlPureFictionChallengeOp,
)
from sr_od.application.treasures_lightward.random_team import (
    extract_missing_name,
    pick_random_teams,
    re_pick,
)
from sr_od.config.character_const import CHARACTER_LIST
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

_SELECT_SCREEN: str = '逐光捡金'
_TEAM_SCREEN: str = '虚构叙事-编队'

#: 挑战重试预算 = 初选 + 2 次换人重选;仅针对「列表到底未找到 X」形态
_MAX_CHALLENGE_ATTEMPTS: int = 3


class PureFictionApp(SrApplication):
    """虚构叙事一键挑战:主界面起、大世界收;单次运行挑战关卡01一次。"""

    def __init__(self, ctx: SrContext, run_record: AppRunRecord | None = None,
                 instance_idx: int | None = None):
        """
        Args:
            ctx: 上下文
            run_record: 运行记录(factory 传入;None 时框架自行解析)
            instance_idx: 账号实例下标(config 目录编号,1 基,构造期快照;
                缺省取当前实例)
        """
        SrApplication.__init__(self, ctx, pure_fiction_const.APP_ID,
                               op_name=gt('虚构叙事'), run_record=run_record)
        idx = instance_idx if instance_idx is not None else ctx.current_instance_idx
        self.config: PureFictionConfig = PureFictionConfig(idx)
        # 随机选出的按行拼接名单(前 4 = 节点一),写入端 = 随机选人节点
        self._team_names: list[str] = []

    @operation_node(name='前往虚构叙事', is_start_node=True, node_max_retry_times=3)
    def goto(self) -> OperationRoundResult:
        """① 导航段:任意画面 → 虚构叙事选关(新期开场页由导航 op 收尾处理)。"""
        op = GotoTreasuresLightward(self.ctx, TLMode.PURE_FICTION)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='前往虚构叙事')
    @operation_node(name='进编队屏', node_max_retry_times=10)
    def enter_team_screen(self) -> OperationRoundResult:
        """选关点「纸鹤-关卡01」→ 编队屏,until 双锚验证转移(点了≠进了)。

        已在编队屏直接短路(挑战组合 op 前置 = 已在编队屏,其入口只校验不导航)。"""
        screen = self.last_screenshot
        if (self.round_by_find_area(screen, _TEAM_SCREEN, '标题-虚构叙事行').is_success
                and self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success):
            return self.round_success()
        return self.round_by_find_and_click_area(
            screen, _SELECT_SCREEN, '纸鹤-关卡01',
            until_find_all=[
                (_TEAM_SCREEN, '标题-虚构叙事行'),
                (_TEAM_SCREEN, '标题-编队行'),
            ],
            pre_delay=0.5, success_wait=2, retry_wait=2,
        )

    @node_from(from_name='进编队屏')
    @operation_node(name='随机选人')
    def pick_team(self) -> OperationRoundResult:
        """从角色池随机抽 8 人(纯逻辑,不流转画面);增益占位全选第 1 项。"""
        known = {c.cn for c in CHARACTER_LIST}
        full_pool = self.config.character_pool
        pool = [name for name in full_pool if name in known]
        dropped = len(full_pool) - len(pool)
        if dropped:
            log.info('虚构叙事 app: 角色池剔除不在常量表的名单 %d 个', dropped)
        try:
            self._team_names = pick_random_teams(pool, 2)
        except ValueError as e:
            return self.round_fail(str(e))
        log.info('虚构叙事 app: 随机队伍 %s', self._team_names)
        return self.round_success()

    @node_from(from_name='随机选人')
    @operation_node(name='执行挑战', node_max_retry_times=2)
    def challenge(self) -> OperationRoundResult:
        """挑战组合 op(带换人重选,与末日幻影 app 同款韧性):编队 → 增益装配
        → 进入故事 → 战斗推进 → 返回选关。

        填充失败的已知形态 = 「列表到底未找到 X」(候选名在编队屏列表实扫
        不到)——剔除该名重选重试,预算 2 次;其余失败按设计中止。"""
        excluded: set[str] = set()
        last: OperationRoundResult | None = None
        for _ in range(_MAX_CHALLENGE_ATTEMPTS):
            op = TlPureFictionChallengeOp(
                self.ctx, self._team_names, buff_slot=1, buff_slots=[1, 1])
            op_result = op.execute()
            if op_result.success:
                return self.round_by_op_result(op_result)
            last = self.round_by_op_result(op_result)
            missing = extract_missing_name(op_result.status)
            if missing is None:
                return last
            excluded.add(missing)
            log.info('虚构叙事 app: %s 在编队屏列表扫不到,剔除后重选(已剔 %s)',
                     missing, sorted(excluded))
            known = {c.cn for c in CHARACTER_LIST}
            pool = [n for n in self.config.character_pool if n in known]
            try:
                self._team_names = re_pick(pool, excluded, 2)
            except ValueError:
                return self.round_fail(f'剔除 {missing} 重选后角色池不足')
        return last

    @node_from(from_name='执行挑战')
    @operation_node(name='返回大世界', node_max_retry_times=3)
    def back_to_world(self) -> OperationRoundResult:
        """④ 返回段:回大世界,保证与其它 app/人工操作在大世界干净交接。"""
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.start_running()
    app = PureFictionApp(ctx)
    app.execute()


if __name__ == '__main__':
    __debug()
