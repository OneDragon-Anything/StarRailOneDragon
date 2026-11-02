# 完成品保护档 落地

## 完成前常规检查(各阶段完成判据引用本节,不复述)

- `uv run ruff check` 对本阶段改动文件全部通过;
- 本阶段直接受影响测试全量一次通过(`uv run pytest sr-od-test/ -m "not slow"` 相关子集;排序核心阶段跑 CW L1 全量);
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交;
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号;提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 排序核心:十档重排 + 单帧测试

**范围**:`criteria/priority.py::sort_key` 按 design §2.2 十档判定表重排(保留张谓词 `is_kept_unit` 新增〔含 ShopUnit 排除支〕、档 4 完成品插入、原档 5 语义保留仅编号位移 5→7、档号位移);锁定帧 `need_star_by_member` 装配补全(design §2.5-1);`interest_exempt_member` 与模块头/docstring/运行时日志与告警文案的档号表述跟改(逻辑不动,仅表述);`test_priority.py` 逐档断言重写 + 旋转门同型新测试。
**边界**:不含消费面测试跟改(3.2)、不含观测/文档面(3.3)。
**设计依据**:design.md §2.1/§2.2/§2.3/§2.4/§2.5。
**文件面**:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/priority.py`;`sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/test_priority.py`。
**依赖**:无。
**优先级建议**:0
**完成判据**:
- 十档逐档断言通过;落档边界五例(design §2.3)逐条有断言(含锁定帧与未锁定帧分帧断言、2★ 直出候选非保留张断言);旋转门同型帧(达标 2★ 席满让位非 victim)断言通过;
- **CW L1 判读口径(预期红集)**:本阶段十档重排会使 design §2.6 测试清单 3.2 面(九个消费面测试文件)的档号/键名断言按预期变红——逐条登记红集后放行,**红集必须与 §2.6 清单文件吻合(清单外文件变红 = 实现问题,停手)**;除清单文件外全绿;L1 全绿在 3.2 完成后达成;
- design §2.4 不变式逐条自检(兜底谓词零改动/凑息豁免逻辑不动/单一源/零新数值);
- 完成前常规检查(本文首节;L1 判读按本条预期红集口径;test_priority.py 本身全绿)。
**验收凭据形式**:测试名(test_priority.py 各用例)+ ruff 通过。

## 3.2 消费面测试跟改

**范围**:design §2.6 测试清单中 3.1 之外的九个测试文件档号/语义断言跟改;改测试 = 重推语义(引 design 对应节),禁机械跟绿。
**边界**:不新增测试文件;不含 src 代码改动(若跟改中发现实现与 design 不符 = 停手回 3.1)。
**设计依据**:design.md §2.2/§2.3/§2.5。
**文件面**:`sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/test_sell_candidates.py`;`sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/shop/test_acquire_yield.py`;`sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/test_shop_session_loop.py`;`sr-od-test/test/sr_od/application/currency_war/operations/cw_screen/test_prep_pipeline.py`;`sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/supply/test_decide.py`;`sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/test_supply.py`;`sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/test_no_target_three_arms.py`;`sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/test_protection.py`;`sr-od-test/test/sr_od/application/currency_war/kernel/test_cw_comps.py`。
**依赖**:3.1。
**优先级建议**:1
**完成判据**:
- 上述测试全量一次通过;每处改动的 docstring/注释引 design 章节;
- 完成前常规检查(本文首节)。
**验收凭据形式**:测试通过记录。

## 3.3 观测与注释面

**范围**:观测键域注释与档号引用注释面——design §2.6 代码清单除 priority.py(3.1 已含)外的全部非锚类注释消费位:schema.py 键表节、shop.py 头注与 :825/:856/:859/:1115、sell_candidates.py :35/:128/:240/:443、predicates.py :9/:83、supply.py :164、protection.py :9/:41/:47-48、criteria/sell.py :103/:237、cw_comps.py :247/:315、cw_intention.py :1294、cw_chars.py :44。
**边界**:不动任何运行逻辑;键生成代码零改动(动态格式化已覆盖,design §2.5-7);不含正本文档(归末阶段);**priority-model § 锚改指(cw_comps.py:248、sell_candidates.py:10-11/:246/:359、sell.py:185/:297、priority.py 模块头)统一归正本阶段——32 号稿须先存在,3.3 工人 grep 命中 priority-model 时按本边界跳过并留待正本阶段,禁自行改指**。
**设计依据**:design.md §2.5/§2.6。
**文件面**:`src/sr_od/application/currency_war/telemetry/schema.py`;`src/sr_od/application/currency_war/strategies/impl/mandate_v1/shop.py`;`src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/sell_candidates.py`;`src/sr_od/application/currency_war/strategies/impl/mandate_v1/statefn/predicates.py`;`src/sr_od/application/currency_war/strategies/impl/mandate_v1/supply.py`;`src/sr_od/application/currency_war/strategies/impl/mandate_v1/protection.py`;`src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/sell.py`;`src/sr_od/application/currency_war/kernel/cw_comps.py`;`src/sr_od/application/currency_war/kernel/cw_intention.py`;`src/sr_od/application/currency_war/data/cw_chars.py`。
**依赖**:3.1。
**优先级建议**:2
**完成判据**:
- 在役注释面旧口径清零:判定标准 = 引用语义对应现行十档编号;辅助 grep 模式「档 2/3/5」「档 8 已完成资产」「tier_<1..8>」「八档」「档 6」「档 7」在上述在役文件按语义复核清零(**显式排除**:①`schema.py` 停产键族段的历史墓碑——退役键名是键名史,禁改写;②「priority-model」锚命中——按本节边界统一归正本阶段;③新表合法命中〔档 6 = 压牌库、档 7 = 凑两星〕按语义排除);
- 完成前常规检查(本文首节;ruff)。
**验收凭据形式**:grep 清零记录(含排除段说明)+ ruff。

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新。
**设计依据**:本文件「正本更新清单」节。
**文件面**:清单所列文档。
**依赖**:3.1-3.3 全部。
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致。
**验收凭据形式**:文档对照 review。

## 正本更新清单

> 「←」语义 = 导致阶段(iteration-design §3.2);标注「执行时点 = 末阶段」的行,其锚改指须待本阶段内 32 号稿建成后再动,禁提前指向不存在的正本。

- `strategy-docs/32_unified_sell_priority.md`(新建):十档判定规格正本,**范围 = design §2.1-§2.3 as-built 化 + 上一迭代 priority-model 现行有效内容收编:§1(PriorityContext 输入契约/确定性约束)、§2 幸存语义(成员名单两态/配方支判窗/need_star 两态取值按 design §2.5-1 新口径/无表项缺省规则/聚合口径——凡未被新判定表取代者照录)、§3 非表行口径(兜底档概率分档口径注与序数键取值规则——凡未被新判定表表列承载者照录)、§4(随机流实例)、§5(卖出取用形态与池子)**(§6 退役史不迁)——判定表只迁一半会让 §1/§2/§3/§4/§5 的代码引用死亡(design §2.6 正本段)← 3.1
- `src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/priority.py`:模块头规格锚 `priority-model` → 32 号稿;docstring 残留 §X 引用清零 ← 3.1(执行时点 = 末阶段,32 号稿先建)
- `src/sr_od/application/currency_war/kernel/cw_comps.py`:`:248` 规格锚 → 32 号稿 ← 3.3(执行时点 = 末阶段)
- `src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/sell_candidates.py`:`:10-11` 同行双锚**分账改指**:`priority-model §5` → 32 号稿;`acquisition-and-sell §3` → 11 号稿 §4.0(该收编范围不含 acquisition 篇,禁整行改指吞锚);`:246`/`:359` 规格锚 → 32 号稿 ← 3.3(执行时点 = 末阶段)
- `src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/sell.py`:`:185`/:297 规格锚 → 32 号稿 + **同行「档 7」→「档 9」表述跟改**(锚与档号同句,一并处置,防 3.3 禁改面残留旧档号)← 3.3(执行时点 = 末阶段)
- `strategy-docs/11_shop_decisions.md`:§4.0 补完成品保护语义句;§1 表(:14「受统一价值序档 6 保护」句含内)档号全量同步(:109/:117/:121/:163/:164/:170);**:109「单一源 = 代码函数体,正本不另抄逐档谓词表」声明改写为「判定表正本 = 32 号稿,函数体为实现」**(否则与 32 号稿正本化互斥,XT-2 变体)← 3.1
- `strategy-docs/01_math_framework.md`:七面判据表(:58-59 卖出排序行/骨架件行)与凑钱触发行(:61「档 8 概率分档」)档号同步;**:58「八档判定与档内键的单一源 = 代码函数体」声明同款改写为「判定表正本 = 32 号稿」** ← 3.1
- `strategy-docs/12_line_and_intention.md`::29 义务面括注(「档 2/3/5 名单同源」与「档 6 保护」两句)、:88「档 2/3/5 承载买入与保留」← 3.3
- `strategy-docs/30_supply_screen.md`::34(「档 8 概率分量/档 4 压牌库带」)、:46(「现行承载 = 档 2」「档 1 保护」)、:47(「档 8 键无聚合星级分量」)、:69(「聚合谓词档 2/5/6/7」)按十档跟改 ← 正本阶段。**说明**:30 号稿该四处现为姊妹迭代 supply-unified(已收口)落地的旧档号文本,本批末阶段改写时一并按十档复核其语义;XT-2(逐档表正本落点缺位)清定**归属本批**(32 号稿即其治本解),supply-unified 稿的同项以本批为准
- `strategy-docs/README.md`:§2 分篇表补 32 号稿行(正本入口可达性)← 正本阶段
- `changes/2026-10-29-unified-priority/details/priority-model.md`:**不修改**,随 changes 寿命自然退役(代码锚已改指 32 号稿;本行登记 = 退役声明,防后来者续修死亡文件)← 本迭代裁定(design §2.6)
