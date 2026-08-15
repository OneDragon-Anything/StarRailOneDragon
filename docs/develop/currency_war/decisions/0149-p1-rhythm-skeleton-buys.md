# 0149 · 凑牌节奏:P1 过渡骨架驱动买牌 + 无损购买窗口

- **Status**: Accepted(2026-08-16;P1 期先落买牌节奏,过渡成型停手判据/开局囤 bench 细化留批次2)
- **Context**: M15-M28 十四局同款死因收敛:**凑牌节奏缺位** —— P1 商店无 target 卡时,`_saving` 攒金门 +
  off-target prefilter 双拦 → 整轮空手/攒金死守 → 板 8 阵营各 1 散装/裸板进 boss → HP 崩。M28(0152 栈)
  复现:P1 全过但 boss 磨 90+ HP,hp 5 进 P2 死 2-4。
- **Decision Drivers**: 用户五条权威口述(economy_research §7-11~14)+ plaza 方法论 M3(枢纽分级)/M4(骨架=成对拼装);
  数据层已备(skeleton_factions 派生 15 羁绊 / EARLY_CORE_POOL+TEMPO_POOL 两级 / TRANSITION_FACTIONS)。
- **Considered Options**:
  - A. 放宽 prefilter 阈值(全局松)—— 否:M25 实证 flex 宽松=spread 合法化,回到 8 阵营散装。
  - B. 只加 no-loss 窗口 —— 不够:M22 实证金 21-35 也在空手(窗口只覆盖金<20)。
  - C. **骨架纪律买牌(选中)**:不是「放宽」而是「换判据」—— P1 无 target 卡可买时,按**骨架配对纪律**
    (与 flex 配对同构:TEMPO 枢纽单买放行 + 骨架羁绊已有 ≥1 才深化)买过渡件;攒金门对 no-loss 窗口
    (金<20,用户 §7-11 原话)豁免。散买骨架单张仍拒(防 spread 回归)。
- **Decision**:
  1. `_skeleton_buy_ok(card, state)`(cw_plan):三类合法过渡买——①枢纽池(EARLY_CORE_POOL 单买=开局,
     TEMPO_POOL 打工);②骨架羁绊配对(skeleton 派生集内,board+bench 已有 ≥1 深化);③通用填充件
     (星期日;用户 §7-14「阵容有缺口暂时用着没所谓」,板未满时)。
  2. **攒金门 no-loss 豁免**:金 < 20(1 息档内)买过渡件不损息还压缩牌池(用户 §7-11)—— `_saving`
     分支对 `_skeleton_buy_ok` 放行。
  3. **prefilter 骨架例外**:shop 无可买 target 且未成型(fp<COMMIT_FRAC)时,骨架合法买不按 off-target
     拒(与 tempo 例外并立;板饿死代价 > spread 代价,live 7 局实锤)。已成型仍严格聚焦。
  4. **P1 追级抑制**(§7-12,批次1落):金 < INTEREST_THRESHOLD 非boss/锁血不追级 —— 已由
     `_want_level_up`/node_plan 地板覆盖(M22 后校准),本 ADR 不重复建模,仅记录口径。
  5. 批次2 留:**过渡成型停手**(lv5-6+骨架凑+过渡核2★→停D攒息,§7-13 —— 需「过渡成型」概念进评估,
     接 tempo score;**开局囤 bench**(§7-1)已由 ADR-0130 rest 过滤落。
- **影响面**:cw_plan(买牌两门)+ 测试;预期效应 = P1 板从「8 阵营各1」变为「2-3 个激活骨架对 + target
  期权重叠」,boss 前 HP 显著留存(对照 M28 boss 磨 90+ HP)。live 验证判据:P1 结束时 board 激活档
  骨架 ≥2 且 hp 进 boss ≥40。
