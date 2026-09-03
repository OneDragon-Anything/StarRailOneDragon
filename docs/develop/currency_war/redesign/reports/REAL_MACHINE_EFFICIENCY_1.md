# 货币战争实机效率 + C4 补采准备批(2026-09-01)

依据:`REAL_MACHINE_COLLECTION_1.md`「跑局批」节(效率发现 + 败局链缺口 + 难度读数位)。
本批全部为**等待参数压缩 + 临时采集钩子补分支 + 画面建档**,零决策代码改动。

## 任务1:结算动画/强敌来袭「点击空白加速」效率优化(完成)

### 先澄清一个事实

跑局批报告 ⑥ 称「点击空白加速 未使用」——**代码核查不成立**:battle_loop 分支 2
(OCR「点击空白加速」/「点击空白处继续」→ 点 BLANK)一直存在且实局生效(h_ 成对帧
2s 间隔 = 分支 2 一轮迭代即翻页,报告自己的语料可证)。真实的浪费不在「没点」,
而在**点完之后的等待参数偏保守**:每次点空白后 round_wait(1.5),加上 loop 整轮
分支链重识别开销,页1 动画 + 横幅 + 统计页每页都多等 ~0.5-1s。

### 改动(battle_loop.py,全部只动 wait 数值 + 注释)

| 位置 | 改动 | 理由(注释已写入代码) |
|---|---|---|
| 分支 2(点空白加速/处继续) | wait 1.5 → **0.8** | 点空白 = 跳过页1 动画/强敌横幅/位面过渡,游戏 ~1s 内翻到下一静态页;点空白幂等,短 wait 只让 loop 早一轮识别下一页 |
| 分支 3(继续挑战,成功+未生效两路) | wait 1.5 → **1.0** | 半开帧防护主防线 = 备战双锚 + PREP_SETTLE_S 3s 稳定门 + 0e 分支前置(沿用 w781 已论证口径);未生效路径早重试 = 早触发长按兜底 |
| 分支 6(总伤害/数据统计点空白) | wait 1.5 → **1.0** | 与分支 2 同语义,静态统计页早一轮重识别无风险 |

- 预期收益:每场战斗结算链(页1 + 横幅 + 页2 + 统计页)省 ~1.5-2.5s,每局 ~9 场
  合计 **~15-20s/局**(跑局批报告估 ~30s 是按「未点空白」的误判口径;实际点是点了的,
  本批压掉的是等待残余)。下批实局用 [cw-loop][battle_end] → 备战相位进入日志时差验证。
- 未动:PREP_SETTLE_S 稳定门(3.0s)——属「锚定/稳定解耦」待批件,见下。

## 任务2:败局链采集钩子(完成,临时件)

缺口:局3 的 2-3/2-4 败局结算与「挑战失败」终局链全程零 h_ 帧——钩子原只挂分支 2/3,
失败链不走这两个分支。补两处(同 settle_collect_hooks.py,同款 best-effort + 封顶 400 帧):

1. **分支 1f**(败方单场结算页:挑战进度 + 挑战结束):进入分支即采一帧(在
   `_record_loss_page` 前)——覆盖每场输轮的结算页;
2. **分支 3b**(终局结算链:前往结算/下一页/下一步/返回货币战争):每页点
   SETTLEMENT_NEXT 前采一帧——覆盖团灭后「挑战失败」多页链(C4 战败布局主缺口)。

- settle_collect_hooks.py docstring 已同步调用点清单;
- 生命周期不变:采集完成(结论进 redesign 报告)后与本钩子族一起删整段
  (文件 + 4 处接线);
- 验证方式:下一局若有败局/团灭,window_batch 出现新 h_ 帧且时刻落在败局日志窗口内。

## 任务3:难度读数 OCR 区建档(完成)

- 位置:备战屏左上星徽晋级徽章下方数字,中心约 (135,83);
- 视觉核验(3 张样本帧,glm-5.3-flash 直读):读数 108 / 108 / 114,裸数字 bbox
  三张一致 [117,73,153,94],加余量后取 **[107,63,166,104]**(容纳 2~3 位数字);
- 先读该屏现有 yml(65 个 area)确认无重名/无同位重复——已有 `文本-难度`
  [116,28,156,113](含徽章,偏高)与 `按钮-敌人难度` [95,20,180,120](点击区),
  均非纯数字 OCR 区;新增 area **`难度读数`**(空 text,定位区)经 MCP
  upsert_screen_area 建档,area_count 65→66;
- 注意:全屏 OCR 在 3 张样本上均**读不到**该数字(小字号+底纹),运行时读数需
  区域裁剪 OCR(框架 round_by_ocr_area / reader 走本 area rect)——这是 λ 表钥匙
  真值源的读法前提,下批实机验证区域 OCR 命中率;
- 采集缺口维持:位面 2/3 难度值未采,下批位面过渡后首备战补采。

## 任务4:代码类待批清单(本批不做,涉及面大单独批)

1. **稳定门解耦(锚定/稳定分离)**:备战子态稳定门 PREP_SETTLE_S=3.0s 每次备战相位
   固定等 3s 才派 PrepDirector,开店链同理 ~13s/次 → 指纹-only 稳定确认可提前放行,
   预计省 ~29s/局(上一批 screen_flow_timing.md 优化候选节)。涉及识别 gate 体系
   (cw_observation_gate / prep_director),需单独设计 + 测试,非纯参数。
2. **录屏通道修复**:record_screen start 假成功 / fixed 失败 / 文件不落盘(连续两批
   实证)。修好后才能做手动逐环节测量;替代方案 = 密集截屏环(本批前已用 2s/张 外环)。

## 任务5:验证

- ruff:`battle_loop.py` + `settle_collect_hooks.py` All checks passed;
- 测试:直接受影响集 5 文件 249 passed(test_cw_telemetry_collect / test_cw_round_flow /
  test_cw_all_ops_importable / test_stall_watchdog / test_cw_obs_gates);
- screen_info 无 area 数量类测试锁,新 area 无波及;
- MCP server 已重启(PID 47816,重启时 idle 无对局,不触 r99 守卫),钩子新分支 +
  wait 改动 + 新 area 下一局生效。

## 改动文件清单

- `src/sr_od/application/currency_war/operations/battle_loop.py`:3 处 wait 压缩 +
  2 处采集钩子接线(临时);
- `src/sr_od/application/currency_war/operations/settle_collect_hooks.py`:docstring
  调用点同步(临时件,随钩子族删);
- `assets/game_data/screen_info/currency_war_battle_prep.yml`(经 MCP upsert):新增
  area `难度读数` [107,63,166,104]。
