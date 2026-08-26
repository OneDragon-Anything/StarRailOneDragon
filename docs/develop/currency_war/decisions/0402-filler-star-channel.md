# 0402 产星通道(方案 A filler_star 期权分 + 方案 B 同名副本方向门豁免)

- 日期:2026-09-02
- 状态:accepted
- 前置:W231 诊断(`.debug/temp/currency_war/w231_star_diag/w231_star_diagnosis.md`)、ADR-0340(merge_progress)、ADR-0339(core_star)、ADR-0401(form 星级分量)
- 关联:W232 实现批(`.debug/temp/currency_war/w232_filler_star/`)

## Context(为什么)

W230 证实 sim 星级因果通道已建(ADR-0401 form 星级分量),但承接门
outcome 面无方向的根因=**策略栈 P1 段几乎不做星级投资**:进场 star≥2
率仅 7.7%(n=100),93/100 局 star_depth 峰值恒 0。W231 逐决策位取证:

1. **评分维结构性零分**(主):merge_progress/core_star/targets 三项
   全部只辖目标集内名字——降级梯队填充件(bond_fallback/pair 通道
   买入、板上多数)的第 2 份买入全维零 delta → 仲裁器「非正分」
   结构性拒;478 张「已持有名」机会仅 17.6% 成交;
2. **目标集内副本也输给新件**(次):on-target 机会成交率 ~20%,
   买预算被 line_opportunistic 等新件通道挤出;
3. **方向门错拦**(配套):`pair_wants` 的方向阵营判断先于同名副本
   判断,填充件副本在锁定后被方向门排除(45 张/100 局机会);
4. r410 `copy_swap_useless` 守卫在生成层拦 deployed 非目标件的
   同名副本(候选不存在,评分层无从显影)。

经济面非主因(副本买入均价 1.46 金/局,[11] 1 费净 0 例外存在)。
实机互证:run26/28 全 1★ 同型。

## Decision(做了什么)

**方案 A(评分项)**:`score_state` 新增分项 `filler_star` = 已
deployed 填充件(目标集外名字)的第 2 份同名 1★ 期权分
(`scoring._filler_star_progress_count`,每名只计一次进度;第 3 份
merge 成 2★ 后回落 0——填充名 2★ 不另计价,战力走阵营计数 star
加权)。与 merge_progress 互补不双计(目标集内让位)。硬边界
([31] 反散件防违反):只辖已持有名的第 2 份(压库语义 [15]/[22],
不授权为填充件 D 刷);只辖已 deployed 名(纯 bench 囤件不折,
ADR-0295 同式域边界);copies_cap 沿用(仲裁层守卫照常辖)。

**生成层豁免(A 臂联动)**:`generate_candidates` 的 r410 守卫段,
`filler_star_unit>0` 时已 deployed 名(`candidates._has_deployed_copy`,
deployed-only 口径)的同名副本放行生成;默认关 = r410 守卫现行为
不变(W96 `test_r7_frame_generation_guard_unchanged` 锁延续)。

**方案 B(候选门)**:`candidates._buy_tag` 在方向阵营门
(`pair_wants`)之前加同名副本豁免分支(冷启动例外 r383b 的全轮域
推广)——副本是升星素材(filler_star/merge_progress 期权通道)而非
新方向投资,方向门拦它=语义错位。r408 同轮已卖守卫保留(仍拒);
A5 阵营上限与 copies_cap 不受影响(已持有名阵营必 ∈ owned_factions)。

**开关载体**:registry 两字段 `filler_star_unit: float = 0.0` /
`pair_copy_direction_exempt: bool = False`,**默认双关(=现行为零
漂移,A/B 通道保留,ADR-0305 先例)**;A/B 臂(u0.5/u1.0)两开关
同臂开(单独开 B 解锁的副本买入在 unit=0 时评分仍零维,且会经
bond_fallback 条件缝隙产生意外行为——两臂同开保证「产星通道」
语义完整)。

## Considered Options(最值钱栏)

| 选项 | 裁决 | 理由 |
|---|---|---|
| 方向门改挂 discipline.pair_wants 内部(W231 原稿) | 否,移 _buy_tag 层 | pair_wants 无 registry 入参,加参=全消费面改签名;且无条件改会破坏零漂移门(unit=0 臂也要逐位同现行为)——豁免必须是 flag 化分支 |
| filler_star 泛化 merge_progress 的目标集判据 | 否,独立分项 | 改既有项口径=动已标定项(core_star/targets 联动语义),双计/回归风险;独立分项+独立开关=可 A/B 可回滚 |
| 豁免辖 bench∪deployed(has_same_name_copy 口径) | 否,deployed-only | bench 囤件期权本就该折(ADR-0295);bench-only 名的同名卡放行=授权散件囤积,违反 [31] |
| B 无条件生效(代码级重构,零成本) | 否 | 破坏零漂移门:unit=0 臂也要逐位同现行为,无 flag 的行为变更无法验证「默认关=现行为」 |
| 目标集内副本也加权(W231 §②-2 on-target 成交率 ~20%) | 挂账 | merge_progress=3.0 已辖目标集内第 2 份;输给新件是仲裁排序问题不是评分缺失,另立批裁决 |
| 方案 C(末窗星级定向授权) | 挂账,依赖链 A/B→ADR-0400 复验→C | W231 定稿:先产星,承接门的星级投资方向才有落点 |

## Consequences

- **默认值论证**:双关默认 = P1 零漂移门的结构前提(unit=0 臂对
  改动前基线逐 seed 逐位 diff 恒空,实测 0 处);ADR-0400 先例
  (行为面有效但 outcome 面无一致正方向 → 默认关通道保留)。
- **A/B 数字**(n=300 池 3be1d31006541ba2 导出件 seed 0-299 同池
  同 seed 配对,planes=2 invest on,
  `.debug/temp/currency_war/w232_filler_star/w232_ab.json`):
  - 主指标:进场 star≥2 率 u0=10.1% → u0.5=24.4% / u1=24.1%
    (基线口径 n=100 为 7.7%,n=300 自然波动);merges/局
    0.13 → 0.38/0.37;dup 买入 0.81 → 2.41 张/局(金 1.40→3.55);
    P1 出口金 33.88 → 32.63/32.34(-1.3/-1.5,息档内);
  - 锚:hp_ge_60 0.003→0.000/0.000(本池基线近零,不可辨);
    engines2_by_r6 0.497→0.513/0.510(微升);
  - **锚回归**(`w232_anchor.json`,W230 复验③ 口径 w158_strict):
    arm0 四项精确一致 ✓(never2 [229,257,274,293]/strict_mal 24/
    出口 hp 29.5/金 33.88——主锚不漂);开臂 P1 面漂移如实披露:
    never2 4→7(+3:93/181/261/288/292 进入,229/257 退出)/
    strict_mal 24→26/25;出口 hp 29.5→29.68(微升);金 33.88→
    32.63/32.34。never2 微增=副本买入挤占部分局的引擎成型路径,
    与 engines2_by_r6 微升并存——两指标分母不同(never2=严格
    恶性局计数,engines2=r6 前达成率),净效应在锚面判为可接受
    噪声量级(±3/300)。
  - outcome 面(星级投资的真回报,ADR-0401 通道首次能量出):
    p2_hp0_rate 0.931→0.909/0.909(配对方向:arm-only hp0 9 局
    vs u0-only 15 局,正方向);存活轮 3.79→3.79/3.81(配对
    56>/59< / 57>/59<,wash);p2 胜率 0.192→0.179/0.183(微降)。
    **hp0 方向为正但存活轮/胜率 wash——部分正方向,不足以裁默认
    开**(与 ADR-0400「无一正方向」相比有进步,方向证据在 hp0 维)。
  - 单位选择:u0.5 与 u1.0 两臂几乎无差(24.4/24.1%、merges
    0.38/0.37)——期权分只把 0 分顶成正分,量级在过门后不改变
    排序竞争格局;未来若裁开,u0.5 为保守端。
- 单帧锁 9 条(`test_cw_w232_filler_star.py`):项值 5(2 份
  显影/bench-only 不折/目标集内让位/star≥2 回落/每名一进度)+
  门序 3(默认双关无候选/B 豁免 'copy' 标签/B 单独对 bench-only
  名有效)+ 边界 2(copies_cap 沿用/A 臂豁免范围)+ 评分断言
  (A+B 臂 deployed 副本买入正分且 filler_star 维构成 delta)+
  默认值常量锁。
- 检查网:批㉞ supply-label 一致性探针用 DEFAULT_REGISTRY(双关),
  新分支不触发——检查面无需新增位(r410 豁免与 B 豁免均在 flag
  开臂才生效,默认态行为面与检查器口径一致)。
- 风险与边界:填充件 2★ 挤占目标件金——engines2_by_r6 微升
  (0.497→0.513)未见挤出;出口金 -1.3/-1.5 在息档内;
  W96 r7 帧生成层不变式在默认态保持(锁续)。
