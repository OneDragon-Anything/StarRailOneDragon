# ADR-0457: hp 可信位消费门(血线谓词 fail-closed)+ hp 读链放大回退与覆盖值位同写

- **Status**: accepted(2026-08-30,编排者审定——Considered Options 论证核可,消费门/读链/写侧三件与实现 8f902840 一致)
- **Date**: 2026-08-29

## Context

局21 P2 r4(ts 03:28:43)实证 hp 可信位防线缺在消费层:state 三位
(hp=100, hp_readable=False, hp_trusted=False)自洽且正确标注了「带毒假值」,
但血线谓词 `blood_budget_levelup_blocked`(ADR-0448 的单一收口)只做
`state.hp <= p2_levelup_stop_hp` 阈值比较,无任何可信位检查 → 幽灵 100>21
不触发 → 12×LevelUp 放行,全部发生在 ADR-0448 血线 21 带内(W576 ❌1.1)。
毒化生产链两个独立源头:①`read_hp_opt` 是最后一个未接放大手法的文本
reader,低血小数值(≤16)原生分辨率 det 漏检 → None(失明帧裁片目视清晰、
x3 放大即恢复,物理遮挡已否定);②`shop.py` HP 链裸兜底——关帧 miss 且
结算真值不新鲜时裸取 100,且覆盖 `state.hp` 时不同步写 hp_readable/
hp_trusted(值位分家,(100, False, False) 三位自洽假值即此形态)。

与 W403/ADR-0431 的分工边界(写死):对账层管「值对不对」(拦错值入库),
消费层管「这个帧配不配用值做决定」(拦不可信值进阈值谓词)。两层正交,
缺一即洞——局21 实证对账层完好在位、消费层裸奔照放 12×LevelUp。

## Considered Options

1. **消费门 fail-closed:不可信帧按血线内处理(采纳)** —— 线内升级
   EV=−C−I 严格负(ADR-0448 数学,与 β 无关);拒付的最坏情形(真值其实
   在线外)= 少升一级,机会成本一帧;误放的最坏情形(真值在线内)=
   血线内追级,实证结局即局21 r4(金换人口、人没活到)。证据缺失时禁令
   保持有效,与 ADR-0428「兜底假值帧仍拒」同型、同一非对称。
2. **拒收后维持上次决策(拒绝)** —— 谓词逐帧无状态,被 arbiter 约束/
   稳态多击组/deploy_cap 补偿臂①三面共享;引入跨帧决策记忆 = 新状态机,
   复杂度与脆性不成比例。
3. **拒收后降级默认姿态(拒绝)** —— 拒付只封 LevelUp 通道,买牌/刷新
   各有其门;重选姿态放大波及面,且「血线胜」已隐含停花未来,不需要
   第二重姿态机制。
4. **逐调用面加守卫(arbiter/remediation 各加)(拒绝)** —— 三调用面
   已汇入单一谓词(W523 封旁路接线),谓词入口一处守卫即全覆盖;散写
   三份违反单一源纪律(W393 A1.1:新增 hp 守卫消费点一律走
   `hp_decision_trusted` helper)。
5. **只修写侧不修消费门(拒绝)** —— 写侧修复(放大回退+值位同写)降低
   门的拦截率,但「跨节点陈旧沿用」「未来新增兜底路径」等不可信帧仍会
   出现;消费门是安全依赖,写侧是体验优化,先后不可倒置。

## Decision

1. **消费门(P0)**:`decision_v2/discipline.blood_budget_levelup_blocked`
   入口,ALL IN 豁免判定之后、阈值比较之前,加
   `if not hp_decision_trusted(state): return True`。单一源
   `hp_decision_trusted`(`posture_release.py`,W393/ADR-0428 既有实现,
   本批未上移 cw_state——posture_release 对 discipline 的引用全在函数体
   内延迟 import,模块级反向 import 无环,零迁移成本)。守卫位置语义:
   开关 off(A/B 对照臂)与 ALL IN 豁免均先于守卫——A/B 注入面不变,
   「位面末花光是时机不是血线判断」的豁免在不可信帧上仍生效。
2. **读链放大回退**:`cw_observation.read_hp_opt` 加小目标两级放大回退
   (全图 miss → `_ocr_upscaled` 3x CUBIC → `_ocr_upscaled_binarized`,
   与金/等级/XP 读链同款,W332 家族口径);仅 miss 路径新增开销,常路径
   (全图命中)零变化。
3. **写侧止毒**:`shop.py` ①关帧 miss+新鲜度门失败 → 不再裸兜底 100,
   `hp_value=None`;②新增模块级单一写点 `_apply_hp(state, value, readable,
   trusted)`:值+保真位同写(真读→(v, True, True)/结算真值(fresh 门过)
   →(v, False, True)/None→不覆盖,保留 read_game_state 对账层值+位),
   三个覆盖点(买前 update_target/shop 开帧循环/买后重估)全部改走。

## Consequences

- 现役行为面唯一变化:「不可信 hp(hp_readable ∧ hp_trusted 皆 False)帧
  不再被血线谓词消费」。sim 帧恒真读(默认 hp_readable=True)→ 门短路,
  逐位等价(源级锁+全量套件证明零漂移)。
- 拦截面:商店单元帧 (False, True)(同节点沿用,ADR-0428 主救场景)照常
  放行;真读帧直通;被拦的是「跨节点陈旧沿用」与「兜底/丢位假值」——
  恰为不该做血线判断的两类帧。
- 效率:谓词 +0.10µs/次(0.40→0.50µs 中位,N=100);decide_prep 端到端
  中位 0.462ms,守卫开销占比 ≈0.02%。read_hp_opt 回退仅 miss 路径。
- 遗留挂账:①det 漏检字形机制(墨宽/首数字 1)定量语料(扫历史 shots
  hp 区)待扩证,放大倍率 3x 为与家族对齐的起步值;②DESIGN 测试计划
  第 5 组「cw_sim_checks 段级检查增不可信 hp 帧 LevelUp 违规项」需改
  cw_sim_checks.py(本批文件面外,已声明避让)——现以「sim 恒真读→门
  短路」源级锁+sim 冒烟锁承载等价保障,检查器扩展挂 W580c;③outcomes
  补给节点 hp 推导污染(局21 r3「26 conf 1.0」vs 画面 16)遥测侧另案。
