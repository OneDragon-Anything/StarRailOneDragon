"""货币战争 词缀源效果结构化注册 + 装备注册表改写成员扫描申报(非策略源效果辖域)。

**辖域**(统一 state 迭代 GameState 数据结构设计 §5.1「词缀效果辖域申报」与
§7 扫描范围源 c/源 e 的代码化;两份 data 注册表 = 效果文本真值,本模块 = 规格申报面):
- **词缀源结构化注册** ``AFFIX_EFFECT_SPECS``:会改写 GameState 字段的敌人词缀
  (成长的烦恼/变宝为废/永久创伤)按 EffectSpec 四元组建格。键 = affix_effects_data
  词缀名,spec.id 同值——词缀无 plaza id 命名空间,效果清单 first() 以词缀名为键。
- **装备注册表改写成员扫描** ``scan_rewrite_equipments`` × ``EQUIP_REWRITE_DECLARATIONS``:
  cw_equipment_data 全量中改写金/小队生命/生命上限/容量/单位/装备面的成员逐件申报
  写入归属——装备效果大量随投资卡发放后成常驻写入源,不点名=无人看管。
- **装备改写成员写端落码登记** ``EQUIP_WRITE_SIDES``:申报表 25 件逐件登记
  落码写端(桥/贡献算术/动作上报/负写端四形,分形判据见其行注);桥与
  贡献算术宿主 = kernel/cw_effect_inventory.py 文末「装备改写写端」段
  (免模块级成环,与板面重写桥同宿主纪律);动作上报宿主 =
  kernel/cw_action_report/tool_use(工具动作机械执行直接上报写容器)。
- **词缀运行时登记挂点共用体** ``register_affixes_from_names``:简报/位面详情
  两读链的产出点经它入效果账本(生产调用方 =
  ``operations/cw_screen/cw_screen_briefing.py::CwScreenBriefing.observe``
  词缀读链登记段,开局首读 / ``operations/cw_screen/cw_screen_plane_intel.py``
  上报节点词缀登记段,接管局补采)。

**边界**:
- STRATEGY_EFFECTS 只产策略源(cw_investments overlay 头注,键空间/孤儿校验独立);
  环境源('portal')登记端未建,ActiveEffect.source 词表预留。
- 改写面写端:装备申报面已按归属判据落码(EQUIP_WRITE_SIDES 四形登记;
  写端桥为账本→字段桥,生产挂点接线归节点结算/获得回执各辖批,接线前
  一律观察覆盖兜底;动作上报形 = 工具动作上报函数已接线 live,工具七行
  归 kernel/cw_action_report/tool_use);词缀面写端(CwActionLevelUpParam
  金/装备库存/hp_max)不在本模块,归属单一源 = 各 spec 的 notes,仍观察
  覆盖兜底。
- 开局不利不入 SPEC:其确定性写端已有专用载体 kernel/cw_opening_hp.opening_hp_prior
  (_AFFIX_HP_DELTA),再建 EffectSpec = −20 数值第二份(双源漂移),
  见 AFFIX_SPEC_EXEMPT。

**防漂移锁**(sr-od-test test_cw_affix_spec_registry):谓词扫描命中集必须恰等于
SPEC ∪ 豁免集(词缀)/申报表(装备)。运行时采集(write_affix_effects)向
affix_effects_data 追加新词缀后,新改写源若未申报,下一轮测试即红、强制人工评审;
**不设 import 即炸**——运行时采集路径不能因覆盖缺口中断(与 cw_investments
孤儿校验「结构自洽炸、覆盖完备靠锁」分层同理)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.affix_effects_data import AFFIX_EFFECTS
from sr_od.application.currency_war.data.cw_equipment_data import EQUIPMENTS
from sr_od.application.currency_war.kernel import (
    cw_effect_inventory as _effect_inventory,
)
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    SOURCE_AFFIX,
    BattlefieldEffect,
    DurationKind,
    DutyFlags,
    EffectKind,
    EffectSpec,
    TriggerKind,
)
from sr_od.application.currency_war.kernel.cw_investments import EconomyEffect

if TYPE_CHECKING:
    # 仅类型注解引用(项目规范允许);GameState/Unit 真类在 cw_game_state,
    # 其模块头 import 本模块的兄弟模块(cw_effect_inventory),模块级 import
    # 有成环风险,与登记挂点共用体的运行期惰性 import 纪律同型。
    pass

# ===== 词缀源效果规格(键 = affix_effects_data 词缀名;spec.id 同键)=====
AFFIX_EFFECT_SPECS: dict[str, EffectSpec] = {
    # 成长的烦恼:官方「在你达到8级后，每次购买经验会损失1金币。」(affix_effects_data
    # 同键原文;competitors.md 玩法知识面)。改写面 = CwActionLevelUpParam 经验金面:等级窗开窗后
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
        notes='CwActionLevelUpParam 金面改写源:8级起每次购经验+1金;归属=逻辑写(确定性),写端未接线走观察覆盖'),
    # 变宝为废:官方「每个位面开始时，首次合成的进阶装备会有50%的概率变成垃圾袋。」
    # 改写面 = 装备库存:随机 50% → 不建逻辑写端,观察收口(归属判据:含概率/随机
    # 结果不可预知)。trigger=ON_MERGE(装备合成事件,与武力刷新同触发面;每位面
    # 首次性由 payload 字段语义承载)。duties.predict = 随机改写面在案
    # (装备合成对账类消费方须预知垃圾袋分支,防合法随机态刷缺陷台账)。
    '变宝为废': EffectSpec(
        id='变宝为废', name='变宝为废', trigger=TriggerKind.ON_MERGE,
        duration=DurationKind.WHILE_HELD, category=EffectKind.BATTLEFIELD,
        payload=BattlefieldEffect(first_merge_equip_junk=0.5),
        duties=DutyFlags(predict=True),
        notes='装备库存改写源:每位面首次合成进阶装备50%变垃圾袋;随机面不建逻辑写,观察收口'),
    # 永久创伤:官方「我方小队生命值降低时，会减少等同于生命值降低值20%的生命上限，
    # 最多降低生命上限的60%。」hp_max 字段在 GameState 缺位(健康充值/成本控制/
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
    # hp0_survey 实证档),经 cw_reconcile.reconcile_hp 开局分支消费;
    # 再建 EffectSpec = −20 数值第二份,禁。
    '开局不利': '已有专用写端载体 cw_opening_hp._AFFIX_HP_DELTA,禁第二份−20数值源',
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
#: 无 GameState 字段载体,非本申报面辖域。
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
#: 归属判据(效果写入归属判据正本 = docs/develop/sr_od/application/currency_war/game_state/
#: effect-domain.md §6.3;详设 = GameState 数据结构设计 §5.3):结果可准确
#: 计算(确定性公式+已知输入)→ 逻辑写;含概率/随机 → 不建逻辑写端,观察
#: 收口。「现观察覆盖兜底」= 生产挂点接线归各辖批(工具执行/节点结算/获得
#: 回执),接线前记录面维持观察覆盖。
EQUIP_REWRITE_DECLARATIONS: dict[str, str] = {
    '财富宝钻': '金面:装备者每3备战阶段+1金(确定性→逻辑写;写端=贡献算术'
              'equip_diamond_phase_gold,组合写归节点边界金结算载体 settle_node_'
              'boundary_gold——窗口与轮首收入共享,禁单独直写;逐件进度折算的'
              '本拍增量由调用侧供给,载体禁内发明进度存储);容量面:+1团队规模'
              '——deploy_cap 识别真值观察写端照常跟踪,效果侧不建 cap 改写(宝钻'
              '豁免申报面)',
    '财富': '金面:进新节点+4金(确定性→逻辑写;写端=贡献算术 equip_node_gold_'
          'grant,轮首收入族同型,组合写归节点边界金结算载体 settle_node_'
          'boundary_gold)',
    '精密拆装扳手': '金面:重复获得拆装扳手改+1金(确定性→逻辑写;写端=贡献算术'
                 'equip_wrench_duplicate_gold,组合写收口=settle_wrench_duplicate_'
                 'gold,获得回执时点窗口独占);装备归属面:∞次取下全装备回区,'
                 '使用面写端=动作上报 report:report_action_precision_wrench_use_'
                 'param(两笔逻辑写:回区+穿戴清空,工具不递减)',
    '极·阿瓦隆': '生命面:获得宝具时+50小队生命(确定性→逻辑写;写端=桥 apply_'
              'equip_acquire_hp,获得时点窗口独占,hp 写入闸辖——hp 未读跳过;'
              '现观察覆盖兜底)',
    '诅咒·阿瓦隆': '生命面:战斗结算−6小队生命(确定性;结算屏真值同拍已含该效果'
                '——独立 logic 直写=双计/部分预测刷缺陷台账,观察收口;确定性'
                '算术归 sim 真值面与战前决策消费)',
    '罪孽王冠': '生命面:战败扣双倍小队生命(确定性;损失幅度=战斗事实非独立可算'
             '面——独立直写=部分预测刷缺陷台账,观察收口;确定性算术归 sim 真值'
             '面与战前决策消费);注册表正文 OCR 截断(「扣除双倍小队」后残缺)',
    '生命之环': '生命上限面:+15%(确定性→逻辑写候选);hp_max 字段缺位,观察收口'
              '+缺口申报',
    '生命之环·特权': '生命上限面:+30%(确定性→逻辑写候选);hp_max 字段缺位,观察'
                 '收口+缺口申报',
    '诅咒·宝石剑泽尔里奇': '容量面:−1团队规模——deploy_cap 识别真值观察写端照常跟踪,'
                      '效果侧不建 cap 改写(宝钻同款豁免;负写端=观察收口)',
    '数据拷贝仪': '单位面:装备者每参与3战获自身1星复制(计数臂确定性→逻辑写;写端'
               '=桥 spawn_equip_bench_unit,成熟回执时点窗口独占;参与计数进度'
               '载体=settle_copy_machine_participation(现值观察面=前台+后台在册'
               '单位));任意获得30%概率臂随机→观察收口',
    '数据拷贝仪Max': '单位面:计数臂同数据拷贝仪(参与2战→逻辑写,写端=入席桥,'
                 '阈值表=COPY_MACHINE_MATURE_BATTLES);立即获得银狼LV.999 腿 = '
                 '获得后果(1星[口述·权威 2026-09-18],后果 = 装备数据行后果应用 '
                 'apply_equip_acquire_consequence 统一辖,不经本表登记行双登记)',
    '数据拷贝仪Pro': '单位面:计数臂同数据拷贝仪(参与3战→逻辑写,写端=入席桥)',
    '员工投影仪': '单位面:拖拽→备战席该角色1星复制进席(确定性→逻辑写;官方前置'
               '门=拖动目标3费及以下,门在发射位判据面辖、上报侧注册表现读前置查'
               '防御纵深);写端=动作上报 report:report_action_staff_projector_use_'
               'param(复制走获得链 gain_character 统一时序,复制触发三合一=口述·'
               '权威 2026-09-21)',
    '完美投影仪': '单位面:同员工投影仪(无费用门;确定性→逻辑写,写端=动作上报 '
               'report:report_action_perfect_projector_use_param,复制走获得链)',
    '分身墨镜': '单位面:官方文「获得时解锁并获得1星专家【银狼】」=获得时点确定性'
             '发放,前台强度40%为数值行非发放条件(确定性→逻辑写;获得后果=装备'
             '数据行后果应用[口述·权威 2026-09-18,送出1星银狼直接进备战席、'
             '效果与商店购买完全一致],写端=桥 apply_equip_acquire_consequence)',
    '分身墨镜Max': '单位面:同分身墨镜(获得时点 2星专家【银狼】,官方文明示星级;'
                '确定性→逻辑写,获得后果=装备数据行后果应用,写端=桥 '
                'apply_equip_acquire_consequence)',
    '冶金炉': '装备面:拖装备变同类型随机、拖角色全拆+三件同刷(随机面→逻辑写'
            '随机通道 write_logic_rand 采样链;采样池 = cw_sim_equips.furnace_reroll '
            '同源,披露键 furnace_mutate_pool_v0_same_category;写端=动作上报 '
            'report:report_action_furnace_use_param;变异面不走获得链不触发获得'
            '回调,产物后果候实机采证留证行 furnace_mutate_consequence_candidate)',
    '特权赋予卡': '装备面:拖拽后进阶装备变对应特权装备/角色已穿进阶装备随机一件变'
              '特权(确定性变换→逻辑写;映射=·特权后缀 36/36 全覆盖;写端=桥 '
              'transform_equip_to_privilege 库存腿,本批接线 = 工具上报合并单笔'
              '消费(移除工具 ∧ 变换同笔,映射桥 privilege_counterpart;桥零写'
              '分支透传留证);拖角色腿按不能拖角色处理 fail-closed 留证[用户裁定 '
              '2026-09-21 候实机测试],穿域特权化桥 transform_worn_equip_to_'
              'privilege 留守)',
    '拆装扳手': '装备归属面:角色装备全量回区(确定性→逻辑写;使用面写端=动作上报 '
             'report:report_action_wrench_use_param,两笔逻辑写 = equips 合并'
             '(移除工具 ∧ 追加穿戴件)+ 行域穿戴清空);工具消耗品−1(合并同笔)',
    '干将莫邪': '装备面:战斗开始时投影随机进阶装备——战斗内临时面,非备战期装备库存'
             '持久改写;观察收口',
    '极·干将莫邪': '装备面:同干将莫邪(70%概率投影特权装备);观察收口',
    '诅咒·干将莫邪': '装备面:投影同干将莫邪+进战斗前随机3件临时变简易(随机→观察收口)',
    '好运令牌': '装备面:拖拽后从四件推荐进阶装备选一件获得(选定后确定→逻辑写;写端'
             '=桥 grant_equip_item,选定回执时点窗口独占;现役原子通路消费真值归'
             '观察,写端接线候工具上报形态)',
    '随便骰子': '装备归属面:穿戴者每节点自动随机填充两件装备(随机→观察收口;自动行为'
             '写入类)',
    '随便骰子·特权': '装备归属面:同随便骰子(填充特权装备;随机→观察收口)',
}


# ===== 装备改写成员写端落码登记(键集必须恰等于 EQUIP_REWRITE_DECLARATIONS)=====
#: 逐件登记落码写端,值词表五形(窗口独占性分形判据 =
#: cw_effect_inventory 文末「装备改写写端」段头注):
#: - ``bridge:<函数名>``      写端桥——触发窗口独占的确定性直写;
#: - ``contribution:<函数名>`` 贡献算术——触发窗口与未接写端共享,零直写,
#:                             组合写收口 = 节点边界金结算载体
#:                             (settle_node_boundary_gold/settle_wrench_
#:                             duplicate_gold,cw_effect_inventory 文末);
#: - ``report:<函数名>``      动作上报写端——工具动作机械执行后上报函数
#:                             直接写容器(宿主 = kernel/cw_action_report/
#:                             tool_use,tool-gain-report 迭代;确定面
#:                             write_logic、随机面 write_logic_rand 采样链);
#: - ``op:<锚>``              op 域既有写端(本批零新增);
#: - ``observation``           负写端——随机面/真值同拍送达面/字段缺位面。
EQUIP_WRITE_SIDES: dict[str, str] = {
    '财富宝钻': 'contribution:equip_diamond_phase_gold',
    '财富': 'contribution:equip_node_gold_grant',
    '精密拆装扳手': 'contribution:equip_wrench_duplicate_gold',
    '极·阿瓦隆': 'bridge:apply_equip_acquire_hp',
    '诅咒·阿瓦隆': 'observation',
    '罪孽王冠': 'observation',
    '生命之环': 'observation',
    '生命之环·特权': 'observation',
    '诅咒·宝石剑泽尔里奇': 'observation',
    '数据拷贝仪': 'bridge:spawn_equip_bench_unit',
    '数据拷贝仪Max': 'bridge:spawn_equip_bench_unit',
    '数据拷贝仪Pro': 'bridge:spawn_equip_bench_unit',
    '员工投影仪': 'report:report_action_staff_projector_use_param',
    '完美投影仪': 'report:report_action_perfect_projector_use_param',
    '分身墨镜': 'bridge:apply_equip_acquire_consequence',
    '分身墨镜Max': 'bridge:apply_equip_acquire_consequence',
    '冶金炉': 'report:report_action_furnace_use_param',
    '特权赋予卡': 'bridge:transform_equip_to_privilege',
    '拆装扳手': 'report:report_action_wrench_use_param',
    '干将莫邪': 'observation',
    '极·干将莫邪': 'observation',
    '诅咒·干将莫邪': 'observation',
    '好运令牌': 'bridge:grant_equip_item',
    '随便骰子': 'observation',
    '随便骰子·特权': 'observation',
}


def _validate_equip_write_sides() -> None:
    """EQUIP_WRITE_SIDES 构建校验(import 即炸,与 _validate_affix_specs 同纪律):

    ① 键集恰等于 EQUIP_REWRITE_DECLARATIONS(每件申报恰一个落码写端,零静默);
    ② 值词表封闭:bridge:/contribution: 目标函数必须在 cw_effect_inventory
       可解析且可调用(改名/删除即炸);report: 目标函数必须在
       cw_action_report.tool_use 在册(动作上报写端单一宿主,改名/删除
       即炸);op: 锚非空;observation 无载荷;
    ③ 落码形(bridge/contribution/report/op)申报 notes 必含「逻辑写」、
       observation 形必含「观察收口」——登记与归属申报互证,防单边漂移
       (report: 随机面 write_logic_rand 属逻辑族随机写,同辖「逻辑写」)。
    覆盖完备性(扫描命中集 vs 申报表键集)归测试锁(模块 docstring「防漂移锁」)。
    """
    if set(EQUIP_WRITE_SIDES) != set(EQUIP_REWRITE_DECLARATIONS):
        raise ValueError(
            'EQUIP_WRITE_SIDES 键集必须恰等于 EQUIP_REWRITE_DECLARATIONS:'
            f'多={sorted(set(EQUIP_WRITE_SIDES) - set(EQUIP_REWRITE_DECLARATIONS))} '
            f'少={sorted(set(EQUIP_REWRITE_DECLARATIONS) - set(EQUIP_WRITE_SIDES))}')
    for name, side in EQUIP_WRITE_SIDES.items():
        notes = EQUIP_REWRITE_DECLARATIONS[name]
        if side == 'observation':
            if '观察收口' not in notes:
                raise ValueError(f'负写端行申报必含「观察收口」:{name!r}')
        elif side.startswith(('bridge:', 'contribution:')):
            fn = getattr(_effect_inventory, side.split(':', 1)[1], None)
            if not callable(fn):
                raise ValueError(
                    f'写端目标在 cw_effect_inventory 不可解析:{name!r} → {side!r}')
            if '逻辑写' not in notes:
                raise ValueError(f'落码形行申报必含「逻辑写」归属成文:{name!r}')
        elif side.startswith('report:'):
            # 动作上报写端单一宿主 = cw_action_report.tool_use(函数内惰性
            # import:tool_use 依赖链经 cw_gain_chain/cw_game_state,与本
            # 模块无环,登记挂点共用体同型纪律)。
            from sr_od.application.currency_war.kernel.cw_action_report import (
                tool_use as _tool_use,
            )
            fn = getattr(_tool_use, side.split(':', 1)[1], None)
            if not callable(fn):
                raise ValueError(
                    f'写端目标在 cw_action_report.tool_use 不在册:{name!r}'
                    f' → {side!r}')
            if '逻辑写' not in notes:
                raise ValueError(f'落码形行申报必含「逻辑写」归属成文:{name!r}')
        elif side.startswith('op:'):
            if not side[3:].strip():
                raise ValueError(f'op 形写端必带既有锚:{name!r}')
            if '逻辑写' not in notes:
                raise ValueError(f'op 形行申报必含「逻辑写」归属成文:{name!r}')
        else:
            raise ValueError(
                f'EQUIP_WRITE_SIDES 值词表外:{name!r} → {side!r}'
                '(合法形 = bridge:/contribution:/report:/op:/observation)')


# ===== 词缀运行时登记挂点·共用体(简报/位面详情两读链同一登记体)=====
# 登记判据 = 词缀名命中结构化注册(AFFIX_EFFECT_SPECS;效果清单实例以词缀名
# 为 spec.id 键)。注册表外词缀(纯数值/无改写面)零动作,照旧观察覆盖兜底;
# 开局不利走 AFFIX_SPEC_EXEMPT 豁免(专用写端载体,禁第二份数值源)。
# 登记面 best-effort:调用方以 try/except 包裹、失败不阻塞读链主链(与策略源
# 选卡登记挂点同纪律,effect-domain.md §7.3「登记挂点纪律」)。
def register_affixes_from_names(session: object, names: list[str]) -> list[str]:
    """词缀 OCR 名集 → 命中结构化注册的词缀入效果账本(source='affix')。

    - **幂等**:已在册词缀源条目(spec.id = 词缀名)跳过——简报重入/retry、
      位面详情补采重跑同词缀集不得双登记(实例按 spec_key 唯一,
      effect-domain.md §9.1 销案「同卡叠加语义」同源)。
    - **注册表命中才登记**:AFFIX_EFFECT_SPECS 之外的词缀无结构化规格 →
      零动作;改写面写端不归登记挂点(归属单一源 = 各 spec.notes 与
      EQUIP_REWRITE_DECLARATIONS,接线前观察覆盖兜底)。
    - acquired_t = 登记时点节点序快照((plane-1)*9+round,基 1,ActiveEffect
      坐标系;GameState 节点单例;节点未观察(引导窗)= None 缺位,登记面
      不炸,last_state 帧回退已随链退役批删除);余期播种/推进/到期与策略
      源共用同一套挂点逻辑(声明式驱动:节点 tick/计数 bump 按 duties 与
      duration 语义自动辖及词缀条目,挂点代码零来源特判)。
    - 返回本次实际登记的词缀名列表(调用方留证日志;零命中返回空表)。

    game_state_of 运行期函数内 import:board_state 所在模块头 import 本模块
    的兄弟模块(cw_effect_inventory),保持本模块零运行期容器依赖、可离线
    单测(与 cw_effect_inventory 的惰性 import 纪律同型)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        game_state_of,
    )

    gs = game_state_of(session)
    effects = gs.effects
    registered_ids = {e.spec.id for e in effects.by_source(SOURCE_AFFIX)}
    hits: list[EffectSpec] = []
    for name in dict.fromkeys(names):   # 名集内去重保序(读链不应产重名,防御)
        if name in registered_ids:
            continue
        spec = AFFIX_EFFECT_SPECS.get(name)
        if spec is not None:
            hits.append(spec)
    if not hits:
        return []
    _nd = gs.node.value
    acquired_t: int | None = (
        (_nd.plane - 1) * 9 + _nd.round_num) if _nd is not None else None
    for spec in hits:
        effects.register_affix(spec, acquired_t)
    return [spec.name for spec in hits]


_validate_affix_specs()
_validate_equip_write_sides()
