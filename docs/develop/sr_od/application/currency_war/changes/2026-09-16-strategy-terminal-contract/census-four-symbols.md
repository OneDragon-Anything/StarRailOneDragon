# T-5 普查对账表①:四符号全仓普查(r2 返工补件)

> 对账对象 = landing §3.5 完成判据「`strategy_state_of`/`state_of`/`create_session`/`create_state` 符号普查归零(对账表)」+ 验收凭据形式「普查对账表×2」之第一张。补件原因见 `.debug/change-reviews/2026-09-16-strategy-terminal-contract/T-5-r1.md` §5.2(r1 交付对本判据面缺席)。
>
> **普查方法**:`git grep -n -w <符号>`(词边界,排除 `game_state_of`/`strategy_state_of` 对 `state_of` 的前缀串染、`_create_state` 对 `create_state` 的下划线串染),`src/` 与 `sr-od-test/test/` 两仓逐仓;逐文件命中数下表可复算。普查时点 = r2 返工批(2026-09-18)。

## 结论(判据面裁决)

- **零活定义、零活调用**:`create_session`/`create_state` 工厂在全仓**无任何 `def`、无任何属性调用**(`.create_session(`/`.create_state(` 零命中;唯一 `def create_session` 在 `onnxocr/inference_engine.py:150` = ONNX Runtime 会话构建,同名异义,非本退役符号)→「归零」判据本体成立。
- **strategy_state_of / state_of 未归零是申报内的过渡形态**:活读者全部经 §2.6 同源桥(`_session.strategy_state = _strategy.state`,`state_of(session) ≡ self.state`)读**同一状态对象**,语义等价已由 513 绿背书;消亡去向 = T-6(session 类退役时旧读法随迁)。
- **残留面**:①`create_session`/`create_state` 注释·docstring 残留 27 处(去向 = T-8 正本 docstring 普查清单,r1 验收新问题 C 已登记 `cw_back_layout.py:164` 为例);②`create_state` 另有 1 处**鸭子字符串钩子**(mandate_state.py:378 `getattr(strat, 'create_state', None)`,sim 侧第三方策略兼容兜底——现役策略无该属性恒走冷建臂,非符号级引用);③sr-od-test 侧 115+6 处夹具/直驱消费 = 同源桥读法,随 T-6 迁移。

## 表 A `strategy_state_of`(src 131 处;test 6 处)

定义点 = `kernel/cw_strategy_session.py:76`(None-safe 读口;T-6 随 session 类退役)。活读者全部经同源桥读同一状态对象 → **去向 = kernel 同源桥,T-6 消亡/随迁**。

| 文件 | 命中 | 其中活代码调用 | 分类 | 去向 |
|---|---|---|---|---|
| kernel/cw_strategy_session.py | 6 | 1(:65 strategy_state_lazy 内部) | 定义点 + docstring | T-6 随类退役 |
| kernel/cw_intention.py | 10 | 7 | kernel 判据读者 | 同源桥 → T-6 |
| kernel/cw_deploy_logic.py | 8 | 3 | kernel 判据读者 | 同源桥 → T-6 |
| kernel/cw_economy.py | 5 | 3 | kernel 判据读者 | 同源桥 → T-6 |
| kernel/cw_recipe.py | 6 | 5 | kernel 判据读者 | 同源桥 → T-6 |
| kernel/cw_line_switch.py | 4 | 2 | kernel 判据读者 | 同源桥 → T-6 |
| kernel/cw_equip_wear_plan.py | 2 | 1 | kernel 判据读者 | 同源桥 → T-6 |
| kernel/cw_discipline_rules.py | 1 | 1 | kernel 判据读者 | 同源桥 → T-6 |
| kernel/cw_decision_trace.py | 2 | 1(:294;import :90) | kernel 判据读者(模块面零接线,landing §3.7 申报) | T-6 一并处置 |
| kernel/cw_registry.py | 3 | 0 | 注释面(轮键/计数说明) | T-8 docstring 普查 |
| operations/cw_screen/cw_screen_deploy.py | 26 | 24 | operations 读者 | 同源桥 → T-6 |
| operations/cw_loop.py | 12 | 10 | operations 读者 | 同源桥 → T-6 |
| operations/cw_screen/cw_screen_buy_cards.py | 10 | 9 | operations 读者 | 同源桥 → T-6 |
| operations/cw_screen/cw_screen_megastar.py | 7 | 3 | operations 读者 + 注释 | 同源桥 → T-6;注释 T-8 |
| operations/cw_screen/cw_screen_prep.py | 5 | 4 | operations 读者 | 同源桥 → T-6 |
| operations/cw_op/cw_op_sell_off_target.py | 4 | 3 | operations 读者 | 同源桥 → T-6 |
| operations/cw_op/cw_op_tools.py | 2 | 1 | operations 读者 | 同源桥 → T-6 |
| operations/cw_screen/cw_screen_battle_wait.py | 3 | 1 | operations 读者 + 注释 | 同源桥 → T-6;注释 T-8 |
| operations/cw_op/cw_buy_card_action.py | 2 | 1 | operations 读者 | 同源桥 → T-6 |
| operations/cw_screen/cw_screen_equip_pick.py | 2 | 1 | operations 读者 | 同源桥 → T-6 |
| telemetry/schema.py | 6 | 0 | 遥测快照字段注释(透传口径说明) | T-8 docstring 普查 |
| telemetry/match_archive.py | 1 | 0 | 注释面(写入端说明) | T-8 docstring 普查 |
| knowledge/cw_serialize.py | 1 | 0 | docstring | T-8 docstring 普查 |
| obs/recognizers/settlement_recognizer.py | 1 | 0 | docstring(「recognizer 不读 session」边界声明) | T-8 docstring 普查 |
| strategies/impl/mandate_v1/mandate_state.py | 2 | 0 | docstring/注释(访问通道契约说明) | T-8 docstring 普查 |
| **test 仓**(4 文件 6 处:budget_disclosure×2 / cap_override_link×2 / launch_unified×1 / obs_arch_event_screens×1) | 6 | 夹具播种/断言读 | 同源桥读法 | 随 T-6 迁移 |

## 表 B `state_of`(src 140 处;test 115 处)

定义点 = `strategies/impl/mandate_v1/mandate_state.py:341`(§2.6 过渡桥:StrategyState 直传 shim + 裸 session 惰性冷建兜底)。两个消费形态:**(i) gs 宿主读法** `state_of(gs)` = 同源桥等价读(零参管线以 `self.gs` 为宿主);**(ii) session 直传读法** `state_of(session)`/`state_of(self.state)` = mandate 管线内部消费(self.state 作宿主参传递)。两形态同源同对象 → **去向 = mandate shop/管线 session 消费,T-6 终局形态裁决时随迁**(r1 验收 §1③ 已申报该项转段 T-6)。

| 文件 | 命中 | 分类 | 去向 |
|---|---|---|---|
| mandate_v1/mandate_state.py | 2 | 定义(:341)+ 访问通道注释(:328) | T-6 裁决 |
| mandate_v1/entry.py | 39 | 管线 session 消费(ii) | T-6 随迁 |
| mandate_v1/mandate.py | 30 | 管线 session 消费(ii) | T-6 随迁 |
| mandate_v1/shop.py | 19 | 管线 session 消费(ii;并行批在飞件,本批未触碰,数字为普查时点实况) | T-6 随迁 |
| mandate_v1/sell_gate.py | 17 | 管线 session 消费(ii) | T-6 随迁 |
| mandate_v1/proof.py | 12 | 管线 session 消费(ii) | T-6 随迁 |
| mandate_v1/bridge.py | 6 | gs 宿主读法(i,:109 等)+ docstring | 同源桥 → T-6 |
| mandate_v1/economy_cycle.py | 3 | 管线消费(ii,:281)+ import + 注释 | T-6 随迁 |
| mandate_v1/encounter.py | 3 | 管线消费(ii,:273)+ import + docstring | T-6 随迁 |
| strategies/impl/flow.py | 3 | 注释/docstring(self.state 等价声明;间接读退役申报) | T-8 docstring 普查 |
| strategies/impl/cw_strategy.py | 1 | docstring(state setter 同源接线声明) | T-8 docstring 普查 |
| strategies/impl/cw_strategy_manager.py | 1 | 注释(旧读法/新读法等价说明) | T-8 docstring 普查 |
| mandate_v1/criteria/contracts.py | 1 | docstring | T-8 docstring 普查 |
| kernel/cw_deploy_logic.py | 1 | 注释(双轨帧两源分歧警示) | T-8 docstring 普查 |
| operations/cw_screen/cw_screen_megastar.py | 2 | 注释(禁执行层触发 impl 冷建语义) | T-8 docstring 普查 |
| **test 仓**(17 文件 115 处:_cw_helpers + 16 测试文件) | 115 | 夹具播种/直驱消费 = shim 两形态 | 随 T-6 迁移 |

## 表 C `create_session`(src 16 处 CW 域 + onnxocr 3 处同名异义;test 0 处)

**归零判定:成立。** 全仓零 `def`、零属性调用;CW 域 16 处全为注释/docstring 残留。

| 文件 | 命中 | 内容 | 去向 |
|---|---|---|---|
| kernel/cw_strategy_session.py | 3 | docstring/注释(旧接线史说明) | T-8 docstring 普查 |
| kernel/cw_vocab.py | 1 | :1081 注释(「新局起点由策略 create_session 调用」——已失实,复位现经引导漏斗) | T-8 docstring 普查 |
| obs/cw_back_layout.py | 2 | :164-166 注释(r1 验收新问题 C 点名件) | T-8 docstring 普查 |
| operations/cw_loop.py | 2 | :933/:1783 注释(「唯一冷建口」——现唯一冷建口 = 构造注入) | T-8 docstring 普查 |
| strategies/impl/cw_strategy.py | 2 | :76 退役申报(保留)/:217 注释 | :76 为退役声明保留;其余 T-8 |
| strategies/impl/cw_strategy_manager.py | 1 | :75 注释(复位随 create_session 退役迁漏斗) | T-8 docstring 普查 |
| strategies/impl/flow.py | 1 | 模块头 :6(旧生命周期叙述) | T-8 docstring 普查 |
| mandate_v1/mandate_state.py | 1 | :124 注释 | T-8 docstring 普查 |
| onnxocr/inference_engine.py + predict_base.py | 3 | ONNX Runtime 会话构建,**同名异义非本符号** | 不涉,永久在场 |

## 表 D `create_state`(src 14 处;test 0 处)

**归零判定:成立(符号级)。** 全仓零 `def create_state`、零属性调用;唯一非注释引用 = 1 处鸭子字符串钩子。

| 文件 | 命中 | 内容 | 去向 |
|---|---|---|---|
| mandate_v1/mandate_state.py | 7 | :31/:368/:371 docstring;**:378 `getattr(strat, 'create_state', None)` 鸭子字符串钩子**(ensure_strategy_state sim 侧构建口;现役策略无该属性 → factory=None 恒走 :380 冷建兜底臂,生产不可达) | 钩子与 docstring 随 T-6/sim 面清尾裁决 |
| kernel/cw_strategy_session.py | 4 | docstring/注释(旧工厂契约史) | T-8 docstring 普查 |
| strategies/impl/cw_strategy.py | 1 | :76 退役申报(保留) | 保留 |
| strategies/impl/flow.py | 2 | 模块头 :7 + :185 注释(「基类 create_state 返回类型收窄」为旧叙述;现活钩子 = `_create_state` 私有覆写,不在本符号普查面) | T-8 docstring 普查 |

## 与 r1 验收口径的对账

- r1 §1②「`state_of` 在 mandate_state.py 带 StrategyState 直传 shim 存活,shop.py 内 ~67 处 session 消费」:shim 在场核实一致;「~67」与 landing §3.5「shop.py ~68 处 session 消费随批改形」同源 = 改形前预估量。改形落地后 shop.py 现存词边界命中 19 处(管线 shim 消费形态,T-6 随迁),本表以可复算的词边界口径为准。
- r1 §1②「create_session/create_state 确已归零(仅注释残留)」:核实成立,另补登 mandate_state.py:378 鸭子字符串钩子一处(r1 未列,生产不可达,已在上表 D 单列)。
- 「读者迁移同源桥等价、随 T-6 消亡」转段口径:r1 指出仅存在于代码注释(cw_strategy_manager.py:103-105)——本表即为该口径的对账工件化,delivery-t5.md §2 已挂指针。
