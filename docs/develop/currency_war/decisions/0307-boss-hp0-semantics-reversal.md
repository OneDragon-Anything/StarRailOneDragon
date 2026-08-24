# ADR-0307 boss 败局 hp==0 语义改判:违规→删失披露(批41 推翻批40)

- 状态:accepted(2026-08-24)
- 关联:批39(地板删失)/批40(边界复审)/ADR-0279(三维遥测)

## 背景

`check_boss_hp_floor_censoring`(cw_sim_checks.py)是 boss hp 地板删失判读检查。
批40 边界复审新增两条违规分支,其中「hp_after==0 且 killed=False → 写端矛盾
(归零即败应标 killed=True)」——批41 压测官复审**推翻**该判。

## 决策

1. **==0 改判删失披露(note 级)**:killed 语义 = 玩家击败对手(「挑战成功」);
   团灭 = 打不过 → `killed=False` 恰是正确标签,批40 把它要求成 True 是
   **语义倒置**。写端 `cw_settlement_obs` 失败屏 hp=0 为 ground truth
   (conf=1.0),`HP_MIN=0`(cw_obs_core)OCR 可解析真 0——`killed=False +
   hp_after==0` 是合法团灭形态,与 ==1 同族:伤害口径剔除/单独标注,不作违规。
2. **hp_after 缺失分支降级 schema 防御**:当前写端不产 None(语料实证
   21 boss 行无 None),分支保留但定性为防未来写端变更,非语料缺口。
3. **hp_before 回填补跨 run 守卫**:缺省回填取上一行 hp_after 时须同
   run_id——跨 run 边界回填会用上一局末 hp 当本局 boss 前值,产出伪
   「hp 未降」违规(批40 遗留缺陷)。

## Considered Options

- **A(选)**:改判+守卫——语义以写端 ground truth 链为准,违规判据只留
  「真跳变」(killed=False 且同 run 内 hp 未降);
- B:维持批40——把合法团灭当违规报,判读面持续误报,错误方向;
- C:删掉 ==0 分支不管——丢失删失披露(伤害口径会误含地板值)。

## 影响

- 判读面:boss 败局 ==0 行不再计入违规,进删失披露 note(口径须剔除);
- 检查输出文案:「hp_after∈{0,1}」合并披露;
- 锁测试:test_cw_boss_hp_floor_censoring 全量更新(31 过)。
