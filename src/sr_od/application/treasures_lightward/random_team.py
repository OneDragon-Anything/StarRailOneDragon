"""逐光捡金家族共享的随机选人策略(占位接缝,末日幻影/虚构叙事 app 共用)。

用户裁定(2026-11-16):选人策略暂时乱选,先把流程串起来——未来换真策略
(按弱点/练度/体系配队)时替换实现,各 app 编排不变。
"""
from __future__ import annotations

import random
import re
from typing import ClassVar

#: 随机选人默认池 = 2026-11-16 米游社 ``mys_get_characters`` 账号持有名单(65 人)
#: ∩ ``sr_od.config.character_const.CHARACTER_LIST`` 名字校验后的 64 人快照。
#: 「开拓者」被排除:常量表按命途×性别拆名(如「开拓者•存护」),米游社返回
#: 裸名「开拓者」,进池会在编队填充的名字校验处被拒。快照随账号养成/抽卡
#: 变动会过期,过期表现为填充失败「列表到底未找到」——可在各 app 配置覆盖
#: character_pool;根治(编队屏实机扫描建池)留选人策略迭代。
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


def pick_random_teams(pool: list[str], team_count: int) -> list[str]:
    """从候选池无放回随机抽 ``team_count`` 行 × 4 人的名单,按行序拼接。

    Args:
        pool: 候选角色中文名列表(须与编队屏列表卡识别名同口径)
        team_count: 节点行数(2 = 常规双节点,3 = 末日幻影星启;执行期实读)

    Returns:
        长度 ``team_count*4`` 的名字列表,前 4 个 = 节点一队伍,以此类推。

    Raises:
        ValueError: 池人数不足(调用方转节点失败,消息可直接展示)。
    """
    need = team_count * 4
    if len(pool) < need:
        raise ValueError(
            f'角色池 {len(pool)} 人不足 {team_count} 节点所需 {need} 人,'
            f'请在配置 character_pool 补充')
    return random.sample(pool, need)


#: 编队填充失败的候选名提取(末日幻影/虚构叙事填充 op 的失败状态原文同款
#: = f'列表到底未找到 {名}')
MISSING_NAME_PAT: ClassVar[re.Pattern] = re.compile(r'列表到底未找到 (.+)')


def extract_missing_name(status: str | None) -> str | None:
    """从填充失败状态提取扫不到的候选名;非该形态失败返回 None。"""
    if not status:
        return None
    match = MISSING_NAME_PAT.search(status)
    return match.group(1).strip() if match is not None else None


def re_pick(pool: list[str], excluded: set[str], team_count: int) -> list[str]:
    """从**已过合法性过滤**的候选池剔除不可扫名单后重选;池不足抛
    ValueError(调用方转失败)。合法性过滤(∩ 常量表)由调用方先行完成,
    本函数只做剔除与抽取。"""
    return pick_random_teams(
        [name for name in pool if name not in excluded], team_count)
