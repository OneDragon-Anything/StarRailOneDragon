# 设计对抗报告（第 1 轮·无前提攻击）

> 攻击对象：design.md 草案。三核并重，本轮以核一（无前提）为主轴，核二/核三发现的实质问题一并入册。结论：6 个攻击点——1 个设计错误级、1 个行为申报漏项、1 个数字口径错误、3 个判据/清单缺口；全部处置明细见各条，处置后 design/landing 已同步修订。

## A1【设计错误级】「invest_env 构建期校验自动跟随、无需改代码」不成立

- 攻击：design §2.1 第 2 条末句断言 invest_env 校验「随键域自动收窄，无需改代码」。
- 证据：`invest_env.py:220` `_gift_tiers = {'core', 'shared', 'transition', 'off'}` 是**手编硬编码常量**（构建期校验 `_validate_coefficient_tables` 的期望域），非从档位机器派生。删 `GIFT_TIER_SCORE['transition']` 后 `_missing_gift = {'transition'}` 非空 → **import 即炸**——恰是该校验的设计目的（缺键防静默零分）。
- 处置：design §2.1 增补 invest_env.py `_gift_tiers` 常量删 'transition' 键；landing 3.1 文件面加入 `invest_env.py`；§2.5 键域条目改为「常量与分表双侧同步，校验兜底」。

## A2【行为申报漏项】概念股期望分的分母变化未申报

- 攻击：design §2.2 行为申报只覆盖「白送具名打工牌」路径，漏 `random_faction_gift_value`（概念股「白得某阵营角色」的期望分）。
- 证据：`gift_value.py:93-99` 期望分 = 成员档分**算术平均**，`tier != 'off'` 才入分母——transition 档成员现贡献 5.0 且入分母；退役后该成员档变 'off' → **掉出分母**。例：某概念股成员 = 2×core(50) + 1×transition(5) → 现均值 35.0 → 退役后 100/2 = 50.0（期望分**上升**）。受影响面 = 4 个纯打工角色（艾丝妲/赛飞儿/丹恒·腾荒/星期日）所属阵营的概念股。
- 处置：design §2.2 申报表增「概念股期望分」一行（方向 = 分母收缩、期望分升或全员 off 归零二态）；落地批列出受影响概念股清单逐条核期望分变化量。

## A3【数字口径错误】「60% 数据行零行为」与实测分类对不上

- 攻击：design §1 症状 1 称「48 行中 6 行压死 + 约 23 行降档不可达」= 60%；实测 audit：B 类 31 行中不可达（需排除该角色全部 core/shared 套 ≥7 套）= 符玄 6 + 花火 5 = **11 行**；6+11 = 17 行 = **35%**。且「可达/不可达」阈值未定义。
- 证据：护栏现实排除规模先例 = 「持续伤害契约排除 3 个 DOT 套」（invest_env docstring / gift_hit_tier docstring 传导例）——阈值取先例最大值 3 套：需排 ≤3 套 = 可达（20 行），≥7 套 = 不可达（11 行）。
- 处置：design §1 症状 1 改为 35%（17/48），阈值定义（护栏先例 3 套）就地标注；论点不依赖 60%，35% 仍成立。

## A4【验收判据漏洞】符号级 grep 抓不到注释措辞残留

- 攻击：landing 3.1 判据「`transition_chars` 符号级 grep 清零」——注释里「……是 core **非 transition**；常驻是火花**非花火**」（cw_comps.py 绯英线数据注释）等档位词措辞残留不在符号 grep 域内，残留后 docstring 与实现不一致。
- 处置：landing 判据追加「`cw_comps.py`/`shop.py`/`gift_value.py`/`invest_env.py` 四文件面内档位词 `transition` 一词级 grep 复核（残留注释改写或随行删除）」。

## A5【正本清单缺口】research 域复核面收窄漏 transition_combos.md

- 攻击：landing 正本清单末行复核面只点名 final_comps 各篇；`research/transition_combos.md`（过渡阵容知识 doc）与 `combo_methodology.md` 可能引用字段名/三名单口径，未入复核面。
- 处置：landing 该行改为 `docs/game/currency_war/research/` 全域 grep 复核（字段名 + 三名单措辞），命中即改。

## A6【治本悬空】同族第 4 件整字段退役，防复发件状态未更新

- 攻击（核三·跨件半问）：lock_rules→entry_signals→key_items→transition_chars 已是同族（知识卡/名单字段被新统一机器取代后未清算）**第 4 件**整字段退役；key-items-retirement 将「登记↔消费一致性防复发机制」列为外溢立项，至今未建。本设计沿引该行而未更新状态——第 4 件出现强化了「该升架构级设计件」的信号。
- 处置：design §1 不解决清单该行补注「同族已第 4 件，防复发设计件应尽早独立立项（建议下一迭代）」；本迭代不扩范围（外溢判定沿 iteration-design §1.1）。

## 核二（规范遵循）抽查

- 四节齐/七件齐/依据就地标注/无过程叙事：过（A1/A3 属依据与数字实质问题，非格式）；§2.4 判定式与 §2.5 点名行号可验证：过。
- `锻冶专家:刃 = 10.0 断言不变`（design §2.5）复核：刃最高档 = shared（黄泉减益）× advisor 0.5 = 10.0，transition 登记零参与——断言成立，作为压过口径活证保留：过。

## 核三（治本）判定

- 归层「语义层」成立（症状 → 根因链完整，A1-A3 修订后依据闭合）；本迭代修的是根（载体删除）非症状；A6 为唯一悬空项，处置 = 外溢加注不扩范围。

## 收敛判定

6 攻击点全部处置（design §1/§2.1/§2.2/§2.5 与 landing 3.1/正本清单同步修订）；无遗留开放问题——修订后可定稿。
