# 0281 后排布局模型重审:7/9/10/11 档全系幻影,选档改 level 驱动 + 系统单位恒最右

- 状态: accepted
- 日期: 2026-08-24
- 来源: 用户质疑 cap=9≠后排9槽 触发的全行签名扫描终判(2026-08-23 17:4x)+ 用户口述系统单位模型(17:5x);12槽误档事故(8a56db39)与残留第二层(a2636cb1)的后续闭环

## 背景

r84 建立的「后排槽数 = max(6, cap)」六档布局模型(6-11 档全注册)在
cap=12 误读事故后被用户连环质疑,全行证据重审:

- **幻影实证(双源交叉)**:①对 cap=9/10/11 三张触发帧逐格测空槽签名
  (空槽=暗框 0.37/边缘 19)——三帧后排**全部是同一个 8 格布局**
  (边缘带 393-1529);251-393 与 1529-1671 段在三帧全为无格背景
  (暗 0.00/边缘 4-5),1671+ 是装备栏。②系统单位恒最右模型(用户
  口述)——三触发帧狸猫实测 x=1329/1467 只与 8 格布局自洽。
- **幻影成因 = 循环论证**:r84 的「五组实测」里 cap8→8 是真(狸猫局
  交互实拍),cap9/10/11 是把 SIFT 命中往外推网格上套——命中本就落在
  8 格布局内,两种网格编号都解释得通,「右侧空槽实证」实为无格背景。
- **真值布局**:lv3-5→6 格(基线带 534-1386,多局验证)/ lv7-8→8 格
  (393-1529);**cap(宝钻叠加)与布局无关**(两帧同 lv7 cap8/9 同为
  8 格)。lv6→7 格存在性未知(留待采;按用户模型 7 格存在时狸猫应在
  1174/1316)。
- **系统单位恒最右模型**(用户口述权威):狸猫(狸小虎/狸小龙)/佩佩类
  系统召唤单位恒占布局**最右槽位(们)**、不可拖、布局变 x 跟着最右格
  移动(非全局固定坐标——旧「狸猫固定坐标 1316/1458」是不完整表述)。

## 决策

1. **幻影档清除**:`battle_prep.yml` + `_od_merged.yml` 删 后排7/9/10/11槽-*
   全部 area(37+37 条;源与派生层同步删——a2636cb1 残留事故的教训);
   `_LAYOUT_PREFIX` 只留 `{6:'后排', 8:'后排8槽'}`;
2. **选档改 level 驱动**:`effective_back_slots(level)`:≤5→6 / ≥7→8 /
   ==6→保守 6 + `note_pending_7slots` 留证(`back_7slots_pending`,
   `_PENDING_7SLOT_LEVELS={6}`;实锤后清集合并登记 7 档);
   `read_deployed_chars` 的 `deploy_cap` 参数删除,level 缺省走 session
   等级链;cap 误读不再影响选档(r414 防线语义适配:prep_director 的
   cap 域检查只剩「cap<level 不可能」半 + 宝钻叠加 debug);
   停机钩子条件改为「level 对应档无档」(6/8 都有档 → 正常运行永不
   触发,留作补档窗口守卫);
3. **系统单位布局自检**(`check_system_unit_layout`,常设判别器):
   后排读到系统单位(roster cost==0 段,char_id 判定)时,SIFT 单点定位
   (`ransac_locate_x`,homography 投模板中心,部分可见可定位)其实测
   x,与所选档最右 k 格中心对拍(k=系统单位数);差 >40px(<半格宽 71,
   一个格位错 142 必超)→ `obs_conflict('layout_mismatch_by_system_unit')`
   (300s 节流)。比空槽签名便宜(狸猫模板已有);
4. **deploy 剔除不可拖单位**:`exclude_system_units`(cost==0)统一
   收口 `_fix_misplaced_rows`(r250 场内前排保证此前取 `back_chars[0]`
   可能选中狸猫 → 拖必失败白烧重试)与 `_sell_offtarget_deployed`
   (原行内守卫);
5. **后排装备槽同源**:`battle_prep_recognizer` 的后排装备读取
   (`read_row_equipped` 固定 6 格会漏 lv7+ 的位7-8)改
   `back_prefix_for_level(level)` 选档;D-50 旧告警(cap>level→后排
   可能>6)随新模型作废删除。

## Considered Options

- **A. 保留 9/10/11 档 + 降置信标记**:拒绝——幻影档会让 cap 误读
  (如 8/8→12)再度被合理化(12槽误档事故重演),且格点坐标本身
  是外推产物,继续用 = 在错误地基上叠逻辑;
- **B. cap 驱动改真值校准(实测 cap→格数映射)**:拒绝——cap 与布局
  无关已被双源实证,重标定是在错误驱动量上拟合;
- **C. level 驱动 + lv6 保守降级(选定)**——驱动量与游戏机制一致
  (等级解锁团队规模),lv6 唯一未知态显式留证等采集,不停机
  (6 格保守跑的代价 = lv6 局少识别一个可能存在的槽,可接受);
- **D. 狸猫固定坐标判别器(1316/1458 硬编码)**:拒绝——恒最右模型
  下狸猫 x 随布局变,固定坐标只在 8 格局成立(旧 insights「狸猫固定
  坐标假说部分成立」的根因正是样本全在 8 格局);
- **E. 布局自检用空槽签名**:拒绝——每帧逐格暗框检测贵;狸猫 SIFT
  模板已有,恒最右对拍是更便宜的常设判别器(空槽签名留作离线分析)。

## 影响

- `cw_back_layout.py`:level 驱动重写(`_LAYOUT_PREFIX` 缩到 {6,8}、
  `_PENDING_7SLOT_LEVELS`、`note_pending_7slots`、`back_prefix_for_level`);
- `cw_identity_obs.py`:`read_deployed_chars(level=)` + `_session_level`
  + `check_system_unit_layout`/`_sift_locate_x`;停机钩子语义适配;
- `currency_war_char_id.py`:`ransac_locate_x`(SIFT 单点定位,公开
  供自检用);
- `prep_director.py`:r414 域检查适配(level 驱动后 cap 只剩宝钻语义);
- `operations/prep/deploy_bench.py`:`_back_row_centers_by_level`
  (cap→level)、`exclude_system_units`、中环布局重建改 level;
- `recognizers/battle_prep_recognizer.py`:level 先读 + 后排装备选档
  + D-50 告警删除;
- yml:`battle_prep.yml` + `_od_merged.yml` 各删 37 个幻影 area;
- 测试:`test_cw_back_layout.py` 按新模型重写(旧 9/10/11 档识别锁
  回归为「同三帧按 8 格档识别」——新模型最强证据锁);旧锁变更清单
  见进度树;
- 采集待办:lv6 局备战帧(狸猫 x 实测 vs 1174/1316)定 7 格存在性。
