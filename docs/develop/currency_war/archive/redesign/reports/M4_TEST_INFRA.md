# M4 测试基建批报告

批前开工令:sr-od-currency-war-dev skill(测试分层行)+ 项目 AGENTS.md「测试规范」+ sr-od-test/README.md「测试纪律」(9 硬规则)已通读。
文件面:只动 `sr-od-test/`(测试仓)与 `sr-od-test/slow_marks.txt`,未碰 `src/`。
计时环境:2026-09-07,本机串行 `uv run pytest`,PYTHONPATH=src,OCR memo 缓存热。

---

## 第一项:cw_quick 全量对账补齐

**做法**:磁盘实际文件(`sr-od-test/test/sr_od/app/currency_war/` 递归 *.py,126 个)与 `cw_quick.txt` 登记(125 行)逐路径 diff。

**结果:零缺陷,登记完整,未改动清单。**

- 漏登:0;
- 多登/已删残留:0;
- 唯一 diff = `fixtures/regen_w546_count_ocr_fixture.py`(磁盘有、清单无)——这是 fixture **再生脚本**,非测试文件(无 `test_` 前缀,pytest 不收集,README 规定清单只列测试文件),不属登记范围,维持不登。

---

## 第二项:测试提速(慢桶重建 + 快速集验证)

**做法**(实测计时为准):
1. Run A(基线):quick 全量串行 `pytest @cw_quick.txt --durations=300 --durations-min=1.0` → **3128 条(5F/3118P/4S/1XP),437.56s**;
2. 按「整条用例 call+setup ≥2s」从 Run A durations 重建 `slow_marks.txt`;
3. Run B(验证):`pytest @cw_quick.txt -m "not slow"` → **3077 条(2F/3070P/4S/1XP),240.40s**。

**耗时对比:437.6s → 240.4s,降 45%(省 197s)。**

**等价性验证**:
- 差集 = 3128 − 3077 = **51 = 新慢桶条目数**,51 条全部被 conftest 后缀匹配命中跳过(无死条目);
- 失败集一致:全量 5 红 = 快速集 2 红(star_form/w614,非慢)+ equip_grant 画像带 1 条(在慢桶被跳过)+ package_layout 2 条(本批已修复,修后 Run A 复跑 3 绿)。无一条红/绿在两口径间漂移。

**慢桶名单变更**(52 → 51 条,文件头已记档):
- 新增 6 条(本批实测 ≥2s):`test_cw_prep_director.py::test_executor_h3_sphere_verified_only`(4.00s)、`test_cw_screens_entry.py::test_read_game_state_prep`(3.22s)、`test_cw_merge.py::test_read_shop_cards_fills_merge_preview`(2.66s)、`test_cw_prep_director.py::test_pause_panel_triggers_recovery_chain_to_lobby`(2.60s)、`test_cw_r331_fixture.py::test_observe_full_heavy_on_prep_fixture`(2.54s)、`test_cw_economy.py::test_delta_arm_fallback_routes_to_coarse`(2.24s);
- 删 7 条回落 <2s 的旧条目(如 `test_cw_star_form.py::test_p1_zero_drift_star_form` 现 1.89s);
- `__init__.py::test_rollover_with_foreign_open_handle[False]` 按 setup 计时准入(2.91s setup),保留。
- 注:任务书提「xdist 慢桶」——实际手段按 README 规范落地为慢桶过滤(串行口径为规范,`-n 8` 仅本机可选),xdist 未启用。

---

## 第三项:L3 五红残余核对(逐个定性)

先给总判据:**5 条全部串行确定性复现,无一条是并行批在飞的 flake 残留**。在飞(未提交)src diff 仅 4 文件且全是遥测加字段(`cw_performance.py` RoundOutcome 加 4 个默认值字段 / `cw_strategy_session.py` 加私有旗标 `_encounter_refresh_used` / match_archive、query 遥测),w614 行为投影只哈希账本 actions+gold+hp+level,加字段进不了投影——**在飞改动排除为红因**。红因均在已提交代码侧。

| # | 失败 | 复现 | 定性 | 处置 |
|---|---|---|---|---|
| 1 | `test_cw_package_layout.py::test_bucket_membership_complete` | 确定复现 | **登记门红(守卫正确抓到)**:包根新顶层文件 `cw_screen_state.py`(commit fdac8186 入库)未登记进 ROOT_FILES | **本批已修**:ROOT_FILES 登记 `'cw_screen_state': 'app'` 桶(模块 docstring:仿 sim_uni_screen_state 的运行态判定辅助,与 run_state 同类归属 app);修后该文件 3 测试全绿 |
| 2 | `test_cw_package_layout.py::test_package_root_layout` | 确定复现 | 同上(同一未登记文件的第二处锁) | 同上,已修 |
| 3 | `test_cw_star_form.py::test_calibration_anchor_r1_in_band` | 确定复现(seed 固定) | **真缺陷(锁红≠改动错)**:R1 锚综合胜率 14/35=0.40 越出校准带上界 0.285——W956 重锚(297d7eb4)之后落入的行为批(4cbfb64a 输入基线定稿改机制修改器 / a642d28c λ基座重建 PL 键主表等)改变了 sim 战斗结果,未随批重校此带 | 修正项进账本(M4残余:sim行为批欠重锚三锁):按 w910 先例 bisect 定位首个位移 commit 再重校;禁机械跟绿 |
| 4 | `test_cw_w614_sim_fidelity.py::TestZeroDriftAnchor::test_default_path_behavior_digest_unchanged` | 确定复现 | **真缺陷(行为位移哨兵在报)**:digest 297d7eb4→1d3b6c29,默认路径 P1 行为已位移,而锚注释末次重锚停在 W956 批——之后 ≥2 个已提交行为批未随批重锚(该测试注释自身要求「后续行为批重锚须按 w910 先例补单变量 bisect 或同款如实声明」,欠账) | 同上修正项:归因后重锚;锚的位移量与方向需策略侧判读(是预期改进还是回归),非测试基建批可裁 |
| 5 | `test_cw_equip_grant_calib.py::test_p1_grant_volume_matches_real_profile` | 确定复现(seed=17) | **真缺陷(画像带下界击穿)**:seed=17 局终装备保有 1 件 < 下界 2(偏 −50%,超 ±20% 容差)——同窗口行为批的供给/合成取舍变化所致 | 同上修正项:重校画像带前先判 seed=17 的行为链(供给节点数是否被策略改少),必要时换样本口径 |

**账本登记**:`决策/进度.md` M4 行已过 + 新增顶层行「M4残余:sim行为批欠重锚三锁」(未做,bisect→重锚/重校),check 通过。

---

## 改动文件清单

- `sr-od-test/slow_marks.txt`(重建,52→51 条,文件头记重建依据)
- `sr-od-test/test/sr_od/app/currency_war/test_cw_package_layout.py`(ROOT_FILES 登记 cw_screen_state)
- `.debug/progress/2026-08-31-currency-war-redesign/决策/进度.md`(M4 行+修正项,progress.py write + 直改提级 + check OK)
- 本报告

未动:`src/` 全部(含在飞 M2 改动,原样保留)、`cw_quick.txt`(对账零差,无需改)。
