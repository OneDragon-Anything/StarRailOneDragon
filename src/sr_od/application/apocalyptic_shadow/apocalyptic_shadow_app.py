"""末日幻影独立应用:导航 → 编队屏探测规模 → 随机选人 → 挑战 → 领奖 → 回大世界。

编排按四段式骨架(设计依据见迭代设计稿 §3/§5):
① 导航段 = ``GotoTreasuresLightward``(任意画面 → 末日幻影选关,实机验证);
② 玩法段 = 探测节点(选关→编队屏,实读节点行数定 8/12 人)+ 随机选人(纯逻辑)
   + ``TlApocalypticShadowChallengeOp``(编队→装配→挑战→战斗→结算→回选关);
③ 领奖段 = ``TlRewardClaimOp``(祭礼两 tab 一键全领,失败不阻塞收尾);
④ 返回段 = ``BackToNormalWorldPlus``(回大世界,与开拓力 app 同款收尾)。

选人策略为随机占位(用户裁定 2026-11-16),真策略接缝在 ``strategy.py``。
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, ClassVar

from one_dragon.base.operation.application_run_record import AppRunRecord
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.application.apocalyptic_shadow import apocalyptic_shadow_const
from sr_od.application.apocalyptic_shadow.apocalyptic_shadow_config import (
    ApocalypticShadowConfig,
)
from sr_od.application.apocalyptic_shadow.strategy import pick_random_teams
from sr_od.application.sr_application import SrApplication
from sr_od.application.treasures_lightward.obs.tl_team_common import (
    get_area_center_point,
)
from sr_od.application.treasures_lightward.obs.tl_team_obs import read_team_nodes
from sr_od.application.treasures_lightward.operations.apocalyptic_shadow.challenge import (
    TlApocalypticShadowChallengeOp,
)
from sr_od.application.treasures_lightward.operations.apocalyptic_shadow.reward_claim import (
    TlRewardClaimOp,
)
from sr_od.application.treasures_lightward.operations.goto_treasures_lightward import (
    GotoTreasuresLightward,
    TLMode,
)
from sr_od.config.character_const import CHARACTER_LIST
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

_SELECT_SCREEN: str = '末日幻影-选关'
_TEAM_SCREEN: str = '末日幻影-编队'
_BANNER_SCREEN: str = '末日幻影-首领简报'


class ApocalypticShadowApp(SrApplication):
    """末日幻影一键挑战:主界面起、大世界收;单次运行挑战当前默认选中难度
    (=最高可玩,本 app 不做难度选择)一次。"""

    #: 挑战重试预算 = 初选 + 2 次换人重选;仅针对「列表到底未找到 X」形态
    _MAX_CHALLENGE_ATTEMPTS: int = 3

    #: 编队填充失败的候选名提取(填充 op 的失败状态原文 = f'列表到底未找到 {名}')
    _MISSING_NAME_PAT: ClassVar[re.Pattern] = re.compile(r'列表到底未找到 (.+)')

    def __init__(self, ctx: SrContext, run_record: AppRunRecord | None = None,
                 instance_idx: int | None = None):
        """
        Args:
            ctx: 上下文
            run_record: 运行记录(factory 传入;None 时框架自行解析)
            instance_idx: 账号实例下标(config 目录编号,1 基,构造期快照;
                缺省取当前实例)
        """
        SrApplication.__init__(self, ctx, apocalyptic_shadow_const.APP_ID,
                               op_name=gt('末日幻影'), run_record=run_record)
        idx = instance_idx if instance_idx is not None else ctx.current_instance_idx
        self.config: ApocalypticShadowConfig = ApocalypticShadowConfig(idx)
        # 编队屏节点行数(2 = 01-03 双节点,3 = 星启 04)——探测节点执行期实读快照
        self._team_count: int = 0
        # 随机选出的按行拼接名单(前 4 = 节点一),写入端 = 随机选人节点
        self._team_names: list[str] = []
        # 每行终焉公理增益序号(1 基;占位策略固定全 1,增益名称随期轮换不锚名)
        self._buff_slots: tuple[int, ...] = ()

    @operation_node(name='前往末日幻影', is_start_node=True, node_max_retry_times=3)
    def goto(self) -> OperationRoundResult:
        """① 导航段:任意画面 → 末日幻影选关(含不在入口链时的回大世界兜底)。"""
        op = GotoTreasuresLightward(self.ctx, TLMode.APOCALYPTIC_SHADOW)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='前往末日幻影')
    @operation_node(name='进编队屏探测规模', node_max_retry_times=10)
    def probe_team_size(self) -> OperationRoundResult:
        """选关屏 → 编队屏,实读节点行数定选人数量。

        进入分支与挑战组合 op 的入口节点同款(challenge.py 进入编队屏,
        实机验证语义):未通关难度 = 「前往挑战」;已通关 = 「重新挑战」;
        已有编队 = 「更换编队」(+可能弹确认,确认按钮先判防止点穿)。
        首领简报横幅 = 编队满员态进编队屏会自动弹(挑战已用旧队发起)——
        本 app 要换随机队,此态不可继续,显式失败让调用方先处理进行中的挑战。
        到达验证 = 编队屏双锚,到达后行数实读失败按重试(遮挡容错)。"""
        screen = self.last_screenshot
        if self.round_by_find_area(
                screen, _BANNER_SCREEN, '提示-点击空白处关闭').is_success:
            return self.round_fail(
                '编队满员态自动弹首领简报(旧编队已被发起挑战),'
                '请先处理进行中的挑战再运行本 app')
        if (self.round_by_find_area(screen, _TEAM_SCREEN, '标题-末日幻影行').is_success
                and self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success):
            return self._read_team_size()
        if self.round_by_find_area(
                screen, _SELECT_SCREEN, '按钮-更换编队确认').is_success:
            self.ctx.controller.click(
                get_area_center_point(self.ctx, _SELECT_SCREEN, '按钮-更换编队确认'),
                press_time=0.15)
            return self.round_retry('选关屏点更换编队确认', wait=2.5)
        for area_name in ('按钮-前往挑战', '按钮-重新挑战', '按钮-更换编队'):
            if self.round_by_find_area(screen, _SELECT_SCREEN, area_name).is_success:
                self.ctx.controller.click(
                    get_area_center_point(self.ctx, _SELECT_SCREEN, area_name),
                    press_time=0.15)
                return self.round_retry(f'选关屏点{area_name}', wait=2.5)
        return self.round_retry('画面异常(不在末日幻影选关屏也不在编队屏)', wait=1.5)

    @node_from(from_name='进编队屏探测规模')
    @operation_node(name='随机选人')
    def pick_team(self) -> OperationRoundResult:
        """从角色池随机抽队(纯逻辑,不流转画面);名单与增益槽在此定死。"""
        known = {c.cn for c in CHARACTER_LIST}
        full_pool = self.config.character_pool
        pool = [name for name in full_pool if name in known]
        dropped = len(full_pool) - len(pool)
        if dropped:
            log.info('末日幻影 app: 角色池剔除不在常量表的名单 %d 个', dropped)
        try:
            self._team_names = pick_random_teams(pool, self._team_count)
        except ValueError as e:
            return self.round_fail(str(e))
        self._buff_slots = tuple([1] * self._team_count)
        log.info('末日幻影 app: 随机队伍 %s,增益槽 %s',
                 self._team_names, list(self._buff_slots))
        return self.round_success()

    @node_from(from_name='随机选人')
    @operation_node(name='执行挑战', node_max_retry_times=2)
    def challenge(self) -> OperationRoundResult:
        """挑战组合 op(带换人重选):编队 → 装配 → 前往挑战 → 战斗推进 → 返回选关。

        填充失败的已知形态 = 「列表到底未找到 X」(候选名在编队屏角色列表
        实扫不到;2026-11-16 实测:狩猎版三月七整列表遍历从未出卡,根因待查,
        证据见迭代设计稿 §10)。此形态剔除该名重选重试——填充 op 先清空
        再填,可安全重入;重试预算耗尽或非此形态失败 → 按设计中止。"""
        excluded: set[str] = set()
        last: OperationRoundResult | None = None
        for _ in range(self._MAX_CHALLENGE_ATTEMPTS):
            op = TlApocalypticShadowChallengeOp(
                self.ctx, self._team_names, self._buff_slots)
            op_result = op.execute()
            if op_result.success:
                return self.round_by_op_result(op_result)
            last = self.round_by_op_result(op_result)
            match = self._MISSING_NAME_PAT.search(op_result.status or '')
            if match is None:
                return last
            missing = match.group(1).strip()
            excluded.add(missing)
            log.info('末日幻影 app: %s 在编队屏列表扫不到,剔除后重选(已剔 %s)',
                     missing, sorted(excluded))
            if not self._re_pick(excluded):
                return self.round_fail(f'剔除 {missing} 重选后角色池不足')
        return last

    def _re_pick(self, excluded: set[str]) -> bool:
        """剔除不可扫名单后重选队伍(重写 _team_names/_buff_slots);
        池不足返回 False(调用方走失败,队伍保持上次值不再发起)。"""
        known = {c.cn for c in CHARACTER_LIST}
        pool = [n for n in self.config.character_pool
                if n in known and n not in excluded]
        try:
            self._team_names = pick_random_teams(pool, self._team_count)
        except ValueError:
            return False
        self._buff_slots = tuple([1] * self._team_count)
        log.info('末日幻影 app: 重选队伍 %s', self._team_names)
        return True

    @node_from(from_name='执行挑战')
    @operation_node(name='领取期次奖励', node_max_retry_times=2)
    def claim(self) -> OperationRoundResult:
        """③ 领奖段:祭礼两 tab 一键全领。失败按设计继续收尾(主产出挑战
        已完成;祭礼奖励无时效,下次运行补领)。"""
        if not self.config.claim_rewards:
            return self.round_success('配置关闭领奖,跳过')
        op_result = TlRewardClaimOp(self.ctx).execute()
        if op_result.success:
            return self.round_success('祭礼奖励已领取')
        log.info('末日幻影 app: 领奖失败继续收尾,状态=%s', op_result.status)
        return self.round_success('领奖失败,继续收尾')

    @node_from(from_name='领取期次奖励')
    @operation_node(name='返回大世界', node_max_retry_times=3)
    def back_to_world(self) -> OperationRoundResult:
        """④ 返回段:回大世界,保证与其它 app/人工操作在大世界干净交接。"""
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())

    def _read_team_size(self) -> OperationRoundResult:
        """实读编队屏节点行数并记录;锚读不到按重试(弹窗遮挡容错)。"""
        nodes = read_team_nodes(self.ctx, self.last_screenshot,
                                screen_name=_TEAM_SCREEN)
        if not nodes:
            return self.round_retry('编队屏节点锚未读到(画面遮挡?),重读', wait=1.5)
        if len(nodes) not in (2, 3):
            return self.round_fail(f'编队屏节点行数 {len(nodes)} 超出预期(2/3)')
        self._team_count = len(nodes)
        log.info('末日幻影 app: 编队屏节点行数 %d', len(nodes))
        return self.round_success()


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.start_running()
    app = ApocalypticShadowApp(ctx)
    app.execute()


if __name__ == '__main__':
    __debug()
