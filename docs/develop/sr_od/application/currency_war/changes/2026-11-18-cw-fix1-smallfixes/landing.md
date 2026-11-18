# CW 动作 op 小修批(fix-1)落地记录

> 迭代设计 = 同目录 [design.md](design.md)(commit 18d8883e0);本文件记录实施落点与待实机复核项。

## 1. 逐件落点

### 1.1 件 3:DragCwChar 类 docstring 按 §9 三要素补齐

- 主仓 commit:`ae92e34bd`(纯注释零逻辑,1 文件 +21/-11)。
- 文件清单:`src/sr_od/application/currency_war/operations/actions/drag_cw_char.py`——类 docstring 补槽位坐标系三要素(1 基画面物理槽位 / screen_info area 序号 / 取值时机)+ extras 0 基换算 + 与 `CwActionMoveUnitOp` 基差异双向声明;`__init__` Args 块删除防双源(对照模板 `CwSellBenchBySlot` 同款);`back_centers` 转换处补 0 基↔1 基行内注释。
- 验证:`ruff check` 通过;CW 域全量 157 条全绿(零行为漂移);describe 反射探针实证 `:param` 段三要素透出(from_idx 1 基 / extras 下标+1 换算 / CwActionMoveUnitOp 基差异 / back_centers 全在 docstring)。

### 1.2 件 2:采集族装入口画面锚 + actions 包读屏契约修订

- 主仓 commit:`ce0e43aa5`(3 文件 +31/-10);测试仓 commit:`b578f976`(新测试 168 行)。
- 文件清单:
  - `src/sr_od/application/currency_war/operations/actions/cw_collect_reward_ores.py`——入口节点头部晶矿识别前装入 口画面锚(窄判定只认备战;错屏二次识别取真名显式 fail 带「未识别」兜底);docstring 删「无商店展开守卫」整段换锚语义(判「我在哪屏」不判「点完生效没」)。
  - `src/sr_od/application/currency_war/operations/actions/__init__.py`——读屏纪律第三条整段替换为「读屏受限」双合法面(①动作本体目标定位 ②入口画面锚),原「不做画面状态判断、不设前置守卫」口径错误短语删除。
  - `src/sr_od/application/currency_war/operations/cw_op/cw_collect_ore_action.py`——类 docstring 前置声明锚归属(锚归画面 op 观察侧,错屏防线 = cw_screen_prep 入口判定 + 下一帧观察对账);零逻辑。
- 设计检查点处置(m5 二次识别时序):实码核验 = 无名单 `get_match_screen_name` 在 current/last 均空时走 else 分支直扫全部活跃画面档(screen_utils.py else 分支),有残留时 BFS + 末段兜底扫描仍覆盖全量(L546-553)——`check_and_update_current_screen(screen)` 单调用已满足「报错能对上实际画面」,无需额外直扫兜底;两条错屏 fixture 用例实证真名透出。
- 验证:新测试 6 条全绿(错屏 fail 带真名「货币战争-备战-开商店」/「货币战争-备战-开拓商店」、零点击;备战拾取回归 4 球帧逐球点击 / max_clicks 截断 / 空读 success 保留;参数越界 ValueError);CW 域回归全绿(见 §2 现场说明);`grep 不设前置守卫` 全库零残留。
- 测试守卫判别力依据(m3)已承载于测试模块 docstring(备战 id_mark「标识-前台区域」矩形在两商店浮层帧下被浮层内容覆盖 → 不全中 → 备战不命中;浮层改版致判别失效时该用例先红)。

### 1.3 件 1:CwToggleShopPanel 扩参数面支持开拓商店

- 主仓 commit:本 landing.md 入库提交(随件 1 一并);测试仓 commit:`be0c9e55`(新测试 188 行)。
- 文件清单:
  - `assets/game_data/screen_info/currency_war_battle_prep_pioneer_shop.yml`——经 MCP `upsert_screen_area` 增「标识-银轨商店徽记」area(五要素与备战档逐字段同构:rect [230,220,310,580] / template currency_war:cw_rail_shop_badge / 阈值 0.7 / 非 id_mark;`goto_list: [货币战争-备战]` 补反向导航边)。
  - `src/sr_od/application/currency_war/kernel/cw_obs_core.py`——增 `PIONEER_SHOP_SCREEN_NAME` 常量。
  - `src/sr_od/application/currency_war/operations/actions/cw_toggle_shop_panel.py`——参数面三值 + 节点内分画面取控件(备战/开商店静态中心零变化;开拓商店直调 `screen_utils.find_and_click_area` 带内模板命中位直点,miss 显式 fail 零引擎重试带可操作提示;AREA_NO_CONFIG / 点击失败各有显式 status)+ 类 docstring 三值口径与 miss 出口描述。
  - `skills/sr-od-currency-war/references/screens/货币战争-备战-开拓商店.md`——第 5 步收店口径 1 行(文档承诺 − op 能力缺口闭合)。
- 设计检查点处置(i2 max_clicks 类边缘项):件 1 无此项;件 2 测试点 3(参数校验)按审查 i2 口径保留(文件新建锁契约完整面,成本近零)。
- 验证:新测试 7 条全绿(开拓商店构造成功 / 非法值 ValueError 带可用值列表 / 备战·开商店静态中心回归 / 命中分支恰一次点击坐标 = fixture 真值 (267,262) 非带中心 / miss 分支显式 fail 零点击零引擎重试(轮数计数实证)/ describe 反射面透出三值与 miss 出口);CW 域回归全绿(同 §2)。
- fixture 真值标注:开拓商店帧 `商店展开.webp` 徽记中心 (267,262)——离线探针(与画面档 area 同构 crop_and_match_template @0.7)score 0.974 读出 + 人工看图复核金菱形徽记居中;测试内未复刻被测逻辑现算期望。

## 2. 测试现场说明(并行批在飞干扰)

CW 域全量回归期,并行批(2026-11-18-prep-special-flow)对 `cw_screen_prep.py` 等的在飞改动使 `test_prep_special_flow.py` 两条用例红(锁定出战/收店探针域,非本批文件与调用链;隔离复跑 + 改动时间线归因确认)。本批回归口径 = 排除该两条后全绿(件 2 时 163 passed / 件 1 时 170 passed,2 deselected);该域全绿由并行批自己收口。

## 3. 待实机复核项(随下次实机棒顺带,禁碰活窗纪律)

1. **开拓态徽记带位**:建档带 [230,220,310,580] 系备战态实测迁移,设计留「以实机为准」回填口径——重点核对带下缘 580 与徽记 y 浮动上限(实测 y=515 + 模板 49px ≈ 564)余量约 16px 是否够;不符以实机回填开拓档 pc_rect。
2. **模板 `cw_rail_shop_badge` 开拓态命中**:识别器三态分离度标定覆盖「面板开启态」,开拓态视觉变体(如高亮态)未单独取证——实机单跑 `CwToggleShopPanel {"screen_name":"货币战争-备战-开拓商店"}` 验证命中与落点。
3. **件 2 错屏守卫实机面**:实机 MCP 直调 `CwCollectRewardOres` 错屏场景(如商店开着)确认 fail status 报真名;fixture 已实证,实机复核 = 帧域一致性的最后确认。
4. **验收三连的 run_operation 单跑**:全部待实机(本批实施期零游戏窗口操作,list/describe 反射面已离线核过)。
