"""货币战争 通用插件注册表(判断层,手编;W25,C4 契约;2026-08-25)。

**建库基准(leader 裁决 4,防名单迭代残留)**:单卡名单取
``.debug/temp/currency_war/cw_dev/deep_read/comp_elements_and_plugins.md`` 的
**三B 节(单卡插件名单定稿,2026-08-24 用户裁定 v3 纯效果序)**;小羁绊名单取
**三C 节(小羁绊名单定稿,W17 效果复核后)**——即文档内**最晚定稿节**。
勿从旧节(三/三A/插件池数据定级版)取名单:椒丘曾入「一线」后被剔除(v3)、
巡海游侠1「槽位效率最高」被 W17 复核作出池——旧节名单已被推翻。

定位(comp_elements 三·二):通用插件 = 小羁绊(2-3 人凑一档)与单卡(1 人即生效),
不限费用,判据「占用少的槽位发挥作用」(槽位效率)。它是**不属于任何一套最终阵容骨架**
的公共资源层,填充台阶间空位;可回收(正料到位卖出近无损)。

**互补不重叠(唯一硬规则)**:插件身份是「在当前这套阵容里不是骨架」——同一张卡在
A 套是插件、在 B 套是正料,完全正常。``majority_lines`` 字段承载线内身份标注
(已是骨架的家族/套——插件身份不在这些线成立,非踢出);过半线刷新走**单一写入口**
(流派统计刷新动作同时改本表 majority_lines 与对应 ``Comp.sub_tiers``,不做两处
可独立编辑的开关——W22 §3 防双源)。

消费方(后续批接线):decision_v2 层1 插件买门、C3 fill_gap 空位规则
(能开新档 > 单卡效果 > 散件)、禁用表查表(买门拒绝 reason 带 matrix 键)。
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class PluginEntry:
    """一个通用插件(单卡或小羁绊)的注册条目。

    - ``plugin_id``:稳定 id(单卡=角色规范名;小羁绊=<羁绊名><档位>);
    - ``kind``:'unit'(单卡)| 'small_faction'(小羁绊);
    - ``tier``:'T1'(稀缺职能)/ 'T2'(标准增益)/ 'T3'(条件件·对症才买)
      ——单卡分界=T1/T2 职能稀缺性、T3 稳定性差/条件触发(三B);小羁绊分界=
      效果给谁(三C:全队通用/混合型/队员口径);
    - ``effect_scope``:'team'(全队通用)| 'member'(队员口径)| 'char'(角色特定);
    - ``majority_lines``:线内身份标注——该插件的全部**过半线家族列表**
      (W16 统计搬运,W50 补全为完整列表;旧部分标注[只记反例线]已废);
      单卡条目从 ``W16_MAJORITY_LINES`` 程序同步(单一写入口),小羁绊
      条目手注(三C 口径);家族键 = ``cw_comps.V2_FAMILIES``;
    - ``source``:证据指针(comp_elements_and_plugins 三B/三C 定稿节)。
    """
    plugin_id: str
    kind: str                                  # 'unit' | 'small_faction'
    tier: str                                  # 'T1' | 'T2' | 'T3'
    effect_scope: str                          # 'team' | 'member' | 'char'
    majority_lines: frozenset[str] = field(default_factory=frozenset)
    source: str = ''


# ===== 单卡插件(22 张;三B 定稿 v3 纯效果序)=====
# T1=职能稀缺(有没有第二家能给同样效果);T2=标准增益(内部按强度);T3=条件件/对症才买。
# 不进池:线核心 carry / 独立羁绊绑死件(昔涟/布洛妮娅)/ 开拓者双形态(形态字段疑混待核)。
_UNIT_PLUGINS: tuple[PluginEntry, ...] = (
    # --- T1 稀缺职能(6)---
    PluginEntry("知更鸟", "unit", "T1", "team", source="三B T1:全体前台立即行动+全体伤害"),
    PluginEntry("符玄", "unit", "T1", "team", source="三B T1:分摊+免死"),
    PluginEntry("瓦尔特", "unit", "T1", "team", frozenset({"姬子列车"}),
                source="三B T1:推条+延后倒计时;姬子A 反震流必拿(吸仇恨件互斥外的时间死穴解药)"),
    PluginEntry("银狼", "unit", "T1", "team", source="三B T1:全体降防"),
    # ↑ W55(R2 §2 银狼·本体条):plugin_id 修正为注册表规范名「银狼」(cw_chars.CHARACTERS 键,
    #   与升费链 carry「银狼LV.999」是两个条目)——旧值「银狼·本体」不在 CHARACTERS,
    #   买门按名匹配永不命中(PluginEntry docstring 承诺单卡=角色规范名,此处曾违约)。
    PluginEntry("花火", "unit", "T1", "team", source="三B T1:拉条+产战技点"),
    PluginEntry("星期日", "unit", "T1", "team", source="三B T1:拉条+能量+蒙福者"),
    # --- T2 标准增益(7)---
    PluginEntry("三月七", "unit", "T2", "team", frozenset({"姬子列车", "白厄反甲"}),
                source="三B T2:小队伤害+行动护盾;双身份——姬子88/白厄87 过半=骨架,其余线插件"),
    PluginEntry("藿藿", "unit", "T2", "team", frozenset({"欢愉族", "圣杯双C"}),
                source="三B T2:后台回能+提攻;双身份——绯英72/圣杯55 过半=骨架,其余线插件"),
    PluginEntry("丹恒·腾荒", "unit", "T2", "team", source="三B T2:全体前台盾+攻提(盾系→万敌线禁用)"),
    PluginEntry("砂金", "unit", "T2", "team", source="三B T2:小队伤害+盾(盾系→万敌线禁用)"),
    PluginEntry("罗刹", "unit", "T2", "team", source="三B T2:治疗结界"),
    PluginEntry("那刻夏", "unit", "T2", "team", source="三B T2:伤害光环"),
    PluginEntry("缇宝", "unit", "T2", "team", source="三B T2:幸运一击增益"),
    # --- T3 条件件·对症才买(9)---
    PluginEntry("灵砂", "unit", "T3", "team", source="三B T3"),
    PluginEntry("佩拉", "unit", "T3", "team", source="三B T3"),
    PluginEntry("托帕&账账", "unit", "T3", "team", source="三B T3"),
    PluginEntry("停云", "unit", "T3", "team", source="三B T3(婷云)"),
    PluginEntry("加拉赫", "unit", "T3", "team", source="三B T3"),
    PluginEntry("风堇", "unit", "T3", "team", source="三B T3(万敌线外——万敌线内为第二记录器正料)"),
    PluginEntry("刻律德菈", "unit", "T3", "team", source="三B T3"),
    PluginEntry("赛飞儿", "unit", "T3", "team", source="三B T3"),
    PluginEntry("杰帕德", "unit", "T3", "team", source="三B T3(⚠️反震流禁用:分受击概率,攻略 #48;盾系→万敌禁用)"),
)

# ===== 小羁绊插件(15 个;三C 定稿 W17 效果复核版)=====
# T1 全队通用(仅 3)/T2 混合型+双向效果/T3 队员口径(只 buff 本羁绊成员,对症才碰);
# 另有角色特定型 2 个。出池:巡海游侠1(自 buff 不给全队,「槽位效率最高」作废);
# DOT2 归体系卡(P1 层);独立羁绊 7 个绑死单卡,不进池。
# W55(R2 §2 🔴):补 `圣杯2`——三C T3 定稿明列 15 个小羁绊,建库时静默落 14 且无出池
# 记录,违反「取三C 最晚定稿节」建库基准;本批补齐(测试锁 smalls==15)。
_SMALL_FACTION_PLUGINS: tuple[PluginEntry, ...] = (
    # --- T1 全队通用(3)---
    PluginEntry("列车2", "small_faction", "T1", "team", source="三C T1:撞击+20% 全体强度"),
    PluginEntry("战技点2", "small_faction", "T1", "team", frozenset({"万敌燃血"}),
                source="三C T1:12%速+12%伤全队+抽奖;万敌线 90% 已升格第三引擎副档"),
    PluginEntry("量子2", "small_faction", "T1", "team", source="三C T1:敌侧受伤+15%"),
    # --- T2 混合型+双向效果(3)---
    PluginEntry("治疗2", "small_faction", "T2", "team", source="三C T2:simple 层全队 12% 生命(W16 漏记)"),
    PluginEntry("护盾2", "small_faction", "T2", "team", frozenset({"姬子列车"}),
                source="三C T2:全队 12% 全伤+叠盾;姬子反震流 50% 副档(盾循环机制必然);万敌线硬禁用"),
    PluginEntry("减益2", "small_faction", "T2", "team", frozenset({"姬子列车", "黄泉减益"}),
                source="三C T2(用户裁定升):离火敌造伤降 3%/层=敌侧收益;姬子输出流 58% 副档;黄泉意向有正料转正路径"),
    # --- T3 队员口径(6)---
    PluginEntry("星核2", "small_faction", "T3", "member", frozenset({"欢愉族", "DOT卡芙卡"}),
                source="三C T3:仅本羁绊队员;银狼档笑点泵 82%/DOT 线 54% 过半=骨架"),
    PluginEntry("贝洛伯格2", "small_faction", "T3", "member", source="三C T3:仅贝队员+造物引擎(「面板最猛」作废)"),
    PluginEntry("夜半2", "small_faction", "T3", "member", frozenset({"万敌燃血"}),
                source="三C T3:夜之半神首档;万敌线 96% 必配=主档骨架"),
    PluginEntry("学者2", "small_faction", "T3", "member", source="三C T3:混合型(首档带 30% 全体强度,顺手收门槛降低,仍不主动凑)"),
    PluginEntry("公司2", "small_faction", "T3", "member", source="三C T3:混合型(同上)"),
    PluginEntry("击破2", "small_faction", "T3", "member", frozenset({"黄泉减益"}),
                source="三C T3;黄泉线 58% 升格候选(sub_tiers 对拍锚)"),
    # W55(R2 §2 🔴 补齐):三C T3 定稿名单明列「圣杯2」,建库时静默丢弃(15→14)。
    # 效果=命运圣杯 2 档开祈愿试炼任务链(产出 Archer;comp_elements 三·4 圣杯任务系统)。
    # majority_lines 不标:圣杯双C 两线它是主档骨架(form_tiers 命运圣杯 3),插件身份不在该线成立。
    PluginEntry("圣杯2", "small_faction", "T3", "member",
                source="三C T3 定稿(15 件全落);命运圣杯 2 档开祈愿试炼任务链,队员口径对症才碰"),
    # --- 角色特定型(按交集逻辑用;三C)---
    PluginEntry("星间旅人1", "small_faction", "T3", "char", source="三C 角色特定:羁绊数值套在逐角色条款上(选谁=选效果),量级待实机"),
    PluginEntry("盛会之星2", "small_faction", "T3", "char", source="三C 角色特定:逐角色条款(巨星绑定)"),
)

# ===== W16 过半线统计(线内身份标注单一源;2026-08-25 W50 补全,W47 条2裁决①)=====
# 来源:`.debug/temp/currency_war/cw_dev/deep_read/W16_报告.md` A2(过滤②,N=809 帖
# v4.4+沙盒过滤口径)——「某线出现率 ≥50%」的家族键集合(V2_FAMILIES;绯英/银狼
# 两线同归欢愉族 → 家族键去重后计数少于线数)。**数据搬运非新统计**。
# 覆盖:8 张骨架件(≥3 线过半;千冶·刃/开拓者·记忆不在插件池——骨架身份,
# 但跨线骨架派生 CROSS_LINE_SKELETON 需要它们的过半数据)+ 4 张边界卡
# (恰 2 线过半且全局 ≥15%,W16 A2 边界组;开拓者·欢愉两线同族 → 1 键)。
W16_MAJORITY_LINES: dict[str, frozenset[str]] = {
    # --- 8 张骨架件(A2 表;线明细见 W16 报告)---
    '瓦尔特': frozenset({'姬子列车', '黄泉减益', 'DOT卡芙卡', '欢愉族',
                         '希儿量子', '圣杯双C'}),          # 7 线(绯英/银狼同族)
    '千冶·刃': frozenset({'万敌燃血', '黄泉减益', 'DOT卡芙卡', '白厄反甲',
                          '希儿量子', '姬子列车', '欢愉族', '圣杯双C'}),  # 8 线
    '符玄': frozenset({'希儿量子', '欢愉族', '圣杯双C', '万敌燃血',
                       'DOT卡芙卡'}),                      # 6 线
    '星期日': frozenset({'姬子列车', '白厄反甲', '圣杯双C'}),   # 3 线
    '开拓者·记忆': frozenset({'圣杯双C', '姬子列车', '白厄反甲'}),  # 3 线
    '花火': frozenset({'希儿量子', '万敌燃血', '圣杯双C', '欢愉族'}),  # 4 线
    '缇宝': frozenset({'大黑塔群攻', '万敌燃血', '希儿量子', '黄泉减益'}),  # 4 线
    '刻律德菈': frozenset({'万敌燃血', '希儿量子', '圣杯双C'}),   # 3 线
    # --- 边界组(恰 2 线过半且全局 ≥15%;A2 边界注)---
    '三月七': frozenset({'姬子列车', '白厄反甲'}),        # 姬子88/白厄87
    '姬子·启行': frozenset({'姬子列车', '白厄反甲'}),     # 姬子100/白厄82
    '开拓者·欢愉': frozenset({'欢愉族'}),                # 绯英96/银狼94(同族)
    '藿藿': frozenset({'欢愉族', '圣杯双C'}),             # 绯英72/圣杯55
}


def cross_line_skeleton() -> tuple[str, ...]:
    """跨线骨架名单派生(W47 条2 裁决①重启;strategy_v4 点0 弱意向囤货集)。

    规则(W16 A2 口径,数据源 = W16_MAJORITY_LINES):
    - **≥3 线过半**(家族键数 ≥3)→ 骨架件(8 张);
    - **恰 2 家族过半的边界卡**,排除「过半线中以它为 carry 的线级定义件」
      (``COMP_LIBRARY.plaza_carry``;姬子·启行 = 姬子线 carry,该线采购
      本就含它,无跨线信息)→ 双身份 2 张(三月七/藿藿;开拓者·欢愉
      两线同族 1 键,天然不进边界)。

    派生结果与原手写 10 名快照一致(cw_intention 测试锁;不等 = 数据错)。
    """
    from sr_od.application.currency_war.cw_comps import COMP_LIBRARY
    carries = {c.plaza_carry for c in COMP_LIBRARY if getattr(c, 'plaza_carry', '')}
    out: set[str] = set()
    for name, fams in W16_MAJORITY_LINES.items():
        if len(fams) >= 3 or len(fams) == 2 and name not in carries:
            out.add(name)
    return tuple(sorted(out))


PLUGIN_LIBRARY: dict[str, PluginEntry] = {p.plugin_id: p for p in (*_UNIT_PLUGINS, *_SMALL_FACTION_PLUGINS)}

# W50(W47 条2 裁决①):单卡插件的 majority_lines 与 W16 统计表**程序同步**
# (单一写入口——过半线刷新只改 W16_MAJORITY_LINES,上方的部分标注字面量
# 被 W16 全集覆盖;小羁绊插件的 majority_lines 仍手注[三C 口径,无 W16 单卡
# 统计])。锁测试对拍两侧一致。

PLUGIN_LIBRARY.update({
    p.plugin_id: replace(p, majority_lines=W16_MAJORITY_LINES[p.plugin_id])
    for p in _UNIT_PLUGINS if p.plugin_id in W16_MAJORITY_LINES
})

# ===== 禁用矩阵(硬冲突行,教义手编;判定法=阵容机制原文 × 插件机制原文)=====
# 键 (plugin_id, family|comp名);值 = 机制原因。硬冲突=见了不买;机制不打架但位置/资源
# 打架的**弱不适配不进本表**(进不进由打分定,如 治疗2×万敌(轻)/量子2×姬子反震(轻))。
PLUGIN_DISABLE_MATRIX: dict[tuple[str, str], str] = {
    # 盾系 × 万敌燃血(官方原文:燃血队员无法获盾,受盾只转 2%+1000 回血=负资产;连带盾类装备全禁)
    ("护盾2", "万敌燃血"): "官方:燃血队员无法获盾,受盾转微回血=负资产",
    ("砂金", "万敌燃血"): "盾系单卡×燃血无法获盾(同上,官方原文)",
    ("丹恒·腾荒", "万敌燃血"): "盾系单卡×燃血无法获盾(同上,官方原文)",
    ("杰帕德", "万敌燃血"): "盾系单卡×燃血无法获盾(同上,官方原文)",
    # W55(R2 §2 三月七漏行):注册表 三月七 flows=("护盾",) 且效果含「行动护盾」(cw_chars:106)——
    # 按判定法(阵容机制原文×插件机制原文)她是盾系单卡,须入盾系×万敌矩阵;
    # 三B 原文「砂金/腾荒/杰帕德等」的「等」即留此口,买门接线前收齐,防万敌线买进负资产件。
    ("三月七", "万敌燃血"): "盾系单卡×燃血无法获盾(行动护盾,官方原文;R2 §2 漏行补齐)",
    # 杰帕德 × 吸仇恨流(反震/反甲:吸仇恨件互斥,分受击概率,攻略 #48)
    ("杰帕德", "姬子列车"): "反震流吸仇恨互斥:与三月七外骨骼分受击概率(攻略 #48)",
    ("杰帕德", "白厄反甲"): "反甲流吸仇恨互斥(同姬子A,白厄前排法则+外骨骼类吸仇恨)",
    ("杰帕德", "反甲白厄"): "反甲流吸仇恨互斥(comp 名键,旧读者兼容)",
}


def plugin_disabled(plugin_id: str, line: str) -> str | None:
    """查禁用矩阵:返回机制原因(禁用)或 None(可用)。

    ``line`` = 家族键(V2_FAMILIES)或 comp 名(矩阵两级键都收,兼容家族/套消费)。
    买门拒绝时 reason 应带 matrix 键(C4 验收 3)。
    """
    return PLUGIN_DISABLE_MATRIX.get((plugin_id, line))
