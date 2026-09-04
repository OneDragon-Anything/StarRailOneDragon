# ADR-0456: 刷新费基价模型(徽标退役出决策链)+ 安灯「计划≠尝试」三态分流

> **【版本界碑（2026-09-04 存量 review 恢复件）】**本件在 3311c453 存量 review 删除后因活引用恢复（strategy-docs 01 §6【注·对拍定谳】与 10 §2.1 引 ADR-0456）；恢复后亲验对象仍活（`cw_state.REFRESH_COST_BASE = 2` 在档，obs/kernel/mandate_v1 消费链现行），正常在档。对象若后续属已亡栈则按界碑读。

> **【勘误(2026-08-30,W590 对抗审计后)】**三定谳核心命题经攻击存活(基价 2:
> 严格干净对账对 5 个全支持、14 条 offset 零 variance 排除反例遗漏;徽标退役:
> 徽标=5 时实付 2 直接账面反证+971 条读数无断代;局22 根因独立复核成立),
> 但三处表述收窄:①「不随等级/位面变」系外推——语料无 level3-4/7-9、
> plane2-3、金<35 的已执行刷新,覆盖域=P1r9/level5-6;②「徽标=min(gold//10,5)
> 恒等式」降格为「93.3% 符合的经验规律」——65 条残差(gold<10 读 10 等)
> 未帧级定性,「OCR 串读」是假设非实证;③free_refresh_proc 判据曾存在
> before 名集取 plan 期读数的缺陷(波内买卡不摘 state.shop,买+刷新波里
> 真落空被误判为免费生效)——**已修(W592)**:刷前名集改为刷新点击前
> 一刻现读(与点前金同帧;已买空槽的未识别读不含刷新证据,比较前剔除;
> 刷后一侧含未识别槽仍按不可判不猜)。修复前该通道产出的 flag/台账按
> 存疑处理;修复后恢复正证据资格。审计全文=
> `.debug/temp/currency_war/w590_w577_adversarial/REPORT.md`。

## 背景

局20-22 判读暴露两个同源缺陷:

1. **刷新费语义错**:全部 14 条 refresh_expect_mismatch 缺陷(4 局)期望≠实付,offset 恒正、随金位变化。三流对拍定谳:右下角「文本-刷新金币数」rect 读到的**不是刷价**——UI 实为商店折叠面板「↻ N」徽标,N=min(gold//10,5)(= 利息公式,8 帧 fixture + 实机决策行零例外);而相邻决策行金差干净对账(只含 LevelUp+Refresh 的最小对账对)证明**实付恒 2 金基价**,不随金币/次数/等级变。invest_effects.md「刷新 45% 概率免费 → 期望刷价 1.1」隐含基价 2(2×0.55=1.1)旁证。局20 decisions 的 state.shop_refresh_cost 实测分布 {0:3,1:10,2:11,3:10,4:12,5:20,10:13}——0-5 外乱值(10/1/0)为徽标/等级 OCR 串读噪声,佐证退役读数修法。
2. **安灯误停**(局22 05:05:41 停线):r9 已刷 4 次达 MAX_REFRESH 硬墙,plan 的 RefreshShop 被 shop.py `continue` **合法跳过**(没点击没扣金,gold 50→50);classify_spend_unit 只看「计划花费>0 且金差≈0」→ not_effective → 安灯停线。「计划≠尝试」被混为一谈。

## 决策

**件 1(基价模型)**:新增 `cw_state.REFRESH_COST_BASE = 2`(建模值,非读数兜底);`read_game_state` 不再 OCR 刷价,`state.shop_refresh_cost` 恒基价(决策热路径净少一次 OCR);`read_shop_refresh_cost` 函数与 area 保留改注「徽标读数=利息数值,仅旁证」,退出主链;`build_refresh_expect` 刷价输入改基价常量 → 期望=实付,mismatch 缺陷类归零。8 处消费点(cw_line_switch:135 / decision_v2 candidates:496·economy_cycle:179·ev:219·scoring:595,724·posture_release:101 / cw_sim:1697 / shop.py:727)全 `or 2`,值恒基价后行为不变、零波及。免费刷新存在性证据不足(局22 假象由件 2 解释),不预建模。

**件 2(三态分流)**:执行侧可见化——shop.py 硬墙跳过/「至首个 RefreshShop 截断」丢弃点写执行事实进单元账(SpendUnitRecord 扩 `plan_truncated`/`refresh_skipped`/`refresh_attempted`/`refresh_board_changed`,经 `set_unit_exec_facts` 暂存槽同 gold_close 模式);classify_spend_unit 增可选 `executed` 入参,判定序:①plan_truncated → `plan_truncated`(**不停**,口径差留台账)②金差≈0∧计划花费>0∧已尝试 → `not_effective`(**停**,真点击落空)③已尝试∧牌面已变 → `free_refresh_proc`(**不停**)。executed=None(历史局)退回 W494 原语义零漂移;exec_fail_should_stop 只对 not_effective 停,新态自动豁免;钩子数据源补 spend_ledger 单元行(同一 replay join 面)。

**件 3(免费采证)**:free_refresh_proc 的事后正证据(点击后两帧一致门+牌名集对拍:「牌面已变∧Δgold=0」)不依赖事前状态,覆盖棱/策略/未知一切免费来源;豁免臂命中时截图+flag(`cw_free_refresh_proc.flag`)留证**不停机**。该通道是修正后判定语义的一部分,永久保留(区别于 W542 商店入口停机采证钩子,后者证入口形态、生命周期独立)。事前判据(STRATEGY_ECONOMY)只作补充标签不作门。

## Considered Options

- 刷价:①基价常量建模(采纳——三流对账+期望账数学自洽,热路径提速)②保留 OCR+or-2 兜底(把徽标噪声喂决策,W554 假设已定谳半对半错)③逐波现读刷价(读的仍是徽标,语义错未修)。
- 安灯:①执行事实进单元账+分类器分流(采纳——治本,「计划花费 vs 金差 vs 牌面变化」三观测三分)②放宽 not_effective 容差(真落空也放过,安灯失效)③关停安灯(因噎废食)。
- 牌面不可判(refresh_effective None)**不**当「已变」——真落空不能被洗成免费,停线面不可静默变窄(有锁)。

## 影响

- SpendUnitRecord schema 扩 4 字段(旧行缺省 falsy,读端兼容);W573「裸 shop_refresh_cost 进期望」源码锁按锁纪律重写为基价锁(语义已被取代,docstring 记一句);W514 接线锁跟调用形参形状;决策消费点零改动。
- 消费点逐核清单(恒 2 后语义核验):cw_line_switch:135/decision_v2 candidates:496/economy_cycle:179/ev:219/scoring:595,724/posture_release:101/cw_sim:1697/shop.py:727 —— 全部「读不到→2」语义消解为「恒为 2」,无「把读不到当免费」残留。

## 验证

- 新锁:刷价基价模型锁(主链退出+恒 2)/分类器三新形态锁(局20 r9、局22 u1 真实序列 fixture)/build_refresh_expect 基价锁(徽标 5 期望按 2)/谓词豁免锁。
- 受影响锁对账:test_cw_observation 实帧锁(语义翻转注释,值不变)/W564 真值表(纯函数未动)/prep_director 谓词锁/w494 分类器与 ledger 结构锁/W514 接线锁。
- CW 域全集 `uv run pytest sr-od-test/test/sr_od/app/currency_war/ -q` + ruff(交付时附结果)。

## 开放证据项

1. 「↻ N」徽标 UI 语义定谳(N=利息数值;显示 bug 还是利息徽标)——W542 钩子停机画面 analyze 或用户口述。
2. 局22 停机截图 gold=78 vs 账面 close=50——疑截图时点已过 1-9 结算,判读批核对 settle 时序。
3. 免费刷新实机来源(棱 45% vs 策略类)与频率——等 W542 钩子或本 ADR 采证通道正证据,不预建模。
