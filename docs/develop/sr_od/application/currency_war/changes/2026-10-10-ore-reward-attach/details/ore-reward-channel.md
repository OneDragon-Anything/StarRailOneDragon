# 声明通道与奖励生成(详设)

## 问题与约束

- **通道分工是硬约束**(依据 cw_game_state.py `write_logic_rand` docstring:观察覆盖差异 = 随机效果落地属预期;策略器消费前必须重观察,logic_rand 落消费门不可信侧):`observe` 写画面真值,`write_logic_rand` 写「可能世界快照」。附着奖励在实机是猜测 → 只能走随机态;`spheres` 的位置/颜色是画面真值 → 留观察通道。**附着值若混进 `OreSight.points`,spheres 域不会被标随机态,消费门(logic_rand_fields)对它失灵**——故附着值独立成域。
- **声明归属不可观察**(用户裁定 2026-10-10):增发货币的 6/8/12 金矿与通用矿同屏时,坐标区分不了谁是声明矿 → 分配本身掷随机,整条写入走随机态。
- **坐标跨帧抖动是常态,不是例外**:Hough 圆心亚像素抖动 + 发光呼吸(cw_identity_obs.py `_SPHERE_PERSIST_POS_TOL=12`/`_SPHERE_PERSIST_R_TOL=6` 常量注释),`find_ore_sights` 返回当帧原始圆心、无量化吸附。观察链两帧持存(`filter_persistent_ores`)是**防幻检的容差过滤器,不是坐标稳定器**——身份解析必须在挂接层自做容差配对(见 §4),否则精确键在抖动下换键,声明金被「消失清洗 + 新现重掷」链路静默蒸发。
- **注册表分域**:增发货币已在 `ENV_ECONOMY`(估值域)。本通道是**世界发放域**,与估值域不互斥——`ENV_GIFTS ∩ ENV_ECONOMY = ∅` 检查的语义是「单一环境只落一个估值结构」(cw_investments.py `_validate_env_gifts`),本注册表不参与该检查,代之以「同值校验」(见 §2)。
- 挂接入口两端共用:spheres 的写端有两处(live = operations/cw_screen/cw_screen_prep.py 备战观察写端;sim = sim/cw_sim_backend.py `_present_node_screen`),必须单一入口防漂移。

## 方案

### 1. GameState 新域(cw_game_state.py)

```python
# 附着奖励域(随机态):键 = 矿身份最新观察坐标 'x,y',值 = OreReward
ore_rewards: Field[dict[str, OreReward]] = field(default_factory=Field)
# 声明待兑现队列(逻辑态):元素 = (env, plane, gold)
ore_declared_pending: Field[tuple[tuple[str, int, int], ...]] = field(default_factory=Field)
# 声明已消费标记(逻辑态):元素 = (env, plane)——幂等守卫第二腿,位面过渡同清理
ore_declared_done: Field[tuple[tuple[str, int], ...]] = field(default_factory=Field)
```

- [索引定义] `ore_rewards` 键 `'x,y'` = 矿身份**最新一次观察**的 `(int(x), int(y))` 拼接(身份连续性判定见 §4,键随轨迹重挂);取值时机 = 矿身份首现生成刻,存续至开成摘除/消失清理。
- [索引定义] `ore_declared_pending` 元素 `plane` = 1 基位面号(与 `NodeKey.plane` 同坐标系);`gold` = 该位面声明金额(卡面直读)。`ore_declared_done` 元素 = (env, plane),生成消费刻追加,位面过渡随 pending 同清理(§5)。

**工程面三件**(与域定义同批交付):

- **开局种子底座**:三域入种子列表(`_seed(gs.ore_rewards, {})` / `_seed(gs.ore_declared_pending, ())` / `_seed(gs.ore_declared_done, ())`,沿 `pending_item_grants`/`active_env` 种子族先例,cw_game_state.py 开局种子函数)——域值恒非 None,幂等守卫与合并写零 None 防御。
- **快照恢复登记**:`full_state_snapshot` 经 `_json_safe`(dataclass→dict、tuple→list);恢复表按字段名重建复杂域(先例 = node/deployed 重建 λ)。`ore_rewards` 登记重建 → `{k: OreReward(**v) for k, v in ...}`;`ore_declared_pending` / `ore_declared_done` 登记重建 → `tuple(tuple(e) for e in ...)`(done 随快照存续 = 恢复局不重发声明)。不登记则恢复面拿到 dict-of-dicts/list-of-lists 静默类型漂移,回放/Δ池判读面降级。
- **None 起点合并**:§4 步序 4 合并写遇域值 None → 从 `{}` 起合并(种子后近乎不可达,防御性一行)。

### 2. 声明注册表(cw_investments.py)

```python
ENV_ORE_GRANTS: dict[str, tuple[int, ...]] = {
    # 每位面开局 6/8/12 金晶矿(id 103 原文直读,cw_invest_data PlazaPortal('103'))
    '增发货币': (6, 8, 12),
}
```

构建校验(沿 `_validate_env_economy` import 即炸先例,并入同文件校验族):

- 键 ⊆ `INVESTMENT_ENVS`(孤儿键防版本更新失联);
- 值 = 长度 3、逐项正整数的元组(位面 1-3);
- 同键在 `ENV_ECONOMY` 有非空 `gold_per_plane_start` → **长度相等且逐位同值**(双源防漂移:估值面与世界面同出卡面,失同步即构建期炸)。

### 3. 共享生成函数(cw_ore_reward.py)

```python
def generate_ore_rewards(declared_gold: tuple[int, ...], coords, level, rng
                         ) -> dict[str, OreReward]
```

- `declared_gold` 长度 ≤ `len(coords)`(构造方保证;违者 ValueError):逐个 `rng.choice` 剩余坐标(不放回)占位 → `OreReward(kind='gold', gold=值)`;
- 其余坐标逐个 `roll_ore_reward(rng, level)`(三选一临时口径 v0 原状,`ORE_ASSUMPTION_KEYS` 披露);
- `level` 不在 `REFRESH_PROB` → 沿 `roll_ore_reward` 显式 ValueError(口径错档禁静默兜底,先例同函数);
- 返回 `{'x,y': OreReward}`;纯函数,rng 注入。

### 4. 挂接入口(kernel/cw_ore_channel.py,新模块)

```python
def report_spheres_observed(gs, sight: OreSight, *, obs_sig, hook_sig,
                            evidence: str) -> None
```

步序(单一入口,两端写 spheres 一律经此):

1. 旧坐标列 = 写前 `gs.spheres.value.points` 的 (x,y) 列表(值 None → 空列);
2. `gs.observe(gs.spheres, sight, sig=obs_sig)`(现行为原样,含空读照写 count=0 语义);
3. **容差配对**(身份连续性判定):旧列 × 新列中,**配对门 = 双轴独立 ≤ 持存容差 12px(常量单一源 = `cw_identity_obs._SPHERE_PERSIST_POS_TOL` **公开化重命名**为 `SPHERE_PERSIST_POS_TOL**,kernel 在**函数体内 lazy import** 公开名以避免模块级环——**kernel→obs 运行时导入现无先例**(cw_encounter_selection.py:39 的引用在 TYPE_CHECKING 块,运行时不执行),本迭代立此形态、落地后即为后续先例;禁复制数值;门语义与 `filter_persistent_ores` 同)**,**贪心排序键 = 欧氏标量距离**,最近者优先一一配对。配对命中 = 同身份:
   - `ore_rewards` 键 old→new **重挂**(write_logic_rand,evidence=`ore_gen_rekey#p{plane}`,值不变**不重掷**——声明金由此在坐标抖动下保全);
   - 配对歧义(多对多交叉)时按确定规则取一致配对——**候选对按(旧列序 × 新列序)枚举,距离平局 = 枚举序先者优先,禁随机**:附着是随机态猜测,配对误差不引入系统偏差(sim 侧合成坐标恒稳无歧义)。**误配几何可达域定量**:同帧两矿圆心最小间距 = Hough `minDist=35`(cw_identity_obs `find_ore_sights`),跨帧各抖 ±12px 时异矿最窄 35−2×12 = **11px ≤ tol**,交叉配对几何可达;贪心最近在真对距离 < 交叉对距离时选真对,真对距离 = 抖差(常态 ≪ 11px),常态救回;
   - **跨面板别名披露**:上一面板未点击残留矿与下一面板矿同坐标时按同身份继承旧附着——sim 侧经济中性(未被消费的附着即世界真值),live 侧自愈于观察收口;极端角(现役身份全为别名残留)声明条目饿死至过期清理,接受并披露;
4. **生成集 = 无附着的现役身份**(步序 3 重挂后,新值坐标中仍无 `ore_rewards` 键者——覆盖未配对新现、level 缺读跳过帧、恢复/竞态残留形态)。生成集非空:
   - `level = gs.level.value`;None → 本帧不生成(种子恒写 level=3,生产近乎不可达,此为保真防御;该批身份仍无键,下帧自动再进生成集;点击侧另有兜底,details/ore-click-consume.md §1);
   - 出队 `ore_declared_pending` 中**当前 plane** 的声明条目(节点域 `NodeKey.plane`;无则空);
   - `generate_ore_rewards(声明金额列, 新现坐标列, level, action_sampling_rng('ore_reward_gen', None))`;
   - 合并写 `gs.ore_rewards`(write_logic_rand,produced_by=`'ore_reward_attach'`,evidence=`f'ore_gen#p{plane}+{n}'`,sig=hook_sig;None 起点从 `{}` 起);
   - 声明消费写 = `ore_declared_pending` 移除条目 + `ore_declared_done` 追加 `(env, plane)`(**同一 write_logic**——消费与标记原子;依据 = kernel 确定效果直写 write_logic 先例(cw_exec_state 金腿 / cw_effect_inventory 退款腿);不属「容器逻辑写端 anchor_aware」族:该域无观察写端可锚定,声明是登记事实非观察投影,与 anchor_aware 纪律无涉);
5. 未配对**消失**身份:对应键从 `ore_rewards` 移除(同 write_logic_rand,evidence=`'ore_gen_cleanup'`;零配对变化 ∧ 零新现 ∧ 零消失 → 零写)。

**点击未真开的回补形态**(点击载荷发了、画面矿未消,下帧矿重现):点击已摘除该坐标(无旧坐标可配对)→ 按未配对新现重掷 = 新猜测,无偏;误记金域随机态由观察收口纠偏(依据:write_logic_rand「观察覆盖差异 = 随机效果落地,预期内非 bug」)。

### 5. 声明入队与过期(同模块)

入队 = **电平触发单一规则 + 消费标记**(无边沿检测、无帧间记忆、无 op 成员。边沿形态已否定:op 每备战环重建,成员记忆在跨环重入时伪造边沿、消费即移除销毁幂等守卫前提 → 同位面重复发放;环境选定边沿在帧内不可见——`active_env` 非漏斗写、帧内恒不变,帧内快照救得了位面边沿救不了环境边沿)。**live 接线规约**(实现者照此开工,不留拍板空间):

- **判定点 = 每个 heavy 帧 `observe_full` 回执之后、spheres 写之前**(节点域 plane 的写点在 `observe_full` 内的 read_game_state 漏斗,cw_observation.py read_receipt → `gs.observe(gs.node, …)`;`observe_node_anchor` 锚的是序号不更新 plane——漏斗回执后已无「旧 plane 现值」,禁在锚定前后找前值)。**plane 取值源 = 回执后 `gs.node.value.plane`**;None(首锚定前,node 域不在开局种子表)→ 本帧不检查,下一 heavy 帧兜住。
- **入队条件(电平)**:`env = active_env 现值 ∈ ENV_ORE_GRANTS` ∧ `(env, plane)` ∉ `ore_declared_pending` ∧ `(env, plane)` ∉ `ore_declared_done` → 追加 `(env, plane, ENV_ORE_GRANTS[env][plane-1])`(write_logic)。位面 1 晚选环境、位面 2/3 过渡、恢复局续跑,全部由此一式闭合。
- **消费标记**即 §4 步序 4(pending 移除 + done 追加,同一写)——done 是幂等守卫第二腿:**跨备战环、跨恢复局**(done 随快照存续)重查不重发。
- **过期(电平清理)**:判定点顺手移除 `ore_declared_pending` / `ore_declared_done` 中 plane ≠ 当前 plane 的条目(write_logic,evidence 留痕 `ore_declared_expired#p{old}`)。若实机为自动开启(矿永不出现),pending 条目留至位面过渡被清理即终态——零污染,这就是把「自动开启假设」从 fail-closed 预设改为**模型对两种现实都稳健**的机制面;披露键 `ore_plane_start_pending`(**本迭代新增**,落 sim 侧 3.3;呈现面/色档/自动开启未实采,实机首遇校)。
- **次序硬约束 = 入队与过期电平检查完成先于同帧 spheres 写**——现观察序「observe_full(:240)→ …→ spheres 写(:384)」天然满足,接线点固定在回执后即可(接错次序则位面首帧新现生成时声明未入队,若该帧后无新现,声明永不附着)。
- **sig 形态(两端各自,均过 write_logic_rand 的 `_validate_sig`)**:live 入队/过期/消费写 = logic_hook 族,group_id=`'prep:ore-channel'`,actor=`CwScreenPrep`;sim 挂接写 = `logic_sig('sim:ores')`(logic_action 族,sim 现行构造形态,见 ore-sim-plane-start §3)。参数名 `hook_sig` 泛指「挂接写用 sig」,族差异即上述两端形态,不再另定。

## 关键取舍

- **附着值进 `OreSight.points`(元组加槽) vs 独立域**:选独立。通道纪律与消费门(问题与约束第一条)压过「单容器」直觉;代价 = 两域身份键耦合,由挂接入口单一化承担(写端只有一处入口,键不会分叉)。
- **身份解析 = 容差配对轨迹继承 vs 精确键 vs 量化键**:选轨迹继承。精确键被观察链自己的容差过滤器反证(约束第三条);量化键在分箱边界有同样的翻箱抖动;轨迹继承对亚像素抖动稳健且声明金保全。代价 = 每帧可能的重挂写(廉价 logic_rand 写一行)与配对歧义(猜测值上无偏,披露)。
- **边沿触发(快照对拍)vs 电平触发 + 消费标记**:选电平。边沿形态两难:op 成员记忆跨环重建伪造边沿(消费即移除销毁守卫前提 → 同位面重发),帧内快照救不了环境选定边沿(`active_env` 非漏斗写、帧内恒不变);电平 + done 标记一揽子闭合(跨环/恢复局/晚选环境/位面过渡),代价 = 多一个轻标记域。
- **pending 队列 vs 上下文纯推导**(active_env × plane 现推):选队列。「已发/未发」从 `ore_rewards` 现值不可推导(键随点击/清理/重挂消失,推导需历史),纯推导会在矿消失后重复入队(重复发放声明)。
