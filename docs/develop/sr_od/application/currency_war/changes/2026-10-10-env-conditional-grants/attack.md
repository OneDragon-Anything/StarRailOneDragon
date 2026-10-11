# 环境条件发放 迭代设计·对抗审查报告

> 审查对象:本目录 README.md / design.md / landing.md / details/env-conditional-grant.md。
> 审查规范:docs/develop/harness/iteration-design.md §5(写作硬规则)、§7(三核)。
> 对照基准:全部「依据」按符号/内容直查代码核验(不依赖文档所写行号);审查轮次内共核验 25 组依据,逐条见 §三。

## 一、结论

**有条件通过**——主链(结算屏触发点 / write_logic_rand 随机态发放 / done 一次性守卫 / live 零回调 / 触发检查 live+sim 单一 kernel 源)与用户六条裁定逐条对齐,且关键代码事实全部核验属实;但 **§5「补给宝钻采纳」的 deploy_cap 腿按现文惰性,「缺口闭合」自证不成立**(最重发现),另有一处可达的随机态「洗白→安灯」风险链、三钻身份依据失真、引用锚与 sig 形态两处规范违例——修订 details §5(供给采纳段+sig 形态)与 landing 引用锚后可定稿,3.1/3.2 两阶段现有文本已基本可开工。

## 二、发现清单

### F1【高】§5「补给宝钻采纳」的回调 deploy_cap 腿对补给路径恒惰性——「缺口闭合」自证不成立

- **问题**:回调公式 `deploy_cap = level_of(gs) + equips 现值中 '财富宝钻' 计数`(details §4.2),但 sim 侧补给宝钻从不进 `gs.equips`——`_on_supply_picked` 带钻分支只写 `diamond_count`(sim/cw_sim_backend.py:1093-1101),带钻选项的 equip 是普通装备件、钻石是**额外**授予(test_cw_sim_backend.py:851-881 实证:上报写 `pick.equip` 入栏,钻石走 `_on_supply_picked` 计数)。于是把裸写替换为回调后:diamond_count +1 ✓、back_layout +1 ✓、**deploy_cap = level + 0 = 不涨**——用户裁定 3 点名要闭合的两腿缺口的 cap 腿原样留着。更糟的是双存域域内关系破裂:back_layout +1 而 deploy_cap 不动,违背容器在册口径「理论关系 back_layout ≈ 6+(cap−level) 仅域内成立」(kernel/cw_game_state.py deploy_cap 字段注)。landing 3.3 判据「supply 采纳后:带钻补给局三域同步(缺口闭合的行为面)」按现文不可达。
- **证据**:cw_sim_backend.py:1093-1101(现状只写 diamond_count);details §4.2(cap 公式按 equips 计数);details §5「三写生效,sim 上限保真缺口闭合」;test_cw_sim_backend.py:881(`diamond_count == (1 if diamond else 0)`,equip 另行走上报腿)。
- **建议修法**:二选一并写死进 details §5:①供给采纳时同时把 `'财富宝钻'` 追加入 `gs.equips`(使 cap 公式可计;需申报为 sim 内部口径并与 live 侧行为对齐说明);②回调 cap 公式改按 `diamond_count` 现值计数(「拥有」= diamond_count 台账),同时深井路径刚 append 过 equips 不受影响。任选其一都须连带处理 F3(三钻身份)。

### F2【中】随机态发放的猜值可被同窗确定性写「洗白」成 logic 源 → 观察失配走安灯链,与「预期内非 bug」申报冲突

- **问题**:发放把 `equips` 写成 logic_rand(猜值含幻影财富宝钻),设计申报「观察覆盖差异 = 随机效果落地,预期内非 bug——零持续污染」。但结算完成白名单含补给/遭遇/投资策略(cw_screen_battle_wait.py:86-92),**该结算后、下一 heavy 观察前的窗口**内任何确定性 equips 写会把猜值吸收进 logic 源:补给选中带钻选项(策略第 1 级就偏好带钻,mandate_v1/supply.py:8-9、114-116)→ `report_action_pick_supply_param` 装备腿 `write_logic(gs.equips, 猜值+[item])`(cw_action_report/pick_supply.py:101-104)→ 字段来源翻 logic → 下一备战帧观察读到真实装备集(幻影钻名/件序不符)→ 失配按 **logic 源三分流 → 安灯停机**(observe() 的 `target.source == 'logic'` 分支,cw_game_state.py:2803-2814;EXEMPT_REGISTRY 无 equips 在册豁免,cw_mismatch_policy.py:63)。单局一次性(深井只发一次)但可达,且后果是无人值守 run 停机。窗口内**读**猜值的面(flow.py:760、mandate supply.py:164、pick_supply.py:101)同未披露。
- **证据**:write_logic_rand docstring 的消费纪律是软约束(「策略器消费前必须重观察」,无硬闸);observe() 失配路由按**写时刻来源**定谳;pick_supply 装备腿恒 write_logic。
- **建议修法**:details 补窗口边界披露段(晶矿通道对每条边界逐条披露,本设计缺失),并三选一给处置:①申报接受 + 把 `env_grant` 前缀登记进失配豁免(豁免 ≠ 消失,留证照落);②发放写改在下一 heavy 观察前夜执行(违背裁定触发点,不推荐);③给触发函数追加「同窗已有确定性 equips 写则放弃发放下结算重试」的次序守卫。至少要把「读猜值消费面清单」写进披露。

### F3【中】「补给宝钻即财富宝钻(带钻选项语义)」依据失真:带钻选项 = 三钻之一,红/蓝钻无 cap 语义

- **问题**:设计把 sim 供给采纳硬编码为 `on_diamond_acquired(gs, '财富宝钻', sig)`,引「带钻选项语义」为据;而在册观察契约是 `has_diamond:装备位带三钻之一(红钻/蓝钻/财富宝钻)`(kernel/cw_events.py:74;cw_node_obs.py:227「装备名精确匹配三钻」;cw_obs_core.py:50 `DIAMOND_EQUIP_NAMES = {红钻, 蓝钻, 财富宝钻}`),红钻/蓝钻官方条目无团队上限语义(data/cw_equipment_data.py:64-65「用于合成…星徽」)。三钻真实分布未定(U24 披露键 `SUPPLY_DIAMOND_SLOT_PENDING` 在册,cw_sim_backend.py:521)——现文等于让 sim 对红/蓝钻补给也 back_layout+1,是**保真度倒退**,与 landing 3.3「sim 行为变化 = 保真度修复」方向相反。landing 判据「宝钻裁决只认财富宝钻」在硬编码实参下永真,不构成可验收判据。
- **建议修法**:details §5 明示「sim 一律按财富宝钻建模,真实分布 U24 未定」的假设并挂 SUPPLY_DIAMOND_SLOT_PENDING 披露键(或采样三钻身份);landing 3.3 该判据改为可证伪形态(如断言 evidence/produced_by 通道,或披露键断言)。

### F4【中】landing 引用锚「ore-conditional」不存在(§5 硬规则 4 引用锚存在性违例)

- **问题**:landing 3.1「行为对照 ore-conditional §1–§4」、3.3「行为对照 ore-conditional §5 sim 部分」——迭代内不存在任何 ore-conditional 文档,本迭代的详设是 details/env-conditional-grant.md;章节号序列与该详设吻合,系改名/复制残留。这正是 §5 规则 4「全量同步复查:逐一核设计引用的每个符号/路径存在性」要拦的形态。
- **建议修法**:两处改指 `details/env-conditional-grant.md §1–§4 / §5`。

### F5【中】sim 接线 sig 形态双表述歧义,选错即渠道族校验炸、sim 局崩(实现者无需再设计违例)

- **问题**:details §5「sig = `obs_sig(group_id='sim:env')` / `logic_sig('sim:env')` 形态沿 3.3 晶矿先例(挂接/登记分通道)」——触发函数**只有一个 sig 参**且两笔写(write_logic_rand + write_logic)全在 logic 族(cw_game_state.py:3058/3095 校验),`obs_sig` 是 family='obs'(sim/cw_sim_base.py:30-33)传进去即 ValueError;晶矿先例的双 sig 是因为它还有 spheres 的 observe 写,本函数没有。`_resolve_battle` 无 try 包裹 → 异常直接炸穿 sim run。实现者面对双表述必须自行拍板(违反停手令前提)。
- **建议修法**:写死 sim 传 `logic_sig(group_id='sim:env')` 单 sig,删「obs_sig/挂接/登记分通道」句;live 侧 `logic_hook` 族表述正确保留(先例 = cw_screen_prep.py:136-137 `_ORE_HOOK_SIG`)。

### F6【低】触发函数 done 现值 None 防御缺失

- **问题**:伪码 `(env, 'first_streak') ∈ env_grants_done` 与「现值 + ((env,'first_streak'),)」未防 `value=None`。生产双端都种子化(实机经 game_state_of;**sim 在 `__post_init__` 显式 `seed_opening_state`**,cw_sim_backend.py:776-780),但测试直构容器与旧档恢复(restore 对快照缺键域保持 None,cw_game_state.py:3854)可达,`None + tuple` = TypeError。晶矿先例同位有 `tuple(gs.ore_declared_done.value or ())` 防御(cw_ore_channel.py:168、239-240),本设计引用其形态却未带防御。
- **建议修法**:伪码补 `or ()`,与先例同形;landing 3.1 判据「回调三写含…None 防御」扩为「触发函数与回调全部现值读口的 None 防御」。

### F7【低】design.md §0 状态「草案」与 README「对抗审中」不同步

- **问题**:对抗审已启动(本报告即其产物),README 进度行已写「对抗审中」,design.md §0 仍「草案」。硬规则 4 全量反查应同步两处。
- **建议修法**:design.md §0 状态改「对抗审中」(定稿时再改「定稿」)。

### F8【低】跨迭代过程号引用寿命错配(R5/R6/「3.3 晶矿先例」)

- **问题**:details「晶矿迭代 R5/R6 教训」「ore 迭代 R5 教训」、landing「防 ore 迭代 R5 式假绿」、details §5「3.3 晶矿先例」——指向**兄弟 changes/ 迭代的攻击报告轮次号与 landing 阶段号**。changes/ 会不定期删减,失锚后这些引用不可重建(AGENTS.md §8「引用必须是持久索引」同判;iteration-design §1 引用寿命分层:跨迭代工件引用寿命 = 两迭代寿命的 min,不满足本迭代的可读性承诺)。教训语义本身已内联复述,引用只是装饰。
- **建议修法**:R 号删除,改持久指针(「晶矿声明通道 done 域落地形态见 kernel/cw_ore_channel.py」)或纯语义描述(内联句已够)。

### F9【低】关键取舍「获得链原语面向确定性写」依据失真

- **问题**:取舍称「获得链的装备获得原语面向『获得时点确定的发放』(确定性写)」——`gain_equipment` 带 `rand: bool` 必参(cw_gain_chain.py:517、531 `_select_write(gs, rand)`),rand=True 时其写行(`list(inv) + [item]` 经 write_logic_rand)与本设计的发放写**完全同形**(gain-chain.md §2.3/§5 在册)。结论(独立写)仍可成立,但真实理由是另两条:done 与发放的原子内聚(同 sig 相邻两笔)+ 装备获得后果枚举不含宝钻语义(需另加分支,与回调重复)。依据错 = §5 规则 1 的攻击目标。
- **建议修法**:取舍段改写为上述真实理由,删「确定性写」前提句。

### F10【低】live OCR 假阳方向的假发放会永久占据一次性(披露缺)

- **问题**:`parse_streak` 假阳(如连败×5 的「败」字漏读 → +5)会触发假发放;equips 观察能纠偏**值**(幻影钻被整表覆盖掉),但 done 标记无撤销腿 → 真 5 连胜在本局不再补发。一次性守卫不可逆是该设计固有属性,可与接管局披露并句披露即可,现文未提。
- **建议修法**:details「恢复局边界披露」段并句:「OCR 方向假阳同理,假发放占据一次性、值由观察纠偏,接受并披露」。

### F11【低】孤儿键校验族第 6 次逐表复写(治本核·跨件半问)

- **问题**:`_validate_env_economy` / `_validate_env_ore_grants` / `_validate_env_gifts` / `_validate_strategy_grants` / `_validate_env_pool_rewrite` 之后,ENV_STREAK_GRANTS 再写第 6 份「孤儿键 + 格式」校验——同族第 N 次出现按根源两问应问「是否同一个更高层架构根」。注意:用户否定的是「统一**条件框架**」(触发接线万能通道),**不覆盖**校验助手提取——两者不冲突。
- **建议修法**:本迭代可照旧逐表写(与姊妹迭代同形优先);在「关键取舍」或正本动机段留一句「校验骨架重复 6 份,提取共用 `_validate_env_table(表, 键集, 值检)` 助手挂后续批」,给根治排期入口即可;不构成立项阻塞。

## 三、依据核验表(25 组,逐条对码)

| # | 设计主张 | 核验结果 | 出处(符号/内容定位) |
|---|---|---|---|
| 1 | 深井角斗场(104)「本局首次达成5连胜时,获得【财富宝钻】」原文 | ✅ 逐字属实 | data/cw_invest_data.py `PlazaPortal(id='104')` |
| 2 | `INVESTMENT_ENVS` 含键『深井角斗场』(登记表键合法) | ✅ 键 = PLAZA_PORTALS.name 构建 | kernel/cw_investments.py `_build_envs`/`INVESTMENT_ENVS` |
| 3 | `_validate_env_economy` / `ENV_ORE_GRANTS` import 即炸先例(3.1 姊妹迭代已落地) | ✅ 在册,含孤儿键+双源同步两腿 | cw_investments.py `ENV_ORE_GRANTS`/`_validate_env_ore_grants`(模块级直调) |
| 4 | 结算覆盖写端 `apply_settlement_cover` 做 `gs.observe(gs.streak, streak_after)`,None 跳写 | ✅ 属实;sig 固定 obs/CwScreenBattleWait | kernel/cw_game_state.py `apply_settlement_cover` |
| 5 | streak 真值唯一生产点 = `parse_streak`,前缀定方向(连胜+/连败−),失读 None | ✅ 属实 | obs/cw_settlement_obs.py `parse_streak` |
| 6 | live 唯一接线点可行:battle_wait 结算块,`streak_after` 与 gs 同域可得 | ✅ `apply_settlement_cover` 全仓唯一生产调用点;`_obs.streak`/`gs_of_ctx` 在作用域内;外层 try 兜底不阻塞 | operations/cw_screen/cw_screen_battle_wait.py 结算覆盖段 |
| 7 | sim 结算 streak 写点 `_resolve_battle` → observe(signed),幂等守卫在册 | ✅ `_settled_key` 键控;死亡早退不触发(败向 streak,无冲突) | sim/cw_sim_backend.py `_resolve_battle` |
| 8 | sim 现状缺口:补给宝钻只写 diamond_count | ✅ 属实,含 `or 0` 防御 | cw_sim_backend.py `_on_supply_picked` |
| 9 | sim 容器种子化(有 `or ()` 级前提) | ✅ `__post_init__` 显式 `seed_opening_state` + diamond_count observe 0 | cw_sim_backend.py `__post_init__` |
| 10 | `max_units_of` = cap(≥level 采信)封顶 4+back_layout,消费面广 | ✅ 公式属实;20+ 消费点(部署/板满/升级判据) | cw_game_state.py `max_units_of` 及 grep 消费面 |
| 11 | equips/deploy_cap 观察写端整表覆盖语义 | ✅ equips = 备战 heavy 整表 observe;deploy_cap = 双帧一致门 observe,失读 carry | operations/cw_screen/cw_screen_prep.py 装备段;obs/cw_observation.py 'deploy_cap' 写端 |
| 12 | `write_logic_rand` 通道纪律(随机落地预期内、消费前重观察) | ✅ docstring 属实(纪律为软约束,见 F2) | cw_game_state.py `write_logic_rand` |
| 13 | done 直写先例 = cw_exec_state 金腿 / cw_effect_inventory 退款腿 | ✅ 两处 `write_logic` 在册 | cw_exec_state.py 金腿;cw_effect_inventory.py 退款腿 |
| 14 | 晶矿 done 域四件套先例(种子/恢复 tuple 重建/独立 schema 键/审计行) | ✅ 四件全在册;恢复不登记则 tuple→list 静默漂移的判断正确 | cw_game_state.py 种子三域/DEFAULT_GS_SCHEMA 三键/`restore_state_snapshot.rebuild`;cw_projection_audit.py 三行 |
| 15 | 财富宝钻官方条目(cap+1 拥有即算可叠加、每3备战阶段+1金、合成 recipes 三路) | ✅ 逐字属实 | data/cw_equipment_data.py `'财富宝钻'` 行 |
| 16 | 红/蓝钻 cap 语义无涉;`DIAMOND_EQUIP_NAMES` = 视觉判定族 | ✅ 条目无 cap 文本;集合 = {红钻,蓝钻,财富宝钻}(同时反证 F3:带钻≠财富宝钻) | data/cw_equipment_data.py 红钻/蓝钻行;kernel/cw_obs_core.py `DIAMOND_EQUIP_NAMES` |
| 17 | 宝钻金面效果已注册、发放路径零登记义务 | ✅ `equip_diamond_phase_gold` 纯算术按 worn 计数,无登记面 | kernel/cw_effect_inventory.py `equip_diamond_phase_gold` |
| 18 | 「同 `roll_ore_reward` live/sim 单一正确性来源」先例引用 | ✅ live(collect_ore 腿)与 sim(generate_ore_rewards)同函数 | kernel/cw_ore_reward.py `roll_ore_reward`;两调用点 |
| 19 | 既有发放通道:ENV_GIFTS items_immediate/items_scheduled | ✅ 在册 | cw_investments.py `GiftGrant`/`ENV_GIFTS` |
| 20 | 「D-53 实测口径」持久在案 | ✅ D-53 = cap 读链校准编号,多处引用(5 fixture 核正、局38 r2 cap5/lv3) | obs/cw_observation.py D-53 各处 |
| 21 | live logic_hook 族 sig 先例(group 'prep:ore-channel' 形态) | ✅ `_ORE_HOOK_SIG` 同形在册 | cw_screen_prep.py `_ORE_HOOK_SIG` + `check_ore_declared_level` 接线 |
| 22 | 正本更新清单五个路径真实存在 | ✅ 五路径全存在 | game_state/fields.md、game_state/gain-chain.md、flow/projection_contract.md、sim/sim-wiring.md、docs/game/currency_war/research/invest_effects.md |
| 23 | landing 结构合规(阶段七件齐、首节常规检查自包含、末阶段正本更新、README 合模板) | ✅ 形齐(引用锚错名见 F4,状态不同步见 F7) | landing.md 各阶段;README.md |
| 24 | 测试先例与技法可得(test_cw_ore_channel / opening_seed / sim_backend 在册;import 即炸测试 = monkeypatch+直调 validator) | ✅ 在册且技法有先例 | sr-od-test/test/sr_od/application/currency_war/ 三文件;test_cw_ore_channel.py 校验段 |
| 25 | 深井角斗场现状零触发建模 | ✅ 全 src 无 104/深井触发逻辑(仅数据行与策略 stance) | grep 全量 |

## 四、实现者试读(逐阶段:凭文档能否开工)

- **3.1 kernel 条件发放与登记表 —— 基本可开工**。四件套/登记表/条件矩阵/发放写行均有直接先例(晶矿通道同形),文件面真实;两处需带答案补:done 现值 `or ()` 防御(F6,可按先例自补)、审计行内容照 ore 行抄形。「import 即炸」测试技法有在册先例(monkeypatch + 直调 validator)。
- **3.2 live 接线 —— 可开工**。调用点全仓唯一、`streak_after` 可得、sig 形态有 `_ORE_HOOK_SIG` 同形先例;唯一小坑是异常会被外层 try 记成「结算覆盖写失败」标签(可接受,建议实现时独立 try 或改日志措辞,属实现自由度)。
- **3.3 sim 接线 + supply 采纳 —— 不可直接开工**。F1(cap 腿惰性,「缺口闭合」判据按现文写不出来)、F3(三钻身份假设未申报)、F5(sig 选错即崩)三个问题都在本阶段的设计依据内,且都没有「设计未回答→停手回指」的可用答案——必须先回 details §5 修订,否则实现者必然自行拍板(在未过对抗审的语境做设计决策)或交付一个与自身判据矛盾的实现。
- **末阶段正本更新 —— 可执行**。清单五路径全部存在、逐条映射到阶段,无悬空引用。

**总试读结论**:3.1/3.2/末阶段凭文档可开工;3.3 被 F1/F3/F5 阻塞,修订后放行。
