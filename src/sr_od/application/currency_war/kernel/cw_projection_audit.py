"""字段投影完备性审计注册面(观察对账族架构收束)。

**问题域**:统一观察对账失配告警(2026-09-16-unified-obs-reconcile)把「游戏侧
状态变更未投影进逻辑态」逐帧暴露为停局——逐例打补丁不可收敛(2026-09-18
五连停局实证,``.debug/temp/incidents/20260918-reconcile/``),本注册面把
**全部 GameState 容器字段**对「游戏侧变更是否会造成 observe 失配」做
一次性三分类申报,并锁「无写端无规则」集合清零:

1. ``write_end``:游戏侧该域的合法变更都有动作/结算/派生**投影写端**
   (bot 动作后逻辑态随写,或从观察数据派生写入);
2. ``absorb_rule``:存在**吸收规则**承接无写端的游戏侧变更(结算真值收束
   ``settle_truth``、豁免注册表、行内纯重排采新
   ``deploy_slot_reorder``);
3. ``observation_only``:字段**有观察读端但零逻辑写端**——observe 覆盖
   逻辑态不存在,失配比对(``observe()`` 仅在 ``target.source == 'logic'``
   分支路由)结构上不可达,天然无停局面;
4. ``process_only``:字段**无观察读端**(bot 自有事实/派生面/回执)——
   观察覆盖永不触及,同属结构上不可失配。

三/四态的关系:任务口径的三分类里,「无写端无规则」= 可失配面(status ∈
{write_end, absorb_rule} 才合法出现)中既无写端也无规则的缺口,经本次审计收束
后**恒空**(由测试仓 test_board_derived_and_reorder.py 完备性测试);
observation_only / process_only 是「结构上不可失配」的声明性收束,非缺口。

**维护纪律**:新增 GameState 容器字段必须在 :data:`PROJECTION_AUDIT`
登记行(登记缺失 = 完备性测试红);行内容变更走 review 可见,禁运行时
改写。人读镜像 = 迭代目录 ``projection-audit.md``(生成自本表,改表须
同步改镜像)。
"""
from __future__ import annotations

from dataclasses import dataclass

#: 审计状态枚举(语义见模块 docstring;禁扩静默,新状态须先过架构裁决)。
AUDIT_WRITE_END: str = 'write_end'
AUDIT_ABSORB_RULE: str = 'absorb_rule'
AUDIT_OBSERVATION_ONLY: str = 'observation_only'
AUDIT_PROCESS_ONLY: str = 'process_only'
AUDIT_STATUSES: tuple[str, ...] = (
    AUDIT_WRITE_END, AUDIT_ABSORB_RULE, AUDIT_OBSERVATION_ONLY,
    AUDIT_PROCESS_ONLY)


@dataclass(frozen=True)
class ProjectionAuditRow:
    """一个容器字段的投影完备性申报行。

    - ``status``:四态之一(:data:`AUDIT_STATUSES`);
    - ``basis``:一行持久依据(写端 evidence 名 / 吸收规则符号名 /
      不可失配的结构理由);basis 是 review 面与排障入口,写机制名不写
      会话局部指代。
    """

    status: str
    basis: str


#: 全字段审计表(键 = GameState 容器字段名;完备性测试:GameState 全部
#: Field 域 ⊆ 本表,本表键 ⊆ Field 域,双向对齐)。分组注释与表行同序。
PROJECTION_AUDIT: dict[str, ProjectionAuditRow] = {
    # —— 节点族(观察覆盖,派生规则写端)——
    'node': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='派生规则四条分支(备战解析/弹窗/位面过渡/BOSS简报)write_logic + 两帧确认门'
              '(链正本 §2-4);商店查链目标 = 生效序与镜像最新者'
              '(_shop_panel_type_target,20260918-reconcile 第 11 例)+ '
              '类型直定倒退免疫(镜像序领先丢弃留证);观察每帧覆盖'),
    'node_path': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='链写端 = 备战帧链读 + maybe_emit_chain_diff 两帧确认;'
              '基线位面入口写定'),
    'node_path_baseline': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='位面入口写定恒稳(链正本 §2),局中不被链读覆盖'),
    # —— 单位域(可失配面核心;吸收规则族)——
    # 星级读数 = 席位单元属性(非独立容器字段),其识别层单帧抖动的吸收
    # 规则 = star_two_frame_gate(kernel/cw_reconcile 槽位锚定 + 两帧一致
    # 才采新),随席位三域写路径一并申报(出处 run_20260915_054718 §5)。
    'deployed': ProjectionAuditRow(
        status=AUDIT_ABSORB_RULE,
        basis='deploy/sell/swap 投影写端(单字段视图整值替换,'
              '容器合并)'
              ' + 行内纯重排采新'
              '(deploy_slot_reorder,20260918-reconcile 第5例收口;'
              '吸收口径 = 子表内单元级多重集相等,换排不吸收)'
              ' + 星级抖动门采新(star_two_frame_gate,槽位锚定+两帧一致)'),
    'bench': ProjectionAuditRow(
        status=AUDIT_ABSORB_RULE,
        basis='buy/sell/deploy/swap 投影写端 + 星级抖动门采新'
              '(star_two_frame_gate,槽位锚定+两帧一致)。已知缺口:投资卡'
              '随机授予现无写端无吸收(申报表族 2026-09-19 拆除待重设计),'
              '命中照真失配停'),
    'back_layout': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='识别口径真值(三信号裁决 = cw_back_layout,观察侧写),'
              '零逻辑写端'),
    'tracked_account_observed': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='观察状态簿记(接管失效/reconcile 锚定写),无 OCR 读端'),
    # —— 经济与成长 ——
    'gold': ProjectionAuditRow(
        status=AUDIT_ABSORB_RULE,
        basis='buy/sell/levelup/refresh 投影 + 结算真值收口 '
              '(settle_truth:边界收入随结算入账,boundary_income_credited 留证)。'
              '晶矿随机金走逻辑随机态,写端申报:生成写 = ore_reward_attach'
              '(挂接入口,含 rekey 重挂),兑现写 = collect_ore 上报'
              '(logic_rand_outcome 行收口,2026-10-10-ore-reward-attach);'
              '投资卡随机授予仍无写端(申报表族 2026-09-19 拆除待重设计),'
              '命中照真失配停'),
    'level': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='买经验上报升档直写(f810f2454 投影补 level 域)+ prep 分支'
              '推进(xp_apply_clicks 单一源)+ 观察覆盖'),
    'xp': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='买经验上报/prep 分支推进(xp_apply_clicks)+ 观察覆盖'),
    'streak': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='纯观察读面(结算带符号 vs 备战 magnitude 双源留证),'
              '零逻辑写端'),
    'pending_loss': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='败态挂账(战斗结算失败分支写,轮首收入败补支消费即清;'
              'sim 写端 = sim/cw_sim_backend;实机写端候结算屏败局观察)'),
    'shop_locked': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='整店锁(字段先行占位:动作词表无锁通道,首版恒解锁;'
              '实机写端候实机补档)'),
    'diamond_count': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='宝钻计数(UI 可见;补给带钻选项授予写端 = sim 后端;'
              '实机写端候实机补档)'),
    'hp': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='结算覆盖 apply_settlement_cover(唯一真值入口)+ 宝物加血'
              '投影(EffectLedgerBridge)+ 词缀域写尾回调先验重算'
              '(write_prior,T-45 敌后破坏删除分支经 cw_opening_hp.'
              'on_enemy_affixes_logic_write,与开局先验同通道);写闸 §3.2.13'),
    'level_up_cost': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='识别真值(None=未读到禁兜底),零逻辑写端'),
    'deploy_cap': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='识别口径真值(双帧一致采信门),零逻辑写端'),
    # —— 局级事实(开局写定恒稳族)——
    'selected_difficulty': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='开局写定恒稳(cw_strategy_manager 职级写入)+ 观察覆盖'),
    'game_mode': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='标准/超频两屏无建档,写端接线前申报位(§3.1.2)'),
    'enemy_difficulty': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='非单调识别真值(§3.2.14),零逻辑写端'),
    # —— 局级观察面 ——
    'plane_bosses': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='位面 boss 名(简报读数/位面详情实采写门;开局写定恒稳族)'),
    'active_env': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='动作落地相获得链写(gain_invest_env)+ 观察覆盖'),
    'enemy_affixes': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='开局写定(简报/位面详情实采写门;位面详情写门随机态分支'
              '走 observe 覆盖转正,T-45)+ 获得链删除分支(敌后破坏失效'
              '删除,经 _select_write 择道随机态)+ 观察覆盖'),
    'board': ProjectionAuditRow(
        status=AUDIT_ABSORB_RULE,
        basis='派生量:deployed 写端挂钩 _resync_board_delta'
              ' 自动重算,禁独立手写 + 派生漂移观察覆盖采新'
              '(board_derived_adopt,安灯不响);观察侧 badge OCR 双源仲裁'),
    'shop_refresh_cost': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='刷新费现场 OCR(live)+ sim 开店呈现写回(观察通道,'
              'kernel 渲染 world_shop_refresh_cost 现算;零逻辑写端)'),
    # (刷新计数组口径(2026-09-21 Field 化):免费刷新剩余次数升格容器
    #  字段 free_refresh_left(审计行见下方家族块);付费/全量两计数留
    #  效果账本 ActiveEffectInventory,审计面 = 账本自身测试面。)
    'prev_node_spent': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='上节点花费位(§3.3.9,仅逻辑写)'),
    'free_refresh_left': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='商店免费刷新剩余次数(屏上「免费刷新 N」观察真值;观察写端'
              ' = 入口观察漏斗刷新钮三态锚定,免费态锚次数/付费域锚 0/判不出'
              '跳写)+ 动作扣减/发放登记 logic 直写(burst 桥/节点边界桥/'
              '合成事件腿三发放写端,后者宿主 = cw_effect_inventory;观察'
              '覆盖失配走 Field 既有安灯)'),
    'encounter_refresh_left': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='遭遇刷新剩余次数(屏上「剩余次数：N」观察真值;观察写端'
              ' = report_screen_encounter_obs 摄入,读缺跳写;§3.4.1)'
              ' + 观察覆盖'),
    'supply_refresh_left': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='补给刷新剩余次数(屏上「剩余次数：N」观察真值;观察写端'
              ' = report_screen_supply_node_obs 摄入,读缺跳写;sim 写端'
              ' = 补给节点入口初始 left 与刷新递减;§3.4.2)'
              ' + 观察覆盖'),
    'env_refresh_left': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='投资环境刷新剩余次数(屏上「剩余次数：N」观察真值;观察写端'
              ' = report_screen_invest_env_obs 摄入,读缺跳写;§3.4.3)'
              ' + 观察覆盖'),
    'strategy_refresh_left': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='投资策略逐卡刷新剩余次数(键 = 规范卡名;观察写端 = '
              'report_screen_invest_strategy_obs 摄入「刷新次数N」,读缺键'
              ' 跳写;§3.4.4) + 观察覆盖'),
    'active_strategies': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='动作落地获得链写(gain_invest_strategy:按名字去重追加)'
              ' + 观察覆盖(持卡列表)'),
    'unlocked_experts': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='本局已解锁专家顾问(获得链 advisor 道权威写:on_env_gained/'
              'on_strategy_gained/on_equipment_gained 解锁原语,只增去重;'
              '池派生消费 = cw_pool) + 专家邀请函通道申报行缺口'
              '(pick_expert_name_unobserved,候选名观察建档批接线);'
              '商店出现未登记专家 = 观察覆盖采新'),
    'pending_item_grants': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='定时道具发放队列(唯一逻辑写端 = 获得链:on_env_gained 登记'
              '入队 / discharge_due_item_grants 到点消费回写),队列 = 卡文'
              '推算知识,无观察读端'),
    'pending_strategy_offers': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='策略延时 offer 倒计时队列(唯一逻辑写端 = 获得链登记腿入队'
              ' / 节点边界 tick 递减 / sim 呈现腿弹除回写),队列 = 卡文'
              '推算知识,无观察读端;实机局呈现腿不接(不对称申报,'
              'pending_item_grants 同款)'),
    'pending_strategy_grants': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='策略延时发放倒计时队列(唯一逻辑写端 = 获得链登记腿入队'
              ' / 节点边界 tick 递减 / sim 发放腿弹除回写),队列 = 卡文'
              '推算知识,无观察读端;实机局发放腿不接(不对称申报,'
              'pending_strategy_offers 同款:发放物以 equips 观察首见'
              '入账)'),
    'strategy_conditional_done': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='策略卡条件发放已发标记(幂等守卫「首次」,元素 = 规范卡名'
              '或复合键 first_buy_xp#<费用>,局内恒存随快照存续),无观察'
              '读端——发放登记事实非观察投影(同族行先例 = '
              'env_grants_done);逻辑写端六处 = '
              'cw_gain_chain.check_strategy_conditional_grants(tick 位'
              '检查腿,发放成功 placed 刻追加;拒落域不闩自愈重试)+ sim '
              '到级金腿闩笔(check_strategy_level_grants 决策、sim advance '
              '双点接线段写,producer strategy_level_grant)+ 策略卡到级'
              '装备腿(check_strategy_level_equip_grants 直写形态,live '
              '结算位 + sim advance 双点同链,producer '
              'strategy_level_equip_grant)+ 全都要族选卡事件消耗闩'
              '(check_strategy_take_all_supply 挂补给选定上报三 applied '
              '出口,事件消耗制每事件耗 1 格,计数键 take_all#<卡名>#<序号> '
              '前缀计数 < 配额(map 银 1/金 2),producer '
              'CwScreenSupplyNode 未选域发放写端家族值)+ 策略卡首购经验'
              '桶闩(check_strategy_first_buy_xp_grants 挂买牌上报尾段,'
              'evidence first_buy_xp#<费用>,先闩后 sim 世界写 '
              'xp:first_buy:* at-most-once,producer '
              'strategy_first_buy_xp_grant)+ 策略卡购买翻星消耗闩'
              '(mark_strategy_buy_star_flip_consumed 挂买牌上报 applied '
              '后尾段,纯卡名键,evidence strategy_buy_star_flip:<卡名>,'
              '翻转在落位拍先于闩写 at-most-once,producer '
              'strategy_buy_star_flip_grant)'),
    'strategy_hp_loss_accum': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='损血档位触发累积器(「每损失20点」按当前局全程累计实际'
              '损血,发放刻取模余数结转,周期型触发器无 done 闩),无观察'
              '读端——发放记账过程量(同族行先例 = env_grants_done/'
              'ore_declared_done);唯一逻辑写端 = cw_gain_chain.'
              'check_strategy_hp_loss_grants'),
    'strategy_char_grant_bindings': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='绑定型随机角色授予名字绑定域(键 = 卡规范名,值 = 获得时点'
              '采样掷得的绑定角色名;持续型值非「首次」布尔闩,与 '
              'strategy_conditional_done 分域),无观察读端——掷骰结果非'
              '画面可读面;唯一逻辑写端 = cw_gain_effects.'
              '_make_bound_char_grant_effect(采样后 sim 门控写,live 零写'
              ':live 掷骰是猜测且本域为复制发放腿唯一判据,假绑定静默存续'
              '不可接受);消费端 = cw_gain_chain.'
              'check_strategy_node_char_grants(持卡未绑定 fail-closed 零'
              '发放留证 gain_chain_strategy_char_bind_missing)'),
    'strategy_gold_next_nodes_left': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='分期金剩余腿数容器(键 = 卡规范名,值 = 该卡剩余「进入新'
              '节点」发金腿数;每卡独立条目非聚合槽,双持姊妹卡各键并存,'
              '与 strategy_char_grant_bindings 同形),无观察读端——剩余'
              '腿数 = 卡文推算知识,游戏 UI 无读面;唯一逻辑写端两处 = '
              'cw_sim_backend._on_invest_picked(拿卡落地拍初始化,值 = '
              '注册值 gold_next_nodes_count 直接赋值,重置语义 = 排除闸'
              '下防御性默认)与 _begin_node_window 收入段分期金腿(发金'
              '与递减同拍),均 sim 门控写,live 零写——live 分期发放由'
              '游戏自算自显,金整字段观察覆盖收口'),
    'strategy_bond_battle_armed': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='策略卡羁绊条件战后发放武装标记(三态 None=未观察/False='
              '已消费/True=武装;触发-发放两拍制状态载体:结算拍评估「持卡'
              ' ∧ 战斗完成 ∧ 激活羁绊数 ≥ 表载阈值」置 True,下一节点窗'
              '拍采样交付后置 False),无观察读端——条件评估真值系 sim '
              '世界内部判定(板面激活数),live 无独立观察通道(装备入栏 '
              '= equips 观察覆盖);唯一逻辑写端两处 = cw_gain_chain.'
              'check_strategy_bond_battle_grants(武装)/ '
              'discharge_strategy_bond_battle_grants(消费),唯一调用点 '
              '= sim 结算腿与节点窗收口腿'),
    'strategy_bond_tier_fired': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='策略卡羁绊档位条件发放已发档位闩(逐档「首次」簿记,元素 '
              "= '<卡名>#<档位>' 复合键,first_buy_xp#<费用> 复合键同款;"
              '降档再回不弹,祈愿首达档簿记判例),无观察读端——条件评估真值'
              '系 sim 世界内部判定(板面激活数),live 无独立观察通道(星徽'
              '入栏 = equips 观察覆盖,不对称申报同族先例);唯一逻辑写端 '
              '= cw_gain_chain.check_strategy_bond_tier_grants(发放落位'
              '刻逐档追加,拒落域不闩重试自愈),唯一调用点 = sim 结算腿'),
    'round_fresh_buys': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='轮内新鲜买入账(record_fresh_buy 单口),无 OCR 读端'),
    # —— 持久账本 ——
    'equips': ProjectionAuditRow(
        status=AUDIT_ABSORB_RULE,
        basis='sell 回收/穿戴扣减/桥直写 + 工具动作上报写端(cw_action_'
              'report/tool_use:消耗移除与效果同笔合并写,炉随机面 = '
              'logic_rand 采样链)+ 策略卡世界发放具名装备写端'
              '(获得链 gain_equipment 确定发放尾追:延时发放/条件发放'
              '两通道)。已知缺口:投资卡随机装备授予现无写端无吸收'
              '(申报表族 2026-09-19 拆除待重设计,维持待其实现批消化),'
              '命中照真失配停'),
    'consumables': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='消耗品库存读面(§3.2.16),零逻辑写端'),
    'occupied_equips': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='已穿装备位置读面(装备域姊妹面,黑板帧退役时立域;写端单一源 = CwScreenPrep 观察'
              '装配点),零逻辑写端'),
    'spheres': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='晶矿视觉域(§3.2.8,点击目标非席位居民),零逻辑写端'
              '(点击摘除 = write_logic_rand 随机态写,非 write_logic)'),
    # —— 晶矿附着奖励与声明通道(
    #    通道分工 = 附着值走随机态独立域,不进 spheres 观察面)——
    'ore_rewards': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='附着奖励随机态域(键 = 矿身份最新观察坐标,容差配对轨迹'
              '继承),无观察写端——附着值是可能世界快照非画面真值,observe '
              '覆盖结构上不可达;写端 = cw_ore_channel 挂接入口(rekey/生成/'
              '清理,write_logic_rand)+ collect_ore 兑现摘除;读端 = '
              'collect_ore 兑现,策略禁读(契约 = cw_prep_actions 模块头/'
              'select_ore_clicks docstring,消费门不可信侧口径先例 = '
              'cw_hp_policy.hp_readable)'),
    'ore_declared_pending': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='声明待兑现队列(卡文推算登记非观察投影,游戏 UI 无'
              '「待发放列表」可读;同族行先例 = pending_item_grants),'
              '无观察读端;唯一逻辑写端 = cw_ore_channel(入队电平/'
              '消费移除/位面过渡过期)'),
    'ore_declared_done': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='声明已消费标记(幂等守卫第二分支,随快照存续),无观察读端;'
              '唯一逻辑写端 = cw_ore_channel(消费追加/位面过渡过期清理)'),
    'env_grants_done': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='环境条件发放已发标记(幂等守卫,元素 (env, 条件键),局内'
              '恒存随快照存续;键清单含纯具名 first_streak/refresh_threshold/'
              'interest_threshold/dot_confirm/battle_co_presence 与键值载荷 '
              'star_grant#<名>/'
              'boss#<位面>-<轮> 周期键/dot_anchor#<位面>-<轮> 纯登记锚键/'
              'dot_battle#<k> sim 进度键/ore_open#<阈值> 晶矿开启阈值键/'
              'deploy_lock_uid#<uid> 赠卡锁完胜作用域键/bond_tier_<档位> '
              '击破档位触发器),'
              '无观察'
              '读端——发放登记事实非观察投影(同族行先例 = ore_declared_'
              'done);逻辑写端 = cw_env_grants 触发函数族单一写端族 '
              '(check_env_streak_grants/check_env_refresh_grants/'
              'check_env_interest_grants/check_env_boss_grants/'
              'check_env_dot_grants/check_env_ore_open_grants/'
              'check_env_battle_grants'
              '(发放刻/证实刻追加,dot 三键与 battle_co_presence 见'
              ' fields.md §3.5.5)'
              '/grant_env_bond_tier(羁绊档位发放刻追加,判定住 '
              'cw_faction_callbacks.check_env_bond_tier_grants,deployed '
              '写尾门外必查)'
              '+ cw_gain_chain.on_env_gained(随机装备绑定分支 star_grant#,'
              'placed 守卫下追加;持续伤害契约锚键分支 dot_anchor#,节点窗'
              '开才写;赠卡锁分支 deploy_lock_uid#,发放刻追加);'
              'check_env_merge_grants 零 done 写'
              '(合并升星事件携带事实,无一次性封账面,显式零写非枚举遗漏)'),
    'env_grant_deploy_locks': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='环境发放角色上场锁(实例粒度,元素 (char_id, uid, 解锁序位'
              ' NodePos),发放刻由发号计数器配对赋号,无观察读端——锁状态'
              ' = 模型推导非画面读面〔实机「备战席哪张被锁」识别未建,识别'
              '专项后补〕;逻辑写端 = cw_env_grants(check_env_battle_grants'
              ' 触发发放 + check_env_deploy_lock_perfect 完胜改写)+ '
              'cw_gain_chain(环境获得链赠卡分支)三口,消费端 = deploy_move/'
              'swap_deploy 上报入口锁守卫 deploy_lock_block_reason;比对'
              '自愈无主动清理,记录滞留至局终'),
    'pending_item_opens': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='环境倒计时件开盒队列(T-34 命运礼物,元素 (件名, 解锁序位'
              ' NodePos),无观察读端——队列 = 卡文推算知识,战利品区板件'
              '显示另建观察域 giftbox_sight〔旁路读数留证,本队列三写端与'
              '语义不受其影响〕;'
              '逻辑写端 = cw_gain_chain.on_env_gained 登记入队 + '
              'discharge_due_item_opens 到点弹除(sim 进节点收口,实机'
              '不接)+ check_env_item_open_perfect 完胜回退三口,消费端'
              ' = 开盒原语单一;到点比对自愈无主动清理'),
    'giftbox_sight': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='惊喜盒板件 ⏳N 读数观察域(纯旁路证据,设计 '
              '2026-10-19-giftbox-piece-obs):观察读端 = 备战观察 heavy '
              '段挂接入口(report_giftbox_sight_observed 单一写径,读到才'
              '整条替换写、读不到零写),零逻辑写端;模型世界真值 = '
              'pending_item_opens 队列,本域不参与任何行为分支、运行时'
              '零比较零纠偏,与队列不一致 = 离线校准对账留证'),
    'env_grant_uid_seq': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='环境发放实例号发号计数器(发放刻单调发号上界,无观察读端'
              '——纯进程内发号器;逻辑写端 = cw_env_grants.'
              'check_env_battle_grants 发放刻 + cw_gain_chain.on_env_gained'
              ' 赠卡锁分支发放刻双口,配对消费 = 锁记录 uid'),
    'node_seq_by_plane': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='逐位面节点序列场字段(T-8;键 = 位面 1 基,值 = 节点类型序,'
              'None = 未注册回退默认表),无观察读端——序列由环境 desc 规则'
              '化确定可计算,观察对账走节点行 CV 读→live 台账独立通道(失配'
              '留证不自动改写);唯一逻辑写端 = cw_gain_chain.gain_invest_env '
              "尾段(evidence='node_seq:env',注册即落全量)"),
    # —— 交互状态 ——
    'prep_substate': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='分类子态四档(§3.2.17;恢复锁定档 = 会话推断,接管协议'
              ' §6.3 写),零对账冲突面'),
    'event_overlay': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='浮层双义读面(§3.6.1),零逻辑写端'),
    'overflow_warning': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='观察 + 获得链逻辑双写端(cw_gain_chain 溢出落位,角色/占席'
              '道具同款)+ CwActionSellBenchParam 溢出分支 logic 直写 False'
              '(推算消亡,观察赢)'),
    'overflow_card': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='观察 + 获得链逻辑双写端(cw_gain_chain 溢出落位直写身份,'
              '角色 char_id/占席道具名两分,BENCH_ITEM_NAMES 判 kind)'
              ' + 溢出分支入位消费直写(§3.2.20)'),
    # —— 画面附加域(payload 随画面重建)——
    'shop': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='CwActionBuyCardParam payload 投影(proj_buy_payload)+ 关店执行位离屏'
              '清场(CwActionCloseShopOp 自上报 report_action_close_shop_param'
              ' → leave_screen;sim 与实机同一动作 op)'
              ';刷后牌面 = 随机态采样 + 重观察覆盖'),
    'encounter': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='遭遇屏 OCR 读入逻辑写(每 visit 重建,等值覆盖)'),
    'supply': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='补给屏 payload 读面(随画面重建),零独立逻辑写端'),
    # —— 选择族 opts 槽(观察读面)——
    'invest_strategy_opts': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='选择族读面(终态契约 landing §3.1),零逻辑写端'),
    'invest_env_opts': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='选择族读面(环境选卡 OCR),零逻辑写端'),
    'megastar_opts': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='选择族读面,零逻辑写端'),
    'partner_opts': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='选择族读面,零逻辑写端'),
    'planner_opts': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='选择族读面,零逻辑写端'),
    'star_tome_opts': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='选择族读面,零逻辑写端'),
    'wish_trial_opts': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='选择族读面,零逻辑写端'),
    'box_card_names': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='选择族读面,零逻辑写端'),
    'star_tome_opts_xy': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='选项坐标伴随域(fields.md §3.4.5a):与同名名字域同一次观察'
              '同帧同源写,零逻辑写端'),
    'wish_trial_opts_xy': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='选项坐标伴随域(fields.md §3.4.5a):与同名名字域同一次观察'
              '同帧同源写,零逻辑写端'),
    'box_card_names_xy': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='选项坐标伴随域(fields.md §3.4.5a):与同名名字域同一次观察'
              '同帧同源写,零逻辑写端'),
    'fortune_opts_xy': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='选项坐标伴随域(fields.md §3.4.5a):与同名名字域同一次观察'
              '同帧同源写,零逻辑写端'),
    'fortune_opts': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='选择族读面,零逻辑写端'),
    'expert_invite': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='邀请函 payload 读面(§3.4 契约扩员),零逻辑写端'),
    # —— 十事件屏选择结果(bot 决策事实)——
    'chosen_encounter': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='选择族读面 + 动作侧发射即写(遭遇扩围批:写端迁 '
              'cw_action_report/pick_encounter.py,发射即写;兑现后清)'),
    'encounter_reward_claimed': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='遭遇奖励兑现记录(结算兑现回调 claim_encounter_reward 写:'
              '双证判遭遇 + progress_delta>0 单判,兑现即清 chosen_encounter'
              ' 单次消费;遥测接线候批)'),
    'chosen_supply': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='补给选择结果(handler 写,无 chosen 观察读端)'),
    'unchosen_supply': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='补给未选列快照(画面 op 真选分支确认窗写,双消费即清 = '
              'check_strategy_supply_salvage(R-entry 打捞腿)+ '
              'check_strategy_take_all_supply(全都要族 R-choice 选卡'
              '时点,先到——选卡即清,打捞腿下一补给进入后到早退零写);'
              '无观察读端)'),
    'chosen_megastar': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='盛会之星选择结果(handler 写,无 chosen 观察读端)'),
    'chosen_partner': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='伙伴选择结果(handler 写,无 chosen 观察读端)'),
    'chosen_wish': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='祈愿试炼选择结果(handler 写,无 chosen 观察读端)'),
    'chosen_fortune': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='命运卜者选择结果(chosen 写端未接线 = fields.md §4 先补档,'
              '无 chosen 观察读端;建档在册 cw_fortune_picker.yml)'),
    'chosen_hack': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='骇入策划选择结果(handler 写,暂无画面建档)'),
    'chosen_expert': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='专家邀请选择写入 + 邀请屏 chosen 观察(§3.4)'),
    'chosen_tome': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='星徽秘典弹窗卡名(handler 写,无 chosen 观察读端)'),
    'chosen_equip': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='装备三选一结果(handler 写,暂无画面建档)'),
    'lv999_cost_tier': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='银狼LV.999 当前费用档(动作报告写:升费分支/上阵变费分支;'
              '读口 = cw_economy.effective_cost)'),
    # —— 结算 ——
    'settlement': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='结算覆盖链真值(apply_settlement_cover,消解后'
              ' hp 唯一真值入口)'),
    'hp_floor_triggered': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='hp 保底事件位(§3.5.3,纯观察登记无判据载体)'),
    # —— 派生域与画面上下文 ——
    'prev_screen': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='实机 = 观察汇聚(observe_screen_context,R1 §3.1.4);'
              'sim = _announce_screen 容器广播(evidence screen: 前缀,'
              '值级豁免结算/大厅屏,迭代 2026-10-16-sim-screen-announce)'),
    'current_screen': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='实机 = 观察汇聚(observe_screen_context);'
              'sim = _announce_screen 容器广播(第二写点,'
              '迭代 2026-10-16-sim-screen-announce)'),
    'top_bar_raw': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='顶栏原文观察层字段(用户终裁 2026-09-11 字段层次终极版:'
              '原文缺读不写禁猜),零逻辑写端'),
    'node_pos': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='两态序键:锚定态 observe_node_anchor 直写 observation / '
              '推进态 report_node_advance 经推进原语写 logic(值 = '
              '(位面,轮) 元组键,2026-10-12-abolish-node-ordinal)'),
    # —— 回执与局终 ——
    'receipts': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='动作回执滚动窗(note_action_receipt 单点),无 OCR 读端'),
    'match_final': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='局终行载荷(write_match_final 单点,段内幂等),无 OCR 读端'),
}


def audit_missing_fields(field_names: list[str]) -> list[str]:
    """完备性测试半边:GameState Field 域中未在本表登记的字段名。"""
    return [f for f in field_names if f not in PROJECTION_AUDIT]


def audit_stale_keys(field_names: list[str]) -> list[str]:
    """完备性测试另半边:本表中已不存在的字段键(字段停用后残留)。"""
    return [k for k in PROJECTION_AUDIT if k not in set(field_names)]


def audit_bad_status_keys() -> list[str]:
    """状态枚举外/缺口态的键(「无写端无规则」恒空的表内表达:
    合法状态只有四态,可失配面必须落在 write_end/absorb_rule)。"""
    return [k for k, row in PROJECTION_AUDIT.items()
            if row.status not in AUDIT_STATUSES]


#: 已知停局家族的机制必含关键词(完备性测试的抽检半边:五连停局各域的
#: 收束机制必须仍在其位——防后续重构悄悄拔掉吸收/派生面)。
_STOP_FAMILY_MECHANISMS: dict[str, tuple[str, ...]] = {
    'bench': ('star_two_frame_gate',),
    'gold': ('settle_truth',),
    'deployed': ('deploy_slot_reorder', 'star_two_frame_gate'),
    'board': ('_resync_board_delta', 'board_derived_adopt'),
    'node': ('_shop_panel_type_target',),
}


def audit_family_mechanism_missing() -> list[str]:
    """抽检测试:停局家族字段的 basis 丢失机制关键词的键。"""
    out: list[str] = []
    for field_name, keys in _STOP_FAMILY_MECHANISMS.items():
        row = PROJECTION_AUDIT.get(field_name)
        if row is None:
            out.append(field_name)
            continue
        if any(k not in row.basis for k in keys):
            out.append(field_name)
    return out
