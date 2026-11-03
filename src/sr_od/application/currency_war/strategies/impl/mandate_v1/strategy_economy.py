"""策略卡经济通道金等价折算(mandate_v1 共用模块;投资策略屏现金分承载面)。

设计正本 = strategy-docs/29_invest_strategy_screen.md §2.1(下称
「29 号稿」);复用契约形态与折算约定沿 env 批
env_economy.py——``(值, resolved)`` 返回、fail-closed 门、
:data:`XP_GOLD_RATE` 语义同源,但**通道公式分立**:
``EnvEconomyEffect``(整局规则改写)与本模块消费的 ``EconomyEffect``
(per-node/一次性流)字段空间不同构,公式不可共享(29 号稿 §2.1)。

归属(宪法五:框架层只留游戏原始真值,衍生估值归策略层):kernel 侧只留
游戏原始真值 ``cw_investments.STRATEGY_ECONOMY``(通道结构 = 游戏效果
原文的结构化,【注】);本模块承载策略层的金等价折算。

职责:策略卡可数值化经济通道折成**金等价期望** ``(expected_gold,
resolved)``——resolved=False = fail-closed(缺参/日程不可得/位置缺失帧
之外的异常形态),消费端按无现金处理(invest_strategy 组件组装处统一
``resolved ∧ expected_gold > 0`` 才计,半值禁出)。

**剩余口径**(沿 env_economy 同形态):从 gs 当前节点起算到局终——开局
取卡帧 = 全局期望,局内重发帧 = 剩余期望,同一函数自然覆盖。

**剩余节点数自算单一源**(宪法二查表键合法形态;框架不向
策略供视界量,序列模块只留键原语):长度唯一真值源 = GameState 场字段
``node_seq_by_plane``(修饰局 10/8、默认局 9/7;None = 未注册态回退默认
表),自算消费符号单一源 = 策略门面 ``statefn/horizon.r_remaining``/
``r_global``(本模块零新写视界实现);视界封顶 modeled planes(场字段
键集 = P1+P2,P3 = 建模域外 = 运行终局,不可达轮不计;行为申报 = 迭代
abolish-node-ordinal details/horizon-cleanup.md §8)。**口径偏差申报**
(29 号稿 §2.1 原文申报,如实保留):``r_global`` 含当前节点,而「进入
新节点给金/XP」类通道语义不含已进入的当前节点——原样消费 = per-node
通道系统性 +1 节点偏差(同向偏高,量级 ≤ 单节点流值);boss 通道同族偏高
(当前节点即 boss 位时多计一笔已发放 boss 金)。取上端 = 现金分计分偏高
已知并申报(29 号稿 §2.1 口径申报行),非防低估。``total_remaining_nodes``
恒按 9/位面的旧口径(01_math_framework §5 R_全局 行登记缺陷)已随视界族
清扫修正为场字段求和——本模块仍统一经门面自算,不直引该对照量。

**待建模通道**(v1 fail-closed = 0,建模落地自动进现金分):见
:data:`STRATEGY_ECONOMY_PENDING_MODELING` 与字段分类的「待建模」集
(刷新族/时点大额族/XP 折扣族/轨迹倍率族/合成与购买触发族/血补偿族/
息 cap 覆写/升级流——分类依据与29 号稿 §2.1 逐通道对应)。

**不计分通道**(结构登记、永不为分):血本位分区覆盖(xp_buy_hp_cost/
hp_gold_swap,invest_strategy 结构分区覆盖)、难度族(难度→价值需战力
建模,宪法一禁域)、期权/远见族(均匀分布假设未证)、负向结构登记
(无正账可折)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_investments import (
    INVESTMENT_STRATEGIES,
    STRATEGY_ECONOMY,
    EconomyEffect,
    get_strategy,
)
from sr_od.application.currency_war.kernel.cw_node_schedule import (
    PLANE_NODE_TABLES,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.env_economy import (
    XP_GOLD_RATE,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.horizon import (
    r_global,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import GameState

# ===== 字段分类(全字段三分;单一源 = 三集合,构建校验兜底)=====
# 分类判据与29 号稿 §2.1 逐通道对应:「计分」= v1 落地通道公式可算;
# 「待建模」= 有字段分支但价值模型缺(fail-closed = 0,建模落地自动进);
# 「不计」= 结构登记永不为分。字段分类校验覆盖「有字段分支」;卡级登记
# (PENDING_MODELING)覆盖「无字段分支 ∪ 字段已登记未挂值分支」,两适用范围不重叠。

#: 计分通道字段(v1 公式直算,值全 = 注册表游戏定义【注】直读):
#: - instant_gold:选卡当场一次性金(面值);
#: - gold_at_final_supply:「进入最后一个补给阶段后」金(尾款交付,
#:   面值——触发 = 展平全序列最末 supply 位〔必经节点,存活即到〕,
#:   兑现结构性归计分桶,与 instant_gold 同判;等值迁移自 instant_gold
#:   通道,现金分零漂移);
#: - gold_next_nodes_amount/count:「现在及接下来 count 次」分期金配对
#:   字段——**配对 count 半字段同入计分类**(消费公式两半齐用,分类粒度
#:   = 字段,半字段缺席即分类校验炸出);
#: - gold_per_node / gold_per_boss_node / interest_flat_per_node:
#:   per-node 流(息上调整数分支金等价直读);
#: - xp_per_node / xp_instant:XP 通道(× XP_GOLD_RATE 折算)。
_CASH_SCORED_FIELDS: frozenset[str] = frozenset({
    'instant_gold',
    'gold_at_final_supply',
    'gold_next_nodes_amount', 'gold_next_nodes_count',
    'gold_per_node', 'gold_per_boss_node', 'interest_flat_per_node',
    'xp_per_node', 'xp_instant',
})

#: 待建模通道字段(v1 fail-closed = 0;逐字段建模缺口与29 号稿 §2.1
#: 通道清单一一对应):
#: - 息 cap 覆写:interest_cap_override(金轨线依赖);
#: - 升级流:gold_per_level_up(E[剩余升级次数] = P58 期望等级日程,
#:   草案/证明骨架未证,处置规则 A 禁数值实现——P58 证明完成为解封条件);
#: - 时点大额族:gold_at_node/gold_at_node_offset(超发货币型,正向分支条件
#:   兑现概率未建模且负向分支 = 清空持有金轨迹依赖)、gold_at_level/
#:   gold_at_level_target(成长基金型,到达等级概率未建模);
#: - 刷新族:free_refresh_burst/free_refresh_per_node/refresh_surprise_
#:   every/refresh_per_compose/refresh_free_chance/refresh_shop_rewrite_
#:   every_3cost/free_refresh_cond_gold_above/step/cap/
#:   free_refresh_cond_prev_node_unspent(刷新机会成本模型缺,P97 预算
#:   只证可达性不证单次价值);
#: - XP 通道:xp_per_refresh(刷新 XP 收入的价值缺金值口径)、
#:   xp_buy_cost_discount/xp_click_discount_from_level/_at(P22 占优方向
#:   已登记但金值未立);
#: - 轨迹依赖:win_reward_mult/sell_price_mult;
#: - 合成触发族:gold_per_2star2cost_merge/gold_per_3star_merge(频次
#:   分布未采);
#: - 购买触发族:gold_per_three_5cost(每购买 3 个 5 费给金,非合成;
#:   购买频次分布未采);
#: - 刷新触发族:gold_per_refresh_pair(刷新出对条件金,出对频次分布
#:   未采——条件概率型按兑现结构性归本桶,与合成触发族同判据);
#: - 血补偿族:gold_per_20hp_lost(未来损血期望未采,且未来建模同样触发
#:   宪法三 hp 消费硬闸门)、gold_per_hp_lost_now(价值 = f(已损血),
#:   宪法三硬闸门外第三消费点须用户逐项确认,未确认期 fail-closed = 0);
#: - 状态置位族:streak_set(「使当前连胜数变为N」选卡当场带符号绝对
#:   置位,首例 胜利,还是胜利 = 4)——置位带来的连胜金流变化是轨迹
#:   依赖(后续胜负序列未定),估值价值未建模;keep_streak_on_loss
#:   (败局连胜维持,首例 嘴硬,读法边界见字段注)——维持省下的连胜
#:   金流价值是轨迹依赖(后续胜负序列未定;连胜全程价值量级见
#:   combat.md),估值未建模。
_PENDING_MODELING_FIELDS: frozenset[str] = frozenset({
    'interest_cap_override',
    'gold_per_level_up',
    'gold_at_node', 'gold_at_node_offset',
    'gold_at_level', 'gold_at_level_target',
    'free_refresh_burst', 'free_refresh_per_node',
    'refresh_surprise_every', 'refresh_per_compose',
    'refresh_free_chance', 'refresh_shop_rewrite_every_3cost',
    'free_refresh_cond_gold_above', 'free_refresh_cond_gold_step',
    'free_refresh_cond_cap',
    'free_refresh_cond_prev_node_unspent',
    'xp_per_refresh', 'xp_buy_cost_discount',
    'xp_click_discount_from_level', 'xp_click_discount_from_level_at',
    'win_reward_mult', 'sell_price_mult',
    'gold_per_2star2cost_merge', 'gold_per_3star_merge',
    'gold_per_three_5cost',
    'gold_per_refresh_pair',
    'gold_per_20hp_lost', 'gold_per_hp_lost_now',
    'streak_set',
    'keep_streak_on_loss',
    # 位面开始周期族(xp_per_plane/free_refresh_per_plane,固定理财位面
    # 段):世界发放腿已建模(kernel 位面开始桥/补发桥 + sim 位面窗腿/
    # 选卡拍补发腿);估值通道未建——剩余位面数视界口现网无现成成员
    #(xp_per_node 通道折算基数 = 剩余节点数,位面粒度须自建视界口),
    # 激活归估值批,先按待建模塌 0
    'xp_per_plane', 'free_refresh_per_plane',
    # 位面周期金/强制店改写对(公司严选):gold_per_plane 与上两字段同判
    # (位面粒度视界口缺,塌 0;世界发放腿已建 = sim 位面首节点窗金腿 +
    # 选卡拍补发金腿);shop_rewrite_forced_cost/unique = 强制店改写呈现
    # 面腿(触发拍店面内容改写,非现金流通道),估值范围外申报
    'gold_per_plane',
    'shop_rewrite_forced_cost', 'shop_rewrite_forced_unique',
})

#: 不计分通道字段(结构登记、永不为分):
#: - 血本位分区覆盖:xp_buy_hp_cost/hp_gold_swap(invest_strategy 血本位
#:   三态序以 is_blood_economy 集合排除覆盖,价值面不入现金账);
#:   boss_end_heal_hp(奋斗协议首领战回血腿)/battle_end_heal_hp(星际
#:   和平保险战斗结束回血腿,全战斗域)= HP 世界面发放同 hp_instant
#:   归定价出域族(hp 定价通道作废,hp 永不折金;世界腿 = sim 结算段
#:   策略腿区独立笔);
#: - 难度族:difficulty_delta/difficulty_per_streak/difficulty_node_types
#:   (难度→价值需战力建模,宪法一禁域);encounter_tier_extremes_only
#:   (二极管遭遇收窄结构旗标,端点 sim 呈现面派生无数值,同禁域);
#: - 期权/远见族:future_quality_upgrade/difficulty_inflation_exempt
#:   (远见品质改写 = 期权待建模,均匀分布假设未证);
#: - 负向结构登记:xp_click_surcharge_from_level/_at、hp_max_loss_pct_of_
#:   loss/hp_max_loss_cap_pct、loss_hp_extra(败局额外扣血,纯负向成本
#:   无正账可折,首例 嘴硬;消费 = sim 结算 hp 腿);
#: - 定价出域族:hp_instant(健康充值 +30 生命直给)——hp 定价通道作废
#:   正本(invest_effects.md 血金互兑裁定)支撑「永不为分」,非「待建模」
#:   (无未来进分语义);世界面发放 = sim 选卡落地拍独立笔。
#: - 进度轴结构改写族:level_cap_override(等级帽覆写,首例 控制规模
#:   「最大等级变为7级」= 7)——世界面消费走 kernel 解析 helper
#:   (cw_economy.level_cap_of,聚合取严 + min(MAX_PLAYER_LEVEL, 覆写)
#:   收窄),零金流非现金流通道,结构登记永不为分(与引擎排除桶同桶
#:   划界轴「是否持续通道」);策略侧等级判据仍读注册表 level_max,
#:   系「实机无卡真值」另一把尺,禁与本字段混读。
_NOT_SCORED_FIELDS: frozenset[str] = frozenset({
    'xp_buy_hp_cost', 'hp_gold_swap', 'boss_end_heal_hp',
    'battle_end_heal_hp',
    'difficulty_delta', 'difficulty_per_streak', 'difficulty_node_types',
    'encounter_tier_extremes_only',
    'future_quality_upgrade', 'difficulty_inflation_exempt',
    'xp_click_surcharge_from_level', 'xp_click_surcharge_from_level_at',
    'hp_max_loss_pct_of_loss', 'hp_max_loss_cap_pct',
    'loss_hp_extra',
    'hp_instant',
    'level_cap_override',
})

# ===== 「待建模」卡级已登记(键 = 注册表规范卡名,值 = 未建模分支清单描述)=====
# **卡级登记适用范围 = 无字段分支 ∪ 字段已登记未挂值分支**(区别于字段分类校验的
# 「有字段分支」适用范围):字段分类校验只扫 EconomyEffect 已挂值条目,扫不到
# 「字段已登记但条目未挂值」与「无字段分支」(效果结构在注册表无对应字段),
# 唯卡级登记覆盖得住(「字段已登记未挂值」先例 = 固定理财系 xp_instant,
# 2026-11-01 起两卡全字段挂值,该形态在册代表余 孪生素数/狸财经狸 类无字段分支)。
# 已登记行覆盖未建模分支的**可见性**(治理账,非运行时闸——已建模分支照常计分,
# 见 strategy_economy_value docstring);建模落地后改写对应行描述。
STRATEGY_ECONOMY_PENDING_MODELING: dict[str, str] = {
    # 固定理财系:官方「现在以及每个位面开始时,获得4/6经验值和2/3次免费
    # 刷新」——即时段(「现在」段 XP/刷新)已挂值发放(固定理财 xp_instant=4/
    # burst=2,固定理财+ xp_instant=6/burst=3);位面段字段已挂值、发放腿
    # 已建(kernel 位面开始桥/登记拍补发桥 + sim 位面首节点窗腿/选卡拍
    # 补发腿,用户裁定 2026-11-01 拍定中途拿卡所在位面补发,两卡同判);
    # 策略侧估值通道未建(两字段归 _PENDING_MODELING_FIELDS 待建模分类
    # 塌 0,激活归估值批)
    '固定理财': '位面段估值通道未建(xp_per_plane/free_refresh_per_plane'
               '待建模分类塌 0);即时段与位面段世界发放腿均已建',
    '固定理财+': '位面段估值通道未建(xp_per_plane/free_refresh_per_plane'
                '待建模分类塌 0);即时段与位面段世界发放腿均已建',
    # 公司严选:官方「现在及每个位面开始时，开启一个由5个独特4费角色组成
    # 的商店，并获得3金币」——即时段 instant_gold 面值已计分(现金通道);
    # 位面段金与商店改写对已挂值、世界发放腿已建(sim 位面首节点窗金腿/
    # 改写腿 + 选卡拍改写腿/补发双腿,改写 = 呈现面腿非现金流);估值通道
    # 未建(三字段待建模分类塌 0,激活归估值批)
    '公司严选': '位面段估值通道未建(gold_per_plane/shop_rewrite_forced_'
               'cost/unique 待建模分类塌 0);即时段面值已计分,位面段世界'
               '发放腿均已建',
    # 孪生素数:首购计数经验分支(2/3/5/7/11——XP_GOLD_RATE 下数值与金同),
    # 字段全缺省 = 纯无字段分支( EconomyEffect(xp_instant=0) 全默认)
    '孪生素数': '首购经验腿已建世界通道 STRATEGY_FIRST_BUY_XP_GRANTS;估值零登记维持',
    # 空仓:节点条件 XP 腿(物品栏+备战席无装备〔消耗品除外〕每节点 +2)
    # 已建世界通道 = cw_investments.STRATEGY_EMPTY_EQUIP_XP_GRANTS + kernel
    # 纯判定 + sim 节点窗挂点;即时腿 1 件随机简易 = cw_gain_effects 随机
    # 装备族泛化表(零估值面,无具名 gift);条件流挂 xp_per_node 无条件
    # 通道 = 系统性失真(孪生素数同判),STRATEGY_ECONOMY 零条目维持
    '空仓': '空仓经验腿已建世界通道 STRATEGY_EMPTY_EQUIP_XP_GRANTS;估值零登记维持',
    # 空仓+:即时 10XP 走 xp_instant 通道(现金分自动激活),窗腿 2XP 同空仓
    # 谓词,装备腿 1 件简易同泛化表;估值零登记维持(随机装备不可具名)
    '空仓+': '空仓经验腿已建世界通道 STRATEGY_EMPTY_EQUIP_XP_GRANTS;估值零登记维持',
    # 人才空洞:节点条件 XP 腿(备战席角色 ≤4 名每节点 +3)已建世界通道 =
    # cw_investments.STRATEGY_BENCH_COUNT_XP_GRANTS + kernel 纯判定 +
    # sim 节点窗挂点;条件流挂 xp_per_node 无条件通道 = 系统性失真
    # (空仓同判),STRATEGY_ECONOMY 零条目维持
    '人才空洞': '备战席计数经验腿已建世界通道 STRATEGY_BENCH_COUNT_XP_GRANTS;'
              '估值零登记维持',

    '人才济济': '备战席计数经验腿已建世界通道 STRATEGY_BENCH_COUNT_XP_GRANTS;'
              '估值零登记维持',
    # 愚者恶作剧:双腿分治——离场金腿(备战席 1星花火/火花进节点留 2/4 金
    # 离场)已建世界通道 = cw_investments.STRATEGY_BENCH_LEAVE_GOLD_GRANTS
    # + kernel 纯判定 + sim 节点窗挂点;商店变形腿(2/4 费 20% 变花火/火花)
    # = 随机资产面零建模申报(effect-domain §6.4 用户裁定直辖,市场活力
    # 同型,live 观察覆盖,sim 收益面低估);估值零登记维持
    '愚者恶作剧': '离场金腿已建世界通道 STRATEGY_BENCH_LEAVE_GOLD_GRANTS;'
              '商店变形腿随机资产面零建模申报(观察覆盖);估值零登记维持',
    # 赞美太阳:节点条件 XP 腿(每拥有一件【白昼装备】以及其原型装备,
    # 进入新节点每件 +1)已建世界通道 = cw_investments
    # .STRATEGY_EQUIP_COUNT_XP_GRANTS(计数域 = DAYLIGHT_EQUIP_XP_NAME_SET
    # 白昼系名集)+ kernel 纯判定 + sim 节点窗挂点;动态计数挂 xp_per_node
    # 无条件通道 = 系统性失真(零拥有局虚计/多件局漏计,空仓/人才空洞
    # 同判),STRATEGY_ECONOMY 零条目维持
    '赞美太阳': '装备计数经验腿已建世界通道 STRATEGY_EQUIP_COUNT_XP_GRANTS;'
              '估值零登记维持',
    # 狸财经狸:利息分支已计(interest_flat_per_node=2);取款/存款分支无字段
    # (金<20 取 10、P3 首领取全部存款——存款累计值消费端推,行为条件流)
    '狸财经狸': '取款分支(金<20 取 10)+存款分支(P3 首领取全部存款)无字段载体;'
               '30 本金系非玩家收入语境值不进账',
    # 超发货币:gold_at_node 族字段已挂值(归时点大额族字段待建模),
    # 但「失去现有全部金」负向分支无字段且方向不明——兼无字段分支在卡级已登记
    '超发货币': '正向分支兑现条件(5 节点后)概率未建模(gold_at_node 族字段'
               '待建模);负向分支「失去现有全部金」无字段载体,方向不明',
    # —— 注册表外经济语义卡代表例(economy 未注册但 research 已登记明列
    # 经济结构 = 建模待修问题形态,按无已建模机械成分 0 分申报低估;
    # invest_effects 批 3/4 已登记,禁凭 research 记载凭直觉给分)——
    '被动收入': '每节点 XP 经验腿已建世界通道 STRATEGY_BENCH_LEFT_COST_XP_GRANTS;估值零登记维持'
               '大于买断制现金流),无字段载体',
    '气氛组': '战斗结束按 0 伤害角色数给 XP,无字段载体',
    '气氛组+': '战斗结束按 0 伤害角色数给 XP 腿无字段载体(同气氛组);'
              '即时 XP 腿已挂 xp_instant=8',
    '存款回报': '条件免费刷新分支已建模(free_refresh_cond_prev_node_unspent=2,'
              '发放经节点桥,载体在 cw_investments.STRATEGY_ECONOMY);'
              '字段级估值 pending 归 _PENDING_MODELING_FIELDS 刷新族',
    '招财狗': '战斗胜利未损血 → 每佩佩 1 金(轨迹依赖:佩佩数×不败率),'
             '无字段载体',
    '免战牌': '跳过机制分支无经济字段载体(省一场战斗的价值面不折现,'
             '世界面已建 = sim battle_skip 消费通道);即时 XP 腿已挂 '
             'xp_instant=30(现金计分)',
    # 合并同类项:金腿 = 刷新出对条件金(gold_per_refresh_pair,登记形态
    # 等值迁移自 instant_gold);burst 4 刷腿已建模(获得链登记腿发放),
    # 不列缺口。估值 fail-closed 申报句形态照现役值句。
    '合并同类项': '刷新出对条件金腿(gold_per_refresh_pair)频次分布未采,'
                 '估值 fail-closed=0',
    # 大裁员:卖全场退款腿 = 无字段载体(退款额依赖场上构成,非估值常量;
    # 出售面世界通道已建 = STRATEGY_EFFECTS 条目登记腿双桥);×2 卖价修饰
    # 挂 sell_price_mult(待建模字段分类塌 0),施于净额/基础价口径待实采
    # (缺口单一源 = fields.md §4 SellBench 修饰行),闭合前世界面退款按
    # 基础公式记(sim 低估申报制)。
    '大裁员': '卖全场退款腿无字段载体(依赖场上构成,非估值常量);'
              '×2 卖价修饰(sell_price_mult)施径口径待实采,'
              '字段级估值 pending 归 _PENDING_MODELING_FIELDS',
    # 降本增效:免费购买腿已建(uses 载体 duration_uses=6,世界通道 =
    # STRATEGY_EFFECTS 条目 + 买牌上报免费闸);估值未入现金通道(免
    # 费省下的购牌金依赖后续购买行为,轨迹依赖族);×2 卖价修饰同大裁员
    # (sell_price_mult 轨迹依赖族待建模,施径口径待实采)。
    '降本增效': '免费购买腿(6 次,uses 载体已建,估值未入现金通道);'
              '×2 卖价修饰(sell_price_mult)施径口径待实采,'
              '字段级估值 pending 归 _PENDING_MODELING_FIELDS',
}


# ===== 金等价折算(单一入口)=====


def strategy_economy_value(name: str, gs: GameState) -> tuple[float, bool]:
    """策略卡经济通道金等价期望(单一入口;契约沿 env_economy.env_economy_value)。

    返回 ``(expected_gold, resolved)``;resolved=False = fail-closed
    (未入册/全默认无通道/非正金期望),消费端按无现金处理。
    无 economy 条目或全默认 → (0, False)(无通道可装,非异常)。

    **卡级待建模登记不设运行时闸**:STRATEGY_ECONOMY_PENDING_MODELING
    覆盖「无字段分支 ∪ 字段已登记未挂值分支」的可见性(治理账),已建模分支照常
    计分——狸财经狸的 interest_flat_per_node 活计分分支 × 剩余节点数照付
    (行为申报 7:计 2 金/节点流,取款/存款分支待建模塌 0);未建模字段
    天然不入下方通道公式 = 塌 0,建模落地加通道即自动进现金分。

    通道(值全部 = 注册表游戏定义【注】直读;剩余视界查表单一源 =
    策略门面 ``statefn/horizon.r_remaining``/``r_global`` 场字段自算,
    禁新写第三实现):
    - instant_gold:选卡当场一次性金,面值(**勿读 gold_next_nodes_amount
      代「现在」分支**——长期主义系「现在」分支由 amount 现值承载,误读即漏
      现在分支);
    - gold_at_final_supply:「进入最后一个补给阶段后」金,面值(尾款交付;
      必经节点条件金与 instant_gold 同桶);
    - gold_next_nodes:「现在」分支 amount + count 节点分支 amount ×
      min(count, max(剩余节点数 − 1, 0))——「接下来」不含当前节点,按
      ``剩余节点数 − 1`` 截断(剩余节点数含当前节点,R≤count 终局帧多计
      的 1 条分支消除);
    - gold_per_node × 剩余节点数(r_global 场字段自算,None 回退默认表);
    - gold_per_boss_node × 剩余 boss 节点数(场字段序列自当前节点(含)
      起 ``'boss'`` kind 直查;封顶 modeled planes,P3 虚拟末槽不再计入
      ——默认局 P1 段 3→2、P2 起 2→1,行为申报 details §8.3;含当前位面
      口径的偏差见模块 docstring 申报);
    - interest_flat_per_node × 剩余节点数(息上调整数分支,金等价直读);
    - xp_per_node × 剩余节点数 × XP_GOLD_RATE;
    - xp_instant × XP_GOLD_RATE。

    位置缺失帧:沿 env 屏先例退化 (1, 1) 现读(场字段/默认表读出照常)。
    """
    st = get_strategy(name)
    eff = st.economy if st is not None else None
    if eff is None or eff == EconomyEffect():
        return (0.0, False)

    node = gs.node.value
    if node is None:
        # 位置缺失帧退化 (1, 1)(沿 env 屏先例;分支行为有单测)
        cur_plane, cur_round = 1, 1
    else:
        cur_plane, cur_round = int(node.plane), int(node.round_num)
    remaining = r_global(gs, cur_plane, cur_round)

    acc = 0.0
    # 通道 1:选卡当场一次性金(面值;「现在」分支另由 gold_next_nodes 承载)
    if eff.instant_gold:
        acc += float(eff.instant_gold)
    # 通道 2:「进入最后一个补给阶段后」金(尾款交付;面值直入——必经
    # 节点条件金,与 instant_gold 同桶等值,估值零漂移)
    if eff.gold_at_final_supply:
        acc += float(eff.gold_at_final_supply)
    # 通道 3:「现在及接下来 count 次进节点每次 amount 金」分期金
    # (长期主义系;count 分支按「剩余节点数 − 1」截断——「接下来」不含
    # 当前节点,剩余节点数含当前节点)
    if eff.gold_next_nodes_amount and eff.gold_next_nodes_count:
        _compounds = min(eff.gold_next_nodes_count, max(remaining - 1, 0))
        acc += float(eff.gold_next_nodes_amount) * (1 + _compounds)
    # 通道 4:每节点金流
    if eff.gold_per_node:
        acc += float(eff.gold_per_node) * remaining
    # 通道 5:每 boss 节点金(剩余 boss 数 = 场字段序列自当前节点(含)
    # 起 'boss' kind 直查——替代停用的「位面末槽 × 每位面恰一 boss」几何
    # 假设,修饰局 boss 位移与未来序列变异天然正确;封顶 modeled planes,
    # P3 虚拟末槽不再计入 → 默认局 P1 段 3→2、P2 起 2→1(行为申报
    # details §8.3);当前节点即 boss 位时多计一笔已发放 boss 金的同族
    # 偏高申报见模块 docstring)
    if eff.gold_per_boss_node:
        _seqs = gs.node_seq_by_plane.value or PLANE_NODE_TABLES
        _from = max(1, cur_round) - 1   # 自当前节点(含)起;round 缺效防御同旧 or 1 支
        _bosses = sum(
            (seq[_from:] if k == cur_plane else seq).count('boss')
            for k, seq in _seqs.items() if k >= cur_plane)
        acc += float(eff.gold_per_boss_node) * _bosses
    # 通道 6:固定息(每节点固定息上调整数,金等价直读)
    if eff.interest_flat_per_node:
        acc += float(eff.interest_flat_per_node) * remaining
    # 通道 7:每节点 XP 流
    if eff.xp_per_node:
        acc += float(eff.xp_per_node) * remaining * XP_GOLD_RATE
    # 通道 8:即时 XP
    if eff.xp_instant:
        acc += float(eff.xp_instant) * XP_GOLD_RATE

    if acc <= 0.0:
        # fail-closed 门:非正金期望 = 无通道可计(全通道非负,0 即空)
        return (0.0, False)
    return (acc, True)


# ===== 构建期校验(import 即炸)=====


def _validate_field_classification() -> None:
    """EconomyEffect 全字段三分分类校验(未分类字段 = 建模缺口
    静默,炸出——沿 env 批立场表覆盖校验的治理形态,对象从 83 环境换成
    字段闭集)。

    扫 STRATEGY_ECONOMY 全表**非默认字段**:每个出现过的字段名必须落
    「计分/待建模/不计」三类之一(单一定义 = 唯一归属,双归属即炸);
    三分类并集必须恰覆盖 EconomyEffect 全字段闭集(注册表新字段未分类
    即炸,防静默塌 0)。"""
    from dataclasses import fields as _dc_fields

    _defaults = EconomyEffect()
    _seen: set[str] = set()
    for _eff in STRATEGY_ECONOMY.values():
        for _f in _dc_fields(EconomyEffect):
            if getattr(_eff, _f.name) != getattr(_defaults, _f.name):
                _seen.add(_f.name)
    _classified = _CASH_SCORED_FIELDS | _PENDING_MODELING_FIELDS | _NOT_SCORED_FIELDS
    _unclassified = _seen - _classified
    if _unclassified:
        raise ValueError(
            f"策略经济字段未分类(计分/待建模/不计三分缺位):{sorted(_unclassified)}")
    _double = (_CASH_SCORED_FIELDS & _PENDING_MODELING_FIELDS)
    _double |= (_CASH_SCORED_FIELDS & _NOT_SCORED_FIELDS)
    _double |= (_PENDING_MODELING_FIELDS & _NOT_SCORED_FIELDS)
    if _double:
        raise ValueError(f"策略经济字段双归属(分类互斥破):{sorted(_double)}")
    _all_fields = {_f.name for _f in _dc_fields(EconomyEffect)}
    _missing = _all_fields - _classified
    if _missing:
        raise ValueError(
            f"策略经济字段分类闭集缺位(EconomyEffect 新字段未入三分):{sorted(_missing)}")


def _validate_pending_modeling_registry() -> None:
    """卡级待建模登记校验(断言集合按 29 号稿 §2.1 定死,防「兜底」
    写成恒真断言):

    ① 键 = 注册表规范名(孤儿即炸);② 值非空(描述分支清单);
    ③ 「economy 条目已登记而 EconomyEffect 全字段默认的登记条目必须已登记」
    (现仅孪生素数——全默认卡不入字段分类校验视野,唯卡级登记可覆盖);
    ④ 按适用范围规则派生的登记卡闭集必须已登记(直调 5 张:固定理财/固定理财+/
    孪生素数/狸财经狸/超发货币——前两者兼「字段已登记未挂值」分支,后三者
    兼「无字段」分支)。混合卡的分支级明细不可自动验证,靠行为申报清单
    (29 号稿 §2.1)人工对账兜底。"""
    for _name in STRATEGY_ECONOMY_PENDING_MODELING:
        if _name not in INVESTMENT_STRATEGIES:
            raise ValueError(f"待建模在册孤儿键(注册表无此卡):{_name!r}")
        if not STRATEGY_ECONOMY_PENDING_MODELING[_name]:
            raise ValueError(f"待建模在册空描述:{_name!r}")
    # ③ 全默认 economy 条目必须已登记(现仅孪生素数,直调亲核)
    _default_eff = EconomyEffect()
    _all_default = {n for n, eff in STRATEGY_ECONOMY.items()
                    if eff == _default_eff}
    _missing_default = _all_default - set(STRATEGY_ECONOMY_PENDING_MODELING)
    if _missing_default:
        raise ValueError(
            f"全默认 economy 条目缺卡级待建模登记:{sorted(_missing_default)}")
    # ④ 适用范围规则派生闭集必须已登记(直调 5 张;固定理财系兼未挂值分支、
    # 后三者兼无字段分支——两适用范围形态各由本断言覆盖住代表)
    _required_closed_set = ('固定理财', '固定理财+', '孪生素数', '狸财经狸', '超发货币')
    _missing_closed = [n for n in _required_closed_set
                       if n not in STRATEGY_ECONOMY_PENDING_MODELING]
    if _missing_closed:
        raise ValueError(
            f"按辖域规则派生的待建模登记卡闭集缺位:{_missing_closed}")


_validate_field_classification()
_validate_pending_modeling_registry()
