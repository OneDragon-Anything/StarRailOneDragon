"""批统计面(四指标):①P1 出口金 ②过渡凑齐率(P1 出口) ③终局金 ④终局阵容完成率,外加 [28] 线读数一行。

定位:sim-testing「找问题」三步的第 1 步统计(每局每指标都有值,怎么判定
「表现不好」不在此规定)。用户规格(2026-09-08):旧九族过程量指标全部删除,
只保留四个指标 + [28] 线读数——其余指标可从这四个推理。

四指标口径(数据可得性已在真实档案核对:2026-09-08 第四跑批 findprob_cal4 /
findprob_cal4p 的 P1-only sim 载体 + 生产档案;两源统一行 =
row{plane, round, node_type, gold, hp, form, form_ok, level, locked_comp,
p1_pair, state_board_factions/state_deployed(sim 行轮末快照)},
同轮多决策帧时保留最末帧——sim 末轮清算连帧即得清算后残金):
- ① P1 出口金 = 每局 plane==1 末行的 gold(行 gold = 决策帧快照,轮结算后值)。
  未通关局的出口金照读,P1通关? 列单独标。
  边界:sim 决策帧 = 决策时点快照,末帧之后仍有动作的局行源金轻微高估局终金
  (cal4p 实测:行源中位 47.5 vs 引擎局账 39;HEAD 腿两源一致 = 5.0)。
- ② 过渡凑齐率 = ① 同行凑齐判定。判定口径 = 行内 state 轮末快照现算
  readiness 判据(单一源 = kernel/cw_launch_admission
  ``readiness_form_ok_from_snapshot``;判据核 form_progress 鸭型桩契约
  消费 board_factions/deployed 两键):决策行 ``form_ok`` 字段是策略器
  镜像写端(write_shop_mirrors)在商店决策帧时点的读数,与同行 state
  (引擎轮末值)不同时点——轮内升级解锁席位后补位达标的局镜像恒 False,
  凑齐率被低估(2026-09-15 批 4/300 实证),故轮末快照可算时一律现算;
  快照缺输入(生产档案行/旧批行)回退 form_ok 镜像读数(不虚构)。
  form 原值(b_t 优先/form_score 回退,退役只读)逐局展示。批级 =
  通关局中凑齐真占比;通关局 = 0 的批(P1-only sim 载体)如实披露
  不适用,禁折 0。
- ③ 终局金 = 每局最后一条行的 gold。
- ④ 终局阵容完成率 = 末行 locked_comp 非空时按②同款行凑齐判定(1/0);
  locked_comp 空 = 未锁线 = 0(用户规格逐字)。批级 = ④=1 局占比,
  分母 = 可判局。口径分叉:sim 行 locked_comp 缺键/空串 = 未锁线
  (引擎未建锁线态 = 没锁);档案行结构性无 v3_intention 键 = 无数据,
  不入分母(「无数据」与「未锁线」两种事实,混同会把档案伪影当行为信号)。
  **P1 配方对代理键(观测面专用,局表 p 标)**:locked_comp 空而同行
  v3_intention.p1_pair 非空 = P1 配方锁活跃帧(:配方锁局
  locked_comp 恒空,引擎语义零改,本脚本只读遥测)——锁定目标代理 =
  配方对,④ 改按②同款判定并标 p。语义依据:P1 配方锁的锁定目标 =
  配方对(kernel/cw_intention.pair_target_comp 物化伪 comp),凑齐判定
  = 行内轮末快照对该伪 comp 现算 readiness(回退 form_ok 镜像),⟺
  终局板面完成配方锁方向 = ④ 问题的 P1 等价问法。动机:P1-only 载体
  下不加代理则 ④ 结构性恒 0 = 指标-载体错配。边界:配方对空窗帧
  (p1_pair 空)仍按未锁线 = 0;①资格锁局 locked_comp 非空走既有
  判定分支,代理不辖;P2+ 帧 p1_pair 恒空(IntentionState 字段契约),
  代理结构性不可达。

P1 通关判定(按优先级):行面存在 plane>=2 行 → 行面证据;否则局级权威源
(sim = runs.jsonl 的 plane_reached;档案 = endgame.plane_reached)≥2 → 行面
证据;两源都缺 → 行面规则收尾:无 plane>=2 行 = 无行面证据。**死亡筛
(T-169 统计口径增补,2026-09-09)**:行面证据达 2 后还须末行 hp>0——死在
P2 段的局(末行 hp=0)行面不存活。hp 缺读(行无 hp 键)局死亡筛不适用 =
保持 plane 证据判定(边界如实申报:该类局死亡状态不可判,不折 0 不折 1)。
**killed 消费(通关权威口径,件3)**:通关 = 行面存活 ∧ 局末行
outcomes killed==True。killed = 结算屏「玩家击败对手」,是行面证据之外的
唯一权威胜负口径——「活满末轮」与「杀穿 boss」两种结局在行面同形,
只看行面会把前者整批误判为通关,通关率系统性虚高(全载体批实测为
真值的数倍,读数以 killed 列为准)。局末行 killed 不可判(outcomes
缺局 / sim 键缺 / None,旧批无该字段同此)→ 未知桶:不入通关
(禁默认通关),报告头按局数显影;不回退取早轮行——早轮 True 只证该轮
胜,不证终局杀穿。档案侧合成轮同律:补给节点的 outcome 是采集端合成
填充,killed=true 非战斗结算,不承载真值(合成轮恰为末轮 → 整局未知
桶,证据档案见 _archive_rows 注)。输出双列披露:通关率(killed 真值,
权威)+ 通关率(行面口径,旧列兼容——无 killed 数据的历史批/档案唯一
可算口径);逐局表「行/killed」双标记同义。**权威源降级通道(T-169 落地审 F7)**:
新批布局(2026-09-07)不落 runs.jsonl——runs.jsonl 缺失时改读
outcomes.jsonl 逐局 max(plane) 作局级权威源(同语义);runs 值优先不覆盖。
载体验证(2026-09-09 增补):模拟常开批须 --planes 2 才有 P2 观测
(planes=1 段表只含 P1 九轮,P2 面零观测)。
载体标识:批统计头行自动标注载体类型
(全载体 = 生产档案或存在 plane>=2 行的 sim 批;P1-only = 零 plane>=2 行
的 sim 批——其通关率 0 是载体辖域结果,禁当行为信号,与下行边界同义)。

出口生存余量读数行(T-169 账本 23:49 增补/落地审 F3 补交付;读数非门):
P1 出口行(= ① 同行源)hp 分布 min/中位/max + 死亡地板命中数(sim 地板 0,
出口 hp<=0 = 死在出口帧)——与死亡筛同源不同问:筛答「算不算通关」,
本行答「出口时还剩多少血」;hp 缺读局不入分布,可读数随行披露。

boss 结算敏感性边界披露(sim 源头行固定披露):boss 战损 Δ 采样键 =
净星深一维(迁移审计 w240),不含 rung(成型度)维——「同净星深、
不同成型度」的 boss 战损差异在 sim 内不可分辨(无敏感性边界可读)。升维
rung×净星深二维列是后续候选(T-169 增补项 ②,本批只披露不升维);判读
boss 段读数(如 hp 轨迹尾段)时按此键边界理解。

[28] 线读数 = P1 出口金 ≥50 的局数,一行,不做门只做读数——[28] 双指标验收
明确「出口金单独不作验收」(单指标优化会复刻「金 92 过线但板面弱」的假达标);
出处 = docs/game/currency_war/research/user_playstyle.md 的 [28] 条
(50 金息律簇,P1 验收框架:息基保住 × P1 形态达标)。

数据源与用法(项目根运行;另机/异目录语料用 --sim-root/--matches-root 显式指路):
    uv run python skills/sr-od-currency-war-dev/scripts/cw_batch_stats.py --sim-batch latest
    (latest 口径 = 批目录名内嵌创建时间戳最新的含账批次,非字典序/非 mtime)
    uv run python skills/sr-od-currency-war-dev/scripts/cw_batch_stats.py --batch <批次目录>
    uv run python skills/sr-od-currency-war-dev/scripts/cw_batch_stats.py --recent 10
    uv run python skills/sr-od-currency-war-dev/scripts/cw_batch_stats.py --match <game_id>
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

# src 判据引导(②④轮末现算的判据单一源 = kernel readiness 快照读口):
# 自脚本位反推仓库 src 加入 sys.path,项目根直跑零前置;导入失败(异机
# 裸语料/非仓布局)= 判据复用不可用,②④回退 form_ok 镜像读数(回退态
# stderr 显影一行,统计仍可算,读数口径降级如实申报)。
_REPO_SRC = Path(__file__).resolve().parents[3] / 'src'
if _REPO_SRC.is_dir() and str(_REPO_SRC) not in sys.path:
    sys.path.insert(0, str(_REPO_SRC))
try:
    from sr_od.application.currency_war.kernel.cw_launch_admission import (
        readiness_form_ok_from_snapshot,
    )
except ImportError:   # pragma: no cover — 零 src 环境回退分支
    readiness_form_ok_from_snapshot = None
    print('[cw-batch-stats] src 判据不可用,②④回退 form_ok 镜像读数'
          '(轮末现算停用)', file=sys.stderr)

# 落盘根(2026-09-07 布局裁定,.debug/currency_war/telemetry/{live,matches,sim};
# 单一源 = src kernel/cw_observe 根常量块,数据面按同值独立声明——src 可用
# 时判据面走 kernel 快照读口,数据布局常量维持本地声明不随 src 缺失失效)
SIM_ROOT = Path('.debug/currency_war/telemetry/sim')
MATCHES = Path('.debug/currency_war/telemetry/matches')

# 批目录名内嵌创建戳形状(YYYYMMDD_HHMMSS;runner 毫秒批为 15 字符前缀)
_SIM_STAMP_RE = re.compile(r'\d{8}_\d{6}')


def _latest_sim_batch(root: Path) -> Path:
    """``--sim-batch latest`` 的最新批选取(口径:批名内嵌创建时间戳)。

    批目录名内嵌 ``YYYYMMDD_HHMMSS`` 创建戳是落盘命名自带事实(单一源 =
    sim/runner._default_sim_runs_dir 与 sim/cw_sim_piggy 的 stamp 段),
    取最大 = 最近开批的统计批。弃两候选口径的理由:
    - 名字典序:sim_piggy_*(p>数字)压过全部日期批,会命中探针小批
      而非最新统计批(sim_piggy_super_20260912… 实证);
    - 目录 mtime:批目录会被批外后写触碰(2026-09-10 六批目录 mtime
      全同实证),顺序失真。
    无时间戳目录(freeze_* 等池目录)与缺 decisions.jsonl 的目录不入
    候选;同秒并列按名字典序取大(runner 毫秒段已使同秒碰撞趋零)。
    """
    def _key(d: Path) -> tuple[str, str]:
        m = _SIM_STAMP_RE.search(d.name)
        return (m.group(0) if m else '', d.name)

    cands = [d for d in root.iterdir() if d.is_dir()
             and (d / 'decisions.jsonl').is_file()]
    if not cands:
        raise SystemExit(f'批根下无可统计批次(缺 decisions.jsonl):{root}')
    return max(cands, key=_key)


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in open(path, encoding='utf-8') if line.strip()]


# ---------- 数据装配:统一成 row{plane,round,node_type,gold,hp,form,form_ok,level,locked_comp} ----------

def _game_shell() -> dict:
    return {'rows': [], 'plane_reached': None, 'killed': None}


def _sim_rows(batch: Path) -> dict[str, dict]:
    dec = _load(batch / 'decisions.jsonl')
    outs = _load(batch / 'outcomes.jsonl')
    games: dict[str, dict] = {}

    def g(rid: str) -> dict:
        return games.setdefault(rid, _game_shell())

    for o in _load(batch / 'runs.jsonl'):
        # 局级权威源:P1 通关判定用(引擎自记 plane_reached;旧批布局)
        g(o.get('run_id') or '?')['plane_reached'] = o.get('plane_reached')
    for r in dec:
        st = r.get('state') or {}
        key = (r.get('plane') or 1, r.get('round_num') or 0)
        # 同轮多决策帧全保留,按 (plane, round) 排序;指标只读各辖域末行
        # (①=plane==1 末行,③=全局末行),末轮清算连帧时末帧 gold
        # 即清算后残金(取值语义见模块 docstring)
        g(r.get('run_id') or '?')['rows'].append({
            '_key': key,
            'plane': key[0], 'round': key[1], 'node_type': None,
            'gold': r.get('gold'), 'hp': r.get('hp'),
            'form': r.get('b_t', r.get('form_score')),  # b_t 优先(新数据),form_score 回退读历史(退役只读)
            'form_ok': r.get('form_ok'),
            'level': st.get('level'),
            # 锁线字段(单一源 = v3_intention.locked_comp;缺键/空串 = 未锁线)
            'locked_comp': (r.get('v3_intention') or {}).get('locked_comp') or '',
            # P1 配方锁目标(v3_intention.p1_pair;缺键/空 = 配方锁未活跃)
            'p1_pair': (r.get('v3_intention') or {}).get('p1_pair') or (),
            # 轮末快照两键(②④凑齐现算输入;缺 = 回退 form_ok 镜像)
            'state_board_factions': st.get('board_factions'),
            'state_deployed': st.get('deployed'),
        })
    for o in outs:
        for row in g(o.get('run_id') or '?')['rows']:
            if row['_key'] == (o.get('plane') or 1, o.get('round_num') or 0):
                row['node_type'] = o.get('node_type')
    # killed 真值捕获(通关权威口径消费源,件3):逐局取
    # (plane, round) 最大的 outcome 行的 sim.killed——末行 = 该局最后一场
    # 战斗的结算,True = 玩家击败对手(全载体 = 杀穿 boss = 真通关)。
    # 不回退取早轮行:早轮 True 只证该轮胜,不证终局杀穿。sim 键缺/None
    # = 不可判(旧批无该字段同此,未知桶,禁默认通关);局无 outcome 行
    # 时 games 里的 killed 保持 shell 初值 None,同归未知桶。
    last_out: dict[str, tuple] = {}
    for o in outs:
        rid = o.get('run_id') or '?'
        key = (o.get('plane') or 1, o.get('round_num') or 0)
        if rid not in last_out or key >= last_out[rid][0]:
            last_out[rid] = (key, (o.get('sim') or {}).get('killed'))
    for rid, (_, k) in last_out.items():
        gd = games.get(rid)
        if gd is not None:
            gd['killed'] = k
    # 权威源降级通道(T-169 落地审 F7:新批布局 2026-09-07 起不落
    # runs.jsonl,旧通道成死路)——runs.jsonl 缺失时读 outcomes.jsonl
    # 逐局 max(plane)(同语义:引擎实际到达的最高位面,逐轮行带 plane);
    # runs 值优先不覆盖(旧批兼容)。两源皆缺的局 plane_reached 保持
    # None(不可判,死亡筛不适用),report 头部小注显影(F3)。
    # 位置=decisions/outcomes 两循环后(games 键已齐),回填才非空操作。
    if not (batch / 'runs.jsonl').exists():
        max_plane: dict[str, int] = {}
        for o in outs:
            rid = o.get('run_id') or '?'
            pl = o.get('plane')
            if isinstance(pl, int):
                max_plane[rid] = max(max_plane.get(rid, 0), pl)
        for rid, pl in max_plane.items():
            gd = games.get(rid)
            if gd is not None and gd['plane_reached'] is None:
                gd['plane_reached'] = pl
    out: dict[str, dict] = {}
    for rid, gd in games.items():
        rows = sorted(gd['rows'], key=lambda r: r['_key'])
        for r in rows:
            del r['_key']
        out[rid] = {'rows': rows, 'plane_reached': gd['plane_reached'],
                    'killed': gd['killed']}
    return out


def _archive_rows(mid: str) -> dict:
    p = MATCHES / f'match_{mid}.json'
    if not p.exists():
        idx = _load(MATCHES / 'index.jsonl')
        hit = [e['game_id'] for e in idx if e.get('game_id', '').endswith(mid)]
        if not hit:
            raise SystemExit(f'档案不存在:{mid}')
        p = MATCHES / f'match_{hit[-1]}.json'
    m = json.loads(p.read_text(encoding='utf-8'))
    rows = [{
        'plane': r.get('plane'), 'round': r.get('round'), 'node_type': r.get('node_type'),
        'gold': r.get('gold'), 'hp': r.get('hp'),
        'form': r.get('b_t', r.get('form_score')), 'form_ok': r.get('form_ok'),
        'level': r.get('level'),
        # 档案行无 v3_intention 键 → None(结构性无数据;与 sim 的「未锁线」
        # 是两种事实,④ 判定时不入分母,见模块 docstring)
        'locked_comp': None,
        # 档案行结构性无 p1_pair(同上,两种事实)→ None,代理分支不可达
        'p1_pair': None,
    } for r in m.get('rounds', [])]
    eg = m.get('endgame', {}) or {}
    # killed 真值(权威口径,件3):取 (plane, round) 最大轮的
    # outcome.killed,与 sim 侧同律——不回退取早轮(早轮 True 只证该轮胜,
    # 不证终局杀穿)。末轮 outcome 缺/null 或 killed=null = 不可判(未知
    # 桶,禁默认通关;旧档案末轮 outcome 未捕获常见,如实申报)。
    # 合成轮不承载真值:补给节点 outcome 是采集端合成填充(source=
    # synthetic_supply),其 killed=true 非战斗结算——恰为末轮时整局落
    # 未知桶(不排除出扫描:排除式会在「真末轮 outcome 缺失+早轮
    # killed=true」场景复刻不回退违规)。行面合取对此拦不住:合成末轮
    # 快照 hp>0 且 plane_reached≥2 时行面同样通过(实库档案
    # g_20260901_202525/g_20260902_023643 的 loss/stopped 局曾据此误判)。
    last_round = None
    last_key = (-1, -1)
    for r in m.get('rounds', []):
        key = (r.get('plane') or 1, r.get('round') or 0)
        if key >= last_key:
            last_key = key
            last_round = r
    oc = (last_round or {}).get('outcome') if last_round else None
    # 合成判定双信号:结构面 = 非战斗节点(补给);标注面 = source 带
    # synthetic 前缀(防未来新增合成种类)。loss_page/recovered 是真实
    # 结算的恢复通道,不在排除面。
    synth = oc is not None and (
        (last_round or {}).get('node_type') == '补给'
        or str(oc.get('source') or '').startswith('synthetic'))
    killed = None if oc is None or synth else oc.get('killed')
    return {'rows': rows, 'plane_reached': eg.get('plane_reached'),
            'killed': killed,
            'game_id': m.get('game_id', mid)}


# ---------- 四指标 ----------

def _row_form_ok(row: dict) -> bool | None:
    """行凑齐判定(口径单一源 = 模块 docstring ②节):轮末快照现算优先
    (kernel readiness 快照读口,消除镜像写端商店帧时点差),快照缺
    输入/判据不可判(None)回退 form_ok 镜像读数——回退语义与旧口径
    逐位等价,旧行/档案行零漂移。"""
    if readiness_form_ok_from_snapshot is not None:
        v = readiness_form_ok_from_snapshot(
            {'board_factions': row.get('state_board_factions'),
             'deployed': row.get('state_deployed')},
            locked_comp=row.get('locked_comp') or '',
            p1_pair=row.get('p1_pair') or ())
        if v is not None:
            return v
    return row.get('form_ok')


def game_metrics(game: dict) -> dict:
    """逐局四指标取值(口径见模块 docstring;None = 无数据,不折 0)。

    通关双口径:passed_row = 行面口径(披露列);passed = killed 真值
    (权威,件3)= passed_row ∧ game['killed'] is True。killed
    不可判(None)→ passed 必 False 且入未知桶(禁默认通关)。
    """
    rows: list[dict] = game['rows']
    p1_rows = [r for r in rows if r['plane'] == 1]
    p1_last = p1_rows[-1] if p1_rows else None
    last = rows[-1] if rows else None
    # 行面口径(披露列):plane 证据 + 死亡筛,无 killed 数据历史批唯一可算口径
    passed_row = any((r.get('plane') or 0) >= 2 for r in rows)
    if not passed_row and game.get('plane_reached') is not None:
        passed_row = game['plane_reached'] >= 2
    # 死亡筛(T-169 统计口径增补):plane 证据达 2 后还须末行 hp>0——
    # 死在 P2 的局(末行 hp=0)行面不存活。hp 缺读局不适用死亡筛 =
    # 保持 plane 证据判定(不可判 ≠ 判死,边界见模块 docstring)。
    if passed_row and last is not None and last.get('hp') is not None \
            and last['hp'] <= 0:
        passed_row = False
    # killed 消费(权威口径,件3):通关 = 行面存活 ∧ 局末行
    # killed==True。killed None(缺行/缺键)= 未知桶,不入通关(禁默认
    # 通关)——「活到末轮」与「杀穿 boss」在行面同形,killed 是唯一区分。
    killed = game.get('killed')
    passed = passed_row and killed is True
    lc = last.get('locked_comp') if last else None
    proxy = False
    if lc is None:
        comp_done = None            # 档案源结构性无锁线字段 = 无数据
    elif lc:
        comp_done = 1 if _row_form_ok(last) else 0
    elif last.get('p1_pair'):
        # P1 配方对代理键(观测面专用;口径与语义依据见模块 docstring ④ 节):
        # locked_comp 按 在 P1 配方锁帧恒空,p1_pair 非空 = 配方锁
        # 活跃 → 锁定目标代理 = 配方对,完成判定按②同款行凑齐判定(该
        # 帧族判据核即配方对物化方向)。只读遥测,语义零改。
        comp_done = 1 if _row_form_ok(last) else 0
        proxy = True
    else:
        comp_done = 0               # 未锁线 = 0(用户规格逐字;含配方对空窗帧)
    return {
        'passed_row': passed_row,
        'passed': passed,
        'killed': killed,
        'exit_gold': p1_last.get('gold') if p1_last else None,
        'exit_hp': p1_last.get('hp') if p1_last else None,
        'exit_form_ok': _row_form_ok(p1_last) if p1_last else None,
        'exit_form': p1_last.get('form') if p1_last else None,
        'final_gold': last.get('gold') if last else None,
        'comp_done': comp_done,
        'comp_proxy': proxy,
    }


def _fmt(v, nd: int = 0) -> str:
    if v is None:
        return '—'
    return f'{v:.{nd}f}' if isinstance(v, float) else str(v)


def carrier_label(games: dict[str, dict], source: str) -> str:
    """批载体标识(头行自动标注;T-169 统计口径增补)。

    全载体 = 生产档案,或存在 plane>=2 行的 sim 批(数据证明可达位面 2);
    P1-only = 零 plane>=2 行的 sim 批——该批通关率 0 是载体辖域结果,
    禁当行为信号(判读先看本标识再看通关率)。边界:planes=2 sim 批
    恰逢全批死在 P1 时行面证据与 P1-only 载体同形,本标识按「数据可见
    辖域」如实标注(该批同样没有 P2 数据可判,语义不漂)。
    """
    if source == 'archive':
        return '全载体(生产档案)'
    has_p2 = any((r.get('plane') or 0) >= 2
                 for g in games.values() for r in g.get('rows') or [])
    if has_p2:
        return '全载体(sim,存在 plane≥2 行)'
    return 'P1-only(零 plane≥2 行;通关率 0 属载体辖域)'


def report(games: dict[str, dict], title: str, source: str = 'sim') -> None:
    ms = {rid: game_metrics(g) for rid, g in games.items()}
    n = len(ms)

    # 通关双口径(权威 = killed 真值,件3;行面口径旧列披露)。
    # ② 过渡凑齐率的「通关局」分母随权威口径走。
    passed = sum(1 for m in ms.values() if m['passed'])
    passed_row_n = sum(1 for m in ms.values() if m['passed_row'])
    killed_unknown = sum(1 for m in ms.values() if m['killed'] is None)
    ok_games = [m for m in ms.values() if m['passed']]
    ok_ok = sum(1 for m in ok_games if m['exit_form_ok'])
    golds = [m['final_gold'] for m in ms.values() if isinstance(m['final_gold'], (int, float))]
    comp = [m['comp_done'] for m in ms.values() if m['comp_done'] is not None]
    comp1 = sum(1 for c in comp if c == 1)
    line28 = sum(1 for m in ms.values()
                 if isinstance(m['exit_gold'], (int, float)) and m['exit_gold'] >= 50)
    gold28 = sum(1 for m in ms.values() if isinstance(m['exit_gold'], (int, float)))

    print(f'\n== 批统计面(四指标) | {title} | 局数 {n} '
          f'| 载体: {carrier_label(games, source)} ==')
    if source == 'sim':
        # boss 结算敏感性边界披露(T-169 增补 ②,只披露不升维;口径见
        # 模块 docstring「boss 结算敏感性边界披露」节,单一源在彼处)
        print('边界: boss 结算键=净星深一维,无 rung×净星深'
              '敏感性——升维列后续候选,boss 段读数按一维键边界理解')
        # 局级权威源缺行小注(T-169 落地审 F3):runs/outcomes 两通道皆
        # 无法给出 plane_reached 的局数——该类局死亡筛不适用(不可判),
        # 通关判定降级行面证据;>0 时显影,归 runs/账本完整性问题。
        no_auth = sum(1 for gd in games.values()
                      if gd.get('plane_reached') is None)
        if no_auth:
            print(f'注: 局级权威源缺行 {no_auth}/{n} 局无 plane_reached'
                  '(runs/outcomes 双通道皆缺;通关判定降级行面证据)')
    # 通关双口径披露:权威 = killed 真值;行面口径旧列兼容历史批。
    # 差值拆解 = 行面误判面(未杀穿 a + 真值不可判 b),判读直接可见。
    print(f'通关率(killed 真值,权威): {passed}/{n}')
    row_kf = sum(1 for m in ms.values()
                 if m['passed_row'] and m['killed'] is False)
    row_ku = sum(1 for m in ms.values()
                 if m['passed_row'] and m['killed'] is None)
    row_tail = (f'(行面多计 {passed_row_n - passed} = 未杀穿 {row_kf} '
                f'+ 真值不可判 {row_ku})') if passed_row_n != passed else ''
    print(f'通关率(行面口径,披露用): {passed_row_n}/{n} {row_tail}'.rstrip())
    if killed_unknown:
        print(f'注: killed 真值不可判 {killed_unknown}/{n} 局(局末行 '
              'outcomes killed 缺行/缺键/None;不入通关,如实申报)')
    if ok_games:
        print(f'②过渡凑齐率(P1 出口,通关局中): {ok_ok}/{len(ok_games)} = {ok_ok / len(ok_games):.0%}')
    else:
        print(f'②过渡凑齐率(P1 出口,通关局中): 不适用(通关局 0/{n})')
    g3 = (f'{min(golds)} / {statistics.median(golds)} / {max(golds)}'
          if golds else '无数据')
    print(f'③终局金 min/中位/max: {g3}(可读 {len(golds)}/{n} 局)')
    if comp:
        proxy_n = sum(1 for m in ms.values() if m['comp_proxy'])
        print(f'④终局阵容完成率: {comp1}/{len(comp)} = {comp1 / len(comp):.0%}'
              + (f'(可判 {len(comp)}/{n} 局)' if len(comp) < n else '')
              + (f'[P1 配方对代理判定 {proxy_n} 局,局表 p 标]'
                 if proxy_n else ''))
    else:
        print('④终局阵容完成率: 无数据(全批无锁线字段观测)')
    print(f'[28]线 出口金≥50: {line28}/{gold28} 局(读数,非门)')
    # 出口生存余量读数行(T-169 账本 23:49 增补/落地审 F3 补交付;
    # 读数非门):P1 出口行(= ① 同行源)hp 分布 + 死亡地板命中数
    # (sim 地板 0,出口 hp<=0 = 死在出口帧;与死亡筛同源不同问——
    # 筛答「算不算通关」,本行答「出口时还剩多少血」)。hp 缺读局
    # 不入分布,可读数随行披露。
    exit_hps = [m['exit_hp'] for m in ms.values()
                if isinstance(m['exit_hp'], (int, float))]
    exit_floor = sum(1 for h in exit_hps if h <= 0)
    eh3 = (f'{min(exit_hps)} / {statistics.median(exit_hps)} / {max(exit_hps)}'
           if exit_hps else '无数据')
    print(f'出口生存余量 hp min/中位/max: {eh3}(可读 {len(exit_hps)}/{n} 局) '
          f'| 地板命中(hp≤0) {exit_floor} 局(读数,非门)')

    print(f"\n{'局号':<22} {'通关行/killed':<12} {'①出口金':>7} {'②凑齐(形态)':<14} {'③终局金':>7} {'④完成':>5}")
    for rid in sorted(ms):
        m = ms[rid]
        rmark = '✓' if m['passed_row'] else '✗'
        kmark = '—' if m['killed'] is None else ('✓' if m['killed'] else '✗')
        mark = f'{rmark}/{kmark}'
        if m['exit_form_ok'] is None:
            c2 = '—'
        else:
            c2 = ('✓' if m['exit_form_ok'] else '✗') + f' {_fmt(m["exit_form"], 2)}'
        c4 = ('—' if m['comp_done'] is None
              else str(m['comp_done']) + ('p' if m['comp_proxy'] else ''))
        print(f'{rid:<22} {mark:<6} {_fmt(m["exit_gold"]):>7} {c2:<14} '
              f'{_fmt(m["final_gold"]):>7} {c4:>5}')


def main() -> None:
    global SIM_ROOT, MATCHES
    ap = argparse.ArgumentParser()
    ap.add_argument('--sim-batch', default='',
                    help='sim 批次名或 latest(= 批名内嵌创建时间戳最新'
                         '的含账批次;口径见 _latest_sim_batch)')
    ap.add_argument('--batch', default='', help='sim 批次目录直接指路径(离线/另机语料)')
    ap.add_argument('--recent', type=int, default=0, help='生产档案最近 N 局')
    ap.add_argument('--match', default='', help='生产档案单局 game_id')
    # 档案根参数(覆盖缺省 telemetry 根;离线/另机语料对账用)
    ap.add_argument('--sim-root', default=str(SIM_ROOT),
                    help='sim 批根目录(缺省 .debug/currency_war/telemetry/sim)')
    ap.add_argument('--matches-root', default=str(MATCHES),
                    help='按局档案根(缺省 .debug/currency_war/telemetry/matches)')
    args = ap.parse_args()
    SIM_ROOT = Path(args.sim_root)
    MATCHES = Path(args.matches_root)
    if args.batch:
        batch = Path(args.batch)
        if not (batch / 'decisions.jsonl').is_file():
            raise SystemExit(f'批次目录不含 decisions.jsonl:{batch}')
        report(_sim_rows(batch), batch.name, source='sim')
    elif args.sim_batch:
        name = args.sim_batch
        batch = (_latest_sim_batch(SIM_ROOT) if name == 'latest'
                 else SIM_ROOT / name)
        if not batch.is_dir():
            raise SystemExit(f'批次不存在:{batch}')
        report(_sim_rows(batch), batch.name, source='sim')
    elif args.match:
        g = _archive_rows(args.match)
        report({g['game_id']: g}, g['game_id'], source='archive')
    elif args.recent:
        idx = _load(MATCHES / 'index.jsonl')[-args.recent:]
        games: dict[str, dict] = {}
        for e in idx:
            if not (MATCHES / f"match_{e['game_id']}.json").exists():
                continue
            g = _archive_rows(e['game_id'])
            games[g['game_id']] = g
        report(games, f'生产档案最近 {len(games)} 局', source='archive')
    else:
        ap.error('需 --sim-batch / --batch / --recent / --match 之一')


if __name__ == '__main__':
    main()
