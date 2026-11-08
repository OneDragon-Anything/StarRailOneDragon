"""按材料名刷取副本 operation(材料缺口 → 具体副本 → 开拓力刷取)。

养成线 op 的材料补给侧:常量 dungeon_drop_const.MATERIAL_MISSIONS 给出
材料 → 具体副本实例({category, mission, region},与指南关卡同名对齐,
由 tools/game_data/generate_ascension_const.py 从官方 wiki 来源串 join
指南数据生成),本 op 把它接到 UseTrailblazePower(自带传送+挑战 N 次)
上——「查到缺口 → 去刷」的执行端;典型上游是 MCP
character_lookup(with_ascension=true) 的 missions_by_material。

定位(构造期显式失败,不静默):
- find_missions_by_material(material) → 实例列表;mission_index 指定用哪个
  (默认 0);一材料多实例 = 多区域均可刷(如信用点在多个花萼赤);
- SrGuideData 按 (分类名, mission_name, region_name) 精确匹配解析
  GuideMission——解析失败 = 常量表与指南数据不同步(版本适配欠账,
  生成时会有「未解析」警告),报错指向重跑生成器/更新指南 yml。

前置:任意画面(首节点回大世界;UseTrailblazePower 自带 GuideTransport
从大世界传送进本)。

⚠️ 真实资源消耗:times 次挑战共扣 times × mission.power 开拓力
(花萼 10/凝滞虚影·历战余响 30/侵蚀隧洞 40);次数由调用方按材料缺口与
单次产量估算,**发起前必须向用户说明预计消耗并获同意**。
"""

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.challenge_mission.use_trailblaze_power import UseTrailblazePower
from sr_od.config.dungeon_drop_const import find_missions_by_material
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guide_def import GuideMission
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.sr_operation import SrOperation


class FarmMaterialOp(SrOperation):
    """刷指定材料 times 次,终点 = UseTrailblazePower 的战斗收尾状态。

    ⚠️ times × mission.power 开拓力为真实消耗,调用方发起前须获用户同意。
    """

    def __init__(self, ctx: SrContext, material: str, times: int,
                 mission_index: int = 0, team_num: int = 0,
                 support: str | None = None):
        """
        :param ctx: 上下文
        :param material: 材料名(与 MATERIAL_MISSIONS 键一致,如「天人遗垢」)
        :param times: 计划挑战次数(>0)
        :param mission_index: 使用的副本实例下标——坐标系 = find_missions_by_material
            返回列表的下标(常量表生成期快照,顺序稳定);取值时机 = 构造期
        :param team_num: 配队编号(0 = 游戏内当前配队)
        :param support: 支援角色 id,None = 不用
        """
        material = material.strip()
        entries = find_missions_by_material(material)
        if not entries:
            raise ValueError(
                f'材料「{material}」无实例级副本映射(MATERIAL_MISSIONS 无条目;'
                f'分类级可刷不代表能定位具体关卡,如差分宇宙类材料)')
        if not 0 <= mission_index < len(entries):
            raise ValueError(f'mission_index {mission_index} 越界:'
                             f'「{material}」共 {len(entries)} 个实例: {entries}')
        if times <= 0:
            raise ValueError(f'times 必须 > 0, 得到 {times}')
        entry = entries[mission_index]
        mission = ctx.guide_data.get_mission_by_guide_info(
            entry['category'], entry['mission'], entry['region'])
        if mission is None:
            raise ValueError(
                f'指南数据无关卡 {entry}(常量表与指南数据不同步:'
                f'重跑 tools/game_data/generate_ascension_const.py 或更新指南 yml)')

        self.material: str = material
        self.mission: GuideMission = mission
        self.times: int = times
        self.mission_index: int = mission_index
        self.team_num: int = team_num
        self.support: str | None = support
        SrOperation.__init__(self, ctx,
                             op_name=f'{gt("材料刷取")} {material}×{times}',
                             node_max_retry_times=8)
        log.info('材料刷取: %s → %s ×%d (每次开拓力 %d)',
                 material, mission.unique_id, times, mission.power)

    #------------------- 节点图 -------------------#

    @operation_node(name='回大世界', is_start_node=True, node_max_retry_times=2)
    def back_to_world(self) -> OperationRoundResult:
        """起点确定:回大世界(UseTrailblazePower 从大世界开指南传送)。"""
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='回大世界')
    @operation_node(name='刷取材料')
    def farm(self) -> OperationRoundResult:
        """委托 UseTrailblazePower:传送进本 + 挑战 times 次。"""
        op = UseTrailblazePower(self.ctx, self.mission, self.team_num,
                                self.times, support=self.support)
        return self.round_by_op_result(op.execute())
