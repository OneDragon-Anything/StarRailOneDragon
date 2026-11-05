# 28 投资环境画面策略(invest env screen)

> 画面 = 货币战争-投资环境(开局/固定节点的整局增益三选一,可整组刷新重掷);**能力面** = [../screens/README.md](../screens/README.md) §5.2/§5.5。本篇 = 该画面的**策略面**(宪法六「一画面一策略文件、一画面一策略文档」首批兑现,2026-09-23 迁移迭代)。
> 决策本体 = `strategies/impl/mandate_v1/invest_env.py::decide / decide_pick`(纯值出口);共用模块同目录 `line_value.py`(方向分)/ `gift_value.py`(赠卡分)/ `env_economy.py`(现金分);动作包装与同帧去重 = `strategies/impl/flow.py::_decide_invest` kind='env' 分支;画面 op = `operations/cw_screen/cw_screen_invest_env.py`(整组重掷后结束本次访问、返回主循环)。判据权威定义引用不重复,数值单一源在代码(本篇只写常量名)。
> 术语(首现定义):**单一源** = 该信息的唯一权威出处;**帧** = 一次截取游戏画面并做一次决策的时点;**对账** = 预期记账状态与实际读数的比对核验;**fail-closed** = 读不到数据时默认走保守分支;**视界** = 决策考虑的未来时间跨度;**终局阵容已锁定** = 最终阵容已确定、此后围绕它买牌的状态(`locked_comp`);**降格帧**(`demoted_endgame`) = 原定终局阵容已放弃的帧,方向分按未锁定口径(即忽略已锁定的终局阵容);**evicted(已排除阵容名单)** = 「等同信号未发生」的阵容名单(哪些阵容因等同信号未发生而被排除出候选;由意向状态直接透传);**DoT** = 持续伤害类机制;**数字来源标注(四种)**:【注】游戏定义值 /【推】已证推导 /【拟】观测估计 /【拍】用户立场登记值。
> 行为对照基线与迁移动机归 git 历史(本篇自足,长期以本篇为准)。

## 1. 标尺(统一加法)

- **单位 = 分;1 分 := 1 金等价**(归一化约定,非语义拍值;经验值折金沿 `env_economy.XP_GOLD_RATE` 承载)。旧 kernel 的多标尺层次压制(裸分/送卡档/阵营 floor/经济域带各标尺不可比,靠层次常数定先后)已整体停用。
- **总分 = 现金分 + 赠卡分 + 立场分 + 转向轴加分**;取总分最高者,平分取先(同分取候选序靠前)。
- 加法合法的前提:所有分值声明为同一标尺上的量(分差有含义);立场表按「分值思维」维护(拍的是量级与差距,不是名次)。
- 数字来源标注(四种)核对:现金 A 类精确通道 = 【注】游戏定义值 + 【推】位面到达加权;C 类估算通道 = 【拟】(值+置信区间+来源+截止,fail-closed 退路);立场分 = 【拍】(用户策略立场的登记值,合法性来自裁定本身,不是任何形态的推导产物)。

## 2. 四价值组件

| 组件 | 单一源 | 语义要点 |
|---|---|---|
| 现金分 | `env_economy.env_economy_value(name, gs) -> (expected_gold, resolved)` | 环境经济通道折金等价期望;`resolved ∧ > 0` 才计,fail-closed 恒 0(缺参/置信区间方向不闭合/未入模)。A 类精确(增发货币/蓝海/成功经验/策略大师)、C 类估算(经济过热系,零有效估计期恒 fail-closed)、gold_after_refreshes 系(长线利好/二手市场)= **拍值注册** `_GOLD_AFTER_REFRESHES_FIXED`(无条件计,不读局内刷新计数;定标依据 = `../proofs/p97-refresh-budget.md` §7)、品质改写层(**层 E** = 品质改写型环境会把策略牌池的品质改写,这一项算的是改写后取卡的金流期望比不改写时抬升多少的增量口径;`_pool_rewrite_value`,当前态 fail-closed,转正准入门未过) |
| 方向分 | **已废止(2026-11-03 零消费清理批)** | 原语义 = 概念股/邀请按触线集取 `LINE_STRENGTH_SCORE` 强度档分;随 `Comp.strength` 字段与 `line_value.py` 整链下线移除(消费实证 = 选线不读 strength、唯此一消费链;git 历史可溯)。环境方向差异由赠卡分/立场分承载 |
| 赠卡分 | `gift_value.named_gift_value / random_faction_gift_value` | 具名赠卡(契约 ×7 + 特邀专家 ×4,登记 = kernel `cw_investments.ENV_GIFTS` 留 kernel):档位判定复用 kernel `cw_comps.gift_hit_tier`(机制事实判定留 kernel),档→分映射 `GIFT_TIER_SCORE`;advisor(付费顾问期权)同档分乘 `ADVISOR_DISCOUNT`(付费期权 < 白得)。随机阵营赠卡(概念股「获得某阵营角色」)= 该阵营注册成员(`cw_chars.chars_by_faction`)在未排除候选阵容 core∪shared∪transition 名单中出现者的档位分**算术平均**(随机发放取无偏口径;无成员已登记 → 0)。白得卡全员集外 → 赠卡分自然 0,环境其余成分照常计分(旧整体失格规则已删) |
| 立场分 | `invest_env.STANCE_SCORE`(`StanceRow.score` + 每行裁定理由) | 仅登记「无机械成分」环境(判定 = 无阵营 ∧ 不在 ENV_GIFTS ∧ 不在 ENV_ECONOMY,价值不含可推导成分,纯立场)+ 点名零值机械环境;表外环境立场恒 0。覆盖由构建期校验兜底(缺行 import 即炸) |

## 3. 排除与转向轴(交互规则)

> **共用判据单一源** = [13_pick_family.md](13_pick_family.md) §4(代码 = `strategies/impl/mandate_v1/pick_common.py`)——转向轴常数与选卡克制减分为投资环境/投资策略两画面共用,语义细则归彼处,本节只记本屏落点;禁止在本篇复制第二份语义(宪法六:双源即违例)。

- **阵容冲突护栏**(指向集单一源 = `kernel/cw_investments.env_faction_scope`,策略侧 `strategy_faction_scope` 同文件):候选环境阵容指向集与基准空交 → 并入排除通道(与禁选同一条 excluded 合取,`_score_frame` 内组装)。基准 = 锁定线 `Comp.factions`(锁定帧,历史误持不入基;降格帧锁线不入基回持有基)∨ 已持有投资(环境+策略)指向并集(未锁定帧,同名归一查询);基准空(无指向持有 ∧ 未锁定)→ 不辖,选卡与无护栏逐位一致。全部候选出域且次数闸尽 → 全排除退化帧(下行)。环境指向 = faction 分支(概念股/邀请/契约全量登记,专家类例外特邀专家:加拉赫→击破)+ 通道派生分支(统一阵容评分迭代起替换旧亲和分支:`cw_invest_channels.env_strong_lines` 全档命中线〔羁绊 ∈ 线羁绊要求档 0 键;加分层(档 ≥1)与 flex 同为弱关联线不入〕各线 factions 并集,副阵营随线带入;专家类目通用 0——所赠角色走证据分)。依据:策略槽不服务异线阵容(与策略侧同判据,29 号稿 §5 裁定 2026-10-17)。
- **禁选**:config `env_forbid` 子串命中 → 排除出候选。
- **选卡克制减分**(counters_dot 硬排除迁移,统一阵容评分迭代):选项名含词缀关键词 ∧ 词缀克制名单与阵容羁绊要求档 0 键有交集的候选减 `COUNTER_PICK_PENALTY`(直写表 `pick_common.AFFIX_COUNTERS_FACTIONS`,纯加权,组件分量;环境名不含词缀注册名族,生产帧恒 0——机制与策略屏同源,「是否克制」是直写表事实判定;「减分」是策略,在共用件)。
- **priority**:`env_priority` 子串命中 → 加 `STEERING_PRIORITY_BONUS`(固定偏好分,软偏好——压不过 S 档阵容的方向分,「用户点名是偏好不是支配」)。
- **全排除退化帧**(三候选全被排除):对全体候选(含被禁)取 argmax 最不负分者,原因编码以 `all-excluded-fallback` 开头(判读面唯一标识)。

> 注:旧 kernel 全禁帧的代码体实况 = 冻结槽 0(全禁帧分数恒更低、strict 比较恒假),「全体 argmax」从未是 kernel 行为;本件 argmax 语义是本篇 §1 加法标尺在退化帧的延展实现。

## 4. 刷新判据

- **建议刷 = 排除槽存在 ∨ 帧最好总分 < `REFRESH_THRESHOLD`**,且次数闸 `gs.env_refresh_left ≥ 1`(状态容器(GameState)读数 None = 未观察 → 不建议刷,fail-closed)。
- `REFRESH_THRESHOLD` = 全部 83 条环境**无轴总分**的均值,构建期由注册表+系数+立场表派生(单一源 = 表,表改阈值自动随动)。依据:重掷免费,重掷后帧最好期望 ≥ 单抽期望 = 全表均值(取均值 = 保守向);不取低分位——立场 0 值条目多,分位阈值会沉到 0 附近令判据失效。
- **输出契约**:`decide` 返回纯值 dataclass(`InvestEnvDecision(idx, reason)` / `RefreshSuggestion(reason)`),不含动作类型值。flow 包装:`RefreshSuggestion` → `CwActionRefreshInvestCardsParam`(slots = 全帧槽位真值标记——环境屏整组重掷、单全局钮,handler 只消费真值);`InvestEnvDecision` → `CwActionPickInvestEnvParam`。handler 侧 obs.refresh 现读闸 + 状态容器 env_refresh_left 对照闸原样,op 层零改动。
- **同帧去重 memo**(flow scratch):建议帧首调发建议;handler 刷新闸全败同访问重调时,落选卡走 `decide_pick`(与 decide 同一评分基线,零选卡漂移)并清 memo 键;再调恢复首调建议语义。sim 复用预留 `decide_pick`(现 sim 投资面 = offer 采样 + inject_choices 直写状态容器,不经本入口)。

## 5. 共用模块复用预留

投资策略画面已消费本批共用件(其权威版本 = [29_invest_strategy_screen.md](29_invest_strategy_screen.md)),复用落点三句:

- **策略卡现金分** = 策略层新入口 `strategy_economy.strategy_economy_value`(消费 kernel `EconomyEffect` per-node/一次性通道)——与本屏 `env_economy_value`(消费 `EnvEconomyEffect` 整局规则改写通道)公式分立,不复用同一入口;
- **共用件提升形态** = mandate_v1 包内共用模块 `pick_common`(转向轴/克制减分单一源,文档面 = `13_pick_family.md` §4),非跨策略包——跨策略共用待第二策略实现出现时再评估;
- **赠卡口径** = 策略屏走 kernel `STRATEGY_GRANTS` + `gift_value.grant_gift_value` 新口——非本屏 `named_gift_value`/`random_faction_gift_value` 在用具名/随机两口径;两屏共用面 = 档→分映射(`GIFT_TIER_SCORE`/`ADVISOR_DISCOUNT`)与 `line_value_best` 三种意向状态判定内层入口。
