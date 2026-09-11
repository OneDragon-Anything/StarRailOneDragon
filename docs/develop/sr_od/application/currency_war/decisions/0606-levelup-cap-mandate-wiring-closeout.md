# ADR-0606: 等级帽单一源收口(mandate 第 4 消费位接线 + lv9_stop 收严必填 + level_spend_blocked 同族接线)

- 状态:已实施
- 关联:ADR-0565(本批所收口挂账的决策源:等级帽单一源、4 消费位接线、过渡缺省通道辖域申报)、ADR-0471(sim 注入视图先例)、`kernel/cw_registry.py`(`level_max=10`/`vd_p2_loss` 注册表真值)

## 1. 背景与问题

ADR-0565 落码时 mandate.py 属并行在飞文件面(禁并行同文件),留两笔挂账:①`mandate.py` 备战 M3 的 `lv9_stop` 消费位未接线,由判据函数「`level_max=None` 回读 `DEFAULT_REGISTRY`」过渡缺省通道覆盖;②同族泛化项——同文件 `level_spend_blocked` 调用位裸缺省(未传 registry)。过渡缺省通道长期存留 = 第二源回潮温床(ADR-0565 §6 在案):任何新消费位照抄该形态即可绕过单一源纪律,且注册表与策略面之间重新出现无机制强制的「恰同值」巧合。

## 2. Considered Options

- **A(采纳)run_mandate 加 registry 注入参数 + 两消费位接线 + lv9_stop 收严必填**:`run_mandate(frame, session, state, registry)` 经 `entry.emit` 注入链下传(生产 = `MandateV1Strategy.registry`,与 entry `_reg`/shop `_reg` 同一通道约定);M3 链 `lv9_stop(frame.level, _reg.level_max)`、`level_spend_blocked(state, session, _reg)`;`lv9_stop` 的 `level_max` 参数收严必填,过渡缺省通道拆除。
- **B(否决)维持缺省通道 + 对账锁**:对账锁只能发现漂移、不能阻止第二源存在(同 ADR-0565 §2-B 否决理由);run_mandate 是 lv9_stop 唯一残存裸缺省消费位,留着即温床本体。
- **C(否决)level_spend_blocked 的 registry 参数同步收严必填**:三生产消费位(entry posture 镜像/shop M3/mandate 备战 M3)接线后已全量注入,函数级 `None` 通道 = 与 entry/shop `_reg` 同款「直调/测试面兼容」约定,收严属接口面变更且无行为收益;留待该通道出现新裸消费位时随批收(见 §4 边界)。

## 3. 已实施架构

- `mandate_v1/mandate.py`:`run_mandate` 签名加 `registry: DecisionV2Registry | None = None`;M3 链两消费位(`lv9_stop` 传 `_reg.level_max`、`level_spend_blocked` 传 `_reg`)消费注入表;`None→DEFAULT_REGISTRY` 兜底与 entry/shop `_reg` 通道同款(直调/测试面兼容,生产链经 entry.emit 恒注入)。
- `mandate_v1/entry.py`:`emit` 将收到的 `registry` 下传 `run_mandate`(与同函数 `_reconcile_posture_authorization` 同一注入链)。
- `criteria/levelup.py`:`lv9_stop(level, level_max)` 收严必填,删过渡缺省回读;docstring 声明 4 消费位全量接线与禁新消费位依赖缺省。
- **零行为变更申报**:mandate 消费位仅 live prep 可达(sim 引擎只调 shop 栈,ADR-0565 §4),live 注入值 = `DEFAULT_REGISTRY`(level_max=10 与停付线字段同值),接线前后逐帧判定等价;`level_spend_blocked` 消费的停付线字段(`vd_p2_loss` 族)与 `level_max` 无关,sim 注入视图(仅 level_max 异)下本就无分歧。本批消除的是接口面的裸缺省通道,非行为分支。

## 4. 边界

- sim 零漂移:备战栈无 sim 调用方;shop 侧两消费位维持注入视图 9 冻结语义,既有 sim 冻结锁(`test_cw_sim_shop_single_source`/`test_cw_w614`)不动。
- `level_spend_blocked` 函数级 `None` 通道保留(与 entry/shop `_reg` 同款约定),新消费位禁依赖缺省;若未来出现第 4 个生产消费位,随批收严必填(同 lv9_stop 先例)。
- 键串 `lv9_stop` 保留不改名(ADR-0565 键名裁决承继)。

## 5. 验证

- 变异红证:`sr-od-test/test/sr_od/app/currency_war/test_cw_l3_prep_must_spend_latch.py::TestL3RegistryInjection` 两把注入变异锁——①等级帽:注入 `level_max=9` 视图 lv9 帧必落 `l3_reject_level_cap`,换 `level_max=11` 同帧过帽落 `levelup_budget_gate_blocked`;②停付让位:注入 `vd_p2_loss=30`(危机带线 41→60)hp=50 帧必落 `crisis_level_spend_defer`,缺省表同帧不停付。对「接线拆除回读缺省表」变异态单跑两锁全红,还原后全绿——锁行为不锁回显,禁机械跟绿。
- 点名 7 个直接受影响测试文件(213+ 条)全绿;`ruff check` 全部改动文件绿;L1 快速集归 commit 门。
