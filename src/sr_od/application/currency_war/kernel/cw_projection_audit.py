"""字段投影完备性审计注册面(观察对账族架构收口;T-40)。

**问题域**:统一观察对账安灯(2026-09-16-unified-obs-reconcile)把「游戏侧
状态变更未投影进逻辑态」逐帧显影为停局——逐例打补丁不可收敛(2026-09-18
五连停局实证,``.debug/temp/incidents/20260918-reconcile/``),本注册面把
**全部 GameState 容器字段**对「游戏侧变更是否会造成 observe 失配」做
一次性三分类申报,并锁「无写端无规则」集合清零:

1. ``write_end``:游戏侧该域的合法变更都有动作/结算/派生**投影写端**
   (bot 动作后逻辑态随写,或从观察数据派生写入);
2. ``absorb_rule``:存在**吸收规则**承接无写端的游戏侧变更(结算真值收口
   ``settle_truth``、豁免注册表、行内纯重排采新
   ``deploy_slot_reorder``);
3. ``observation_only``:字段**有观察读端但零逻辑写端**——observe 覆盖
   逻辑态不存在,失配比对(``observe()`` 仅在 ``target.source == 'logic'``
   分支路由)结构上不可达,天然无停局面;
4. ``process_only``:字段**无观察读端**(bot 自有事实/派生面/回执)——
   观察覆盖永不触及,同属结构上不可失配。

三/四态的关系:任务口径的三分类里,「无写端无规则」= 可失配面(status ∈
{write_end, absorb_rule} 才合法出现)中既无写端也无规则的缺口,本批收口
后**恒空**(锁 = 测试仓 test_cw_board_derived_and_reorder.py 完备性锁);
observation_only / process_only 是「结构上不可失配」的声明性收口,非缺口。

**维护纪律**:新增 GameState 容器字段必须在 :data:`PROJECTION_AUDIT`
登记行(登记缺失 = 完备性锁红);行内容变更走 review 可见,禁运行时
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


#: 全字段审计表(键 = GameState 容器字段名;完备性锁:GameState 全部
#: Field 域 ⊆ 本表,本表键 ⊆ Field 域,双向对齐)。分组注释与表行同序。
PROJECTION_AUDIT: dict[str, ProjectionAuditRow] = {
    # —— 节点族(观察覆盖,派生规则写端)——
    'node': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='派生规则四腿(备战解析/弹窗/0q/0p)write_logic + 两帧确认门'
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
    'front_row': ProjectionAuditRow(
        status=AUDIT_ABSORB_RULE,
        basis='deploy/sell/swap 投影写端 + 行内纯重排采新'
              '(deploy_slot_reorder,20260918-reconcile 第5例收口)'
              ' + 星级抖动门采新(star_two_frame_gate,槽位锚定+两帧一致)'),
    'back_row': ProjectionAuditRow(
        status=AUDIT_ABSORB_RULE,
        basis='deploy/sell/swap 投影写端 + 行内纯重排采新'
              '(deploy_slot_reorder,20260918-reconcile 第5例收口)'
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
              '晶矿随机金已改走逻辑随机态(collect_ore 采样直写,'
              'logic_rand_outcome 行收口,2026-09-20 logic-rand-sampling);'
              '投资卡随机授予仍无写端(申报表族 2026-09-19 拆除待重设计),'
              '命中照真失配停'),
    'level': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='CwActionLevelUpShopParam 升档直写(f810f2454 投影补 level 域)+ prep 腿'
              '推进(xp_apply_clicks 单一源)+ 观察覆盖'),
    'xp': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='CwActionLevelUpShopParam/prep 腿推进(xp_apply_clicks)+ 观察覆盖'),
    'streak': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='纯观察读面(结算带符号 vs 备战 magnitude 双源留证),'
              '零逻辑写端'),
    'hp': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='结算覆盖 apply_settlement_cover(唯一真值入口)+ 宝物加血'
              '投影(EffectLedgerBridge);写闸 §3.2.13'),
    'level_up_cost': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='识别真值(None=未读到禁兜底),零逻辑写端'),
    'deploy_cap': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='识别口径真值(ADR-0420 双帧一致采信门),零逻辑写端'),
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
    # —— 恢复旗标(bot 自有事实)——
    'resumed_match': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='恢复检测旗标(_mark_session_resumed 单口),无 OCR 读端'),
    # —— 局级观察面 ——
    'plane_bosses': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='位面 boss 名(简报读数/位面详情实采写门;开局写定恒稳族)'),
    'active_env': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='选卡确认挂点直写(active_env 写入)+ 观察覆盖'),
    'enemy_affixes': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='开局写定(简报/位面详情实采写门)+ 观察覆盖'),
    'active_strategies': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='选卡确认挂点登记 + 观察覆盖(持卡列表)'),
    'board': ProjectionAuditRow(
        status=AUDIT_ABSORB_RULE,
        basis='派生量:front_row/back_row 写端挂钩 _resync_board_delta'
              ' 自动重算,禁独立手写 + 派生漂移观察覆盖采新'
              '(board_derived_adopt,安灯不响);观察侧 badge OCR 双源仲裁'
              '(ADR-0417)'),
    'shop_refresh_cost': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='刷新费现场 OCR(ADR-0622),零逻辑写端'),
    # (刷新计数组三行——free_refresh_balance/paid_refresh_count/
    #  total_refresh_count——已随 2026-09-18 迁入裁决移出容器,审计面
    #  随域退役;账本侧审计 = 效果账本自身测试面。)
    'prev_node_spent': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='上节点花费位(§3.3.9,仅逻辑写)'),
    'encounter_refresh_used': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='节点屏刷新计数(on_outcome 发射型钩子,§3.4.1)'),
    'supply_refresh_used': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='节点屏刷新计数(§3.4.2)'),
    'env_refresh_used': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='节点屏刷新计数(§3.4.3,零写端申报不动)'),
    'strategy_refresh_used': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='节点屏刷新计数(§3.4.4,逐卡)'),
    'round_fresh_buys': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='轮内新鲜买入账(record_fresh_buy 单口),无 OCR 读端'),
    # —— 持久账本 ——
    'equips': ProjectionAuditRow(
        status=AUDIT_ABSORB_RULE,
        basis='sell 回收/穿戴扣减/桥直写。已知缺口:投资卡随机装备授予'
              '现无写端无吸收(申报表族 2026-09-19 拆除待重设计),'
              '命中照真失配停'),
    'consumables': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='消耗品库存读面(§3.2.16),零逻辑写端'),
    'occupied_equips': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='已穿装备位置读面(装备域姊妹面,迭代 2026-09-18-prep-obs-'
              'retirement 阶段 3.2 立域;写端单一源 = CwScreenPrep 观察'
              '装配点),零逻辑写端'),
    'spheres': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='晶矿视觉域(§3.2.8,点击目标非席位居民),零逻辑写端'),
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
        basis='观察每入口帧实读覆盖 + CwActionSellBenchParam 溢出腿 logic 直写 False'
              '(推算消亡,观察赢)'),
    'overflow_card': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='观察写端单一源 + 溢出腿入位消费直写(§3.2.20)'),
    # —— 画面附加域(payload 随画面重建)——
    'shop': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='CwActionBuyCardParam payload 投影(proj_buy_payload)+ 关店机械口离屏'
              '清场(CwOpCloseShop._clear_shop_payload → leave_screen;'
              'report_action_close_shop_param 同口 = sim 路径)'
              ';刷后牌面 = 续段重观察覆盖'),
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
    'fortune_opts': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='选择族读面,零逻辑写端'),
    'expert_invite': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='邀请函 payload 读面(§3.4 契约扩员),零逻辑写端'),
    'equip_pick_opts': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='选择族读面,零逻辑写端'),
    'encounter_refreshed_in_visit': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='刷新建议 per-visit 位(写 False/True 均 fail-loud),'
              '无 OCR 读端'),
    # —— 十事件屏选择结果(bot 决策事实)——
    'chosen_encounter': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='选择 handler 单次逻辑写入 + 事件屏 chosen 观察(§3.4)'),
    'chosen_supply': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='补给选择结果(handler 写,无 chosen 观察读端)'),
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
        basis='命运卜者选择结果(handler 写,暂无画面建档)'),
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
        basis='银狼LV.999 当前费用档(动作报告写:升费腿/上阵变费腿;'
              '读口 = cw_economy.effective_cost)'),
    # —— 结算 ——
    'settlement': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='结算覆盖链真值(apply_settlement_cover,ADR-0282 消解后'
              ' hp 唯一真值入口)'),
    'hp_floor_triggered': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='hp 保底事件位(§3.5.3,纯观察登记无判据载体)'),
    # —— 派生域与画面上下文 ——
    'prev_screen': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='观察汇聚唯一写点(observe_screen_context,R1 §3.1.4)'),
    'current_screen': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='观察汇聚唯一写点(observe_screen_context)'),
    'top_bar_raw': ProjectionAuditRow(
        status=AUDIT_OBSERVATION_ONLY,
        basis='顶栏原文观察层字段(用户终裁 2026-09-11 字段层次终极版:'
              '原文缺读不写禁猜),零逻辑写端'),
    'node_ord': ProjectionAuditRow(
        status=AUDIT_WRITE_END,
        basis='派生规则四腿全部 write_logic(逻辑层,用户终裁 2026-09-11);'
              '无观察写序键例外'),
    # —— 回执与局终 ——
    'receipts': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='动作回执滚动窗(note_action_receipt 单点),无 OCR 读端'),
    'match_final': ProjectionAuditRow(
        status=AUDIT_PROCESS_ONLY,
        basis='局终行载荷(write_match_final 单点,段内幂等),无 OCR 读端'),
}


def audit_missing_fields(field_names: list[str]) -> list[str]:
    """完备性锁半边:GameState Field 域中未在本表登记的字段名。"""
    return [f for f in field_names if f not in PROJECTION_AUDIT]


def audit_stale_keys(field_names: list[str]) -> list[str]:
    """完备性锁另半边:本表中已不存在的字段键(字段退役后残留)。"""
    return [k for k in PROJECTION_AUDIT if k not in set(field_names)]


def audit_bad_status_keys() -> list[str]:
    """状态枚举外/缺口态的键(「无写端无规则」恒空的表内表达:
    合法状态只有四态,可失配面必须落在 write_end/absorb_rule)。"""
    return [k for k, row in PROJECTION_AUDIT.items()
            if row.status not in AUDIT_STATUSES]


#: 已知停局家族的机制必含关键词(完备性锁的抽检半边:五连停局各域的
#: 收口机制必须仍在其位——防后续重构悄悄拔掉吸收/派生面)。
_STOP_FAMILY_MECHANISMS: dict[str, tuple[str, ...]] = {
    'bench': ('star_two_frame_gate',),
    'gold': ('settle_truth',),
    'front_row': ('deploy_slot_reorder', 'star_two_frame_gate'),
    'back_row': ('deploy_slot_reorder', 'star_two_frame_gate'),
    'board': ('_resync_board_delta', 'board_derived_adopt'),
    'node': ('_shop_panel_type_target',),
}


def audit_family_mechanism_missing() -> list[str]:
    """抽检锁:停局家族字段的 basis 丢失机制关键词的键。"""
    out: list[str] = []
    for field_name, keys in _STOP_FAMILY_MECHANISMS.items():
        row = PROJECTION_AUDIT.get(field_name)
        if row is None:
            out.append(field_name)
            continue
        if any(k not in row.basis for k in keys):
            out.append(field_name)
    return out
