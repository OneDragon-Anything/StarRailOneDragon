"""货币战争 · 线库 v1(Phase A Day 6;redesign §11 七字段简化版)。

**判断层,手维护**——字段内容=十类深读文档的结构化
(research/final_comps/ 各 final_*.md;证据可溯源)。

Phase A schema(七字段+bench_windows,r208 对抗修正⑥):
  line_id / carry+drive / p2p3_forms / star_tiers / degrade_to /
  roll_anchor / equip_priority(一句话)
外加: core_cards(信号 2 层锁线的核心卡)、bench_windows
([21] 买而不上——结构性修正,砍了会犯「5级拖姬子上场」错)。

⚠️ Phase A 无消费方的预埋字段(S3,诚实声明):degrade_to 与
bench_windows 目前**零运行时消费**——它们是 Phase B 决策循环
(LineStrategy)的输入;降级触发条件(D 卡失败 N 次,redesign
装置 D)同样 Phase B 才实现。Phase A 的本模块只做「数据就位+
结构被测试锁定」,不做行为。

三条线(r213 对抗修正:覆盖三驱动型+兜底;受击流视门槛①
结果——reactive 14.6% 未超阈,万敌仍上但保守系数最深):
  1. 姬子线(burst;体量最大 274 篇)
  2. 绯英线(action;欢愉族低门槛入口,全试用可玩)
  3. DOT 线(兜底;自动友好最高,降级链终点)
白厄线(换线验证)Phase A 后半接入(先立三线跑通)。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LineV1:
    """一条线的 Phase A 档案(七字段+锁线核心)。"""
    line_id: str
    carry: str                       # CARRY 规范名
    drive_type: str                  # burst / action / dot_fallback
    core_cards: list[str]            # 信号 2 层:这些卡出现→锁线
    p2p3_forms: dict[str, str]       # 位面→目标形态键(战力表口径)
    star_tiers: dict[str, str]       # 角色组→星级档(target/opportunistic)
    degrade_to: str | None           # 降级目标线 id(None=兜底无降级)
    roll_anchor: str                 # D 牌锚点(一句话)
    equip_priority: str              # 装备优先序(一句话)
    bench_windows: dict[str, str] = field(default_factory=dict)
    # 核心卡上场窗口([21]):卡名→窗口描述
    opportunistic_cards: list[str] = field(default_factory=list)
    # S3 单一源:顺手升档名单(与 star_tiers 文本同步维护;
    # 消费方=line_strategy._line_wants,勿在消费侧另建缓存)


#: 姬子线的星级三档(r201 用户裁定)
_JIZI_STARS: dict[str, str] = {
    'target': '姬子·启行(7级D三星);三月七(opportunistic,装备载体)',
    'opportunistic': '瓦尔特/符玄/星期日(刷到就买,2星保底)',
    'floor': '其余成员 2 星',
}


LINE_LIBRARY_V1: list[LineV1] = [
    LineV1(
        line_id='jizi_train',
        carry='姬子·启行',
        drive_type='burst',
        core_cards=['姬子·启行'],      # 仅启行版(r224 B1:普通「姬子」
        # 是击破特化变体的 B 套语义,不是锁线依据——看到普通姬子
        # 不锁,避免 CARRY 不在场却锁进本线去 D 一个没出现的单位)
        # 形态键=战力表真实数据键(r223b 探查;理想化简键在 plaza
        # 数据中不存在——数据一致性测试逼出的修正)
        p2p3_forms={
            'P2': '列车同行4+护盾3',       # 25+15 篇(r191 P2 王者桥)
            'P3': '列车同行6+护盾3',       # 11 篇@8(15 篇变体含能量3)
        },
        star_tiers=_JIZI_STARS,
        degrade_to='dot_fallback',      # 姬子没3星→杨叔C(P3 内降档);
        # Phase A 简化:直接落兜底(杨叔线 Phase B 立线后接)
        roll_anchor='7级D三星姬子(3费);卡30利息慢D',
        # r224 S1:主体 A 套(~60% 反震形态)装备序——反甲优先;
        # 「双风暴潮+电锯」是 B 输出套(~25%),Phase A 锁主形态
        equip_priority='三月七第一件自适应外骨骼(吸仇恨刚需)'
                       '>姬子以牙还牙甲×2-3(反震主体A套)'
                       '>瓦尔特回能',
        # r224 S2:窗口=条件式(调研 #35「开局刷到即上」的例外)
        bench_windows={'姬子·启行': '列车2已成型即上;否则>=7级'},
        opportunistic_cards=['瓦尔特', '符玄', '星期日', '三月七'],
    ),
    LineV1(
        line_id='feiying_joy',
        carry='绯英',
        drive_type='action',
        core_cards=['绯英'],
        # 欢愉线数据形态分散(r223b):plaza 的欢愉终局键全是长
        # 复合键且≤4 篇——P2 用最强组合键(4篇);P3 键 3 篇
        # **弱证据**(action 因子下不过阈→查表 miss→战力模式
        # 补强,表在说真话:该形态未经充分验证);Phase B 遥测细化
        p2p3_forms={
            'P2': '列车同行4+欢愉4',       # 4 篇@7(action 因子过)
            'P3': '欢愉5+星间旅人3+减益2+列车同行2+战技点2+星核猎手2+量子同频2',  # 3篇@9 弱证据
        },
        star_tiers={
            'target': '绯英(6级D三星,2费即战力)',
            'opportunistic': '爻光(绯英充能泵)/银狼LV.999/藿藿',
            'floor': '其余 2 星',
        },
        degrade_to='dot_fallback',      # 银狼升费卡住→绯英线的反向;
        # 绯英自身卡死→兜底
        roll_anchor='6级D三星绯英(2费便宜,早成型)',
        equip_priority='绯英风暴潮×2+永动机>爻光靴×3>藿藿绝对热量',
        bench_windows={'绯英': '6级且欢愉2+在场'},
        opportunistic_cards=['爻光', '银狼LV.999', '藿藿'],
    ),
    LineV1(
        line_id='dot_fallback',
        carry='卡芙卡',
        drive_type='dot_fallback',
        core_cards=[],                  # 兜底线不锁信号(永远可选)
        # DOT 终局键全是长复合(最强 2 篇)——r186 深读的 DOT6
        # 形态在 plaza 数据里没有单一键。Phase A:兜底线的战力
        # 判断主要靠前期形态(持续伤害2@P1 5 篇级)+观测驱动,
        # P2/P3 键取最强复合键(弱证据,Phase B 细化)
        p2p3_forms={
            'P2': '持续伤害4+减益2+星核猎手2+银河学者2',  # 2 篇@7
            'P3': '减益4+星核猎手4+持续伤害2+量子同频2',  # 2 篇@10
        },
        star_tiers={
            'target': '卡芙卡(7级D三星)',
            'opportunistic': '黑天鹅/海瑟音/桑博/椒丘/艾丝妲',
            'floor': '其余 2 星',
        },
        degrade_to=None,                # 兜底无降级(防环终点)
        roll_anchor='前期DOT2即战力;7级D三星卡芙卡',
        equip_priority='卡芙卡风暴潮×3>阮·梅充能>黑天鹅天基轨道炮',
        bench_windows={},
        opportunistic_cards=['黑天鹅', '海瑟音', '桑博', '椒丘', '艾丝妲'],
    ),
]


def line_of(line_id: str) -> LineV1 | None:
    """按 id 查线(消费便捷)。"""
    for line in LINE_LIBRARY_V1:
        if line.line_id == line_id:
            return line
    return None
