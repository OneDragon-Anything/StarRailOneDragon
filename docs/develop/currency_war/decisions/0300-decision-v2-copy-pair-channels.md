# 0300 - 决策框架 v2 copy/pair 通道迁移批(ADR-0299 买入面残余清偿)

- **Status**: accepted(2026-08-25;平局线 ±3.3 保持:n=100 配对差
  +1.89(SE 2.72),vs 0299 基线 +1.74 在噪声带内)
- **Context**:ADR-0299 Considered Options ②登记的残余:copy 3/
  pair 通道在 v1 有语义、v2 未迁移(残余 layer1 ~0.7/局,解剖表
  终态 6.7%);buys v2 11.3 vs v1 15.0。
- **Decision**(生成层两件,判据单源直通不复制):
  1. **pair 候选通道**:candidates._pair_wants = v1
     `LineStrategy._pair_wants` 直通(与 _engine_seed_wants 同式);
     _buy_tag 在 engine_seed 之后、bond_fallback 之前裁决
     (与 v1 _want_label OR 链同序)。语义全在单一源:冷启动
     首购只放行 桥名单∪引擎阵营∪同名副本(r368/r371b/r383b)、
     方向期阵营门(r350:锁线=线形态羁绊/桥=引擎阵营)、A5
     spread 门(≥3 阵营不开新)、常态同阵营凑对、r408 同轮
     已卖不回买。
  2. **copy 候选通道**:同名副本素材打专属标签(与 v1
     _want_label 的 r383b 拆分同式——_has_same_name_copy 且
     非 r408 已卖);保留判据镜像 v1 `_copy_swap_useless`
     (r410:在场副本会被 deploy 侧 off-target 卖出 → 买新副本
     =无效换卡,生成器层拒,直通单一源)。副本上限仍归
     copies_cap(生成器)+ 层4 copies_cap(仲裁,双保险)。
  3. 注册:pair/copy 进 buy_tag_priority 与 economy/war/
     catchup 放行标签集(**emergency 集保持窄**——v2 应急集
     设计本就窄于常态,非迁移遗漏);进 _PIPELINE_TAGS(买件
     经部署管线显影,bench 折减权重下纯囤件显影不足)。
- **Considered Options**:
  1. **pair/copy 也进 emergency_tags**:否决——应急态保命
     优先,v2 应急集(line_carry/opportunistic/bridge_core/
     engine_seed/carry_gate/off_target/free_bench/deploy)
     本就不含 bond_fallback/refresh 等常态通道,加 pair/copy
     扩散应急放行面无证据支撑。
  2. **副本买加评分项(3合1 原料期权)**:否决——评分侧加项
     会抬 base 分压缩其他买(ADR-0299 同型教训:种子持有项
     双窗劣于生成-only);copy 走管线显影已够。
- **验证**(snapshot 池 066c4185,单进程串行,v1 臂同进程重跑;
  v1 臂 final_hp 与 0299 逐位一致=代码无漂移):
  - 双窗 30+30:窗1 配对差 +0.80(SE 4.39)/窗2 +2.70
    (SE 4.99)——双窗同号,方向一致;
  - **n=100 终验(900000-900099)**:v1 32.37 vs v2 30.48,
    配对差 **+1.89(SE 2.72)**,平局线 ±3.3 内保持(vs 0299
    +1.74:差 0.15 在噪声带内,v2 均值 30.63→30.48 微降
    非方向性);
  - **buys 11.3→11.8/局**(未到 14:预期内——通道采纳
    d2_pair 9+d2_copy 12/30 局 ≈0.7/局,恰清偿 0299 登记的
    残余 layer1 ~0.7/局;剩余 3.2/局缺口主体=供给分叉回声
    61.6%+layer3 评分(DOT flow 首砖 0 分盲区,0.4/局,已
    登记),非生成层);
  - 通道点火实锤:d2_pair 9/d2_copy 12(含 _merge 4)/30 局
    (生产端点火纪律);
  - 测试:0300 新锁 11/11(pair 生成/A5 拒/r350 拒/r408 拒/
    copy 标签/r410 守卫双向/注册全);currency_war 全目录
    1327 通过(0291 bond_fallback fixture 改锁 r350 方向门外
    独占场景;0293 hash 91de0e92→509c228d 按流程更新,数值
    字段全部不变;0299 三锁的「不生成」断言改锁 engine_seed
    语义≠迁移前无候选副作用);ruff 通过。
  - ⚠️ 已知无关红:test_ci_smoke_snapshot_batch
    equip_value_strategy_key_coverage=在飞 worker 域
    (ADR-0298,同 0299 批)。
- **Consequences**:
  - 正:v1 买通道面(copy/pair)全迁移完成,判据单一源直通
    (v1 演进自动跟随);买入面生成层残差清偿;副本守卫
    (r410)在 v2 首次生效(v1 挂 _buy_guards,v2 此前无对应)。
  - 负/风险:①buys 缺口 3.2/局主体是不可修的供给回声+已登记
    的评分层盲区,买入面收敛空间见顶——下批方向在评分层
    (DOT flow 首砖)或不再追 buys 面;②pair 通道冷启动分支
    与 engine_seed 在 r1-r2 有判据交叠(v1 同构,非新增);
    ③v1 臂在演进,后续配对仍须同进程重跑。
