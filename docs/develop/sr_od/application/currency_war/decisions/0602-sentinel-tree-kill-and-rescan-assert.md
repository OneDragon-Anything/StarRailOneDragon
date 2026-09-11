# ADR-0602: 哨兵杀净=树终杀+杀后复扫断言,cycle_restart 两消费点收口(T-132 微批;2026-09-08 哨兵武装链断事故的决策 why)

- **Status**: 已实施(方案审裁决形态放行+落地审需修 F1/F2/F5 已修;commit 候编排者统一门;「复扫零残留」实弹验收挂进度账本 T-132 待验行)
- **Date**: 2026-09-08(事故、方案审、实施、落地审同日;本 ADR 随落地审修正批补立)
- **关联**: ADR-0586(遥测根切换——cycle_restart 哨兵寻址单一源迁 rewatch 的同链前件)、`skills/sr-od-currency-war-dev/references/runtime-ops.md`「哨兵脚本组」(实机运维单一源,纪律行「杀哨兵只许经 rewatch;任何信道停后必复扫」决策 why 在本文)、`references/autonomous-loop.md` §3(报警消费协议第④步补位硬收尾=本决策的纯口径配套件)
- **原始材料**: 方案审与落地审原文在 `.debug/temp/currency_war/attacks/t132_sentinel_chain/`(不入 git,易失);本文为其决策内容的持久收编,两者冲突时以本文为准。

## 1. 背景与决策 why

2026-09-08 晚事故实录四条(方案审输入):

1. 手工 `Stop-Process` 杀哨兵,只杀掉 pwsh 包装——Windows 进程杀不级联,uv→venv python→base python 三层孤儿照常存活(哨兵实为四层进程链 pwsh→uv→venv python→base python,活体扫描每脚本 4 pid,当时每层命令行都含脚本名)。
2. 孤儿占 `cw_runs_gap` 守卫锁:锁检查验 pid 活性+cmdline 含脚本名即判「在岗」拒绝新实例——哑孤儿被当在岗,下一轮武装被拒。
3. 报警链断成哑哨兵:进程在,但退出码(=警报)已无接收方。
4. 事件哨兵 HIT 退出后 70 分钟无人补位,节点滞留零报警(第五缺口,见 §4 纯口径件)。

关键定性:**这不是 rewatch 能力缺口,是杀净步骤绕开了工具**(当晚四层全命中命令行匹配,走 rewatch 缺省形态本可杀净);且单点杀不止手工——已提交代码内 cycle_restart 就有两处(§3)。同族事故第四次:重武三步早已在 runtime-ops 明文,仍被跳过——纪律只写不做不够,必须把「人忘了」变成「命令报红」。

## 2. 决策本体(rewatch 杀净出口)

- **树终杀**(`collect_tree`):每个匹配进程经 psutil `children(recursive=True)` 把全部后代收进杀集(按 pid 去重,排除自身)。为什么:今天四层命令行都含脚本名、命令行匹配够用,明天 uv 改实现未必——后代命令行不含脚本名/不可读时按命令行抓不到,树语义保证链上进程不孤儿化。psutil 单机制,不引 taskkill/CIM 第二套。边界(如实申报):祖先方向不收编,只杀向下——今天祖先层同样全命中;杀父后 children 遍历本就走不到祖先。
- **杀后复扫断言**(`kill_all`):每轮杀完重跑 `find_old_watchers`,与杀集幸存者按 pid 去重合并(`_merge_procs`,防同进程双计);非空自动再杀,`KILL_RESCAN_MAX=3` 轮(1 轮主杀+至多 2 轮复扫再杀)有界重试,不做无限兜圈;仍非空 `exit 2` 可验证失败。**停净双判据**(落地审 F1 修正):成功行=「[杀净] …复扫零残留 ✅」;他信道已停净=「[杀净] 无需杀(本来就干净)」——二者之一即停净;「[复扫]」前缀行只在重试轮与最终失败出现,不作停净判据(runtime-ops L63 原措辞只认「复扫零残留」,在已停净场景不可达,会死等)。
- **AccessDenied 归宿**(`_kill_procs`,落地审 F2):Windows TerminateProcess 是原子的——目标死了,或抛 `AccessDenied`(需管理员),不存在「不抛异常但不死」的中间态。kill 抑制 NoSuchProcess+AccessDenied,杀不动=视作存活返回,交复扫轮有界重试,最终 exit 2。不抑制会让真实「需管理员权限」场景变成未处理异常(traceback 退 1),绕过 exit 2 契约,消费方(编排者后台 job / cycle_restart)拿到契约外退出码。

## 3. cycle_restart 两消费点收口

单点杀不止手工 Stop-Process——已提交代码内就有两处:`supervise()` 兄弟终止与 `start_app` 失败回滚都用 `Popen.terminate()`。kid 是 uv 层进程,Windows 下 TerminateProcess 不级联,只杀 uv 层会孤儿化 venv python→base python 链——即:**只要某件哨兵报警,cycle_restart 自己就会制造阻塞下一轮武装的孤儿**,复刻 §1 全链。

修法:rewatch 实现树终杀复用缝 `kill_pids_tree(pids)`(目标+树收编后代一并杀,返回杀后仍存活的杀集 pid,目标已死幂等返回空),两消费点复用同一实现——杀语义单一源,禁在消费点自造第二套树杀。杀净失败随 rewatch 透传 2,归 cycle_restart main 退出码契约「参数/前置失败」桶(fail-safe:中止而不带孤儿武装新哨兵);消费点树杀后仍有存活 pid 时打警告行指引跑 rewatch 复扫。

## 4. 否决面与已知局限(Considered Options)

否决:

- **rewatch 加 `--kill-all` 旗标**:缺省路径本就是查旧→杀净,旗标与缺省行为重名,零行为增益,还暗示「缺省不杀净」的错误心智模型(方案审 F5)。直接强化缺省 `kill_all`。
- **守卫侧修**(`cw_runs_gap` 锁检查识别哑孤儿):报警信道是否还被接收,不可从进程表检测,做了也是猜;治本在杀净侧让孤儿不存在(方案审 F2)。守卫语义维持现状即正确。
- **仅运行手册补单行**:重武三步早已明文仍被跳过(同族第四次),纯纪律拦不住「人忘了」;复扫断言把遗忘变报红,手册行与断言两者都要、不二选一。
- **taskkill/CIM 第二杀机制**:psutil 已是 rewatch 既有依赖,树遍历 `children()` 即可,单机制原则。

已知局限(申报不修):

- **verify 按名计件**:同名双实例仍计 1 件,`exit 0` 检不出实例堆积(打印的 pid 列表供人眼核对;runtime-ops L62「每脚本恰 1」的核查靠人)。
- **verify cmdline 命中即在岗**:哑孤儿(报警信道已断的残留进程)照样绿,`exit 0` ≠ 报警信道活;活性回读以 `cw_sentinel.pos` 心跳推进 / 后台 job 结算为准(runtime-ops「哨兵活性回读」行)。(落地审 F4)
- **第五缺口纯口径收口**:哨兵退出→补位之间无自动化防线,本批以零代码收口——autonomous-loop §3 报警消费协议补第④步「消费完毕→按重武三步补位硬收尾(补位完成前显式声明接受降级监控)」+§2 实机监控模板存活问句落成 `rewatch --verify N` 机械命令。自动化补位(编排者协议层)归后续批另议。

## 5. 验收设计(测试锁 `sr-od-test/test/sr_od/app/currency_war/test_cw_rewatch_tree_kill.py`)

三行为锁(monkeypatch 伪进程树+psutil 桩命名空间,零真实进程、零真实 .debug 写;档壳桩是「杀→复扫」循环的机制锁,非 Windows 杀语义映射——TerminateProcess 原子,真实「杀不动」由 AccessDenied 桩建模):

1. **树递归**:无名后代(cmdline 不含脚本名)进杀集且被杀;
2. **杀后复扫**:只有复扫可见的漏网哨兵被自动再杀(kill 调用数 > 单轮上限 2 为凭)+「复扫零残留」契约行;轮数耗尽仍非空 `exit 2`;
3. **--selftest 零杀**。

附加:kill_pids_tree 复用缝语义+已死 pid 幂等;supervise 行为锁(兄弟只经缝终止、首个退出者退出码透传);消费点源码锁(`rw.kill_pids_tree(` 恰 2 处 / `.terminate()` 绝迹 / cycle_restart 禁自引 psutil);AccessDenied 桩 case(归 exit 2 契约,不 traceback——落地审 F2)。

- **变异验证**:复扫断言移除 → `test_rescan_catches_straggler_and_kills_again` 红(且变异代码仍打印契约行,证明锁的是断言本体而非输出文案)。
- **实弹**:不专设演练(真哨兵在岗造同名诱饵会污染核岗与守卫锁),随下次局间交接自然验收,判据=杀净输出「复扫零残留 ✅」+`--verify 3` 过;验收结果回写进度账本 T-132 待验行(落地审 F6)。

## 6. 出处指针表(代码注释 → 本文)

注释中的「T-132 方案审」易失索引(T-132 是进度账本局部 id,方案审文件不入 git)已全量改指本文 § 号,语义描述保留:

| 注释主题 | 文件 | 指针 |
|---|---|---|
| collect_tree 树收编 why | tools/cw/rewatch.py | §2 |
| _kill_procs AccessDenied 归宿 | tools/cw/rewatch.py | §2 |
| kill_all 出口契约/停净双判据 | tools/cw/rewatch.py | §2 |
| kill_pids_tree 复用缝 | tools/cw/rewatch.py | §3 |
| verify 已知局限申报 | tools/cw/rewatch.py | §4 |
| kill_watchers 停净判据+透传 | tools/cw/cycle_restart.py | §2/§3 |
| supervise 树终杀注 | tools/cw/cycle_restart.py | §3 |
| start_app 回滚树终杀注 | tools/cw/cycle_restart.py | §3 |
| main docstring 退出码契约(杀净失败透传 2) | tools/cw/cycle_restart.py | §3 |
| 测试锁 docstring/机制锁声明/出处 | test_cw_rewatch_tree_kill.py | §2/§5 |
| runtime-ops 纪律行「决策 why=ADR-0602」 | runtime-ops.md | 全文 |
