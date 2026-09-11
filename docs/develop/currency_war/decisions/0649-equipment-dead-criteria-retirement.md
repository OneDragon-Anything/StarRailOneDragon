# ADR-0649: equipment 三死判据面退役除名(wear_release/keep_policy/endgame_context)

- 状态:accepted(2026-09-11)
- 背靠:T-298-规范验收发现 F2(criteria 三判据面零生产消费位却活体注册);T-302 诊断定谳段交付报告(`.debug/temp/currency_war/T-302-交付报告.md` r2 修订版)+方案对抗审(`reviews/T-302-方案对抗审.md`,阻断-1/低-1/2/3/信息-1 全采纳);ADR-0644 §2(D-* 修复池编号解析单一源,本件取代其中 criteria/equipment 落点行,见「关联」);18 号稿/ADR-0526(kernel 五行释放判据表)、21 号稿/ADR-0531(row3 并入 O1)、01_math_framework §3.6(P42 ③ 命题在册)、affix_allocation 墓碑先例(判据出处纠错批)
- 落点:`strategies/impl/mandate_v1/criteria/equipment.py`(三函数物理删除,模块 docstring 墓碑化)、`criteria/__init__.py` BYPASS_TABLE 三行墓碑注、`criteria/contracts.py` CONTRACTS 三行墓碑注、`mandate.py` M7 注释消费锚修正、19 号稿 :14/:32/:92 语义改写、测试树删 `TestBossNodeRelease` 整类;零行为语义变更(删零调用死码 + 修正注释/文档引用)

## 1. 背景与定谳

三判据面(`wear_release` 修复池 D-B/`keep_policy` P42 ③/`endgame_context` 修复池 D-P3)生于换核批1(ba1176c68),以占位形态随批入库;三面统一定谳 = **退役除名**,处置形态仿同表 affix_allocation 墓碑先例(物理删函数 + BYPASS_TABLE/CONTRACTS 行改墓碑注)。共同事实基座:

1. **自入库首日起生产调用点为零**(git 全史 3 commit 覆盖文件全程 + 今日 AST 全树 Call 节点双形态扫描 = 0);mandate.py 的「D-B 释放门 = criteria/equipment.wear_release 消费」注释从未兑现——生产链 = kernel `cw_equip_env.resolve_wear_release` 五行表(prep_actions 分发段实调,18 号稿/ADR-0526)。
2. **wear_release**:问题域已被 18 号稿五行表 + 21 号稿 O1 完整接管且更精细(逐件 `classify_item_hold`);玩法口述·权威「无用简易不穿着、囤装备栏」与占位 ①支方向相反,占位不仅无用、复活反而是错的。
3. **keep_policy**:命题 P42 ③ 在册已证(01_math_framework §3.6),但生产落码载体缺位(kernel `classify_item_hold` 无兑现距离维度);占位对 d*>1 默认返回「喂」,与命题「默认保留不喂」**方向相反**且缺「P3 boss 掉落流终止冗余件开放」唯一例外——禁作命题种子复用。
4. **endgame_context**:`r_remaining <= 3` 系未证拍定值(无【注】【推】【拟】三形态标注),按数学先行门「无标注数字不得进决策门」作废;修复池项 D-P3 本身 OPEN 挂账不变(定谳手段 = 实机 boss 掉血分布对拍,从未执行),未来落码必须从对拍数据重新推导,不复用 3。

## 2. Decision

1. 三函数物理删除;equipment.py 收敛为墓碑模块(三面各记退役缘由+现行落点+复活条件)。
2. BYPASS_TABLE/CONTRACTS 三行保留改墓碑注(仿 affix_allocation 先例:零调用面墓碑 + 现行单一源指针 + 「目录行保留旁路枚举完备性」);keep_policy 两处墓碑注均写明反向事实禁种子注。
3. mandate.py M7 注释消费锚改指实际链路(kernel `resolve_wear_release` 判据表,prep_actions 分发段计划产出位消费,ADR-0526/0601)。
4. 19 号稿 :14/:32/:92 三处按 **语义改写**(非指针替换)落 kernel 真实语义:判据 = `resolve_wear_release` row3(row1 否定支,仅辖 P1 r≤2 扣留窗口的战斗类节点释放)+ O1 战斗前置门;r≥3 帧无扣留,硬节点释放系「无扣留默认」承载;词汇表 = 注册表单一源 `opening_hold_battle_nodes`(cw_registry.py,frozenset({'战斗','boss','遭遇','精英'}) 四 OCR 标签)——与已删占位 ③支 的 HARD_NODE_TYPES(criteria/refresh.py,{'encounter','boss'} 英文 token,'encounter' 不在生产 node_type 词汇表)双重不同源,「与 HARD_NODE_TYPES 同源」从句随函数退役删除;「已落行为位/零金结构判据/不动」结论保留(硬节点装备穿戴确在产)。:4 判据源行系历史溯源注,留史不动(指针悬空由两表墓碑注自会重定向)。
5. 测试树删 `TestBossNodeRelease` 整类 + `crit_equip` 导入 + 节头注释:被锁语义已由 kernel 表取代(出处链 18 号稿/ADR-0526/0531 齐备),锁的存在性纪律「语义已被取代的锁走删除」;kernel row3/O1 行为已有 test_cw_opening_hold/test_cw_equip/test_cw_opening_tool_semantics 多把现役锁覆盖,无覆盖缺口。
6. 01_math_framework §3.6 不动(退役的是死函数,不是命题)。

## 3. Considered Options

- **退役除名(采纳)**:三面考古账齐备(零调用 git+AST 双证、语义后继在册、命题与占位反向),删除严格更安全。
- **挂激活义务(否决)**:对 wear_release 无意义(问题域已被接管,D-B 定谳已由 18 号稿完成);对 keep_policy 现行架构无「组件定向喂件」决策位,激活义务无处落地;对 endgame_context 已有 OPEN 挂账,不缺义务缺定谳数据。
- **保留修正标注(否决)**:死码留树持续制造「已接线」假象——19 号稿三处「唯一已落行为差的补强落点」误引即实证,标注挡不住再次误引。

## 4. Consequences

- criteria 六面注册表三行由「活体登记」转「墓碑登记」,消费面读者按墓碑注直达 kernel 单一源;CONTRACTS 完备性锁为「函数→行」单向动态枚举,删函数留行恒绿,零锁险。
- **对 ADR-0644 §2 的取代关系申报**:ADR-0644 §2「D-* 修复池编号」映射行原文「各项现行落点=mandate_v1 各实现本体(criteria/equipment、criteria/refresh、criteria/levelup 等)与 18 号稿」——对 D-B/D-P3 两项,本 ADR 取代该行中的 **criteria/equipment** 落点(D-B 现行落点 = 18 号稿/kernel 释放判据链;D-P3 = OPEN 挂账无代码载体);ADR-0644 正文 immutable 不回改,取代关系由本件承载。
- **存量漂移随批申报(信息-1,非本批引入)**:criteria/__init__.py 模块 docstring 自称 BYPASS_TABLE 是「旁路枚举对拍测试的单一源」,与测试树对该表零消费的现实漂移(对拍测试已不在树);本批墓碑行沿用先例措辞「旁路枚举完备性」与先例一致,该 docstring 自称是否另批处置由编排者裁。
- 19 号稿 :4 留史注保留;predicates.py:47「wear_release 通道」措辞退役后单指 kernel 生锈豁免通道,经对抗审核验无歧义,不改。

## 5. 验证

- 涉改测试亲跑:test_cw_mandate_decide.py(删锁后余锁绿)+ test_cw_contracts.py(完备性锁动态构造自洽)。
- 全 src/sr-od-test 消费面 grep 复核:三函数符号仅存于定义本体(已删)/两表墓碑行/kernel 同名异符号 `resolve_wear_release`/注释,零调用点。
- ruff 本工文件净;点名域快速集(currency_war not slow 抽验)零新增红。
