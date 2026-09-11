# ADR-0533: 必花域备战期闩 + L3 资格拒分键 + 观测面实机接线(L3 断链排查修批)

## 背景

第二十~二十二局濒死段三局同构(hp1 金 43-56 闲置入死战),单局复盘与门链直调定谳:
L3 备战经验出口零发射不是资格门 bug,而是复合缺口的叠加效果——

1. **域豁免逐帧瞬时判定**:必花域豁免(G_must 边界内的危机让位压制)按当帧金位
   现算;商店域首笔消费把金拉回域内的瞬间,同备战期后续 prep 帧即失去豁免,
   被 P2 危机带 hp 门常态挂起——「花光」义务在域边界上蒸发(残金 43-56 闲置同构的根)。
2. **prep `_state_view` 硬置 xp 字段**:xp_progress/level_up_cost 置 None 使整批升级
   成本按 0 进度虚高(实例帧真 32g 虚 52g),在残金带构成 spend_unified 假拒的第二静默面。
3. **拒因零落盘**:上述两面的拦截都不产生 decisions 行可辨分键(「拒因不可辨」的直接来源),
   form_score 写者虽在但商店观察帧 deployed 恒空致实机恒 0。

## 决策

1. **必花域备战期闩**:本备战期曾入域即置 `session.cw4_must_spend_phase`
   (键式 (plane, round),与开店闩同构,跨期自动失效);闩存续帧域豁免保持,
   闩延命帧记 `must_spend_zone_latch_extend` 分键。「花光」义务闭环 = 花到
   整批买不齐/满级(与 P48/ADR-0528 自洽),非机械清零。
2. **L3 资格拒分键落盘**:`l3_reject_level_cap` / `l3_reject_batch_unaffordable`
   逐帧可辨;spend_unified 拦截自此显影(二十局候选 1 的盲区钉锁按锁的存在性
   纪律重推为可辨锚)。
3. **prep `_state_view` xp 现读透传**:state 现读、缺读帧维持旧兜底——消除
   成本虚高假拒。
4. **form_score 回退源**:商店观察帧 deployed 恒空(入口只播种 bench)→ 回退源
   接 `session.tracked_deployed`,板面真空照写 0 不虚构。
5. **实机遥测两件接线**(recorder.py + schema.py):`refresh_trigger` 分键 =
   决策行自 actions 的 RefreshShop.reason 计数(与 sim 账本行同键同语义,粒度
   差异=发射侧行级 vs 执行侧轮级,判读对账注意);`sess_terminal_release` 接回
   `terminal_release_bit` 单一源透传(schema docstring 同步)。

## Considered Options

- 采纳:备战期闩(治本于「域豁免时点粒度过细」)——与开店闩同构,零新参数。
- 拒:放宽危机让位 hp 门——禁令(20 号稿危机带语义在案)。
- 拒:域豁免改「本局曾入域」全局口径——过度豁免面不可控(非备战期消费也被豁免)。
- 拒:XP 成本维持估算口径——虚高假拒实证在案,现读是消除静默面的最小修。

## 后果

- 正:三局濒死「花光蒸发」根因收口;L3 拒因逐帧可辨;xp 成本真实化;form_score
  实机可读(回退源);refresh_trigger/terminal_release 实机接线(观测面 226 行缺口收口)。
- 负/权衡:闩延命帧构成过度豁免面(仅辖 L3 升级分支,shop 栈不读该键,面受控);
  判读粒度差异(refresh_trigger 两键)需要对账意识。
- 锁面:`test_cw_l3_prep_must_spend_latch.py` 12 锁(闩延命/负向新备战期/跨期失效/
  两拒因键/xp 两形态判决相反/form_score 回退与真空 0/recorder 四件);
  `test_cw_must_spend_zone.py` 盲区钉锁按锁纪律重推为可辨锚。
