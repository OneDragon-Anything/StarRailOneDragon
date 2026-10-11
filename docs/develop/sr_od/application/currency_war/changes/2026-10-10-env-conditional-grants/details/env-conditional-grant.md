# 条件达成发放机制(详设)

## 问题与约束

- **通道纪律**(依据 cw_game_state.py `write_logic_rand` docstring:落位/细节不可观察的效果走随机态,观察覆盖差异 = 随机效果落地属预期):财富宝钻到达的**库存位置不可观察** → 发放 = `write_logic_rand` 可能世界快照;`equips` 是观察域(owned_equips 识别器读屏覆盖),下一备战帧整表覆盖纠偏——猜错自愈,零持续污染。
- **触发点代码事实**:streak 真值唯一生产点 = 结算屏 OCR(`parse_streak`「连胜×N」前缀 = 方向,cw_settlement_obs.py)→ 结算覆盖写端 `apply_settlement_cover`(kernel/cw_game_state.py,`gs.observe(gs.streak, streak_after)`),调用方 = operations/cw_screen/cw_screen_battle_wait.py(结算观察回执携带 streak_after);sim 同构 = cw_sim_backend.py 结算路径 `streak_signed_after` → observe。**触发检查挂在两处 streak 落账之后**,不新建观察面。
- **「本局首次」守卫不能依赖持有状态**:补给/合成(蓝蓝/红红/红蓝 recipes)/其他卡(钻石商人等)都会给财富宝钻——「身上没宝钻」作守卫会误跳。守卫 = done 标记域(状态住 GameState;ore 迭代 R5 教训:op 成员记忆跨环重建伪造状态,禁用)。
- **回调边界**:deploy_cap/back_layout/diamond_count 的 live 写端 = 观察识别器(逻辑侧禁写,投影审计在册)→ **live 不调回调**;sim 世界事实由 sim 自己写 → 回调 = sim 专用,两个调用点(深井发放后 + 补给宝钻)。
- 接口契约引用(总纲 §2):触发检查单一源;登记表三条校验;done 域四件套;发放 write_logic_rand / done write_logic;回调 observe 三写。

## 方案

### 1. GameState 新域(cw_game_state.py)

```python
# 环境条件发放已发标记(逻辑态):元素 = (env, 条件键)
env_grants_done: Field[tuple[tuple[str, str], ...]] = field(default_factory=Field)
```

- [索引定义] 元素 `env` = 环境规范名;条件键 = 具名触发器(`'first_streak'`);取值时机 = 发放刻追加,局内恒存(无过期——「本局首次」整局有效,与晶矿 done 的位面过期清理不同:连胜无周期语义)。

**工程面四件**(沿晶矿迭代 T-1 先例,同批交付):

- **开局种子**:`_seed(gs.env_grants_done, ())`;
- **快照恢复登记**:恢复表 tuple 化重建(`tuple(tuple(e) for e in ...)`);done 随快照存续;
- **DEFAULT_GS_SCHEMA**:独立键 `env_grants_done: 1`(不并入他域 bump——他域本体未变);
- **投影审计行**:完备性锁强制新域登记(先例 = 晶矿三域,T-1)。

### 2. 登记表(cw_investments.py)

```python
ENV_STREAK_GRANTS: dict[str, tuple[int, str]] = {
    # 本局首次 5 连胜 → 财富宝钻(id 104 原文直读,cw_invest_data PlazaPortal('104'))
    '深井角斗场': (5, '财富宝钻'),
}
```

构建校验(沿 `_validate_env_economy` import 即炸先例,并入同文件校验族):键 ⊆ `INVESTMENT_ENVS`(孤儿键);装备名 ∈ `EQUIPMENTS`;阈值 ≥ 1。

### 3. 触发检查 kernel 函数(kernel/cw_env_grants.py,新模块)

```python
def check_env_streak_grants(gs, streak_after: int, sig) -> str | None
```

单一源,live/sim 都调它(同一条件两处各写判定 = 漂移)。条件矩阵(顺序即短路序):

1. `env = gs.active_env.value`;None/空 → None;
2. `grant = ENV_STREAK_GRANTS.get(env)`;None → None;
3. `streak_after <= 0`(连败/零方向)→ None;
4. `streak_after < grant[0]`(阈值)→ None;
5. `(env, 'first_streak') ∈ env_grants_done` → None(已发);
6. **发放**:`base = gs.equips.value`;None → None(**宁缺勿造,不标 done——条件每结算重查,下个结算自动重试**,与晶矿生成集「下帧再试」同性质);
   `_w_rand(gs.equips, list(base) + [grant[1]], evidence=f'env_grant#{env}#streak{grant[0]}')`(write_logic_rand,produced_by=`'env_conditional_grant'`);
   `_w_logic(gs.env_grants_done, 现值 + ((env, 'first_streak'),), evidence 同串)`(write_logic;直写先例 = cw_exec_state 金腿 / cw_effect_inventory 退款腿,不属 anchor_aware 族——登记事实非观察投影);
7. 返回 `grant[1]`(被发装备名;调用方据此决定是否调宝钻回调)。

**无 rng**:随机态指认知通道(落位未知、观察校准),追加位置(尾部)确定,不消耗随机数。

**恢复局边界披露**:接管局 done 为空、active_env 非空 → 首个 streak ≥ 阈值的结算触发发放 = 最佳猜测;live equips 整表覆盖纠偏零持续污染,sim 无接管局。接受并披露。

### 4. 宝钻获得回调(同模块)

```python
def on_diamond_acquired(gs, equip_name: str, sig) -> None
```

- `equip_name != '财富宝钻'` → 直接返回(cap 加成语义只属财富宝钻,官方条目「拥有宝钻可以使团队规模上限 +1」= cw_equipment_data 财富宝钻行;红/蓝钻是补给视觉族同框,cap 语义无涉——依据 cw_obs_core `DIAMOND_EQUIP_NAMES` 仅视觉判定族);
- 三写(全部 `gs.observe`,sim 世界事实先例 = `_on_supply_picked` 的 diamond_count 写):
  1. `diamond_count` 现值 + 1(宝钻族均计数);
  2. `deploy_cap` = `level_of(gs)` + equips 现值中 `'财富宝钻'` 计数(拥有即算、可叠加,D-53 实测口径);
  3. `back_layout` = `min(9, 现值 + 1)`(值域 6-9;现值 None → 以机制基线 6 起算,种子后不可达防御);
- **live 不调用**:三域 live 写端 = 观察识别器,下一备战帧自动覆盖(总纲「明确不解决」节)。

### 5. 接线(live 与 sim)

- **live**:battle_wait 结算覆盖调用点之后(`apply_settlement_cover` 以非 None streak_after 调用时),`check_env_streak_grants(gs, streak_after, sig)`;sig = logic_hook 族,group `'battle-wait:env-grant'`,actor `CwScreenBattleWait`;返回值忽略(live 无回调)。**streak_after 为 None 的结算不调**(覆盖写端本就跳过 streak 观察,口径一致)。
- **sim**:结算路径 streak observe 之后,`check_env_streak_grants(gs, signed, sig)`;返回非 None → `on_diamond_acquired(gs, 返回名, sig)`;sig = `obs_sig(group_id='sim:env')` / `logic_sig('sim:env')` 形态沿 3.3 晶矿先例(挂接/登记分通道)。
- **补给宝钻采纳**(缺口闭合):`_on_supply_picked` 的裸 `diamond_count +1` 写替换为 `on_diamond_acquired(gs, '财富宝钻', sig)`——补给宝钻即财富宝钻(带钻选项语义),三写生效,sim 上限保真缺口闭合;既有补给测试若断言 deploy_cap/back_layout 旧值需跟改。

### 6. 测试面摘要(细则归 landing)

触发函数全条件矩阵(方向/阈值/已发/环境不在册/equips 缺读重试)、随机态写行与 done 追加、恢复局边界(快照含 done 不重发)、live 接线次序(结算覆盖后、观察整表覆盖纠偏)、sim 数值对照(5 连胜后三域)+ supply 采纳后行为变化跟改。

## 关键取舍

- **边沿/快照机制 vs 电平 + done 标记**:直接电平 + done(晶矿迭代 R5/R6 教训整体继承:边沿与 op 成员记忆在本仓备战环语义下不可靠)。本机制的检查点 = 结算(低频、天然幂等友好),连电平的优势都比晶矿场景小。
- **条件数据进登记表 vs 硬编码在触发点**:登记表。理由 = 孤儿键校验防静默失联(游戏版本改环境名,硬编码 if 无声失效,登记表 import 即炸),与 ENV_ORE_GRANTS 同纪律;不是通用化——表只收「连胜触发器」形状,升级类条件卡各建各表。
- **发放 = 独立随机态写 vs 进获得链统一原语**:独立写。获得链的装备获得原语面向「获得时点确定的发放」(确定性写);本机制落位未知走随机态,且 done 标记与发放的原子性(同 sig 相邻两笔)在触发函数内聚更直观。获得链复用留给未来确有共性的场景。
