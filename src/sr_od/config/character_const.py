from typing import List, Optional

from one_dragon.utils import str_utils
from one_dragon.utils.i18_utils import gt


class CharacterPath:

    def __init__(self, id: str, cn: str):
        """
        角色命途
        :param id: 唯一标识
        :param cn: 中文名称
        """

        self.id: str = id
        """命途唯一标识"""
        self.cn: str = cn
        """命途中文名称"""


CHARACTER_PATH_DESTRUCTION = CharacterPath(id='destruction', cn='毁灭')
CHARACTER_PATH_PRESERVATION = CharacterPath(id='preservation', cn='存护')
CHARACTER_PATH_HUNT = CharacterPath(id='hunt', cn='巡猎')
CHARACTER_PATH_ABUNDANCE = CharacterPath(id='abundance', cn='丰饶')
CHARACTER_PATH_NIHILITY = CharacterPath(id='nihility', cn='虚无')
CHARACTER_PATH_ERUDITION = CharacterPath(id='erudition', cn='智识')
CHARACTER_PATH_HARMONY = CharacterPath(id='harmony', cn='同谐')
CHARACTER_PATH_REMEMBRANCE = CharacterPath(id='remembrance', cn='记忆')

CHARACTER_PATH_LIST: List[CharacterPath] = [
    CHARACTER_PATH_DESTRUCTION,
    CHARACTER_PATH_PRESERVATION,
    CHARACTER_PATH_HUNT,
    CHARACTER_PATH_ABUNDANCE,
    CHARACTER_PATH_NIHILITY,
    CHARACTER_PATH_ERUDITION,
    CHARACTER_PATH_HARMONY,
    CHARACTER_PATH_REMEMBRANCE,
]

ATTACK_PATH_LIST: List[CharacterPath] = [CHARACTER_PATH_DESTRUCTION, CHARACTER_PATH_HUNT, CHARACTER_PATH_ERUDITION, CHARACTER_PATH_REMEMBRANCE]
"""输出命途"""

SURVIVAL_PATH_LIST: List[CharacterPath] = [CHARACTER_PATH_PRESERVATION, CHARACTER_PATH_ABUNDANCE]
"""生存命途"""

SUPPORT_PATH_LIST: List[CharacterPath] = [CHARACTER_PATH_NIHILITY, CHARACTER_PATH_HARMONY]
"""辅助命途"""


class CharacterCombatType:

    def __init__(self, id: str, cn: str):
        """
        角色属性
        :param id: 唯一标识
        :param cn: 中文名称
        """

        self.id: str = id
        """属性唯一标识"""
        self.cn: str = cn
        """属性中文名称"""

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other) -> bool:
        return self.id == other.id


QUANTUM = CharacterCombatType(id='quantum', cn='量子')
PHYSICAL = CharacterCombatType(id='physical', cn='物理')
IMAGINARY = CharacterCombatType(id='imaginary', cn='虚数')
FIRE = CharacterCombatType(id='fire', cn='火')
LIGHTNING = CharacterCombatType(id='lightning', cn='雷')
ICE = CharacterCombatType(id='ice', cn='冰')
WIND = CharacterCombatType(id='wind', cn='风')

CHARACTER_COMBAT_TYPE_LIST = [
    QUANTUM,
    PHYSICAL,
    IMAGINARY,
    FIRE,
    LIGHTNING,
    ICE,
    WIND,
]


def get_combat_type_by_id(combat_type_id: str) -> Optional[CharacterCombatType]:
    """
    根据ID获取属性
    :param combat_type_id:
    :return:
    """
    for ct in CHARACTER_COMBAT_TYPE_LIST:
        if ct.id == combat_type_id:
            return ct
    return None


class CharacterTechniqueType:

    def __init__(self, id: str, remark: str):
        """
        角色秘技类型
        :param id: 唯一标识
        :param remark: 备注
        """

        self.id: str = id
        """唯一标识"""
        self.remark: str = remark
        """备注"""


TECHNIQUE_BUFF = CharacterTechniqueType(id='buff', remark='BUFF类')
TECHNIQUE_AREA = CharacterTechniqueType(id='buff_area', remark='领域')
TECHNIQUE_BUFF_ATTACK = CharacterTechniqueType(id='buff_attack', remark='需攻击触发BUFF类')
TECHNIQUE_ATTACK = CharacterTechniqueType(id='attack', remark='攻击类')
TECHNIQUE_BUFF_ATTACK_DISAPPEAR = CharacterTechniqueType(id='buff_attack', remark='需攻击触发BUFF类 攻击后消失')


class Character:

    def __init__(self, id: str, cn: str, path: CharacterPath, combat_type: CharacterCombatType, level: int, technique_type: CharacterTechniqueType,
                 buff_lasting_seconds: float = 20):
        """
        角色秘技类型
        :param id: 角色唯一标识
        :param cn: 备注
        :param path: 命途
        :param combat_type: 属性
        :param level:
        :param technique_type:
        """

        self.id: str = id
        """角色唯一标识"""
        self.cn: str = cn
        """角色中文名称"""
        self.path: CharacterPath = path
        """命途"""
        self.combat_type: CharacterCombatType = combat_type
        """属性"""
        self.level: int = level
        """星级"""
        self.technique_type: CharacterTechniqueType = technique_type
        """秘技类型"""
        self.buff_lasting_seconds: float = buff_lasting_seconds  # BUFF持续时间

    def __lt__(self, other):
        return self.level > other.level \
            or (self.level == other.level and self.id < other.id)

    def __eq__(self, other):
        return self.level == other.level and self.id == other.id

    def __gt__(self, other):
        return self.level > other.level or (self.level == other.level and self.id < other.id)


ARLAN = Character(id='arlan', cn='阿兰', path=CHARACTER_PATH_DESTRUCTION, combat_type=LIGHTNING, level=4, technique_type=TECHNIQUE_ATTACK)
ASTA = Character(id='asta', cn='艾丝妲', path=CHARACTER_PATH_HARMONY, combat_type=FIRE, level=4, technique_type=TECHNIQUE_ATTACK)
BAILU = Character(id='bailu', cn='白露', path=CHARACTER_PATH_ABUNDANCE, combat_type=LIGHTNING, level=5, technique_type=TECHNIQUE_BUFF)
BLADE = Character(id='blade', cn='刃', path=CHARACTER_PATH_DESTRUCTION, combat_type=WIND, level=5, technique_type=TECHNIQUE_ATTACK)
BRONYA = Character(id='bronya', cn='布洛妮娅', path=CHARACTER_PATH_HARMONY, combat_type=WIND, level=5, technique_type=TECHNIQUE_BUFF)
CAELUM_DESTRUCTION = Character(id='caelum_destruction', cn='男主毁灭', path=CHARACTER_PATH_DESTRUCTION, combat_type=PHYSICAL, level=4, technique_type=TECHNIQUE_BUFF)
CAELUM_PRESERVATION = Character(id='caelum_preservation', cn='男主存护', path=CHARACTER_PATH_PRESERVATION, combat_type=FIRE, level=4, technique_type=TECHNIQUE_BUFF)
CAELUM_HARMONY = Character(id='caelum_harmony', cn='男主同谐', path=CHARACTER_PATH_HARMONY, combat_type=IMAGINARY, level=4, technique_type=TECHNIQUE_BUFF)
CAELUM_REMEMBRANCE = Character(id='caelum_remembrance', cn='男主记忆', path=CHARACTER_PATH_REMEMBRANCE, combat_type=ICE, level=4, technique_type=TECHNIQUE_AREA)
CLARA = Character(id='clara', cn='克拉拉', path=CHARACTER_PATH_DESTRUCTION, combat_type=PHYSICAL, level=5, technique_type=TECHNIQUE_ATTACK)
DANHENG = Character(id='danheng', cn='丹恒', path=CHARACTER_PATH_HUNT, combat_type=WIND, level=4, technique_type=TECHNIQUE_BUFF)
DANHENGIMBIBITORLUNAE = Character(id='danhengimbibitorlunae', cn='丹恒·饮月', path=CHARACTER_PATH_DESTRUCTION, combat_type=IMAGINARY, level=5, technique_type=TECHNIQUE_BUFF_ATTACK)
FUXUAN = Character(id='fuxuan', cn='符玄', path=CHARACTER_PATH_PRESERVATION, combat_type=QUANTUM, level=5, technique_type=TECHNIQUE_BUFF)
GEPARD = Character(id='gepard', cn='杰帕德', path=CHARACTER_PATH_PRESERVATION, combat_type=ICE, level=5, technique_type=TECHNIQUE_BUFF)
GUINAIFEN = Character(id='guinaifen', cn='桂乃芬', path=CHARACTER_PATH_NIHILITY, combat_type=FIRE, level=4, technique_type=TECHNIQUE_ATTACK)
HERTA = Character(id='herta', cn='黑塔', path=CHARACTER_PATH_ERUDITION, combat_type=ICE, level=4, technique_type=TECHNIQUE_BUFF)
HIMEKO = Character(id='himeko', cn='姬子', path=CHARACTER_PATH_ERUDITION, combat_type=FIRE, level=5, technique_type=TECHNIQUE_BUFF)
HOOK = Character(id='hook', cn='虎克', path=CHARACTER_PATH_DESTRUCTION, combat_type=FIRE, level=4, technique_type=TECHNIQUE_ATTACK)
HUOHUO = Character(id='huohuo', cn='藿藿', path=CHARACTER_PATH_ABUNDANCE, combat_type=WIND, level=5, technique_type=TECHNIQUE_BUFF)
JINGLIU = Character(id='jingliu', cn='镜流', path=CHARACTER_PATH_DESTRUCTION, combat_type=ICE, level=5, technique_type=TECHNIQUE_BUFF_ATTACK)
JINGYUAN = Character(id='jingyuan', cn='景元', path=CHARACTER_PATH_ERUDITION, combat_type=LIGHTNING, level=5, technique_type=TECHNIQUE_BUFF)
KAFKA = Character(id='kafka', cn='卡芙卡', path=CHARACTER_PATH_NIHILITY, combat_type=LIGHTNING, level=5, technique_type=TECHNIQUE_ATTACK)
LUKA = Character(id='luka', cn='卢卡', path=CHARACTER_PATH_NIHILITY, combat_type=PHYSICAL, level=4, technique_type=TECHNIQUE_ATTACK)
LUOCHA = Character(id='luocha', cn='罗刹', path=CHARACTER_PATH_ABUNDANCE, combat_type=IMAGINARY, level=5, technique_type=TECHNIQUE_BUFF)
LYNX = Character(id='lynx', cn='玲可', path=CHARACTER_PATH_ABUNDANCE, combat_type=QUANTUM, level=4, technique_type=TECHNIQUE_BUFF)
MARCH7TH_PRESERVATION = Character(id='march7th_preservation', cn='三月七存护', path=CHARACTER_PATH_PRESERVATION, combat_type=ICE, level=4, technique_type=TECHNIQUE_ATTACK)
MARCH7TH_HUNT = Character(id='march7th_hunt', cn='三月七巡猎', path=CHARACTER_PATH_HUNT, combat_type=IMAGINARY, level=4, technique_type=TECHNIQUE_BUFF)
NATASHA = Character(id='natasha', cn='娜塔莎', path=CHARACTER_PATH_ABUNDANCE, combat_type=PHYSICAL, level=4, technique_type=TECHNIQUE_ATTACK)
PELA = Character(id='pela', cn='佩拉', path=CHARACTER_PATH_NIHILITY, combat_type=ICE, level=4, technique_type=TECHNIQUE_ATTACK)
QINGQUE = Character(id='qingque', cn='青雀', path=CHARACTER_PATH_ERUDITION, combat_type=QUANTUM, level=4, technique_type=TECHNIQUE_BUFF)
SAMPO = Character(id='sampo', cn='桑博', path=CHARACTER_PATH_NIHILITY, combat_type=WIND, level=4, technique_type=TECHNIQUE_BUFF)
SEELE = Character(id='seele', cn='希儿', path=CHARACTER_PATH_HUNT, combat_type=QUANTUM, level=5, technique_type=TECHNIQUE_BUFF_ATTACK)
SERVAL = Character(id='serval', cn='希露瓦', path=CHARACTER_PATH_ERUDITION, combat_type=LIGHTNING, level=4, technique_type=TECHNIQUE_ATTACK)
SILVERWOLF = Character(id='silverwolf', cn='银狼', path=CHARACTER_PATH_NIHILITY, combat_type=QUANTUM, level=5, technique_type=TECHNIQUE_ATTACK)
STELLE_DESTRUCTION = Character(id='stelle_destruction', cn='女主毁灭', path=CHARACTER_PATH_DESTRUCTION, combat_type=PHYSICAL, level=4, technique_type=TECHNIQUE_BUFF)
STELLE_PRESERVATION = Character(id='stelle_preservation', cn='女主存护', path=CHARACTER_PATH_PRESERVATION, combat_type=FIRE, level=4, technique_type=TECHNIQUE_BUFF)
STELLE_HARMONY = Character(id='stelle_harmony', cn='女主同谐', path=CHARACTER_PATH_HARMONY, combat_type=IMAGINARY, level=4, technique_type=TECHNIQUE_BUFF)
STELLE_REMEMBRANCE = Character(id='stelle_remembrance', cn='女主记忆', path=CHARACTER_PATH_REMEMBRANCE, combat_type=ICE, level=4, technique_type=TECHNIQUE_AREA)
SUSHANG = Character(id='sushang', cn='素裳', path=CHARACTER_PATH_HUNT, combat_type=PHYSICAL, level=4, technique_type=TECHNIQUE_ATTACK)
TINGYUN = Character(id='tingyun', cn='停云', path=CHARACTER_PATH_HARMONY, combat_type=LIGHTNING, level=4, technique_type=TECHNIQUE_BUFF)
TOPAZNUMBY = Character(id='topaznumby', cn='托帕&账账', path=CHARACTER_PATH_HUNT, combat_type=FIRE, level=5, technique_type=TECHNIQUE_BUFF)
WELT = Character(id='welt', cn='瓦尔特', path=CHARACTER_PATH_NIHILITY, combat_type=IMAGINARY, level=5, technique_type=TECHNIQUE_BUFF)
YANQING = Character(id='yanqing', cn='彦卿', path=CHARACTER_PATH_HUNT, combat_type=ICE, level=5, technique_type=TECHNIQUE_BUFF)
YUKONG = Character(id='yukong', cn='驭空', path=CHARACTER_PATH_HARMONY, combat_type=IMAGINARY, level=4, technique_type=TECHNIQUE_BUFF_ATTACK)
ARGENTI = Character(id='argenti', cn='银枝', path=CHARACTER_PATH_ERUDITION, combat_type=PHYSICAL, level=5, technique_type=TECHNIQUE_BUFF_ATTACK)
HANYA = Character(id='hanya', cn='寒鸦', path=CHARACTER_PATH_HARMONY, combat_type=PHYSICAL, level=4, technique_type=TECHNIQUE_ATTACK)
RUANMEI = Character(id='ruanmei', cn='阮·梅', path=CHARACTER_PATH_HARMONY, combat_type=ICE, level=5, technique_type=TECHNIQUE_BUFF,
                    buff_lasting_seconds=999)
XUEYI = Character(id='xueyi', cn='雪衣', path=CHARACTER_PATH_DESTRUCTION, combat_type=QUANTUM, level=4, technique_type=TECHNIQUE_ATTACK)
DRRATIO = Character(id='drratio', cn='真理医生', path=CHARACTER_PATH_HUNT, combat_type=IMAGINARY, level=5, technique_type=TECHNIQUE_BUFF)
MISHA = Character(id='misha', cn='米沙', path=CHARACTER_PATH_DESTRUCTION, combat_type=ICE, level=4, technique_type=TECHNIQUE_AREA)
BLACKSWAN = Character(id='blackswan', cn='黑天鹅', path=CHARACTER_PATH_NIHILITY, combat_type=WIND, level=5, technique_type=TECHNIQUE_BUFF)
SPARKLE = Character(id='sparkle', cn='花火', path=CHARACTER_PATH_HARMONY, combat_type=QUANTUM, level=5, technique_type=TECHNIQUE_BUFF)
GALLAGHER = Character(id='gallagher', cn='加拉赫', path=CHARACTER_PATH_ABUNDANCE, combat_type=FIRE, level=4, technique_type=TECHNIQUE_ATTACK)
ACHERON = Character(id='acheron', cn='黄泉', path=CHARACTER_PATH_NIHILITY, combat_type=LIGHTNING, level=5, technique_type=TECHNIQUE_ATTACK)
AVENTURINE = Character(id='aventurine', cn='砂金', path=CHARACTER_PATH_PRESERVATION, combat_type=IMAGINARY, level=5, technique_type=TECHNIQUE_BUFF)
ROBIN = Character(id='robin', cn='知更鸟', path=CHARACTER_PATH_HARMONY, combat_type=PHYSICAL, level=5, technique_type=TECHNIQUE_AREA)
BOOTHILL = Character(id='boothill', cn='波提欧', path=CHARACTER_PATH_HUNT, combat_type=PHYSICAL, level=5, technique_type=TECHNIQUE_BUFF)
FIREFLY = Character(id='firefly', cn='流萤', path=CHARACTER_PATH_DESTRUCTION, combat_type=FIRE, level=5, technique_type=TECHNIQUE_BUFF_ATTACK_DISAPPEAR,
                    buff_lasting_seconds=5)
JADE = Character(id='jade', cn='翡翠', path=CHARACTER_PATH_ERUDITION, combat_type=QUANTUM, level=5, technique_type=TECHNIQUE_BUFF_ATTACK)
YUNLI = Character(id='yunli', cn='云璃', path=CHARACTER_PATH_DESTRUCTION, combat_type=PHYSICAL, level=5, technique_type=TECHNIQUE_BUFF_ATTACK)
FEIXIAO = Character(id='feixiao', cn='飞霄', path=CHARACTER_PATH_HUNT, combat_type=WIND, level=5, technique_type=TECHNIQUE_BUFF_ATTACK_DISAPPEAR,
                    buff_lasting_seconds=20)
MOZE = Character(id='moze', cn='貊泽', path=CHARACTER_PATH_HUNT, combat_type=LIGHTNING, level=4, technique_type=TECHNIQUE_BUFF_ATTACK)
LINGSHA = Character(id='lingsha', cn='灵砂', path=CHARACTER_PATH_ABUNDANCE, combat_type=FIRE, level=5, technique_type=TECHNIQUE_BUFF)
JIAOQIU = Character(id='jiaoqiu', cn='椒丘', path=CHARACTER_PATH_NIHILITY, combat_type=FIRE, level=5, technique_type=TECHNIQUE_AREA)
RAPPA = Character(id='rappa', cn='乱破', path=CHARACTER_PATH_ERUDITION, combat_type=IMAGINARY, level=5, technique_type=TECHNIQUE_BUFF_ATTACK)
SUNDAY = Character(id='sunday', cn='星期日', path=CHARACTER_PATH_HARMONY, combat_type=IMAGINARY, level=5, technique_type=TECHNIQUE_BUFF)
FUGUE = Character(id='fugue', cn='忘归人', path=CHARACTER_PATH_HARMONY, combat_type=FIRE, level=5, technique_type=TECHNIQUE_BUFF)
THE_HERTA = Character(id='the_herta', cn='大黑塔', path=CHARACTER_PATH_ERUDITION, combat_type=ICE, level=5, technique_type=TECHNIQUE_BUFF)
AGLAEA = Character(id='aglaea', cn='阿格莱雅', path=CHARACTER_PATH_REMEMBRANCE, combat_type=LIGHTNING, level=5, technique_type=TECHNIQUE_ATTACK)
TRIBBIE = Character(id='tribbie', cn='缇宝', path=CHARACTER_PATH_HARMONY, combat_type=QUANTUM, level=5, technique_type=TECHNIQUE_BUFF)
CASORICE = Character(id='casorice', cn='遐蝶', path=CHARACTER_PATH_REMEMBRANCE, combat_type=QUANTUM, level=5, technique_type=TECHNIQUE_BUFF_ATTACK)
HYACINE = Character(id='hyacine', cn='风堇', path=CHARACTER_PATH_REMEMBRANCE, combat_type=WIND, level=5, technique_type=TECHNIQUE_BUFF)
PHAINON = Character(id='phainon', cn='白厄', path=CHARACTER_PATH_DESTRUCTION, combat_type=PHYSICAL, level=5, technique_type=TECHNIQUE_ATTACK)
ARCHER = Character(id='archer', cn='Archer', path=CHARACTER_PATH_HUNT, combat_type=QUANTUM, level=5, technique_type=TECHNIQUE_ATTACK)
SABER = Character(id='saber', cn='Saber', path=CHARACTER_PATH_DESTRUCTION, combat_type=WIND, level=5, technique_type=TECHNIQUE_BUFF)
ANAXA = Character(id='anaxa', cn='那刻夏', path=CHARACTER_PATH_ERUDITION, combat_type=WIND, level=5, technique_type=TECHNIQUE_BUFF)
HYSILENS = Character(id='hysilens', cn='海瑟音', path=CHARACTER_PATH_NIHILITY, combat_type=PHYSICAL, level=5, technique_type=TECHNIQUE_AREA)
CERYDRA = Character(id='cerydra', cn='刻律德菈', path=CHARACTER_PATH_HARMONY, combat_type=WIND, level=5, technique_type=TECHNIQUE_BUFF)
MYDEI = Character(id='mydei', cn='万敌', path=CHARACTER_PATH_DESTRUCTION, combat_type=PHYSICAL, level=5, technique_type=TECHNIQUE_BUFF_ATTACK)
EVERNIGHT = Character(id='evernight', cn='长夜月', path=CHARACTER_PATH_REMEMBRANCE, combat_type=ICE, level=5, technique_type=TECHNIQUE_BUFF)
DANHENGPERMANSORTERRAE = Character(id='danhengpermansorterrae', cn='丹恒·腾荒', path=CHARACTER_PATH_PRESERVATION, combat_type=PHYSICAL, level=5, technique_type=TECHNIQUE_BUFF)


CHARACTER_LIST: List[Character] = [
    ARLAN,
    ASTA,
    BAILU,
    BLADE,
    BRONYA,
    CAELUM_DESTRUCTION,
    CAELUM_PRESERVATION,
    CAELUM_HARMONY,
    CAELUM_REMEMBRANCE,
    CLARA,
    DANHENG,
    DANHENGIMBIBITORLUNAE,
    FUXUAN,
    GEPARD,
    GUINAIFEN,
    HERTA,
    HIMEKO,
    HOOK,
    HUOHUO,
    JINGLIU,
    JINGYUAN,
    KAFKA,
    LUKA,
    LUOCHA,
    LYNX,
    MARCH7TH_PRESERVATION,
    MARCH7TH_HUNT,
    NATASHA,
    PELA,
    QINGQUE,
    SAMPO,
    SEELE,
    SERVAL,
    SILVERWOLF,
    STELLE_DESTRUCTION,
    STELLE_PRESERVATION,
    STELLE_HARMONY,
    STELLE_REMEMBRANCE,
    SUSHANG,
    TINGYUN,
    TOPAZNUMBY,
    WELT,
    YANQING,
    YUKONG,
    ARGENTI,
    HANYA,
    RUANMEI,
    XUEYI,
    DRRATIO,
    MISHA,
    BLACKSWAN,
    SPARKLE,
    GALLAGHER,
    ACHERON,
    AVENTURINE,
    ROBIN,
    BOOTHILL,
    FIREFLY,
    JADE,
    YUNLI,
    FEIXIAO,
    MOZE,
    LINGSHA,
    JIAOQIU,
    RAPPA,
    SUNDAY,
    FUGUE,
    THE_HERTA,
    AGLAEA,
    TRIBBIE,
    CASORICE,
    HYACINE,
    PHAINON,
    ARCHER,
    SABER,
    ANAXA,
    HYSILENS,
    CERYDRA,
    MYDEI,
    EVERNIGHT,
    DANHENGPERMANSORTERRAE,
]


def filter_character_list(destiny_id: Optional[str] = None,
                          combat_type_id: Optional[str] = None,
                          level: Optional[int] = None,
                          character_name: Optional[str] = None) -> List[Character]:
    filter_list = []

    for c in CHARACTER_LIST:
        if destiny_id is not None and c.path.id != destiny_id:
            continue
        if combat_type_id is not None and c.combat_type.id != combat_type_id:
            continue
        if level is not None and c.level != level:
            continue
        if character_name is not None and not str_utils.find_by_lcs(character_name, gt(c.cn), percent=1):
            continue

        filter_list.append(c)

    filter_list.sort()

    return filter_list


def get_character_by_id(c_id: str) -> Optional[Character]:
    for c in CHARACTER_LIST:
        if c.id == c_id:
            return c
    return None


SPECIAL_ATTACK_CHARACTER_LIST = [
    KAFKA,
    ACHERON
]


def is_attack_character(character_id: str) -> bool:
    """
    是否输出位角色
    - 巡猎、毁灭、智识 命途
    - 其它命途的特殊角色
    :param character_id:
    :return:
    """
    character = get_character_by_id(character_id)
    if character is None:
        return False
    if character.path in ATTACK_PATH_LIST:
        return True
    return character in SPECIAL_ATTACK_CHARACTER_LIST


def is_survival_character(character_id: str) -> bool:
    """
    是否生存位角色
    - 存护、丰饶 命途
    :param character_id:
    :return:
    """
    character = get_character_by_id(character_id)
    if character is None:
        return False
    return character.path in SURVIVAL_PATH_LIST


def is_support_character(character_id: str) -> bool:
    """
    是否辅助位角色
    - 同谐、虚无 命途
    :param character_id:
    :return:
    """
    character = get_character_by_id(character_id)
    if character is None:
        return False
    return character.path in SUPPORT_PATH_LIST

