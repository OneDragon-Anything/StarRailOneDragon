# transition-chars-retirement 迭代设计（总纲）

## 0. 元信息

- 迭代目标：`Comp.transition_chars` 整字段退役 + 送卡估值档位机器降三档 + 商店拒因标签归并（用户裁定，2026-11-05 字段冗余排查会话——按 key-items-retirement 同标准（统一机器承载 vs 特殊逻辑）审视剩余字段后裁定；本篇为该裁定的完整设计）。
- 状态：草案
- 文档清单：（无详设——单文档方案，本篇即完整设计；改动面 = 一个字段 + 一个档位机器 + 一个遥测标签，无跨主题接口）

## 1. 问题与动机

- 现状症状（三条，均为可复核的存量事实，实测复核脚本口径见 §2.4）：
  1. **35% 数据行零行为**（17/48）：6 行压死（角色的 transition 套 ⊆ 其同套 core/shared 名单——`_char_gift_tier` 取全库最高档，同套更高身份恒压过：卡芙卡/开拓者·记忆/忘归人/灵砂/藿藿/阿格莱雅）+ 11 行降档不可达（需投资环境冲突护栏排除该角色**全部** core/shared 套——符玄需排 8 套、花火需排 7 套；护栏现实排除规模先例最大值 = 3 套〔「持续伤害契约排除三 DOT 套」，invest_env/gift_hit_tier docstring 传导例〕，需排 ≤3 套的 20 行算可达）。病根 = 登记口径（按线记「这条线前期用谁打工」）与消费口径（全库最高档取档）错位——登记↔消费不一致（同 key_items 58 死行判例）。
  2. **语义层违规——终局条目夹带过渡知识的最后载体**：字段语义「早期打工牌(后期卖)」= P1 过渡知识。key-items-retirement design §1 根因句「过渡体系已统一承载 P1 过渡知识后，终局条目不应再夹带过渡逻辑」逐字命中本字段（该迭代清了 key_items 的过渡夹带，本字段是同一裁定的漏网载体）。`GIFT_TIER_SCORE` 的 transition 档（5 分）= 终局身份估值里的「过渡情面档」，与已退役的选线证据骨架档（+2000 特权档）同构镜像：都是给「对终局无关但前期有点用」的件留的第三条估值通道。
  3. **统一机器承载率高**：48 行中 39 行（81%）的知识已被统一机器承载——过渡体系承载 29 行（TRANSITION_BONDS 点名件 ∪ 羁绊型/混合型块的羁绊全员）、跨线 core 身份承载 10 行；唯一决策消费的量级 = 白送打工牌 5 分（core 档 10%、shared 档 25%），且全库仅 4 人（艾丝妲/赛飞儿/丹恒·腾荒/星期日——全库最高档即 transition）的赠卡估值由它决定。
- 根因归层：**语义层**（与 key_items 同层同根：过渡体系建成后的旧知识载体未收编清算）。次生根因同 key_items：登记口径错位（docstring「早期打工牌」诱导按线全量登记，消费只认全库最高档）。
- 解决到哪：字段删除（实例字段 12 → 11）+ 档位机器降三档（core/shared/off）+ 拒因标签 `transition_char` 键停写；行为变化逐类申报（§2.2）。
- 明确不解决（外溢面，禁并入本迭代）：
  - 白送打工牌估值归零后的任何补偿通道（transition 档语义本身不成立，见 §2.2 门翻转论证——off 档 0 分就是「与终局候选无关」的正确语义）；
  - 通用打工件（艾丝妲/赛飞儿/丹恒·腾荒/星期日）的 P1 价值知识不迁任何载体（知识价值趋零：任何 1-2 费卡可顶 P1 前期战力，无需注册表逐人登记——如实申报为接受损失）；
  - 商店拒因可辨性的派生标签方案（「非 members 低费件」现读派生）不立项——`non_line` 桶已是 docstring 申报的兼容态（shop.py `shop_unbought_reasons`「打工件照旧落本键或 non_line 桶(可辨性申报)」）；
  - 过渡块→终局线衔接通道（沿 key-items-retirement 不解决清单裁定：现行不需要）；
  - 同族「登记↔消费一致性」防复发机制（沿 key-items-retirement §1 外溢立项行，自成设计件；**同族整字段退役至此已第 4 件**——lock_rules→entry_signals→key_items→本字段，防复发件应尽早独立立项，建议下一迭代，不并入本迭代）。

## 2. 方案

（单文档方案：此处即完整设计）

### 2.1 系统级变化

1. **`Comp.transition_chars` 字段删除**（cw_comps.py）：21 套数据行（48 行）+ 字段声明行删除；`members` 读口 docstring 的「transition_chars 不计（打工后卖，不构成终局成员）」句改写为「终局成员 = core ∪ shared 两名单」（集合语义不变——members 本来就只取 core∪shared）。
2. **送卡档位机器降三档**（cw_comps.py + gift_value.py）：
   - `_GIFT_TIER_RANK`：删 'transition' 键 → `{'core': 2, 'shared': 1, 'off': 0}`；
   - `_GIFT_TIER_DOWN`：降档链改两步 → `{'core': 'shared', 'shared': 'off', 'off': 'off'}`；
   - `_char_gift_tier`：名单扫描删 transition 半边（core/shared 两名单）；docstring 的卡芙卡跨套例（「专家桑博DOT 亦列其 shared/transition」）改写为两档口径；
   - `gift_hit_tier`：返回域 'core'|'shared'|'off'；docstring 档域声明与 evicted 传导例（「排除 DOT 套 → 椒丘落 transition」）按两档语义改写（降档例改 shared→off 方向）；
   - `GIFT_TIER_SCORE`（gift_value.py）：删 `'transition': 5.0` 键；模块头与 `random_faction_gift_value` docstring 的「三名单(core∪shared∪transition)」措辞改两名单；
   - invest_env.py `_validate_coefficient_tables` 的期望域常量 `_gift_tiers`（`:220`，手编硬编码 `{'core','shared','transition','off'}`）**同步删 'transition' 键**——该常量不从档位机器派生，漏改则构建期校验 import 即炸（缺键防线本身就是该校验的设计目的）；test 键域断言随同。
3. **商店拒因标签归并**（shop.py `shop_unbought_reasons`）：`transition_char` 分类键停写（`trans` 集合读取段删除），成员统一落 `non_line`；docstring 拒因清单删 transition_chars 行、「可辨性申报」句随标签退役简化；退役标签申报区（`protection_member_rejected` 等三键历史停写区）追加 `transition_char` 行（键保留、停写不清理，判读兼容）。
4. **正本与 skill 同步**：见 landing.md 正本更新清单。

### 2.2 行为变化申报（48 行逐类 + 边角场景）

统一验证口径（沿 key-items-retirement / comp-structure-unification 3.3 先例）：不做 A/B 模拟对照；行为验证 = 落地批测试全绿；实机观察点 = 投资三选一帧遥测（`decision_payload` 投资分组件）中白送打工牌卡的赠卡分 0 值案例。

| 类 | 行数 | 变化 | 论证 |
|---|---|---|---|
| A 基线活（全库最高档即 transition） | 11（4 人：艾丝妲/赛飞儿/丹恒·腾荒/星期日） | 白送该角色赠卡分 5 → 0 | **门翻转即设计意图**：赠卡估值回答「白得的角色对终局候选值多少」——打工牌后期卖、对终局无关，off 档 0 分是该语义的正确取值；5 分是把 P1 前期价值混进终局估值的情面分，而前期用牌价值归过渡库管（架构裁定，or-reqs-retirement 3.2）。投资三选一排序中 5 分差仅在候选卡总分贴身时翻转选择，量级申报接受 |
| B 降档活（evicted 边角） | 31（10 人） | 候选排除场景的 transition 兜底（5 分）消失 → off 0 分 | 现实可达子集 = 刃/椒丘/银枝（需排 1 套）/饮月/桑博/风堇（需排 2 套）/姬子/知更鸟（需排 3 套）；符玄（8 套）/花火（7 套）不可达。兜底语义同 A 类论证（情面分），消失为设计意图；5 分量级申报接受 |
| **概念股期望分**（`random_faction_gift_value` 路径） | 4 人所属阵营的概念股 | 期望分分母收缩：transition 档成员现贡献 5.0 且入算术平均分母（`gift_value.py:93-99` `tier != 'off'` 才入），退役后该成员档变 off → **掉出分母**——期望分上升（例：2×core(50)+1×transition(5) 均值 35.0 → 100/2 = 50.0）或全员 off 归零 | 方向单调可判：分母收缩去掉的是最低贡献者（5 分），其余成员均值恒 ≥ 5 → 期望分**升或不变**（全员掉出 = 返回 0 是唯一降向，此时该概念股本就趋零价值）。落地批列出受影响概念股清单逐条核变化量 |
| C 压死 | 6（6 人） | 零行为 | 同套更高身份恒压过（§1 症状 1 判定式），删除前后 `_char_gift_tier` 返回值逐场景相同 |
| 拒因标签 | 48（全量） | `transition_char` 键停写 → 落 `non_line` | 纯遥测可观测性（复盘拒因串），零决策行为；docstring 已申报两桶兼容（§1 不解决清单第三行）；键保留停写，历史 replay 判读不炸 |

### 2.3 知识归宿登记

| 知识 | 归宿 |
|---|---|
| 前期经手谁（饮月/花火/椒丘等的按线打工叙事） | 过渡体系 TRANSITION_BONDS（点名件/羁绊全员，已在）+ final_comps 各篇「达成路径」叙事（已在，文档层无同步义务） |
| 通用打工件（艾丝妲/赛飞儿/丹恒·腾荒/星期日） | 不迁（§1 不解决清单第二行：知识价值趋零，接受损失申报） |
| 「按线打工登记」整体（48 行） | 知识源 = final_comps 各篇 + plaza 校准注（就地注释，git 历史可溯）；实现层从未以登记口径被消费 |

### 2.4 复核口径（供落地批重跑验证）

活性三分类判定式（与 §1 症状 1 / §2.2 同口径；落地后重跑应得「字段不存在」）：

```
压死判定: trans_suits(char) ⊆ core_suits(char) ∪ shared_suits(char)
基线活判定: _char_gift_tier(char, frozenset()) == 'transition'
降档可达判定: ∃evicted: 全部 core/shared 套 ∈ evicted ∧ 某 transition 套 ∉ evicted
```

（本迭代不把一次性脚本入仓；判定式即持久口径，同 key-items-retirement §2.4。）

### 2.5 接口契约（对消费方的破坏面）

- `Comp.transition_chars` 属性消失：全库生产消费恰 2 处——`cw_comps._char_gift_tier`（名单扫描半边）与 `shop.shop_unbought_reasons`（trans 集合读取段），随本迭代同批改写；grep `transition_chars` 清零为验收判据（含数据行/注释/docstring）。
- `gift_hit_tier` 返回域收窄：消费方 = gift_value.py 三口（`GIFT_TIER_SCORE[gift_hit_tier(...)]` 直索引——键域同批同步，缺键即 KeyError 暴露，无静默路径）+ invest_env 构建期校验（自动跟随）。
- `GIFT_TIER_SCORE` 键域收窄：消费方 = gift_value.py 内部 + invest_env.py 构建期校验（**期望域常量 `_gift_tiers` 与分表双侧同步删键**，单侧漏改即 import 炸——校验兜底而非自动跟随）+ 测试键域断言（同步点名）。
- 测试消费同步点名（落地批 grep 复核）：
  - test_invest_strategy.py `:270`（`hosts` 全名单构造 `| set(c.transition_chars)` 半边删除）；`:278`（`锻冶专家:刃` = 10.0 断言**不变**——刃最高档 = shared 20 × advisor 0.5，transition 登记零参与，本断言即「压过口径」的活证，保留）；`:1028` 键域断言 `{'core','shared','transition','off'}` → 三档；
  - test_cw_comps.py 档位断言（`持续伤害契约`='core' 等不涉 transition 键的原样；涉档域全集的断言改写）；
  - test_shop_session_loop.py 拒因断言（`transition_char` 键如有断言 → `non_line` 期望，grep 定位）；
  - test_licai_jingli / test_strategy_yueguang 等 `gift_hit_tier` 直调断言（'off' 档原样，零改动预期，grep 复核）。
