from enum import Enum
from typing import Optional, List

from one_dragon.utils import str_utils
from one_dragon.utils.i18_utils import gt


class SimUniType:

    def __init__(self, uid: str, category: str, name: str):
        self.uid: str = uid
        """唯一标识"""

        self.category: str = category
        """左上角显示的分类"""

        self.name: str = name
        """类型名称"""


class SimUniTypeEnum(Enum):

    NORMAL = SimUniType('sim_uni_type_simulated_universe', '模拟宇宙', '模拟宇宙')

    EXTEND_SWARM = SimUniType('sim_uni_type_swarm_disaster', '拓展装置', '寰宇蝗虫')

    EXTEND_GOLD = SimUniType('sim_uni_type_gold_and_gears', '拓展装置', '黄金与机械')


class SimUniWorld:

    def __init__(self, idx: int, name: str, max_diff: int):
        self.idx = idx
        self.name = name
        self.max_diff: int = max_diff

    @property
    def unique_id(self) -> str:
        return 'sim_uni_normal_world_%02d' % self.idx


class SimUniWorldEnum(Enum):

    WORLD_00 = SimUniWorld(0, '本周积分', 0)
    WORLD_01 = SimUniWorld(1, '第一宇宙', 0)
    WORLD_02 = SimUniWorld(2, '第二宇宙', 0)
    WORLD_03 = SimUniWorld(3, '第三宇宙', 5)
    WORLD_04 = SimUniWorld(4, '第四宇宙', 5)
    WORLD_05 = SimUniWorld(5, '第五宇宙', 4)
    WORLD_06 = SimUniWorld(6, '第六宇宙', 4)
    WORLD_07 = SimUniWorld(7, '第七宇宙', 4)
    WORLD_08 = SimUniWorld(8, '第八宇宙', 4)
    WORLD_09 = SimUniWorld(9, '第九宇宙', 4)


class OrnamentExtraction:

    def __init__(self, idx: int, name: str, max_diff: int):
        """
        饰品提取
        :param idx:
        :param name:
        :param max_diff:
        """
        self.idx = idx
        self.name = name
        self.max_diff: int = max_diff

    @property
    def unique_id(self) -> str:
        return 'ornament_extraction_%02d' % self.idx


class OrnamentExtractionEnum(Enum):

    OE_11 = OrnamentExtraction(11, '蠹役饥肠', 5)
    OE_10 = OrnamentExtraction(10, '永恒笑剧', 5)
    OE_09 = OrnamentExtraction(9, '伴你入眠', 5)
    OE_08 = OrnamentExtraction(8, '天剑如雨', 5)
    OE_07 = OrnamentExtraction(7, '孽果盘生', 5)
    OE_06 = OrnamentExtraction(6, '百年冻土', 5)
    OE_05 = OrnamentExtraction(5, '温柔话语', 5)
    OE_04 = OrnamentExtraction(4, '浴火钢心', 5)
    OE_03 = OrnamentExtraction(3, '坚城不倒', 5)


UNI_NUM_CN: dict[int, str] = {
    1: '一',
    2: '二',
    3: '三',
    4: '四',
    5: '五',
    6: '六',
    7: '七',
    8: '八',
    9: '九',
}


class SimUniLevelType:

    def __init__(self, type_id: str, type_name: str, route_id: Optional[str] = None):
        self.type_id: str = type_id  # 类型ID 也用于模板ID
        self.type_name: str = type_name  # 类型名称 中文
        self.route_id: str = type_id if route_id is None else route_id

    @property
    def template_id(self) -> str:
        return 'level_type_%s' % self.type_id


class SimUniLevelTypeEnum(Enum):

    COMBAT = SimUniLevelType('combat', '区域-战斗')
    ENCOUNTER = SimUniLevelType('encounter', '区域-遭遇', route_id='event')
    ELITE = SimUniLevelType('elite', '区域-精英')
    BOSS = SimUniLevelType('boss', '区域-首领', route_id='elite')
    EVENT = SimUniLevelType('event', '区域-事件')
    TRANSACTION = SimUniLevelType('transaction', '区域-交易', route_id='event')
    RESPITE = SimUniLevelType('respite', '区域-休整')


def level_type_from_id(level_type_id: str) -> Optional[SimUniLevelType]:
    for enum in SimUniLevelTypeEnum:
        if enum.value.type_id == level_type_id:
            return enum.value
    return None


def level_type_from_name(level_type_name: str) -> Optional[SimUniLevelType]:
    for enum in SimUniLevelTypeEnum:
        if gt(enum.value.type_name) == level_type_name:
            return enum.value
    return None


class SimUniPath(Enum):

    KT: str = '开拓'

    PRESERVATION: str = '存护'

    REMEMBRANCE: str = '记忆'

    NIHILITY: str = '虚无'

    ABUNDANCE: str = '丰饶'

    HUNT: str = '巡猎'

    DESTRUCTION: str = '毁灭'

    ELATION: str = '欢愉'

    PROPAGATION: str = '繁育'

    ERUDITION: str = '智识'


def path_of(path_str: str) -> Optional[SimUniPath]:
    for path in SimUniPath:
        if path.value == path_str:
            return path
    return None


def match_best_path_by_ocr(path_ocr: str) -> Optional[SimUniPath]:
    path_list = [path for path in SimUniPath]
    target_path_list = [gt(path.value, 'ocr') for path in SimUniPath]
    idx = str_utils.find_best_match_by_lcs(path_ocr, target_path_list)
    if idx is None:
        return None
    else:
        return path_list[idx]


class SimUniBlessLevel(Enum):
    """命途等级"""

    WHOLE: str = '命途'
    ECHO: str = '命途回响'
    STAR_3: str = '三星祝福'
    STAR_2: str = '二星祝福'
    STAR_1: str = '一星祝福'


class SimUniBless:

    def __init__(self, path: SimUniPath, title: str, short_desc: str, full_desc: str,
                 level: SimUniBlessLevel):
        self.path: SimUniPath = path  # 命途
        self.title: str = title  # 祝福名称
        self.short_desc: str = short_desc  # 简短描述
        self.full_desc: str = full_desc  # 详细描述
        self.level: SimUniBlessLevel = level

    def __repr__(self) -> str:
        return '%s %s' % (gt(self.path.value, 'game'), gt(self.title, 'game'))


# https://bbs.mihoyo.com/sr/wiki/content/767/detail?bbs_presentation_style=no_header
# 2024.01.13 1.6版本时更新 缺少黄金与机械部分
class SimUniBlessEnum(Enum):

    # 开拓
    BLESS_00_000 = SimUniBless(SimUniPath.KT, '开拓', '', '', SimUniBlessLevel.WHOLE)
    BLESS_00_001 = SimUniBless(SimUniPath.KT, '破碎宇宙', '', '', SimUniBlessLevel.STAR_1)
    BLESS_00_002 = SimUniBless(SimUniPath.KT, '神奇宇宙', '', '', SimUniBlessLevel.STAR_1)
    BLESS_00_003 = SimUniBless(SimUniPath.KT, '祝福宇宙', '', '', SimUniBlessLevel.STAR_1)

    # 存护
    BLESS_01_000 = SimUniBless(SimUniPath.PRESERVATION, '存护', '', '', SimUniBlessLevel.WHOLE)
    BLESS_01_001 = SimUniBless(SimUniPath.PRESERVATION, '命途回响：「存护」', '', '', SimUniBlessLevel.ECHO)
    BLESS_01_002 = SimUniBless(SimUniPath.PRESERVATION, '回响构音:共晶反应', '', '', SimUniBlessLevel.ECHO)
    BLESS_01_003 = SimUniBless(SimUniPath.PRESERVATION, '回响构音:均晶转变', '', '', SimUniBlessLevel.ECHO)
    BLESS_01_004 = SimUniBless(SimUniPath.PRESERVATION, '回响构音:零维强化', '', '', SimUniBlessLevel.ECHO)
    BLESS_01_005 = SimUniBless(SimUniPath.PRESERVATION, '回响交错:披锋效应', '', '', SimUniBlessLevel.ECHO)
    BLESS_01_006 = SimUniBless(SimUniPath.PRESERVATION, '回响交错:冷脆现象', '', '', SimUniBlessLevel.ECHO)
    BLESS_01_007 = SimUniBless(SimUniPath.PRESERVATION, '神性构筑·谐振传递', '', '', SimUniBlessLevel.STAR_3)
    BLESS_01_008 = SimUniBless(SimUniPath.PRESERVATION, '神性构筑·宏观偏析', '', '', SimUniBlessLevel.STAR_3)
    BLESS_01_009 = SimUniBless(SimUniPath.PRESERVATION, '神性构筑·超静定场', '', '', SimUniBlessLevel.STAR_3)
    BLESS_01_010 = SimUniBless(SimUniPath.PRESERVATION, '星间构筑·迸裂晶格', '', '', SimUniBlessLevel.STAR_2)
    BLESS_01_011 = SimUniBless(SimUniPath.PRESERVATION, '星间构筑·回馈庇护', '', '', SimUniBlessLevel.STAR_2)
    BLESS_01_012 = SimUniBless(SimUniPath.PRESERVATION, '星间构筑·安全载荷', '', '', SimUniBlessLevel.STAR_2)
    BLESS_01_013 = SimUniBless(SimUniPath.PRESERVATION, '星间构筑·四棱锥体', '', '', SimUniBlessLevel.STAR_2)
    BLESS_01_014 = SimUniBless(SimUniPath.PRESERVATION, '星间构筑·亚共晶体', '', '', SimUniBlessLevel.STAR_2)
    BLESS_01_015 = SimUniBless(SimUniPath.PRESERVATION, '星间构筑·切变结构', '', '', SimUniBlessLevel.STAR_2)
    BLESS_01_016 = SimUniBless(SimUniPath.PRESERVATION, '星间构筑·固溶强化', '', '', SimUniBlessLevel.STAR_2)
    BLESS_01_017 = SimUniBless(SimUniPath.PRESERVATION, '构筑·哨戒', '', '', SimUniBlessLevel.STAR_1)
    BLESS_01_018 = SimUniBless(SimUniPath.PRESERVATION, '构筑·坚定', '', '', SimUniBlessLevel.STAR_1)
    BLESS_01_019 = SimUniBless(SimUniPath.PRESERVATION, '构筑·回转', '', '', SimUniBlessLevel.STAR_1)
    BLESS_01_020 = SimUniBless(SimUniPath.PRESERVATION, '构筑·弥合', '', '', SimUniBlessLevel.STAR_1)
    BLESS_01_021 = SimUniBless(SimUniPath.PRESERVATION, '构筑·专注', '', '', SimUniBlessLevel.STAR_1)
    BLESS_01_022 = SimUniBless(SimUniPath.PRESERVATION, '构筑·聚塑', '', '', SimUniBlessLevel.STAR_1)
    BLESS_01_023 = SimUniBless(SimUniPath.PRESERVATION, '构筑·补偿', '', '', SimUniBlessLevel.STAR_1)
    BLESS_01_024 = SimUniBless(SimUniPath.PRESERVATION, '构筑·进发', '', '', SimUniBlessLevel.STAR_1)

    # 记忆
    BLESS_02_000 = SimUniBless(SimUniPath.REMEMBRANCE, '记忆', '', '', SimUniBlessLevel.WHOLE)
    BLESS_02_001 = SimUniBless(SimUniPath.REMEMBRANCE, '命途回响：「记忆」', '', '', SimUniBlessLevel.ECHO)
    BLESS_02_002 = SimUniBless(SimUniPath.REMEMBRANCE, '回响构音:体验的富翁', '', '', SimUniBlessLevel.ECHO)
    BLESS_02_003 = SimUniBless(SimUniPath.REMEMBRANCE, '回响构音:全面回忆', '', '', SimUniBlessLevel.ECHO)
    BLESS_02_004 = SimUniBless(SimUniPath.REMEMBRANCE, '回响构音:第二次初恋', '', '', SimUniBlessLevel.ECHO)
    BLESS_02_005 = SimUniBless(SimUniPath.REMEMBRANCE, '回响交错:雾中风景', '', '', SimUniBlessLevel.ECHO)
    BLESS_02_006 = SimUniBless(SimUniPath.REMEMBRANCE, '回响交错:脸庞，村年', '', '', SimUniBlessLevel.ECHO)
    BLESS_02_007 = SimUniBless(SimUniPath.REMEMBRANCE, '完美体验:纯真', '', '', SimUniBlessLevel.STAR_3)
    BLESS_02_008 = SimUniBless(SimUniPath.REMEMBRANCE, '完美体验:缄默', '', '', SimUniBlessLevel.STAR_3)
    BLESS_02_009 = SimUniBless(SimUniPath.REMEMBRANCE, '完美体验:浮黎', '', '', SimUniBlessLevel.STAR_3)
    BLESS_02_010 = SimUniBless(SimUniPath.REMEMBRANCE, '极端体验:头晕目眩', '', '', SimUniBlessLevel.STAR_2)
    BLESS_02_011 = SimUniBless(SimUniPath.REMEMBRANCE, '极端体验:多愁善感', '', '', SimUniBlessLevel.STAR_2)
    BLESS_02_012 = SimUniBless(SimUniPath.REMEMBRANCE, '极端体验:特立独行', '', '', SimUniBlessLevel.STAR_2)
    BLESS_02_013 = SimUniBless(SimUniPath.REMEMBRANCE, '极端体验:沦浃肌髓', '', '', SimUniBlessLevel.STAR_2)
    BLESS_02_014 = SimUniBless(SimUniPath.REMEMBRANCE, '极端体验:不寒而栗', '', '', SimUniBlessLevel.STAR_2)
    BLESS_02_015 = SimUniBless(SimUniPath.REMEMBRANCE, '极端体验:麻木不仁', '', '', SimUniBlessLevel.STAR_2)
    BLESS_02_016 = SimUniBless(SimUniPath.REMEMBRANCE, '极端体验:怅然若失', '', '', SimUniBlessLevel.STAR_2)
    BLESS_02_017 = SimUniBless(SimUniPath.REMEMBRANCE, '体验:难言的羞耻', '', '', SimUniBlessLevel.STAR_1)
    BLESS_02_018 = SimUniBless(SimUniPath.REMEMBRANCE, '体验:决绝的痛恨', '', '', SimUniBlessLevel.STAR_1)
    BLESS_02_019 = SimUniBless(SimUniPath.REMEMBRANCE, '体验:原初的苦衷', '', '', SimUniBlessLevel.STAR_1)
    BLESS_02_020 = SimUniBless(SimUniPath.REMEMBRANCE, '体验:丢失的记忆', '', '', SimUniBlessLevel.STAR_1)
    BLESS_02_021 = SimUniBless(SimUniPath.REMEMBRANCE, '体验:病痛的折磨', '', '', SimUniBlessLevel.STAR_1)
    BLESS_02_022 = SimUniBless(SimUniPath.REMEMBRANCE, '体验:攀升的刺激', '', '', SimUniBlessLevel.STAR_1)
    BLESS_02_023 = SimUniBless(SimUniPath.REMEMBRANCE, '体验:回应的兴奋', '', '', SimUniBlessLevel.STAR_1)
    BLESS_02_024 = SimUniBless(SimUniPath.REMEMBRANCE, '体验:疏离的煎熬', '', '', SimUniBlessLevel.STAR_1)

    # 虚无
    BLESS_03_000 = SimUniBless(SimUniPath.NIHILITY, '虚无', '', '', SimUniBlessLevel.WHOLE)
    BLESS_03_001 = SimUniBless(SimUniPath.NIHILITY, '命途回响：「虚无」', '', '', SimUniBlessLevel.ECHO)
    BLESS_03_002 = SimUniBless(SimUniPath.NIHILITY, '回响构音:局外人', '', '', SimUniBlessLevel.ECHO)
    BLESS_03_003 = SimUniBless(SimUniPath.NIHILITY, '回响构音:怀疑的四重根', '', '', SimUniBlessLevel.ECHO)
    BLESS_03_004 = SimUniBless(SimUniPath.NIHILITY, '回响构音:苦难与阳光', '', '', SimUniBlessLevel.ECHO)
    BLESS_03_005 = SimUniBless(SimUniPath.NIHILITY, '回响交错:林中路', '', '', SimUniBlessLevel.ECHO)
    BLESS_03_006 = SimUniBless(SimUniPath.NIHILITY, '回响交错:白夜', '', '', SimUniBlessLevel.ECHO)
    BLESS_03_007 = SimUniBless(SimUniPath.NIHILITY, '为何一切尚未消失', '', '', SimUniBlessLevel.STAR_3)
    BLESS_03_008 = SimUniBless(SimUniPath.NIHILITY, '被装在套子里的人', '', '', SimUniBlessLevel.STAR_3)
    BLESS_03_009 = SimUniBless(SimUniPath.NIHILITY, '感官追奉者的葬礼', '', '', SimUniBlessLevel.STAR_3)
    BLESS_03_010 = SimUniBless(SimUniPath.NIHILITY, '开端与终结', '', '', SimUniBlessLevel.STAR_2)
    BLESS_03_011 = SimUniBless(SimUniPath.NIHILITY, '火堆外的夜', '', '', SimUniBlessLevel.STAR_2)
    BLESS_03_012 = SimUniBless(SimUniPath.NIHILITY, '旷野的呼告', '', '', SimUniBlessLevel.STAR_2)
    BLESS_03_013 = SimUniBless(SimUniPath.NIHILITY, '他人即地狱', '', '', SimUniBlessLevel.STAR_2)
    BLESS_03_014 = SimUniBless(SimUniPath.NIHILITY, '无根据颂歌', '', '', SimUniBlessLevel.STAR_2)
    BLESS_03_015 = SimUniBless(SimUniPath.NIHILITY, '存在的黄昏', '', '', SimUniBlessLevel.STAR_2)
    BLESS_03_016 = SimUniBless(SimUniPath.NIHILITY, '自欺咖啡馆', '', '', SimUniBlessLevel.STAR_2)
    BLESS_03_017 = SimUniBless(SimUniPath.NIHILITY, '漠视主义', '', '', SimUniBlessLevel.STAR_1)
    BLESS_03_018 = SimUniBless(SimUniPath.NIHILITY, '悲剧讲座', '', '', SimUniBlessLevel.STAR_1)
    BLESS_03_019 = SimUniBless(SimUniPath.NIHILITY, '知觉迷墙', '', '', SimUniBlessLevel.STAR_1)
    BLESS_03_020 = SimUniBless(SimUniPath.NIHILITY, '意义质询', '', '', SimUniBlessLevel.STAR_1)
    BLESS_03_021 = SimUniBless(SimUniPath.NIHILITY, '虚妄供品', '', '', SimUniBlessLevel.STAR_1)
    BLESS_03_022 = SimUniBless(SimUniPath.NIHILITY, '日出之前', '', '', SimUniBlessLevel.STAR_1)
    BLESS_03_023 = SimUniBless(SimUniPath.NIHILITY, '盲目视界', '', '', SimUniBlessLevel.STAR_1)
    BLESS_03_024 = SimUniBless(SimUniPath.NIHILITY, '情绪舍离', '', '', SimUniBlessLevel.STAR_1)

    # 丰饶
    BLESS_04_000 = SimUniBless(SimUniPath.ABUNDANCE, '丰饶', '', '', SimUniBlessLevel.WHOLE)
    BLESS_04_001 = SimUniBless(SimUniPath.ABUNDANCE, '命途回响：「丰饶」', '', '', SimUniBlessLevel.ECHO)
    BLESS_04_002 = SimUniBless(SimUniPath.ABUNDANCE, '回响构音:无余涅槃', '', '', SimUniBlessLevel.ECHO)
    BLESS_04_003 = SimUniBless(SimUniPath.ABUNDANCE, '回响构音:诸法无我', '', '', SimUniBlessLevel.ECHO)
    BLESS_04_004 = SimUniBless(SimUniPath.ABUNDANCE, '回响构音:诸行无常', '', '', SimUniBlessLevel.ECHO)
    BLESS_04_005 = SimUniBless(SimUniPath.ABUNDANCE, '回响交错:旃檀薪尽', '', '', SimUniBlessLevel.ECHO)
    BLESS_04_006 = SimUniBless(SimUniPath.ABUNDANCE, '回响交错:先照高山', '', '', SimUniBlessLevel.ECHO)
    BLESS_04_007 = SimUniBless(SimUniPath.ABUNDANCE, '丰饶众生，一法界心', '', '', SimUniBlessLevel.STAR_3)
    BLESS_04_008 = SimUniBless(SimUniPath.ABUNDANCE, '葳蕤繁祉，延彼遐龄', '', '', SimUniBlessLevel.STAR_3)
    BLESS_04_009 = SimUniBless(SimUniPath.ABUNDANCE, '若罪若福，施诸愿印', '', '', SimUniBlessLevel.STAR_3)
    BLESS_04_010 = SimUniBless(SimUniPath.ABUNDANCE, '大愿般若船', '', '', SimUniBlessLevel.STAR_2)
    BLESS_04_011 = SimUniBless(SimUniPath.ABUNDANCE, '灭罪累生善', '', '', SimUniBlessLevel.STAR_2)
    BLESS_04_012 = SimUniBless(SimUniPath.ABUNDANCE, '慧海度慈航', '', '', SimUniBlessLevel.STAR_2)
    BLESS_04_013 = SimUniBless(SimUniPath.ABUNDANCE, '明澈琉璃身', '', '', SimUniBlessLevel.STAR_2)
    BLESS_04_014 = SimUniBless(SimUniPath.ABUNDANCE, '宝光烛日月', '', '', SimUniBlessLevel.STAR_2)
    BLESS_04_015 = SimUniBless(SimUniPath.ABUNDANCE, '厌离邪秽苦', '', '', SimUniBlessLevel.STAR_2)
    BLESS_04_016 = SimUniBless(SimUniPath.ABUNDANCE, '天人不动众', '', '', SimUniBlessLevel.STAR_2)
    BLESS_04_017 = SimUniBless(SimUniPath.ABUNDANCE, '加持', '', '', SimUniBlessLevel.STAR_1)
    BLESS_04_018 = SimUniBless(SimUniPath.ABUNDANCE, '延寿', '', '', SimUniBlessLevel.STAR_1)
    BLESS_04_019 = SimUniBless(SimUniPath.ABUNDANCE, '禳灾', '', '', SimUniBlessLevel.STAR_1)
    BLESS_04_020 = SimUniBless(SimUniPath.ABUNDANCE, '甘露', '', '', SimUniBlessLevel.STAR_1)
    BLESS_04_021 = SimUniBless(SimUniPath.ABUNDANCE, '愿印', '', '', SimUniBlessLevel.STAR_1)
    BLESS_04_022 = SimUniBless(SimUniPath.ABUNDANCE, '回生', '', '', SimUniBlessLevel.STAR_1)
    BLESS_04_023 = SimUniBless(SimUniPath.ABUNDANCE, '胜军', '', '', SimUniBlessLevel.STAR_1)
    BLESS_04_024 = SimUniBless(SimUniPath.ABUNDANCE, '法雨', '', '', SimUniBlessLevel.STAR_1)

    # 巡猎
    BLESS_05_000 = SimUniBless(SimUniPath.HUNT, '巡猎', '', '', SimUniBlessLevel.WHOLE)
    BLESS_05_001 = SimUniBless(SimUniPath.HUNT, '命途回响：「巡猎」', '', '', SimUniBlessLevel.ECHO)
    BLESS_05_002 = SimUniBless(SimUniPath.HUNT, '回响构音:柘弓危矢', '', '', SimUniBlessLevel.ECHO)
    BLESS_05_003 = SimUniBless(SimUniPath.HUNT, '回响构音:射不主皮', '', '', SimUniBlessLevel.ECHO)
    BLESS_05_004 = SimUniBless(SimUniPath.HUNT, '回响构音:狩星巡日', '', '', SimUniBlessLevel.ECHO)
    BLESS_05_005 = SimUniBless(SimUniPath.HUNT, '回响交错:火驰星流', '', '', SimUniBlessLevel.ECHO)
    BLESS_05_006 = SimUniBless(SimUniPath.HUNT, '回响交错:足逸惊飙', '', '', SimUniBlessLevel.ECHO)
    BLESS_05_007 = SimUniBless(SimUniPath.HUNT, '帝弓断空彻太清', '', '', SimUniBlessLevel.STAR_3)
    BLESS_05_008 = SimUniBless(SimUniPath.HUNT, '帝车超光所向捷', '', '', SimUniBlessLevel.STAR_3)
    BLESS_05_009 = SimUniBless(SimUniPath.HUNT, '帝星君临制穹桑', '', '', SimUniBlessLevel.STAR_3)
    BLESS_05_010 = SimUniBless(SimUniPath.HUNT, '序师执迟彝', '', '', SimUniBlessLevel.STAR_2)
    BLESS_05_011 = SimUniBless(SimUniPath.HUNT, '白矢决射御', '', '', SimUniBlessLevel.STAR_2)
    BLESS_05_012 = SimUniBless(SimUniPath.HUNT, '流岚追孽物', '', '', SimUniBlessLevel.STAR_2)
    BLESS_05_013 = SimUniBless(SimUniPath.HUNT, '云镝逐步离', '', '', SimUniBlessLevel.STAR_2)
    BLESS_05_014 = SimUniBless(SimUniPath.HUNT, '景星助狩月', '', '', SimUniBlessLevel.STAR_2)
    BLESS_05_015 = SimUniBless(SimUniPath.HUNT, '飞虹诛凿齿', '', '', SimUniBlessLevel.STAR_2)
    BLESS_05_016 = SimUniBless(SimUniPath.HUNT, '天舟缴夙敌', '', '', SimUniBlessLevel.STAR_2)
    BLESS_05_017 = SimUniBless(SimUniPath.HUNT, '背孤击虚', '', '', SimUniBlessLevel.STAR_1)
    BLESS_05_018 = SimUniBless(SimUniPath.HUNT, '雷车动地', '', '', SimUniBlessLevel.STAR_1)
    BLESS_05_019 = SimUniBless(SimUniPath.HUNT, '彤弓素矰', '', '', SimUniBlessLevel.STAR_1)
    BLESS_05_020 = SimUniBless(SimUniPath.HUNT, '天格步危', '', '', SimUniBlessLevel.STAR_1)
    BLESS_05_021 = SimUniBless(SimUniPath.HUNT, '桑弧蓬矢', '', '', SimUniBlessLevel.STAR_1)
    BLESS_05_022 = SimUniBless(SimUniPath.HUNT, '乌号基答', '', '', SimUniBlessLevel.STAR_1)
    BLESS_05_023 = SimUniBless(SimUniPath.HUNT, '背生击死', '', '', SimUniBlessLevel.STAR_1)
    BLESS_05_024 = SimUniBless(SimUniPath.HUNT, '电射牛斗', '', '', SimUniBlessLevel.STAR_1)

    # 毁灭
    BLESS_06_000 = SimUniBless(SimUniPath.DESTRUCTION, '毁灭', '', '', SimUniBlessLevel.WHOLE)
    BLESS_06_001 = SimUniBless(SimUniPath.DESTRUCTION, '命途回响：「毁灭」', '', '', SimUniBlessLevel.ECHO)
    BLESS_06_002 = SimUniBless(SimUniPath.DESTRUCTION, '回响构音:事件视界', '', '', SimUniBlessLevel.ECHO)
    BLESS_06_003 = SimUniBless(SimUniPath.DESTRUCTION, '回响构音:极端氦闪', '', '', SimUniBlessLevel.ECHO)
    BLESS_06_004 = SimUniBless(SimUniPath.DESTRUCTION, '回响构音:激变变星', '', '', SimUniBlessLevel.ECHO)
    BLESS_06_005 = SimUniBless(SimUniPath.DESTRUCTION, '回响交错:次行星带', '', '', SimUniBlessLevel.ECHO)
    BLESS_06_006 = SimUniBless(SimUniPath.DESTRUCTION, '回响交错:零龄主序', '', '', SimUniBlessLevel.ECHO)
    BLESS_06_007 = SimUniBless(SimUniPath.DESTRUCTION, '湮灭回归不等式', '', '', SimUniBlessLevel.STAR_3)
    BLESS_06_008 = SimUniBless(SimUniPath.DESTRUCTION, '寰宇热寂特征数', '', '', SimUniBlessLevel.STAR_3)
    BLESS_06_009 = SimUniBless(SimUniPath.DESTRUCTION, '反物质非逆方程', '', '', SimUniBlessLevel.STAR_3)
    BLESS_06_010 = SimUniBless(SimUniPath.DESTRUCTION, '戒律性闪变', '', '', SimUniBlessLevel.STAR_2)
    BLESS_06_011 = SimUniBless(SimUniPath.DESTRUCTION, '灾难性共振', '', '', SimUniBlessLevel.STAR_2)
    BLESS_06_012 = SimUniBless(SimUniPath.DESTRUCTION, '破坏性耀发', '', '', SimUniBlessLevel.STAR_2)
    BLESS_06_013 = SimUniBless(SimUniPath.DESTRUCTION, '预兆性景深', '', '', SimUniBlessLevel.STAR_2)
    BLESS_06_014 = SimUniBless(SimUniPath.DESTRUCTION, '毁灭性吸积', '', '', SimUniBlessLevel.STAR_2)
    BLESS_06_015 = SimUniBless(SimUniPath.DESTRUCTION, '危害性余光', '', '', SimUniBlessLevel.STAR_2)
    BLESS_06_016 = SimUniBless(SimUniPath.DESTRUCTION, '递增性末日', '', '', SimUniBlessLevel.STAR_2)
    BLESS_06_017 = SimUniBless(SimUniPath.DESTRUCTION, '永坍缩体', '', '', SimUniBlessLevel.STAR_1)
    BLESS_06_018 = SimUniBless(SimUniPath.DESTRUCTION, '偏振受体', '', '', SimUniBlessLevel.STAR_1)
    BLESS_06_019 = SimUniBless(SimUniPath.DESTRUCTION, '回光效应', '', '', SimUniBlessLevel.STAR_1)
    BLESS_06_020 = SimUniBless(SimUniPath.DESTRUCTION, '不稳定带', '', '', SimUniBlessLevel.STAR_1)
    BLESS_06_021 = SimUniBless(SimUniPath.DESTRUCTION, '原生黑洞', '', '', SimUniBlessLevel.STAR_1)
    BLESS_06_022 = SimUniBless(SimUniPath.DESTRUCTION, '轨道红移', '', '', SimUniBlessLevel.STAR_1)
    BLESS_06_023 = SimUniBless(SimUniPath.DESTRUCTION, '储备度规', '', '', SimUniBlessLevel.STAR_1)
    BLESS_06_024 = SimUniBless(SimUniPath.DESTRUCTION, '哨戒卫星', '', '', SimUniBlessLevel.STAR_1)

    # 欢愉
    BLESS_07_000 = SimUniBless(SimUniPath.ELATION, '欢愉', '', '', SimUniBlessLevel.WHOLE)
    BLESS_07_001 = SimUniBless(SimUniPath.ELATION, '命途回响：「欢愉」', '', '', SimUniBlessLevel.ECHO)
    BLESS_07_002 = SimUniBless(SimUniPath.ELATION, '回响构音:开盖有奖', '', '', SimUniBlessLevel.ECHO)
    BLESS_07_003 = SimUniBless(SimUniPath.ELATION, '回响构音:末日狂欢', '', '', SimUniBlessLevel.ECHO)
    BLESS_07_004 = SimUniBless(SimUniPath.ELATION, '回响构音:树苗长高舞', '', '', SimUniBlessLevel.ECHO)
    BLESS_07_005 = SimUniBless(SimUniPath.ELATION, '回响交错:冰棺与豚鼠', '', '', SimUniBlessLevel.ECHO)
    BLESS_07_006 = SimUniBless(SimUniPath.ELATION, '回响交错:安康鱼之味', '', '', SimUniBlessLevel.ECHO)
    BLESS_07_007 = SimUniBless(SimUniPath.ELATION, '《四号屠场·众生安眠》', '', '', SimUniBlessLevel.STAR_3)
    BLESS_07_008 = SimUniBless(SimUniPath.ELATION, '《自动口琴·茫茫白夜》', '', '', SimUniBlessLevel.STAR_3)
    BLESS_07_009 = SimUniBless(SimUniPath.ELATION, '《冠军晚餐·猫的摇篮》', '', '', SimUniBlessLevel.STAR_3)
    BLESS_07_010 = SimUniBless(SimUniPath.ELATION, '《流吧，你的眼泪》', '', '', SimUniBlessLevel.STAR_2)
    BLESS_07_011 = SimUniBless(SimUniPath.ELATION, '《燃烧男子的肖像》', '', '', SimUniBlessLevel.STAR_2)
    BLESS_07_012 = SimUniBless(SimUniPath.ELATION, '《砂时镜下的幼园》', '', '', SimUniBlessLevel.STAR_2)
    BLESS_07_013 = SimUniBless(SimUniPath.ELATION, '《十二猴子与怒汉》', '', '', SimUniBlessLevel.STAR_2)
    BLESS_07_014 = SimUniBless(SimUniPath.ELATION, '《第二十一条军规》', '', '', SimUniBlessLevel.STAR_2)
    BLESS_07_015 = SimUniBless(SimUniPath.ELATION, '《被涂污的信天翁》', '', '', SimUniBlessLevel.STAR_2)
    BLESS_07_016 = SimUniBless(SimUniPath.ELATION, '《利尔他引力之虹》', '', '', SimUniBlessLevel.STAR_2)
    BLESS_07_017 = SimUniBless(SimUniPath.ELATION, '《基本有害》', '', '', SimUniBlessLevel.STAR_1)
    BLESS_07_018 = SimUniBless(SimUniPath.ELATION, '《阴风阵阵》', '', '', SimUniBlessLevel.STAR_1)
    BLESS_07_019 = SimUniBless(SimUniPath.ELATION, '《回灯塔去》', '', '', SimUniBlessLevel.STAR_1)
    BLESS_07_020 = SimUniBless(SimUniPath.ELATION, '《奇爱医生》', '', '', SimUniBlessLevel.STAR_1)
    BLESS_07_021 = SimUniBless(SimUniPath.ELATION, '《铂金时代》', '', '', SimUniBlessLevel.STAR_1)
    BLESS_07_022 = SimUniBless(SimUniPath.ELATION, '《操行满分》', '', '', SimUniBlessLevel.STAR_1)
    BLESS_07_023 = SimUniBless(SimUniPath.ELATION, '《发条苹果》', '', '', SimUniBlessLevel.STAR_1)
    BLESS_07_024 = SimUniBless(SimUniPath.ELATION, '《灰暗的火》', '', '', SimUniBlessLevel.STAR_1)

    # 繁育
    BLESS_08_000 = SimUniBless(SimUniPath.PROPAGATION, '繁育', '', '', SimUniBlessLevel.WHOLE)
    BLESS_08_001 = SimUniBless(SimUniPath.PROPAGATION, '命途回响：「繁育」', '', '', SimUniBlessLevel.ECHO)
    BLESS_08_002 = SimUniBless(SimUniPath.PROPAGATION, '回响构音:刺吸口器', '', '', SimUniBlessLevel.ECHO)
    BLESS_08_003 = SimUniBless(SimUniPath.PROPAGATION, '回响构音:酚类物质', '', '', SimUniBlessLevel.ECHO)
    BLESS_08_004 = SimUniBless(SimUniPath.PROPAGATION, '回响构音:结晶鳌刺', '', '', SimUniBlessLevel.ECHO)
    BLESS_08_005 = SimUniBless(SimUniPath.PROPAGATION, '回响交错:重叠象眼', '', '', SimUniBlessLevel.ECHO)
    BLESS_08_006 = SimUniBless(SimUniPath.PROPAGATION, '回响交错:附着菌毯', '', '', SimUniBlessLevel.ECHO)
    BLESS_08_007 = SimUniBless(SimUniPath.PROPAGATION, '子囊释放', '', '', SimUniBlessLevel.STAR_3)
    BLESS_08_008 = SimUniBless(SimUniPath.PROPAGATION, '菌种脓疱', '', '', SimUniBlessLevel.STAR_3)
    BLESS_08_009 = SimUniBless(SimUniPath.PROPAGATION, '镰刀肢足', '', '', SimUniBlessLevel.STAR_3)
    BLESS_08_010 = SimUniBless(SimUniPath.PROPAGATION, '腐殖疮', '', '', SimUniBlessLevel.STAR_2)
    BLESS_08_011 = SimUniBless(SimUniPath.PROPAGATION, '裂解酶', '', '', SimUniBlessLevel.STAR_2)
    BLESS_08_012 = SimUniBless(SimUniPath.PROPAGATION, '代谢腔', '', '', SimUniBlessLevel.STAR_2)
    BLESS_08_013 = SimUniBless(SimUniPath.PROPAGATION, '兴奋腺', '', '', SimUniBlessLevel.STAR_2)
    BLESS_08_014 = SimUniBless(SimUniPath.PROPAGATION, '裸脑质', '', '', SimUniBlessLevel.STAR_2)
    BLESS_08_015 = SimUniBless(SimUniPath.PROPAGATION, '节间膜', '', '', SimUniBlessLevel.STAR_2)
    BLESS_08_016 = SimUniBless(SimUniPath.PROPAGATION, '催化剂', '', '', SimUniBlessLevel.STAR_2)
    BLESS_08_017 = SimUniBless(SimUniPath.PROPAGATION, '骨刃', '', '', SimUniBlessLevel.STAR_1)
    BLESS_08_018 = SimUniBless(SimUniPath.PROPAGATION, '脊刺', '', '', SimUniBlessLevel.STAR_1)
    BLESS_08_019 = SimUniBless(SimUniPath.PROPAGATION, '槽针', '', '', SimUniBlessLevel.STAR_1)
    BLESS_08_020 = SimUniBless(SimUniPath.PROPAGATION, '结膜', '', '', SimUniBlessLevel.STAR_1)
    BLESS_08_021 = SimUniBless(SimUniPath.PROPAGATION, '鳞翅', '', '', SimUniBlessLevel.STAR_1)
    BLESS_08_022 = SimUniBless(SimUniPath.PROPAGATION, '复眼', '', '', SimUniBlessLevel.STAR_1)
    BLESS_08_023 = SimUniBless(SimUniPath.PROPAGATION, '孢夹', '', '', SimUniBlessLevel.STAR_1)
    BLESS_08_024 = SimUniBless(SimUniPath.PROPAGATION, '液囊', '', '', SimUniBlessLevel.STAR_1)

    # 智识
    BLESS_09_000 = SimUniBless(SimUniPath.ERUDITION, '智识', '', '', SimUniBlessLevel.WHOLE)
    BLESS_09_001 = SimUniBless(SimUniPath.ERUDITION, '命途回响：「智识」', '', '', SimUniBlessLevel.ECHO)
    BLESS_09_002 = SimUniBless(SimUniPath.ERUDITION, '回响构音:核心熔毁', '', '', SimUniBlessLevel.ECHO)
    BLESS_09_003 = SimUniBless(SimUniPath.ERUDITION, '回响构音:连带传染', '', '', SimUniBlessLevel.ECHO)
    BLESS_09_004 = SimUniBless(SimUniPath.ERUDITION, '回响构音:模因逆推', '', '', SimUniBlessLevel.ECHO)
    BLESS_09_005 = SimUniBless(SimUniPath.ERUDITION, '回响交错:全盘扫描', '', '', SimUniBlessLevel.ECHO)
    BLESS_09_006 = SimUniBless(SimUniPath.ERUDITION, '回响交错:数据加固', '', '', SimUniBlessLevel.ECHO)
    BLESS_09_007 = SimUniBless(SimUniPath.ERUDITION, 'BCI-34型灰质', '', '', SimUniBlessLevel.STAR_3)
    BLESS_09_008 = SimUniBless(SimUniPath.ERUDITION, 'SMR-2型杏仁核', '', '', SimUniBlessLevel.STAR_3)
    BLESS_09_009 = SimUniBless(SimUniPath.ERUDITION, 'VEP-18型枕叶', '', '', SimUniBlessLevel.STAR_3)
    BLESS_09_010 = SimUniBless(SimUniPath.ERUDITION, '附加:前庭系统', '', '', SimUniBlessLevel.STAR_2)
    BLESS_09_011 = SimUniBless(SimUniPath.ERUDITION, '模仿:递质合成', '', '', SimUniBlessLevel.STAR_2)
    BLESS_09_012 = SimUniBless(SimUniPath.ERUDITION, '植入:外显记忆', '', '', SimUniBlessLevel.STAR_2)
    BLESS_09_013 = SimUniBless(SimUniPath.ERUDITION, '拟态:触觉通路', '', '', SimUniBlessLevel.STAR_2)
    BLESS_09_014 = SimUniBless(SimUniPath.ERUDITION, '分析:闻下知觉', '', '', SimUniBlessLevel.STAR_2)
    BLESS_09_015 = SimUniBless(SimUniPath.ERUDITION, '装载:纹状皮层', '', '', SimUniBlessLevel.STAR_2)
    BLESS_09_016 = SimUniBless(SimUniPath.ERUDITION, '激发:跳跃传导', '', '', SimUniBlessLevel.STAR_2)
    BLESS_09_017 = SimUniBless(SimUniPath.ERUDITION, '齿轮啮合的王座', '', '', SimUniBlessLevel.STAR_1)
    BLESS_09_018 = SimUniBless(SimUniPath.ERUDITION, '导线弯绕的指环', '', '', SimUniBlessLevel.STAR_1)
    BLESS_09_019 = SimUniBless(SimUniPath.ERUDITION, '能量变矩的权杖', '', '', SimUniBlessLevel.STAR_1)
    BLESS_09_020 = SimUniBless(SimUniPath.ERUDITION, '偏时引燃的炬火', '', '', SimUniBlessLevel.STAR_1)
    BLESS_09_021 = SimUniBless(SimUniPath.ERUDITION, '延迟衍射的烛光', '', '', SimUniBlessLevel.STAR_1)
    BLESS_09_022 = SimUniBless(SimUniPath.ERUDITION, '金属斑驳的华盖', '', '', SimUniBlessLevel.STAR_1)
    BLESS_09_023 = SimUniBless(SimUniPath.ERUDITION, '线圈编织的罗绮', '', '', SimUniBlessLevel.STAR_1)
    BLESS_09_024 = SimUniBless(SimUniPath.ERUDITION, '管道交错的桂冠', '', '', SimUniBlessLevel.STAR_1)


PATH_BLESS_LIST: dict[str, List[SimUniBless]] = {}
for _bless_enum in SimUniBlessEnum:
    _bless: SimUniBless = _bless_enum.value
    _path = _bless.path

    if _path.value not in PATH_BLESS_LIST:
        PATH_BLESS_LIST[_path.value] = []

    PATH_BLESS_LIST[_path.value].append(_bless)


def match_best_bless_by_ocr(title_ocr: str, path_ocr: str) -> Optional[SimUniBless]:
    """
    根据OCR结果，匹配一个最合适的祝福
    :param title_ocr: OCR得到的祝福名称
    :param path_ocr: OCR得到的命途名称
    :return:
    """
    path = match_best_path_by_ocr(path_ocr)
    if path is None:
        return None

    bless_list = PATH_BLESS_LIST[path.value]
    target_title_list = [gt(bless.title, 'ocr') for bless in bless_list if bless.title != bless.path.value]

    idx = str_utils.find_best_match_by_lcs(title_ocr, target_title_list)
    if idx is None:  # 未录入的祝福
        return bless_list[0]
    else:
        return bless_list[idx + 1]


def bless_enum_from_title(bless_title: str) -> Optional[SimUniBlessEnum]:
    for bless in SimUniBlessEnum:
        if bless_title == gt(bless.value.title, 'ocr'):
            return bless
    return None


class SimUniCurio:

    def __init__(self, name: str, py: str, negative: bool = False, invalid_after_got: bool = False):
        self.name: str = name
        self.py: str = py
        self.negative: bool = negative  # 负面奇物
        self.invalid_after_got: bool = invalid_after_got  # 得到后立刻生效 然后变成无效奇物

    def __repr__(self):
        return self.name


# https://bbs.mihoyo.com/sr/wiki/content/816/detail?bbs_presentation_style=no_header
# 2023.01.13 1.6版本更新 只有普通模拟宇宙的
class SimUniCurioEnum(Enum):

    CURIO_000 = SimUniCurio('未知奇物', 'wzqw')
    CURIO_001 = SimUniCurio('家族缘结', 'jzyj')
    CURIO_002 = SimUniCurio('黑洞之阱', 'hdzj')
    CURIO_003 = SimUniCurio('天才俱乐部普通八卦', 'tcjlbptbg')
    CURIO_004 = SimUniCurio('混沌特效灵药', 'hdtxly')
    CURIO_005 = SimUniCurio('鲁珀特帝国机械齿轮', 'lbtdgjxcl')
    CURIO_006 = SimUniCurio('龋齿星系模型', 'qcxxmx')
    CURIO_007 = SimUniCurio('愚者面具', 'yzmj')
    CURIO_008 = SimUniCurio('虚构机兵', 'xgjb')
    CURIO_009 = SimUniCurio('人造陨石球', 'rzysq')
    CURIO_010 = SimUniCurio('塔拉毒火焰', 'tldhy')
    CURIO_011 = SimUniCurio('降维骰子', 'jwsz')
    CURIO_012 = SimUniCurio('万象无常骰', 'wxwcs', invalid_after_got=True)
    CURIO_013 = SimUniCurio('闪耀的偏方三八面骰', 'sydpsbms', invalid_after_got=True)
    CURIO_014 = SimUniCurio('混沌云芝', 'hdlz')
    CURIO_015 = SimUniCurio('跃迁复眼', 'yqfy')
    CURIO_016 = SimUniCurio('异木果实', 'ymgs')
    CURIO_017 = SimUniCurio('测不准匣', 'cbzx', invalid_after_got=True)
    CURIO_018 = SimUniCurio('香涎干酪', 'xygl')
    CURIO_019 = SimUniCurio('福灵胶', 'flj')
    CURIO_020 = SimUniCurio('永不停嘴的羊皮卷', 'ybtzdypj')
    CURIO_021 = SimUniCurio('博士之袍', 'bszp')
    CURIO_022 = SimUniCurio('纯美之袍', 'cmzp')
    CURIO_023 = SimUniCurio('俱乐部券', 'jlbq')
    CURIO_024 = SimUniCurio('信仰债券', 'xyzq')
    CURIO_025 = SimUniCurio('分裂金币', 'fljb')
    CURIO_026 = SimUniCurio('分裂银币', 'flyb')
    CURIO_027 = SimUniCurio('空无烛剪', 'kwzj', invalid_after_got=True)
    CURIO_028 = SimUniCurio('湮灭烛剪', 'ymzj')
    CURIO_029 = SimUniCurio('天外重声大碟', 'twcsdd')
    CURIO_030 = SimUniCurio('存护火漆', 'chhq')
    CURIO_031 = SimUniCurio('欢愉火漆', 'hyhq')
    CURIO_032 = SimUniCurio('巡猎火漆', 'xlhq')
    CURIO_033 = SimUniCurio('毁灭火漆', 'hmhq')
    CURIO_034 = SimUniCurio('记忆火漆', 'jyhq')
    CURIO_035 = SimUniCurio('虚无火漆', 'xwhq')
    CURIO_036 = SimUniCurio('丰饶火漆', 'frhq')
    CURIO_037 = SimUniCurio('智识火漆', 'zshq')
    CURIO_038 = SimUniCurio('繁育火漆', 'fyhq')
    CURIO_039 = SimUniCurio('乱七八糟的代码', 'lqbzddm')
    CURIO_040 = SimUniCurio('有点蹊跷的代码', 'ydqqddm')
    CURIO_041 = SimUniCurio('中规中矩的代码', 'zgzjddm')
    CURIO_042 = SimUniCurio('精确优雅的代码', 'jqyyddm')
    CURIO_043 = SimUniCurio('没有注释的代码', 'myzsddm')
    CURIO_044 = SimUniCurio('无限递归的代码', 'wxdgddm')
    CURIO_045 = SimUniCurio('碎星芳饵', 'sxfe')
    CURIO_046 = SimUniCurio('虫网', 'cw', negative=True)
    CURIO_047 = SimUniCurio('天使型谢债发行机', 'tsxxzfxj')
    CURIO_048 = SimUniCurio('换境桂冠', 'hjgg')
    CURIO_049 = SimUniCurio('时空棱镜', 'sklj')
    CURIO_050 = SimUniCurio('银河大乐透', 'yhdlt')
    CURIO_051 = SimUniCurio('星际大乐透', 'xjdlt')
    CURIO_052 = SimUniCurio('万识囊', 'wsl')
    CURIO_053 = SimUniCurio('卜筵咕咕钟', 'pyggz', negative=True)
    CURIO_054 = SimUniCurio('黑森林咕咕钟', 'hslggz', negative=True)
    CURIO_055 = SimUniCurio('永动咕咕钟', 'ydggz', negative=True)
    CURIO_056 = SimUniCurio('公司咕咕钟', 'gsggz', negative=True)
    CURIO_057 = SimUniCurio('机械咕咕钟', 'jxggz', negative=True)
    CURIO_058 = SimUniCurio('分裂咕咕钟', 'flggz', negative=True)
    CURIO_059 = SimUniCurio('信标着色剂', 'xbzsj')
    CURIO_060 = SimUniCurio('粉红冲撞', 'fhcz')


def match_best_curio_by_ocr(name_ocr: str) -> Optional[SimUniCurio]:
    """
    根据OCR结果，匹配一个最合适的奇物
    :param name_ocr: OCR得到的奇物名称
    :return:
    """
    target_list = [gt(c.value.name, 'ocr') for c in SimUniCurioEnum.__members__.values()]
    idx = str_utils.find_best_match_by_lcs(name_ocr, target_list)
    if idx is not None:
        return SimUniCurioEnum['CURIO_%03d' % idx].value
    else:
        return None


def curio_enum_from_name(name: str) -> Optional[SimUniCurioEnum]:
    for curio in SimUniCurioEnum:
        if name == gt(curio.value.name, 'ocr'):
            return curio
    return None
