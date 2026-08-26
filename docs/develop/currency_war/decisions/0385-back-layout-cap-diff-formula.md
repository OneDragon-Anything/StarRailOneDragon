# 0385 后排布局选档勘误:双通道对账(公式 + CV 实测;推翻 0281 level 驱动)

- 状态: accepted(2026-08-26 同日口述双通道指令修订:单公式 → 公式+CV 对账)
- 日期: 2026-08-26
- 来源: run 26(2026-08-26 12:20-12:57,P2r7 用户热键停局)崩坏局取证
  (`.debug/sr_od_mcp/main_server.log` 只读取证)+ 用户口述(board_structure.md,
  最高权威,含同日量化公式与双通道对账指令追加);同批姊妹条目
  ADR-0386(off-target 卖出熔断,同局根因②)

## 背景(run 26 崩坏形态·根因①)

deployed 4/8 + 3 人躺备战 + 仙舟引擎全下岗 + 列车 2→1。根因① = 布局模型
错误(用户口述推翻):ADR-0281 的「level≥7→后排 8 格」归因错误——其唯一
8 格实证(狸猫局)本身带召唤物。用户口述澄清
(docs/game/currency_war/research/board_structure.md):**等级只定上场人数
cap,不定格子数;前台恒 4 格 + 后台恒 6 格;只有钻石或召唤物存在时后台才
变多**;同日量化公式追加:**后台格数 = 6 + (cap − level)**。

run 26 = lv8 无召唤物局(cap=level=8 → 应 6 格),代码按 8 格坐标跑:

- 8 格档槽位(464..1458)与 6 格基线(604..1315)**共享 604-1316 段**,差异
  只在两端扩展格(464/1458)——拖拽多数「碰巧」落在真槽,但两端扩展格恒空
  → `back_empty` 多计 2 个幻影空位 → deploy 拖向不存在的 1/8 号格被游戏拒
  →「源槽未变」重试烧尽 → **3 人躺备战**(崩坏形态的直接机制);
- 读板/空位计算(cap 板满门的 deployed 计数)按 8 格全失真;
- 同局根因②(off-target 卖出振荡,ADR-0386)独立成立:卖出的拖拽全部
  「源槽变 ✓」成功——off-target 误判输入未被 8 格误读污染,①修法不治愈②。

## 决策

1. **选档单一入口 `select_back_layout(ctx, screen, level=None, cap=None)`**:
   驱动 = 口述公式「后台格数 = 6 + (cap − level)」;cap 源 =
   `read_deploy_cap`(paddle 直读权威,X/Y 的 Y),level 源 = 显式参或
   session 等级链(单调链防毒化);任一读不到 → diff 按 0(退 6 格基线,
   失败安全侧 = run 26 崩坏形态的反向)。
2. **公式值路由 `back_slots_from_cap_diff(diff)`**(纯函数):diff0→6 /
   diff≥2→8 / **diff==1(7 格)档未建档 → 保守 8 格超集** + `note_7slots_pending`
   obs_conflict 留证(采集指引:钻石局截备战帧 → 交互实锤 → upsert
   后排7槽-1..7 → `_LAYOUT_PREFIX` 登记 7);diff<0(读错族)按 0、diff>2
   (DEPLOY_CAP_MAX_DIFF 域外)按 2——与旧幻影观察自洽(cap9/10/11 的
   lv7/8 局 diff≥2 全落 8 格,「9/10/11 全是 8 格」由此得解)。
3. **level 驱动模型整体作废**:删 `effective_back_slots` /
   `note_pending_7slots` / `_PENDING_7SLOT_LEVELS` / `back_prefix_for_level`;
   `read_deployed_chars` 的旧布局停机钩子(「level 对应档无档」)随驱动模型
   作废删除——公式选档恒落 6/8 已建档档,补档窗口守卫由 7 格留证承载。
4. **消费方全改**(grep 全量):`deploy_bench._back_row_centers`
   (原 `_back_row_centers_by_level`)+ `_deploy_deterministic` 中环重建
   (cap 复用现读值)+ `cw_identity_obs.read_deployed_chars` +
   `battle_prep_recognizer` 后排装备槽(前排模板先载,选档共享同一入口)+
   `prep_director._observe`(lv6 待采留证摘除;cap>level debug 记后排扩展量)。
5. **交叉验证保留**:`check_system_unit_layout`(系统单位恒最右,ADR-0281
   件3)作选档的兜底网(选档与画面不符 → layout_mismatch 留证);0281 的
   件3/件4(系统单位模型/剔除)不受本勘误影响,继续有效。

### 修订(同日口述双通道指令,W209 补充落地)

6. **双通道对账(两通道都做)**:
   - **公式通道**(快速路径)= 上述 1-2(6+(cap−level),两现成 OCR 读数);
   - **CV 通道**(画面实测)= `cv_back_slots(screen)`:后排 y 带(600-739)
     槽位存在性签名——候选位裁切(±71px)灰度 **std** 判别「槽存在」;
     **阈值 6.0 的标定依据**(W209 探针,sr-od-test 11 帧):无格背景
     std ≤ 2.9(6 帧 6 格态 × 两端扩展位 = 12 样本),空槽暗框 std ≥ 10.5,
     占位立绘 50-67——阈值取背景上限 2.07×、空槽下限 0.57×,双向余量 >1.7×,
     非硬调;格数 = 6 + 两端扩展位(464/1458)存在数(扩展几何 = 基线两端
     追加:6/8 档共享中段 604-1316 的实证推论,单端扩展即 7 格);
   - **对账语义(口述裁决)**:一致 → 公式值;**不一致 → CV 实测值**
     (画面事实 > 推导——公式依赖的 cap/level 两个 OCR 读数可能错)+
     `obs_conflict('back_layout_channel_conflict')` 留证带两值(便于判读
     查哪个 reader);CV 不可判(帧越界/锚位 606/1031 无槽签名,如 overlay
     遮挡/非备战帧)→ 退公式值(公式 = CV 偶发失效的兜底 + 低成本快速路径)。
   - 主从权衡:实现为「CV 可判则 CV 优先采信,公式兜底」——CV 判错面
     (特效/overlay 短窗污染)由锚守卫 + 节流留证网住,而公式判错面
     (OCR 误读,run 26 实证族)无自检;两通道写日志同报(`公式 X/cv Y`)。
7. **7 格档处理**:公式 diff==1 与 CV 单端扩展都自然给出 7;screen_info 未
   建档(仅 6/8)→ **保守 8 格超集** + `note_7slots_pending` 采集留证
   (同决策 2;超集读全扩展带,拖到不存在格被拒 = 廉价失败方向)。
   附带证据:「后排7槽-P2开局局」实拍帧经 CV 复核两端扩展位均为背景
   (std 2.8/2.1)= **6 格**,旧「7 槽」观察同属幻影——公式通道自洽的又一实证。

## Considered Options

- **A. 保留 level 驱动 + lv6 采集**:拒绝——run 26 实证 level 驱动在 lv8
  无召唤物局产生系统性幻影空位;口述(最高权威)已推翻;
- **B. diff==1 用 6 格基线(严格保守)**:拒绝——cap 差≥1 保证扩展格存在,
  6 格基线丢读扩展带(系统单位/扩展位单位不可见);8 格超集读全带,拖到
  不存在的位 8 被游戏拒 = 廉价失败方向(白拖一次 vs 永久漏读);
- **C. diff==1 停机钩子(补档窗口停机留证)**:拒绝——钻石+1 局非罕见态,
  停机烧局代价 > 超集降级代价;7 格真值由留证采集指引渐进补档;
- **D. 钻石图标/buff 面板单独识别**:拒绝——口述公式直接消解该问题
  (cap/level 两现成 OCR 读数相减即格数),无需新识别通道;
- **E.(修订批)只做公式通道,CV 仅留证不改选档**:拒绝——口述指令明确
  「不一致用 CV 实测值」(画面事实>推导);且公式判错族(OCR 误读,
  run 26 的 cap/level 读数族)无自检,单公式通道会重演 run 26;
- **F.(修订批)CV 判别用模板匹配(空槽暗框模板)**:拒绝——std 签名
  判据更简单且标定分离度极大(背景 ≤2.9 vs 空槽 ≥10.5),模板匹配引入
  光照/主题敏感面,收益不成比例(ADR-0281 空槽签名法已证可行,本通道
  是其廉价化);
- **G.(修订批)CV 扫全带逐 x 滑窗找槽(不依赖候选位)**:拒绝——已知
  6/8 档几何共享中段,候选位法(两端扩展位 464/1458 + 锚 606/1031)
  O(4) 裁切即可判档;滑窗法引入峰检参数与误检面,复杂度不成比例。

## 影响

- `cw_back_layout.py`:公式驱动重写(select_back_layout /
  back_slots_from_cap_diff / note_7slots_pending / back_row_slot_rects_ctx
  改前缀枚举)+ 修订批:cv_back_slots / note_channel_conflict / 双通道对账;
- `cw_identity_obs.py`:read_deployed_chars 选档改公式;停机钩子删除;
- `operations/prep/deploy_bench.py`:`_back_row_centers` / 中环重建;
- `recognizers/battle_prep_recognizer.py`:选档共享入口;
- `prep_director.py`:lv6 留证摘除;
- ADR-0281:**部分勘误**(level 驱动选档作废;件3 系统单位自检/件4 剔除
  保留;幻影档清除结论继续有效且被公式自洽解释);
- 测试:`test_cw_back_layout.py` 选档段重写(公式路由/选档入口/留证/
  公式驱动读板)+ `test_cw_r348_cap_domain.py` 重写(「cap 不进选档」锁
  反转为「cap 差进选档」)+ 修订批双通道锁(cv_back_slots 11 帧全量
  标定 / 对账一致 / 不一致 CV 优先+两值留证 / CV None 公式兜底);
- 采集待办:钻石+1 局(diff==1)备战帧 → 7 格交互实锤补档。
