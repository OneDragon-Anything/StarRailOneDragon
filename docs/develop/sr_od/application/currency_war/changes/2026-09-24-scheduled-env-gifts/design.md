# 环境定时道具发放与特权武装箱开箱 迭代设计(总纲)

## 0. 元信息

- 迭代目标:投资环境**定时道具发放**通道(指定「位-轮」节点发放)+ **特权武装箱开箱链路泛化**——落地投资环境「特权阶级」(效果原文「第二位面开始时,获得1个特权武装箱。」,`data/cw_invest_data.py` PlazaPortal id=102)。
- 承接出处:迭代 `2026-09-23-invest-effects-calc` 逐卡讨论 T-3,用户裁定(2026-09-24):①特权武装箱按简易武装箱同款处理——overlay 标题改特权武装箱、四选一候选 = 特权装备;②「环境表登记不够通用——之前的立刻获得,现在这个要指定节点,在2-1」。
- 状态:定稿
- 文档清单:无详设(单文档方案,§2 即完整设计)

## 1. 问题与动机

**现状症状**:

1. 登记模型只有「获得即发」:`GiftGrant`(kernel/cw_investments.py)的通道
   `chars_immediate`/`chars_conditional`/`items_immediate` 全部在 `gain_invest_env`
   落地时点立即生效;「第二位面开始时」类时点效果无处登记(登记即错时点)。
   首例 = 特权阶级(本迭代落地)。**勘误界定**:增发货币(一/二/三位面开始晶矿)
   已走经济结构化通道不在本缺口(`ENV_ECONOMY['增发货币'].gold_per_plane_start=(6,8,12)`,
   cw_investments.py:1161,sim 位面开局金消费);策略侧定时族(军备供应链
   「接下来5个节点开始时」、红钻/蓝钻闪耀「3个节点后」)为相对/重复时点形态,
   与本通道不同构,归 §1「明确不解决」。
2. 武装箱获得弹窗的识别锚 = 品名不是族名:画面档
   `currency_war_armory_box_dialog.yml` 的 id_mark = `标识-简易武装箱`
   (text=`简易武装箱`),overlay 注册表
   (kernel/cw_overlay_registry.py:227)与弹窗 op
   (cw_screen_armory_box.py)同锚;`currency_war_app.py::_IN_MATCH_KEYWORDS`
   fallback 关键词也是 `简易武装箱`。特权武装箱弹窗(标题「特权武装箱」)首遇时,
   全链路靠 LCS 阈值的巧合命中(见 §2.6 数学),无显式登记。
3. 特权装备识别面已就绪但有暗闸、链路无入口:四选一候选归一化域 `EQUIPMENT_ROSTER`
   已含全部 36 件特权装备(cw_equipment_data.py:141-177,roster :233),但登记表
   没有任何通道能把特权武装箱发给玩家;且选卡读数闸 8 字上限先于归一化,会把
   9 字特权名确定性静默丢弃(四选一缩三选一,详见 §2.7)。

**根因归层**:①语义层——登记模型缺「发放时点」维度;②约定层——画面锚按具体品名
登记,而非按画面身份(弹窗族)登记。

**解决到哪**:

- `GiftGrant` 增定时道具通道(指定「位-轮」),特权阶级完成登记;
- 容器持「待发放队列」,获得链提供到点发放原语,sim 世界在进节点收口消费;
- 武装箱弹窗识别锚泛化到族名(武装箱),特权弹窗显式覆盖;
- 选卡读数闸上限放宽至注册表最长名(9 字特权名可达),归一/决策面不动。

**明确不解决**(防外溢):

- 相对延迟时点(N 个节点后 / 接下来 N 个节点开始时)——另一形态,届时另批;
- 实机局 discharge 接线——实机容器备战真值由 heavy 观察覆盖(两态制观察赢,
  fields.md §2.3),队列在实机局保持登记态不消费;待实机首遇后按需另批;
- 特权/进阶武装箱**备战槽图标模板**与开箱动作 op 对非简易箱的支持(现役
  `round_fail('无简易武装箱')` 响亮暴露)——实机裁片缺,沿 T-421 待实机首遇;
- 特权武装箱弹窗/选卡画面的实机截图对照校准(布局沿用简易箱档,首遇验证);
- 特权装备打分质量(`pick_equipment` 通用 props 面消费,策略侧辖域)。

## 2. 方案

### 2.1 登记模型:GiftGrant.items_scheduled

`GiftGrant` 新增字段 `items_scheduled: tuple[tuple[str, str], ...] = ()`,
元素 = (节点键, 道具名),节点键格式 `'位-轮'`(如 `'2-1'` = 位面2第1节点)。

- 登记首条:`ENV_GIFTS['特权阶级'] = GiftGrant(items_scheduled=(('2-1', '特权武装箱'),))`。
  「位面开始」= 该位面第 1 节点(权威先例:位面开局环境金 `gold_per_plane_start`
  落在 (plane, 1) 节点窗,sim/cw_sim_backend.py `_apply_env_plane_gold`);
  效果原文直读,数量 = 元素重复次数(与 items_immediate 同约定)。
- `_validate_env_gifts`(import 即炸)扩展三校验:①节点键格式
  `^[1-3]-[1-9]$`;②道具名禁 ∈ `CHARACTER_ROSTER`(道具/角色通道串行防呆);
  ③空发放集判定并入 items_scheduled(即时角色/条件角色/即时道具/定时道具全空 = 数据残缺)。
- **`BENCH_ITEM_NAMES` 派生面同步扩展**(正确性关键):词表当前从两张 GiftGrant
  授予表的 `items_immediate` 派生;定时道具同为占席道具,派生式并入
  `items_scheduled` 的道具名——否则溢出位身份 kind 判定会把「特权武装箱」
  当角色(假角色进合成素材组,cw_gain_chain `_build_pool` / sell_bench 溢出腿)。

### 2.2 容器队列:pending_item_grants

新容器字段 `pending_item_grants: Field[list[dict]]`(dict-list 先例 =
`receipts`,cw_game_state.py:2403),语义 = 「已登记、未到点发放的占席道具队列」:

- entry 形:`{'env': <环境名>, 'plane': <int>, 'round_num': <int>, 'item': <道具名>}`。
  env = 登记来源(provenance/对账);plane/round_num = 入队时解析好的目标节点
  (解析在校验期保证格式,登记期完成转换)。
- 开局种子底座 = `[]`(A 类,与 active_env 同批;`seed_opening_state` +
  test_cw_game_state_opening_seed `_A_SEEDED` 同步)。
- 域归属 = `match_facts`(环境/持卡所在域),`DEFAULT_GS_SCHEMA['match_facts']`
  5→6,版本注记 = 新增 pending_item_grants(cw_game_state.py:170);
  行级 `GAME_STATE_SCHEMA_VERSION` 不动(域粒度版本即为此设,§3.7.1)。
- 写端声明:**唯一逻辑写端 = 获得链**(on_env_gained 登记入队 / discharge 消费回写);
  **无观察写端**——队列是卡文推算知识,游戏 UI 无「待发放列表」可读。
  fields.md 新节随正本更新阶段落地。
- 对账申报:按 `cw_projection_audit` 维护纪律,新容器字段必须在
  `PROJECTION_AUDIT` 登记行(登记缺失 = 完备性测试红,测试 =
  test_cw_board_derived_and_reorder.py)+ 同步人读镜像
  `.debug/progress/2026-09-16-strategy-terminal-contract/projection-audit.md`
  (模块 docstring 维护纪律:改表须同步改镜像;行状态 = `process_only`,
  无观察读端,§2.2 写端声明推论)。

### 2.3 获得链:登记入队 + 到点发放原语

- `on_env_gained` 道具通道扩两支:`items_immediate` 语义不变;
  `items_scheduled` 逐项入队(一次 write 回写整表)+ 效果串
  `item_scheduled:<名>@<节点键>`(如 `item_scheduled:特权武装箱@2-1`,
  数量 = 元素重复次数,发放事实登记与即时通道同阶)。
- 新原语(kernel/cw_gain_chain.py,与 on_env_gained 同区):

  ```
  discharge_due_item_grants(gs, *, plane: int, round_num: int,
                            rand: bool, sig: ChannelSig) -> tuple[str, ...]
  ```

  ①读 `pending_item_grants` 现值,按 (plane, round_num) 分割命中/保留;
  ②命中项逐个 `_place_bench_item`(备战空槽 → 席满溢出落位 → 溢出位被占零写
  留证,复用 2026-09-24 道具落位语义),每项效果串 `item_gift:<名>`;
  ③命中非空才一次 write 回写保留队列。零吞错:落位异常上抛(gain-chain.md §6),
  队列回写收尾——生产挂点(sim 窗口守卫)无重入面,无幂等需求;未来实机挂点
  接线时按其重入面另评。
- rand 语义:环境发放 = 确定发放,调用方传 `rand=False`(gain-chain.md §5)。

### 2.4 sim 世界生效:进节点收口挂点

- 挂点 = `SimBackend._begin_node_window` 内 `self._apply_env_plane_gold(plane)`
  之后一行:调 `discharge_due_item_grants(self.gs, plane=plane, round_num=r,
  rand=False, sig=logic_sig('sim:env'))`(`logic_sig` 先例 =
  sim/cw_sim_base.py:37;组名沿 `sim:env` 与环境金同窗)。
- 时机正确性:该收口有幂等守卫(`_window_begun_ord`,cw_sim_backend.py:1294-1299)
  且**位面过渡点空白与直进节点共用**(:1287-1289)——(2,1) 的发放发生在位面过渡屏
  被点掉、2-1 节点窗真正打开时,即「第二位面开始时」;窗口重放不会双发。

### 2.5 实机侧边界(不对称申报)

实机局不接 discharge(见 §1 明确不解决):队列登记后保持原样,备战真值由观察覆盖。
消费方(策略前瞻「还有几只箱在路上」)现无;首遇后若需要,另批接 prep 入口。

### 2.6 武装箱弹窗识别锚泛化(品名 → 族名)

- 数学依据:`find_by_lcs(source, target, percent)` 判定式 = 
  `LCS(source, target) >= len(source) * percent`,**分母 = 登记文本长度**
  (one_dragon/utils/str_utils.py:26-44;画面匹配消费 =
  one_dragon/base/screen/screen_utils.py:130)。锚 text 改 `武装箱` 后:
  对标题「简易武装箱」LCS=3 ≥ 3×0.5 ✓(1.0)、对「特权武装箱」同 ✓;
  现役锚 `简易武装箱` 对「特权武装箱」= 3 ≥ 5×0.5(0.6)——巧合命中属实,
  本改动把巧合换成显式。
- 同款先例:四选一选卡画面档 id_mark `标识-武装箱` text=`武装箱`
  (currency_war_battle_prep_supply_box.yml:5-18)生产现役,两箱选卡屏通用。
- 改动面(四处,同锚同值):
  ①画面档 `currency_war_armory_box_dialog.yml`:area
  `标识-简易武装箱`→`标识-武装箱`、text `简易武装箱`→`武装箱`
  (经 MCP `upsert_screen_area` + `delete_screen_area`,禁手编 yml);
  ②overlay 注册表 武装箱弹窗条 `anchor_area`(cw_overlay_registry.py:227);
  ③弹窗 op `CwScreenArmoryBox` 两处锚引用与 docstring
  (cw_screen_armory_box.py:60/:84);
  ④`currency_war_app.py::_IN_MATCH_KEYWORDS` fallback 关键词
  `简易武装箱`→`武装箱`(lcs_percent=0.8:LCS 3 ≥ 3×0.8 ✓)。
- 弹窗说明文案差异(「从四件简易装备中选择」vs 特权版)不入锚:画面身份由标题
  承担,说明文字不参与识别。

### 2.7 选卡(特权装备四选一):读数闸放宽 + 归一/决策零改动

- **读数闸改动(阻断项修订)**:卡名 OCR 读数闸现过滤 `2 <= len(读数) <= 8`
  (cw_screen_box_pick.py `_read_card_names`),且**先于归一化**——9 字特权装备名
  会被确定性静默丢弃,真实失败形态 = 四选一缩成三选一(策略在残缺候选集上
  「成功」选卡,非响亮暴露)。36 件特权装备中 5 件为 9 字名
  (战场进化手册/反卫星狙击枪/自适应外骨骼/痛觉阻断芯片/虫洞掘进钻头 各 +「·特权」,
  cw_equipment_data.py:156/158/160/169/175)。
  修法:上限改**注册表最长名长度派生**(模块级
  `_CARD_NAME_LEN_MAX = max(len(n) for n in _EQUIP_ROSTER_LIST)`,坐标系 =
  装备注册表最长名,新长名自动跟上,禁手抄常数);下限 2 不动。用例:9 字名
  经读数闸存活并归一精确命中(装配沿 test_cw_screen_progression_inline.py
  `_make_box_pick` 但须还原其 `_read_card_names` 桩以直调真读数闸,OCR 结果
  桩沿 test_cw_takeover_intel_pipeline.py 的 `cw_obs_core._ocr` patch 惯用法)。
- 归一化两段(注册名精确命中 → `lcs_resolve_strict` 兜底)与决策面零改动:
  36 件特权装备在册(cw_equipment_data.py:141-177),OCR 全名精确命中;
  失败 = 观察失败 round_fail 交回重读(现有语义,零新路径)。
- 风险登记:特权装备名含「·特权」后缀,OCR 缺读/形变的实际命中率无实机样本;
  读数闸放宽后形变态(如 8 字缺读)仍走既有两段转换,失败重读语义不变,
  不选错卡性质不变。实机首遇对照,不入本迭代判据。

## 3. 关键取舍

1. **容器队列 vs 复用效果账本(effect_inventory)**:效果账本辖「持续型效果的
   进展状态」(计数器模型,fields.md §5.1),其一次性定点发放与计数器模型不同构;
   且账本各挂点接线状态参差(「接线归辖批」注记多处)。队列字段直白、自足、
   可独立验收。正本化时此取舍进 fields.md 新节动机段。
2. **队列字段 vs 无状态扫描**:无状态扫描(每次进节点扫
   `ENV_GIFTS[active_env].items_scheduled`)需外置幂等账,且绑死「来源=active_env
   单一环境」——策略源定时发放(军备供应链族)无法容纳;队列 = 显式世界状态,
   队列清空天然幂等。
3. **泛化锚 vs 特权弹窗独立建档**:独立档要复制 OverlaySpec + op 双屏分支,
   而 LCS 分母语义(text='武装箱' 对两标题均 1.0)使单档泛化零歧义;选卡画面档
   已有同款先例。进阶武装箱(T-421)未来同一锚直接覆盖。
4. **实机 discharge 接线推迟**:观察已覆盖实机容器真值,接线是无遥测收益的
   行为面扩张;以「明确不解决」申报,防范围外溢。
