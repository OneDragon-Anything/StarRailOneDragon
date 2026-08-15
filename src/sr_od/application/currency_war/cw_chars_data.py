# 警告:本文件由 tools/cw/gen_plaza_chars.py 生成(plaza config V4.4),勿手编;版本更新重跑生成。
# 重跑: uv run python tools/cw/gen_plaza_chars.py
# 同源产物(人读文档层,技能/星级效果全文): docs/game/currency_war/data/characters/<角色名>.md
# 数据粒度 = plaza 条目(同名多档各一条:银狼LV.999 三费档/布洛妮娅变体/开拓者双形态等);
# 规范名:• 已统一为·;开拓者已按 id 映射(8009=开拓者·欢愉/8007=开拓者·记忆)。
"""plaza 官方接口角色数据(V4.4,gen_plaza_chars.py 生成)。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlazaRole:
    """单 plaza 条目(id/cost/position/traits/技能名)。"""
    id: str
    name: str
    cost: int
    position: str          # Front/Back/Common
    traits: tuple[str, ...]
    skills: tuple[str, ...]
    tags: tuple[str, ...]   # 官方职能标签(category_tags 并集):输出/辅助/治疗/护盾
    is_hide: bool
    is_expert: bool


PLAZA_ROLES: tuple[PlazaRole, ...] = (
    PlazaRole(id='1001', name='三月七', cost=1, position='Back', traits=('列车同行', '护盾'), skills=('本姑娘保护你！',), tags=('护盾',), is_hide=False, is_expert=False),
    PlazaRole(id='1003', name='姬子', cost=3, position='Back', traits=('列车同行', '击破'), skills=('天惊石破',), tags=('输出',), is_hide=False, is_expert=True),
    PlazaRole(id='1004', name='瓦尔特', cost=5, position='Front', traits=('列车同行', '星间旅人', '减益'), skills=('黑洞领域',), tags=('输出', '辅助'), is_hide=False, is_expert=False),
    PlazaRole(id='1005', name='卡芙卡', cost=2, position='Common', traits=('星核猎手', '持续伤害'), skills=('浓墨的夜', '浓墨的夜'), tags=('输出', '辅助'), is_hide=False, is_expert=False),
    PlazaRole(id='1006', name='银狼', cost=4, position='Common', traits=('星核猎手', '量子同频'), skills=('全域封禁', '全域封禁'), tags=('辅助', '输出'), is_hide=False, is_expert=True),
    PlazaRole(id='1009', name='艾丝妲', cost=1, position='Front', traits=('银河学者', '持续伤害'), skills=('高能射线',), tags=('辅助',), is_hide=False, is_expert=False),
    PlazaRole(id='1013', name='黑塔', cost=1, position='Common', traits=('银河学者', '群攻'), skills=('转圈圈', '转圈圈'), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1014', name='Saber', cost=3, position='Common', traits=('命运圣杯', '能量'), skills=('理想乡', '理想乡'), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1015', name='Archer', cost=5, position='Front', traits=('命运圣杯', '战技点', '魔术师'), skills=('幻想崩坏',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1102', name='希儿', cost=3, position='Front', traits=('贝洛伯格', '量子同频'), skills=('弱者斩杀',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1104', name='杰帕德', cost=4, position='Front', traits=('贝洛伯格', '护盾'), skills=('筑城之志',), tags=('护盾', '输出'), is_hide=False, is_expert=False),
    PlazaRole(id='1105', name='娜塔莎', cost=3, position='Common', traits=('贝洛伯格', '治疗'), skills=('爱的礼物', '爱的礼物'), tags=('治疗',), is_hide=False, is_expert=False),
    PlazaRole(id='1106', name='佩拉', cost=2, position='Back', traits=('贝洛伯格', '减益'), skills=('破甲弹头',), tags=('辅助', '输出'), is_hide=False, is_expert=True),
    PlazaRole(id='1108', name='桑博', cost=1, position='Common', traits=('贝洛伯格', '星间旅人', '持续伤害'), skills=('风刃连击', '风刃连击'), tags=('输出',), is_hide=False, is_expert=True),
    PlazaRole(id='1112', name='托帕&账账', cost=5, position='Back', traits=('公司', '追击'), skills=('猪市',), tags=('输出', '辅助'), is_hide=False, is_expert=False),
    PlazaRole(id='1201', name='青雀', cost=1, position='Front', traits=('仙舟', '战技点'), skills=('雀神',), tags=('输出',), is_hide=False, is_expert=True),
    PlazaRole(id='1202', name='停云', cost=1, position='Back', traits=('仙舟', '能量'), skills=('佳音降祥瑞',), tags=('辅助',), is_hide=False, is_expert=True),
    PlazaRole(id='1203', name='罗刹', cost=4, position='Back', traits=('星间旅人', '治疗'), skills=('生生不息',), tags=('治疗', '辅助'), is_hide=False, is_expert=False),
    PlazaRole(id='1204', name='景元', cost=5, position='Front', traits=('仙舟', '群攻'), skills=('煌煌神威',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1205', name='刃', cost=1, position='Back', traits=('星核猎手', '燃血'), skills=('玉石俱焚',), tags=('输出',), is_hide=False, is_expert=True),
    PlazaRole(id='1208', name='符玄', cost=4, position='Back', traits=('仙舟', '治疗', '量子同频'), skills=('大穷观阵',), tags=('治疗', '辅助'), is_hide=False, is_expert=False),
    PlazaRole(id='1209', name='彦卿', cost=4, position='Back', traits=('仙舟', '狼狩', '减益'), skills=('天河奔怒涛',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1212', name='镜流', cost=3, position='Back', traits=('狼狩', '燃血'), skills=('冷月寒光',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1213', name='丹恒·饮月', cost=2, position='Front', traits=('列车同行', '仙舟', '战技点'), skills=('苍龙战于深渊',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1217', name='藿藿', cost=1, position='Common', traits=('仙舟', '能量', '治疗'), skills=('遣神役鬼', '遣神役鬼'), tags=('治疗', '辅助'), is_hide=False, is_expert=False),
    PlazaRole(id='1218', name='椒丘', cost=1, position='Front', traits=('狼狩', '减益', '持续伤害'), skills=('燎烟古方',), tags=('治疗', '辅助'), is_hide=False, is_expert=False),
    PlazaRole(id='1220', name='飞霄', cost=1, position='Front', traits=('狼狩', '追击'), skills=('大捷！大捷！',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1221', name='云璃', cost=5, position='Back', traits=('狼狩', '能量'), skills=('以剑为盾',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1222', name='灵砂', cost=2, position='Front', traits=('狼狩', '击破', '治疗'), skills=('浮元旌旗，蔽日遮天',), tags=('治疗', '输出'), is_hide=False, is_expert=False),
    PlazaRole(id='1223', name='貊泽', cost=1, position='Back', traits=('狼狩', '追击'), skills=('归于暗影',), tags=('输出', '辅助'), is_hide=False, is_expert=True),
    PlazaRole(id='1225', name='忘归人', cost=3, position='Back', traits=('仙舟', '击破'), skills=('燎火惊鸿舞',), tags=('辅助', '输出'), is_hide=False, is_expert=False),
    PlazaRole(id='1301', name='加拉赫', cost=1, position='Common', traits=('盛会之星', '击破', '治疗'), skills=('酒花满溢', '酒花满溢'), tags=('治疗',), is_hide=False, is_expert=True),
    PlazaRole(id='1302', name='银枝', cost=2, position='Common', traits=('星间旅人', '群攻'), skills=('美美与共', '美美与共'), tags=('输出', '辅助'), is_hide=False, is_expert=False),
    PlazaRole(id='1303', name='阮·梅', cost=2, position='Back', traits=('银河学者', '击破'), skills=('残梅傲雪绽',), tags=('辅助',), is_hide=False, is_expert=False),
    PlazaRole(id='1304', name='砂金', cost=2, position='Front', traits=('公司', '追击', '护盾'), skills=('博弈论',), tags=('护盾', '输出'), is_hide=False, is_expert=False),
    PlazaRole(id='1305', name='真理医生', cost=3, position='Front', traits=('银河学者', '星间旅人', '追击'), skills=('饱和式提问',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1306', name='花火', cost=2, position='Back', traits=('盛会之星', '量子同频', '战技点'), skills=('欺诈面具',), tags=('辅助',), is_hide=False, is_expert=False),
    PlazaRole(id='1307', name='黑天鹅', cost=5, position='Back', traits=('盛会之星', '持续伤害', '命运卜者'), skills=('窥视奥迹',), tags=('输出', '辅助'), is_hide=False, is_expert=False),
    PlazaRole(id='1308', name='黄泉', cost=3, position='Front', traits=('巡海游侠', '减益'), skills=('飞雷紫',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1309', name='知更鸟', cost=4, position='Back', traits=('盛会之星', '追击'), skills=('银河歌姬',), tags=('辅助', '输出'), is_hide=False, is_expert=False),
    PlazaRole(id='1310', name='流萤', cost=5, position='Front', traits=('星核猎手', '击破'), skills=('点燃大海',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1313', name='星期日', cost=3, position='Common', traits=('列车同行', '盛会之星', '能量'), skills=('福泽亲吻的大地', '福泽亲吻的大地'), tags=('辅助',), is_hide=False, is_expert=False),
    PlazaRole(id='1314', name='翡翠', cost=1, position='Back', traits=('公司', '群攻'), skills=('利益交换',), tags=('输出', '辅助'), is_hide=False, is_expert=False),
    PlazaRole(id='1315', name='波提欧', cost=4, position='Front', traits=('巡海游侠', '击破'), skills=('清空弹匣',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1317', name='乱破', cost=1, position='Front', traits=('巡海游侠', '击破'), skills=('忍•虚数•破界流',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1321', name='大丽花', cost=1, position='Common', traits=('盛会之星', '击破'), skills=('终将到来的葬礼', '终将到来的葬礼'), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1401', name='大黑塔', cost=4, position='Front', traits=('银河学者', '群攻'), skills=('双塔奇兵',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1402', name='阿格莱雅', cost=1, position='Front', traits=('昼之半神', '能量'), skills=('金织如梦',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1403', name='缇宝', cost=2, position='Common', traits=('昼之半神', '群攻', '量子同频'), skills=('一二三，火箭发射！', '一二三，火箭发射！'), tags=('辅助', '输出'), is_hide=False, is_expert=False),
    PlazaRole(id='1404', name='万敌', cost=1, position='Common', traits=('夜之半神', '燃血'), skills=('沐浴神血', '沐浴神血'), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1405', name='那刻夏', cost=3, position='Back', traits=('昼之半神', '群攻'), skills=('研究的力量',), tags=('输出', '辅助'), is_hide=False, is_expert=False),
    PlazaRole(id='1406', name='赛飞儿', cost=1, position='Front', traits=('夜之半神', '追击', '减益'), skills=('好东西，偷了！',), tags=('辅助',), is_hide=False, is_expert=False),
    PlazaRole(id='1407', name='遐蝶', cost=4, position='Front', traits=('夜之半神', '燃血'), skills=('荒芜流淌',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1408', name='白厄', cost=3, position='Front', traits=('救世主',), skills=('我独自战斗',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1409', name='风堇', cost=2, position='Front', traits=('昼之半神', '治疗', '燃血'), skills=('飞天神马小伊卡',), tags=('治疗', '输出'), is_hide=False, is_expert=False),
    PlazaRole(id='1410', name='海瑟音', cost=4, position='Front', traits=('昼之半神', '持续伤害'), skills=('深海回响',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1412', name='刻律德菈', cost=3, position='Common', traits=('夜之半神', '战技点'), skills=('我来，我见，我征服！', '我来，我见，我征服！'), tags=('辅助',), is_hide=False, is_expert=False),
    PlazaRole(id='1413', name='长夜月', cost=4, position='Common', traits=('夜之半神', '燃血'), skills=('长夜漫漫', '长夜漫漫'), tags=('输出', '辅助'), is_hide=False, is_expert=False),
    PlazaRole(id='1414', name='丹恒·腾荒', cost=2, position='Back', traits=('夜之半神', '护盾'), skills=('龙灵在天',), tags=('护盾',), is_hide=False, is_expert=False),
    PlazaRole(id='1415', name='昔涟', cost=5, position='Front', traits=('昼之半神', '夜之半神', '挚爱之人'), skills=('爱与黄金',), tags=('辅助', '输出'), is_hide=False, is_expert=False),
    PlazaRole(id='1501', name='火花', cost=4, position='Front', traits=('星间旅人', '战技点', '欢愉'), skills=('流量为王',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1502', name='爻光', cost=1, position='Common', traits=('仙舟', '欢愉'), skills=('嬉变一爻，祸福自招', '嬉变一爻，祸福自招'), tags=('辅助',), is_hide=False, is_expert=False),
    PlazaRole(id='1504', name='不死途', cost=2, position='Common', traits=('巡海游侠', '追击'), skills=('贪婪之手', '贪婪之手'), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1505', name='绯英', cost=2, position='Common', traits=('星间旅人', '欢愉'), skills=('绯红踏英歌', '绯红踏英歌'), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1507', name='千冶·刃', cost=2, position='Back', traits=('星核猎手', '燃血', '减益'), skills=('万般消磨，吾身为刃',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1508', name='远坂凛', cost=1, position='Common', traits=('命运圣杯', '战技点'), skills=('宝石魔术师', '宝石魔术师'), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1509', name='吉尔伽美什', cost=2, position='Common', traits=('命运圣杯', '能量'), skills=('窃用宝物的贼人啊，本王准了！', '窃用宝物的贼人啊，本王准了！'), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='1510', name='姬子·启行', cost=3, position='Front', traits=('列车同行', '领航员'), skills=('领航的星炬',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='8007', name='开拓者·记忆', cost=4, position='Front', traits=('列车同行', '能量', '欢愉'), skills=('欧拉！',), tags=('辅助', '输出'), is_hide=True, is_expert=False),
    PlazaRole(id='8009', name='开拓者·欢愉', cost=4, position='Back', traits=('列车同行', '能量', '欢愉'), skills=('喜剧开场',), tags=('辅助',), is_hide=False, is_expert=False),
    PlazaRole(id='11011', name='布洛妮娅', cost=5, position='Front', traits=('贝洛伯格', '大守护者'), skills=('领军之旗',), tags=('辅助', '输出'), is_hide=True, is_expert=False),
    PlazaRole(id='11012', name='布洛妮娅', cost=5, position='Front', traits=('燃血', '大守护者'), skills=('冲锋之号',), tags=('辅助', '输出'), is_hide=False, is_expert=False),
    PlazaRole(id='15061', name='银狼LV.999', cost=3, position='Front', traits=('星核猎手', '欢愉', '头号玩家'), skills=('键盘攻击',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='15062', name='银狼LV.999', cost=4, position='Front', traits=('星核猎手', '欢愉', '头号玩家'), skills=('键盘攻击',), tags=('输出',), is_hide=False, is_expert=False),
    PlazaRole(id='15063', name='银狼LV.999', cost=5, position='Front', traits=('星核猎手', '欢愉', '头号玩家'), skills=('键盘攻击',), tags=('输出',), is_hide=False, is_expert=False),
)


def by_plaza_id() -> dict[str, PlazaRole]:
    """id → 条目(含隐藏/变体)。"""
    return {r.id: r for r in PLAZA_ROLES}
