"""货币战争 词缀源效果结构化注册 + 装备注册表改写成员扫描申报(非策略源效果辖域)。

**辖域**(统一 state 迭代 BoardState 数据结构设计 §5.1「词缀效果辖域申报」与
§7 扫描范围源 c/源 e 的代码化;两份 data 注册表 = 效果文本真值,本模块 = 规格申报面):
- **词缀源结构化注册** ``AFFIX_EFFECT_SPECS``:会改写 BoardState 字段的敌人词缀
  (成长的烦恼/变宝为废/永久创伤)按 EffectSpec 四元组建格。键 = affix_effects_data
  词缀名,spec.id 同值——词缀无 plaza id 命名空间,效果清单 first() 以词缀名为键。
- **装备注册表改写成员扫描** ``scan_rewrite_equipments`` × ``EQUIP_REWRITE_DECLARATIONS``:
  cw_equipment_data 全量中改写金/小队生命/生命上限/容量/单位/装备面的成员逐件申报
  写入归属——装备效果大量随投资卡发放后成常驻写入源,不点名=无人看管。

**边界**:
- STRATEGY_EFFECTS 只产策略源(cw_investments overlay 头注,键空间/孤儿校验独立);
  环境源('portal')登记端未建,ActiveEffect.source 词表预留。
- 本模块只建**规格与申报**,不做运行时接线:词缀登记挂点(简报/位面详情词缀读链 →
  ``ActiveEffectInventory.register_affix``)与改写面写端(LevelUp 金/装备库存/
  hp_max)均未接线,现状一律观察覆盖兜底——各 spec 的 notes 记写入归属。
- 开局不利不入 SPEC:其确定性写端已有专用载体 kernel/cw_opening_hp.opening_hp_prior
  (_AFFIX_HP_DELTA,ADR-0559),再建 EffectSpec = −20 数值第二份(双源漂移),
  见 AFFIX_SPEC_EXEMPT。

**防漂移锁**(sr-od-test test_cw_affix_spec_registry):谓词扫描命中集必须恰等于
SPEC ∪ 豁免集(词缀)/申报表(装备)。运行时采集(write_affix_effects)向
affix_effects_data 追加新词缀后,新改写源若未申报,下一轮测试即红、强制人工评审;
**不设 import 即炸**——运行时采集路径不能因覆盖缺口中断(与 cw_investments
孤儿校验「结构自洽炸、覆盖完备靠锁」分层同理)。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.affix_effects_data import AFFIX_EFFECTS
from sr_od.application.currency_war.data.cw_equipment_data import EQUIPMENTS
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    BattlefieldEffect,
    DurationKind,
    DutyFlags,
    EffectKind,
    EffectSpec,
    TriggerKind,
)
from sr_od.application.currency_war.kernel.cw_investments import EconomyEffect

# ===== 词缀源效果规格(键 = affix_effects_data 词缀名;spec.id 同键)=====
AFFIX_EFFECT_SPECS: dict[str, EffectSpec] = {
    # 成长的烦恼:官方「在你达到8级后，每次购买经验会损失1金币。」(affix_effects_data
    # 同键原文;competitors.md 玩法知识面)。改写面 = LevelUp 经验金面:等级窗开窗后
    # 每次购经验 +1 金,确定性 → 归属 = 逻辑写(效果写入归属判据:结果可准确计算);
    # 写端未接线,现走观察覆盖兜底。duties.predict = 买经验成本对账须预知(注意:
    # predict_for 的 action→trigger 映射只回同 trigger 条目,本条 CONDITIONAL 不经
    # 该口,写端取词缀修饰走 by_source('affix')/payload 字段直读)。
    # 字段镜像策略卡「成长的快乐」xp_click_discount_from_level 对(8 级起降价,
    # 此处反向加价);聚合通道不共用(词缀源不经 aggregate_economy)。
    '成长的烦恼': EffectSpec(
        id='成长的烦恼', name='成长的烦恼', trigger=TriggerKind.CONDITIONAL,
        duration=DurationKind.WHILE_HELD, category=EffectKind.ECONOMY,
        payload=EconomyEffect(xp_click_surcharge_from_level=1,
                              xp_click_surcharge_from_level_at=8),
        duties=DutyFlags(predict=True),
        notes='LevelUp 金面改写源:8级起每次购经验+1金;归属=逻辑写(确定性),写端未接线走观察覆盖'),
    # 变宝为废:官方「每个位面开始时，首次合成的进阶装备会有50%的概率变成垃圾袋。」
    # 改写面 = 装备库存:随机 50% → 不建逻辑写端,观察收口(归属判据:含概率/随机
    # 结果不可预知)。trigger=ON_MERGE(装备合成事件,与武力刷新同触发面;每位面
    # 首次性由 payload 字段语义承载)。duties.predict = 装备合成期望对账
    # (compare_equip_expect)须预知垃圾袋分支,防合法随机态刷缺陷台账。
    '变宝为废': EffectSpec(
        id='变宝为废', name='变宝为废', trigger=TriggerKind.ON_MERGE,
        duration=DurationKind.WHILE_HELD, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(first_merge_equip_junk=0.5),
        duties=DutyFlags(predict=True),
        notes='装备库存改写源:每位面首次合成进阶装备50%变垃圾袋;随机面不建逻辑写,观察收口'),
    # 永久创伤:官方「我方小队生命值降低时，会减少等同于生命值降低值20%的生命上限，
    # 最多降低生命上限的60%。」hp_max 字段在 BoardState 缺位(健康充值/成本控制/
    # 二极管/本词缀=来源四源,一并缺口申报)→ 观察收口;数值仅建档不进经济分
    # (gold_per_20hp_lost 同先例)。零响应登记(游戏侧自算,bot 无待办)。
    '永久创伤': EffectSpec(
        id='永久创伤', name='永久创伤', trigger=TriggerKind.CONDITIONAL,
        duration=DurationKind.WHILE_HELD, category=EffectKind.STATE,
        payload=EconomyEffect(hp_max_loss_pct_of_loss=20, hp_max_loss_cap_pct=60),
        notes='hp_max 词缀源(来源枚举第四源):hp_max 字段缺位,观察收口;数值仅建档'),
}

#: 谓词命中但不建 EffectSpec 的词缀(豁免必须点名 + 理由,禁静默)。
AFFIX_SPEC_EXEMPT: dict[str, str] = {
    # 开局不利:效果「游戏开始时,小队生命值减少20点」的确定性写端已有专用载体
    # kernel/cw_opening_hp.opening_hp_prior(_AFFIX_HP_DELTA['开局不利']=-20,
    # ADR-0559 hp0_survey 实证档),经 cw_reconcile.reconcile_hp 开局分支消费;
    # 再建 EffectSpec = −20 数值第二份,禁。
    '开局不利': '已有专用写端载体 cw_opening_hp._AFFIX_HP_DELTA(ADR-0559),禁第二份−20数值源',
}


def _validate_affix_specs() -> None:
    """AFFIX_EFFECT_SPECS 构建校验(import 即炸,防注册表漂移静默失联):

    ① 孤儿键:词缀名必须在 affix_effects_data(运行时采集删改词缀名 → 这里炸);
    ② id/name 双等于键(词缀无 plaza id,键即身份);
    ③ payload↔category 一致(与 STRATEGY_EFFECTS 同规则);
    ④ pending → notes 必写保守支。
    覆盖完备性(谓词扫描 vs 申报集)不在此层——运行时采集会追加新词缀,
    覆盖缺口归测试锁(见模块 docstring「防漂移锁」)。
    """
    for name, spec in AFFIX_EFFECT_SPECS.items():
        if name not in AFFIX_EFFECTS:
            raise ValueError(
                f"AFFIX_EFFECT_SPECS 孤儿键(affix_effects_data 无此词缀):{name!r}")
        if spec.id != name or spec.name != name:
            raise ValueError(f"AFFIX_EFFECT_SPECS id/name 必须等于词缀键:{name!r}")
        if spec.category in (EffectKind.ECONOMY, EffectKind.STATE):
            ok = isinstance(spec.payload, EconomyEffect)
        elif spec.category == EffectKind.BATTLEFIELD:
            ok = isinstance(spec.payload, BattlefieldEffect)
        else:
            ok = False  # 词缀辖域无 UNIT_BUFF 用例;新类别入册须先扩本守卫
        if not ok:
            raise ValueError(
                f"AFFIX_EFFECT_SPECS payload↔category 不一致:{name!r} "
                f"category={spec.category} payload={type(spec.payload).__name__}")
        if spec.pending and not spec.notes:
            raise ValueError(f"AFFIX_EFFECT_SPECS pending 条目必须写保守支 notes:{name!r}")


# ===== 词缀改写谓词扫描(效果面完备性 §7 源 e 的代码化)=====
#: 判定谓词 = 效果文本改写金/生命/装备/单位面。粗召回过滤器(宁滥勿缺:
#: 新改写源漏报 = 无人看管,误报 = 人工评审一次)。面形 = (面名, 关键词组集):
#: 任一关键词组**组内全现**即命中该面(组内=AND,组间=OR——单关键词组退化
#: 为包含判定)。敌方侧生命类文本(熄火/强化/净化族)用「小队」「我方小队」
#: 锚定排除。倒计时增减族(决战在即/战个痛快/时间刺客)不入谓词——倒计时
#: 无 BoardState 字段载体,非本申报面辖域。
_AFFIX_REWRITE_FACES: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...] = (
    ('gold', (('金币',),)),
    ('hp', (('小队生命值',),)),
    ('hp_max', (('我方小队', '生命上限'),)),
    ('equip', (('合成', '装备'),)),
    ('unit', (('1星复制',), ('解锁并获得',))),
)


def _match_faces(effect_text: str,
                 faces: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...]
                 ) -> list[str]:
    """效果文本 × 面形表 → 命中面名(组内 AND/组间 OR,见 _AFFIX_REWRITE_FACES;
    文本先去空白再匹配——注册表正文含采集期 OCR 空格,如「变为对应的特 权装备」)。"""
    compact = ''.join(effect_text.split())
    hit: list[str] = []
    for face, groups in faces:
        if any(all(kw in compact for kw in group) for group in groups):
            hit.append(face)
    return hit


def scan_rewrite_affixes() -> dict[str, str]:
    """affix_effects_data 全量 × 改写谓词 → {词缀名: 命中面(逗号连)}。

    命中集与申报集(SPEC ∪ EXEMPT)的恰等由测试锁看管;新增改写词缀未申报
    时锁红(运行时采集不中断,见模块 docstring)。
    """
    return {name: ','.join(_match_faces(text, _AFFIX_REWRITE_FACES))
            for name, text in AFFIX_EFFECTS.items()
            if _match_faces(text, _AFFIX_REWRITE_FACES)}


# ===== 装备注册表改写成员扫描(效果面完备性 §7 源 c 的代码化)=====
#: 判定谓词 = 效果文本触发金/生命/容量字段改写 ∨ 改写单位装备归属 ∨ 发牌进席/
#: 解锁获得单位。面形语义同 _AFFIX_REWRITE_FACES(组内 AND/组间 OR)。
#: 词表口径:小队生命 = 「小队生命值」措辞(单位战斗内生命/护盾文本不含该词,
#: 天然排除);罪孽王冠正文 OCR 截断(「扣除双倍小队」后残缺),以残文关键词
#: 单列。节点态改写(破解芯片「节点变为弱化状态」)不在源 c 谓词辖域,归节点
#: 序列台账面。
_EQUIP_REWRITE_FACES: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...] = (
    ('gold', (('金币',),)),
    ('squad_hp', (('小队生命值',),)),
    ('squad_hp_truncated', (('扣除双倍小队',),)),
    ('hp_max', (('生命上限提高',),)),
    ('cap', (('团队规模',),)),
    ('unit_copy', (('1星复制',),)),
    ('unit_unlock', (('解锁并获得',),)),
    ('equip_own', (('取下',),)),
    ('equip_transform', (('变为同类型',), ('变为对应的特权装备',),
                         ('变为特权装备',), ('变为简易装备',))),
    ('equip_project', (('投影',),)),
    ('equip_grant', (('选择一件获得',),)),
    ('equip_autofill', (('填充两件',),)),
)


def scan_rewrite_equipments() -> dict[str, str]:
    """cw_equipment_data 全量 × 改写谓词 → {装备名: 命中面(逗号连)}。

    命中集与 EQUIP_REWRITE_DECLARATIONS 的恰等由测试锁看管;装备注册表为
    生成文件(勿手改),新增改写件后锁红 → 在申报表补行评审。
    """
    return {name: ','.join(_match_faces(eq.effect, _EQUIP_REWRITE_FACES))
            for name, eq in EQUIPMENTS.items()
            if _match_faces(eq.effect, _EQUIP_REWRITE_FACES)}


# ===== 装备改写成员写入归属申报表(键集必须恰等于 scan_rewrite_equipments 命中集)=====
#: 归属判据:结果可准确计算(确定性公式+已知输入)→ 逻辑写;含概率/随机 →
#: 不建逻辑写端,观察收口。「未接线」= 写端载体未落,现状一律观察覆盖兜底。
EQUIP_REWRITE_DECLARATIONS: dict[str, str] = {
    '财富宝钻': '金面:装备者每3备战阶段+1金(确定性→逻辑写候选,未接线);容量面:+1团队规模'
              '——deploy_cap 识别真值观察写端照常跟踪,效果侧不建 cap 改写(宝钻豁免申报面)',
    '财富': '金面:进新节点+4金(确定性→逻辑写候选,轮首收入族同型,未接线)',
    '精密拆装扳手': '金面:重复获得拆装扳手改+1金(确定性→逻辑写);装备归属面:∞次取下全装备回区;现观察覆盖兜底',
    '极·阿瓦隆': '生命面:获得宝具时+50小队生命(确定性→逻辑写候选,未接线;hp 写入闸辖)',
    '诅咒·阿瓦隆': '生命面:战斗结算−6小队生命(确定性→逻辑写候选,与结算覆盖同时序,未接线)',
    '罪孽王冠': '生命面:战败扣双倍小队生命(确定性→逻辑写候选,未接线);注册表正文 OCR 截断(「扣除双倍小队」后残缺)',
    '生命之环': '生命上限面:+15%(确定性→逻辑写候选);hp_max 字段缺位,观察收口+缺口申报',
    '生命之环·特权': '生命上限面:+30%(确定性→逻辑写候选);hp_max 字段缺位,观察收口+缺口申报',
    '诅咒·宝石剑泽尔里奇': '容量面:−1团队规模——deploy_cap 识别真值观察写端照常跟踪,效果侧不建 cap 改写(宝钻同款豁免)',
    '数据拷贝仪': '单位面:装备者每参与3战获自身1星复制(计数臂确定性→逻辑写候选;任意获得30%概率臂随机→观察收口)',
    '数据拷贝仪Max': '单位面:同数据拷贝仪(参与2战/伤害增幅50%;另含立即获得银狼LV.999)',
    '数据拷贝仪Pro': '单位面:同数据拷贝仪(参与3战/伤害增幅50%)',
    '员工投影仪': '单位面:拖拽→备战席该角色1星复制进席(确定性→逻辑写候选;官方前置门=拖动目标3费及以下);写端=工具拖拽执行,现观察覆盖兜底',
    '完美投影仪': '单位面:同员工投影仪(无费用门);现观察覆盖兜底',
    '分身墨镜': '单位面:前台强度40%时解锁并获1星专家银狼(条件解锁,未接线观察覆盖兜底)',
    '分身墨镜Max': '单位面:同分身墨镜(50%/2星银狼;未接线观察覆盖兜底)',
    '冶金炉': '装备面:拖装备变同类型随机=产出不可预知→观察收口;拖角色=全拆+三件同刷随机→观察收口',
    '特权赋予卡': '装备面:拖拽后进阶装备变对应特权装备/角色已穿进阶装备随机一件变特权(确定性变换;拖拽执行落地,现观察覆盖兜底)',
    '拆装扳手': '装备归属面:角色装备全量回区(确定性→逻辑写;现有流向锚=cw_equip_env 装备转移链);工具消耗品−1',
    '干将莫邪': '装备面:战斗开始时投影随机进阶装备——战斗内临时面,非备战期装备库存持久改写;观察覆盖兜底',
    '极·干将莫邪': '装备面:同干将莫邪(70%概率投影特权装备);观察覆盖兜底',
    '诅咒·干将莫邪': '装备面:投影同干将莫邪+进战斗前随机3件临时变简易(随机→观察收口)',
    '好运令牌': '装备面:拖拽后从四件推荐进阶装备选一件获得(选定后确定→逻辑写候选);现观察覆盖兜底',
    '随便骰子': '装备归属面:穿戴者每节点自动随机填充两件装备(随机→观察收口;自动行为写入类)',
    '随便骰子·特权': '装备归属面:同随便骰子(填充特权装备;随机→观察收口)',
}


_validate_affix_specs()
