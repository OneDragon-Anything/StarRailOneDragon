"""末日幻影 app 运行时配置。

落点 = config/<实例>/<应用组>/apocalyptic_shadow.yml(ApplicationConfig 口径);
factory 实现 create_config 后,MCP 通用配置工具(describe/get/set)可直接读写。
"""
from __future__ import annotations

from one_dragon.base.operation.application.application_config import ApplicationConfig

#: 随机选人默认池 = 2026-11-16 米游社 ``mys_get_characters`` 账号持有名单(65 人)
#: ∩ ``sr_od.config.character_const.CHARACTER_LIST`` 名字校验后的 64 人快照。
#: 「开拓者」被排除:常量表按命途拆名(如「开拓者•存护」),米游社返回裸名
#: 「开拓者」,进池会在编队填充的名字校验处被拒。快照随账号养成/抽卡变动会
#: 过期,过期表现为填充失败「列表到底未找到」——可在配置覆盖 character_pool;
#: 根治(编队屏实机扫描建池)留选人策略迭代。
DEFAULT_CHARACTER_POOL: list[str] = [
    '星神★阿哈', '姬子•启行', '远坂凛', '千冶•刃', '银狼LV.999', '真珠', '爻光',
    '丹恒•腾荒', '长夜月', '海瑟音', '风堇', '遐蝶', '缇宝', '大丽花', '波提欧',
    '星期日', '知更鸟', '黄泉', '黑天鹅', '花火', '真理医生', '砂金', '阮•梅',
    '灵砂', '飞霄', '椒丘', '藿藿', '丹恒•饮月', '镜流', '白露', '符玄', '刃',
    '罗刹', '克拉拉', '杰帕德', '希儿', '布洛妮娅', 'Archer', '银狼', '卡芙卡',
    '瓦尔特', '姬子', '米沙', '加拉赫', '三月七', '貊泽', '寒鸦', '雪衣', '桂乃芬',
    '驭空', '素裳', '停云', '青雀', '卢卡', '玲可', '虎克', '桑博', '佩拉',
    '娜塔莎', '希露瓦', '黑塔', '艾丝妲', '阿兰', '丹恒',
]


class ApocalypticShadowConfig(ApplicationConfig):
    """末日幻影 app 配置(随机选人占位策略 + 领奖开关)。"""

    def __init__(self, instance_idx: int, group_id: str = 'one_dragon'):
        """
        Args:
            instance_idx: 账号实例下标(config 目录编号,1 基,构造期快照)
            group_id: 应用组 id,独立运行固定默认组
        """
        ApplicationConfig.__init__(self, 'apocalyptic_shadow', instance_idx, group_id)

    @property
    def claim_rewards(self) -> bool:
        """挑战成功后是否领取期次祭礼奖励(两 tab 一键全领)。"""
        return self.get('claim_rewards', True)

    @claim_rewards.setter
    def claim_rewards(self, new_value: bool) -> None:
        self.update('claim_rewards', new_value)

    @property
    def character_pool(self) -> list[str]:
        """随机选人候选池(角色中文名,与编队屏列表卡识别名同口径);
        配置为空列表时回落默认快照池。"""
        pool: list[str] = self.get('character_pool', DEFAULT_CHARACTER_POOL)
        if not pool:
            return list(DEFAULT_CHARACTER_POOL)
        return list(pool)

    @character_pool.setter
    def character_pool(self, new_value: list[str]) -> None:
        self.update('character_pool', new_value)
