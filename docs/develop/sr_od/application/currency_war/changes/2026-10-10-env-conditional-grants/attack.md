# 环境条件发放 迭代设计·对抗审查报告(第二轮·定点复审)

> 审查对象:本目录 README.md / design.md / landing.md / details/env-conditional-grant.md 当前修订稿。
> 核验基准:第一轮报告(本文件上一版)F1–F11 逐条;代码按符号直查,不依赖文档所写行号。本轮新核验 19 组代码事实,出处逐条内嵌。
> 复审范围:修复核验(逐条对码)+ 修订交互快攻(仅本轮触碰段落)+ 跨文档三方同步(design §2 第 5 条 ↔ details §5 ↔ landing 3.3)。

## 一、结论

**有条件通过(第二轮)——未达定稿**。第一轮 11 项发现中 7 项完全闭合(F1 主体/F3/F4/F5/L1/L2/L4/L5/L6,详见 §二),高危的 F1 结构性修复成立:supply 不采纳回调后「恒惰性腿」消失,深井发放路径 cap 公式经三向追问自洽。但修订只在自己触碰的段落内自洽,**三处中危残留跨出了触碰面**:

- **N1【中】**:F1 修复的旧口径三处残留——design §0 迭代目标行、§1「解决到哪」、details「问题与约束·回调边界」仍写「sim 深井发放与补给宝钻两处调用 / 两个调用点 / 补给缺口顺手闭合」,与 §2 第 5 条「supply 路径零改动」直接矛盾(违反 iteration-design §5 规则 4「修订后全量同步复查……禁只改触碰段」,其「防的事故」原文即此形态:「行为变化申报与派工面残留旧口径」);
- **N2【中】**:F2 新增「同窗洗白形态披露」段的**后果失真**——洗白后下一 equips 观察走的是 logic 源**真失配 → 安灯停机**(生产 = 留证 + 停机 flag),不是「临时缺口、整表覆盖自愈」;且「频率极低(需带钻补给)」低估:任意补给选定都写 equips,不限带钻。「不设守卫、接受披露」的处置建立在失真后果上,不自洽;
- **N3【中】**:回调三写 observe 的 sig 形态与 sim 单 sig 接线**矛盾**——`observe()` 渠道校验只收 obs 族,而接线写死 `logic_sig('sim:env')` 并让回调复用入参 sig,首笔 observe 即 ValueError(F5 同类,修订交互新面);
- **N4【低】**:跨迭代过程号清除不全(「ore 迭代 R5 教训」×1、T-1×3、T-5×1)。

四项均为定点文本修法,无结构返工;修订后免第三轮全量再审,定点复核即定稿(iteration-design §6:定稿门槛 = 攻击收敛 + 试读过,「带开放问题的定稿」不存在,故本轮不放行定稿)。

## 二、修复核验表(对照第一轮 F1–F11 逐条)

| 编号 | 修订主张 | 核验结果 | 核验依据(符号/内容定位) |
|---|---|---|---|
| **F1**【高】 | supply 不采纳回调、路径零改动;「明确不解决」新增钻类型未建模条目 | **主体闭合,残留 3 处旧口径 → N1**。①②③ 分见下三行 | — |
| F1-① 新前提与代码事实一致性 | 「supply 带钻选项的钻类型未建模(聚合计数,可能红/蓝/财富任一)」 | ✅ **属实** | 选项侧 `has_diamond: bool` 无类型位(test_cw_sim_backend.py:870 `any(o.has_diamond)`、:872-873 `chosen_supply = ('', equip, has_diamond)`);`_on_supply_picked` 仅 `int(diamond_count.value or 0) + 1` 的 observe 写、零类型判别,且 `disclosures.setdefault(SUPPLY_DIAMOND_SLOT_PENDING, 'uniform_slot')`(sim/cw_sim_backend.py:1093-1103,披露键 :522)——「聚合计数、类型未建模」与代码逐字吻合 |
| F1-② 恒惰性腿是否结构性消失 | 不采纳后「cap 腿对补给路径恒惰性」不再存在 | ✅ **结构性消失**。旧 F1 的成立前提是「supply 调回调但 cap 公式读不到宝钻」;现文回调唯一调用点 = 深井发放路径,该路径发放刻刚把宝钻 append 进 equips,cap 腿必然可计——不存在任何「调了回调但公式读零」的路径。landing 3.3 判据同步反转(「supply 路径零行为变化:diamond_count +1,deploy_cap/back_layout 不变」),可证伪且与代码现状一致 | details §5 不采纳段(:83);design §2 第 5 条(:34)与契约·回调边界(:43「仅深井发放路径调用」);landing 3.3(:38、:46) |
| F1-③ 深井路径 cap 公式自洽性(R5 式追问) | 先 write_logic_rand append 宝钻 → 回调读 equips 现值计数 | ✅ **自洽**。`write_logic_rand` 经 `_write_logic_frame` 即时落值(source='logic_rand'),回调随即读 `gs.equips.value` 含新 append 的财富宝钻 → cap = level+1;`back_layout = min(9, 现值+1)` 与 cap 同步 +1,域内关系「back_layout ≈ 6+(cap−level)」保持(kernel/cw_game_state.py:2250 字段注);`level_of` 未观察缺省 1 无 None 炸(:3989-3992);diamond_count 开局种子 0(:790)+ `or 0` 防御;equips None 在该路径不可达(触发条件 6 的宁缺勿造前置)。边界注:sim 现状唯一向 equips 写入财富宝钻的路径 = 本发放(box 候选池 U24 未定、挂 BOX_POOL_PENDING_U24 披露,:1119;ENV_GIFTS 无宝钻条目),故「count=1、cap=level+1」在现模下恒真;未来 sim 若建模合成/礼包获得宝钻,回调须随获得路径接线,否则域内关系破裂——建议正本化时带一句 | cw_game_state.py:3095-3098;cw_sim_backend.py:1093-1103;landing 3.3 数值对照判据(:45) |
| **F2**【中】 | 同窗洗白披露落 §3;处置「不设守卫、接受披露」 | **披露落了,处置不自洽 → N2**(后果失真 + 频率低估,详 §三) | 披露段在 details:60;反证链见 N2 |
| **F3**【中】 | 失真依据清除;「红/蓝钻无 cap 语义」新依据 | ✅ **闭合**。旧失真依据(「带钻选项语义」支撑 supply 硬编码财富宝钻)随「supply 不采纳」结构性清除;新依据逐字属实:财富宝钻条目「拥有宝钻可以使团队规模上限+1,无论是否被角色穿戴」(data/cw_equipment_data.py:53);红钻「用于合成阵营星徽」、蓝钻「用于合成流派星徽」均无 cap 文本(:64-65);`DIAMOND_EQUIP_NAMES = {红钻, 蓝钻, 财富宝钻}` 系视觉判定族(kernel/cw_obs_core.py:50)。附非阻塞小注:landing 3.3「宝钻裁决只认财富宝钻」(:44)在接线面仍近永真(登记表唯一实参 = 财富宝钻),其证伪路径 = 回调**直调负例**单测(§4 早退分支),建议 3.1 验收凭据「回调三写」点名含负例 | details §4(:72);cw_equipment_data.py:53/64-65 |
| **F4**【中】 | 引用锚全部可解析 | ✅ **闭合**。grep `ore-conditional` 全目录零残留(仅第一轮报告自引);landing 三处设计依据均指 `details/env-conditional-grant.md` §1–§4 / §5(live 部分) / §5(sim)/§4(回调) + design §2 第 5 条,全部可解析;design 自引「§2 第 5 条」、details「总纲 §2」可解析 | landing:13/18/26/39;grep 全量 |
| **F5**【中】 | sig 单形态写死,三方一致 | ✅ **触发函数面闭合;回调面溢出新矛盾 → N3**。触发函数:design 契约「禁 obs_sig 进触发函数」(:42)/ details §5「sig 写死单形态 = logic_sig('sim:env')」(:82)/ landing 3.3「sig 写死 logic_sig('sim:env') 单形态」(:44)三方一致,无「挂接/登记分通道」残留;代码事实核实:`write_logic`/`write_logic_rand` 渠道校验均 `_validate_sig(sig, ('logic_action', 'logic_hook'))`(cw_game_state.py:3058/3095),`obs_sig` = family='obs'(sim/cw_sim_base.py:30-34)传入即炸,`logic_sig` = family='logic_action'(:37-40)合法 | design:42;details:82;landing:44;cw_game_state.py:3058/3095;cw_sim_base.py:30-40 |
| **L1(F6)**【低】 | done 现值 None 防御 | ✅ **闭合**。条件矩阵第 5 序「done 现值(None → 视为空,防御)」、第 6 序 done 追加「现值(None → 视为空)+ ((env,'first_streak'),)」双读口均带防御(details:52/55),与晶矿先例 `or ()` 同形;landing 3.1 判据扩为「触发条件矩阵七序短路含 done None 防御……回调三写含 back_layout min9 与 None 防御」(landing:18) | details:52/55/76;landing:18 |
| **L2(F7)**【低】 | design §0 状态同步 | ✅ **闭合**。design:6「状态:对抗审中」与 README 进度行一致 | design:6;README |
| **L3(F8)**【低】 | 跨迭代过程号清除 | **部分闭合 → N4**:landing「防 ore 迭代 R5 式假绿」已改语义表述(「防姊妹迭代实证的假绿形态」landing:31)、details §5「3.3 晶矿先例」已删;但 details:7 仍留「ore 迭代 R5 教训」,另有 T-1×3(design:40、details:22、details:27)、T-5×1(design:5,含 .debug/progress 本地路径指针)——同为兄弟迭代任务号,寿命不受本迭代控制,与 F8 同判据 | grep 全量;N4 |
| **L4(F9)**【低】 | 获得链前提修正 | ✅ **闭合**。取舍第三条已删「确定性写」前提,改真实理由:随机态纪律(落位未知走 write_logic_rand + 观察收口)+ done 原子性(同 sig 相邻两笔)(details:93);获得链 `rand: bool` 必参事实与现文不冲突(cw_sim_backend.py:1134-1137 `gain_equipment(..., rand=False, ...)` 同形在册) | details:93 |
| **L5(F10)**【低】 | OCR 假阳披露 | ✅ **闭合**。details §3 第三披露段(:64)+ design「明确不解决」并句(:23),措辞与第一轮建议一致(假发放永久占据一次性、值由观察纠偏、接受并披露、校准另线) | details:64;design:23 |
| **L6(F11)**【低】 | 校验样板第 6 处记档 | ✅ **闭合**。取舍第二条记档「孤儿键校验样板已第 6 处同形复写,提取排期入口留 harness 反馈队列;提取的是校验样板,非条件框架」(:92)——恰好把「校验样板 ≠ 条件框架」的裁定边界写明;第 6 处计数属实(`_validate_env_economy`/`_validate_env_ore_grants`/`_validate_env_gifts`/`_validate_strategy_grants`/`_validate_env_pool_rewrite` 五处在册,cw_investments.py:1200/1246/1355/1602/1739) | details:92;cw_investments.py 五 validator |

**跨文档三方同步**(design §2 第 5 条 ↔ details §5 ↔ landing 3.3):契约面一致 ✅(supply 零改动 + 回调仅深井 + sig 单形态,三处互证);破坏同步的只有 §二 N1 所列三处契约面**之外**的残留段。

## 三、新发现(仅限本轮触碰面)

### N1【中】F1 修复传播不全:三处旧「两调用点/补给缺口顺手闭合」口径残留

- **位置与原文**:
  1. design.md:5(§0 迭代目标,用户裁定记录):「『宝钻到手 → 重算上限』做成**共用函数**(sim 侧补给宝钻的既有上限缺口顺手闭合)」——裁定原文可留,但修订推翻了裁定的落地范围,现文无任何后注,读者先读到「补给缺口本迭代闭合」,三节之后才读到「supply 零改动、另批」;
  2. design.md:17(§1 解决到哪):「宝钻回调 = kernel 共用函数(sim 深井发放与补给宝钻两处调用)」;
  3. details:8(问题与约束·回调边界):「回调 = sim 专用,两个调用点(深井发放后 + 补给宝钻)」。
- **矛盾对象**:design:34(§2 第 5 条「supply 路径零改动」)、design:43(契约「仅深井发放路径调用」)、details:83(§5 不采纳段)、landing:38/46(3.3 范围与零变化判据)。
- **规范出处**:iteration-design.md §5 规则 4「修订后全量同步复查……禁只改触碰段」,其明列防的事故 =「方案改了、行为变化申报与派工面残留旧口径」。
- **危害**:details 详设自顶向下阅读时,:8 先于 §5 出现,实现者按「两个调用点」接线 supply → 回调即复活第一轮 F1 的假闭合(supply 宝钻不进 equips,cap 腿恒惰)。
- **修法**(三处各一句):①design:5 句尾补后注「(修订后调整:补给不采纳回调,该缺口不在本迭代闭合,见 §2 第 5 条)」;②design:17 改「宝钻回调 = kernel 共用函数(唯一调用点 = sim 深井发放路径;supply 不采纳,见第 5 条)」;③details:8 改「回调 = sim 专用,唯一调用点 = 深井发放后(supply 不采纳回调,见 §5)」。

### N2【中】F2 披露段后果失真:洗白后实为 logic 源真失配 → 安灯停机,非「临时缺口自愈」;频率前提亦低估

- **现文**(details:60):「猜值可能被洗白(逻辑态临时丢失宝钻)——真值仍在游戏世界,下一 equips 观察**整表覆盖**恢复,损失 = 逻辑态临时缺口;频率极低(需同窗结算 5 连胜 + 带钻补给),接受并披露,不设守卫。」
- **代码事实链**(逐环核实):
  1. 洗白腿 = 补给装备腿 `owned = list(gs.equips.value or []); owned.append(item); gs.write_logic(gs.equips, owned, ...)`(kernel/cw_action_report/pick_supply.py:101-104)——**读现值追加回写,任意补给选定都走此腿(不限带钻)**;write_logic 把字段来源从 logic_rand 翻成纯 logic(无任何 rand 继承闸,`any_logic_rand` 全仓无调用点,仅 docstring 提及);
  2. 下一备战帧 heavy 观察:observe() 对 `source == 'logic'` 且值不等 → 先经 deployed/board 两个吸收器(equips 均不命中)→ `_route_logic_mismatch`(cw_game_state.py:2803-2814);**只有 `source == 'logic_rand'` 的覆盖才静默采新**(:2794-2802)——披露声称的「整表覆盖恢复」仅是未洗白情形的行为;
  3. 三分流:豁免注册表 `EXEMPT_REGISTRY: dict = {}` **为空**(kernel/cw_mismatch_policy.py:63),抑制前缀仅 `'sim:engine'/'sim:synthesized'` 且「生产实机链零 sim 前缀写点」(cw_game_state.py:995)→ equips 失配 = **真失配** → 缺陷行 + `[cw!]` 告警 + 安灯钩子,生产装配 = 截图留证 + **停机 flag**(cw_mismatch_policy.py:15-16)——即第一轮 F2 点名的「无人值守 run 停机」后果原样可达。值确被观察采新(「观察赢」覆盖照常,cw_game_state.py:2815),但停机同时发生,不是「损失 = 临时缺口」。
- **频率修正**:洗白不需「带钻补给」——幻影宝钻(发放 guess)与实读装备集不符即失配;深井 5 连胜结算的下一节点凡为补给(结算完成白名单含补给,cw_screen_battle_wait.py:86-92;补给必选卡 → 必写 equips)即触发,一次/局发放时刻的条件概率不低。「频率极低」的前提句失真。
- **附带裁定事实**:第一轮修法选项①(把 `env_grant` 前缀登记失配豁免)对洗白形态**结构性无效**——豁免查表第三维用**字段现 evidence**(cw_mismatch_policy.py:66-91,路由传 `logic_evidence=target.evidence`),洗白后字段 evidence = 洗白写端的 `owned[...]` 前缀,`env_grant` 前缀永不命中;而按 equips 字段全量豁免会吞掉该字段全部真 bug。故「不设守卫」下唯一自洽出路是**如实披露停机后果并显式接受**。
- **修法**(二选一):①维持「不设守卫」,重写披露段:「同窗确定性 equips 写(补给装备腿等)会把字段来源翻 logic,下一 heavy 观察 = logic 源真失配 → 安灯停机(生产 = 留证 + 停机),值由观察采新;接受该风险并披露——发生时按安灯现场处理,续跑即愈(done 已标记不重发,幻影值已被观察覆盖)」;②不愿接受停机则回到第一轮选项③次序守卫(同窗已有确定性 equips 写则本结算放弃发放、下结算重试)。任选其一均删「临时缺口/整表覆盖恢复/需带钻补给」三处失真表述。

### N3【中】回调三写 observe 的 sig 形态与 sim 单 sig 接线矛盾(F5 同类,修订交互新面)

- **问题**:design 契约「回调写法:三域全部 `gs.observe`」(design:44)+ details §4 回调签名 `on_diamond_acquired(gs, equip_name: str, sig)`(details:69)+ details §5 sim 接线「`on_diamond_acquired(gs, 返回名, sig)`;sig 写死单形态 = `logic_sig('sim:env')`」(details:82)——回调若复用入参 sig,其三笔 `gs.observe` 写在第一笔即炸:`observe()` 渠道校验 `_validate_sig(sig, ('obs',))` **只收 obs 族**(cw_game_state.py:2792),logic_action 族传入即 ValueError,`_resolve_battle` 无 try 包裹 → sim 局崩。
- **定性**:F5 修的是**触发函数**(两笔 logic 写,单 logic_sig 正确);回调是另一个函数、三笔**观察通道**写,sig 族需求相反。修订把「单形态」写死到接线变量后,回调的 sig 形态变成「实现者自行拍板」(违停手令前提,F5 同罪);照字面复用则必崩。
- **先例**:同文件 `_on_supply_picked` 的 observe 写**不收 sig 参、内部自构** `obs_sig(group_id='sim:diamond')`(cw_sim_backend.py:1099-1101)。
- **修法**(一处):details §4 补一句「回调内部三写自构 obs 族 sig(如 `obs_sig(group_id='sim:env-diamond')`),先例 = `_on_supply_picked` 内构形态;入参不传 sig」并同步改签名为 `on_diamond_acquired(gs, equip_name: str) -> None`(与先例同形,推荐);或保留 sig 参但明写「仅用于留证行,observe 写一律内构 obs 族 sig」。design:44 与 landing 3.3 同步一句。

### N4【低】跨迭代过程号残留(F8/L3 尾巴)

- **残留清单**:details:7「ore 迭代 R5 教训:op 成员记忆跨环重建伪造状态,禁用」(R 号);design:40「投影审计行(完备性锁强制,T-1 先例)」、details:22「沿晶矿迭代 T-1 先例」、details:27「先例 = 晶矿三域,T-1」(兄弟迭代任务号 ×3);design:5「源迭代 `.debug/progress/2026-09-23-invest-effects-calc` T-5」(任务号 + gitignore 本地路径指针 ×1)。
- **判据**:与 F8 同类——兄弟迭代工件(changes/ 任务表、.debug/progress)均可删减,失锚不可重建;教训语义均已内联复述,过程号只是装饰。
- **修法**:details:7 删「ore 迭代 R5 教训:」字样留语义句(或改持久指针「晶矿声明通道 done 域落地形态见 kernel/cw_ore_channel.py」);三处 T-1 改持久指针(「先例 = cw_game_state.py 种子三域/DEFAULT_GS_SCHEMA 独立键/投影审计行」)或纯语义;design:5 的 T-5 改纯语义(「深井角斗场机制接入外溢」已自足,删 T-5 与 .debug 路径)。

## 四、定稿试读(修订 N1–N4 后逐阶段)

- **3.1 kernel 条件发放与登记表——可开工**。条件矩阵七序(含 None 防御)、四件套、登记表三条校验(`INVESTMENT_ENVS`/`EQUIPMENTS` 符号均在册,cw_investments.py:799、cw_equipment_data.py:51)、evidence 形态齐备;N3 修后回调签名定型,N4 修后依据指针全持久。
- **3.2 live 接线——可开工**(本轮修订未触碰其可开工结论;调用点唯一、sig 先例 `_ORE_HOOK_SIG` 同形、streak_after None 口径一致)。
- **3.3 sim 接线——N1/N3 修后可开工**。数值对照判据(diamond_count +1、cap = level+1、back_layout +1 min9、同 seed 重放)在现模下可达(F1-③ 边界注成立);「supply 零行为变化」判据与 `_on_supply_picked` 零改动现状对齐,可证伪。
- **末阶段正本更新——可执行**(五路径全在,glob 复核通过)。

**总试读结论**:本轮不放行定稿(带 3 中 1 低 = 「带开放问题的定稿」不存在);N1–N4 均为定点文本修法,修订后定点复核(不必全量再审)即放行定稿。
