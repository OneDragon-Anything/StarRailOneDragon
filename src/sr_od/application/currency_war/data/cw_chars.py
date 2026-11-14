"""货币战争 角色域注册表(Character + SYSTEM_UNITS;meta 层)。

**来源**:纯角色 = 攻略广场 game/config API role_list 官方镜像(63 条,含同名多档;
重生成与版本更新工序 = ``skills/sr-od-dev-currency-war/references/version-update.md``);
系统单位 = 实机采集人工登记(官方无数据)。人读角色文档 =
``docs/game/currency_war/data/characters/``(生成器产,与注册表同源)。

**库形态**(为什么建模):核心实体(角色/阵营/策略/环境/装备)应是**正规 model 类 +
注册表**(可查询、可校验、有类型关系),而非字符串散落各处。本模块是角色域:
- ``Character``:单角色(费用/站位/分类标签/阵营/流派/独立羁绊/专家/隐藏标记)。
- ``CHARACTERS``:官方镜像 tuple(63 条)——角色规范名单一真相源;键唯一性不成立
  (星神★阿哈 4/5/7 三档同名),按名查一律走 ``get_char``(多档返起始档,可指名取档)。
- ``SYSTEM_UNITS``:系统单位 dict(5 条,键=name)——游戏系统赠送的非购买单位,
  与纯角色分型(命名依据见 SYSTEM_UNITS 段注)。
- ``ALL_UNITS`` / ``ALL_UNIT_NAMES``:虚拟并集(实例 63+5=68;名字集合 66 名
  ——多档同名在名字侧去重)——遍历全部单位与反扫词表等消费点统一走它,
  零拼接。

**牌池口径**:is_hide=True = 官方隐藏态(v4.7 仅丹恒·腾荒 = 饮月绑定随从,依据
``docs/game/currency_war/research/v47_tenghuang_binding.md``),剔出玩家可见列表。
**数据层查询函数(chars_by_cost 等)不过滤 is_hide**;牌池排除由购买/概率语义的
消费方执行——固定牌池/商店概率/费段统计各自过滤,效果发放与 sim 镜像保持全量。

**规范名原则**:OCR/char_id/COMP_LIBRARY.core_chars/config.character_priority
都用规范名(非粉丝昵称);规范名 = 官方 name 经 U+2022(•)→U+00B7(·)归一
(归一单一源 = gen_plaza_chars.py canon())= 模板目录名 = roster 成员名。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Character:
    """单个货币战争角色(攻略广场官方镜像数据)。"""
    name: str                   # 规范名(= 官方 name 经 • → · 归一;= 模板目录名)
    cost: int                   # 费用(官方 rarity;值域 1/2/3/4/5/7;多档角色每档一条各自带 cost)
    position: str               # "front"(前台)/ "back"(后台)/ "common"(双排皆可,官方 Common:技能效果不绑定排)
    category_tags: tuple[str, ...]  # 官方技能分类多标签(值域:输出/辅助/治疗/护盾;取首技能标签组)
    factions: tuple[str, ...]   # 阵营羁绊(无则空)
    schools: tuple[str, ...]    # 流派羁绊(无则空)
    independent: str = ""       # 独立羁绊名(无则 "")
    source: str = ""            # 官方 id(plaza role_list[].id,保 str;对拍锚)
    # 专家顾问:初始不参与普通商店招募(fixed_pool 排除,概率模型 v 值同口径排除),
    # 对局中经投资环境/投资策略/专家邀请函三通道解锁后本局加入商店(机制依据 =
    # docs/game/currency_war/research/economy.md §1)。名单权威 = plaza is_expert
    # 字段(v4.7 名单 63 条全 False,专家机制空转维持现状,空集下闭集闸 = 拒绝
    # 一切专家写入)。解锁写端 = cw_gain_chain(env/strategy advisor 道 + 装备
    # 通道),状态 = GameState.unlocked_experts,池消费 = cw_pool。
    is_expert: bool = False
    # 官方隐藏态:数据保留但剔出玩家可见列表——牌池排除锚(数据层查询不过滤,
    # 购买/概率语义消费方过滤;v4.7 仅丹恒·腾荒 = 饮月绑定随从,依据 =
    # docs/game/currency_war/research/v47_tenghuang_binding.md)。
    is_hide: bool = False

    def position_pref(self) -> str:
        """部署站位偏好 → "front"/"back"(common 默认 back,可被阵容层 char_positions 覆盖)。

        common(官方 Common=双排皆可)默认 back 是**无知识时的安全兜底**(后排不挨打、
        不占前排保证位),非游戏定义——游戏对 Common 本就没有排定义。排差异来自阵容
        机制面(受击方向/前后台强度分配/装备排绑定/巡海后台供增益类),有机制证据时
        经 Comp.char_positions 覆盖(2026-11-04 全量审查 17 名终局 Common 成员:
        仅绯英实证前排需覆盖,万敌/爻光/知更鸟三例既有覆盖维持,其余默认即实证)。"""
        if self.position == "front":
            return "front"
        return "back"   # back / common → back


# ===== 开拓者形态切换 =====
# 机制:注册表按「归一基名 → {排: 该排的形态规范名}」登记形态表,身份计算
# (羁绊/计数)按「当前排」归一形态(同一开拓者前台/后台形态羁绊不同,同局
# 反复换排是常态操作,不归一会造成羁绊计数虚高/漏算)。v4.7 名单开拓者仅基名
# 「开拓者」单条目(旧双形态「开拓者·记忆/欢愉」不在册)→ 形态表清空:
# trailblazer_form 基名直通、is_trailblazer 恒 False(数据驱动空转);未来名单
# 恢复形态条目时补表即恢复归一。
_TRAILBLAZER_FORMS: dict[str, dict[str, str]] = {}


def trailblazer_form(name: str, row: str) -> str:
    """开拓者按排归一形态名:``row`` = "front"/"back";非开拓者原样返回。

    形态表空(当前名单开拓者仅基名单条目,无双形态)→ 基名直通,
    name 原样返回;row 参数保留(消费方签名不变,当前无归一可做)。
    """
    forms = next((v for k, v in _TRAILBLAZER_FORMS.items() if k in name), None)
    if forms is not None and row in forms:
        return forms[row]
    return name


def is_trailblazer(name: str) -> bool:
    return any(base in name for base in _TRAILBLAZER_FORMS)


def _ch(
    name: str,
    cost: int,
    position: str,
    category_tags: tuple[str, ...],
    factions: tuple[str, ...] = (),
    schools: tuple[str, ...] = (),
    independent: str = "",
    source: str = "",
    is_expert: bool = False,
    is_hide: bool = False,
) -> Character:
    """构造助手(官方段条目文本形态;参数序 = 生成器产段契约,勿改序)。"""
    return Character(
        name=name, cost=cost, position=position, category_tags=category_tags,
        factions=factions, schools=schools, independent=independent,
        source=source, is_expert=is_expert, is_hide=is_hide,
    )


# === 官方段(生成器产,勿手改;重写入口 gen_plaza_chars.py) ===
# 数据源:攻略广场 game/config API role_list(63 条);名字已归一(U+2022→U+00B7);
# _ch 参数序 = 工厂签名;is_hide 条目语义见行内注。版本更新:重跑生成器产
# registry_chars_v<版本>.py 片段,按本标记整段替换条目。
CHARACTERS: tuple[Character, ...] = (
    _ch('瓦尔特', 1, 'common', ('输出', '辅助'), factions=('开拓银轨',), schools=('群攻',), source='100402'),
    _ch('卡芙卡', 5, 'front', ('输出', '辅助'), factions=('星核猎手',), schools=('持续伤害',), source='100502'),
    _ch('希露瓦', 4, 'front', ('输出',), factions=('少女乐队',), schools=('持续伤害',), source='110302'),
    _ch('娜塔莎', 2, 'back', ('治疗', '输出'), factions=('星间旅人',), schools=('持续伤害', '治疗'), source='110502'),
    _ch('克拉拉', 5, 'common', ('输出',), factions=('星间旅人',), schools=('反击',), independent='机心巧匠', source='110702'),
    _ch('托帕&账账', 1, 'common', ('输出', '辅助'), factions=('千星商会',), schools=('追击',), source='111202'),
    _ch('罗刹', 3, 'common', ('治疗', '辅助'), factions=('星间旅人',), schools=('治疗',), source='120302'),
    _ch('景元', 1, 'common', ('输出',), factions=('云上五骁',), schools=('召唤',), source='120402'),
    _ch('刃', 4, 'common', ('输出',), factions=('云上五骁',), schools=('反击',), source='120502'),
    _ch('符玄', 3, 'back', ('治疗', '辅助'), factions=('小小巨人',), schools=('反击', '守护'), source='120802'),
    _ch('桂乃芬', 1, 'common', ('辅助', '输出'), factions=('仙舟舰队',), schools=('持续伤害',), source='121002'),
    _ch('白露', 2, 'back', ('治疗',), factions=('云上五骁',), schools=('连击', '治疗'), source='121102'),
    _ch('镜流', 3, 'common', ('输出',), factions=('云上五骁',), schools=('连击',), source='121202'),
    _ch('丹恒·饮月', 5, 'front', ('输出',), factions=('开拓银轨', '云上五骁'), independent='双龙吟', source='121302'),
    _ch('雪衣', 5, 'front', ('输出', '辅助'), factions=('仙舟舰队',), schools=('击破',), source='121402'),
    _ch('寒鸦', 4, 'back', ('辅助',), factions=('仙舟舰队',), schools=('连击',), source='121502'),
    _ch('藿藿', 4, 'back', ('治疗', '辅助'), factions=('小小巨人',), schools=('能量', '治疗'), source='121702'),
    _ch('椒丘', 3, 'front', ('辅助', '输出'), factions=('仙舟舰队',), schools=('持续伤害',), source='121802'),
    _ch('飞霄', 3, 'front', ('输出',), factions=('仙舟舰队',), schools=('追击',), source='122002'),
    _ch('云璃', 2, 'common', ('输出',), factions=('仙舟舰队',), schools=('反击',), source='122102'),
    _ch('灵砂', 1, 'common', ('治疗', '辅助'), factions=('仙舟舰队',), schools=('群攻', '治疗'), source='122202'),
    _ch('三月七', 1, 'back', ('辅助', '输出'), factions=('开拓银轨',), schools=('追击',), source='122402'),
    _ch('忘归人', 1, 'common', ('辅助',), factions=('星间旅人',), schools=('击破',), source='122502'),
    _ch('砂金', 4, 'common', ('护盾', '输出'), factions=('星间旅人',), schools=('追击', '守护'), source='130402'),
    _ch('花火', 2, 'front', ('辅助',), factions=('小小巨人', '梦境交织'), schools=('欢愉',), source='130602'),
    _ch('黑天鹅', 1, 'back', ('输出', '辅助'), factions=('梦境交织',), schools=('持续伤害',), source='130702'),
    _ch('黄泉', 4, 'front', ('输出',), factions=('梦境交织',), schools=('群攻',), source='130802'),
    _ch('知更鸟', 2, 'front', ('辅助',), factions=('少女乐队',), schools=('追击',), source='130902'),
    _ch('流萤', 2, 'front', ('输出',), factions=('星核猎手',), schools=('击破',), source='131002'),
    _ch('星期日', 2, 'common', ('辅助',), factions=('幻月游戏', '开拓银轨'), schools=('连击',), source='131302'),
    _ch('翡翠', 5, 'back', ('输出', '辅助'), factions=('千星商会',), schools=('群攻',), independent='黑市主理人', source='131402'),
    _ch('波提欧', 1, 'front', ('输出',), factions=('星间旅人',), schools=('击破',), source='131502'),
    _ch('乱破', 3, 'back', ('输出',), factions=('少女乐队',), schools=('击破',), source='131702'),
    _ch('大丽花', 3, 'common', ('辅助',), factions=('梦境交织',), schools=('击破',), source='132102'),
    _ch('大黑塔', 2, 'front', ('输出',), factions=('星间旅人',), schools=('群攻',), source='140102'),
    _ch('阿格莱雅', 5, 'front', ('输出',), factions=('奇兽花园',), schools=('连击',), source='140202'),
    _ch('缇宝', 4, 'common', ('辅助', '输出'), factions=('小小巨人',), schools=('追击',), source='140302'),
    _ch('万敌', 2, 'common', ('输出',), factions=('奇兽花园', '黄金大饭店'), schools=('反击',), source='140402'),
    _ch('那刻夏', 1, 'front', ('输出',), factions=('奇兽花园',), schools=('连击',), source='140502'),
    _ch('赛飞儿', 3, 'back', ('辅助',), factions=('奇兽花园',), schools=('群攻',), source='140602'),
    _ch('遐蝶', 3, 'common', ('输出',), factions=('黄金大饭店',), schools=('召唤',), source='140702'),
    _ch('白厄', 5, 'common', ('输出',), factions=('黄金大饭店',), independent='盗火行者', source='140802'),
    _ch('风堇', 4, 'common', ('治疗', '输出'), factions=('奇兽花园',), schools=('召唤', '治疗'), source='140902'),
    _ch('海瑟音', 2, 'common', ('输出',), factions=('奇兽花园',), schools=('持续伤害',), source='141002'),
    _ch('刻律德菈', 1, 'back', ('辅助',), factions=('小小巨人',), schools=('连击',), source='141202'),
    _ch('长夜月', 1, 'common', ('输出', '辅助'), factions=('奇兽花园', '梦境交织'), schools=('召唤',), source='141302'),
    _ch('丹恒·腾荒', 5, 'back', ('护盾',), independent='双龙吟', source='141402', is_hide=True),  # 官方隐藏态:饮月绑定随从(双龙吟召唤,星级随饮月),非独立入池员工
    _ch('昔涟', 4, 'front', ('辅助',), factions=('黄金大饭店',), schools=('召唤',), source='141502'),
    _ch('火花', 1, 'common', ('输出',), factions=('幻月游戏', '少女乐队'), schools=('欢愉',), source='150102'),
    _ch('爻光', 3, 'back', ('辅助',), factions=('千星商会',), schools=('欢愉',), source='150202'),
    _ch('真珠', 1, 'back', ('治疗', '辅助'), factions=('幻月游戏', '千星商会'), schools=('守护',), source='150302'),
    _ch('不死途', 5, 'back', ('输出',), factions=('幻月游戏',), schools=('追击',), independent='巡海游侠', source='150402'),
    _ch('绯英', 2, 'common', ('输出',), factions=('幻月游戏',), schools=('能量',), source='150502'),
    _ch('银狼LV.999', 3, 'front', ('输出',), factions=('幻月游戏', '星核猎手'), schools=('欢愉',), source='150602'),
    _ch('千冶·刃', 4, 'common', ('输出', '辅助'), factions=('幻月游戏', '星核猎手'), schools=('群攻',), source='150702'),
    _ch('姬子·启行', 4, 'front', ('输出',), factions=('开拓银轨',), schools=('能量',), source='151002'),
    _ch('星神★阿哈', 4, 'front', ('辅助',), schools=('欢愉',), independent='幻乐之主', source='151112'),
    _ch('星神★阿哈', 5, 'front', ('辅助',), schools=('欢愉',), independent='幻乐之主', source='151122'),
    _ch('星神★阿哈', 7, 'front', ('辅助',), schools=('欢愉',), independent='幻乐之主', source='151132'),
    _ch('知更鸟·晴歌', 2, 'common', ('辅助',), factions=('千星商会',), schools=('召唤', '能量'), source='151202'),
    _ch('砂金·戏浪', 4, 'front', ('输出',), factions=('千星商会',), schools=('欢愉',), source='151302'),
    _ch('帕姆王', 5, 'back', ('输出', '辅助'), factions=('开拓银轨',), source='604202'),
    _ch('开拓者', 3, 'common', ('辅助',), factions=('开拓银轨', '星核猎手'), schools=('能量',), source='800902'),
)
# === 官方段结束 ===

# ===== 系统单位(游戏系统赠送的非购买单位;与纯角色分型) =====
# 命名依据:不用 SUMMONS——「召唤」是 4.7 正式羁绊名(config 内「召唤/召唤星徽/
# 召唤力/召唤概念股」),裸名正面撞车,且官方「召唤物」语义 = 战斗内羁绊召唤物
# (神君类,与本类并存的两实体),一词不能两指;用「系统单位」——对齐既有代码
# 符号(is_unsellable_system_unit / check_system_unit_layout 等)与观测层
# 「系统召唤单位恒占布局最右」表述。容器用 dict:键唯一约束在此成立(名字唯一、
# 数量小、按名查是唯一访问模式),与角色容器形态差异各有语义。


@dataclass(frozen=True)
class SystemUnit:
    """系统单位 = 游戏系统(投资策略/投资环境效果)赠送的非购买单位。

    官方无类名(效果文本直呼其名)。共享行为特性(全体一致,不逐条重复):
    cost=0(非购买)/恒后台/恒占布局最右格/不可拖动/不可卖/无羁绊。
    """
    name: str    # 规范名 = 模板目录名 = SYSTEM_UNIT_ROSTER 成员名
    source: str  # 溯源(live:<策略/环境名>,实机采集;登记保留采集时原文)


# 人工维护段(实机采集溯源,生成器不产);dict 键 = name(构造约定保证一致)。
SYSTEM_UNITS: dict[str, SystemUnit] = {
    # 佩佩:投资策略族召唤(招财狗/溜佩佩/佩佩驾到/佩佩客串等;plaza API 不列
    # 召唤单位 → 无官方 art,模板 = 现场采集 character_avatar/佩佩/raw.png 实拍)。
    '佩佩': SystemUnit(name='佩佩', source='live:招财狗/溜佩佩族召唤'),
    # 狸小虎/狸小龙:投资策略「龙虎兄弟狸」送双狸猫(弟弟狸小虎=蓝/哥哥狸小龙=红,
    # 同造型异色 → 识别走色相仲裁区分);纯增益填充位,效果=【随便骰子】。
    '狸小虎': SystemUnit(name='狸小虎', source='live:龙虎兄弟狸'),
    '狸小龙': SystemUnit(name='狸小龙', source='live:龙虎兄弟狸'),
    # 狸职狸狸:投资策略「狸职手续」(id 204001)发放的 3 个穿 1 件简易装备的
    # 【狸狸】(三只各带 1 件装备恒占最右格);与蓝/红狸同造型,灰度 SIFT 会互撞
    # ——已落同规格模板(净艺术区+掩码)消除。
    '狸职狸狸': SystemUnit(name='狸职狸狸', source='live:狸职手续204001'),
    # 姵姵:投资卡「孪生姵姵」(id 302501)发放对象,与佩佩同族。模板目录现无
    # 「姵姵」→ 在册但识别不可达(SIFT 永不命中)为已知缺口,待实机现场采集
    # 模板(佩佩先例 = 实拍)。
    '姵姵': SystemUnit(name='姵姵', source='实机(live):孪生姵姵302501'),
}

# ===== 派生集合(模块加载时派生;遍历/词表消费点统一走虚拟集合,零拼接) =====

#: 纯角色规范名集合(61 名;官方段 63 条含星神★阿哈三档同名,名字侧去重。
#: 系统单位不在内)。闭集闸按消费方语义分流:校验对象
#: 可能是系统单位的闸(发放角色/反扫词表)走 ALL_UNIT_NAMES;纯角色语义闸
#: (判据角色/参与名/奖励角色等发放对象恒为角色的)保持本集合。
CHARACTER_ROSTER: frozenset[str] = frozenset(c.name for c in CHARACTERS)

SYSTEM_UNIT_ROSTER: frozenset[str] = frozenset(SYSTEM_UNITS)

#: 全部单位名字词表(= CHARACTER_ROSTER ∪ SYSTEM_UNIT_ROSTER;识别 resolve/
#: 反扫守卫等含系统单位的词表统一走它)。
ALL_UNIT_NAMES: frozenset[str] = CHARACTER_ROSTER | SYSTEM_UNIT_ROSTER

#: 全部单位实例虚拟并集(63 角色 + 5 系统单位 = 68;遍历全部单位处统一走它)。
#: 角色在前、系统单位在后,顺序无语义。
ALL_UNITS: tuple[Character | SystemUnit, ...] = (*CHARACTERS, *SYSTEM_UNITS.values())


def get_char(name: str, cost: int | None = None) -> Character | None:
    """按规范名取 Character;无则 None。

    cost=None:身份查询——唯一档角色返该档,多档角色返起始档(cost 最小);
    cost 给定:档位查询——未命中(名字不存在或该档不存在)返 None。
    """
    if cost is None:
        chars = [c for c in CHARACTERS if c.name == name]
        return min(chars, key=lambda c: c.cost) if chars else None
    for c in CHARACTERS:
        if c.name == name and c.cost == cost:
            return c
    return None


# 专家顾问名单(从 CHARACTERS 派生,查询便捷口;权威标注在各条目 is_expert)。
# v4.7 名单 is_expert 全 False → 空集;空集下 assert_expert_names 闭集闸 =
# 拒绝一切专家写入(专家机制空转维持现状;解锁写端/状态容器/池消费链路不变)。
EXPERT_CHARS: frozenset[str] = frozenset(c.name for c in CHARACTERS if c.is_expert)


def assert_expert_names(names: frozenset[str] | set[str] | tuple[str, ...]) -> None:
    """成员闭集校验:传入名集必须 ⊆ 专家名单(防御调用方拼写漂移造状态)。

    越界名 raise ValueError(unlocked_experts 写端与池派生的构建/写入期闸)。
    """
    unknown = sorted(set(names) - EXPERT_CHARS)
    if unknown:
        raise ValueError(f'非专家顾问名混入解锁状态(注册表 is_expert 无此人,'
                         f'版本改名/拼写漂移?):{unknown}')


# ===== 查询(数据层:不过滤 is_hide——牌池排除归购买/概率语义消费方) =====

def char_first_faction(char_id: str) -> str:
    """主阵营注册表派生单一源(faction 不入状态容器形状;「首位 = 定义件」
    契约正本 = strategy-docs/12_line_and_intention.md §1.1 carry_anchor 行,
    三类消费口径共用):注册表命中 → ``factions[0]``
    (命中但无阵营登记 = '');未注册名/空名 = '?'。"""
    if not char_id:
        return '?'
    ch = get_char(char_id)
    if ch is None:
        return '?'
    return ch.factions[0] if ch.factions else ''


def chars_by_cost(cost: int) -> list[Character]:
    """某费用的全部角色(全档口径,含同名多档各档;不滤 is_hide)。"""
    return [c for c in CHARACTERS if c.cost == cost]


def chars_by_faction(faction: str, include_schools: bool = True) -> list[Character]:
    """属某阵营的角色(include_schools=True 则也匹配流派羁绊)。

    成员关系派生自 CHARACTERS(角色自报 factions/schools)—— FactionInfo.members() 调本函数。
    """
    out = [c for c in CHARACTERS if faction in c.factions]
    if include_schools:
        out += [c for c in CHARACTERS if faction in c.schools and c not in out]
    return out


# ===== 选边型双羁绊(板面羁绊计数选边机制;机制/承载分工见
# cw_bond_equips.unit_bond_tags docstring 与 fields.md §5.2 披露键组)=====

#: 选边型双羁绊角色(首例布洛妮娅,用户裁定 2026-10-28):注册表
#: factions/schools 双边都登记(采样域/成员反查双边命中),板面羁绊
#: 计数按图鉴逻辑选边单边计入。值 = (羁绊甲, 羁绊乙);比较基数 =
#: 其余在场角色的注册表出身(factions+schools,不含装备贡献);平局 =
#: 乙(布洛妮娅 = 燃血,可见条目形态默认;假设,披露键
#: BRONYA_SIDE_PICK_TIE_BLOOD 登记)。
#: 布洛妮娅不在 v4.7 名单 → 本表当前为空映射死码(无害,机制原样保留);
#: 未来名单出现双羁绊角色时按同口径登记。
SIDE_PICK_DUAL_BONDS: dict[str, tuple[str, str]] = {'布洛妮娅': ('贝洛伯格', '燃血')}

#: 选边平局默认乙羁绊的假设申报键(图鉴只写「人数更多」,平局无依据;
#: 校准源 = 实机对局布洛妮娅在场且两边等数时的羁绊等级面板读数,
#: 随机态观察只靠画面读数,不响停)。
BRONYA_SIDE_PICK_TIE_BLOOD: str = 'bronya_side_pick_tie_blood'


def side_pick_bond(char_id: str, peer_cids: list[str] | None) -> str | None:
    """选边型双羁绊角色的板面计入羁绊名(非该类角色 = None)。

    peer_cids = 同场其余角色 cid(不含自己);基数只数注册表出身
    (factions+schools)。开拓者不在选边两边(列车同行/能量出身,基数
    零贡献),其形态读法与本规则无关,不另立读法。平局 → 乙羁绊
    (SIDE_PICK_DUAL_BONDS 值第二位,假设申报 BRONYA_SIDE_PICK_TIE_BLOOD)。
    未注册 peer 不计两边(同注册表口径)。"""
    pair = SIDE_PICK_DUAL_BONDS.get(char_id)
    if pair is None:
        return None
    bond_a, bond_b = pair
    count_a = count_b = 0
    for cid in (peer_cids or ()):
        ch = get_char(str(cid)) if cid else None
        if ch is None:
            continue
        born = set(ch.factions) | set(ch.schools)
        if bond_a in born:
            count_a += 1
        if bond_b in born:
            count_b += 1
    if count_a > count_b:
        return bond_a
    return bond_b
