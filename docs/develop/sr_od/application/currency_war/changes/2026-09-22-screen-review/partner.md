# T-11 选择伙伴 修法设计(partner)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:对抗收敛待用户裁决+新规范增补待裁决(对抗轨迹:r1 未收敛 7 条→修订→r2 未收敛 2 条→修订→r3 未收敛 1 条低→修订→r4 收敛 0 条;新规范增补 = §3,增补依据 = respec-T9-T15.md §2.3;增补节对抗:respec-attack-AB 判未收敛 11 条(中 2 低 9)→ 按 11 条定点修订 §3→复攻(respec-attack-AB-r2)残留 3 条一行级→二轮修订→编排侧机械验证收口(2026-09-22,T-37 晨报 G4))
- 发现源:`.debug/progress/2026-09-22-cw-screen-review/reports/T-11-r1.md`(F-1..F-6;总判定高1 中2 低3)。涉事代码与代码内文档以仓库现状为真值;定位一律符号锚 / 文档节号(行号不作定位依据,约定 = flow/README.md 卷首)。路径根 = `src/sr_od/application/currency_war/`。

## 1. 问题与动机

### F-1 画面 op 决策出口:idx 越界静默钳位 + 决策缺席盲选 idx0(高)

- **现状症状**:`operations/cw_screen/cw_screen_partner.py::CwScreenPartner.act` 首轮决策块两条违规路径——①`idx = pick.idx if 0 <= pick.idx < len(cands) else 0`:决策返回 idx 越界被**静默钳到 0** 续跑(流程侧值域改写 + 静默降级;该行无注释自述、无正本在册背书);②`if match is not None and options:` 为假时策略器不被调用,以常量 `idx = 0` + `reason = 'no-candidates(fallback)'` 盲选派发——候选空(options 空 ⇔ cands 空,obs options 由 cands enumerate 生成)虽被块尾 `round_fail('伙伴屏无候选…')` 显式拦截(零盲发,报告 §3.3 正面面),但 **match 缺席 ∧ 候选非空 = 真盲发路径**(局外直跑即落此支)。`decide` 返回 None/异型 → `pick.idx` AttributeError = 异常出口响亮(合规,但诊断面只有类型名不指因)。
- **根因归层(根源两问)**:根在**流程层**——决策出口兜底残留:`idx=0` 常量盲选 = 流程侧默认决策,钳位句 = 流程侧值域改写。决策控制分层铁律(flow/README.md §1)已把「动作值域过滤」划归策略侧、禁流程侧任何决策闸门与政策判断;op-layer.md §1.1 出口③(决策无有效输出 = 异常 fail,零盲发)、§1.3(非法返回 = 策略器 bug 响亮暴露,**禁静默跳过或降级续跑**)反向禁止。现役策略实现(`strategies/impl/flow.py::decide_partner`,idx 恒取自 options)契约上不越界,该路径 bug 才可达——但正本恰规定该情形必须响亮暴露。同族家族模式又一例(遭遇 T-4 / 盛会之星 T-8 / 选择装备 T-9 / 卜者 T-12 / 祈愿 T-13 均已判同族违规;跨稿计数口径不一,族级全集与计数归 T-37 对账,→ §2.2 家族联动面);本稿删兜底、换守卫,修根非症状。
- **解决到哪**:首轮决策块改三守卫(决策输入具名 fail 零盲发 / 返回契约具名 fail / idx 值域守卫断言恒炸),删默认 idx、钳位句与块尾重复 fail;`chosen_partner` 写端守卫条件随守卫简化;`screens/partner.md` as-built 申报守卫出口;行为锁桩面(`cw_match=None` 驱动)随守卫语义换 match 桩(断言面不变)。
- **明确不解决**:重入裁决 / 确认被拒守卫 / CONFIRM_REJECT_MAX 有界防线(在册一致面,报告 §3.3——失败治理出口,非决策闸);建档缺失 fail(「候选-卡区」,坐标单一真相源,一致面);策略侧 `decide_partner` 的 idx=0 缺省实现与「OCR 未就绪」告示(策略域,strategy-docs/13_pick_family.md §1 E6 在册,T-8 稿同口径不扩);兄弟屏同族面(→ §2.2,归口 T-37);报告 §4 无法核对面(实机验证归运行期)。

### F-2 chosen_partner 写时点:正本两说 + 同族分裂(中)

- **现状症状**:代码现值 = 首轮决策**派发前**写(选择点,值 = 意图,确认点击未发生;写点 = act 内 `write_logic(gs.chosen_partner, …)`,与巨星 `chosen_megastar` 派发前写同款)。正本两说:op-layer.md §1.1 重入裁决条括注「chosen_* 类落地记录在此刻写(……巨星/伙伴/祈愿/星徽等维持……)」与 fields.md §3.4 导语「其余屏 = **重入裁决点单次**逻辑写入」都把伙伴绑在重入裁决点;op-layer.md §2.2 又并列「重入裁决点/**选择点**」二元判定点。同族行为分裂:祈愿按重入裁决点写且有行为锁(sr-od-test `test_cw_screen_two_node_family.py::test_wish_chosen_written_at_reentry_adjudication_only`,明锁「落地前写 = 幻影 chosen = 红」),伙伴/巨星按选择点写(megastar.md §2「派发前写」)。partner.md §6 as-built(「选择点直写、确认前」)与代码一致,但未把该两说申报为裁定,字段级正本 fields.md 现文字与代码不符。
- **根因归层**:**约定层(正本间表述两说)**——代码行为有 op-layer.md §2.2 判定点二元背书(报告 F-3 同判),差距面 = 正本表述,非行为违例。
- **解决到哪**:三处正本收敛为「判定点二元 + 逐屏在册申报」——fields.md §3.4 导语尾句按屏分列(伙伴 = 选择点)、op-layer.md §1.1 括注按屏分列、partner.md §6 补判定点在册指针与写点理由(§2.3 给目标文本)。零行为变更。
- **明确不解决**:伙伴写时点行为本身(不改写时点);祈愿/星徽写时点(各屏审查辖,祈愿行为锁在册);`kernel/cw_screen_report/partner.py` 模块头「留守选择点」申报(已与目标口径一致,不动);chosen 不进 report 的动作事实边界辖域(一致面)。

### F-3 fields.md §3.4.5 伙伴缺口登记滞后于现状(中)

- **现状症状**:fields.md §3.4.5 伙伴子句现文「伙伴=候选阵营与立绘(**暂无候选建档区域**——接线前先补档)」与现状不符——建档「候选-卡区」已在档(`assets/game_data/screen_info/currency_war_partner.yml`,点击带锚定用),SIFT 真身识别已接线;剩余识别几何(候选标签行 y/x 过滤带 = `CwScreenPartner.LABEL_CY_LO/HI`、`LABEL_CX_LO/HI` ClassVar;立绘裁剪框 = `_identify_portraits` 类内几何)仍为**代码内矩形**——未进 screen_info,也未按遭遇屏先例(fields.md §3.4.1「遭遇屏建档无剩余次数区域——现役走代码内矩形先例」)申报。partner.md §3 把 y/x 带写成本稿原数值(「y 带 340-400 ∧ x 带 450-1550」),既违「数值 / 权重 / 阈值只写常量名(单一源在代码)」(AGENTS §9 as-built 条款),也未挂缺口指针。
- **根因归层**:**约定层(字段正本缺口登记滞后)**——AGENTS §5 坐标单一真相源要求识别几何最终归 yml,现状与正字登记之间的候批欠账未立。
- **解决到哪**:fields.md §3.4.5 伙伴子句改「先例申报」口径;partner.md §3 带值改常量名 + 挂先例与缺口指针(§2.4)。零行为变更。
- **明确不解决**:实际补档(候选标签行 / 立绘裁剪框 area 化)归运行期建档流程(实机归档帧 + 观察读链对账,MCP upsert 改资产),本稿只正字正本登记;sim 腿(sim 无伙伴画面段,模块头申报)不动。

### F-4 kernel/cw_events.py 伙伴段注释陈旧 + idx 缺坐标系数定义(低)

- **现状症状**:三处——①段头注「✅ 已派发 cw_screen_partner;⚠️ 候选只立绘 char_id=label→多 idx0,真接需 **SIFT 立绘**」:SIFT 已接入(`cw_screen_partner.py::_identify_portraits`),「真接需」与现状矛盾,「多 idx0」缺省语义已归策略侧;②`PartnerOption.char_id` docstring「空 = OCR 未就绪 → 默认 idx=0 = 今天盲点 stage 立绘」同款过时,且缺省选卡语义单一源在策略器(E6 规格),docstring 未指;③`PartnerOption.idx` 无 [索引定义] 注释(AGENTS §8 索引字段条款须坐标系 + 取值时机;`CwScreenPartnerObs.options`、cw_vocab 各 Pick 已同款在册),`PartnerPick` 已被 `cw_vocab.CwActionPickPartnerParam` 替代(cw_vocab 该类 docstring 在册)、现役仅 `EVENT_PICK_TYPES` 登记在场零生产零消费,而其 docstring 仍申报「decide_partner 返回」——死类型挂活跃语义,注释与现状不符。
- **根因归层**:**约定层(注释纪律滞后)**——SIFT 接线后词级维护未跟。
- **解决到哪**:三站点词级改写(§2.5;`PartnerPick` = 退役/替代申报 + 登记语义注——该类型已被 `cw_vocab.CwActionPickPartnerParam` 替代(cw_vocab 该类 docstring 在册)且零生产零消费(仅 `EVENT_PICK_TYPES` 登记在场),不给死类型挂活跃消费指针)。零行为变更。
- **明确不解决**:`strategies/impl/flow.py::decide_partner` docstring 的「OCR 未就绪…随阶段5」告示(报告未点名,策略域,T-8 稿同口径);`/§11.3.4⑦` 类旧指针仅在被改写的 docstring 内随之清除,不逐站点考古。

### F-5 变更前缀残留与死符号指针:四处(低)

- **现状症状**:①`cw_screen_partner.py` 模块头独立注释「# r104(2026-08-20):SIFT 立绘识别接入……」;②act 内 chosen 写块注释「# **r358d**(遥测接线)……终态契约 §B:session 份退役……」(「终态契约 §B」为会话局部指);③`cw_overlay_pick_action.py::CwActionPickPartnerOp.run` 内「# bug#1 吞……(2026-08-06 **r6** stall;手动 click 即关)」;④act 派发段前注「# 「点选候选 → 确认」脉冲链经工厂(**统一动作工厂批4**:体迁 ``cw_overlay_pick_action.PartnerPickOp``,方法级替身缝保留)」——批名变更史残留 + 死符号指针(`cw_overlay_pick_action.py` 现类 = `CwActionPickPartnerOp`,无 `PartnerPickOp`;派发 = `action_op_for` 注册表直派,「方法级替身缝」已不存)。AGENTS §8 变更条款:前缀只留机制语义,批号/日期清;注释与现状一致。
- **根因归层**:**约定层(注释纪律残留)**。
- **解决到哪**:四站点词级清除(§2.6;站点②与站点④在 §2.1 施工面一并落)。零行为变更。
- **明确不解决**:模块头「机制更正(2026-09-15 实机事故,详见 docs/game/screens/currency_war_choose_partner.md)」注(报告 §3 检查⑧明判 = 当前值成立理由 + 持久指针,符合条款,不动);「bug#1」标签(跨文件在册交互陷阱标签,非会话局部,保留)。

### F-6 partner.md §4 上报列两相词汇残留(低)

- **现状症状**:上报列「零写族单相:确认点击发出后即**全相**,**发射相**意图遥测……」——「全相/发射相」为分相实现旧词;现役 `kernel/cw_action_report/zero_writes.py::report_action_pick_partner_param` = 三行委托回执(`LogicOutcome(applied=True)`,调用侧弃值),无独立发射相写面;action_ops.md §1 增补 2 已立「单相全域在册、两相词汇禁回潮」。
- **根因归层**:**约定层(文档措辞滞后)**。
- **解决到哪**:上报列词级改写(§2.7)。零行为变更。
- **明确不解决**:`zero_writes.py` 本体与命名完备锁(一致面,报告检查面无发现)。

### 在册核对结论

报告 §3 一致面本稿全部不回退:容器槽零参读(`_require_slot_options` 离屏 None = ValueError 观察层失约契约)、无候选 / 建档缺失两显式失败路径(文案沿用)、CONFIRM_REJECT_MAX 失败治理出口、观察上报四锁(`test_cw_screen_two_node_family.py` 观察 / 门锁 + `test_cw_screen_report_ports.py` 四锁 + `test_cw_action_report_contract.py` 词表遍历)、选选流序两行为锁(`test_cw_partner_select_confirm_flow.py`)、外环 fail 重派网(`test_cw_loop_op_fail_redispatch_cap.py`,桩面驱动不触真类)。

## 2. 方案

### 2.1 F-1 修法:决策出口三守卫(零盲发,删兜底)

**代码面**(`cw_screen_partner.py::CwScreenPartner.act`):

1. 模块级 import 提升:现 act 派发段函数内局部 `from …kernel.cw_vocab import CwActionPickPartnerParam` 提升为模块级(守卫②需要类型可见;kernel 层零环,本模块已模块级 import `kernel.cw_events` 同款;先例 = `cw_overlay_pick_action.py` 模块头)。提升后派发段同名局部 import 删除;`action_op_for` / `OverlayPickExecEnv` 两处局部 import 维持现款(仅守卫需要者提升)。
2. 首轮决策块(`if self._pick_point is None:` 内)重写为守卫序列(目标文本):

```python
cands = self._cands
options = self._obs.options if self._obs is not None else []
match = self.ctx.cw_match
# 守卫①(决策输入,op-layer §1.1 出口③ 零盲发,两臂均零点击零派发):
# 候选空 = 在册显式失败上移至决策前;match 缺席 = 局外语境无策略器
# 可问,决策面无兜底(原常量 idx0 盲选派发退役)。
if not options:
    return self.round_fail('伙伴屏无候选(OCR 未命中候选标签),禁兜底盲点')
if match is None:
    return self.round_fail(
        '[cw-partner] 决策无有效输出零盲发(match=None,局外语境)')
# 守卫②(返回契约,op-layer §1.3):None/词表外 = 策略器 bug 具名
# fail 留证(原 AttributeError 异常出口子径收编,消息含原值)。
pick = match.strategy.decide_partner()
if not isinstance(pick, CwActionPickPartnerParam):
    return self.round_fail(
        f'decide_partner 决策无有效输出(词表外/None): {pick!r}')
# 守卫③(值域,op-layer §1.3 守卫断言):越界 = 恒炸,禁钳位。
# 界 = len(cands)(点击目标数组;options 与 cands 恒等长——obs options
# 由 cands enumerate 生成,observe/_identify_portraits 三分支恒返
# len==len(cands))。
if not (0 <= pick.idx < len(cands)):
    raise AssertionError(
        f'[cw-partner] pick idx 越界(策略器 bug,禁钳位): '
        f'idx={pick.idx} len(cands)={len(cands)} pick={pick!r}')
self._pick_idx = pick.idx
log.info('[cw-partner] candidates=%s pick=idx%s %s',
         [o.char_id for o in options], pick.idx, pick.reason)
# 伙伴选择落容器 chosen_partner(gs 单一源,session 域无此写端;守卫
# ①③已保证 options 非空且 idx 在界;点选前写 = 选择点,单次逻辑写入
# 豁免面,与巨星 chosen_megastar 派发前写同款;fields.md §3.4 导语
# 判定点在册)。
if getattr(match, 'gs', None) is not None:
    from sr_od.application.currency_war.kernel.cw_game_state import ChannelSig
    match.gs.write_logic(
        match.gs.chosen_partner,
        options[self._pick_idx].char_id or '',
        produced_by='CwScreenPartner',
        sig=ChannelSig(family='logic_action',
                       actor='CwScreenPartner', mode='compute'))
point = self._pick_point_for(cands[self._pick_idx])
if point is None:
    return self.round_fail('伙伴屏建档缺失:候选-卡区(禁裸坐标兜底)')
self._pick_point = point
```

3. 删除面:常量 `idx = 0` / `reason = 'no-candidates(fallback)'` / 钳位三元 / `if match is not None and options:` 条件支 / chosen 写端四条件(`if match is not None and options and 0 <= idx < len(options) and getattr(match, 'gs', None) is not None:` → 守卫①③承载后仅剩 gs 判空)/ 块尾 `if not cands or not (0 <= idx < len(cands)): round_fail('伙伴屏无候选…')` 整块(两半分别由守卫①/③承载,失败语义单点化;显式失败语义不回退——仍零点击零盲发,文案沿用)。
4. 保留面:重入裁决顶部 / 确认被拒守卫 / 派发 `action_op_for(CwActionPickPartnerParam(idx=self._pick_idx), self.ctx, _env).execute()` 两轮同形(重入轮无策略调用,守卫③保证决策轮 `_pick_idx == pick.idx`,重建非钳位载体);`self._pick_idx` [索引定义] 注释现款维持。派发段前注**不属保留面**——「统一动作工厂批4:体迁 ``PartnerPickOp``,方法级替身缝保留」含批名变更史 + 死符号指针(现类 = `CwActionPickPartnerOp`,替身缝已随注册表直派消解),随本施工一并改写(§2.6 F-5 站点④)。
5. docstring 同步:模块 docstring 决策动作 node 描述在「确认被拒守卫(……)」后补「+ 决策出口三守卫(输入 / 返回契约 / 值域,op-layer §1.1 出口③ / §1.3)」;act docstring 步 2「首轮决策一次……」后补「守卫①②③(候选空 / match 缺席 = 具名 fail;返回 None·词表外 = 具名 fail 含原值;越界 = AssertionError)先于决策与写端,零点击」。
6. 配套注释面:`observe` docstring 尾「(决策走决策面缺省支,分支原样)」随 F-1 退役 → 「(report 跳写 = 容器写闸,与决策无关;决策面无局外兜底,守卫见 act)」。

**落点语义**(机制方向依据 = `one_dragon/base/operation/operation.py` 实文:仅 RETRY 计 `node_retry_times`、其余状态清零且 FAIL 直落 `op_fail`;节点体在 try/except 内,异常被收口为 `round_retry('异常')` + 留证截图):守卫①②(round_fail)= **直落 op fail 交外循环,零节点预算消耗**(一次即终,非计预算路径);候选空 = 瞬时 OCR 失读由外环 fail 重派网获得新帧自愈、持续失读有界响亮停(`cw_loop.py::CwLoop`,行为锁 = `test_cw_loop_op_fail_redispatch_cap.py`);守卫③(AssertionError)= **经框架节点异常收口**(`round_retry('异常')` + 留证截图)沿 RETRY 计节点预算 node_max_retry_times=10,确定性 bug 每轮必炸、预算内有界响亮终止(耗尽 = op fail)。

**文档面**(`screens/partner.md` as-built):

- §2 形态声明:在「……否则 idx=0,规格 = 13_pick_family.md §1 E6)」后插「;决策出口三守卫:候选空 = 具名 round_fail 零盲发(「伙伴屏无候选」在册文案上移至决策前)、match 缺席 = 具名 round_fail(决策面无局外兜底)、返回 None/词表外 = 具名 round_fail(含原值)、idx 越界 = 守卫断言 AssertionError 禁钳位(op-layer.md §1.1 出口③/§1.3;均在派发前零点击)」。
- §3 观察面尾句:「match/gs 缺席的局外兜底路径跳过,决策走缺省支」→「match/gs 缺席的局外路径跳过 report——report 跳写 = 容器写闸,与决策无关;决策面无局外兜底,无 match = 决策无有效输出走守卫 fail,见 §2」。
- §4 脉冲链步 2 行首插守卫行(候选空 / match 缺席 / 返回词表外·None = round_fail,越界 = AssertionError,均先于决策与写端零点击);步 3 删「无候选……」半句(已上移至步 2 守卫,文案不变),保留「建档缺失……」半句。
- §5 终结表补一行:「| 决策出口守卫(候选空/match 缺席/返回词表外·None/idx 越界) | 守卫 fail(op FAIL) | round_fail(含原值,直落零预算)/ 框架异常路径(留证截图 + node_max_retry_times=10 预算耗尽,守卫③)交回外循环;连续 fail 由外环 fail 重派网兜底(cw_loop.py::CwLoop) |」。
- §8 守卫与防线补两条 + 退役申报:「决策输入守卫:候选空/无 match = 具名 round_fail 零盲发(原「常量 idx0 盲选派发」退役;无候选在册文案保留)」「返回契约与值域守卫:返回 None/词表外 = 具名 round_fail;pick idx 越界 = 守卫断言 AssertionError(原「静默钳 0」退役)」。
- §9 遥测与锁面:测试锁清单补守卫两锁(`test_cw_screen_two_node_family.py` 伙伴臂:输入守卫锁 / 返回契约+值域锁)与选选流序锁桩面变更(cw_match 桩)申报。

**测试面**(施工义务,守卫落地即红的面必须同批改):

- `test_cw_partner_select_confirm_flow.py::_make_watched_op`:现款 `monkeypatch.setattr(test_context, 'cw_match', None)`(文件头注自述「cw_match=None(idx0 兜底,决策质量不在锁范围)」)正踩守卫① match 缺席臂——改为 match 桩:`SimpleNamespace(strategy=SimpleNamespace(decide_partner=lambda: CwActionPickPartnerParam(idx=0, reason='stub')))`(真词表类型,守卫②同款);桩无 `gs` 属性 → chosen 写端经 `getattr(match, 'gs', None)` 跳过,两锁零容器断言不受影响。文件头注该半句改「cw_match 桩(decide_partner 恒 idx=0;决策质量不在锁范围,守卫面锁 = test_cw_screen_two_node_family 伙伴臂)」。**两条锁断言面不变**(idx=0 桩 → 首候选点位;点位几何断言与候选带矩形同源,与 idx 数值无关;点位稳定性断言与 idx 无关)——桩面随行为语义同步,非放宽断言。
- `test_cw_screen_two_node_family.py` 伙伴臂补两锁(装配同 `_OBS_ROWS['partner']` 读链桩两元 + 门桩放行 + `action_op_for` 派发捕获桩,同文件装备 / 祈愿锁同款;fail 臂经 `_run_node(test_context, op, op.act)` 断言 round_fail,越界臂经 `op.act()` 直调 + `pytest.raises(AssertionError)`):
  - 锁①输入守卫:空候选臂(`_read_candidates` 桩改返 [])与 match 缺席臂(`cw_match=None` + 读链桩两元)→ round_fail、派发桩零调用(两臂合一锁)。
  - 锁②返回契约 + 值域:None/异型臂(`decide_partner=lambda: SimpleNamespace(idx=0)`)→ round_fail 含「词表外」;越界臂(`_make_match(session, decide_partner=lambda: CwActionPickPartnerParam(idx=5, reason='stub'))`,候选两元)→ AssertionError、零派发。
- 冲突核查:伙伴现役锁面 = 观察 / 门锁(`_OBS_ROWS` / `_GATE_ROWS`,不触 act 决策)+ 选选两行为锁(桩面已列)+ pick op 直驱锁(`test_cw_unified_action_4.py`,env 桩驱动不触画面 op 守卫)+ 外环重派锁(`_ScriptedOp` 桩)——除已列桩面外零波及。

**关键取舍**:

1. **守卫①拆两臂保在册文案**(vs 巨星稿合并单守卫):「伙伴屏无候选」显式失败为审查在册正面面(报告 §3.3),且候选空(瞬时 OCR 失读,重派自愈)与 match 缺席(环境异常)病因与处置不同,分支消息可判读;语义与合并单守卫等价(均 = 输入具名 fail 零盲发),族级对账按同义处理(→ §2.2 归 T-37 裁是否归一拼写)。
2. **守卫②收编 AttributeError 子径**:现款异常出口响亮但消息无策略器语义;具名 fail 含原值留证(巨星稿取舍同款),零诊断损失。
3. **派发保持重建形态**(vs 直发策略产实例):重入轮无策略调用,直发仅首轮可行;守卫③已保证缓存 == 策略产值,重建无值域改写(巨星稿取舍 3 同款;族级对账按「直发 vs 重建 = 屏形态差异,非守卫分歧」记录)。
4. **match 缺席语义变化显式申报**:局外直跑 / MCP 手动由「盲发 idx0」变「fail 零盲发」——正本条款(§1.1 出口③)明文要求;现役伙伴两行为锁正踩该路径,桩面义务已列(与巨星「现役测试无一锁 match-None 路径」不同,伙伴必须同批改桩)。
5. **块尾无候选 fail 删除**(vs 原位保留):守卫①上移后原位判永假,双落点必漂移;失败语义单点化,文案与零盲发语义不变。

### 2.2 F-1 家族联动面:pick 族决策出口家族模式

- **模式认定**:「idx 越界静默钳位 + 决策无有效输出盲选 idx0」——已判同族违规六屏:遭遇(T-4,encounter.md)/ 盛会之星(T-8,megastar.md)/ 选择装备(T-9,equip_pick.md)/ 本屏(T-11)/ 卜者(T-12,报告已出判违规、设计稿在途)/ 祈愿(T-13,报告已出判违规「盲选 idx0 回退 + 静默钳位 + 吞策略响亮失败」、设计稿在途);跨稿记法不一(T-8 修订版记 6 件 / T-12 自述第 4 件)——**成员清单与计数为成稿时点快照,族级全集与计数以 T-37 汇总时最新报告 / 设计稿目录为准**(megastar.md 修订版 §2.2 同款免责),本稿不以任一计数为对账基线。同结构已核销成员:银狼(T-10,报告 §3 明判无此结构——`CARD_AREAS[idx]` 直接异常响亮)、投资两屏(T-6/T-7,isinstance + 值域 round_fail 在册)、补给(T-5,机械兜底点守卫在册)。
- **族级统一修法**(与三稿同构,本稿 §2.1 已落):①决策输入守卫(空候选 / 无策略器 = 具名 fail 零盲发;屏内在册特形出口以正本申报为准——遭遇「空候选 = 零点击终结交回重读」、本稿「伙伴屏无候选」文案沿用);②返回契约守卫(None / 词表外 = 具名 fail 含原值);③值域守卫(idx 越界 = 守卫断言恒炸,禁钳位);④删全部默认 idx / 钳位句 / 兜底支;⑤守卫均在派发前零点击;⑥**不建共享守卫函数**(各屏词表类型 / 界源 / 日志 tag 不同,内联 2-3 行,先例 = encounter.md §2.1)。
- **已知兄弟屏清单**:遭遇 = 本目录 encounter.md(T-4,对抗触顶待裁决)/ 盛会之星 = megastar.md(T-8,修订版)/ 选择装备 = equip_pick.md(T-9,修订版)/ 卜者、祈愿 = 报告已出、设计稿在途(T-12/T-13)/ 本屏 = partner.md(T-11)/ 银狼 = T-10 报告明判合规(非同族成员,清单列已核销);在途 = 星徽(T-14)/ 专家邀请函(T-15)/ 武装箱(T-16)审查未出,同族可能扩员——清单为快照,全集归 T-37。
- **归口 T-37 裁决面**:①是否合并为一次族级实施批(统一守卫形态 / 共享测试锁模板 / 一次对抗;各稿独立可实施,合并时以统一口径为准);②守卫①拼写归一(巨星合并单守卫 vs 本稿两臂保在册文案,语义等价);③共享面 `cw_overlay_pick_action.py::OverlayPickExecEnv.idx` 字段注释「(钳位后生效值)」陈旧措辞随族级批一次改净(equip_pick.md §2.2 已挂同一面,本稿同挂不独立改——伙伴派发同用该 env 字段,单屏改必致共享注与未修屏临时不一致);④op-layer.md §1.3 守卫在册登记 = **无条件默认动作,非开放裁决**:本稿落地批正本更新阶段必登记本屏三条守卫出口(输入 / 返回契约 / 值域)入 §1.3 守卫清单(现文仅 `guard_proposal_vs_expected` 单例枚举;先例 = equip_pick.md §2.2 归口② 同款)——T-37 仅裁族级合并实施时是否把逐屏条目改写为族级统一条目,不存在无人登记路径(§2.8 正本文档行已列落点)。

### 2.3 F-2 修法:写时点正本收敛为判定点二元逐屏分列(零行为变更)

1. `game_state/fields.md` §3.4 导语尾句——替换锚 = 实文「其余屏 = 重入裁决点单次↵逻辑写入;观察覆盖负责画面态,chosen 负责选择事实)」(↵ = 原文换行位,在「单次」之后;「单次」属「重入裁决点单次逻辑写入」短语本体,与前半遭遇括注的「单次消费」是两个词),替换为「盛会之星/伙伴 = **选择点**单次逻辑写入(决策动作 node 派发前写,各屏文档 §6 在册:megastar.md/partner.md;写点 → 点选→确认窗口内无流程读者,确认未落地由重入裁决与显式失败出口治理)、祈愿试炼/星徽秘典等其余屏 = 重入裁决点单次逻辑写入;观察覆盖负责画面态,chosen 负责选择事实)」。**「单次」保留声明**:目标句沿用实文与 T-8 目标句同款「单次逻辑写入」措辞,两候选句在「单次」上同向。**跨稿接缝(三方同句,fields.md §3.4 导语「其余屏 = 重入裁决点单次逻辑写入」全文件唯一句)**:①T-8 = megastar.md §2.4——改写判定点枚举半边(其「其余屏随判定点走单次逻辑写入(判定点二元 = screens/op-layer.md §2.2):盛会之星 = 选择点(…)、其余屏 = 重入裁决点」半句仍与伙伴冲突,差异面 = 指针形态:本句 = 逐屏文档指针,T-8 = 判定点二元指针);②T-9 = equip_pick.md §2.3 fields.md 头注条——对同句**追加例外括注**(「装备三选一/骇入策划无 chosen_* 写端,效果 = 动作侧即时单相写,见 §3.4.5/§4」;缺此括注则本句「祈愿试炼/星徽秘典**等**其余屏」把两无写端屏涵括为重入裁决点 chosen 写屏,与 fields.md §3.4.5/§4 同批改写正面矛盾);③T-11 = 本句(盛会之星/伙伴两选择点)。**合并落行 = 本稿骨架句 + T-9 例外括注(挂接「祈愿试炼/星徽秘典等其余屏」半句)的合并句,文本归 T-37 对账**——三稿各自均无完整三方视图,禁以任一单边「合并落行」为基线执行。
2. `screens/op-layer.md` §1.1 重入裁决条括注「(见 §2 动作事实边界;巨星/伙伴/祈愿/星徽等维持,投资两屏已改动作执行时经获得链记,遭遇已改动作侧发射即写,补给确认即写留守选卡分支)」→「(见 §2 动作事实边界;巨星/伙伴 = 选择点维持(派发前写,各屏文档 §6 在册)、祈愿/星徽等 = 重入裁决点维持,投资两屏已改动作执行时经获得链记,遭遇已改动作侧发射即写,补给确认即写留守选卡分支)」。**认领申报**:该括注含巨星半——T-8 稿修法面未含 op-layer.md(其 §2.7 文件面无该文件),本稿认领整句改写避免残段无人施工;与 megastar.md §6 / fields.md 改写同向,归 T-37 对账。
3. `screens/partner.md` §6 chosen 行「- `chosen_partner` write_logic(选择点直写、确认前;session 份退役,gs 单一源;单次逻辑写入豁免)。」→「- `chosen_partner` write_logic(**选择点**直写、确认前 = 判定点二元之选择点(fields.md §3.4 导语在册);写点 → 点选→确认窗口内无流程读者,确认未落地 = 重入裁决不写成功 + CONFIRM_REJECT_MAX 显式失败出口 + 外环重派重写,无幻影成功消费面;gs 单一源,session 域无此写端;单次逻辑写入豁免)。」

**关键取舍**:收敛文本不改行为(备选「把伙伴写时点改到重入裁决点对齐 fields.md 现文」放弃——行为变更(chosen 可信窗后移)+ 与巨星两屏在册 as-built 分裂 + 需重接现役写端语义,收益仅「少改两行文档」;祈愿行为锁明锁重入裁决点,统一到任一侧都是行为变更出范围)。判定点二元权威 = op-layer.md §2.2「记账随判定点走(重入裁决点/选择点)」。

### 2.4 F-3 修法:缺口登记正字(零行为变更)

1. `game_state/fields.md` §3.4.5 伙伴子句「伙伴=候选阵营与立绘(**暂无候选建档区域**——接线前先补档)」→「伙伴=候选阵营与立绘(点击带 = 建档「候选-卡区」在档,锚定选中点 y;候选标签行 y/x 过滤带与立绘裁剪框 = 现役代码内矩形先例——同遭遇屏 §3.4.1 先例申报;SIFT 真身识别已接线;标签行 / 裁剪框 area 化补档候批、不阻接线)」。依据:currency_war_partner.yml「候选-卡区」在档;`cw_screen_partner.py` LABEL_* ClassVar 与 `_identify_portraits` 裁剪几何;fields.md §3.4.1 先例句;AGENTS §5 坐标单一真相源(现状与 yml 归一的候批欠账以此立账)。
2. `screens/partner.md` §3 两处:①候选读链行「label 行 y 带 340-400 ∧ x 带 450-1550」→「label 行 y 带 = `CwScreenPartner.LABEL_CY_LO/HI`、x 带 = `LABEL_CX_LO/HI`(数值单一源在代码;识别几何现役走代码内矩形先例 = fields.md §3.4.5,标签行 / 立绘裁剪框 area 化补档候批)」(「必须滤 x」半句与排除表申报不变);②立绘真身行「(label 上方立绘区 vs portrait_plaza 模板库……)」后补「(裁剪框 = `_identify_portraits` 类内几何,数值单一源在代码,同先例申报)」。

**关键取舍**:先例申报立即正字(vs 立即补档)——补档需实机归档帧对账改资产,归运行期建档流程;欠账已按先例句式立账,正本不再与现状矛盾。

### 2.5 F-4 修法:cw_events.py 伙伴段词级改写(零行为变更)

| 站点 | 现文 | 目标文本 |
|---|---|---|
| 段头注 | `# ===== 选择伙伴节点(decide_partner;✅ 已派发 cw_screen_partner;⚠️ 候选只立绘 char_id=label→多 idx0,真接需 SIFT 立绘)=====` | `# ===== 选择伙伴节点(decide_partner;宿主 = operations/cw_screen/cw_screen_partner.py;候选真身 = SIFT 立绘识别,识别失败回落 label 流派名)=====` |
| `PartnerOption` docstring | `"""一个伙伴候选(OCR/SIFT 读角色名,``read_partner`` 阶段5;/§11.3.4⑦)。`<br><br>`char_id:候选角色名(空 = OCR 未就绪 → 默认 idx=0 = 今天盲点 stage 立绘)。`<br>`"""` | `"""一个伙伴候选(角色名 = SIFT 真身识别产物,识别失败回落 label 流派名;`<br>`生产读端 = 画面 op 观察 node 一次读,cw_screen_partner.py::observe)。`<br><br>`[索引定义] idx:坐标系 = 画面物理候选位序(左→右)0 基,与`<br>` ``CwScreenPartnerObs.options``/容器 ``partner_opts`` 槽同一候选列表;`<br>` 取值时机 = 观察 node 入口帧一次读快照,访问内恒稳。`<br>`char_id:候选角色名(空 = 识别未命中回落失败/读缺);缺省选卡语义`<br>`单一源 = 策略器 ``decide_partner``(strategy-docs/13_pick_family.md §1 E6)。`<br>`"""` |
| `PartnerPick` docstring | `"""decide_partner 返回:选第几个候选 + 原因。"""` | `"""kernel 时代伙伴选卡返回载体,已被 ``cw_vocab.CwActionPickPartnerParam```<br>`替代(替代关系在册 = cw_vocab 该类 docstring);现役仅 ``EVENT_PICK_TYPES```<br>`登记在场(登记面,零生产零消费)。`<br><br>`[索引定义] idx:历史语义 = 候选列表下标 0 基(登记面保留,现役零消费)。`<br>`"""` |

依据:SIFT 接线现款(`_identify_portraits` 三分支);E6 规格在册(13_pick_family.md §1 决策表 E6 行);[索引定义] 同款先例(`cw_screen_report/partner.py::CwScreenPartnerObs` docstring、cw_vocab 各 Pick 字段注);AGENTS §8 索引字段条款(坐标系 + 取值时机,防线字段注明消费端)。

### 2.6 F-5 修法:变更前缀与死符号指针清除(零行为变更)

| 站点 | 现文 | 目标文本 |
|---|---|---|
| `cw_screen_partner.py` 模块头独立注 | `# r104(2026-08-20):SIFT 立绘识别接入(portrait_plaza 库)——候选真身喂 decide_partner,`<br>`# core_chars 匹配真正生效(此前 label 流派名恒不命中 → 恒 idx=0 最左盲点)。` | **整块删除**——现值语义已由模块 docstring「候选观察一次读(OCR + SIFT 立绘识别真身,失败回落 label 名)」与 `_identify_portraits` docstring「真身识别让 decide_partner 的 core_chars 匹配真正生效」承载,无信息丢失 |
| act 内 chosen 写块注 | `# r358d(遥测接线):伙伴选择落容器(chosen_partner,gs 单一源`<br>`# ——终态契约 §B:session 份退役;点选前写——决策半派发前,`<br>`# 单次逻辑写入豁免面,与巨星 chosen_megastar 派发前写同款)。` | 已在 §2.1 守卫改写目标代码内一并落(前缀 r358d 与会话局部指「终态契约 §B」清除,机制语义与 fields.md §3.4 指针保留),无独立施工面 |
| `cw_overlay_pick_action.py::CwActionPickPartnerOp.run` 内注 | `# bug#1 吞(before_screenshot 移光标)→ overlay 不关 flat-loop(2026-08-06 r6 stall;手动 click 即关)。` | `# bug#1 吞(before_screenshot 移光标)→ overlay 不关 flat-loop stall;mouse_move+click 手动点击即关。`(bug#1 = 跨文件在册交互陷阱标签,保留) |
| `cw_screen_partner.py` act 派发段前注 | `# 「点选候选 → 确认」脉冲链经工厂(统一动作工厂批4:体迁`<br>`# ``cw_overlay_pick_action.PartnerPickOp``,方法级替身缝保留)。` | `# 「点选候选 → 确认」脉冲链经注册表工厂派发(``cw_overlay_pick_action.py::`<br>`# CwActionPickPartnerOp``,机械链 + 自上报在动作 op 内)。`(去批名变更史、死符号 `PartnerPickOp` 改现类、删「方法级替身缝」半句;随 §2.1 施工面一并落) |

依据:AGENTS §8 变更条款(前缀只留机制语义);模块头「机制更正」注报告明判符合条款不动(§1 F-5 明确不解决)。

### 2.7 F-6 修法:上报列两相词汇清除(零行为变更)

`screens/partner.md` §4 动作上报列「自上报 `report_action_pick_partner_param`(零写族单相:确认点击发出后即全相,发射相意图遥测,容器零写等观察覆盖;确认点读缺 retry 旁路未发确认点击,不上报)」→「自上报 `report_action_pick_partner_param`(零写族单相:确认点击发出后即按完整结果上报回执,容器零写、真值归观察覆盖;确认点读缺 retry 旁路未发确认点击,不上报)」。依据:action_ops.md §1 增补 2(单相全域在册、两相词汇禁回潮);`zero_writes.py::report_action_pick_partner_param` 现役 = 回执(applied=True,调用侧弃值),无独立发射相写面。

### 2.8 实施文件面全集

- **行为变更(仅 F-1)**:`cw_screen_partner.py`(守卫 / 删兜底 / 注释 / docstring);`sr-od-test/…/test_cw_partner_select_confirm_flow.py`(桩面 cw_match 桩 + 头注半句);`sr-od-test/…/test_cw_screen_two_node_family.py`(伙伴臂补两锁)。
- **代码内文档(零行为)**:`kernel/cw_events.py`(F-4 三站点);`cw_overlay_pick_action.py::CwActionPickPartnerOp` 类体内注(F-5 站点③;`cw_screen_partner.py` 注释面随 F-1 同文件施工,含 F-5 站点②④)。
- **正本文档(零行为)**:`game_state/fields.md`(§3.4 导语 F-2 + §3.4.5 F-3);`screens/op-layer.md`(§1.1 括注 F-2 + §1.3 守卫出口登记 F-1,落地批正本更新阶段无条件执行 = §2.2 ④);`screens/partner.md`(§2/§3/§4/§5/§6/§8/§9:F-1 as-built + F-3 §3 + F-6 §4 + F-2 §6)。
- **跨稿共享面(本稿不独立施工)**:fields.md §3.4 导语为**三方同句认领**(T-8 = megastar.md §2.4 枚举半边 / T-9 = equip_pick.md §2.3 例外括注 / T-11 = 本稿骨架句,详 = §2.3 ①)——合并落行 = 含 T-9 例外括注并入后的合并句,文本归 T-37 对账;`OverlayPickExecEnv.idx` 字段注释「(钳位后生效值)」挂 T-37 族级批(§2.2 ③);`cw_overlay_pick_action.py` 模块头段归 encounter.md §2.3(T-37 在册),本稿只动 PickPartnerOp 类体内注。
- **其余文件零触碰**:策略侧(`flow.py::decide_partner` 告示不扩)、祈愿 / 星徽写时点、sim 腿、`zero_writes.py` 本体、建档资产(yml)。

## 3. 新规范增补(2026-09-22 两条款)

> **增补依据**:`.debug/progress/2026-09-22-cw-screen-review/reports/respec-T9-T15.md` §2.3(T-11)与 §2.8(跨屏共性);两条款原文 = `screens/op-layer.md` §1.1 :34「观察标准化门」/ :36「画面 op 不支持局外单独调用」(commit 2f35d4011,用户裁定 2026-09-22)。两条款入正本晚于本稿对抗收敛(时序性缺口),本节 = 在已收敛三守卫修法主体上的增补申报与连带改写,不推翻主体。本节只增补,不改 §1/§2 既有正文——既有目标文本需连带改写的,逐字给出改写文本与落点节号,由落地批按本节执行。
>
> **轨迹注(r2 复攻后定点修订)**:respec-attack-AB-r2(`.debug/progress/2026-09-22-cw-screen-review/reviews/respec-attack-AB-r2.md`)判 11 条全部落位、残留 3 条(低 3):本稿 2 条 = ①3.1-j「现」引语含加粗记号(§1 :15 实文无加粗,引语失真);②3.2-a 落地文本退役引注含「fail 零盲发」,§3.2 验收锚(取舍 4 语境)限定「§0-§2 正文」后仍字面打红。同根余 1 条在 fortune 3.1-f,由 fortune 稿同批修订。本节处置:3.1-j 引语按 :15 实文去加粗(改文同基线不加粗);3.2-a 退役引注改转述形态(见该落点注)。§0 状态行维持,以本注登记轨迹。

### 3.1 增补①(:36 条款):守卫① match 缺席臂 round_fail → round_success 终结交回

**依据**:op-layer.md §1.1 :36 明文「无 match(局外)= 零决策零点击 round_success 终结交回(遭遇屏在册先例同款),不设任何兜底决策路径」;先例代码 = `operations/cw_screen/cw_screen_encounter.py::CwScreenEncounter.act`(`match is None or not options…` → `return self.round_success('候选读缺/局外,零点击终结交回重读', wait=1.5)`,报告锚 :156-165,实查在册)。§2.1 目标代码该臂 = `round_fail('[cw-partner] 决策无有效输出零盲发(match=None,局外语境)')`——零决策零点击 ✓,出口 = fail ≠ :36 明文的 round_success,须改写(报告 §2.3 增补 A)。**两臂分形申报**:候选空(对局内 OCR 失读)不受 :36 辖,留守 round_fail(在册正面面,原报告 §3.3);match 缺席(局外)按 :36 改 round_success——守卫①拆分后自增两臂(候选空臂 fail / match-None 臂 success),非合并单臂;遭遇屏先例为「match-None ∨ 空候选」合并臂形态,本屏不回归先例合并形,出口语义逐臂对齐条款。

**落点 3.1-a = §2.1 代码面目标代码块守卫①段(局部替换,逐字)**。现目标文本:

```python
# 守卫①(决策输入,op-layer §1.1 出口③ 零盲发,两臂均零点击零派发):
# 候选空 = 在册显式失败上移至决策前;match 缺席 = 局外语境无策略器
# 可问,决策面无兜底(原常量 idx0 盲选派发退役)。
if not options:
    return self.round_fail('伙伴屏无候选(OCR 未命中候选标签),禁兜底盲点')
if match is None:
    return self.round_fail(
        '[cw-partner] 决策无有效输出零盲发(match=None,局外语境)')
```

改写后目标文本:

```python
# 守卫①(决策输入,两臂零点击零派发):候选空 = 在册显式失败(留守
# round_fail);match 缺席 = 局外,零决策零点击 round_success 终结
# 交回(op-layer.md §1.1 :36,遭遇屏先例同款;原常量 idx0 盲选派发退役)。
if not options:
    return self.round_fail('伙伴屏无候选(OCR 未命中候选标签),禁兜底盲点')
if match is None:
    return self.round_success(
        '[cw-partner] 局外无 match,零决策零点击终结交回(:36)')
```

**落点 3.1-b..3.1-i = §2.1 同句族连带改写(逐字;3.1-a 为报告增补 A 点名面,以下为同一出口语义申报句族的完备化,同判改写,防落地批按未改句施工出内矛盾)**:

- **3.1-b** §2.1 代码面条目 5(docstring 同步):act docstring 补句现「守卫①②③(候选空 / match 缺席 = 具名 fail;返回 None·词表外 = 具名 fail 含原值;越界 = AssertionError)先于决策与写端,零点击」→ 改「守卫①②③(候选空 = 具名 fail;match 缺席 = 零决策零点击 round_success 终结交回,op-layer.md §1.1 :36;返回 None·词表外 = 具名 fail 含原值;越界 = AssertionError)先于决策与写端,零点击」;同条模块 docstring 补句现「+ 决策出口三守卫(输入 / 返回契约 / 值域,op-layer §1.1 出口③ / §1.3)」→ 改「+ 决策出口三守卫(输入:候选空 fail / match 缺席 :36 round_success 交回 / 返回契约 / 值域,op-layer.md §1.1 :36·出口③ / §1.3)」。
- **3.1-c** §2.1 代码面条目 6(配套注释面):observe docstring 替换文本现「(report 跳写 = 容器写闸,与决策无关;决策面无局外兜底,守卫见 act)」→ 改「(report 跳写 = 容器写闸,与决策无关;决策面无局外兜底——无 match = 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36),守卫见 act)」。
- **3.1-d** §2.1 落点语义段(整段改写,逐字)。现文:「守卫①②(round_fail)= **直落 op fail 交外循环,零节点预算消耗**(一次即终,非计预算路径);候选空 = 瞬时 OCR 失读由外环 fail 重派网获得新帧自愈、持续失读有界响亮停(`cw_loop.py::CwLoop`,行为锁 = `test_cw_loop_op_fail_redispatch_cap.py`);守卫③(AssertionError)= **经框架节点异常收口**(`round_retry('异常')` + 留证截图)沿 RETRY 计节点预算 node_max_retry_times=10,确定性 bug 每轮必炸、预算内有界响亮终止(耗尽 = op fail)。」→ 改:「守卫①候选空臂、守卫②(round_fail)= **直落 op fail 交外循环,零节点预算消耗**(一次即终,非计预算路径);候选空 = 瞬时 OCR 失读由外环 fail 重派网获得新帧自愈、持续失读有界响亮停(`cw_loop.py::CwLoop`,行为锁 = `test_cw_loop_op_fail_redispatch_cap.py`);守卫① match 缺席臂(round_success)= 零决策零点击终结交回外循环重分发(op-layer.md §1.1 :36,零预算消费);守卫③(AssertionError)= **经框架节点异常收口**(`round_retry('异常')` + 留证截图)沿 RETRY 计节点预算 node_max_retry_times=10,确定性 bug 每轮必炸、预算内有界响亮终止(耗尽 = op fail)。」(段首括注「机制方向依据 = …」半句不动)
- **3.1-e** §2.1 文档面 §2 形态声明插句(改写后全文):「;决策出口三守卫:候选空 = 具名 round_fail 零盲发(「伙伴屏无候选」在册文案上移至决策前)、match 缺席 = 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36,遭遇屏先例同款)、返回 None/词表外 = 具名 round_fail(含原值)、idx 越界 = 守卫断言 AssertionError 禁钳位(op-layer.md §1.1 :36/出口③/§1.3;均在派发前零点击)」(现句「match 缺席 = 具名 round_fail(决策面无局外兜底)」半句与引据「出口③/§1.3」随之废弃)。
- **3.1-f** §2.1 文档面 §3 观察面尾句替换文本:现「match/gs 缺席的局外路径跳过 report——report 跳写 = 容器写闸,与决策无关;决策面无局外兜底,无 match = 决策无有效输出走守卫 fail,见 §2」→ 改「match/gs 缺席的局外路径跳过 report——report 跳写 = 容器写闸,与决策无关;决策面无局外兜底,无 match = 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36),见 §2」。
- **3.1-g** §2.1 文档面 §4 脉冲链步 2 守卫行:现「(候选空 / match 缺席 / 返回词表外·None = round_fail,越界 = AssertionError,均先于决策与写端零点击)」→ 改「(候选空 / 返回词表外·None = round_fail;match 缺席 = round_success 零决策零点击终结交回,op-layer.md §1.1 :36;越界 = AssertionError——均先于决策与写端零点击)」。
- **3.1-h** §2.1 文档面 §5 终结表补行:现一行「| 决策出口守卫(候选空/match 缺席/返回词表外·None/idx 越界) | 守卫 fail(op FAIL) | round_fail(含原值,直落零预算)/ 框架异常路径(留证截图 + node_max_retry_times=10 预算耗尽,守卫③)交回外循环;连续 fail 由外环 fail 重派网兜底(cw_loop.py::CwLoop) |」→ 改两行:「| 决策出口守卫(候选空/返回词表外·None/idx 越界) | 守卫 fail(op FAIL) | round_fail(含原值,直落零预算)/ 框架异常路径(留证截图 + node_max_retry_times=10 预算耗尽,守卫③)交回外循环;连续 fail 由外环 fail 重派网兜底(cw_loop.py::CwLoop) |」「| 局外无 match(op-layer.md §1.1 :36) | round_success 终结交回 | 零决策零点击,交回外循环重分发(遭遇屏先例同款) |」。
- **3.1-i** §2.1 文档面 §8 守卫与防线补条:现「决策输入守卫:候选空/无 match = 具名 round_fail 零盲发(原「常量 idx0 盲选派发」退役;无候选在册文案保留)」→ 改「决策输入守卫:候选空 = 具名 round_fail 零盲发(无候选在册文案保留);局外无 match = 零决策零点击 round_success 终结交回(op-layer.md §1.1 :36,遭遇屏先例同款;原「常量 idx0 盲选派发」退役)」。
- **3.1-j**(§1 F-1「解决到哪」总括句,守卫①拆臂后 §1 stance 与 §2.1 修订面对齐;姊妹稿先例 = fortune 3.2-a/3.2-b、equip_pick.md §3.1 落点 3——stance 句入落点清单;引语按 §1 :15 实文逐字,attack 行文加粗记号不入引语,改文同基线不加粗):现「首轮决策块改三守卫(决策输入具名 fail 零盲发 / 返回契约具名 fail / idx 值域守卫断言恒炸),」→ 改「首轮决策块改三守卫(决策输入守卫(候选空具名 fail / match 缺席 :36 round_success 终结交回) / 返回契约具名 fail / idx 值域守卫断言恒炸),」——该句原「决策输入具名 fail 零盲发」总括与 §3.2 验收锚的语境限定(「取舍 4 语境」)不重合而逃逸检查,落点化后纳入同批改写。

**验收锚**:①§2.1 目标代码中 `if match is None:` 臂返回 round_success 且消息含「零决策零点击终结交回」,位置先于守卫②;候选空臂文本零改动;②3.1-b..3.1-j 落地后 §0-§2 正文 grep「match 缺席 = 具名 round_fail」「决策无有效输出零盲发(match=None」零残留(§3 自身逐字引语区除外——3.1-a 现块引用保留被禁短语,全稿字面 grep 必命中引用区);③遭遇屏先例符号锚(`cw_screen_encounter.py::CwScreenEncounter.act`)在稿可溯。

### 3.2 增补②(:36 条款):取舍 4 与族级修法①引据连带改写

**落点 3.2-a = §2.1 关键取舍 4(整条改写,逐字)**。现文:

> 4. **match 缺席语义变化显式申报**:局外直跑 / MCP 手动由「盲发 idx0」变「fail 零盲发」——正本条款(§1.1 出口③)明文要求;现役伙伴两行为锁正踩该路径,桩面义务已列(与巨星「现役测试无一锁 match-None 路径」不同,伙伴必须同批改桩)。

改写后:

> 4. **match 缺席语义变化显式申报**:局外直跑 / MCP 手动由「盲发 idx0」变「零决策零点击 round_success 终结交回」——正本条款(op-layer.md §1.1 :36)明文要求(原具名 fail 终态与「§1.1 出口③」引据随 :36 改写——match 缺席是局外语境,非「决策无有效输出」);现役伙伴两行为锁正踩该路径,桩面义务已列(与巨星「现役测试无一锁 match-None 路径」不同,伙伴必须同批改桩)。

注(转述形态):3.2-a 退役引注为转述——被禁短语「fail 零盲发」字面不入落地文本,以满足本节验收锚取舍 4 语境零残留;原终态申报逐字见上方现文引语。

**落点 3.2-b = §2.2 族级统一修法①(半句改写,逐字)**。现文:「①决策输入守卫(空候选 / 无策略器 = 具名 fail 零盲发;屏内在册特形出口以正本申报为准——遭遇「空候选 = 零点击终结交回重读」、本稿「伙伴屏无候选」文案沿用);」→ 改「①决策输入守卫(空候选 = 具名 fail 零盲发,留守;无策略器(局外 match 缺席)= 零决策零点击 round_success 终结交回,op-layer.md §1.1 :36;屏内在册特形出口以正本申报为准——遭遇「空候选 = 零点击终结交回重读」、本稿「伙伴屏无候选」文案沿用);」

依据:取舍 4 原引据「§1.1 出口③」错位、终态「fail 零盲发」与 :36 明文相抵;§2.2 ①「无策略器 = fail」半句同判(报告 §2.3 增补 B)。两处均为 :36 前收敛文本的时序性引据错位,同批改写。

**验收锚**:§0-§2 正文 grep「fail 零盲发」(取舍 4 语境)与「无策略器 = 具名 fail」零残留(§3 自身逐字引语区除外——3.2-a 现文引用保留「fail 零盲发」,全稿字面 grep 必命中引用区);取舍 4 出现「op-layer.md §1.1 :36」引据。

### 3.3 增补③(:36 条款):测试锁①拆两臂

**落点 = §2.1 测试面锁①(整条改写,逐字)**。现文:

>   - 锁①输入守卫:空候选臂(`_read_candidates` 桩改返 [])与 match 缺席臂(`cw_match=None` + 读链桩两元)→ round_fail、派发桩零调用(两臂合一锁)。

改写后:

>   - 锁①输入守卫(拆两臂,出口断言分形随 :36):候选空臂(`_read_candidates` 桩改返 [])→ round_fail「伙伴屏无候选」、派发桩零调用;match 缺席臂(`cw_match=None` + 读链桩两元,同 `_run_node` 驱动)→ round_success(消息含「零决策零点击终结交回」)、派发桩零调用零点击——两臂分开断言,禁合并出口断言。

依据:两臂出口语义随 :36 分形(3.1),合一锁会把 match-None 臂错锁成 fail(报告 §2.3 增补 C);`test_cw_partner_select_confirm_flow.py` 桩面(match 桩)不受本增补影响,维持 §2.1 测试面现款。

**验收锚**:锁①含「match 缺席臂 → round_success」与「候选空臂 → round_fail」两组独立断言;锁②(返回契约+值域)文本零改动。

### 3.4 增补④(:34 条款):F-4 失败回落语义挂观察标准化门欠账 + 屏契约边界登记

**依据**:op-layer.md §1.1 :34「任一候选转换失败 = 观察失败:观察 node round_fail 早退、零写零上报」「多候选命中同一注册名(选项互斥屏)= 同判转换失败」「各屏转换成功性的附加边界由屏契约(screens/ 各篇)登记」。本屏对门状态:转换点**已在观察侧 ✓**(`_identify_portraits` SIFT 真身识别 = 观察时转换成角色注册表标准名);动作上报**仅 idx ✓**(`CwActionPickPartnerParam(idx)`,cw_vocab [索引定义] 在册;派发经 `OverlayPickExecEnv(idx=…)`)——主体已合门。唯一不一致 = **失败语义**:SIFT 未命中回落 label 流派名(`out.append(cid if cid else _name)`)、SIFT 整体异常全回落——流派名不在角色注册表 = 非标准名照报,:34 要求转换失败 = 观察失败 round_fail 零写零上报;多候选命中同一注册名(两候选 SIFT 识别为同一角色,伙伴 = 选项互斥屏)同判面亦未登记。§2.5 F-4 目标文本把该失败态申报为合法值语义且无欠账注 = 时序性缺口(报告 §2.3 增补 D)。

**落点 3.4-a = §2.5 F-4 修法表 `PartnerOption` 行目标文本 char_id 句(局部替换,逐字;`<br>` = 原表换行标记,沿用)**。现目标文本(char_id 句起,至 docstring 收尾):

```
`<br>`char_id:候选角色名(空 = 识别未命中回落失败/读缺);缺省选卡语义`<br>`单一源 = 策略器 ``decide_partner``(strategy-docs/13_pick_family.md §1 E6)。`<br>`"""
```

改写后目标文本:

```
`<br>`char_id:候选角色名(空 = 识别未命中回落失败/读缺;识别失败回落`<br>`流派名/空 = op-layer.md §1.1 :34 转换失败欠账形态,收敛方向 = 观察`<br>`失败 round_fail 零写零上报;屏级转换成功性边界由 screens/partner.md`<br>`登记,含多候选同名同判);缺省选卡语义单一源 = 策略器 ``decide_partner```<br>`(strategy-docs/13_pick_family.md §1 E6)。`<br>`"""
```

注:同表段头注「识别失败回落 label 流派名」为机制描述句(非值语义申报),不动;本增补只登记欠账与收敛方向,本批不动观察行为(回落照旧),与 :34「欠账逐批收敛,禁新增未标准化直报」口径一致——本屏回落为现役既有语义,无新增未标准化直报面。

**落点 3.4-b = §2.8 实施文件面全集「正本文档」行(局部扩写,逐字)**。现文:

> - **正本文档(零行为)**:`game_state/fields.md`(§3.4 导语 F-2 + §3.4.5 F-3);`screens/op-layer.md`(§1.1 括注 F-2 + §1.3 守卫出口登记 F-1,落地批正本更新阶段无条件执行 = §2.2 ④);`screens/partner.md`(§2/§3/§4/§5/§6/§8/§9:F-1 as-built + F-3 §3 + F-6 §4 + F-2 §6)。

改写后:

> - **正本文档(零行为)**:`game_state/fields.md`(§3.4 导语 F-2 + §3.4.5 F-3);`screens/op-layer.md`(§1.1 括注 F-2 + §1.3 守卫出口登记 F-1,落地批正本更新阶段无条件执行 = §2.2 ④);`screens/partner.md`(§2/§3/§4/§5/§6/§8/§9:F-1 as-built + F-3 §3 + F-6 §4 + F-2 §6;**+ §3 观察面登记 :34 转换成功性边界(char_id 识别失败回落流派名/空 = 转换失败欠账形态,收敛方向 = 观察失败 round_fail 零写零上报;含多候选命中同一注册名同判)+ §6 chosen 行 char_id 值语义随注——本稿 §3 增补④,op-layer.md §1.1 :34「边界由屏契约登记」义务,落地批无条件执行)**。

**验收锚**:§2.5 `PartnerOption` 目标 docstring 含「:34 转换失败欠账形态」;§2.8 `screens/partner.md` 条目含「§3」登记义务与「多候选同名同判」;:34 三要件(失败早退 / 多候选同判 / 屏契约登记)在稿可溯。

### 3.5 :36 行为改写与族级合并裁决面合流申报(跨屏共性)

- 本屏 :36 行为改写 = 守卫① match 缺席臂改 round_success(一行级出口语义),属 **6 屏同形态改写族**(T-9 选择装备 / T-11 本屏 / T-12 命运卜者 / T-13 祈愿试炼 / T-14 星徽秘典 / T-15 专家邀请函;形态 = 局外支/守卫臂 → 零决策零点击 round_success 终结交回;依据 = respec 报告 §2.8 跨屏共性 2;T-10 为零行为批不在内)。
- 与 §2.2 既有「族级合并实施批」裁决面**合流**:归 T-37 时并入族级实施批一次施工(统一 :36 改写形态 + 共享测试锁模板「无 match → round_success + 零派发」断言);跨稿「收编 vs 保留」分歧(respec §2.1③/§2.6 在册)已被 :36 裁定终结(统一口径 = 零决策零点击 round_success 交回,不存在保留面);§2.2 归口①(实施批合并)与归口②(守卫①拼写归一)维持待裁——归口①实文 = 「是否合并为一次族级实施批」,并无「是否收编」子题,原「归口①的『是否收编』候裁面已被终结」指称失准已改正。
- §2.2 归口④(op-layer.md §1.3 守卫清单登记 = 无条件默认动作)不受 :36 影响,维持;族级批实施时本屏守卫①申报条目按 :36 后口径登记。

### 3.6 T-37 登记行原文(T-37 汇总按行抄录,不改写)

- T-11①(:36):partner.md §2.1 守卫① match 缺席臂 round_fail→round_success(`'[cw-partner] 局外无 match,零决策零点击终结交回(:36)'`),守卫①注释两臂分形连改;§2.1 同句族 8 处连带改写逐字见本稿 §3.1;§1 F-1「解决到哪」stance 句随批改写(3.1-j)。
- T-11②(:36):partner.md §2.1 取舍 4 终态与引据改「零决策零点击 round_success 终结交回——op-layer.md §1.1 :36」;§2.2 族级统一修法①「无策略器」半句同步改。
- T-11③(:36):partner.md §2.1 测试锁①拆两臂——match 缺席臂锁 round_success + 零派发零点击,候选空臂留守 round_fail。
- T-11④(:34):partner.md §2.5 F-4 `PartnerOption` char_id 目标句挂「:34 转换失败欠账形态」注(收敛方向 = 观察失败 round_fail 零写零上报);§2.8 增 screens/partner.md §3/§6 转换成功性边界登记义务(含多候选同名同判)。
- T-11合流::36 行为改写并入 6 屏(T-9/T-11/T-12/T-13/T-14/T-15)族级实施批一次施工,共享测试锁模板;跨稿「收编 vs 保留」分歧(respec §2.1③/§2.6 在册)已由 :36 终结;§2.2 归口①(实施批合并)与归口②(守卫①拼写归一)维持待裁。
