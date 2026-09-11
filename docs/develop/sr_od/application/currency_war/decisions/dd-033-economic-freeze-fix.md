# dd-033 经济冻结型败局三病灶治本(目标空窗/姿态脱钩/弱面选线)

## 背景

实机局复盘 g_20260904_031925(第 5 局:金 125 攒死)与 g_20260904_042657(第 6 局:1 买/0 刷/金 127 攒死)共同定谳「经济冻结型败局」三病灶。同族修法第 2 次出现,按根源两问升格治本批。修复批 REPORT = `.debug/temp/currency_war/economic_freeze_fix/REPORT.md`(含逐帧证据链与 sim 配对数字)。

## 决策

### 病灶① 目标空窗(target_comp 空窗 → 决策引擎全停)

- **机制定谳**(g_20260904_042657 p1r5–p1r9 逐帧):R3 断供驱逐(`PAIR_DROUGHT_EVICT_ROUNDS=5`,cw_intention)是**单向门**——`pair_evicted` 一旦写入永不撤销,即便体系成员重新在店(断供证据被驳);两体系在 5 轮店干后双双永久出局,`_derive_p1_pair` 重派生得 `()`,而 `update_target` 物化分支以 `ist.p1_pair` 非空为前提 → `target_comp=None`。cw4 准备域(mandate pass)无 K 空窗回退(商店域有、准备域没有)→ `k_members=()` → M2 无目标、`stop_buy=False` 停掉 dominance/M6、M3 被 arm1/spend_unified 正常拦下 → 引擎只剩 M7 RunEquip,0 买 0 刷 0 升级,金 53→127 滞留至死。
- **修法(三层,单一源不破)**:
  1. **驱逐可逆**(cw_intention `_update_pair_drought`):体系成员重新在店 ⇒ 撤销驱逐(证据被驳;事件标签 `un-evict:pair_supply:<体系>`)。根修。
  2. **P1 物化不空窗**(decision_v2/strategy `update_target`):P1 帧配方对为空时按 `p1_early_pair` 无门槛 top-2 方向物化伪 comp(ADR-0372 买入门同款读法:空窗期同样有方向)。
  3. **准备域 K 回退**(cw4/entry):`target_comp=None` 时经新单一源 `cw_intention.k_empty_window_fallback` 取方向成员(与 shop.py 商店域同源;shop.py 同批改为消费该函数,禁第二源),M2 保持有目标可买。
- 附带**P2 目标移交**(任务书口径「P2 开局必须有目标」):P2 unlocked 帧(配方锁已退场、信号未锁)强制 assignment,候选 = weak_planes 过滤 ∧ 核心可达,按资产最厚取(同 P3 强制锁语义);事件标签 `handoff_lock:<线>`。P2 无可达候选保持 unlocked(⑤兜底,不降格终局)。

### 病灶② posture 接而不用(posture='level' 全程零 LevelUp,posture_unfulfilled 恒 None)

- **机制定谳**:授权面(`get_node_goal` 确定性预算核,spend_mode='level')与执行面(M3:arm1 存在性 + spend_unified 整批纪律)判定不一致时**零对账点**;`session.v3_posture_unfulfilled` 只有 decision_v2 reconcile_spend 会写,cw4 栈从不写 → 恒 None。
- **修法**(cw4/entry `_reconcile_posture_authorization`):每决策段帧级复位 → 发射序列无 LevelUp 而 spend_mode='level' 时,逐门复评 M3 链定位未兑现原因(lv9_stop/arm1_board_not_full/spend_unified_batch_unaffordable/…),置位 `v3_posture_unfulfilled`(形状与 reconcile_spend 同构)+ 计数键 `posture_unfulfilled_level` + log。**只声明不兜底花钱**——升级发射仍由 M3 判据独裁,P56 下界语义零触碰(不重新引入「乱花」对立面)。

### 病灶③ P2 选线绕过 weak_planes(DOT队 weak_planes=(2,) 自注「P2 不选」仍被锁)

- **机制定谳**:weak_planes 过滤只存在于 maybe_pivot 保命路径(cw_comps);意向层③核心卡信号(P2r1 卡芙卡可见)直通 `_lock`,不过滤。
- **修法**:①update_intention 信号面过滤——weak_planes 含当前位面的线不产锁线信号;②强制锁候选(P2 移交/P3)同过 weak_planes 过滤。单一源 = `Comp.weak_planes` 注册表自注。回归锁口径 =「weak_planes 含当前位面时该线不进锁线候选」。

## Considered Options

- 病灶①:只修商店域(已有回退)不动准备域 = 打补丁(引擎仍在准备域空转)——弃;改 update_intention 让 pair 永不空 = 治标(驱逐单向门仍在,方向可能锁死在断供体系)——弃;三层合修(根:驱逐可逆;面:物化+准备域回退)——采纳。
- 病灶②:强制发射 LevelUp = 破 spend_unified/arm1 判据、重引入乱花风险(P56 约束)——弃;显式降级 + 置位 + 日志(动作保证留给 M3 判据演进)——采纳。
- 病灶③:把 DOT队 从 COMP_LIBRARY 摘除 = 销毁 P3 合法线——弃;消费位过滤(信号面+强锁面)——采纳。

## 验收(摘要,详见 REPORT.md)

- 新锁 8 条亲跑绿(`sr-od-test/test/sr_od/app/currency_war/test_cw_economic_freeze.py`);旧锁 w628 P6 注入探针夹具随移交语义演进(weak 帧),legacy 锁 `test_p2_or_empty_pair_not_materialized` 空对断言按新语义改写并记 docstring。
- CW 快速集(2523 项)唯一红 = w614 sim 保真 digest(行为变更预期,任务书允许)。
- sim 配对(n=30/臂,同池指纹 ee3350a297bcbbc4,同 seed):final_hp 差 -0.8(t=-1.0)、P2 买入 +0.2(t=+1.0)、hp0 15→16(单种子翻转)——中性无回退;sim 供给健康,r7 空窗形态在 sim 不复现,机制开火由单帧锁承载。
