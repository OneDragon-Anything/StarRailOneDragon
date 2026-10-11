# 环境条件发放 迭代设计(总纲)

## 0. 元信息

- 迭代目标:源迭代(invest-effects-calc)深井角斗场机制接入外溢。用户裁定(2026-10-10):触发点 = **结算屏连胜真值落账处**(首次 ≥5);获得财富宝钻**落位未知 → 随机态**写;「宝钻到手 → 重算上限」做成**共用函数**(sim 侧补给宝钻的既有上限缺口顺手闭合——**修订后调整:补给不采纳回调,该缺口不在本迭代闭合,见 §2 第 5 条**);live 上限靠观察域自动跟踪,**零回调**。
- 状态:定稿
- 文档清单:
  - details/env-conditional-grant.md —— 登记表、触发检查 kernel 函数、随机态发放与 done 标记、宝钻获得回调、live/sim 接线

## 1. 问题与动机

- 现状症状:
  1. 深井角斗场「本局首次达成 5 连胜时,获得【财富宝钻】」(data/cw_invest_data.py `PlazaPortal(id='104')`)**零建模**:sim 世界里该环境 = 白板;live 靠 equips/deploy_cap 观察覆盖被动兜住,无触发逻辑;
  2. 「达成条件 → 发放」的效果形状首次出现——既有发放通道覆盖「选卡立刻发」(ENV_GIFTS items_immediate)与「指定节点发」(items_scheduled),条件形状无归属;
  3. **sim 上限保真缺口**:sim 补给宝钻只写 `diamond_count +1`(sim/cw_sim_backend.py `_on_supply_picked`),不写 `deploy_cap`/`back_layout`——派生读口 `max_units_of(gs)`(kernel/cw_game_state.py,deploy_cap 真值 ≥level 才采信,封顶 前排4+back_layout)读旧字段,宝钻的 +1 团队槽在 sim 失效。
- 根因归层:**语义层**。「条件触发的发放」与「发放后的世界面联动」两条语义未建模——不是流程或表示问题(sim 结算与 live 结算的 streak 真值链都已存在且正确)。
- 解决到哪:条件发放 = 登记表(kernel 数据)+ 触发检查 kernel 函数(live/sim 同一单一源)+ 随机态发放 + done 标记;宝钻回调 = kernel 函数(唯一调用点 = sim 深井发放路径;supply 不采纳,见 §2 第 5 条)。
- 明确不解决:
  - **策略侧同形状卡**(钻石商人升 9 级/控制规模/多元化团队等)——触发状态与接线点各不相同(level 观察 vs 结算),不预建统一条件框架;本迭代交付的登记表 + 触发函数按「连胜触发器」命名,未来升级类条件卡各建各的触发接线(用户裁定:对应触发点多写几个触发函数更清晰,不强行合并);
  - 宝钻自身效果(团队槽 +1 拥有即算可叠加 / 装备者每 3 备战阶段 +1 金 / 红蓝钻合成)——全部已在册(deploy_cap/back_layout 观察链、cw_effect_inventory `equip_diamond_phase_gold`、合成 recipes),零改动;
  - **live 侧上限回调**——deploy_cap/back_layout 是观察真值域(识别器读屏覆盖),逻辑侧禁写(投影审计在册),宝钻到手下一备战帧识别器自动重算;
  - 恢复局「本局首次」真值不可知——接管局 done 标记为空、active_env 非空,首个结算若 streak ≥ 阈值会触发发放 = 最佳猜测;多发由 equips 观察**整表覆盖**纠偏,零持续污染(sim 无接管局)。接受并披露;
  - OCR 假阳(结算屏误读 5)→ 假发放永久占据一次性(done 不回收,真达成不再发),equips 猜值由观察纠偏;接受并披露(streak OCR 真值链校准另线);
  - **补给带钻选项的钻类型未建模**——sim 聚合计数 `diamond_count`(不分红/蓝/财富),其 cap 联动语义随钻类型建模另批;本迭代补给路径**零改动**(详见 §2 第 5 条)。

## 2. 方案

系统级变化(读一遍知全貌):

1. **登记表** `ENV_STREAK_GRANTS: dict[str, tuple[int, str]]`(cw_investments.py,键 = 环境规范名,值 = (连胜阈值, 装备名);深井角斗场 → (5, 财富宝钻)),三条 import 即炸校验;
2. **GameState 新域** `env_grants_done`(逻辑态;元素 (env, 条件键),一次性守卫标记),四件套 = 种子底座 + 快照恢复登记 + DEFAULT_GS_SCHEMA 独立键 + 投影审计行;
3. **触发检查 kernel 函数**(kernel/cw_env_grants.py 新模块,live/sim 同一单一源):`check_env_streak_grants(gs, streak_after, sig) -> str | None`——active_env 在册 ∧ streak_after 为连胜方向且 ≥ 阈值 ∧ (env, 条件键) ∉ done → **随机态发放**(write_logic_rand equips 追加,落位未知)+ done 追加(write_logic),返回被发装备名;
4. **live 接线**:结算覆盖写端调用点(cw_screen_battle_wait,`apply_settlement_cover` 之后)传入同一 streak_after;
5. **sim 接线**:结算 streak 写点(cw_sim_backend)调用;返回非 None 且装备为宝钻 → 调 **宝钻获得回调** `on_diamond_acquired(gs, 装备名)`(回调内构 obs 族 sig,见契约回调写法;diamond_count +1、deploy_cap = level + 拥有财富宝钻数、back_layout = min(9, 现值+1),observe 写 = sim 世界事实)。**补给宝钻不采纳回调**:补给带钻选项的钻类型未建模(聚合计数,可能是红/蓝/财富任一),红/蓝钻无 cap 语义,硬按财富宝钻回调 = 保真倒退——supply 路径零改动,钻类型建模另批。

跨详设接口契约(总纲定死,各详设不得另行演化):

- **触发检查单一源**:`check_env_streak_grants` 是条件判定的唯一实现,live 与 sim 都调它——同一条件两处各写一份判定 = 漂移(同 `roll_ore_reward` live/sim 共用的单一正确性来源理由,非「通用复用」);
- **登记表** `ENV_STREAK_GRANTS`(键 = 环境规范名,值 = (阈值, 装备名));构建校验:键 ⊆ `INVESTMENT_ENVS`(孤儿键防版本更新改名后静默失联)、装备名 ∈ `EQUIPMENTS`、阈值 ≥ 1;
- **done 标记域** `env_grants_done: Field[tuple[tuple[str, str], ...]]`(元素 (env, 条件键),条件键 = `'first_streak'`);种子 `()`、恢复 tuple 化、DEFAULT_GS_SCHEMA 独立键版本 1(**不并入 spheres/match_facts bump**)、投影审计行(完备性锁强制,晶矿迭代同款先例);
- **发放写通道铁律**:装备落位不可观察 → `write_logic_rand`(用户裁定 2026-10-10);done 追加 = `write_logic`(登记事实,直写先例 = cw_exec_state 金腿 / cw_effect_inventory 退款腿,不属 anchor_aware 族——域无观察写端);
- **sig 单形态(禁 obs_sig 进触发函数)**:live = logic_hook 族,group `'battle-wait:env-grant'`,actor `CwScreenBattleWait`;sim = `logic_sig('sim:env')`——`write_logic_rand` 渠道族校验会炸 obs_sig 形态;
- **回调边界**:live **不调**回调(deploy_cap/back_layout/diamond_count 的 live 写端 = 观察识别器,逻辑侧禁写);回调 = sim 专用,仅深井发放路径调用(见第 5 条,supply 不采纳);
- **回调写法**:三域全部 `gs.observe`(sim 世界事实 = 观察通道,先例 = `_on_supply_picked` 的 diamond_count observe 写),禁 logic 写(与晶矿 done 台账的直写不同——那是登记事实,这是世界数值面);**sig 由回调内部自构 obs 族**(如 `obs_sig(group_id='sim:env-diamond')`),入参不传 sig——observe 渠道校验只收 obs 族,复用调用方 logic 族入参首笔即炸。
