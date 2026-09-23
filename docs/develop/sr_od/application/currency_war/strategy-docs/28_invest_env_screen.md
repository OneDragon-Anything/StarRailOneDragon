# 28 投资环境画面策略(invest env screen)

> 画面 = 货币战争-投资环境(开局/固定节点的整局增益三选一,可整组刷新重掷);**能力面** = [../screens/README.md](../screens/README.md) §5.2/§5.5。本篇 = 该画面的**策略面**(宪法六「一画面一策略文件、一画面一策略文档」首批兑现,2026-09-23 迁移迭代)。
> 决策本体 = `strategies/impl/mandate_v1/invest_env.py::decide / decide_pick`(纯值出口);共用模块同目录 `line_value.py`(方向分)/ `gift_value.py`(赠卡分)/ `env_economy.py`(现金分);动作包装与同帧去重 = `strategies/impl/flow.py::_decide_invest` kind='env' 分支;画面 op = `operations/cw_screen/cw_screen_invest_env.py`(整组重掷终结交回)。判据本体引用不重复,数值单一源在代码(本篇只写常量名)。
> 行为对照基线与迁移动机 = 迁移迭代 `../changes/2026-09-23-invest-env-strategy-migration/design.md`(注:`changes/` 是过程区,本篇自足,长期以本篇为准)。

## 1. 标尺(统一加法)

- **单位 = 分;1 分 := 1 金等价**(归一化约定,非语义拍值;经验值折金沿 `env_economy.XP_GOLD_RATE` 承载)。旧 kernel 的多标尺层次压制(裸分/送卡档/阵营 floor/经济域带各标尺不可比,靠层次常数定先后)已整体退役。
- **总分 = 现金分 + 方向分 + 赠卡分 + 立场分 + 转向轴加分**;取总分最高者,平分取先(同分取候选序靠前)。
- 加法合法的前提:所有分值声明为同一标尺上的量(分差有含义);立场表按「分值思维」维护(拍的是量级与差距,不是名次)。
- 数字三形态对账:现金 A 类精确通道 = 【注】游戏定义值 + 【推】位面到达加权;C 类估算通道 = 【拟】(值+置信区间+来源+截止,fail-closed 退路);立场分 = 【拍】(用户策略立场的登记值,合法性来自裁定本身,不是任何形态的推导产物)。

## 2. 四价值组件

| 组件 | 单一源 | 语义要点 |
|---|---|---|
| 现金分 | `env_economy.env_economy_value(name, gs) -> (expected_gold, resolved)` | 环境经济通道折金等价期望;`resolved ∧ > 0` 才计,fail-closed 恒 0(缺参/置信区间方向不闭合/未入模)。A 类精确(增发货币/蓝海/成功经验/策略大师)、C 类估算(经济过热系,零有效估计期恒 fail-closed)、gold_after_refreshes 系(长线利好/二手市场)= **拍值注册** `_GOLD_AFTER_REFRESHES_FIXED`(无条件计,不读局内刷新计数;锚定 = `../proofs/p97-refresh-budget.md` §7)、品质改写层 E(**层 E** = 品质改写型环境把策略池品质改写后、取卡金流期望相对无改写 offer 的抬升增量口径;`_pool_rewrite_value`,当前态 fail-closed,转正准入门未过) |
| 方向分 | `line_value.line_value(faction, locked_comp, demoted_endgame, evicted)` | 只辖概念股/邀请(邀请只计方向分)。候选线集三口径:①基础集 = 未被 evicted 排除 ∧ `COMP_LIBRARY` 阵容含该环境阵营;②意向已锁线 ∧ 非降格帧 → 基础集 ∩ {锁线阵容}(不含该阵营 → 0);③未锁线或降格帧 → 基础集全体取 max(版本先验,不做信号加权)。线价值 = 强度档分 `LINE_STRENGTH_SCORE`(键 S/A/B) |
| 赠卡分 | `gift_value.named_gift_value / random_faction_gift_value` | 具名赠卡(契约 ×7 + 特邀专家 ×4,登记 = kernel `cw_investments.ENV_GIFTS` 留 kernel):档位判定复用 kernel `cw_comps.gift_hit_tier`(机制事实判定留 kernel),档→分映射 `GIFT_TIER_SCORE`;advisor(付费顾问期权)同档分乘 `ADVISOR_DISCOUNT`(付费期权 < 白得)。随机阵营赠卡(概念股「获得某阵营角色」)= 该阵营注册成员(`cw_chars.chars_by_faction`)在未排除候选阵容 core∪shared∪transition 名单中出现者的档位分**算术平均**(随机发放取无偏口径;无成员在册 → 0)。白得卡全员集外 → 赠卡分自然 0,环境其余成分照常计分(旧整体失格规则已删) |
| 立场分 | `invest_env.STANCE_SCORE`(`StanceRow.score` + 每行裁定理由) | 仅登记「无机械成分」环境(判定 = 无阵营 ∧ 不在 ENV_GIFTS ∧ 不在 ENV_ECONOMY,价值不含可推导成分,纯立场)+ 点名零值机械环境;表外环境立场恒 0。覆盖由构建期校验兜底(缺行 import 即炸) |

术语:**锁线** = 最终阵容已确定、此后围绕它买牌的状态(`locked_comp`);**降格帧**(`demoted_endgame`) = 终局锁线已放弃的帧,方向分按未锁线口径(忽略锁线);**evicted** = 「等同信号未发生」的 comp 名集合(意向状态直通);**DoT** = 持续伤害类机制。

## 3. 排除与转向轴(交互规则)

- **禁选**:config `env_forbid` 子串命中 → 排除出候选。
- **自拆台**:板面 持续伤害+减益 计数 ≥ `BOARD_DOT_COUNT_THRESHOLD` 时,克制 DoT/减益的候选排除(机制归一调 kernel `AFFIX_MECHANIC_MAP`/`MECHANIC_COUNTERS`——「是否克制」是事实判定留 kernel;「排除它」是策略,在画面文件)。
- **priority**:`env_priority` 子串命中 → 加 `STEERING_PRIORITY_BONUS`(固定偏好分,软偏好——压不过 S 线方向分,「用户点名是偏好不是支配」)。
- **全排除退化帧**(三候选全被排除):沿旧机器全禁帧退化行为取全体 argmax 最不负分者,归因串以 `all-excluded-fallback` 开头(判读面唯一标识)。

## 4. 刷新判据

- **建议刷 = 排除槽存在 ∨ 帧最好总分 < `REFRESH_THRESHOLD`**,且次数闸 `gs.env_refresh_left ≥ 1`(容器读数 None = 未观察 → 不建议刷,fail-closed)。
- `REFRESH_THRESHOLD` = 全部 83 条环境**无轴总分**的均值,构建期由注册表+系数+立场表派生(单一源 = 表,表改阈值自动随动)。依据:重掷免费,重掷后帧最好期望 ≥ 单抽期望 = 全表均值(取均值 = 保守向);不取低分位——立场 0 值条目多,分位阈值会沉到 0 附近令判据失效。
- **输出契约**:`decide` 返回纯值 dataclass(`InvestEnvDecision(idx, reason)` / `RefreshSuggestion(reason)`),不含动作词表。flow 包装:`RefreshSuggestion` → `CwActionRefreshInvestCardsParam`(slots = 全帧槽位哨兵——环境屏整组重掷、单全局钮,handler 只消费真值);`InvestEnvDecision` → `CwActionPickInvestEnvParam`。handler 侧 obs.refresh 现读闸 + 容器 env_refresh_left 对照闸原样,op 层零改动。
- **同帧去重 memo**(flow scratch):建议帧首调发建议;handler 刷新闸全败同访问重调时,落选卡走 `decide_pick`(与 decide 同一评分基线,零选卡漂移)并清 memo 键;再调恢复首调建议语义。sim 复用预留 `decide_pick`(现 sim 投资面 = offer 采样 + inject_choices 直写容器,不经本入口)。

## 5. 共用模块复用预留

`line_value`(锁线/先验/降格三形态)、`gift_value`(具名/随机两口径)、`env_economy.env_economy_value`(签名不变)为投资策略屏迁移批预留(现金流卡直接复用 env_economy 与 gift_value);第二策略出现时再评估是否提升为跨策略共用包。
