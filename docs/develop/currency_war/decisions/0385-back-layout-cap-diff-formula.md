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
   建档(仅 6/8)→ **保守 8 格超集运行**(超集读全扩展带,拖到不存在格被拒
   = 廉价失败方向)+ **停机钩子**(见件①)。
   附带证据:「后排7槽-P2开局局」实拍帧经 CV 复核两端扩展位均为背景
   (std 2.8/2.1)= **6 格**,旧「7 槽」观察同属幻影——公式通道自洽的又一实证。

### 件③(同日用户点名,停机钩子处置)

8. **布局停机钩子:语义保留,输入链改**(W209d):ADR-0281 的
   「无档 → 停机+flag 引导现场采集」钩子在 `read_deployed_chars` 复活,
   触发判据从「effective_back_slots(level) 无档」改到
   `resolve_back_slots` 的**对账原始格数 `n_raw` 无档**(=7,钻石+1 局:
   公式 diff==1 或 CV 单端扩展)——停机保画面 + flag 引导现场拖拽采集 7 格
   真值(采完 upsert 后排7槽-1..7 + `_LAYOUT_PREFIX` 登记 7,永不再停)。
   flag 文案带公式/CV 两值与 cap/level/diff 快照(双通道话术,替旧 level
   驱动话术);帧态门(is_prep_like_frame)语义不变。
9. **旧留证机器清理**:「lv6=7 格存在性待采」的问题已被口述公式回答
   (7 格 = 钻石+1,与等级无关)——`_PENDING_7SLOT_LEVELS` /
   `note_pending_7slots` / `note_7slots_pending`(W209 首轮曾建的 diff==1
   留证)整套语义作废清理:7 格的存在性已定,**缺的只是坐标档,由件①钩子管**
   (双通道:轻量 obs_conflict 留证 vs 停机采集,选后者——7 格档无坐标时
   超集运行对部署有代价,且钻石+1 局可遇不可求,停一次采齐一劳永逸)。
10. **公式-历史实证张力(待解,批内不硬解)**:唯一历史 8 格实证(狸猫局
    lv7 cap8/9 两帧同为 8 格)与公式 6+(8−7)=7≠8 冲突。候选解释:①召唤物
    加格但不加 cap(公式需补召唤物项)/②当年 cap 读数有误/③召唤物局两帧
    实为 cap9。处理:双通道对账天然覆盖(CV 为真值,公式不符 →
    `back_layout_channel_conflict` 留证);**run 27+ 验证锚点加一条「遇钻石/
    召唤物局:记录 cap/level/CV 实测格数三点对」**,攒数据后定公式是否需
    召唤物修正项。常量 `FORMULA_SUMMON_TENSION_NOTED`(cw_back_layout)
    记档该未解项。
11. **CV 新格数防抖重读(W209h,run 27 停机事故热修)**:run 27 起 69s 被
    `hook:back_layout_no_profile` 停——flag「对账格数=7(公式 6/CV 7;cap=8
    lv=8 diff=0)」;编排者复算两帧逐位 std:停机帧 1458 位=**6.5**(阈值 6.0
    擦线过;真槽 ≥10.5/背景 ≤2.9 之间**无人带**),fixture 同位 2.2,公式
    6 与复测一致 → **特效/粒子瞬态把单帧顶过阈值 = CV 假阳**。修法(阈值
    不动——6.0 标定有据,瞬态问题用重读解):CV 读数产生「新格数」
    (≠公式值 且 ∉ 已建档档 {6,8},即会触发 7 格采集/停机的读数)→ 单帧
    不行动:隔 ~1s 重读 2 次(`ctx.screenshot` 现截),**三次一致才按 CV
    值行动**(停机/选档);任一不一致 = 瞬态自愈,退公式值 +
    `back_layout_cv_transient` 留证(带重读序列,resolve 返回 `cv_readings`)。
    house 先例 = shop 未识别卡 r34(重读 2 帧仍 miss 才真停)。辖域单点
    收敛:`resolve_back_slots` 的 CV 消费点(停机钩子读其 n_raw,自动受益)。

## Considered Options

- **A. 保留 level 驱动 + lv6 采集**:拒绝——run 26 实证 level 驱动在 lv8
  无召唤物局产生系统性幻影空位;口述(最高权威)已推翻;
- **B. diff==1 用 6 格基线(严格保守)**:拒绝——cap 差≥1 保证扩展格存在,
  6 格基线丢读扩展带(系统单位/扩展位单位不可见);8 格超集读全带,拖到
  不存在的位 8 被游戏拒 = 廉价失败方向(白拖一次 vs 永久漏读);
- **C. diff==1 停机钩子(补档窗口停机留证)**:首轮拒绝(钻石+1 局非罕见态,
  停机烧局代价 > 超集降级代价)→ **件③修订为采纳**(选项 H):用户点名
  处置——钩子语义保留、输入链改双通道;裁决翻转的依据 = 7 格坐标档缺失的
  超集代价(拖到不存在格白烧重试)+ 钻石+1 局可遇不可求(不停机就永远采
  不到 7 格真值)共同压过单次停机烧局;超集运行兜底保留(停机是一次性的,
  采集前先按超集跑);
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
  O(4) 裁切即可判档;滑窗法引入峰检参数与误检面,复杂度不成比例;
- **H.(件③)7 格无档继续 obs_conflict 留证不停机(维持首轮 C 的拒绝)**:
  拒绝——留证攒不齐坐标真值(判读侧只能看见「该有 7 格」,仍要人工截帧
  实锤);停机钩子一次性烧局换「现场拖拽逐位实锤」是采集 7 格档的唯一
  闭环路径(ADR-0281 的 8 档即此法闭环);见决策 8-9。

## 影响

- `cw_back_layout.py`:公式驱动重写(select_back_layout /
  back_slots_from_cap_diff / note_7slots_pending / back_row_slot_rects_ctx
  改前缀枚举)+ 修订批:cv_back_slots / note_channel_conflict / 双通道对账
  (select_back_layout 委托 resolve_back_slots 全量解析)+ 件③:
  note_7slots_pending 删除(留证机器清理)、FORMULA_SUMMON_TENSION_NOTED
  张力记档;
- `cw_identity_obs.py`:read_deployed_chars 选档改双通道;件③:布局停机
  钩子复活(触发判据 n_raw 无档,flag 双通道文案,帧态门保留);
- `operations/prep/deploy_bench.py`:`_back_row_centers` / 中环重建;
- `recognizers/battle_prep_recognizer.py`:选档共享入口;
- `prep_director.py`:lv6 留证摘除;
- ADR-0281:**部分勘误**(level 驱动选档作废;件3 系统单位自检/件4 剔除
  保留;幻影档清除结论继续有效且被公式自洽解释);
- 测试:`test_cw_back_layout.py` 选档段重写(公式路由/选档入口/读板双通道)
  + `test_cw_r348_cap_domain.py` 重写(「cap 不进选档」锁反转为「cap 差进
  选档」)+ 修订批双通道锁(cv_back_slots 标定 / 对账一致 / 不一致 CV 优先
  +两值留证 / CV None 公式兜底)+ 件③钩子锁(n_raw=7 停机+flag 双通道文案
  / 6/8 已建档永不停机 / 旧留证机器已清理)与 r330 帧态门锁适配;
- 采集待办:钻石+1 局(diff==1 或 CV 单端扩展)停机钩子现场采集 7 格真值;
  run 27+ 遇钻石/召唤物局记录 cap/level/CV 三点对(公式召唤物张力,决策 10)。
