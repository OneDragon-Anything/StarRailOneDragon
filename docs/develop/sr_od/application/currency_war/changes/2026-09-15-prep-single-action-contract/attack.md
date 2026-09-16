# 对抗审查报告:备战契约接口收口为单动作(2026-09-15-prep-single-action-contract)

- 审查对象:本目录 README.md / design.md / landing.md(迭代设计);`src/sr_od/application/currency_war/strategies/impl/cw_strategy.py::CwStrategy.decide_prep_screen` docstring as-built 改写(工作区 diff);`docs/develop/sr_od/application/currency_war/strategy-docs/README.md` §3「策略↔流程契约」指针行(「17 接口、序列语义」→「契约成员 13、单动作循环;序列语义为历史注」,工作区 diff)。
- 方法:无前提三核(边界完整性 / 规范遵循 / 治本)。全部数值、口径、引文、码点直调复核,未采信任何转述;行号以当前工作区实态为准。
- 结论:**9 项发现(中 4 / 低 5),无高危**。设计的根因归层、None 通道论证、行为零变化论证、测试影响面盘点均经直调证实成立;发现集中在「取舍论据的代码计数失真」「改写规格的精密度缺口」「正本更新清单完整性」「测试出处指针切换归属」。

## 1. 发现清单

### F1 [中] 取舍论据代码主张失真:「mandate.py 4 处调用点」

- 位置:design.md §2.3 理由 2、§3 备选 B 弃因。
- 主张原文:「直调:`truncate_frame_stable` / `classify_frame_stability` 在 mandate.py 4 处调用点」。
- 直调结果:`mandate.py` 内 `truncate_frame_stable` **零调用**(L1299 仅注释提及「truncate_frame_stable 其后必截」);`classify_frame_stability` 真实调用 **1 处**(L1965;L1960 为 import,L1753/L1956 为注释)。「4 处」的真实构成是 mandate_v1 包内三文件的调用合计:bridge.py L290(truncate,decide_from_turn 截断)、entry.py L297 与 L1157(classify 内部消费)、mandate.py L1965(classify)。
- 影响:理由 2 是「决策核是否一并单动作化」(备选 B)的弃选论据,计数与归属失真会动摇取舍评估的可信度(数值/码点直调禁转述,本条即转述失真样本)。
- 修正方向:改述为「帧稳定分类在 mandate_v1 包内 4 处真实调用(bridge 截断发射、entry 内部两处、mandate.py M7 发射序回排一处),另有 mandate.py L1299/L1753 截断点语义耦合申报」。取舍结论本身不变(耦合实证仍在)。

### F2 [中] §2.2 改写后代码块缺 try/except 异常包装,「零变化」清单未含该段

- 位置:design.md §2.2;landing.md §3.1 完成判据「签名/消费端代码形状与 §2.2/§2.3 代码块一致」。
- 事实:两处决策循环的决策调用均有异常包装(cw_screen_prep.py L2028-2032、L2233-2237):`try: decide_prep_screen(...) except: round_fail('策略决策异常: …')`(注释:策略异常 = 本轮 fail,外循环 retry 链兜)。§2.2 的 after 代码块无此包装,「其余段…零变化」的枚举(F3 validate/期望态记账/执行/终结判定/逻辑态直写/段序号置位)也未列该段。
- 影响:按码块字面落码 = 删除该防线,策略异常从具名 round_fail(交外循环 retry 链)变为 op 异常上抛 = **行为变更**;且「代码形状与码块一致」的验收判据反向鼓励字面执行。另:新 F3 守卫的 log.warning 文案未指定(仅 status 串已指定)。
- 修正方向:§2.2 明示「决策调用的 try/except 与 warning 行原样保留,仅 F3 分支 status/warning 文案随新形状改写(如『策略输出非 CwAction|None』)」,并把该段列入零变化清单;顺带指定被替换分支的相邻注释处理——L2038-2040 / L2244-2245「空批合法(契约 §4…)」注释中的「契约 §4」指向已灭失的契约工作副本(entry.py L17-18 佐证),L2211 lifecycle docstring「终结出口语义 = 空批/…」同批收敛,避免残留死口径。

### F3 [中] landing 正本更新清单漏项 + 指向含糊,「清单清零」≠「正本与实现一致」

- 位置:landing.md「正本更新清单」。
- 直调:对 docs/develop/sr_od/application/currency_war/ 全树 grep「取首项 / 空批 / list[PrepAction]」,post-change stale 点 ≥9 处,清单只挂 4 个文件节。漏项/含糊逐条:
  - (a) `screens/op-layer.md` L21 分域表述句「None/空批通道不表达控制流(备战域空批 = …)」——正是 design §2.1 依据 1 **自引**的那句,收口后「空批」措辞过期;清单条目只引了 L14 代码注释。
  - (b) `screens/prep.md` L53「空批 / overlay 交回 / 访问动作数达上限…均合法交回」未挂。
  - (c) `screens/prep.md` §2 的真实 stale 句在 L15 末尾(「输出 `list[PrepAction]`——单动作循环取首项消费」);清单写「§2 决策循环形态句」,按字面指向 L13 形态句——该句无形状表述、无需改,实现者会扑空。
  - (d) `flow/README.md` §2.2 L64 语义列「空序列合法 = 本帧无动作」;清单括注只写「输入/返回列」。
  - (e)「取首项」选序点迁移进 bridge 后全部过期的表述,均未挂:flow/README.md L23 架构头注「…单动作循环逐帧取首项」、flow/projection_contract.md L90、flow/action_exec.md §3 L28「决策取首项」、screens/README.md L130「备战空批(无动作)|合法交回|空序列合法…」、strategy-docs/22_prep_screen.md L8「单动作循环逐帧取首项」。
- 影响:3.3 的验收 = 清单清零;按现清单清零后正本仍留至少 5 处与实现矛盾的旧口径,迭代收尾义务(正本与实现一致)不达成。
- 修正方向:清单逐条细化到「文件:节:句」粒度并补齐 (a)-(e);flow/README §2.2 序列语义历史注(L77-82)保持不动是对的,无需列入。

### F4 [中] 测试 docstring 出处指针「design.md §2.1 → flow/README §2.2」切换无阶段归属

- 位置:landing.md §3.2 完成判据 vs §3.3 范围。
- 事实:3.2 判据「新锁绿且 docstring 引设计出处(design.md §2.1;正本化后 = flow/README §2.2)」只是括注意图:3.2 验收时 flow/README §2.2 还是旧口径(3.3 才更新),锁只能引 changes/ 内的 design.md;而 3.3 范围与文件面只含「清单所列正本文档」,不含测试文件。
- 影响:按现有判据走完迭代,测试 docstring 将长期引用 `changes/2026-09-15-prep-single-action-contract/design.md`——违反 AGENTS「代码与正本文档禁引 changes/ 内容(长期引用)」铁律,且 changes/ 不定期删减后引用死亡。两阶段判据都没回答「谁在何时切换指针」= 实现者需自行拍板(硬规则 2 卡点)。
- 修正方向:二选一——① 3.3 范围/文件面扩展「测试 docstring 出处指针 design.md §2.1 → flow/README.md §2.2」;② 3.2 判据直接写死「docstring 引 flow/README.md §2.2」,3.3 完成判据加「锁 docstring 指针复验」。

### F5 [低] 状态字段不同步

- 位置:design.md §0「状态:草案」vs README「迭代设计:对抗审中」。iteration-design §2.1 状态域 = 草案→对抗审中→定稿,已进入对抗即应前移。
- 修正:design §0 同步「对抗审中」。

### F6 [低] design §1 过程叙事 + 与 3.1 ① 交叉易误读

- 位置:design.md §1「基类 docstring 的序列契约口径漂移已在本迭代前置批修复(同日提交,勿在本迭代重复处理)」。
- 事实:「前置批/同日提交」属 iteration-design 硬规则 3 禁的过程叙事(上稿改了什么);且 landing 3.1 ① 本来就要再改写同一 docstring(新契约语义),单读 §1 的「勿在本迭代重复处理」易被误判为「docstring 本迭代不动」。
- 修正:改纯范围声明,如「基类 docstring 现行文本已是 as-built 口径;3.1 ① 的改写 = 新契约语义,非口径修复的重复处理」。

### F7 [低] §2.4「replay_to_md.py 渲染商店驱动器记录」表述失真

- 位置:design.md §2.4 第三条。
- 直调:`tools/cw/replay_to_md.py` 头注(L16-17)与主体(L536、L1370)按 decisions 帧渲染**备战/商店/补给三类 op**(「OpenShop…CloseShop 段 = 商店访问 op,其余备战动作按逻辑态终结规则切备战 op」),并非只渲染商店驱动器记录。结论「不触备战契约接口、对 replay 逐位无感」不受影响(渲染读记录流,不调接口)。
- 修正:改述为「渲染 decisions 记录流,不调用备战契约接口」。

### F8 [低] 行为零变化声明未注记判读面文案变化

- 位置:design.md §2.6;关联 §2.2 after 块。
- 事实:空批分支 round_success detail 两处将由「空批(本帧无动作),交回外循环重观察」变为「本帧无动作,交回外循环重观察」。已核:无工具/测试/哨兵 grep 该文案(sr-od-test 与 tools/ 零命中),纯 journal 判读观感;但烟雾判读者会把新文案形态当陌生条目。
- 修正:§2.6 补一行「空批 detail 措辞变化属预期」申报,判读锚点不因此记异常。

### F9 [低] landing 完成判据复述通用工程门

- 位置:landing.md §3.1/§3.2 完成判据(ruff/MCP 重启/L1 内联复述)。iteration-design §3.1 模板要求「§12 通用工程门(引用,不复述)」。内容无错,形式偏差。
- 修正:改引用。

## 2. 核验通过面(直调记录,零发现)

### 2.1 设计稿引文与正本转述(逐条对原文)

- op-layer §1.1 L21 分域表述、§1.4 L37 恒可用终结(备战 = 开战)、§1.3 L31 守卫断言、§4 L153「cw_replay --diff 只重放商店决策面」——均存在,design.md §2.1/§2.2/§2.4 的转述准确(§2.1 依据 1 为近乎逐字引用)。
- flow/README §2.2:契约成员 13(L40「抽象 12 + 工厂 1 = 保留总成员 13」、L84 同)——design §2.1 契约成员数主张与 strategy-docs README 指针行均一致;与代码实态一致(cw_strategy.py abstract 12 = create_session + 11 决策入口,create_state 非 abstract)。指针行「单动作循环」对应 flow README L6 头注、「序列语义为历史注」对应 L77——**指针修改(旧「17 接口」为过期口径)属实且修正正确,零发现**。
- flow README §2.3 L91「sim 消费面注记」、§2.4 L97「归因域限定」——design §2.4 的 sim 不可见主张转述准确。

### 2.2 消费端代码(cw_screen_prep.py)

- 两处决策循环实测 L2025-2043(主循环)与 L2229-2248(lifecycle_decision_cycle),decide 调用点 L2029 / L2234 与 design §1「~L2029/~L2234」吻合;两处同构、每帧 `actions[0]`、空批 `round_success('空批(本帧无动作)…', wait=1.0)`、F3 形状校验 `not isinstance(list) or not all(isinstance(a, CwAction))`——design §2.2 before 代码块与实码逐行吻合。
- None 语义等价主张成立:现空批分支 = round_success 交回外循环、连续空批 stall 兜底归外循环(L2040/L2245 注释),与拟 None 分支逐一等价。
- `CwAction` 为真实类(cw_vocab.py L360 `class CwAction`),`isinstance(result, CwAction)` 运行时可行(现行守卫已同型消费)。

### 2.3 mandate_v1 边界与决策核

- bridge.decide_prep_screen(L107-130):读 `session.prep_obs_frame`、None 抛 ValueError、`_consume_prep_direction_frame`、`_assemble_turn`、`decide_from_turn(obs, turn, session, config, registry=self.registry)` 返回 list——design §2.3「决策核调用不变、边界取首项」的前提全部实证;`decide_from_turn` 签名/返回 L259-262。
- 「emit ⑥ 空则补 StartBattle ⇒ 恒不返回空」:entry.py L936 注释、L943-944 `if not out: out.append(Emitted(StartBattle(), …))` 实证。结构边界备注:truncate 首动作分类为 unknown 时可返回空,但 prep 域可发射词表 17 类全被四分类元组覆盖(CW_ACTION_TYPES 22 类中 BuyCard/LevelUpShop/RefreshShop/CloseShop/OpenBookcard 五类 prep 链不产出),现行为不可达;拟改 bridge 的 `else None` 分支对该边处理正确——恒非空主张在「现状可达行为」语义下成立。
- `_merge_ev_before_frame_end`(L903)与 R197 症1 语义注释(L25-35、L814-817)在;flow.py L32-35「decide_prep_screen 保持 abstract」实证 design「flow 中间 ABC 不实现」。
- session 黑板字段:`prep_obs_frame`(cw_strategy_session.py L206)、`prep_frame_class`(L221)在;`cw4_counters` 的 `prep_*`/`emitter_*` 分键在(entry.py 多处写点)——§2.6 判读锚点 2 的键面真实存在。

### 2.4 测试影响面(§2.5 主张逐项实证)

- sr-od-test 全仓 grep `decide_prep_screen`:仅 test_cw_p2_blood_band.py L246 `def decide_prep_screen(self, *a, **kw)` 桩(形状免疫),与设计主张一致。
- 全仓无 `list[CwAction]`/`非 list`/`actions[0]` 断言,无「空批/策略输出非」文案锁——「在册锁零更新义务」成立。

### 2.5 docstring as-built 审计(cw_strategy.py L121-144,逐句对代码)

十句主张全部属实:①返回 list + 现行消费逐帧取首项 ✓;②输入 = session.prep_obs_frame、跨步状态(defer 计数/意向状态机)同 session(cw4_counters 挂 strategy_state)✓;③两处决策循环同构 ✓;④列表 = 决策核三遍编排发射组织、尾部动作生产不消费 ✓;⑤空序列合法 + stall 兜底归外循环 ✓;⑥画面转移走 OpenShop/StartBattle 终结 ✓(action_exec §1/prep.md §5);⑦已退役语义 + flow/action_exec.md §2(执行契约无成败回执)/§3(无 fail-stop/恢复原语)指针真实且内容吻合 ✓;⑧帧稳定分类在决策核内辖发射组织 ✓;⑨生命周期机制四件(action_key/执行失败记忆/stall 门/强制出战)归流程侧,与 flow §2.2 L82 同清单 ✓;⑩观察帧缺失即抛错(bridge L121-125 抛 ValueError)✓。注释规范(AGENTS §8):引用均为持久索引(文件:节/符号名),无 W 轮次号/rN/批N 类会话局部标识符——合规。

### 2.6 治本三核

- 归层:形状(list)-消费(单动作)错位实证存在,根在表示层——成立。§2 改契约面形状 = 修根,非症状。
- 同族半问:序列遗留的最后一个消费面(商店已合规、pick 族已合规、备战唯一遗留,均实证),非逐件症状补丁链。
- None 通道三点依据:①op-layer §1.1 分域表述 verbatim ✓;②恒非空(§2.3)✓;③26_battle_settlement.md 存在 + op-layer §1.4「备战 = 开战」辖制 ✓。B4 条款在库两处(flow/README L58、cw_strategy.py L111)且语义(第三方兼容/缺省 None)与 design 引用方式一致。备选 A/B/C/D 论证除 F1 计数失真外成立;备选 D 弃因(分域表述冲突 + 第三方等待表达力)与正本一致。
- 第三方兼容面:注册面封闭集 = {mandate_v1}(flow §2.1 L47)实证,「不做静默兼容垫片、响亮暴露」与 op-layer §1.3 守卫断言一致。
- 规范遵循面:文档构成四节齐(无详设已在 §0 声明,README 相应无详设行)、阶段小节七件齐(3.1/3.2/3.3)、依据就地标注总体到位;违例已列 F5/F6/F9。

## 3. 攻击面清单(实际攻击过的面)

| 面 | 直调码点/文档 |
|---|---|
| 设计稿引文真实性 | op-layer §1.1/§1.3/§1.4/§4;flow/README §2.1-§2.5;action_exec §1-§3;prep.md §2/§4/§5;screens/README L130;strategy-docs/22 L8;strategy-docs/README §3 |
| 指针行修改(对象 3) | strategy-docs/README L52 diff ↔ flow/README §2.2 L40/L84 ↔ cw_strategy.py 成员计数 |
| 消费端形状与行号 | cw_screen_prep.py L2025-2043、L2229-2248、L2211、L2038-2040/L2244-2245 |
| 契约签名与成员数 | cw_strategy.py L97-204(create_session/create_state/11 决策入口);cw_vocab.py L360/L834-843 |
| mandate_v1 边界与恒非空 | bridge.py L107-130、L259-291;entry.py L8-35、L200-217、L241-331、L432-446、L903、L936-946、L1157;mandate.py L1299/L1753/L1956/L1960/L1965;flow.py L32-35 |
| None 通道依据链 | op-layer L21/L37;26_battle_settlement.md 存在性;B4 条款(flow/README L58、cw_strategy.py L111);CW_ACTION_TYPES 覆盖核算 |
| sim/replay 可观测面 | flow/README §2.3/§2.4;op-layer §4;tools/cw/replay_to_md.py L16-17/L536/L1370 |
| 测试与锁影响面 | sr-od-test 全仓 grep(decide_prep_screen/list 形状/空批文案);test_cw_p2_blood_band.py L239-249 |
| docstring as-built(对象 2) | cw_strategy.py L121-144 diff ↔ 上述全部码点 |
| 迭代规范遵循 | iteration-design.md §1-§7(四节/七件/硬规则三条);AGENTS §8 注释规范、§9 文档规范(changes/ 引用铁律) |
