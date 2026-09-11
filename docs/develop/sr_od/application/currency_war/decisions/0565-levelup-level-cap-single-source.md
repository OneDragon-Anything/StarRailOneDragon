# ADR-0565: 等级帽单一源(lv9_stop 收 level_max)——策略面游戏定义量第二源纠错 + 4 消费位注册表接线 + sim 注入视图零漂移

- 状态:已实施
- 关联:ADR-0471(sim 两把尺对齐先例:sim_decision_registry 注入视图)、ADR-0561(申报表 #6 lv9 拒付方向相反)、`kernel/cw_registry.py`(`level_max=10`,注册表真值)、`kernel/cw_state.py`(`xp_apply_clicks` 封顶 10 = live 机制语义声明)、P71(边界 2 sim/live 帽分歧)、P48/P21/P39/P71-b(lv9 帧放行后的既有门链)

## 1. 背景与问题

`criteria/levelup.py` 自持 `LEVEL_CAP: int = 9` 常量,注释声称「注册表 LEVEL_CAP 同值」——注册表真值 `kernel/cw_registry.py level_max = 10`(封顶 10 = live 机制语义,`cw_state.xp_apply_clicks` 同源声明)。注释的「同值」为假 = **游戏定义量第二源且已漂移一个版本周期无人知**;live 在 lv9 提前停升,吃掉 lv9→10 档(84 金整批)的人口增量通道。消费面逐一打开:`LEVEL_CAP` 策略面仅被 `lv9_stop` 消费,消费位 4 处——`entry.py`(`_reconcile_posture_authorization` 逐门镜像)、`shop.py` M3 批位、`shop.py` 必花域 L3 位、`mandate.py` 备战 M3 位(均经 `ensure_contract` 契约面),全部是「等级 cap 资格硬闸」。附带纠错:常量注释声称 `pop_slot` 消费该常量,实读 `pop_slot` 收 `deploy_cap` 参数、不读常量——注释不准,随常量删除一并消失。命名陷阱(防二犯):levelup 域的 `cap_resolved` 是**利息上限**,与本命题的等级上限无任何数值或语义关联,预算闸数值面不受本修复影响。

## 2. Considered Options

- **A(采纳)lv9_stop 增加 `level_max` 参数,4 消费位传上下文注册表的 `.level_max`**:live 读 `DEFAULT_REGISTRY`(10 = 机制真值);sim 读 `sim_decision_registry()` 注入视图(=9),sim 行为零变化——9 级冻结、池指纹、ADR-0561 申报全部原样。策略面不再持有任何等级常数。
- **B(否决)自持常量+对账锁**:这正是本次病灶的成因形态——对账锁只能发现漂移,不能阻止第二源存在,且每次注册表变动要人工跑对账,纯负债。
- **C(否决)策略面改持常量 10**:sim 决策视图仍 9 → 复发「决策层发起→执行层拒付」的 22+/局 `level_cap_rejects` 空转(ADR-0471 记录的原病);单一源注入是唯一同时满足「live 真值」与「sim 零漂移」的形态。
- **键名裁决:`lv9_stop` 键串保留不改名**——cap=10 后 9 级不再因它停,名不副实,但改键牵连判读脚本与历史档案可比性,纯改名无收益;docstring 注明「历史键名,语义=等级上限停」。决策迹键 `lv9_stop`/`level_cap`/`l3_reject_level_cap` 同判保留。

## 3. 已实施架构

- **判据面**(`criteria/levelup.py`):删 `LEVEL_CAP` 常量;`lv9_stop(level, level_max=None)`——单一源 = 注册表 `level_max`,`level_max` 由消费位传上下文注册表,禁裸常数;缺省 None 回读 `DEFAULT_REGISTRY` 为**过渡兼容**(辖域见 §4)。
- **消费位接线(3/4 本批)**:①`shop.py` M3 批位与 ②必花域 L3 位传 `_reg.level_max`(`_reg` = `decide_shop_action` 的 registry 注入链,生产 = `flow.py` `self.registry`,sim = `sim_decision_registry()` 视图);③`entry.py` `_reconcile_posture_authorization` 签名加 `registry` 参(emit → decide_from_turn → bridge 注入链),lv9_stop 与同函数 `level_spend_blocked` 均传 `_reg`。
- **第 4 消费位(mandate.py 备战 M3)**:派单时 mandate.py 属并行在飞文件面(禁并行同文件纪律),本批不接线;该位由缺省通道覆盖,行为与接线后等价(见 §4),接线义务归 mandate.py 主理批,接线后 `lv9_stop` 收严为必填参数。(收口 = ADR-0606:接线 + 收严 + level_spend_blocked 同族位接线已落。)
- **同族泛化(方案审义务项)**:`level_spend_blocked` 的裸 DEFAULT 调用——`entry.py` 位本批随函数接线一并补传 `_reg`(一参之改);`mandate.py` 位未传 registry 属同族债,登记归 mandate 主理批,不静默放过。
- **契约回显**(`criteria/contracts.py`):`('levelup','lv9_stop')` scope 改引注册表 `level_max` 口径;BYPASS_TABLE(levelup 域)不变(函数仍在,类别不变)。
- **行为变化声明**:live lv9 帧从「恒拒」变为「按 P48 整买/P21 血预算/P39 双臂门/P71-b 预算闸逐帧判」——游戏定义量纠错,strategy-work §3 第 1 档直接落码无开关;回滚 = git revert。

## 4. 边界申报

- **mandate 过渡缺省通道的可达面**:该消费位仅 live prep 可达——sim 引擎(engine_p1)只调 `decide_shop_screen`(shop 栈,注册表注入),prep 决策链(`decide_prep_screen`→`decide_from_turn`→`run_mandate`)的生产调用方只有画面 op,无 sim 调用方。缺省回读 `DEFAULT_REGISTRY.level_max=10` = live 真值,与接线后行为等价、无 sim 路径。**禁新消费位依赖该缺省**(docstring 在案);mandate 接线后参数收严必填。
- **sim 零漂移**:sim 可达消费位(shop ×2)全部读注入视图 9,sim 行为零变化;后续 sim A/B 判读 lv9→10 帧继续按 P71 边界 2 声明「sim 结构性无帧」,禁把 sim 读数当 lv9→10 行为零值证据。将来 sim 放开到 10(前置 = 追级虚高治理+池指纹重锚,在案)时策略自动跟随,无需二次改策略。
- **测试锁改写清单(锁的存在性纪律,判改不判回退,红证在案)**:
  1. `test_cw4_shop_line` 旧「lv9 帧恒零 LevelUp」锁(钉 9=满级旧语义,已被注册表真值证伪)→ 三帧单一源锁:lv9+sim 视图冻结 / lv9+live 表放行(过 arm1/P21/P48/P71-b)/ lv10+live 表停;
  2. `test_cw_must_spend_zone` 两锁:`level_cap==1` → `batch_unaffordable==1` + `level_cap` 否定面(lv9 帧非 cap 顶,L3 拒因落 P48 整买拦截;R1 切分线靶语义不变);
  3. `test_cw_l3_prep_must_spend_latch` 满级帧锁 lv9→lv10(真满级) + lv9 帧分键否定面(不再因等级帽拒)。
  sim 冻结语义两锁(`test_cw_sim_shop_single_source` / `test_cw_w614` digest 哨兵)按设计保持绿,禁动——它们恰是本修法的回归资产。
- **IMPL_DESIGN §2.3 锚**:原设计件已随归档整编离开 docs 树,契约 anchor 保留历史指针;as-built 语义同步落 strategy-docs 升级面节。

## 5. 验证

- 红证:上列 4 改写锁对 HEAD(旧常数代码)单跑全红;还原本批改动后全绿——锁钉新语义,非机械跟绿。
- `ruff check` 4 个源文件绿;L1 快速集(`pytest sr-od-test/test/sr_od/app/currency_war -m "not slow and not legacy_baseline"`)全绿(基线 2 定谳既有红维持);全量套件归编排者 commit 门。

## 6. 风险与后果

- live lv9 升级发射上升 = 修复目的本征;84 金批的支出量由 P71-b 预算闸量住(ADR-0560),血面由 P21/危机带辖。
- mandate 缺省通道若长期存留(主理批接线后未收严必填)= 第二源回潮的温床——收严义务随本 ADR 挂账,禁新消费位依赖缺省。
