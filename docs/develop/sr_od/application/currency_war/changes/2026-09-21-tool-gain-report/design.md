# 工具上报获得链接入(tool-gain-report)迭代设计(总纲)

> **承接出处**:`changes/2026-09-21-gain-chain/design.md`(链原语)——本批 = 链原语在
> 工具域的接入面;**依赖 = gain-chain 阶段 3.1(链原语,已落地:`kernel/cw_gain_chain.py`
> 在库)**;gain-chain 3.2 接线面(pick_invest)不含本批依赖、时序独立。
> 同期裁定:工具消耗组合壳退役(`101fb6db2`)——本批把「消费真值归观察」升格为
> 「机械执行直接上报写容器」(用户裁定 2026-09-21:动作 op 不判成败,上报无条件
> 按成功写)。

## 0. 元信息

- **迭代目标**:七工具原子动作的上报从零写占位升格为**容器写**——动作 op 机械
  执行不判成败,上报无条件写(确定面 `write_logic`;随机面 `write_logic_rand`
  采样链);装备/角色获得走统一链原语 + 触发回调(用户裁定 2026-09-21)。
- **状态**:定稿(核一无前提攻击 r1 = major 4 + minor 7 全量修订重写 v2;含用户裁定
  折叠:机械执行不判成败/投影仪三合一定谳/特权卡拖角色不支持/特权卡库存腿之外
  变异不走链)
- **文档清单**:无详设(单文档方案)

## 1. 问题与动机

### 1.1 现状症状

1. **七工具上报 = 零写占位**(`kernel/cw_action_report/zero_writes.py` 七函数):动作
   后容器零表达,消费/效果真值全靠下一帧观察;「机械执行直接上报」裁定下确定面
   效果应有逻辑写(上报无条件,不判成败)。
2. **工具确定性效果无写端**:投影仪复制进席/特权卡库存变换/扳手回区在原子通路后
   无人写(组合壳退役时效果写端分派口随撤,桥本体留守)。
3. **获得不走上报链**:投影仪复制进席直接落槽不触发「获得角色」回调与升星判断,
   与链原语统一时序(回调先、升星后、产物重进)不一致。

### 1.2 基线事实(设计前代码态核实)

- **链原语已落地**(`kernel/cw_gain_chain.py`,gain-chain 阶段 3.1):
  `gain_character`(落位/溢出 → 回调 → 3 合 1 升星判断 → 产物递归)/
  `gain_equipment`(入栏 → 回调)/`rand: bool` 必带、递归透传、中途效果可翻转
  (gain-chain 裁定③);查无效果安静不写(裁定④);未观察 = bug 面零写 + 留证
  (裁定⑤)。gain-chain 3.2(pick_invest 接线)未做,与本批无交叠文件。
- **记账载体 = `gs.equips`**:工具件(category='工具')住装备库存,观察「全量含
  工具照录」,策略器同口径——**工具消耗 = equips 多重集移除该工具名**,与效果腿
  同域,必须**单次合并写**(禁拆两笔:拆两笔 = 中间态 + 二次失配面)。
  `gs.consumables`(§3.2.16)为独立死字段(现役零读端零写端,fields.md 申报与现实
  不符),**不入本批**(字段级清偿归 fields 正本批)。
- **桥在库**(`cw_effect_inventory.py`):`transform_equip_to_privilege`(特权卡库存
  腿);`spawn_equip_bench_unit`(投影仪直落桥——本批**退役改走链**,数据拷贝仪
  计数臂仍消费、桥留守);`transform_worn_equip_to_privilege`(穿域腿,随特权卡
  拖角色不支持而留守);`grant_equip_item`(令牌,R9 判据批接)。
- **冶金炉采样池先例**:sim 侧 `cw_sim_equips.furnace_reroll` **逐字同款**(同类别
  池均匀、排除自身)——池语义单一源对齐 sim 实现(对拍锁),禁第二套口径。
  已知数据边角:简易池 8 件 vs 7 件(光能电池归属)在 game 侧待实测项在册——
  池成员资格轴(注册表 category)与该边角一并进披露键。
- **词表参数已带目标身份**(`cw_vocab.py` :571-661):冶金炉/特权卡 `target_kind` +
  `item_name`/`row`/`slot`;扳手/投影仪/令牌 `row`/`slot`。
- **发射位判据面**(`cw_equip_env.py`):特权卡只产**库存腿**(栏内拖法,进阶成品
  在手才放行)——拖角色腿从未发射;令牌 fail-closed 永不进准入(R9 判据批挂账)。
- **投影仪复制触发 3 合 1**(口述·权威 2026-09-21):复制进席 = 标准「获得角色」,
  链式时序(落位 → 回调 → 升星判断 → 产物递归)即游戏语义。席满溢出/落点 =
  链语义承接(gain-chain §2.1 已裁),非本批新裁决。

### 1.3 根因归层

语义层——工具效果(确定/随机/获得/变异)没有统一的上报写语义;症状 = 零写占位 +
孤儿桥。

### 1.4 解决到哪 / 明确不解决

**解决**:七工具上报容器写(语义表 §2.2,记账载体 = equips 合并写)+ 冶金炉采样池
(sim 同源)+ zero_writes 七函数退役 + `EQUIP_WRITE_SIDES` 词表扩展与逐行收口。

**明确不解决**:

| 项 | 排除理由 |
|---|---|
| 特权卡拖角色腿 | 用户裁定 2026-09-21:**按不能拖角色处理,候实机测试**。判据面现役只产库存腿;上报侧收到 char 腿 = fail-closed 留证 |
| 令牌判据面建模与写端 | R9 判据批挂账(发射位 fail-closed 永不准入,本批上报保持零写+留证) |
| 冶金炉变异产物是否触发获得后果 | 已由作用域白名单定谳(2026-09-21)结构性关闭:变异产物域(简易/进阶)与后果表成员(特殊/骇客)不相交,采证钩子保留为结构性不触发的哨兵 |
| `gs.consumables` 死字段清偿 | fields.md §3.2.16 申报与现实不符(零读零写)——字段级退役/修正归 fields 正本批,本批仅不消费 |
| 令牌选定四选一通道的获得记账 | 归装备选择通道(grant 锚已在该通道声明),不归拖曳上报 |
| sim 引擎接线 | 链原语与上报纯函数可复用,另批 |

## 2. 方案(完整设计)

### 2.0 总原则

- **机械执行直接上报**(用户裁定 2026-09-21):动作 op = 机械执行,**不判成败**——
  上报无条件按成功写容器(确定面 `write_logic`;随机面采样链)。「失败」不是本层
  概念:容器与实机若有出入,归观察对账机制按其契约处置,不入本设计 framing。
- **随机面**(效果含采样)走 `write_logic_rand`,产物猜错 = `logic_rand_outcome` 收口
  自愈;采样效果子链 rand=True(gain-chain 裁定③)。rand 写**吸收**工具消失的成败
  差异 = 预期自愈形态(工具还在 = 下轮判据面重评再发射,天然重试)。
- **获得走链**:工具产生的角色/装备获得一律 `gain_character`/`gain_equipment`
  (回调 + 升星判断统一时序);**变异面**(原地替换,数量不变)不走获得链、不触发
  获得回调(候采证,§1.4;采证钩子见 §2.2)。
- **两相形态**:工具无 overlay,单相——动作 op 机械链发出后直调上报(emit 即落地,
  `action_ops` §1 形态;无证据闩)。
- **记账载体合并写**:工具消耗移除与效果腿同域(`gs.equips`)时**单次合并写**,
  禁拆两笔(§1.2)。

### 2.1 文件与接口

- **新建** `kernel/cw_action_report/tool_use.py`:七上报函数,签名两形——
  六函数 `(gs, param, sig)`(与现役零写版同形,op 统一直调与命名规约冒烟锁
  逐类 `fn(gs, param, sig)` 兼容);冶金炉 `(gs, param, sig, *, rng=None)`
  (rng 关键字带缺省 = pick_invest 先例形态,None 时取模块级缺省 rng——
  七函数对 op 侧调用形态不变)。
- `zero_writes.py` 七函数退役(测试爆炸半径 = 3 个契约测试,包级 `__getattr__`
  迁移天然兼容);`EQUIP_WRITE_SIDES` 见 §2.3 词表扩展。
- 桥消费:`transform_equip_to_privilege` 本批接线(特权卡库存腿);
  `spawn_equip_bench_unit` 投影仪消费退役改走链(数据拷贝仪计数臂留守);
  `grant_equip_item`/`transform_worn_equip_to_privilege` 留守不接。

### 2.2 逐工具上报语义表(单一源)

记账载体 = `gs.equips`(工具件住库存,观察全量照录——§1.2);**消耗移除与效果
同域合并写**,无 `consumables` 参与。

| 工具腿 | 容器写(equips 合并写 = 移除工具 + 效果) | 面 | 获得链 |
|---|---|---|---|
| 冶金炉·拖装备 | **单笔 `write_logic_rand`**:equips = 移除工具 ∧ 目标件 → 同类别采样替换。**作用域白名单**(口述·权威 2026-09-21):目标限简易/进阶(特殊含银狼升星奖励专属 10 件/骇客/工具不可作用),越白名单 = fail-closed 零写 + 留证 | rand | 否(变异面) |
| 冶金炉·拖角色 | ①equips **单笔 `write_logic_rand`**:移除工具 ∧ 移除全部穿戴 ∧ 追加(白名单内穿戴件同类别采样替换 + **越白名单穿戴件保留原样**〔聚合留证;是否随动作消失未采证〕);②目标角色行域 `write_logic`(穿戴清空) | ①rand ②logic | 否(变异面) |
| 特权卡·拖装备 | **单笔 `write_logic`**:equips = 移除工具 ∧ 目标件名 → `privilege_counterpart` 替换(映射桥) | logic | 否(变异面) |
| 特权卡·拖角色 | **fail-closed**:留证行(kind=`tool_privilege_worn_unsupported`),零写 | — | — |
| 扳手 | **两笔 `write_logic`**:①equips = 移除工具 ∧ 追加目标角色全部穿戴件;②目标角色行域(穿戴清空) | logic | 否(归属迁移非获得) |
| 精密扳手 | 同扳手,**equips 不移除工具**(无限次不递减) | logic | 否 |
| 员工投影仪 | ①equips `write_logic` 移除工具;②**`gain_character(char_id, 1, rand=False, sig, evidence, producer='CwActionToolUseReport')`**,费用门(≤3)调用前置查(注册表现读),超门 = 留证行零写(防御纵深,发射位已辖) | ①logic ②链 | **是**(复制进席触发 3 合 1 = 口述·权威 2026-09-21;席满溢出/落点 = 链语义承接) |
| 完美投影仪 | 同员工投影仪,无费用门 | 同上 | **是**(同上) |
| 好运令牌 | 零写 + 留证行(kind=`tool_token_not_admitted` 注记;发射位永不准入;写端随 R9 判据批) | — | — |

- 目标身份解析:`row`/`slot` → 容器行域派生表现读单位(与执行拖点同源坐标,
  取值时机 = 上报期现读);单位缺失(未观察/漂移)= bug 面:零写 +
  `record_defect`(kind=`tool_target_unit_missing`)留证不停机(gain-chain 裁定⑤同款)。
- **冶金炉采样池 v0** = `cw_sim_equips.furnace_reroll` **同源**(同类别池均匀、
  排除被变异件自身;**作用域白名单** = 简易/进阶,口述·权威 2026-09-21——
  特殊/骇客目标与产物域均排除,银狼升星奖励专属 10 件实测与白名单零交叠;
  对拍锁钉死两实现等价);披露键
  `furnace_mutate_pool_v0_same_category` 载明:成员资格轴 = 注册表 category、
  简易池 8/7 件(光能电池)边角在册待实测。rng = pick_invest 关键字带缺省形态。
- **变异后果采证钩子**:炉采样命中 `EQUIP_ACQUIRE_CONSEQUENCES` 键集成员 →
  留证行(kind=`furnace_mutate_consequence_candidate`),供实机局判读比对
  「变异产物是否触发后果」(§1.4 采证点的采集机制)。
- 桥零写分支透传(库存未观察/无此件 → None/False):统一落证行
  (kind=`tool_bridge_zero_write`)——detail 区分因,消费真值归观察。

### 2.3 `EQUIP_WRITE_SIDES` 词表扩展与逐行收口

side 值域现封闭(`bridge:/contribution:/op:/observation`,import 校验炸)——本批
**扩展第五形 `report:<函数名>`**(写端 = 动作上报函数,`_validate_equip_write_sides`
同步校验函数在 `tool_use.py` 在册)。逐行终值:

| 行 | 现值 | 终值 |
|---|---|---|
| 冶金炉 | `observation` | `report:report_action_furnace_use_param`(rand 采样写) |
| 员工/完美投影仪 | `bridge:spawn_equip_bench_unit` + 接线候注 | `report:report_action_staff_projector_use_param` / `report:report_action_perfect_projector_use_param`(走链) |
| 特权赋予卡 | `bridge:transform_equip_to_privilege` + 接线候注 | `bridge:transform_equip_to_privilege`(库存腿桥继续消费,去接线候注) |
| 拆装扳手 | `op:CwActionSellBenchParam/RunTools...`(指已退役壳) | `report:report_action_wrench_use_param` |
| 精密拆装扳手 | 贡献算术行(获得回执窗) | 金面不变;使用面注改 `report:report_action_precision_wrench_use_param` |
| 好运令牌 | `bridge:grant_equip_item` + 接线候注 | 维持 `bridge:grant_equip_item` + 接线候注(R9,不虚报已接线) |

### 2.4 失败安全与异常粒度

沿 gain-chain §2.7:链原语零吞错;上报层 best-effort 边界 = 非容器写腿(留证行
log 失败不阻塞);`equips`/行域未观察 = bug 面零写 + 留证(裁定⑤同款)。
rand 写吸收成败差异 = 预期自愈(§2.0),不落缺陷。

### 2.5 测试面

- 逐工具写端锁(equips 合并写:消耗移除 + 效果同笔;扳手/特权卡两字段笔序);
- 冶金炉采样锁:rng 注入同种子同产物;**与 `cw_sim_equips.furnace_reroll` 对拍锁**
  (同池同输入逐次等值);后果表成员命中 → 采证行;
- 投影仪走链锁:经 `gain_character`(回调触发断言——`on_character_gained` 现役
  空集安静不写;升星判断 = 凑满三连合成);变异面**不走链**锁(冶金炉/特权卡
  不触发获得回调);
- 特权卡 char 腿 fail-closed 锁;费用门防御锁;`EQUIP_WRITE_SIDES` 新词表校验锁;
- 原子 op 行为不变回归(`test_cw_unified_action_4` 族);zero_writes 迁移契约测试
  3 处改面;L1。

### 2.6 文件面(全量)

`kernel/cw_action_report/tool_use.py`(新建)、`zero_writes.py`(七函数退役)、
`cw_tool_use_action.py`(import 切换 + 「零对拍,消费归观察」文案同步)、
`cw_affix_effects.py`(EQUIP_WRITE_SIDES 词表扩展 + 逐行终值 + 头注)、
`cw_effect_inventory.py`(spawn 桥投影仪消费退役注/穿域腿注/采证钩子协作注)、
`cw_equip_env.py`(判据面特权卡库存腿注同步)、`cw_vocab.py`(七类 docstring:
炉「rand 采样替换」/特权卡 char 腿 fail-closed/投影仪走链)、`cw_game_state.py`
(consumables 字段注释补「死字段,清偿归 fields 正本批」指针)、
`kernel/cw_projection_audit.py`(equips 审计行 basis 工具写端注);
正本:`fields.md` §3.2.15/§3.2.16、`flow/action_ops.md` §4.5 七工具行;
`sr-od-test/` 对应测试。

### 2.7 关键取舍

| 取舍点 | 选定 | 放弃 | why |
|---|---|---|---|
| 记账载体 | `gs.equips` 合并写 | `gs.consumables` −1 | 工具件实住 equips(观察/策略同口径),consumables = 零读零写死字段(攻击 r1-F1/F2);合并单笔禁中间态 |
| 机械执行直接上报 | 确定面无条件 write_logic | 上报前判断成败/写前验证 | 动作 op = 机械执行不判成败(用户裁定 2026-09-21);成败判断 = 对拍复辟(裁决 3 已废) |
| rand 吸收 | 炉 rand 写吸收成败差异(自愈) | rand 腿建失败留证 | 失败不是本层概念;工具未消耗 = 下轮判据重评再发射 = 天然重试 |
| 获得走链 | 投影仪经 `gain_character` | 复用 `spawn_equip_bench_unit` 直落 | 链统一时序(回调/升星/溢出),直落 = 双时序第三例(跨件半问);三合一有定谳 |
| 变异不走链 | 冶金炉/特权卡 = 变异面直写 | 变异也走 `gain_equipment` | 变异非获得(数量不变);产物后果未采证,链回调会引入未证行为——采证钩子补观测 |
| 特权卡拖角色 | fail-closed 不支持 | 采样实现穿域腿 | 用户裁定候实机;桥留守,实机证可拖即升格 |
| 令牌零写 | 维持 | 最小 grant 实现 | 发射位永不准入,写端无触发源;R9 判据批一并 |
| 文件形态 | 七函数同住 `tool_use.py` | 每动作一文件×7 | 一族一文件(pick_equip 先例);机械半同构,拆七份 = 形式主义 |
| 采样池单一源 | 对齐 sim `furnace_reroll` + 对拍锁 | 上报层独立定义池 | 攻击 r1-F5:同款先例在库,禁第二套口径;8/7 件边角进披露键 |
