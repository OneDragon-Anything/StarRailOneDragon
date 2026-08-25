# 0357 P1 意向锁定产物=过渡配方体系对(终局 comp 锁定移至 P2+)

- 日期:2026-08-27
- 状态:accepted(直接落地)
- 关联:W143 主灶诊断(第二引擎获取链断裂)、0225/0243(cw_recipe 过渡配方一等公民)、
  0353(兜底门两两组合判据)、0338/0341(P1 锁线资格门)、transition_combos.md(四体系
  两两组合=过渡成型,2026-08-23 用户定调)、user_playstyle [20][13][23][31]

## 背景

W143 sim n=100(池 bab146c68c5df11a,seeds 0-99)85 失败局的主灶=**第二引擎获取链
断裂**,根层=意向层锁错目标:P1 锁的是**终局 comp**(COMP_LIBRARY 套名),而 comp 的
form_tiers/采购集只约束自己的羁绊线——

- 56/100 锁 DOT 系 comp(专家桑博DOT/DOT队,仅覆盖 DOT2 单引擎):engines2 成率
  10-19%;第二体系件对锁定策略是「非目标件」,买入天然降权;
- 绯英欢愉 ⑤兜底方向(未锁局的囤货方向)零引擎覆盖:成率 5% 谷底;
- 对照希儿量子(双体系入口)33%——同一供给池养得起,供给参数不是根。

违反 [20]「**过渡是配方不是散买**」(2026-08-20 定调)与 transition_combos 定稿
「四种过渡体系,两两组合过位面 1」——P1 的验收形态是**体系对**,不是终局 comp。

## 决策

1. **P1(位面 1)意向锁定产物=过渡配方体系对**(`IntentionState.p1_pair`,
   四体系键二元组):②③④信号在 P1 **不再锁终局 comp**(过滤条件=
   `_direct_line_qualified`——①类资格通道完整保留,ADR-0338/0341 语义零改动,
   「拿到逆天投资策略才配锁直通线」不变);P2+ comp 锁定/撤销/强制/降格逐位不变,
   进 P2 清 `p1_pair`。
2. **体系对派生**:四体系(仙舟3/列车2/DOT2/希儿系,`TRANSITION_TRAITS` 单一源
   +希儿系哨兵)按手上资产支持度(bench+deployed,注册表阵营∪流派口径,与
   `_engines_count` 同式)取 top-2;平手序=激活占比(列车 .360>DOT .329>仙舟 .292
   >希儿系)。希儿系只认**到手**([23] 锁定由贯穿件=到手,shop 可见不构成方向承诺)。
   门槛 `P1_PAIR_LOCK_MIN_SUPPORT=0.5`(≈三羁绊系 1 件或希儿在手);空窗期
   ([31]① 开局常态)不锁。体系对随资产**重派生**([20]「变体按来牌选」,支持度
   只增,非 pivot;[23] 冻结语义辖终局线不辖 P1 配方)。
3. **囤货方向**:`hoard_target_set` 在 P1 非 comp 锁定局=体系对成员集(mode
   `p1_pair`;希儿系=希儿∪量子∪贝成员);空窗=四体系引擎件全集(mode
   `p1_transition`)——**绯英⑤兜底不再辖 P1**(零引擎覆盖实证)。过渡装备随意
   ([20] 装备语义),equip_targets 恒空。
4. **A/B 通道**:`P1_RECIPE_LOCK`(仿 `P1_FINAL_LINE_GATE` 先例);False=回 W143
   前行为。
5. **default 栈/三臂/应急/ALL IN 零改动**(旁路冻结铁律);decision_v2 各消费方经
   既有接口自动切换:方向门落「未锁」支(=过渡三羁绊门,第二体系件不再被 comp
   档位门拦)、form_ok/formed_stop 落 W132 兜底门(engines≥2,与两两组合口径同构)、
   `session.target_comp=None`(部署/supply 走缺省)。

## Considered Options(W143 §7.1 两条)

- **① comp 评分纳入引擎覆盖数**——否决:仍是「朝终局 comp 散买」语义,只加倾向性
   加分——单引擎覆盖 comp(桑博DOT 19%/DOT队 10%)仍可被锁,锁定后第二体系件仍是
   非目标件;且要动 scoring(意向层外),违反本批边界。选**② 锁定产物改配方对**:
   直接落 [20]/transition_combos 定稿语义,P1 验收形态与锁定目标同构,影响面直达
   engines2 上游。
- 用 `cw_recipe._RECIPES` 单框架伪 comp 作锁定产物——否决:单框架是「一件深度」不是
   P1 验收形态(两两组合才是);配方语义接进意向层锁定产物位即可,粒度按
   transition_combos 定稿。
- P1 完全不禁 comp 锁定、只把⑤兜底方向改过渡——否决:主灶成分①(56/100 锁 DOT
   系)不在此路径上,修不到根。

## 后果

- P1 锁定帧产物:comp 名 → 体系对(账本 target 标签 `过渡配方·A+B`;sim 遥测
  `_direction_established`/`_target_comp_label` 同步认 `p1_pair`,决策逻辑零改)。
- P1 成型停手(form_ok/formed_stop)从「三件套(核心 2★ 质量)」切「兜底门
  (engines≥2,星级盲)」——低质量双引擎板可能提前停手:**seed19(n=25 snapshot)
  涌现危机态囤金零买 1 例,已按 ADR-0289 纪律登记 ci_smoke 待裁**(兜底门是否补
  质量位/危机与成型停手豁免边,裁决归后续批;交互面在 decision_v2,本批边界=
  意向层单文件)。
- P1 `scoring.vd_target_core=''`(V_D 找牌目标空,D 通道关——与未锁局同形);
  pair 找牌目标接口留待后续批(见 W145 报告 §遗留)。
- `cw_performance` comp_tag 配对:pair 标签≠终局 comp tag → 战绩趋势统一 ×0.3
  降权(一致性缩放,无方向性偏置)。
- 验证:ruff+新单帧锁 7(P1 配方对/重派生/希儿到手判据/空窗回退/P2 退场/A-B
  通道/P2 comp 回归)+全量 pytest+sim A/B(同池 bab146c68c5df11a,seeds 0-99,
  主指标 engines2_by_r6 锚 0.15;见 W145 报告)。
