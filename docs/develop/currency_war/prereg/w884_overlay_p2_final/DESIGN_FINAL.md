# W884 · overlay Phase 2 设计收口终版(五条定案)

- 日期:2026-09-11;性质:离线只读设计收口(未跑测试/未触实机;写入限本目录)。
- 输入:W839 报告(`w839_overlay_lifecycle/REPORT.md`,OverlaySpec 字段/五消费面切换表/§2.3 星徽秘典双语义)、W865 B-1 五条补充(`w865_doc_plan_review/REPORT.md`)、现状代码实读(`cw_obs_core.py:95-128` / `cw_observation_gate.py:152-167` / `prep_director.py:386-404` / `battle_loop.py:955-1052`)、W842 零漂移报告(`w842_zerodrift_verdict/REPORT.md`)、W859 复验产物(`w859_pv_reverify/judge_w859.json`)。
- 红线(不变):decision 语义 overlay ⇒ `closable=False`,由注册表一致性测试机器化(C1 红线)。

---

## 一、五条逐条定案

### 定案 1|非锚点判定分支的 spec 表达:**单通道 match='area'(建档收编)+ 动作通道,不引入 ocr_pair/point 判定通道**

先纠正 W865 补充 1 的归类:代码实读(`battle_loop.py:976-1012`)显示四支的性质并不相同——

| 分支 | 判定现状 | 判定本质 | 动作现状 |
|---|---|---|---|
| 0e2 概率表 | `标识-刷新概率表` area 锚 | **已是 area 锚** | 裸坐标点 ×(1501,263) |
| 0e3 道具详情(聘用书) | OCR『聘用书』 AND NOT 祈愿锚 | 裸 OCR + 负条件 | 裸坐标点 ×(1862,65) |
| 0f 消耗品详情 | OCR『消耗品』AND『拖动到』 | 裸 OCR 双条件 | ESC |
| 0g 阿哈装备 | `标识-简易装备` area 锚 | **已是 area 锚** | 裸坐标点(626,250) |

定案:**match 通道只有一种 = `anchor_area`(即 W839 原设计),另加 `close_action` 动作字段**。理由:

1. **0e3/0f 的「裸 OCR」是建档缺口的症状,不是判定语义**:两支是 modal 弹窗但**无 screen 档案**(与金币说明同型 C 类,`cw_obs_core.py:130-134` 注释自证该类存在)。两支均有稳定文本锚——0f 注释明言「拖动到」只出现在消耗品详情 modal(天然独有 id_mark);0e3 建档后 id_mark 用更长的独有文本(如『获得 … 聘用书』标题行)。建档后双条件坍缩为单 area 锚,自然进注册表,消灭孤儿分支。
2. **0e3 的祈愿负条件是分支序问题,由 `dispatch_priority` 解决**:负条件存在的唯一原因是 0e3(行 985)排在 0h 祈愿(行 1018)之前,祈愿选项名含「聘用书」会截胡。把祈愿试炼的 priority 排到道具详情之前,负条件即不需要——判定序本来就是注册表要显式化的数据(W839 §1.3「隐藏的第五维」),不该再往 match 通道塞负谓词。
3. **0e2/0g 的裸坐标是动作不是判定**:判定已是 area 锚,坐标进 `close_action='point'` + `close_point` 载荷,一致性测试校验坐标在 1080p 界内。ESC 动作同理进 `close_action='esc'`。
4. **为什么不选「保留窄实现函数」**:窄函数 = 这三支继续游离在单一源外,「新增画面忘进名单」缺口(ADR-0269 结构性病灶)对它们依然成立,与注册表化的立项目标相悖。ocr_pair/point 判定通道则为一个建档即可消灭的临时形态增加永久 spec 复杂度(负谓词的组合空间不可控),长期不优。

**随迁派生任务**:0e3(道具详情弹窗)/0f(消耗品详情浮层)两画面建档(screen_info entry + id_mark + fixture),成为 Phase 2 的前置子批(实机,见 §四)。

### 定案 2|UPPER_SCREENS 派生规则:**「属 overlay 者派生 + 非-overlay 残余段显式保留」两段式,不整表派生**

定案:注册表内全部条目(decision/display/system)自动并入 UPPER_SCREENS;**注册表语义覆盖不到的非 overlay 上层屏保留为显式残余元组** `UPPER_SCREENS_NON_OVERLAY`(带逐条 why 注释)。`UPPER_SCREENS` 常量本身改为两段拼接的派生值,消费方(`is_prep_like_frame` 逐屏判定)不动。

两案影响分析(现名单 24 屏,`cw_obs_core.py:95-128`):

- **整表派生案的问题**:24 屏中约 8 屏不是 overlay 生命周期对象——位面过渡(过渡帧)、模式选择/阵容编辑(赛前画面)、备战-角色详情/装备详情浮窗/角色信息提示(检视浮窗,无 handler/无退场动作)、攻略码输入弹窗(工具域)。整表派生强迫它们进注册表 → 要么造出 handler=''、closable=False、无任何消费面的僵尸 spec(注册表语义污染,一致性测试的「decision 必有 handler」等断言被迫加豁免),要么改 `OverlaySpec` 语义把它们排除 → 排除后又回到手工名单,双源没消掉只是换了形状。且任何成员集变动直接改变钩子/帧态门行为(局72 伙伴误拖防线),零漂移门下不允许无谓成员变化。
- **本定案的行为影响 = 零**:派生段成员集 = 现名单中属注册表的条目(逐条对表核过:选择伙伴/祈愿试炼/遭遇节点/投资策略/投资环境/盛会之星/积分奖励/简报/中断挑战弹窗/未达上限警告/提示-前台无角色/武装箱弹窗/商店刷新概率表/星徽详情/星徽秘典弹窗/备战-专家邀请函/补给/难度确认),残余段 = 其余 8 屏原样保留。新增 overlay 建档 + 一条 spec 即自动获得帧态门排除,防回归测试断言「registry 每条 ∈ UPPER_SCREENS 派生集」(W839 §4.5 原断言,覆盖面收窄为 registry 侧 + 残余段逐条注释问责)。
- **已知残余缺口显式挂账**:金币说明(C 类无档案 overlay)与 0e3/0f modal 在建档入注册表前仍走锚 OCR 补充判定(`gold_info_overlay_open` 同型),不属本定案新增缺口。

### 定案 3|零漂移判据对齐 W842:**决策序列逐位一致 + 显式剥离已知非确定性 + 重放主张 pin HEAD 基线**

迁移验证门(每消费面切换一步执行)定案:

1. **判据 = 决策序列逐位一致**:同种子窗重放,`decisions.jsonl` 的 actions / v3_intention / 决策金流序列逐位一致;outcomes/shop_snapshots 账本剥离 schema 演进字段后逐位一致。**不**以聚合指标(hp mean/幸存率等)为门——聚合对局部 dispatch 语义变化不敏感,且受种子窗波动污染(W841 教训)。
2. **显式剥离清单**(W842 §二.3 实锤的进程级非确定性,逐条声明后剥离,防假红):
   - 开局装备名哈希随机化:叶子路径 `state.deployed.*.equips` / `state.equipped` / `state.owned_equips` / `sim.unworn_equips` / `rust_units` / `worn_equips_total` 的差异不计漂移(同 seed 同代码两次运行即不同,零行为影响);
   - schema 新增默认 null 字段(遥测演进);
   - run_id/账本目录命名差异(归一后比)。
3. **重放主张 pin HEAD 基线**:每个切换批开工时以 worktree 隔离 + detached HEAD 冻结基线,commit 号写进该批报告的重放配置声明表(W842 §一格式);报告中的「零漂移」主张必须携带该 commit 号,禁无基线号的漂移主张。
4. **本方案预期零行为变化的唯一例外**:星徽秘典出清场表(定案 5)——环入口不再一键关它,改由 0i 选卡消化。该步**豁免零漂移门,改为行为断言门**(0i 选卡路径触发、清场轮内不再点它的关闭钮),在切换表中单列。

### 定案 4|依赖关系显式化:**与 W859 无批间依赖;实为两条执行面共享,任务记录以此为准**

- **裁决:overlay Phase 2 与 W859(件价值复验)之间不存在数据/逻辑依赖**。overlay 注册表是画面识别/派发/清场/退场的声明层重构,不触碰策略权重与开臂状态;W859 是策略域的 PREREG 重验。任务书此前「w859 前置」的说法系编排侧记忆残留,本文件落文后以本条为准。
- **实际共享面(执行序约束,非依赖)**:
  1. **实机单跑道**:Phase 2 的实机哨兵观察局(验证阶梯末段)与任何在飞实机局共享单跑道,只排执行顺序,不构成「谁先完成才能开工」;
  2. **重放基建同源**:零漂移门与 W859/W842 消费同一套重放 worktree 方法与种子窗纪律(定案 3 即为共用条款)。
- **W859 现状核实**:复验已有终态产物(`w859_pv_reverify/judge_w859.json`,W854 判据 recommendation=`delete_code_keep_adr0497`)——即使曾按「前置」理解,该前置已结算,不存在挂起依赖。Phase 2 可独立派单。

### 定案 5|遗留裁决:**星徽秘典 = decision 化;Phase 1 临时哨锁在注册表红线断言转绿的同 commit 拆除**

- **星徽秘典双语义 → decision 化**:`semantic='decision'`、`handler_id='HandleStarTome'`(0i 现有 `_handle_star_tome_pick` 逻辑收拢为 handler 类)、`closable=False`、**从 ENTRY_OVERLAY_CLOSE 移除**(spec 迁入后清场表整体删除,A 面改派生,见切换表)。理由:
  1. C1 红线一致性:它有选卡价值(0i 已实现阵营匹配选卡),「关闭即丢决策内容」;allow_discard 字段会把「注册表层禁止的双语义」改名为「注册表层允许的双语义」,矛盾没消失只是合法化了;
  2. 行为上严格不劣:现状 = 环入口先清场丢一次选卡 → 未清才 0i 选卡;decision 化后 = 环入口不清 → 0i 必然接管选卡,星徽入 owned、槽腾空,少丢一次选卡机会(W839 §1.1 已指认现状是「隐式战术选择」,显式化后选保留价值);
  3. 行为变化面唯一且已在定案 3 挂行为断言门。
- **Phase 1 临时哨锁拆除时机**:Phase 1 落的两把锁——①`prep_director` bail 清单补遭遇节点(生产行为,保留);②测试锁「遭遇节点 ∉ ENTRY_OVERLAY_CLOSE」+ bail 路径行为锁(`test_cw_overlay_bail.py`)。其中**「清场表不含遭遇节点」的临时哨在注册表一致性测试(C1 红线断言:decision ⇒ closable=False ∧ 派生清场集不含任何 decision 条目)全绿的同 commit 删除**——红线断言是其超集,双锁并存即双源。bail 行为锁(遭遇屏锚命中 → `event_overlay='事件overlay:encounter'` → bail)保留,它是行为不变量不是哨。

---

## 二、OverlaySpec 完整规格(终版)

```python
# 落点:obs/overlay_registry.py;键 = screen_name(与 screen_info 体系同键空间)。

@dataclass(frozen=True)
class OverlaySpec:
    # ── 识别 ──
    screen_name: str            # 键;必须已建档于 assets/game_data/screen_info
    anchor_area: str            # 识别锚 area 名(五消费面统一走此锚,禁各自再写锚)
    anchor_area_alt: str = ''   # 第二锚(可选;双锚防误派,0a0/0a3 经验;非空 = 同帧双命中才派发)
    # ── 语义 ──
    semantic: str               # 'decision' | 'display' | 'system'
    handler_id: str = ''        # 专属 handler 类名;decision 恒非空;'' = 无(清场/兜底消化)
    closable: bool = False      # 可清场否;decision 恒 False(C1 红线,一致性测试断言)
    # ── 退场动作 ──
    close_action: str = 'close_area'  # 'close_area' | 'point' | 'esc' | 'handle'
    close_area: str = ''        # close_action='close_area' 时必填(清场/退局链共用)
    close_point: tuple[int, int] | None = None  # ='point' 时必填(1080p 界内,测试校验)
    # ── 派发与计数 ──
    dispatch_priority: int = 0  # C 面派发优先序(全表唯一,测试断言;注释序转数据)
    recovery_exit: str = 'close'  # 恢复/退局面动作:'esc'|'back_button'|'handle'|'close'
    bail_tag: str = ''          # director bail 同因键后缀;decision 类必填且全表唯一
```

派生规则:注册表全量条目并入 UPPER_SCREENS(定案 2);`UPPER_SCREENS_NON_OVERLAY` 残余段 8 屏带 why 注释;清场集 = 遍历 `closable=True` 条目(声明序);bail 扫描集 = 遍历 `semantic='decision'` 条目。

**一致性测试断言集**(test_cw_overlay_registry.py,在 W839 §4 六条基础上修订):
1. 建档完整性(screen_name/anchor_area/close_area 在 screen_info yml 存在);
2. handler 存在性(decision 类 handler_id 非空且可 import);
3. **C1 红线**:decision ⇒ closable is False;派生清场集不含 decision 条目(吸收 Phase 1 临时哨后成为唯一红线锁);
4. bail_tag 唯一;
5. registry 全条目 ∈ UPPER_SCREENS 派生集(残余段不在此断言内,靠注释问责);
6. dispatch_priority 唯一;
7. close_action 载荷完整性('point' ⇒ close_point 非 None 且 0≤x≤1920/0≤y≤1080;'esc' ⇒ 无需载荷;'close_area' ⇒ close_area 非空);
8. `UPPER_SCREENS` 常量值 = 派生值逐条一致(防手改常量绕过派生)。

---

## 三、五消费面切换表(终版)

| 消费面 | 现状 | 终态 | 切换要点 | 验证门 |
|---|---|---|---|---|
| A P0 清场 | `ENTRY_OVERLAY_CLOSE` 5 条自有 dict | 删除;遍历 registry `closable=True` | 星徽秘典移出(定案 5,行为断言门);`ENTRY_OVERLAY_CLEAR_ROUNDS/SETTLE_S` 保留为机制常量 | 零漂移(除星徽条目)+ 行为断言 |
| B director bail | tuple-of-tuples 9 条手写锚/tag | 遍历 registry `semantic='decision'` 锚扫 → `bail_tag` 单源 | tag 键与 `_clear_bail_count` 同源;bail 携 handler_id | 零漂移(判定序不变,扫描集成员 = 现 9 条 + 白名单一致性核) |
| C battle_loop 派发 | ~19 手写 if 分支 | 表驱动分发器,按 dispatch_priority | 0e3/0f 建档入表;0h(祈愿)priority 提前使 0e3 负条件消失;0e2/0g 裸坐标进 close_action 载荷;备战双锚+稳定门语义不变;0i 收拢 HandleStarTome | 零漂移 + overlay 行为锁组全量 |
| D 退出/恢复链 | 手写 OCR 关键词表 + area 分支 | 消费 recovery_exit 逐类派发 | 「遭遇其一」等 OCR 关键词与注册表锚对齐(同屏同锚) | 恢复链行为锁 |
| UPPER_SCREENS | 24 屏自有 tuple | registry 派生段 + `UPPER_SCREENS_NON_OVERLAY` 残余段(8 屏) | 拼接值不变,消费方零改动 | 断言 8(常量=派生值)+ 零漂移 |

切换顺序:先建 registry + 一致性测试(含断言 8,先锁后切)→ A → B → C → D/UPPER_SCREENS,每面独立 commit。

---

## 四、派单就绪声明

**派单就绪**(设计面阻塞 = 0),实施拆为:

- **子批 0(前置,实机)**:0e3 道具详情弹窗 / 0f 消耗品详情浮层建档(screen_info + id_mark + fixture;判据按 od-dev-screen-onboarding 9 步)。无此两档,定案 1 的 area 通道收编不成立。
- **子批 1**:registry + 一致性测试 + UPPER_SCREENS 派生(断言 8 先锁)。
- **子批 2-5**:A/B/C/D 四面逐个切换,每面独立 commit + 定案 3 验证门。
- **子批 6**:实机哨兵监控一局,验证 P0 清场/`事件overlay:` 日志不变量 + 星徽 0i 选卡新路径。

依赖记录(落本文件为准,定案 4):与 W859 无批间依赖;仅实机单跑道执行序与重放基建同源两项执行面共享。

## 剩余阻塞:0(设计面)

唯一外部前置 = 子批 0 两画面建档(实机窗口依赖,非设计阻塞);星徽秘典行为变化已挂行为断言门,不阻塞派单。
