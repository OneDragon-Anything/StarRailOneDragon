"""货币战争 词缀吃怕表注册表(逐线 × 词缀;design §3.3/§4)。

结构 = ``{线名: {词缀注册名: AffixStance}}``;键名空间 =
data/affix_effects_data 的 ``AFFIX_EFFECTS`` 注册名(52 词缀,运行时采集
入库的官方名)。俗称(怪物提速/满愿)不入死键——见 :data:`AFFIX_ALIASES_PENDING`
(俗称→注册名映射待实机采集归位,采集前不猜键)。

数据源 = docs/game/currency_war/research/final_comps/ 各篇 counter 节
(逐线攻略实证;**直接记载 > 类间概括 > 机制推定**三级证据序,本表只收
直接记载)。批次划分(design §8):批 1 = 注册表结构 + 万敌行;批 2 =
其余 11 已审线扩行 + 未登记线兜底层(方向保守:只给怕不给吃)。

同词缀方向逐线相反是本表存在理由(design §1 第 4 条「词缀吃怕是阵容
特定知识」):正当防卫对万敌 +900、其余登记线均怕(−150,列车系 A/B
两套亦怕正当防卫);列车同行·反震另吃受击触发族(忍无可忍/同步行动)
+750(敌方多动=反震燃料;·直伤 B 无吃行)。

万敌无燃料底线(design §4 a 类·独例):开局词缀 ∩ 燃料集 = 空 →
:data:`cw_line_scales.RESTART_PENALTY`(与重开级同档);燃料集 =
本表万敌行**正值**词缀名的投影(吃怕表为源,投影派生单一源)。
「反伤类」= 正当防卫族同义(design §4 表注:AFFIX_EFFECTS 当前无
独立「反伤」注册名,万敌篇词条矩阵「强吃…反伤类」的族指即正当防卫本名)。
"""
from __future__ import annotations

from dataclasses import dataclass

from sr_od.application.currency_war.data.affix_effects_data import (
    AFFIX_EFFECTS,
)
from sr_od.application.currency_war.kernel.cw_line_scales import (
    AFFIX_STRONG_FUEL,
    AFFIX_STRONG_TOP,
    FEAR_PENALTY,
    RESTART_PENALTY,
)


@dataclass(frozen=True)
class AffixStance:
    """单线单词缀吃怕立场(吃=正/怕=负/重开级=极大负)。

    - ``score``:主阶段(成型常态)分值,现行帧消费值;
    - ``stage_overrides``:双面词条的阶段条件覆写((阶段名, 分值) 序列)。
      当前唯一双面词条 = 万敌×灼热轰炸(低血期怕 −150/成型后吃 +750,
      design §3.3):低血期判定输入面 = 运行时血量阈值现读(血量占当前
      上限比例低于阈值即低血期),血量未观察帧不覆写(主阶段分值兜底,
      fail 方向 = 成型常态);
    - ``note``:分值依据(攻略篇/设计节号)——手编数据的防漂移基准。
    """

    score: int
    stage_overrides: tuple[tuple[str, int], ...] = ()
    note: str = ''


#: 俗称/别名待采集登记(design §3.3「俗称建映射,未采集词条待实机采集
#: 归位,俗称键不入表」):攻略原话里的俗称在 AFFIX_EFFECTS 无对应注册名,
#: 禁猜键(错键 = 分值静默失效);实机简报词缀行采集到该词条后,在此建
#: 俗称→注册名映射并把分值登记进对应线行。
AFFIX_ALIASES_PENDING: dict[str, str] = {
    # 姬子列车吃「怪物提速」(final_jizi_train A 节:「吃忍无可忍/同步行动/
    # 怪物提速」)——52 词缀表无此名;候选(随从强化/首领强化等敌方提速族)
    # 语义均不唯一,待实机词缀行 OCR 采到原词再归位。
    '怪物提速': '',
    # 圣杯类怕「满愿」(final_grail_dual:「遇到满愿一定要刷掉!」)——
    # 52 词缀表无此名,待实机采集。
    '满愿': '',
}

#: 吃怕表本体(批 2 = 12 已审线全量;长尾 8 线无 counter 记载不登吃行,
#: 走兜底层)。逐行数据源 = final_comps 各篇 counter 节(原话注释保真)。
AFFINITY_TABLE: dict[str, dict[str, AffixStance]] = {
    # ===== 万敌单C(批 1 直入;final_wandi_burn 词条矩阵节)=====
    '万敌单C': {
        # 强吃·顶级:正当防卫(反伤)——「反伤类」族同义注释:当前
        # AFFIX_EFFECTS 无独立「反伤」注册名,族指即正当防卫本名
        # (万敌篇「强吃:正当防卫/忍无可忍/应激反应/灼热轰炸/一鼓作气/反伤类」)。
        '正当防卫': AffixStance(
            score=AFFIX_STRONG_TOP,
            note='final_wandi_burn 反伤利燃血(debuff=buff 典型);design §2 词缀强吃·顶级档'),
        # 强吃·燃料族:受击/挨打触发类词缀=燃血层的直接燃料。
        '忍无可忍': AffixStance(
            score=AFFIX_STRONG_FUEL,
            note='final_wandi_burn 敌多动旺=受击驱动叠层燃料;design §2 词缀强吃·燃料档'),
        '应激反应': AffixStance(
            score=AFFIX_STRONG_FUEL,
            note='受击触发类=燃血燃料(design §4 万敌行直入清单)'),
        '灼热轰炸': AffixStance(
            score=AFFIX_STRONG_FUEL,
            stage_overrides=(('低血期', FEAR_PENALTY),),
            note='双面词条:成型后吃 +750/低血期怕 −150(万敌篇「避讳:灼热轰炸双面(攻略:低血期怕,成型后吃)」)'),
        '一鼓作气': AffixStance(
            score=AFFIX_STRONG_FUEL,
            note='敌方行动增益=受击频率增益=燃血燃料(design §4 万敌行直入清单)'),
        # 重开级:掉血削上限对燃血是双损(掉血→减上限),机制反例 counter
        # (选卡克制表 pick_common.AFFIX_COUNTERS_FACTIONS「永久创伤→克燃血」同源)。
        '永久创伤': AffixStance(
            score=RESTART_PENALTY,
            note='final_wandi_burn「重开级:永久创伤」;design §2 重开级(排除=极大减分)'),
        # 已登记强吃线的未登记词条记 0 不罚(design §3.3)——不建 0 分键,
        # 缺键即 0(见 :func:`affix_line_score`)。
    },
    # ===== 希儿量子(final_seele_quantum counter 节)=====
    '希儿量子': {
        # 「重开级:量子熄火/丢失幸运/免死金牌/极速制冷/以人为本(攻略多帖)
        #  ——量子同频被禁=核心失效」(final_seele_quantum L76)。
        '量子熄火': AffixStance(
            score=RESTART_PENALTY,
            note='final_seele_quantum「重开级」;量子同频被禁=核心失效'),
        '丢失幸运': AffixStance(
            score=RESTART_PENALTY, note='final_seele_quantum「重开级」(攻略多帖)'),
        '免死金牌': AffixStance(
            score=RESTART_PENALTY, note='final_seele_quantum「重开级」(攻略多帖)'),
        '极速制冷': AffixStance(
            score=RESTART_PENALTY, note='final_seele_quantum「重开级」(攻略多帖)'),
        '以人为本': AffixStance(
            score=RESTART_PENALTY, note='final_seele_quantum「重开级」(攻略多帖)'),
        # 正当防卫「挡不住」二义标待核不登(final_seele_quantum L78「观察:
        # 正当防卫(攻略:『挡不住』——三星怪也能启动,免死金牌也挡不住)」
        # ——「挡不住」主语二义(希儿再现挡不住 or 希儿扛不住反伤),直接
        # 记载语义不可判,待实机核;登记期不猜方向)。
    },
    # ===== 命运圣杯红A(圣杯双核心类级 counter;final_grail_dual)=====
    # 注:双王圣杯(Saber 能量线)属长尾 8 线不登吃行——其能量逃逸怕由
    # 兜底层大招流轴泛化覆盖(圣杯篇构造机理「能量逃逸(克 Saber 路线)」)。
    '命运圣杯红A': {
        # 「counter 词条:正当防卫/复仇心切/一鼓作气/永久创伤/能量逃逸/满愿
        #  (遇到满愿一定要刷掉!)/极速制冷/量子熄火」(final_grail_dual L56-57)
        # + 构造机理「榜样激励(史料级:克高倍率单核)」;满愿俗称待采集不入
        # (AFFIX_ALIASES_PENDING)。
        '正当防卫': AffixStance(score=FEAR_PENALTY, note='final_grail_dual counter 节'),
        '复仇心切': AffixStance(score=FEAR_PENALTY, note='final_grail_dual counter 节'),
        '一鼓作气': AffixStance(score=FEAR_PENALTY, note='final_grail_dual counter 节'),
        '永久创伤': AffixStance(score=FEAR_PENALTY, note='final_grail_dual counter 节'),
        '能量逃逸': AffixStance(score=FEAR_PENALTY, note='final_grail_dual counter 节'),
        '榜样激励': AffixStance(score=FEAR_PENALTY, note='final_grail_dual 构造机理「克高倍率单核」(史料级)'),
        '极速制冷': AffixStance(score=FEAR_PENALTY, note='final_grail_dual counter 节'),
        '量子熄火': AffixStance(score=FEAR_PENALTY, note='final_grail_dual counter 节'),
    },
    # ===== 狼尊欢愉(final_yinlang_joy counter 节)=====
    '狼尊欢愉': {
        # 「counter 词条:避开正当防卫/能量逃逸/时间刺客/忍无可忍(攻略)
        #  ——均为克制『多动+大招频率』类的词条」(final_yinlang_joy L79/L201)。
        '正当防卫': AffixStance(score=FEAR_PENALTY, note='final_yinlang_joy counter 节(克制多动+大招频率)'),
        '能量逃逸': AffixStance(score=FEAR_PENALTY, note='final_yinlang_joy counter 节'),
        '时间刺客': AffixStance(score=FEAR_PENALTY, note='final_yinlang_joy counter 节'),
        '忍无可忍': AffixStance(score=FEAR_PENALTY, note='final_yinlang_joy counter 节'),
    },
    # ===== 绯英欢愉(final_feiying_joy)=====
    '绯英欢愉': {
        # 「counter 同欢愉族(正当防卫/能量逃逸类,克制大招/多动)」
        # (final_feiying_joy L158)——篇内只点名两词缀(「…类」不外推)。
        '正当防卫': AffixStance(score=FEAR_PENALTY, note='final_feiying_joy「counter 同欢愉族」'),
        '能量逃逸': AffixStance(score=FEAR_PENALTY, note='final_feiying_joy「counter 同欢愉族」'),
    },
    # ===== 大黑塔银河学者(final_daheita_aoe counter 节)=====
    '大黑塔银河学者': {
        # 「counter 词条:坠入陷阱/正当防卫/冰之熄火(攻略共识)」
        # (final_daheita_aoe L69/L141);冰之熄火→大黑塔=冰属性主C(主C属性列证据)。
        '坠入陷阱': AffixStance(score=FEAR_PENALTY, note='final_daheita_aoe counter 节(攻略共识)'),
        '正当防卫': AffixStance(score=FEAR_PENALTY, note='final_daheita_aoe counter 节(攻略共识)'),
        '冰之熄火': AffixStance(score=FEAR_PENALTY, note='final_daheita_aoe counter 节(攻略共识);大黑塔冰属性主C'),
    },
    # ===== 黄泉减益(final_huangquan_debuff counter 节)=====
    '黄泉减益': {
        # 「counter 词条:避免正当防卫/同步行动/免死金牌(攻略)」
        # (final_huangquan_debuff L72/L182「克大招流+多动」)。
        '正当防卫': AffixStance(score=FEAR_PENALTY, note='final_huangquan_debuff counter 节(反伤克前排核心)'),
        '同步行动': AffixStance(score=FEAR_PENALTY, note='final_huangquan_debuff counter 节(克大招流+多动)'),
        '免死金牌': AffixStance(score=FEAR_PENALTY, note='final_huangquan_debuff counter 节'),
    },
    # ===== DOT队(final_dot_kafka)=====
    'DOT队': {
        # 「净化身心环境别玩(羁绊注册表 note)」(final_dot_kafka L145)——
        # 敌人半血解所有负面+回血,DOT(负面状态)结算被整体拆除。
        '净化身心': AffixStance(
            score=RESTART_PENALTY,
            note='final_dot_kafka「净化身心环境别玩」;DOT=负面状态被整解'),
    },
    # ===== 龙丹战技点(final_longtail_others 龙丹节)=====
    '龙丹战技点': {
        # 「开局怕:正当防卫/极速制冷/丢失幸运类词条」(final_longtail_others
        # L49 攻略原文细节补记)——开局怕(攻略口径);现行消费面为全局
        # 线分,延展全局(保守向压分)。
        '正当防卫': AffixStance(score=FEAR_PENALTY, note='final_longtail_others 龙丹节「开局怕」;延展全局(保守向压分)'),
        '极速制冷': AffixStance(score=FEAR_PENALTY, note='final_longtail_others 龙丹节「开局怕」;延展全局(保守向压分)'),
        '丢失幸运': AffixStance(score=FEAR_PENALTY, note='final_longtail_others 龙丹节「开局怕」;延展全局(保守向压分)'),
    },
    # ===== 列车同行·反震(A 主体;final_jizi_train A 反震节;批 3 拆分)=====
    '列车同行·反震': {
        # 「词条:吃忍无可忍/同步行动/怪物提速;怕正当防卫/能量逃逸/时间刺客」
        # (final_jizi_train L25,A 反震主体形态)——怪物提速俗称待采集
        # (AFFIX_ALIASES_PENDING);+750=受击触发类燃料档(design §5 姬子A
        # 「吃…(+750 受击触发类)」,反震吃敌方多动)。
        '忍无可忍': AffixStance(
            score=AFFIX_STRONG_FUEL,
            note='final_jizi_train A 节「吃忍无可忍」(受击触发类燃料)'),
        '同步行动': AffixStance(
            score=AFFIX_STRONG_FUEL,
            note='final_jizi_train A 节「吃同步行动」(受击触发类燃料)'),
        '正当防卫': AffixStance(score=FEAR_PENALTY, note='final_jizi_train A 节「怕正当防卫」'),
        '能量逃逸': AffixStance(
            score=FEAR_PENALTY,
            note='final_jizi_train §6 脆弱点「能量逃逸(150 能量大招受能量逃逸影响)」(史料级)'),
        '时间刺客': AffixStance(score=FEAR_PENALTY, note='final_jizi_train A 节「怕时间刺客」'),
        # 重症难题:§6 脆弱点「重症难题(治疗/护盾削弱)克三月七盾循环
        # (史料级)」(final_jizi_train L212-213)。
        '重症难题': AffixStance(score=FEAR_PENALTY, note='final_jizi_train §6 脆弱点「克三月七盾循环」(史料级)'),
    },
    # ===== 列车同行·直伤(B;final_jizi_train B 输出节无词条记载)=====
    '列车同行·直伤': {
        # 怕集同 A 保守复制(design §5「B 节无记载保守复制」——A 节类级
        # counter 证据覆盖两形态);无吃行(受击燃料档属 A 反震引擎,B
        # 直伤不吃)。注:机制推演 B 可能更怕正当防卫(直伤高频攻击吃
        # 反伤),无实证不升档(design §5)。
        '正当防卫': AffixStance(score=FEAR_PENALTY, note='B 节无记载,怕集同 A 保守复制(design §5)'),
        '能量逃逸': AffixStance(score=FEAR_PENALTY, note='B 节无记载,怕集同 A 保守复制(design §5)'),
        '时间刺客': AffixStance(score=FEAR_PENALTY, note='B 节无记载,怕集同 A 保守复制(design §5)'),
        '重症难题': AffixStance(score=FEAR_PENALTY, note='B 节无记载,怕集同 A 保守复制(design §5)'),
    },
    # ===== 昼神阿雅 / 反甲白厄:词缀面无实证记载,不建行(走兜底层)=====
    # 昼神阿雅:counter 仅 boss 面(「counter:电视机 boss → 避」,boss 表辖)。
    # 反甲白厄:忌「燃血类/回血 buff 减行动值」均无注册名(52 词缀表无对应
    #   词条,待实机采集);受击触发类两推断打架(受击多→反甲触发多 vs
    #   受击多→白厄本体先死)标 0 待 sim 不登(design §5 白厄节)。
}

#: 无燃料底线登记线(design §4 a 类:词缀依赖独例 = 万敌;开局词缀 ∩
#: 燃料集 = 空 → 重开级)。出现第二条依赖线时在此扩名即可——燃料集恒按
#: 「该线吃怕表行正值投影」现算,无第二份名单。
FUEL_BOTTOM_LINES: frozenset[str] = frozenset({'万敌单C'})


# ===== 兜底层(未登记线的效果原文泛化;方向保守:只给怕不给吃)=====
# design §3.3:「效果原文分档作未登记词缀默认兜底(方向保守:只给怕不给吃)」
# + 批 2 任务:「未登记线(长尾 8 线 + 词缀面空白的已审线)由兜底层覆盖
# 怕向;已登记强吃线(万敌/列车同行)的未登记词条记 0 不罚」。
# 判定边界:线在 AFFINITY_TABLE 有非空行 = 已登记线(只查表,缺键记 0);
# 无行/空行 = 未登记线(泛化层给怕)。泛化规则只收效果原文无歧义项
# (有向争议词缀如正当防卫/时间刺客不泛化——机制泛化不预判方向)。

#: 主C属性列(属性熄火×7 判定;design §3.3 批 2:「大黑塔冰/希儿量子等,
#: 从 final_comps 引擎节核」)。仅收直接证据(词缀 counter 记载/装备效果
#: 原文中的属性字眼);核不出的线不入(该线属性熄火不泛化——CW 注册表
#: 无属性字段,用本体游戏知识补全属机制推定,违反证据序)。当前三条
#: 证据全部位于已登记线(泛化层暂无作用对象),表为版本重跑扩行基准。
LINE_MAINC_ELEMENT: dict[str, str] = {
    '希儿量子': '量子',      # final_seele_quantum 量子熄火重开级(量子同频主C)
    '大黑塔银河学者': '冰',  # final_daheita_aoe 冰之熄火怕(攻略共识)
    '反甲白厄': '物理',      # 以牙还牙甲「250%…物理伤害」(装备原文;反甲本体物理输出)
}

#: 前后台主力轴(前台/后台/前后台熄火判定):线主C的前台/后排主力性。
# 判据 = 线主C排位(char_positions 覆盖 > cw_chars position 注册);
# 'common' 无实证覆盖 = 前后台灵活/无固定主力面,不入轴(不泛化)。
FRONT_LINES: frozenset[str] = frozenset({
    '列车同行·反震',   # 姬子·启行 front(@0-1 前排首位,final_jizi_train 站位节;A/B 共享 core/站位)
    '列车同行·直伤',   # 同 A(拆分只分装备/引擎结算方向,站位不分岔)
    '命运圣杯红A',     # Archer front(构造机理:前排 0-3 位 102/120)
    '希儿量子',        # 希儿 front(×3C@0 标准式)
    '黄泉减益',        # 黄泉 front(×3C@0)
    '巡海击破',        # 波提欧 front(注册表)
    '龙丹战技点',      # 丹恒·饮月 front(「饮月放一号位」,姬子复制变体节)
    '大黑塔银河学者',  # 大黑塔 front(×3C@0)
    '反甲白厄',        # 白厄 front(×3C@0;反甲流受击吃前排)
    '狼尊欢愉',        # 银狼LV.999 front(×3C@0)
    '昼神阿雅',        # 阿格莱雅 front(速度流)
    '追击飞霄',        # 飞霄 front(注册表)
    '景元仙舟',        # 景元 front(注册表)
    '绯英欢愉',        # 绯英注册 common 但 char_positions 覆盖 front@0(Final 标准式)
    '万敌单C',         # 万敌注册 common 但攻略硬约束 front@0 独占前排(燃血吃受击)
})
BACK_LINES: frozenset[str] = frozenset({
    '千冶减益',        # 千冶·刃 back(注册表;皮靴=速度触发频率)
    '火花星间旅人',    # 花火 back(注册表)
})

#: B1 引擎型分类(21 线,批 3 姬子拆分;README B1 三类 + final_comps 各篇
#: 引擎节/cw_comps 条目注释补核)。消费 = 兜底层泛化(大招流×能量逃逸;
#: dot×净化身心)——A/B 两套均有词缀登记行走表不走泛化,轴值此处作
#: 分类标注/文档引用(通道⑤未来条目挂轴声明:A 受击流不吃速度类增益/
#: B 大招流吃充能类增益)。旧「姬子拆分前双轴任一 hit 即中档」声明随
#: 拆分退役,各归各轴。
LINE_ENGINE_KIND: dict[str, str] = {
    '列车同行·反震': '受击',   # 盾反姬子 A 主体(README B1 受击流)
    '列车同行·直伤': '大招',   # B 输出姬子:助战技直伤+风暴潮叠层(final_jizi B 节;批 3 归轴)
    '命运圣杯红A': '行动',   # Archer 战技连发(README B1 行动流)
    '千冶减益': '行动',      # 千冶·刃皮靴断层第一(速度=攻击触发频率,本条 plaza 校准注)
    '绯英欢愉': '大招',      # 终结技循环吃阿哈加成+永久增幅(README B1 大招流)
    '希儿量子': '行动',      # 拉条链即输出(README B1 行动流)
    '黄泉减益': '大招',      # 大招流(README B1:「黄泉…装备=充能件」)
    '巡海击破': '击破',      # 击破弹射/物理削韧(final_huangquan 构造机理乱破/波提欧行)
    '龙丹战技点': '行动',    # 饮月无限耗点强化普攻(战技点消耗流,README B1 行动流 Archer 同型)
    '双王圣杯': '大招',      # Saber 能量伪永动机(README B1 大招流)
    '火花星间旅人': '行动',  # 花火吃点巧普攻(cw_comps 条目 BV 转录注)
    '大黑塔银河学者': '大招',  # 充能三件套保证开大效率(README B1 大招流)
    '银枝群攻': '大招',      # 冷笑话引擎+大招驱动羁绊协同(cw_comps 条目注)
    '反甲白厄': '受击',      # 以牙还牙甲受击反伤(README B1 受击流)
    '狼尊欢愉': '行动',      # 升费链多动普攻(README B1 行动流)
    '昼神阿雅': '行动',      # 速度流:速度→强度转化链(构造机理三乘区闭环)
    '追击飞霄': '追击',      # 飞霄天赋追击增伤(攻略 76883466)
    '万敌单C': '受击',       # 受伤充能+燃血反打(README B1 受击流)
    'DOT队': 'dot',          # 叠层×引爆,敌方回合结算(final_dot_kafka)
    '景元仙舟': '追击',      # 神君叠段主动输出位(构造机理景元节)
    '专家桑博DOT': 'dot',    # 风化满层引爆(桑博专家变体,final_dot_kafka)
}

#: 暴击引擎轴(丢失幸运判定):线的输出引擎依赖幸运一击(装备公式核心件
#: 为幸运一击类/核心机制吃幸运)。出处 = final_comps 装备公式节。
CRIT_ENGINE_LINES: frozenset[str] = frozenset({
    '双王圣杯',        # 冷笑话引擎「施放终结技时幸运一击率+10%×5层」(Saber 装备公式核心件)
    '银枝群攻',        # 冷笑话引擎(cw_comps 装备公式「银枝(风暴潮+冷笑话)」)
    '火花星间旅人',    # 星间转职章 43.2% 幸运暴伤=唯一有效应(cw_comps 条目 BV 转录注)
})

#: dot 轴(净化身心判定):DOT 主派线(引擎轴派生,单一源)。
_DOT_LINES: frozenset[str] = frozenset(
    line for line, kind in LINE_ENGINE_KIND.items() if kind == 'dot')

#: 属性熄火词缀名 → 属性(AFFIX_EFFECTS 注册名「X之熄火/X熄火」直读)。
_ELEMENT_AFFIXES: dict[str, str] = {
    '风之熄火': '风', '火之熄火': '火', '冰之熄火': '冰', '雷之熄火': '雷',
    '物理熄火': '物理', '量子熄火': '量子', '虚数熄火': '虚数',
}


def generic_fear_bonus(line_name: str,
                        enemy_affixes: tuple[str, ...]) -> int:
    """兜底层泛化分(design §3.3:未登记线 × 未登记词缀,效果原文泛化
    **只给怕不给吃**;方向保守 = 有向争议词缀不泛化)。

    规则集(最小无歧义集;每条 = 效果原文直读,不依赖攻略实证):
    - 属性熄火×7 → 主C属性命中(:data:`LINE_MAINC_ELEMENT`,当前证据
      全在已登记线,泛化暂无作用对象);
    - 前台/后台/前后台熄火 → 前后台主力轴命中(「…伤害只能造成1点」
      克该排主力);
    - 丢失幸运(幸运一击率 −25%)→ 暴击引擎轴;
    - 净化身心(解所有负面+回血)→ dot 轴(DOT=负面状态被整解;
      减益线同被克,但已登记线黄泉减益无此记载=记 0,未登记线千冶减益
      不泛化减益轴保持两线口径一致,版本重跑补);
    - 能量逃逸(攻击者能量 −4)→ 大招流轴(能量循环引擎受损;
      final_grail_dual 构造机理「能量逃逸(克 Saber 路线)」佐证)。
    """
    total = 0
    for affix in enemy_affixes:
        if _generic_fear_hit(line_name, affix):
            total += FEAR_PENALTY
    return total


def _generic_fear_hit(line_name: str, affix: str) -> bool:
    """泛化单词条命中判定(:func:`generic_fear_bonus` 的规则表本体)。"""
    element = _ELEMENT_AFFIXES.get(affix)
    if element is not None:
        return LINE_MAINC_ELEMENT.get(line_name) == element
    if affix == '前台熄火':
        return line_name in FRONT_LINES
    if affix == '后台熄火':
        return line_name in BACK_LINES
    if affix == '前后台熄火':
        return line_name in FRONT_LINES or line_name in BACK_LINES
    if affix == '丢失幸运':
        return line_name in CRIT_ENGINE_LINES
    if affix == '净化身心':
        return line_name in _DOT_LINES
    if affix == '能量逃逸':
        return LINE_ENGINE_KIND.get(line_name) == '大招'
    return False


def affix_row_of(line_name: str) -> dict[str, AffixStance]:
    """线吃怕行读口(未登记线 → 空表;泛化层由 :func:`affix_line_score` 挂)。"""
    return AFFINITY_TABLE.get(line_name, {})


def fuel_set_of(line_name: str) -> frozenset[str]:
    """线燃料集 = 吃怕表该行**正值**词缀名投影(design §4:吃怕表为源,
    投影派生单一源——禁手抄第二份名单;行登记变动燃料集自动跟随)。"""
    return frozenset(
        affix for affix, stance in affix_row_of(line_name).items()
        if stance.score > 0)


def affix_line_score(line_name: str,
                     enemy_affixes: tuple[str, ...]) -> int:
    """线词缀分(design §2 公式的词缀分量;线分引擎消费)。

    = Σ 本线吃怕表[开局词缀] 主阶段分值 + 无燃料底线(登记线 ∧ 开局词缀 ∩
    燃料集 = 空 → 重开级)。登记边界(design §3.3 批 2):线有非空吃怕行 =
    已登记线——未登记词条记 0 不罚(强吃线的未登记词条尤其不误伤);线
    无行 = 未登记线(长尾 8 线+词缀面空白的已审线)——泛化层只给怕
    (:func:`generic_fear_bonus`)。双面词条阶段覆写:低血期判定需运行时
    血量,本函数(开局简报消费点)不覆写,主阶段分值兜底。
    """
    row = affix_row_of(line_name)
    total = sum(row[a].score for a in enemy_affixes if a in row)
    if not row:
        total += generic_fear_bonus(line_name, enemy_affixes)
    if line_name in FUEL_BOTTOM_LINES:
        fuel = fuel_set_of(line_name)
        if fuel and not (fuel & set(enemy_affixes)):
            total += RESTART_PENALTY
    return total


def affix_restart_hit(line_name: str,
                      enemy_affixes: tuple[str, ...]) -> bool:
    """线词缀面重开级命中判定(设计 §6 配方锁联动消费;kernel 侧原语——
    cw_intention 禁 import 策略层线分引擎,重开级命中 = 本表可判的子集)。

    True ⟺ 本线吃怕行任一开局词缀分值 = 重开级 ∨ 无燃料底线触发。
    泛化层恒不给重开级(只怕 −150),不参与本判定。
    """
    row = affix_row_of(line_name)
    if any(row[a].score <= RESTART_PENALTY for a in enemy_affixes if a in row):
        return True
    if line_name in FUEL_BOTTOM_LINES:
        fuel = fuel_set_of(line_name)
        if fuel and not (fuel & set(enemy_affixes)):
            return True
    return False


def _validate_affinity_table() -> None:
    """构建校验(import 即炸):词缀键必须在 AFFIX_EFFECTS 注册名空间
    (手编表写错名 = 分值静默失效);线名必须在 COMP_LIBRARY(同理);
    泛化层轴表覆盖全 21 线(缺行 = 该线泛化静默失效)。
    boss 面校验见 :func:`_validate_boss_table`(同文件)。"""
    from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY
    line_names = {c.name for c in COMP_LIBRARY}
    for line, row in AFFINITY_TABLE.items():
        if line not in line_names:
            raise ValueError(f'吃怕表孤儿线名(COMP_LIBRARY 无此线):{line!r}')
        for affix in row:
            if affix not in AFFIX_EFFECTS:
                raise ValueError(
                    f'吃怕表词缀键不在 AFFIX_EFFECTS 注册名空间:'
                    f'{line!r}×{affix!r}')
    # 泛化层轴覆盖校验(主C属性/引擎轴为部分覆盖——属性列只收直接证据,
    # 覆盖校验只辖全集轴)。
    if set(LINE_ENGINE_KIND) != line_names:
        raise ValueError('LINE_ENGINE_KIND 必须恰好覆盖 COMP_LIBRARY 全部线')
    for line in (*FRONT_LINES, *BACK_LINES, *CRIT_ENGINE_LINES):
        if line not in line_names:
            raise ValueError(f'泛化层轴表孤儿线名:{line!r}')
    for line, element in LINE_MAINC_ELEMENT.items():
        if line not in line_names:
            raise ValueError(f'主C属性列孤儿线名:{line!r}')
        if element not in _ELEMENT_AFFIXES.values():
            raise ValueError(f'主C属性列非法属性值:{line!r}×{element!r}')


_validate_affinity_table()


# ============================================================
# BOSS 面 + 非 boss 强敌(design §3.4;开局简报前置决策)
# ============================================================

@dataclass(frozen=True)
class BossStance:
    """单线单 boss 吃怕立场(boss 无阶段条件,无 stage_overrides)。

    - ``score``:重开级(:data:`RESTART_PENALTY`)或怕(:data:`FEAR_PENALTY`);
    - ``note``:分值依据(攻略篇/设计节号)。
    """

    score: int
    note: str = ''


#: boss 吃怕表(键 = boss 规范公司名,BOSS_MECHANICS 名空间;俗称经
#: ``normalize_boss_name`` 归位)。数据依据 = 4 线实证(design §3.4:
#: 姬子 4 只〔扑满归强敌段〕/希儿蕉研组/阿雅电视机/白厄史瓦罗)——
#: **无直接记载不登记**(D4 清单唯红绿灯带类级括注且适用线均已实证,
#: 其余条目无类级指向不外推);其余 16 线 boss 面空白声明接受(表尾注),
#: 版本重跑攻略 boss 记载补登;boss 面初版单向(只登怕/重开级,无吃档)。
BOSS_AFFINITY: dict[str, dict[str, BossStance]] = {
    # ===== 列车同行 A/B 两套(final_jizi_train 节奏与 counter 节)=====
    # 「counter:扑满(拖时间)/死龙/酒杯怪/电视机/存护星神/红绿灯(白厄子
    # 形态)」(L77)——姬子线 boss 克制引擎结算双形态同源(类级记载),
    # 两套同登记;扑满/红绿灯归非 boss 强敌段;存护星神待验证映射表;
    # 红绿灯「(白厄子形态)」注记正名 = 克白厄子形态非姬子(design §3.4,
    # 与 README「红绿灯→转姬子」一致,不登本行)。
    '列车同行·反震': {
        '灰手生命科技': BossStance(   # 死龙(BOSS_NICKNAMES 归位)
            score=FEAR_PENALTY, note='final_jizi_train counter 节「死龙」(A/B 双形态同源)'),
        '造梦兄弟影业': BossStance(   # 酒杯怪
            score=FEAR_PENALTY, note='final_jizi_train counter 节「酒杯怪」(A/B 双形态同源)'),
        '造梦互动娱乐': BossStance(   # 电视机
            score=FEAR_PENALTY, note='final_jizi_train counter 节「电视机」(A/B 双形态同源)'),
    },
    '列车同行·直伤': {
        '灰手生命科技': BossStance(
            score=FEAR_PENALTY, note='final_jizi_train counter 节「死龙」(A/B 双形态同源)'),
        '造梦兄弟影业': BossStance(
            score=FEAR_PENALTY, note='final_jizi_train counter 节「酒杯怪」(A/B 双形态同源)'),
        '造梦互动娱乐': BossStance(
            score=FEAR_PENALTY, note='final_jizi_train counter 节「电视机」(A/B 双形态同源)'),
    },
    # ===== 希儿量子(final_seele_quantum counter 节「蕉研组 boss(攻略)」)=====
    '希儿量子': {
        '造梦互动娱乐': BossStance(   # 蕉研组
            score=FEAR_PENALTY, note='final_seele_quantum counter 节「蕉研组 boss(攻略)」'),
    },
    # ===== 昼神阿雅(final_longtail_others 昼神节「counter:电视机 boss → 避」)=====
    '昼神阿雅': {
        '造梦互动娱乐': BossStance(   # 电视机
            score=FEAR_PENALTY, note='final_longtail_others 昼神节「counter:电视机 boss → 避」(史料+plaza 双源)'),
    },
    # ===== 反甲白厄(final_baie_reflect「红绿灯/史瓦罗/祸源萨姆 = 重开级(攻略多帖共识)」)=====
    # 祸源萨姆→虫人兵器映射待实机校验(两名各含「祸源/萨姆」词素:虫人兵器
    # 代表「示死祸源:深魇蝗灾」vs 火线动力机甲代表「星核猎手·萨姆」,不
    # 臆造),入 BOSS_NAME_PENDING;红绿灯 = 非 boss 强敌(下段)。
    '反甲白厄': {
        '深穹智械科技': BossStance(   # 史瓦罗(BOSS_NICKNAMES 补映射)
            score=RESTART_PENALTY,
            note='final_baie_reflect「史瓦罗 = 重开级(攻略多帖共识)」'),
    },
    # ===== 其余 16 线 boss 面空白声明(design §3.4「D4 类级清单兜底或
    # 声明接受」二选一,选声明接受)=====
    # README D4 清单逐项核:唯红绿灯带类级括注「反甲系」——其适用线
    # (反甲白厄/万敌单C)已经实证登记(红绿灯归非 boss 强敌段,万敌见
    # final_wandi_burn 词条矩阵);蕉研组/扑满/死龙/酒杯怪/电视机/存护
    # 星神在 D4 原文**无类级指向**,其余线不据此外推(「无直接记载不
    # 登记」——类推自图鉴机制的克制行属推断,不作为登记依据);圣杯
    # 两线(命运圣杯红A/双王圣杯)boss 面空白接受,版本重跑攻略 boss
    # 记载补登。
}

#: 非 boss 强敌吃怕表(设计 §3.4「单列知识条目,作用点=开局线分」)。
#: 键 = 强敌俗称(独立强敌名空间,非 boss 规范名/非词缀注册名):
#: - 「红绿灯」:小怪非 boss(用户确认 2026-08-17)且在 52 词缀表外——
#:   简报词缀行 OCR 命中即扣(词缀读链透传原名,无需注册)。
#: - 「扑满」:非 boss 强敌(奖励节点替换为扑满战斗)——出现条件 =
#:   持有扑满环境(经济过热/经济严重过热,PIGGY_ENV_NAMES 单一源派生),
#:   开局投资环境三选一持有即见(经济环境产物)。
STRONG_ENEMY_AFFINITY: dict[str, dict[str, BossStance]] = {
    # 红绿灯重开级:白厄(final_baie_reflect「红绿灯…重开级」+ 红绿灯预案
    # 「有红绿灯的,转启行队!」)/万敌(final_wandi_burn「重开级:永久创伤/
    # 红绿灯(机械 counter,攻略)」)。
    '反甲白厄': {
        '红绿灯': BossStance(
            score=RESTART_PENALTY,
            note='final_baie_reflect「红绿灯 = 重开级(攻略多帖共识)」+ 红绿灯预案「转启行队」'),
    },
    '万敌单C': {
        '红绿灯': BossStance(
            score=RESTART_PENALTY,
            note='final_wandi_burn 词条矩阵「重开级:永久创伤/红绿灯(机械 counter)」'),
    },
    # 扑满怕档(counter 有解降档,design §3.3):姬子反震慢速「打不动扑满
    # 拖到结束」,但瓦尔特延后倒计时是机制解(final_jizi_train「老杨必拿」)
    # → 降档为怕 −150 而非重开级(A/B 双形态同登记——拖时间克慢速对直伤
    # 形态同向,B 无独立解记载)。定性出处注:拖时间克反震慢速为
    # final_jizi_train A 节记载;「扑满 = 经济环境产物」的实机呈现面
    # (过热环境局奖励节点扑满化)出处 = invest_effects.md 经济过热条。
    '列车同行·反震': {
        '扑满': BossStance(
            score=FEAR_PENALTY,
            note='final_jizi_train「打不动扑满拖到结束」;瓦尔特延后=机制解降档(design §3.3)'),
    },
    '列车同行·直伤': {
        '扑满': BossStance(
            score=FEAR_PENALTY,
            note='A 节类级记载 A/B 同源(拖时间克慢速;瓦尔特机制解同用)'),
    },
}

#: boss 旧名待验证映射表(design §3.4「旧名:存护星神/贝洛伯格加血机器入
#: 待验证映射表(不静默丢)」;版本重跑核,不臆造规范名指向)。
#: - 存护星神:姬子 counter 节记载(final_jizi_train L77),20 boss 图鉴
#:   无对应名,候选不可辨——实机简报 boss 行采集到后再归位;
#: - 贝洛伯格加血机器:万敌 counter(final_wandi_burn「counter:贝洛伯格
#: 加血机器/攻击频率不高的怪」),同上;
#: - 祸源萨姆:白厄重开级三 boss 之一,虫人兵器(示死祸源)vs 火线动力
#:   机甲(萨姆)词素两可,实机校验后入 BOSS_NICKNAMES+反甲白厄行。
BOSS_NAME_PENDING: dict[str, str] = {
    '存护星神': '',
    '贝洛伯格加血机器': '',
    '祸源萨姆': '虫人兵器?',   # 候选指向待实机校验(非定值,空值同为待采)
}


def boss_line_score(line_name: str,
                    plane_bosses: tuple[str, ...]) -> int:
    """线 boss 分(design §3.4「boss 分 = Σ三只克制」;开局简报 3 boss
    候选集均权——位面真值 = CollectPlaneIntel 后逐位面,权重精细档先均权,
    即开局即按简报全集求和)。boss 名经 :func:`normalize_boss_name` 归位
    规范公司名再查表(俗称/简称输入合法);未登记 boss/线记 0(16 线空白
    boss 面 = 类级兜底后声明接受的幅度)。
    """
    from sr_od.application.currency_war.data.cw_enemy_data import (
        normalize_boss_name,
    )
    row = BOSS_AFFINITY.get(line_name, {})
    return sum(row[normalize_boss_name(b)].score
               for b in plane_bosses
               if normalize_boss_name(b) in row)


def strong_enemy_score(line_name: str,
                       enemy_affixes: tuple[str, ...],
                       held_invest: frozenset[str]) -> int:
    """非 boss 强敌分(design §3.4;作用点 = 开局线分,与 boss 分量合并
    进 LineScore.boss)。

    可观察性双通道:红绿灯 = 简报词缀行 OCR 原名透传命中(词缀读链不注册
    白名单,未知名原样入 enemy_affixes);扑满 = 持有扑满环境
    (:data:`PIGGY_ENV_NAMES` 单一源派生,经济环境产物开局可见)。
    """
    from sr_od.application.currency_war.kernel.cw_reward_node import (
        PIGGY_ENV_NAMES,
    )
    row = STRONG_ENEMY_AFFINITY.get(line_name, {})
    total = 0
    if '红绿灯' in row and '红绿灯' in enemy_affixes:
        total += row['红绿灯'].score
    if '扑满' in row and (held_invest & PIGGY_ENV_NAMES):
        total += row['扑满'].score
    return total


def boss_restart_hit(line_name: str,
                     plane_bosses: tuple[str, ...],
                     enemy_affixes: tuple[str, ...] = (),
                     held_invest: frozenset[str] = frozenset()) -> bool:
    """线 boss/强敌面重开级命中判定(设计 §6 配方锁联动消费;与
    :func:`affix_restart_hit` 同族 kernel 原语)。True ⟺ boss 表或强敌表
    任一命中分值 = 重开级。
    """
    from sr_od.application.currency_war.data.cw_enemy_data import (
        normalize_boss_name,
    )
    from sr_od.application.currency_war.kernel.cw_reward_node import (
        PIGGY_ENV_NAMES,
    )
    row = BOSS_AFFINITY.get(line_name, {})
    for b in plane_bosses:
        stance = row.get(normalize_boss_name(b))
        if stance is not None and stance.score <= RESTART_PENALTY:
            return True
    srow = STRONG_ENEMY_AFFINITY.get(line_name, {})
    if '红绿灯' in srow and '红绿灯' in enemy_affixes \
            and srow['红绿灯'].score <= RESTART_PENALTY:
        return True
    return bool('扑满' in srow and held_invest & PIGGY_ENV_NAMES
                and srow['扑满'].score <= RESTART_PENALTY)


def _validate_boss_table() -> None:
    """boss 面构建校验(import 即炸):boss 键必须在 BOSS_MECHANICS 20
    规范公司名空间(写俗称 = 永不命中);强敌键必须非 boss 规范名(防
    名空间串线);线名必须在 COMP_LIBRARY。"""
    from sr_od.application.currency_war.data.cw_enemy_data import (
        BOSS_MECHANICS,
    )
    from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY
    from sr_od.application.currency_war.kernel.cw_reward_node import (
        PIGGY_ENV_NAMES,
    )
    line_names = {c.name for c in COMP_LIBRARY}
    for line, row in BOSS_AFFINITY.items():
        if line not in line_names:
            raise ValueError(f'boss 吃怕表孤儿线名:{line!r}')
        for boss in row:
            if boss not in BOSS_MECHANICS:
                raise ValueError(
                    f'boss 吃怕表键不在 BOSS_MECHANICS 规范名空间'
                    f'(写俗称 = 永不命中,经 BOSS_NICKNAMES 归位):'
                    f'{line!r}×{boss!r}')
    for line, row in STRONG_ENEMY_AFFINITY.items():
        if line not in line_names:
            raise ValueError(f'强敌表孤儿线名:{line!r}')
        for enemy in row:
            if enemy in BOSS_MECHANICS:
                raise ValueError(
                    f'强敌表键撞 boss 规范名空间(非 boss 强敌禁入):'
                    f'{line!r}×{enemy!r}')
    if not PIGGY_ENV_NAMES:
        raise ValueError('扑满环境名单为空(强敌段扑满触发通道失效)')


_validate_boss_table()
