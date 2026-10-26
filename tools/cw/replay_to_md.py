"""货币战争对局 journal → markdown 深度复盘渲染器(journal 行模型版)。

## 数据源与行模型

输入 = state journal(JSONL,两行型):``row='write'`` 字段写入行 /
``row='obs_event'`` 观察事件行;行 = 改了什么(field/after)+ 渠道签名 sig +
版本 id v + 写入后 ``state.values`` 累计快照,行行自足。行模型权威 =
``docs/develop/sr_od/application/currency_war/game_state/journal.md`` §1;
宽容读入口单一源 = ``sr_od.application.currency_war.telemetry.journal_query``
(:func:`read_journal_stats`:坏行/半行/非对象行逐行跳过 + 计数留痕),
本工具是其消费方(运行需 ``PYTHONPATH=src``,先例 =
``tools/cw/repair_invest_attribution.py``)。

## 渲染结构

局头(meta 逐行)→ 开局段 → 逐节点组(P-R,类型取组内首行 ``node.kind``)
→ 组内画面章(画面域写入行切分 + 弹层 actor 注册表双轨;切章锚 =
``field='current_screen'`` 写入行本体,快照携带 cs 只作归属;动作节
章归属锚 = 回执 ``screen`` 字段 = **动作发出画面**——转移类动作(如开
商店)的回执在切屏写入行之后落窗,按发出画面回搜本章组已开画面章归位,
不按位置落到变更后画面(旧数据 screen=目标画面语义 → 位置归属回退);
章内状态差分因果归属 = ``logic_action`` 家族写入行挂其后最近回执的
动作节(动作的效果写入先于其回执落盘;组尾无回执认领 → 章内变化块;
非 logic_action 非 obs 写入挂组内最近动作节);章内
「0 观察 = 开章快照 ∩ 注册键集(表格型键出独立表:备战章上阵表
紧贴备战席表前,余同备战席/商品牌面/选项面)+ 本章观察道写入动态
显影(画面 op 观察到什么本章显什么,首写定帧值;注册键回读与观察
回读异值 → 章尾注记)→ 动作节×N → 策略评价」;策略遥测装配(有文件时):动作节标题下
「策略依据」块(行 1-2 回执 dtag join)/章内「#### 策略依据」小节
(选择族章级挂载)/章尾未落地与失配注记/局头策略遥测行,设计 =
``docs/develop/sr_od/application/currency_war/changes/2026-10-24-strategy-telemetry/``
details/render-assembly.md)→ 未归节(有则)
→ 未归行(防静默丢行)
→ 复盘者附加(固定空节,复盘者协议产物落点)。策略侧会话态(v3 意向/
cw4_counters 等)不渲染;无收尾章、无局况速览。设计 =
``docs/develop/sr_od/application/currency_war/changes/2026-10-16-journal-review-renderer/``
(details/pipeline.md 渲染管线、details/render-spec.md 显示规范);
切章证据收窄与画面广播注册键 = 渲染器自身实现为准(以代码为准)。

## 用法(主仓根目录,PYTHONPATH=src)

    uv run python tools/cw/replay_to_md.py --match g_20260923_172823 \
        [--run run_20260923_172823] [--out 复盘.md | --stdout]
    uv run python tools/cw/replay_to_md.py --journal <根>/state/journal.jsonl \
        --game-id <名>      # sim 批 / live 未装配局(裸 journal 文件)

    [--strategy-telemetry <路径>]:策略遥测 jsonl 文件或目录;缺省探测
    journal 同根 strategy/ 目录(--journal = <根>/strategy/,--match =
    live 根),目录不存在或为空 = 功能关闭(报告与现状零差异)。

- ``--match``:档案 game_id,只读档案切片 ``slices['state/journal.jsonl']``
  (切片缺 → 退出码 2,不回退 live journal——live 为多局混合流,无档案
  元数据无法界定行域)。
- ``--journal``:裸 journal 文件(标准布局 ``<根>/state/journal.jsonl``;
  也可直接给其 state 上级目录),配 ``--game-id`` 命名(缺省取路径祖父
  目录名)。
- ``--run``:按行 ``run_id`` 精确过滤;值不在数据出现过 → 退出码 2(与旧
  渲染器「未知 run 全渲染+警告」不同,语义变更已申报 design §2);空
  run_id 行仅当 ts 落于切片首末行时间窗内放行(窗取切片行 ts,不取档案
  start_ts/end_ts 元数据——实测 9/23 档案 end_ts==start_ts 不可信)。
- ``--out``:缺省 = ``.debug/currency_war/deep_review/<game_id>.md``
  (2026-09-07 布局裁定);``--stdout`` 打印不落盘。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sr_od.application.currency_war.telemetry.journal_query import (
    JOURNAL_REL,
    ROW_OBS_EVENT,
    ROW_WRITE,
    JournalReadStats,
    node_key_of,
    read_journal_stats,
    row_kind,
    row_sig,
    state_values,
)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

#: 缺省档案根(标准布局,相对主仓根 cwd;路径操作用 pathlib)。
DEFAULT_MATCHES_DIR = Path('.debug/currency_war/telemetry/matches')

#: 深评固定落点(2026-09-07 用户裁定:一局一份 <game_id>.md)。
DEEP_REVIEW_DIR = Path('.debug/currency_war/deep_review')

#: CLI 用法错误退出码(档案缺/切片缺/journal 缺/--run 未知/参数矛盾)。
EXIT_USAGE = 2


# ---------------------------------------------------------------------------
# 渲染中间表示(pipeline §6 字段闭集;pipeline↔render-spec 唯一共享面)
# ---------------------------------------------------------------------------


@dataclass
class Delta:
    """一条状态变化(field, 前值, 后值, 说明, is_hook)。"""

    field: str
    before: Any
    after: Any
    note: str = ''
    is_hook: bool = False


@dataclass
class Action:
    """一个动作节(一条回执 = 一节;重试链合并节以 chain 承载全部回执)。"""

    no: int                       # 章内序号,1 基
    op: str
    title: str                    # render-spec §4 组装规则
    reason: str = ''
    detail: str = ''
    screen: str = ''              # 回执 screen = 动作发出画面(动作节章归属锚)
    extra: list[tuple[str, Any]] = field(default_factory=list)
    #: 重试链(pipeline §5:连续回执同 op 且前条 reason 非空 → 合并一节,
    #: 节内逐条列出;首元素 = receipt 本条)
    chain: list[dict[str, Any]] = field(default_factory=list)
    #: 动作级策略依据(回执 dtag join 命中的决策记录,按回执顺序;渲染 =
    #: 标题行下、状态变化表前。空 = 无遥测/未匹配,零差异)
    basis: list[DecisionRecord] = field(default_factory=list)
    deltas: list[Delta] = field(default_factory=list)


@dataclass
class Screen:
    """一个画面章(章首快照观察 + 动作节×N + 章内变化块 + 尾注)。"""

    screen_id: str                # 画面注册表键或原样 id
    title: str
    entry: list[tuple[str, Any]] = field(default_factory=list)
    entry_tables: list[tuple[str, list[str], list[list[str]]]] = field(
        default_factory=list)
    #: 章级策略依据(选择族入口章级挂载命中的决策记录,dseq 序;渲染 =
    #: 0 观察后独立小节「#### 策略依据」。空 = 无遥测/未挂载,零差异)
    strategy_records: list[DecisionRecord] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    trailing_changes: list[Delta] = field(default_factory=list)
    annots: list[str] = field(default_factory=list)
    has_decision: bool = False    # False = 不渲染策略评价节
    #: 构建期临时:未注册画面 op actor → 行数(渲染前聚合转尾注并剥离)
    _unreg_counts: dict[str, int] = field(default_factory=dict)
    #: 构建期临时:渲染同值写入计数(前=后,零信息;渲染前转尾注并剥离)
    _same_skipped: int = 0
    #: 构建期临时:观察尾注去重集(field, 格式化值)——同章重复写同值不刷屏
    _obs_seen: set = field(default_factory=set)
    #: 构建期临时:本章观察道写入显影(field → 格式化值,首写定帧值)——
    #: 0 观察动态段 = 画面 op 观察到什么本章显什么(注册键集之外无观察
    #: 黑洞),渲染时并进 0 观察、渲染前剥离
    _obs_entries: dict[str, str] = field(default_factory=dict)


@dataclass
class NodeInfo:
    """节点组标识(组内首行 node.kind 钉死——组内 kind 会翻转)。"""

    plane: int
    round: int
    kind_cn: str


@dataclass
class Section:
    """报告章组:开局组 → 节点组×N → 未归节组(有则)。"""

    kind: str                     # 'open' | 'node' | 'unattached'
    node: NodeInfo | None
    screens: list[Screen] = field(default_factory=list)
    #: 开局段无画面归属行注记(开局初始化写入/基线观察/缺口;
    #: pipeline §3 修订——粘进当前画面章会把种子推导与全局首遍观察
    #: 误记为画面内容,故落组级桶,仅开局段启用)
    opening_notes: list[str] = field(default_factory=list)
    #: 构建期临时:组内最近动作节(journal 序;重试链合并判据——回执按
    #: 发出画面归章后,重试两脚可能异章落窗,链判据必须跨章)
    _last_action: Action | None = None
    #: 构建期临时:待认领动作效果写入(logic_action 家族;动作的效果写入
    #: 先于其回执落盘,缓冲至该动作回执行到达时入其动作节),组尾无回执
    #: 认领 → 尾扫入最后画面章章内变化块(防静默丢行)
    _pending_deltas: list[Delta] = field(default_factory=list)


@dataclass
class Report:
    """渲染中间表示顶层(pipeline §6)。"""

    meta: list[tuple[str, Any]] = field(default_factory=list)
    stats: JournalReadStats = field(default_factory=JournalReadStats)
    sections: list[Section] = field(default_factory=list)
    annex_unattached: list[str] = field(default_factory=list)
    #: 策略遥测索引(None = 功能关闭:无文件/零记录,局头不加行)
    strategy: StrategyTelemetry | None = None


@dataclass
class DecisionRecord:
    """一条策略决策记录(strategy jsonl 行内存形态;capture-store §2 信封
    键闭集,run_id 过滤后入 join 索引)。"""

    load_seq: int                 # 全局加载序(0 基;FIFO 分配与去重稳定锚)
    dtag: str                     # <strategy_id>:<dseq>,动作级 join 键
    strategy_id: str
    entry: str                    # 决策入口名(14 闭集,ENTRY_SCREEN_MAP 键)
    #: 决策帧节点 {plane, round_num, kind}(gs.node 现读);None = null 帧,
    #: 不入章级挂载,计数进局头「未归属」(render-assembly §3)
    node: dict[str, Any] | None
    emitted_op: str               # 发出动作类型名(指纹一致性校验对照面)
    emitted_reason: str
    emitted_route_tag: str
    payload: dict[str, Any]       # 策略载荷(渲染器不解释语义)


@dataclass
class StrategyTelemetry:
    """策略遥测索引(发现+加载+run 过滤后的 join 面)。

    ``by_dtag`` = 动作级索引(回执 dtag → record,重复 dtag 首现优先);
    ``by_chapter`` = 章级索引,键 = (entry, plane, round_num),值按 dseq 序
    (同键多章 FIFO 分配源;render-assembly §3);``unattached`` 由 join 收尾
    回填 = 未归属记录(node=null/无锚章,局头「未归属 M 条」计数面)。
    """

    records: list[DecisionRecord] = field(default_factory=list)
    by_dtag: dict[str, DecisionRecord] = field(default_factory=dict)
    by_chapter: dict[tuple[str, Any, Any], list[DecisionRecord]] = field(
        default_factory=dict)
    unattached: list[DecisionRecord] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 注册表(render-spec §3):画面章 = current_screen 快照值或弹层 actor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScreenSpec:
    """画面章规格:章名 / 是否决策面 / 0 观察键集(field 名,点分=嵌套)。"""

    title: str
    decision: bool = False
    entry_fields: tuple[str, ...] = ()


#: 快照章注册表(current_screen 值 → 规格)。战斗章结算不入 0 观察——
#: settlement 写入行走 pipeline §5「章内变化」块(键集锚 =
#: cw_screen_battle_wait.py:125,449-461,550-565)。
#:
#: 「货币战争-」前缀 12 键 = sim 引擎画面广播值(cw_sim_backend.py
#: SCREEN_* 常量直通,词表 = 实机建档名);规格 = ACTOR_REGISTRY 对应
#: actor 孪生同款。注册纪律:同 title 必须同规格(decision/键集)——
#: 章相邻合并键 = title(见 _build_section),同 title 异规格会静默
#: 错规格;现注册表全量查重已满足,扩表时守此纪律。
SCREEN_REGISTRY: dict[str, ScreenSpec] = {
    '货币战争-备战': ScreenSpec(
        '画面-备战', True,
        ('gold', 'hp', 'level', 'xp', 'level_up_cost', 'streak', 'deployed',
         'bench', 'back_layout', 'board', 'equips', 'occupied_equips',
         'spheres', 'overflow_warning', 'overflow_card', 'active_strategies',
         'active_env')),
    '货币战争-备战-开商店': ScreenSpec(
        '画面-商店', True,
        ('gold', 'free_refresh_left', 'shop_refresh_cost', 'level', 'shop')),
    '货币战争-战斗等待': ScreenSpec(
        '画面-战斗', False, ('deployed', 'enemy_difficulty',
                             'enemy_affixes')),
    # —— sim 广播值(overlay/流程画面;CwScreenBriefing/CwScreenBossBriefing
    #    等孪生同款)——
    '货币战争-简报': ScreenSpec(
        '画面-BOSS简报', False,
        ('plane_bosses', 'enemy_affixes', 'selected_difficulty')),
    '货币战争-BOSS简报': ScreenSpec(
        '画面-BOSS简报', False,
        ('plane_bosses', 'enemy_affixes', 'selected_difficulty')),
    '货币战争-投资环境': ScreenSpec(
        '画面-投资环境', True,
        ('invest_env_opts', 'env_refresh_left', 'gold')),
    '货币战争-投资策略': ScreenSpec(
        '画面-投资策略', True,
        ('invest_strategy_opts', 'strategy_refresh_left')),
    '货币战争-补给': ScreenSpec(
        '画面-补给', True, ('supply.options', 'supply_refresh_left')),
    '货币战争-遭遇节点': ScreenSpec(
        '画面-遭遇', True, ('encounter.options', 'encounter_refresh_left')),
    '货币战争-位面过渡': ScreenSpec(
        '画面-位面转场', False, ('node_seq_by_plane', 'enemy_affixes')),
    '货币战争-备战-武装箱选择': ScreenSpec(
        '画面-箱子', True, ('box_card_names',)),
    '货币战争-备战-专家邀请函': ScreenSpec(
        '画面-专家邀请', True, ('expert_invite',)),
    '货币战争-盛会之星': ScreenSpec(
        '画面-巨星', True, ('megastar_opts',)),
    '货币战争-银狼升星': ScreenSpec(
        '画面-银狼策划', True, ('planner_opts',)),
    # 广播名来源 = kernel/cw_game_state.py 图层注册(star_tome_opts →
    # 货币战争-星徽秘典弹窗);「书卡」画面即星徽秘典选择,实写键 =
    # star_tome_opts(cw_screen_report/bookcard.py 同门双写)。
    '货币战争-星徽秘典弹窗': ScreenSpec(
        '画面-书卡', True, ('star_tome_opts',)),
}

#: 弹层章注册表(actor 全名 → 规格;回执 screen / sig.screen 不参与切分)。
#: 「其余 operations/cw_screen/ 已定义 op 按裁定②同规:有 journal 行即按其
#: actor 注册显示」——辅助 op 类按类名原样作章名、非决策面、0 观察空
#: (render-spec §3 未给显式章名,按确定性规则落地;CwScreenPrep/CwScreenShop
#: 即快照章两行不另注册,CwScreenBattleWait 归战斗快照章)。
ACTOR_REGISTRY: dict[str, ScreenSpec] = {
    'CwScreenInvestEnv': ScreenSpec('画面-投资环境', True,
                                    ('invest_env_opts', 'env_refresh_left',
                                     'gold')),
    'CwScreenInvestStrategy': ScreenSpec('画面-投资策略', True,
                                         ('invest_strategy_opts',
                                          'strategy_refresh_left')),
    'CwScreenSupplyNode': ScreenSpec('画面-补给', True,
                                     ('supply.options', 'supply_refresh_left')),
    'CwScreenEncounter': ScreenSpec('画面-遭遇', True,
                                    ('encounter.options',
                                     'encounter_refresh_left')),
    'CwScreenBriefing': ScreenSpec('画面-BOSS简报', False,
                                   ('plane_bosses', 'enemy_affixes',
                                    'selected_difficulty')),
    'CwScreenBossBriefing': ScreenSpec('画面-BOSS简报', False,
                                       ('plane_bosses', 'enemy_affixes',
                                        'selected_difficulty')),
    'CwScreenPlaneTransition': ScreenSpec('画面-位面转场', False,
                                          ('node_seq_by_plane',
                                           'enemy_affixes')),
    'CwScreenPlaneDetail': ScreenSpec('画面-位面转场', False,
                                      ('node_seq_by_plane', 'enemy_affixes')),
    'CwScreenPlaneIntel': ScreenSpec('画面-位面转场', False,
                                     ('node_seq_by_plane', 'enemy_affixes')),
    'CwScreenMegastar': ScreenSpec('画面-巨星', True, ('megastar_opts',)),
    'CwScreenPartner': ScreenSpec('画面-伙伴', True, ('partner_opts',)),
    'CwScreenExpertInvite': ScreenSpec('画面-专家邀请', True,
                                       ('expert_invite',)),
    'CwScreenFortune': ScreenSpec('画面-命运卜者', True, ('fortune_opts',)),
    'CwScreenWishTrial': ScreenSpec('画面-祈愿试炼', True,
                                    ('wish_trial_opts',)),
    # 书卡键集 = star_tome_opts(实写端 cw_screen_report/bookcard.py;
    # box_card_names 是武装箱键,错置为存量错行已修复——同 title 同规格
    # 纪律下与 SCREEN_REGISTRY 画面-书卡行一致)。CwScreenBoxPick(画面-
    # 箱子)与武装箱广播行仍持 box_card_names,两屏本就不共键。
    'CwScreenBookcard': ScreenSpec('画面-书卡', True, ('star_tome_opts',)),
    'CwScreenBoxPick': ScreenSpec('画面-箱子', True, ('box_card_names',)),
    'CwScreenArmoryBox': ScreenSpec('画面-军械库', True, ('equips',)),
    'CwScreenAhaEquipPick': ScreenSpec('画面-顿悟装备', True, ('equips',)),
    'CwScreenYinLang': ScreenSpec('画面-银狼策划', True, ('planner_opts',)),
    'CwOpSettleConfirm': ScreenSpec('画面-对局收口', False, ()),
    'CwLoop': ScreenSpec('画面-对局收口', False, ()),
    # —— 交互辅助 op(operations/cw_screen/ 已定义,裁定②同规)——
    'CwScreenItemDetailPopup': ScreenSpec('CwScreenItemDetailPopup'),
    'CwScreenRefreshOddsPopup': ScreenSpec('CwScreenRefreshOddsPopup'),
    'CwScreenRoleDetailOverlay': ScreenSpec('CwScreenRoleDetailOverlay'),
    'CwScreenShopCardDetailPopup': ScreenSpec('CwScreenShopCardDetailPopup'),
    'CwScreenEmblemDetailPopup': ScreenSpec('CwScreenEmblemDetailPopup'),
    'CwScreenInterruptDialog': ScreenSpec('CwScreenInterruptDialog'),
    'CwScreenConsumableOverlay': ScreenSpec('CwScreenConsumableOverlay'),
    'CwScreenNextButton': ScreenSpec('CwScreenNextButton'),
    'CwScreenWaitOneOne': ScreenSpec('CwScreenWaitOneOne'),
    'CwScreenPrepLockedReturn': ScreenSpec('CwScreenPrepLockedReturn'),
    'CwScreenDeployNotFull': ScreenSpec('CwScreenDeployNotFull'),
}

#: 节点类型中文映射(词表来源 = NodeKey.kind 注释 cw_game_state.py:697;
#: 实测值 live+sim 合并覆盖;未知值原样显示)。
NODE_KIND_CN: dict[str, str] = {
    'reward': '奖励', 'battle': '战斗', 'encounter': '遭遇',
    'supply': '补给', 'boss': 'BOSS', 'prep': '备战',
}

#: 快照章形态的画面 op(设计明文「CwScreenPrep/CwScreenShop 即快照章两行,
#: 不另注册」;CwScreenBattleWait 同归战斗快照章)——行经 current_screen 归
#: 快照章,不判未注册缺口。
_SNAPSHOT_SCREEN_ACTORS: frozenset[str] = frozenset({
    'CwScreenPrep', 'CwScreenShop', 'CwScreenBattleWait',
})

#: 已知非画面 op 的 CwScreen 前缀类(商店买入执行逻辑;journal.md §2 actor
#: 类属 = 动作 op 类名——note_action_receipt 回执发出者,历史命名带前缀),
#: 其 logic_action 写入是动作效果,不判未注册缺口。
_ACTION_ACTOR_EXEMPT: frozenset[str] = frozenset({'CwScreenBuyCards'})

#: 观察尾注跳过键(内部路由面,对复盘零信息:上一画面/当前画面——当前画面
#: 已是切章锚,重复显影)。
_OBS_NOTE_SKIP: frozenset[str] = frozenset({'prev_screen', 'current_screen'})

#: 已注册画面章 0 观察键全集(快照章 + 弹层章注册表并集):观察尾注跳过。
#: 这些字段必在后续对应画面章的 0 观察显影,观察道回读是重复显影;且回读
#: 与动作无因果(如节点窗发牌的商店牌面回读挂进采集动作),按时间窗归属
#: 只会制造误归因(sim 广播形态实测:34 条尾注中 30 条为此类)。
_ALL_ENTRY_KEYS: frozenset[str] = frozenset(
    key
    for spec in list(SCREEN_REGISTRY.values()) + list(ACTOR_REGISTRY.values())
    for key in spec.entry_fields)


#: 决策入口 → 渲染章键(策略遥测迭代 render-assembly §2,14 行闭集直译;
#: 章键 = 注册表现名,注册表缺失/更名时以注册表为准修正本表)。行 1-2
#: (prep/shop,对应 4 个回执产出口)走动作级 dtag join,行 3-14(选择
#: 族,不产回执)走章级挂载——两级互斥,适用集钉死 = render-assembly §3。
ENTRY_SCREEN_MAP: dict[str, str] = {
    'decide_prep_screen': '画面-备战',
    'decide_shop_action': '画面-商店',
    'decide_invest_env': '画面-投资环境',
    'decide_invest_strategy': '画面-投资策略',
    'decide_supply': '画面-补给',
    'decide_encounter': '画面-遭遇',
    'decide_megastar': '画面-巨星',
    'decide_partner': '画面-伙伴',
    'decide_planner': '画面-银狼策划',
    'decide_fortune': '画面-命运卜者',
    'decide_wish_trial': '画面-祈愿试炼',
    'decide_box_card': '画面-箱子',
    'decide_expert_invite': '画面-专家邀请',
    'decide_star_tome': '画面-书卡',
}

#: 动作级 join 适用集(行 1-2;选择族 dtag 出现在回执上 = 陈旧搭错异常
#: 形态,按失配处理——capture-store §2 适用域申报的渲染侧对偶)。
_ACTION_JOIN_ENTRIES: frozenset[str] = frozenset(
    {'decide_prep_screen', 'decide_shop_action'})

#: 回执 op 命名域归一(render-assembly §3):prep 统一口与商店落地门写
#: 动作类型名(``type(action).__name__``),open_shop/close_shop 写执行体
#: op 名——指纹校验前先归一;其余回执 op 即动作类型名字面相等。
_OP_NAME_NORMALIZE: dict[str, str] = {
    'CwOpOpenShop': 'CwActionOpenShopParam',
    'CwActionCloseShopOp': 'CwActionCloseShopParam',
}


def _is_unregistered_screen_actor(actor: str) -> bool:
    """未注册画面 op 判定(pipeline §4「未注册 actor」的适用对象)。

    画面 op 类名约定 = CwScreen 前缀(operations/cw_screen/ 实测 33 类全部
    此前缀);命中注册表 / 快照章形态 / 已知动作类豁免外的前缀类 = 未注册,
    行显影缺口注记(缺口可见性 = 对断供静默病根的正面设计目标)。非画面
    actor(观察汇聚 cw_observation/对账/恢复/引擎等)不判——设计条款的
    上下文是画面 op 注册表,不是任意写入者。
    """
    return (actor.startswith('CwScreen')
            and actor not in ACTOR_REGISTRY
            and actor not in _SNAPSHOT_SCREEN_ACTORS
            and actor not in _ACTION_ACTOR_EXEMPT)

#: 动作词中文映射(render-spec §4.1:回执动词开放集,未命中原样显示禁猜)。
ACTION_WORD_MAP: dict[str, str] = {
    # 短动词(live 实测)
    'BuyCard': '买牌', 'SellBench': '卖备战', 'SellDeployed': '卖上阵',
    'DeployMove': '换位', 'RunDeploy': '部署', 'WearEquip': '穿装备',
    'ClickSpheres': '点晶矿', 'CwOpOpenShop': '开店', 'CwOpCloseShop': '收店',
    'StartBattle': '出战',
    # 参数型别名(sim 实测 + 现役发射点 cw_close_shop_action.py:49 等)
    'CwActionBuyCardParam': '买牌', 'CwActionSellBenchParam': '卖备战',
    'CwActionDeployMoveParam': '换位', 'CwActionWearEquipParam': '穿装备',
    'CwActionLevelUpParam': '升级', 'CwActionLevelUpShopParam': '店内升级',
    'CwActionStartBattleParam': '出战', 'CwActionCollectOreParam': '采晶矿',
    'CwActionCloseShopOp': '收店',
    # 代码词表补录(旧流实测有、新账未再现,保留映射)
    'LevelUp': '升级', 'LevelUpShop': '店内升级', 'RefreshShop': '刷新商店',
    'OpenBox': '开箱',
}

#: 状态字段中文映射(render-spec §4.2;journal field → 显示名,未命中显原始名)。
#: 显示形态统一「中文(英文)」(field_cn 出口统一加括号原字段名,方便理解
#: 与对照代码双向);本表 = 中文词表单一源,新字段上报告前先补映射。
FIELD_CN_MAP: dict[str, str] = {
    'gold': '金', 'hp': '血', 'level': '等级', 'xp': '经验', 'streak': '连胜',
    'level_up_cost': '升级价', 'deploy_cap': '部署上限', 'bench': '备战席',
    'deployed': '上阵', 'front_row': '前排', 'back_row': '后排',
    'back_layout': '后台格数', 'board': '羁绊计数', 'equips': '装备库存',
    'occupied_equips': '穿戴', 'shop': '商店牌面', 'spheres': '晶矿',
    'active_env': '投资环境', 'active_strategies': '持卡',
    'planner_opts': '策划候选', 'settlement': '结算', 'node': '节点',
    'node_pos': '节点序位',
    'current_screen': '画面', 'overflow_warning': '溢出警告',
    'overflow_card': '溢出卡',
    # 经济 / 商店域
    'shop_refresh_cost': '商店刷新价', 'free_refresh_left': '免费刷新',
    'diamond_count': '钻石', 'round_fresh_buys': '本轮新买',
    'ore_rewards': '晶矿奖励', 'prev_node_spent': '上节点已消费',
    # 投资域
    'invest_env_opts': '投资环境候选', 'env_refresh_left': '环境刷新余量',
    'invest_strategy_opts': '投资策略候选',
    'strategy_refresh_left': '策略刷新余量',
    # 节点 / 对局面
    'plane_bosses': '位面首领', 'enemy_affixes': '敌方词缀',
    'selected_difficulty': '选择难度', 'enemy_difficulty': '敌方难度',
    'game_mode': '对局模式', 'match_final': '终局',
    'node_seq_by_plane': '节点序列', 'pending_loss': '败态登记',
    'node_path': '节点路径', 'node_path_baseline': '节点路径基线',
    # 弹层选项域
    'supply': '补给', 'encounter': '遭遇',
    'supply_refresh_left': '补给刷新余量',
    'encounter_refresh_left': '遭遇刷新余量',
    'megastar_opts': '巨星候选', 'partner_opts': '伙伴候选',
    'fortune_opts': '命运候选', 'wish_trial_opts': '祈愿候选',
    'expert_invite': '专家邀请', 'box_card_names': '箱子牌名',
    'star_tome_opts': '星徽秘典候选',
    # 表格型键的标题(点分路径键,§4.2 未覆盖的复合键)
    'supply.options': '补给选项', 'encounter.options': '遭遇选项',
}

#: 局头 meta 键 → 显示标签(render-spec §2;键名闭集 = pipeline §6)。
META_LABELS: dict[str, str] = {
    'game_id': '对局', 'runs': '运行段', 'code_commit': '策略版本 commit',
    'registry_fingerprint': '注册表指纹', 'start_ts': '开始', 'end_ts': '结束',
}


# ---------------------------------------------------------------------------
# 基础渲染件
# ---------------------------------------------------------------------------


def _fmt(v: Any) -> str:
    """值 → 单行字符串(bool 中文化,容器压紧凑 json)。"""
    if isinstance(v, bool):
        return '是' if v else '否'
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, separators=(',', ':'))
    return str(v)


def _esc(s: str) -> str:
    """markdown 表格单元格转义(竖线是列分隔符,必须换掉)。"""
    return s.replace('|', '\\|').replace('\n', ' ')


def _short(v: Any, n: int = 48) -> str:
    """值 → 截断字符串(防长 payload 刷屏)。"""
    s = _fmt(v)
    return s if len(s) <= n else s[:n] + '…'


def field_cn(f: str) -> str:
    """field → 显示名「中文(英文)」:中文名便于理解,括号原字段名便于
    对照代码;chosen_* 前缀族 → 已选(各选项);未命中显原始字段名
    (开放词表禁猜,新字段先补 FIELD_CN_MAP 映射再上报告)。"""
    known = FIELD_CN_MAP.get(f)
    if known:
        return f'{known}({f})'
    if f.startswith('chosen_'):
        suffix = f[len('chosen_'):]
        return '已选(' + suffix + ')'
    return f


def action_cn(op: str) -> str:
    """回执动词 → 中文(开放词表未命中原样显示,禁猜)。"""
    return ACTION_WORD_MAP.get(op, op)


def _ts_num(ts: Any) -> float:
    """ts → 可比较数值(仅同档案内相对排序;不可解析 → 0 落最前)。"""
    s = str(ts or '').replace('-', '').replace('T', '').replace(':', '')
    try:
        return float(s)
    except ValueError:
        return 0.0


def _last_receipt(row: dict[str, Any]) -> dict[str, Any] | None:
    """receipts 锚行的最新动作(after 滚动窗末位;空窗/畸形 → None)。"""
    after = row.get('after')
    if isinstance(after, list) and after and isinstance(after[-1], dict):
        return after[-1]
    return None


def _settlement_brief(v: Any) -> str:
    """settlement 载荷 → 人读摘要(render-spec §3 键集;killed→胜负)。"""
    if not isinstance(v, dict):
        return _fmt(v)
    killed = v.get('killed')
    bits = ['胜' if killed is True else ('败' if killed is False else '—')]
    if v.get('hp_after') is not None:
        bits.append(f"血 {v['hp_after']}")
    if v.get('progress_delta') is not None:
        bits.append(f"进度 {v['progress_delta']:+d}")
    if v.get('gold') is not None:
        bits.append(f"金 {v['gold']}")
    if v.get('level') is not None:
        bits.append(f"等级 {v['level']}")
    if isinstance(v.get('xp'), (list, tuple)) and len(v['xp']) == 2:
        bits.append(f"经验 {v['xp'][0]}/{v['xp'][1]}")
    if v.get('streak_after') is not None:
        bits.append(f"连胜 {v['streak_after']}")
    return ' '.join(bits)


def _xp_brief(v: Any) -> str | None:
    """xp (已攒, 所需) → '已攒/所需'(§4.3;非二元形态 → None 不渲染)。"""
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return f'{v[0]}/{v[1]}'
    return None


def _delta_value_cell(f: str, v: Any) -> str:
    """变化表值单元格(人读摘要经 _value_brief;None → '—')。"""
    if v is None:
        return '—'
    return _esc(_value_brief(f, v))


def _unit_brief(u: Any) -> str:
    """单位 dict → '名★级'(§4.3;非 dict → 原样短串)。"""
    if not isinstance(u, dict):
        return _short(u, 20)
    name = str(u.get('char_id') or '?')
    star = u.get('star')
    return f'{name}{star}★' if star is not None else name


# ---------------------------------------------------------------------------
# 值人读摘要(render-spec §4.3:差分单元格与观察行共用;已知键出人读格式,
# 未知键回落截断 json——截断 payload 不是人读格式,新键先进 _VALUE_BRIEFS)
# ---------------------------------------------------------------------------


def _units_join(units: Any) -> str:
    """单位列表 → '名★级、…' / '(空)'。"""
    if not isinstance(units, list):
        return _short(units, 40)
    return '、'.join(_unit_brief(u) for u in units) if units else '(空)'


def _bench_brief(v: Any) -> str:
    """bench 槽位视图 → '爻光1★、三月七1★(空×6)'(unit 槽摘要 + 空槽计数)。"""
    if not isinstance(v, dict) or not isinstance(v.get('slots'), list):
        return _short(v, 40)
    units = [s.get('unit') for s in v['slots']
             if isinstance(s, dict) and s.get('kind') == 'unit']
    empties = sum(1 for s in v['slots']
                  if isinstance(s, dict) and s.get('kind') != 'unit')
    out = _units_join(units)
    return out + (f'(空×{empties})' if empties else '')


def _shop_brief(v: Any) -> str:
    """shop 载荷 → '椒丘1金、翡翠1金(空×2)'(content 摘要 + 空/识别失败计数)。"""
    if not isinstance(v, dict) or not isinstance(v.get('cards'), list):
        return _short(v, 40)
    names: list[str] = []
    empties = unknown = 0
    for s in v['cards']:
        kind = str(s.get('kind') or '') if isinstance(s, dict) else ''
        card = s.get('card') if isinstance(s, dict) else None
        if kind == 'content' and isinstance(card, dict):
            names.append(f"{card.get('name') or '?'}{card.get('cost')}金")
        elif kind == 'unknown':
            unknown += 1
        else:
            empties += 1
    out = '、'.join(names) if names else '(无内容)'
    if empties:
        out += f'(空×{empties})'
    if unknown:
        out += f'(识别失败×{unknown})'
    return out


def _board_brief(v: Any) -> str:
    """board → '仙舟×1、治疗×1' / '(空)'。"""
    if isinstance(v, dict) and v:
        return '、'.join(f'{k}×{n}' for k, n in v.items())
    return '(空)'


def _spheres_brief(v: Any) -> str:
    """spheres → '2 座(灰×2)'(points 为点击载荷不渲染)。"""
    if not isinstance(v, dict):
        return _short(v, 40)
    count = v.get('count')
    colors = v.get('colors') if isinstance(v.get('colors'), list) else []
    agg: dict[str, int] = {}
    for c in colors:
        agg[str(c)] = agg.get(str(c), 0) + 1
    detail = ','.join(f'{c}×{n}' for c, n in agg.items())
    n = count if count is not None else len(colors)
    return f'{n} 座' + (f'({detail})' if detail else '')


def _ore_rewards_brief(v: Any) -> str:
    """ore_rewards {坐标: 奖励} → '40,10=装备 轮滑鞋;50,10=角色 翡翠;70,10=金+3'。"""
    if not isinstance(v, dict):
        return _short(v, 40)
    if not v:
        return '(空)'
    bits: list[str] = []
    for coord, r in v.items():
        if not isinstance(r, dict):
            bits.append(f'{coord}={_short(r, 16)}')
            continue
        kind = str(r.get('kind') or '')
        if kind == 'gold':
            bits.append(f'{coord}=金+{r.get("gold")}')
        elif kind == 'equip':
            bits.append(f'{coord}=装备 {r.get("equip") or "?"}')
        elif kind == 'char':
            bits.append(f'{coord}=角色 {r.get("char") or "?"}')
        else:
            bits.append(f'{coord}={_short(r, 24)}')
    return ';'.join(bits)


def _node_path_brief(v: Any) -> str:
    """node_path → 'P1: —→奖励→战斗→…'(token 中文化,空档 —)。"""
    if not isinstance(v, dict):
        return _short(v, 40)
    seq = v.get('seq') if isinstance(v.get('seq'), list) else []
    tokens = []
    for s in seq:
        t = s.get('token') if isinstance(s, dict) else None
        tokens.append(NODE_KIND_CN.get(str(t), str(t)) if t else '—')
    plane = v.get('plane')
    head = f'P{plane}: ' if plane is not None else ''
    return head + ('→'.join(tokens) if tokens else '(空)')


def _node_brief(v: Any) -> str:
    """node → 'P1-R3 战斗'。"""
    if isinstance(v, dict):
        kind = str(v.get('kind') or '')
        return (f"P{v.get('plane')}-R{v.get('round_num')} "
                f"{NODE_KIND_CN.get(kind, kind or '?')}")
    return _short(v, 40)


def _deployed_brief(v: Any) -> str:
    """deployed → '前排 希儿1★;后排 藿藿1★、三月七1★'。"""
    if not isinstance(v, dict):
        return _short(v, 40)
    parts = []
    for label, key in (('前排', 'front_slots'), ('后排', 'back_slots')):
        slots = v.get(key)
        if isinstance(slots, list):
            parts.append(
                f'{label} {_units_join([u for u in slots if u is not None])}')
    return ';'.join(parts) if parts else _short(v, 40)


def _match_final_brief(v: Any) -> str:
    """match_final → 'stopped hp 84 金 31'(局终行摘要;全键见局头)。"""
    if not isinstance(v, dict):
        return _short(v, 40)
    hp = v.get('hp') if v.get('hp') is not None else '—'
    gold = v.get('gold') if v.get('gold') is not None else '—'
    return f"{v.get('final_type') or '—'} hp {hp} 金 {gold}"


def _scalar_list_brief(v: Any) -> str:
    """标量列表 → 顿号串(render-spec §4.3 通用兜底的具名形态)。"""
    if isinstance(v, list):
        return '、'.join(str(x) for x in v) if v else '(空)'
    return _short(v, 40)


def _occupied_equips_brief(v: Any) -> str:
    """occupied_equips {单位: [装备]} → '椒丘:轮滑鞋、钻头' / '(空)'。"""
    if isinstance(v, dict) and v:
        return '、'.join(f'{k}:{",".join(str(x) for x in eq)}'
                         for k, eq in v.items() if isinstance(eq, list))
    return '(空)'


def _node_seq_by_plane_brief(v: Any) -> str:
    """node_seq_by_plane {位面: token 列表} → 'P1: 奖励→…;P2: …'(token 中文)。"""
    if not isinstance(v, dict):
        return _short(v, 40)
    parts = []
    for plane, seq in v.items():
        tokens = [NODE_KIND_CN.get(str(t), str(t)) if t else '—'
                  for t in (seq if isinstance(seq, list) else [])]
        parts.append(f'P{plane}: ' + ('→'.join(tokens) if tokens else '(空)'))
    return ';'.join(parts) if parts else '(空)'


def _round_fresh_buys_brief(v: Any) -> str:
    """round_fresh_buys {phase: [位面,轮], names: [牌]} → 'phase[1,1]: 翡翠、三月七'。"""
    if not isinstance(v, dict):
        return _short(v, 40)
    phase = v.get('phase')
    names = v.get('names') if isinstance(v.get('names'), list) else []
    head = f'phase{list(phase) if isinstance(phase, list) else phase}: '
    return head + ('、'.join(str(x) for x in names) if names else '(无)')


def _pending_loss_brief(v: Any) -> str:
    """pending_loss {plane, round_num, node_type} → 'P1-R4 (battle)'。"""
    if not isinstance(v, dict):
        return _short(v, 40)
    plane = v.get('plane')
    rnd = v.get('round_num')
    pr = f'P{plane}-R{rnd}' if plane is not None and rnd is not None else '—'
    return f'{pr} ({v.get("node_type") or "?"})'


def _supply_brief(v: Any) -> str:
    """supply 载荷 → '0: +量产型装甲;1: 角色+装备(带钻)'(options 摘要)。"""
    opts = v.get('options') if isinstance(v, dict) else None
    if not isinstance(opts, list):
        return _short(v, 40)
    bits = []
    for i, o in enumerate(opts):
        if not isinstance(o, dict):
            bits.append(f'{i}: {_short(o, 20)}')
            continue
        equips = '+'.join([str(o.get('equip') or '?')]
                          + [str(x) for x in (o.get('extra_equips') or [])])
        char = str(o.get('char') or '')
        dia = '(带钻标)' if o.get('has_diamond') else ''
        body = f'{char}+{equips}{dia}' if char else f'{equips}{dia}'
        bits.append(f"{o.get('idx', i)}: {body}")
    return ';'.join(bits) if bits else '(空)'


#: field → 人读摘要函数(注册即生效;未注册键回落截断 json 并非人读格式)
_VALUE_BRIEFS: dict[str, Any] = {
    'bench': _bench_brief, 'deployed': _deployed_brief,
    'front_row': _units_join, 'back_row': _units_join,
    'board': _board_brief, 'spheres': _spheres_brief, 'shop': _shop_brief,
    'ore_rewards': _ore_rewards_brief, 'node_path': _node_path_brief,
    'node_path_baseline': _node_path_brief, 'node': _node_brief,
    'match_final': _match_final_brief, 'settlement': _settlement_brief,
    'xp': lambda v: (_xp_brief(v) or _short(v, 40)),
    'equips': _scalar_list_brief, 'active_strategies': _scalar_list_brief,
    'plane_bosses': _scalar_list_brief, 'enemy_affixes': _scalar_list_brief,
    'invest_env_opts': _scalar_list_brief,
    'invest_strategy_opts': _scalar_list_brief, 'planner_opts':
        _scalar_list_brief, 'box_card_names': _scalar_list_brief,
    'fortune_opts': _scalar_list_brief, 'megastar_opts': _scalar_list_brief,
    'partner_opts': _scalar_list_brief, 'wish_trial_opts':
        _scalar_list_brief, 'occupied_equips': _occupied_equips_brief,
    'node_seq_by_plane': _node_seq_by_plane_brief,
    'round_fresh_buys': _round_fresh_buys_brief,
    'pending_loss': _pending_loss_brief, 'supply': _supply_brief,
    'encounter': _supply_brief,
    'strategy_refresh_used': _board_brief,  # 卡名→已用次数,同名×n 形态
}


def _value_brief(f: str, v: Any) -> str:
    """field 值 → 人读单行摘要(差分单元格与观察行共用,§4.3;原样未转义——
    转义归出口:差分单元格经 _delta_value_cell,尾注经渲染期统一 _esc)。"""
    if v is None or v == '':
        return '—'
    fn = _VALUE_BRIEFS.get(f)
    if fn is not None:
        return str(fn(v))
    return _short(v, 60)


# ---------------------------------------------------------------------------
# 行加载与 --run 过滤(pipeline §1)
# ---------------------------------------------------------------------------


class _UsageError(Exception):
    """CLI 用法错误(退出码 2;message = stderr 文案)。"""


def load_archive_rows(game_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """--match:读档案切片(只读档案,不回退 live journal,design §2)。

    返回 (切片行, 档案 dict)。切片缺/档案缺/坏 → :class:`_UsageError`。
    """
    path = DEFAULT_MATCHES_DIR / f'match_{game_id}.json'
    if not path.exists():
        raise _UsageError(f'档案不存在: {path}')
    try:
        archive = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        raise _UsageError(f'档案不可读: {path}: {e}') from e
    if not isinstance(archive, dict):
        raise _UsageError(f'档案顶层非对象: {path}')
    slices = archive.get('slices')
    rows = slices.get(JOURNAL_REL) if isinstance(slices, dict) else None
    if not isinstance(rows, list):
        raise _UsageError(
            f'档案切片缺 {JOURNAL_REL} 键(装配产物不完整): {path}')
    return [r for r in rows if isinstance(r, dict)], archive


def load_journal_rows(path: Path) -> tuple[list[dict[str, Any]], JournalReadStats]:
    """--journal:宽容读裸 journal 文件(读入口单一源 = read_journal_stats)。

    接受标准布局文件 ``<根>/state/journal.jsonl`` 或其 state 上级目录;
    read_journal_stats 只认 ``<根>/state/journal.jsonl``,非标准文件名
    (同名解析后 ≠ 传入文件)拒绝——防静默读错文件。
    """
    root = path
    if path.is_file():
        if path.name != Path(JOURNAL_REL).name:
            raise _UsageError(
                f'--journal 需为标准布局 state/journal.jsonl: {path}')
        root = path.parent.parent  # <根>/state/journal.jsonl → replay 根
    elif not path.is_dir():
        raise _UsageError(f'--journal 路径不存在: {path}')
    rows, stats = read_journal_stats(root)
    return rows, stats


def filter_by_run(rows: list[dict[str, Any]], run_filter: str
                  ) -> list[dict[str, Any]]:
    """--run 过滤:run_id 精确匹配;未知值 → 用法错(语义变更已申报)。

    空 run_id 行(局外行)仅在 ts 落于切片首末行时间窗内时放行——窗取
    切片行首末行 ts,不取档案 start_ts/end_ts 元数据(pipeline 问题与约束)。
    """
    runs = {str(r.get('run_id') or '') for r in rows} - {''}
    if run_filter not in runs:
        raise _UsageError(
            f'--run {run_filter} 不在本数据的 run 集合内: {sorted(runs)}')
    ts_all = [str(r.get('ts') or '') for r in rows]
    lo, hi = min(ts_all), max(ts_all)
    out = []
    for r in rows:
        rid = str(r.get('run_id') or '')
        if rid:
            if rid == run_filter:
                out.append(r)
        elif lo <= str(r.get('ts') or '') <= hi:
            out.append(r)
    return out


# ---------------------------------------------------------------------------
# 策略遥测发现与加载(render-assembly §1)
# ---------------------------------------------------------------------------


def strategy_telemetry_path(explicit: str | None,
                            journal_root: Path | None) -> Path | None:
    """遥测路径解析:显式入参优先(文件/目录皆可;不存在 = 用法错);
    缺省探测 journal 同根 ``strategy/`` 目录(--journal = ``<根>/strategy/``;
    --match 无 journal 根 → live 根 = matches 目录父级)。目录不存在或无
    *.jsonl → None = 功能关闭(报告与现状零差异,局头亦不加行)。"""
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise _UsageError(f'--strategy-telemetry 路径不存在: {p}')
        return p
    if journal_root is None:
        return None
    d = journal_root / 'strategy'
    if not d.is_dir() or not any(d.glob('*.jsonl')):
        return None
    return d


def load_strategy_telemetry(path: Path,
                            run_ids: set[str]) -> StrategyTelemetry:
    """加载遥测 jsonl(文件入参 = 单文件;目录 = 全部 *.jsonl)并建索引。

    逐行 json.loads、非法行跳过不致命;``envelope.run_id`` ∉ 本局运行段
    (journal 行 run_id 集)的记录过滤丢弃(live 根多 run 段场景);按
    dtag 建动作级索引、按 (entry, node) 建章级索引(值保加载序 = dseq 序,
    章级 FIFO 分配序)。"""
    tele = StrategyTelemetry()
    files = [path] if path.is_file() else sorted(path.glob('*.jsonl'))
    seq = 0
    for fp in files:
        try:
            lines = fp.read_text(encoding='utf-8').splitlines()
        except OSError:
            continue   # 单文件不可读不致命(遥测是 best-effort 旁路数据)
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            env = obj.get('envelope')
            if not isinstance(env, dict):
                continue
            if str(env.get('run_id') or '') not in run_ids:
                continue
            dtag = str(env.get('dtag') or '')
            if not dtag:
                continue
            if dtag in tele.by_dtag:
                continue   # 重复 dtag 首现优先(dseq 唯一,重复 = 落盘重放形态)
            emitted = env.get('emitted')
            em0 = (emitted[0] if isinstance(emitted, list) and emitted
                   and isinstance(emitted[0], dict) else {})
            payload = obj.get('payload')
            node = env.get('node')
            rec = DecisionRecord(
                load_seq=seq, dtag=dtag,
                strategy_id=str(env.get('strategy_id') or ''),
                entry=str(env.get('entry') or ''),
                node=node if isinstance(node, dict) else None,
                emitted_op=str(em0.get('op') or ''),
                emitted_reason=str(em0.get('reason') or ''),
                emitted_route_tag=str(em0.get('route_tag') or ''),
                payload=payload if isinstance(payload, dict) else {})
            seq += 1
            tele.records.append(rec)
            tele.by_dtag[dtag] = rec
            if rec.node is not None:
                key = (rec.entry, rec.node.get('plane'),
                       rec.node.get('round_num'))
                tele.by_chapter.setdefault(key, []).append(rec)
    return tele


# ---------------------------------------------------------------------------
# 策略遥测两级 join(render-assembly §3)
# ---------------------------------------------------------------------------


def _target_chapters(report: Report, entry: str, plane: Any,
                     rnd: Any) -> list[Screen]:
    """(entry, node) → 候选章(章首现序):节点组 (plane, round_num) 匹配 ×
    章键(ENTRY_SCREEN_MAP)匹配。同 title 章相邻合并不影响多实例——
    备战→商店→备战是三次独立访问,FIFO 按章首现序分配。"""
    title = ENTRY_SCREEN_MAP.get(entry)
    if not title:
        return []
    out: list[Screen] = []
    for sec in report.sections:
        if (sec.node is None or sec.node.plane != plane
                or sec.node.round != rnd):
            continue
        out.extend(s for s in sec.screens if s.title == title)
    return out


def _join_strategy_telemetry(report: Report, tele: StrategyTelemetry) -> None:
    """两级 join(原地改 report 与 tele.unattached;render-assembly §3):

    1. 动作级(行 1-2):回执 dtag → record;op 经归一映射后与信封指纹
       比对,匹配 → 依据块挂动作节;失配/选择族 dtag 异常形态 → 回执按
       无依据处理 + 所在章尾「策略 dtag 失配」注记;
    2. 章级(行 3-14):同键多章 FIFO(records dseq 序对章首现序分配);
    3. 行 1-2 无回执匹配 → 锚章章尾「策略决策未落地」注记(无锚 → 未归属);
    4. 余量(node=null/无锚)→ 局头「未归属 M 条」计数面,不逐条展开。"""
    consumed: set[int] = set()
    for sec in report.sections:
        for scr in sec.screens:
            for act in scr.actions:
                for rcpt in act.chain:
                    dtag = str(rcpt.get('dtag') or '')
                    if not dtag:
                        continue   # 无 dtag 回执跳过
                    rec = tele.by_dtag.get(dtag)
                    if rec is None or rec.load_seq in consumed:
                        continue   # 陈旧 dtag 无 record = 无依据
                    consumed.add(rec.load_seq)
                    op = str(rcpt.get('op') or '')
                    if (rec.entry not in _ACTION_JOIN_ENTRIES
                            or _OP_NAME_NORMALIZE.get(op, op)
                            != rec.emitted_op):
                        scr.annots.append(f'策略 dtag 失配: {dtag}({op})')
                        continue
                    act.basis.append(rec)
    for (entry, plane, rnd), recs in tele.by_chapter.items():
        if entry in _ACTION_JOIN_ENTRIES:
            continue   # 两级互斥:行 1-2 不落章级小节(§3 适用集钉死)
        pending = [r for r in recs if r.load_seq not in consumed]
        if not pending:
            continue
        # strict=False 语义 = 章数与记录数可不等:记录多出章数(截断形态)
        # 的余量留未消费 → 未归属计数面;章多出记录 = 多余章无依据。
        for rec, scr in zip(pending, _target_chapters(report, entry,
                                                      plane, rnd),
                            strict=False):
            consumed.add(rec.load_seq)
            scr.strategy_records.append(rec)
    for rec in tele.records:
        if rec.load_seq in consumed or rec.entry not in _ACTION_JOIN_ENTRIES:
            continue
        node = rec.node or {}
        chapters = _target_chapters(report, rec.entry, node.get('plane'),
                                    node.get('round_num'))
        if not chapters:
            continue   # 无锚章 → 未归属计数面
        consumed.add(rec.load_seq)
        chapters[0].annots.append(
            f'策略决策未落地: {rec.dtag}({rec.emitted_op})')
    tele.unattached = [r for r in tele.records if r.load_seq not in consumed]


# ---------------------------------------------------------------------------
# 节点分组与无 node 行归属(pipeline §2/§3)
# ---------------------------------------------------------------------------


def node_kind_of(row: dict[str, Any]) -> str:
    """行内快照 node.kind(宽容:缺 → 空串,渲染 '?')。"""
    node = state_values(row).get('node')
    return str(node.get('kind') or '') if isinstance(node, dict) else ''


def has_screen_evidence(row: dict[str, Any]) -> bool:
    """画面证据 = current_screen 键在场 或 actor 命中注册表(pipeline §3)。"""
    if 'current_screen' in state_values(row):
        return True
    return str(row_sig(row).get('actor') or '') in ACTOR_REGISTRY


def _annex_brief(row: dict[str, Any]) -> str:
    """未归行清单条目摘要(防静默丢行:能定位到行即可)。"""
    return (f"{row.get('ts') or '—'} row={row_kind(row) or '?'} "
            f"field={row.get('field') or '—'} "
            f"actor={row_sig(row).get('actor') or '—'} "
            f"after={_short(row.get('after'), 60)}")


# ---------------------------------------------------------------------------
# 前值链(pipeline §5):全局 ts 序单遍预计算,与渲染分组解耦
# ---------------------------------------------------------------------------


class _ValueChain:
    """field → 最近一条写入行 after(宽容:行缺 after 时以行内快照回退入链)。"""

    def __init__(self) -> None:
        self._last: dict[str, Any] = {}

    def feed(self, f: str, row: dict[str, Any]) -> None:
        if 'after' in row:
            self._last[f] = row['after']
        else:
            v = state_values(row).get(f)
            if v is not None:
                self._last[f] = v

    def prev(self, f: str, row: dict[str, Any]) -> Any:
        """前值三级回退(pipeline §5):链值 → 本行快照 → None(起点)。"""
        if f in self._last:
            return self._last[f]
        return state_values(row).get(f)


def _precompute_prevs(rows: list[dict[str, Any]]) -> dict[int, Any]:
    """全局 ts 序单遍:变化行 idx → (前值, 前值来源为链)。

    前值来源两档(§5 修订):链值 = 本行之前最近同 field 写入行(真实前写入);
    快照回退 = 行内累计快照(必 ≥ 当前值,可能与 after 相等)。同值过滤只吃
    链档相等——快照档相等 = 该 field 视野内首写,渲染为 '(累计) → 值'。
    """
    chain = _ValueChain()
    prev_of: dict[int, Any] = {}
    for i, r in enumerate(rows):
        if row_kind(r) != ROW_WRITE:
            continue
        f = str(r.get('field') or '')
        if not f or f == 'receipts' or r.get('same_value') is True:
            continue
        is_plain_obs = (row_sig(r).get('family') == 'obs'
                        and f != 'settlement')
        if not is_plain_obs:  # 前值取「本行之前」的链,必须先查后喂
            prev = chain.prev(f, r)
            from_chain = f in chain._last
            prev_of[i] = (prev, from_chain)
        # obs 道不入变化表但仍是真值写入,进链(前值取「最近一条写入行」
        # 不分渠道,pipeline §5 字面)
        chain.feed(f, r)
    return prev_of


# ---------------------------------------------------------------------------
# 画面章切分 + 章内动作差分(pipeline §4/§5,单遍构建)
# ---------------------------------------------------------------------------


def _open_screen(spec: ScreenSpec, screen_id: str) -> Screen:
    return Screen(screen_id=screen_id, title=spec.title,
                  has_decision=spec.decision)


def _locate_screen(row: dict[str, Any], base: Screen | None,
                   cur: Screen | None) -> tuple[Screen, Screen | None, Screen,
                                                list[str]]:
    """一行 → (目标章, 新 base, 新 cur, 开章缺口注记)。规则见 pipeline §4。

    - settlement 写入 = 战斗结算证据(sim 无 current_screen 时的开章依据;
      live 数据 current_screen 行在先,本证据不触发),开/续战斗快照章;
    - 弹层行归属只认 actor 映射:命中即在对应弹层画面章(同章续,异章开新);
    - 画面域行(cs)分两形态(切章证据收窄,sim-screen-announce 迭代 §2.2.1):
      广播行(本行 ``field=='current_screen'``,漏斗/sim 广播写入行本体)=
      唯一切章锚——值 == base(最近快照章)→ 续开 base(弹层结束回底层),
      否则开新快照章(注册表命中;未注册 id 按原样开章 + 缺口);
      非广播行携带的快照 cs 一律只作归属,永不切章——有当前章挂当前章;
      无当前章(组首行)= 组边界基线,按快照 cs 开基线章(pipeline §4
      「组内首行恒开启一个画面章」;sim 广播节拍下组首陈值 cs 即引擎
      仍在屏的底层画面,占位清零的判据面);
    - 无画面证据:挂当前章;无当前章(组首行)→ 占位章 + 缺口。
    """
    actor = str(row_sig(row).get('actor') or '')
    spec = ACTOR_REGISTRY.get(actor)
    if spec is not None:
        if cur is not None and cur.screen_id == actor:
            return cur, base, cur, []
        scr = _open_screen(spec, actor)
        _fill_entry(scr, spec, row)
        return scr, base, scr, []
    vals = state_values(row)
    battle_id = '货币战争-战斗等待'
    if (row_kind(row) == ROW_WRITE
            and str(row.get('field') or '') == 'settlement'
            and not (cur is not None and cur.screen_id == battle_id)):
        s_spec = SCREEN_REGISTRY[battle_id]
        scr = _open_screen(s_spec, battle_id)
        _fill_entry(scr, s_spec, row)
        return scr, scr, scr, []
    is_cs_row = (row_kind(row) == ROW_WRITE
                 and str(row.get('field') or '') == 'current_screen')
    if is_cs_row or 'current_screen' in vals:
        cs = str((row.get('after') if is_cs_row
                  else vals['current_screen']) or '')
        if is_cs_row:
            # 广播行本体 = 唯一切章锚:值 == base → 续开 base(同值广播
            # same_value 行同径续开,不重开章)
            if base is not None and cs == base.screen_id:
                return base, base, base, []
        elif cur is not None:
            return cur, base, cur, []  # 非广播行:cs 只作归属,永不切章
        # cur 为 None(组首行)= 组边界基线:广播/归属形态同按 cs 开基线章
        s_spec = SCREEN_REGISTRY.get(cs)
        if s_spec is not None:
            scr = _open_screen(s_spec, cs)
            _fill_entry(scr, s_spec, row)
            return scr, scr, scr, []
        scr = _open_screen(ScreenSpec(cs), cs)  # 未注册 id:原样开章
        _fill_entry(scr, ScreenSpec(cs), row)
        note = f'缺口: 画面「{cs}」未注册(0 观察键集空,非决策面)'
        return scr, scr, scr, [note]
    if cur is not None:
        return cur, base, cur, []
    scr = _open_screen(ScreenSpec('(未观察)'), '(未观察)')
    note = '缺口: 画面证据缺失(无 current_screen/注册 actor),开占位章'
    return scr, base, scr, [note]


def _fill_entry(scr: Screen, spec: ScreenSpec, row: dict[str, Any]) -> None:
    """开章行快照 → 0 观察(∩ 注册键集,只显有值行)。"""
    scr.entry = _entry_pairs(state_values(row), spec.entry_fields)
    scr.entry_tables = _entry_tables(scr.entry, spec)


def _action_title(receipt: dict[str, Any]) -> str:
    """动作节标题摘要:action 载荷(名(费用金))> detail > 无(render-spec §4)。"""
    act = receipt.get('action')
    if isinstance(act, dict):
        card = act.get('card')
        name = ''
        cost: Any = None
        if isinstance(card, dict):
            name = str(card.get('name') or '')
            cost = card.get('cost')
        name = name or str(act.get('char_id') or '')
        if cost is None:
            cost = act.get('cost')
        if name:
            return f'{name}({cost}金)' if cost is not None else name
    detail = str(receipt.get('detail') or '')
    return _short(detail, 40) if detail else ''


def _consume_row(row: dict[str, Any], scr: Screen, opened: bool,
                 prev_of: dict[int, Any], idx: int, sec: Section) -> None:
    """单行入章:动作锚 / 状态变化 / 尾注(pipeline §5;render-spec §5)。

    ``sec`` = 所属章组(动作节章归属回搜与效果差分缓冲的承载面)。
    """
    kind = row_kind(row)
    if kind == ROW_OBS_EVENT:
        observed = row.get('observed')
        old = observed.get('old') if isinstance(observed, dict) else None
        new = observed.get('new') if isinstance(observed, dict) else None
        verdict = str(row.get('verdict') or '—')
        scr.annots.append(
            f"仲裁 {row.get('field') or '—'}: "
            f"{_short(old, 40)} → {_short(new, 40)}({verdict})")
        return
    if kind != ROW_WRITE:
        scr.annots.append(f'未知行型 row={kind or "?"} '
                          f"field={row.get('field') or '—'}(原样保留)")
        return
    f = str(row.get('field') or '')
    if not f:
        return
    if f == 'receipts':
        if row.get('same_value') is True:
            return  # no-op 整窗重写(pipeline §5:必须排除)
        rec = _last_receipt(row)
        if rec is None:
            scr.annots.append(f'缺口: 回执行 after 空/畸形(ts={row.get("ts")})')
            return
        pending = sec._pending_deltas
        op = str(rec.get('op') or '?')
        last = sec._last_action
        if (last is not None and last.chain
                and str(last.chain[-1].get('op') or '') == op
                and str(last.chain[-1].get('reason') or '')):
            # 重试链:连续回执同 op 且前条受阻(reason 非空)→ 合并一节
            # (判据 = 组内最近动作,跨章——回执按发出画面归章后,重试两脚
            # 可能异章落窗);链节吸收待认领效果写入
            last.chain.append(rec)
            last.deltas.extend(pending)
            pending.clear()
            return
        # extra 排除表保留 'applied'/'gold_delta' 键:旧 journal 历史回执
        # 含两键(applied 布尔/执行点金差证据腿均已退役),保留排除 = 旧
        # 数据不漏显;新数据无此键,保留零成本。
        extra = [(k, v) for k, v in rec.items()
                 if k not in ('op', 'applied', 'gold_delta', 'reason', 'detail',
                              'screen')]
        # 动作节章归属锚 = 回执 screen(动作发出画面,全回执域统一语义):
        # 转移类动作(如开商店)的回执在切屏写入行之后落窗,位置归属会把它
        # 记到变更后画面;按发出画面回搜本章组已开画面章归位。搜不到
        # (旧数据 screen=目标画面语义/画面章未开)→ 位置归属(当前章)。
        target = scr
        rscreen = str(rec.get('screen') or '')
        if rscreen and scr.screen_id != rscreen:
            for s in reversed(sec.screens):
                if s.screen_id == rscreen:
                    target = s
                    break
        act = Action(no=len(target.actions) + 1, op=op,
                     title=_action_title(rec),
                     reason=str(rec.get('reason') or ''),
                     detail=str(rec.get('detail') or ''),
                     screen=rscreen, extra=extra,
                     chain=[rec])
        target.actions.append(act)
        # 因果差分入账:本动作的效果写入(logic_action 家族)先于其回执
        # 落盘,此刻缓冲区 = 自上一回执以来的效果 → 尽数入本节
        act.deltas.extend(pending)
        pending.clear()
        sec._last_action = act
        return
    if row.get('same_value') is True:
        return  # no-op 写入零信息
    actor = str(row_sig(row).get('actor') or '')
    unreg = _is_unregistered_screen_actor(actor)
    if unreg:
        # 未注册画面 op(pipeline §4):不切分,记缺口待聚合尾注显影;
        # receipts 锚行是动作节机制不在此列(上文已 return)
        scr._unreg_counts[actor] = scr._unreg_counts.get(actor, 0) + 1
    family = str(row_sig(row).get('family') or '')
    is_hook = family == 'logic_hook'
    if family == 'obs' and f != 'settlement':
        # 观察道不入变化表(读数不是动作效果)。显影规则 = 画面 op 观察到
        # 什么,本章 0 观察就显什么:
        # - 开章行 = 快照承载,不入账;路由键/空值不入;
        # - 注册键 = 开章快照已显影,回读是重复显影,整条跳过;
        # - 非注册键 = 本章 0 观察动态段(首写定帧值);回读异值 → 章尾注记
        #   (对账纠偏/重观察回读的可见性保留)。
        if opened:
            return
        if f in _OBS_NOTE_SKIP:
            return
        after = row.get('after')
        if after in (None, ''):
            return
        brief = _value_brief(f, after)
        if f in _ALL_ENTRY_KEYS:
            return  # 注册键 = 开章快照已显影,观察回读是重复显影(§5 修订判据)
        if f not in scr._obs_entries:
            scr._obs_entries[f] = brief
            return
        key = (f, brief)
        if brief != scr._obs_entries[f] and key not in scr._obs_seen:
            scr._obs_seen.add(key)
            scr.annots.append(f'观察: {field_cn(f)}={brief}')
        return
    prev_pack = prev_of.get(idx)
    if isinstance(prev_pack, tuple):
        before, from_chain = prev_pack
    else:  # 非 变化行(obs/回执)不经此处;防御形态 = 无前值
        before, from_chain = prev_pack, prev_pack is not None
    delta = Delta(field=f, before=before, after=row.get('after'),
                  note='(效果钩子)' if is_hook else '', is_hook=is_hook)
    # 渲染同值过滤(§5 修订):链档(真实前写入行)前=后 = 零信息,计数进尾注;
    # 开章行豁免(章首写入行是本章证据本体);快照档相等 = 视野内首写,照常
    # 渲染并注 (前值=累计快照)——首写吞掉会让 overlay 候选/结算不显影
    # (sim 广播形态实测:invest_env_opts 首写曾被过滤)。
    cell_b = (_delta_value_cell(f, delta.before)
              if delta.before is not None else None)
    cell_a = _delta_value_cell(f, delta.after)
    if (from_chain and not opened
            and cell_b is not None and cell_b == cell_a):
        scr._same_skipped += 1
        return
    if not from_chain and cell_b is not None and cell_b == cell_a:
        delta.note = ((delta.note + ' ') if delta.note else '') + '(前值=累计快照)'
    if f == 'settlement':
        # 结算走章内变化块(render-spec §3 战斗章注册行:结算不入 0 观察,
        # 也不作动作效果挂动作节——它是结算读数)
        scr.trailing_changes.append(delta)
        return
    if unreg:
        # 未注册画面 op 的非 obs 行:一律走尾注显影(pipeline §4「挂当前
        # 画面章尾注 + 记缺口」),禁静默混入动作状态变化表
        return
    if family == 'logic_action':
        # 动作效果因果归属:效果写入先于其回执落盘 → 缓冲,待该动作回执
        # 行到达时入其动作节(修「效果显影滞后一节」);组尾无回执认领的
        # 由 _build_section 尾扫入章内变化块
        sec._pending_deltas.append(delta)
        return
    # 非 logic_action 非 obs 写入(效果钩子等派生事实):非动作因果 →
    # 挂组内最近动作节(无则章内变化块)
    if sec._last_action is not None:
        sec._last_action.deltas.append(delta)
    else:
        scr.trailing_changes.append(delta)  # 章内变化块(无锚前缀写入行)


def _opening_note(row: dict[str, Any]) -> str:
    """开局段无画面归属行 → 组级注记(pipeline §3 修订;空串 = 零信息跳过)。

    - 仲裁行 / 观察道写入 = 开局基线观察(全局首遍读数,非任何画面内容);
    - 其余写入 = 开局初始化(种子推导/对账/恢复等,写入者非注册画面 actor
      且行无 current_screen——粘进当前章会把对局元数据误记为画面效果);
    - CwScreen 前缀未注册写入者保留缺口显影(响亮暴露,不因换桶静默)。
    """
    kind = row_kind(row)
    actor = str(row_sig(row).get('actor') or '—')
    if kind == ROW_OBS_EVENT:
        observed = row.get('observed') if isinstance(row.get('observed'), dict) else {}
        return (f"仲裁 {row.get('field') or '—'}: "
                f"{_short(observed.get('old'), 40)} → "
                f"{_short(observed.get('new'), 40)}({row.get('verdict') or '—'})")
    if kind != ROW_WRITE:
        return ''
    f = str(row.get('field') or '—')
    if f == 'receipts' or row.get('same_value') is True:
        return ''
    if row.get('after') in (None, ''):
        # 空值/空串不入账(空值跳过防御:sim 广播对 prev_screen 首行
        # 空串是当前采集时序的实测形态,防时序变化出「字段=—」噪声行)
        return ''
    brief = _value_brief(f, row.get('after'))
    if _is_unregistered_screen_actor(actor):
        return f'缺口: 未注册写入者 {actor}: {field_cn(f)}={brief}'
    family = str(row_sig(row).get('family') or '')
    label = '开局基线观察' if family == 'obs' else '开局初始化'
    return f'{label}: {field_cn(f)}={brief}({actor})'


def _is_opening_unattributed(row: dict[str, Any]) -> bool:
    """开局段行是否无画面归属(归组级桶;判定 = 写入者非注册画面 actor 且
    行无 current_screen 证据;回执锚行恒走画面章动作节)。"""
    kind = row_kind(row)
    if kind == ROW_OBS_EVENT:
        return True
    if kind != ROW_WRITE:
        return False
    if str(row.get('field') or '') == 'receipts':
        return False
    actor = str(row_sig(row).get('actor') or '')
    return (actor not in ACTOR_REGISTRY
            and 'current_screen' not in state_values(row))


def _build_section(kind: str, node: NodeInfo | None,
                   rows: list[tuple[int, dict[str, Any]]],
                   prev_of: dict[int, Any]) -> Section:
    """一个组的画面切分 + 章内容构建(组首行恒开章,基线 = 组边界)。

    rows 元素 = (全局行序 idx, 行)——idx 是 _precompute_prevs 前值链的键。
    开局组(kind='open')的无画面归属行落组级注记桶(pipeline §3 修订),
    不参与画面章切分。
    """
    sec = Section(kind=kind, node=node)
    opening = kind == 'open'
    base: Screen | None = None
    cur: Screen | None = None
    for idx, r in rows:
        if opening and _is_opening_unattributed(r):
            note = _opening_note(r)
            if note:
                sec.opening_notes.append(note)
            continue
        cur, base, _, notes = _locate_screen(r, base, cur)
        opened = not any(s is cur for s in sec.screens)  # 身份比较(非 ==)
        if opened and sec.screens and sec.screens[-1].title == cur.title:
            # 相邻合并键 = title(sim-screen-announce §2.2.3):sim overlay
            # 相 = cs 广播行 + actor 行两形态并存,screen_id 异源(画面值 vs
            # actor 名)而 title 同 → 归一单章;非相邻不合并——备战→商店→
            # 备战是三次独立访问。前提 = 注册纪律「同 title 必须同规格」
            # (SCREEN_REGISTRY 注),合并沿用先开章规格。
            cur = sec.screens[-1]
            opened = False
        if opened:
            sec.screens.append(cur)
        cur.annots.extend(notes)
        _consume_row(r, cur, opened, prev_of, idx, sec)
    # 组尾扫尾:无回执认领的挂起效果写入(组末动作的效果在组边界前落盘、
    # 回执随节点翻转行归入下一组等形态)→ 最后画面章章内变化块(防静默
    # 丢行);挂起区跨章时归最后章(罕见形态,可见性优先于章精确)
    if sec._pending_deltas and sec.screens:
        sec.screens[-1].trailing_changes.extend(sec._pending_deltas)
    for s in sec.screens:
        # 未注册画面 op 聚合尾注(pipeline §4「挂尾注 + 记缺口」;同章同
        # actor 一条带计数,按 actor 名排序保确定性)
        for actor in sorted(s._unreg_counts):
            s.annots.append(
                f'缺口: 未注册写入者 {actor} '
                f'×{s._unreg_counts[actor]}(画面 op 未入渲染器注册表,'
                '行未切分;其非观察写入不入状态变化表)')
        s._unreg_counts = {}
    return sec


# ---------------------------------------------------------------------------
# 0 观察渲染中间体(render-spec §3/§4.3)
# ---------------------------------------------------------------------------


def _dig(values: dict[str, Any], path: str) -> Any:
    """点分路径取值('supply.options' → values['supply']['options'])。"""
    cur: Any = values
    for part in path.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _entry_pairs(values: dict[str, Any],
                 fields: tuple[str, ...]) -> list[tuple[str, Any]]:
    """0 观察 = 章首行快照 ∩ 注册键集,只显有值行(空串 = 语义空值,同跳)。"""
    out: list[tuple[str, Any]] = []
    for f in fields:
        v = _dig(values, f)
        if v is None or v == '':
            continue
        out.append((f, v))
    return out


def _shop_table(v: Any) -> tuple[list[str], list[list[str]]] | None:
    """商店牌面表(render-spec §3:槽/牌名/阵营/费用/星级;槽三态)。"""
    if not isinstance(v, dict) or not isinstance(v.get('cards'), list):
        return None
    rows: list[list[str]] = []
    for i, slot in enumerate(v['cards']):
        no = i + 1  # 槽 = ShopSlot 数组下标+1(1 基物理槽)
        kind = str(slot.get('kind') or '') if isinstance(slot, dict) else ''
        card = slot.get('card') if isinstance(slot, dict) else None
        if kind == 'content' and isinstance(card, dict):
            star = card.get('star')
            rows.append([str(no), _esc(str(card.get('name') or '?')),
                         _esc(str(card.get('faction') or '—')),
                         str(card.get('cost') if card.get('cost') is not None
                             else '—'),
                         f'{star}★' if star is not None else '—'])
        elif kind == 'unknown':
            rows.append([str(no), '识别失败', '', '', ''])
        else:
            rows.append([str(no), '空', '', '', ''])
    return (['槽', '牌名', '阵营', '费用', '星级'], rows)


def _bench_table(v: Any) -> tuple[list[str], list[list[str]]] | None:
    """备战席槽位表(§4.3:2 行×9 列横排——表头 = 槽号 1-9,数据行 = 内容;
    内容 = 名★级 / 空 / 道具名 / 未识别,四态同 ShopSlot 三态 + 道具名态:
    道具槽(slot.item 身份轴,授予名/识别钉名)渲染名字,旧档无名槽回退
    未识别)。竖排 9 行浪费版面,用户裁定横排;**备战席** 标题行已承载表
    语义,不设标签列。"""
    if not isinstance(v, dict) or not isinstance(v.get('slots'), list):
        return None
    slots: list[str] = []
    contents: list[str] = []
    for i, slot in enumerate(v['slots']):
        kind = str(slot.get('kind') or '') if isinstance(slot, dict) else ''
        unit = slot.get('unit') if isinstance(slot, dict) else None
        if kind == 'unit' and isinstance(unit, dict):
            content = _unit_brief(unit)
        elif kind == 'empty':
            content = '空'
        elif kind in ('supply_box', 'tome', 'bookcard') \
                and isinstance(slot, dict) and slot.get('item'):
            content = str(slot['item'])
        else:
            content = '未识别'
        slots.append(str(i + 1))
        contents.append(_esc(content))
    return (slots, [contents])


def _deployed_table(v: Any) -> tuple[list[str], list[list[str]]] | None:
    """上阵槽位表(2 行×N 列:行标签 前排/后排;列数 = max(前排, 后排)
    槽数,短行不足列补 —(无此槽);槽位 = 名★级(复用 _unit_brief,不另造
    格式化)/ null → 空)。前排 4 槽、后排随 back_layout 扩容,两行槽数
    不同是常态;前后排全空(开局帧)也照常出全「空」表,保持结构稳定。
    槽列表全缺失(载荷畸形)→ None,回落散列行渲染。"""
    if not isinstance(v, dict):
        return None
    front = v.get('front_slots')
    back = v.get('back_slots')
    front = front if isinstance(front, list) else None
    back = back if isinstance(back, list) else None
    if front is None and back is None:
        return None
    width = max(len(front or []), len(back or []))

    def _row(label: str, slots: list[Any] | None) -> list[str]:
        cells = [_esc(_unit_brief(u)) if u is not None else '空'
                 for u in (slots or [])]
        return [label] + cells + ['—'] * (width - len(cells))

    header = ['排'] + [str(i + 1) for i in range(width)]
    return (header, [_row('前排', front), _row('后排', back)])


def _options_table(v: Any, *, kind: str) -> tuple[list[str], list[list[str]]] | None:
    """选项面表(§4.3:encounter 行 = 难度N=奖励;supply 行 = 角色+装备组)。"""
    opts = v.get('options') if isinstance(v, dict) else None
    if not isinstance(opts, list):
        return None
    rows: list[list[str]] = []
    for i, o in enumerate(opts):
        if not isinstance(o, dict):
            rows.append([str(i + 1), _esc(_short(o, 40))])
            continue
        if kind == 'encounter':
            rewards = o.get('rewards')
            rw = '、'.join(str(x) for x in rewards) \
                if isinstance(rewards, list) else str(rewards or '—')
            rows.append([str(o.get('idx', i + 1)),
                         _esc(f"难度{o.get('difficulty')}={rw}")])
        else:
            equips = '+'.join([str(o.get('equip') or '?')]
                              + [str(x) for x in (o.get('extra_equips') or [])])
            char = str(o.get('char') or '')
            dia = '(带钻标)' if o.get('has_diamond') else ''
            rows.append([str(o.get('idx', i + 1)),
                         _esc(f'{char}+{equips}{dia}' if char
                              else f'{equips}{dia}')])
    return (['列', '内容'], rows)


def _entry_tables(entry: list[tuple[str, Any]], spec: ScreenSpec
                  ) -> list[tuple[str, list[str], list[list[str]]]]:
    """0 观察中的表格型键 → entry_tables(商品牌面/上阵/备战席/选项面)。

    表序随 entry 序:备战章 deployed 在 bench 前 → 上阵表天然紧贴备战席
    表前。上阵表只在与备战席表同章的画面(备战)生效——表格化的定位语义
    = 紧贴备战席表前对照;战斗章快照虽含 deployed(战斗阵容速览),维持
    散列行现状(非备战章不表格化)。"""
    out: list[tuple[str, list[str], list[list[str]]]] = []
    for f, v in entry:
        tbl: tuple[list[str], list[list[str]]] | None = None
        if f == 'shop':
            tbl = _shop_table(v)
        elif f == 'bench':
            tbl = _bench_table(v)
        elif f == 'deployed' and 'bench' in spec.entry_fields:
            tbl = _deployed_table(v)
        elif f == 'supply.options':
            tbl = _options_table(v, kind='supply')
        elif f == 'encounter.options':
            tbl = _options_table(v, kind='encounter')
        if tbl is not None:
            out.append((f, tbl[0], tbl[1]))
    return out


# ---------------------------------------------------------------------------
# 组装(pipeline §2/§3/§6)
# ---------------------------------------------------------------------------


def build_report(rows: list[dict[str, Any]], stats: JournalReadStats, *,
                 game_id: str, archive: dict[str, Any] | None = None,
                 strategy: StrategyTelemetry | None = None) -> Report:
    """排序行 → 渲染中间表示(纯函数,零文件 IO)。

    ``strategy`` = 已加载遥测索引(None/records 空 = 功能关闭);章组建完
    后跑两级 join(join 依赖最终章结构)。"""
    report = Report(stats=stats)
    ordered = sorted(rows, key=lambda r: str(r.get('ts') or ''))
    runs: list[str] = []
    for r in ordered:  # 行内 run_id 首现序去重(pipeline §6 meta runs)
        rid = str(r.get('run_id') or '')
        if rid and rid not in runs:
            runs.append(rid)
    report.meta = [
        ('game_id', game_id), ('runs', runs), ('start_ts',
                                               ordered[0].get('ts') if ordered else ''),
        ('end_ts', ordered[-1].get('ts') if ordered else ''),
    ]
    final = _match_final_of(ordered)
    for key, src in (('code_commit', 'code_commit'),
                     ('registry_fingerprint', 'registry_fingerprint'),
                     ('final_type', 'final_type'), ('final_plane', 'plane'),
                     ('final_round', 'round_num'), ('final_hp', 'hp'),
                     ('final_gold', 'gold'),
                     ('final_duration_s', 'duration_s')):
        report.meta.append((key, final.get(src) if final else None))
    if archive is not None and str(archive.get('continuity_note') or ''):
        report.meta.append(('continuity_note', archive['continuity_note']))

    if not ordered:
        if strategy is not None:
            report.strategy = strategy
            _join_strategy_telemetry(report, strategy)   # 无章可锚 → 全量未归属
        return report
    prev_of = _precompute_prevs(ordered)
    first_node_idx = len(ordered)
    for i, r in enumerate(ordered):
        if node_key_of(r) is not None:
            first_node_idx = i
            break
    # 组收集保留全局行序 idx(_precompute_prevs 前值链的键坐标系)
    open_rows: list[tuple[int, dict[str, Any]]] = []
    node_map: dict[tuple[int, int], list[tuple[int, dict[str, Any]]]] = {}
    unattached: list[tuple[int, dict[str, Any]]] = []
    for i, r in enumerate(ordered):
        key = node_key_of(r)
        if key is not None:
            node_map.setdefault(key, []).append((i, r))
        elif i < first_node_idx:
            open_rows.append((i, r))
        elif has_screen_evidence(r):
            unattached.append((i, r))
        else:
            report.annex_unattached.append(_annex_brief(r))
    if open_rows:
        report.sections.append(
            _build_section('open', None, open_rows, prev_of))
    for key in sorted(node_map):
        grp = node_map[key]
        kind_raw = node_kind_of(grp[0][1])  # kind 钉死组内首行(pipeline §2)
        node = NodeInfo(plane=key[0], round=key[1],
                        kind_cn=NODE_KIND_CN.get(kind_raw, kind_raw or '?'))
        report.sections.append(
            _build_section('node', node, grp, prev_of))
    if unattached:
        report.sections.append(
            _build_section('unattached', None, unattached, prev_of))
    if strategy is not None:
        report.strategy = strategy
        _join_strategy_telemetry(report, strategy)
    return report


def _match_final_of(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """渲染域内最后一条 match_final 写入行载荷(局头终局键来源)。"""
    out: dict[str, Any] = {}
    for r in rows:
        if row_kind(r) == ROW_WRITE and str(r.get('field') or '') == 'match_final':
            after = r.get('after')
            if isinstance(after, dict):
                out = after
    return out


# ---------------------------------------------------------------------------
# markdown 渲染(render-spec §1-§5)
# ---------------------------------------------------------------------------


def _entry_lines(entry: list[tuple[str, Any]],
                 tabular: frozenset[str] | set[str] = frozenset()
                 ) -> list[str]:
    """0 观察键值行(表格型键由 entry_tables 承载,此处跳过;tabular =
    已表格化字段名集——deployed 仅备战章表格化,未表格化章维持散列行)。"""
    out: list[str] = []
    for f, v in entry:
        if f == 'shop':
            probs = v.get('refresh_probs') if isinstance(v, dict) else None
            if isinstance(probs, dict) and probs:
                out.append('- 概率(refresh_probs) ' + '、'.join(
                    f'{k}→{int(round(float(n) * 100))}%'
                    for k, n in probs.items()))
            continue  # 牌面走 entry_tables
        if f in ('bench', 'supply.options', 'encounter.options'):
            continue  # 表格型,见 entry_tables
        if f == 'xp':
            xp = _xp_brief(v)
            if xp is not None:
                out.append(f"- {field_cn('xp')} {xp}")
                continue
        if f == 'deployed':
            if f not in tabular:
                out.extend(_deployed_lines(v))
            continue
        if f == 'board':
            if isinstance(v, dict) and v:
                out.append(f"- {field_cn('board')} "
                           + '、'.join(f'{k}×{n}' for k, n in v.items()))
                continue
        if f == 'spheres':
            line = _spheres_line(v)
            if line:
                out.append(line)
            continue  # 空观察(count/colors 全空)不渲染该行
        if f in ('equips', 'active_strategies') and isinstance(v, list):
            out.append(f'- {field_cn(f)} ' + ('、'.join(str(x) for x in v)
                                              if v else '(空)'))
            continue
        val = '—' if v == '' else _short(v, 80)  # 空串 = 语义空值
        out.append(f'- {field_cn(f)} {val}')
    return out


def _deployed_lines(v: Any) -> list[str]:
    """deployed → 前排/后排两行(§4.3;None/缺 → 不渲染该行)。"""
    if not isinstance(v, dict):
        return []
    out = []
    for label, key in (('前排(front_slots)', 'front_slots'),
                       ('后排(back_slots)', 'back_slots')):
        slots = v.get(key)
        if not isinstance(slots, list):
            continue
        units = [_unit_brief(u) for u in slots if u is not None]
        out.append(f'- {label} ' + ('、'.join(units) if units else '(空)'))
    return out


def _spheres_line(v: Any) -> str:
    """spheres → 'N 座(颜色×n,…)'(points 为点击载荷不渲染)。"""
    if not isinstance(v, dict):
        return ''
    count = v.get('count')
    colors = v.get('colors') if isinstance(v.get('colors'), list) else []
    if count is None and not colors:
        return ''
    agg: dict[str, int] = {}
    for c in colors:
        agg[str(c)] = agg.get(str(c), 0) + 1
    detail = ','.join(f'{c}×{n}' for c, n in agg.items())
    n = count if count is not None else len(colors)
    return f"- {field_cn('spheres')} {n} 座" + (f'({detail})' if detail else '')


def _kv_meta_lines(report: Report) -> list[str]:
    """局头 meta 逐行(render-spec §2;终局键合成一句;stats 独立行)。"""
    m = dict(report.meta)
    out = [f"- 对局: {m.get('game_id') or '—'}"]
    runs = m.get('runs')
    out.append('- 运行段: ' + ('、'.join(str(x) for x in runs) if runs else '—'))
    out.append(f"- 策略版本 commit: {m.get('code_commit') or '—'}")
    out.append(f"- 注册表指纹: {m.get('registry_fingerprint') or '—'}")
    out.append(f"- 时间窗: {m.get('start_ts') or '—'} ~ "
               f"{m.get('end_ts') or '—'}")
    has_final = any(m.get(k) is not None for k in
                    ('final_type', 'final_plane', 'final_round', 'final_hp',
                     'final_gold', 'final_duration_s'))
    if has_final:
        plane = m.get('final_plane')
        rnd = m.get('final_round')
        pr = f'P{plane}-R{rnd}' if plane is not None and rnd is not None else '—'
        dur = m.get('final_duration_s')
        dur_s = f'{float(dur):.0f}s' if isinstance(dur, (int, float)) else '—'
        out.append(f"- 终局: {m.get('final_type') or '—'} 位面 {pr}"
                   f" hp {m.get('final_hp') if m.get('final_hp') is not None else '—'}"
                   f" 金 {m.get('final_gold') if m.get('final_gold') is not None else '—'}"
                   f" 时长 {dur_s}")
    else:
        out.append('- 终局: —(无局终行)')
    st = report.stats
    if st.total_skipped == 0 and st.byte_repair_lines == 0:
        out.append('- 数据完整性: 无')
    else:
        out.append(f'- 数据完整性: 坏行 {st.bad_json_lines}'
                   f'/非对象 {st.non_dict_lines}'
                   f'/字节修复 {st.byte_repair_lines}')
    tele = report.strategy
    if tele is not None and tele.records:
        # 策略遥测行(render-assembly §4):无文件整行省略;未归属 > 0 时
        # 行尾追加计数(node=null/无锚记录,完整性申报面,不逐条展开)。
        ids = '、'.join(dict.fromkeys(
            r.strategy_id or '?' for r in tele.records))
        line = f'- 策略遥测: {ids} ({len(tele.records)} 条)'
        if tele.unattached:
            line += f'(未归属 {len(tele.unattached)} 条)'
        out.append(line)
    if m.get('continuity_note'):
        out.append(f"- 连续性注记: {m['continuity_note']}")
    return out


def _delta_table(deltas: list[Delta]) -> list[str]:
    """状态变化表(render-spec §4:| 字段 | 前 → 后 | 说明 |)。"""
    out = ['| 字段 | 前 → 后 | 说明 |', '|---|---|---|']
    for d in deltas:
        before = '(起点)' if d.before is None else _delta_value_cell(d.field, d.before)
        out.append(f'| {_esc(field_cn(d.field))} | {before} → '
                   f'{_delta_value_cell(d.field, d.after)} | {_esc(d.note)} |')
    return out


def _action_payload_brief(act: dict[str, Any]) -> str:
    """回执 action 载荷 → 人读摘要(BuyCard 形态 = 牌名(阵营,费用金,槽N) +
    char_id + reason;其余键回落短 json——载荷开放演化,新键显式加摘要)。"""
    bits: list[str] = []
    card = act.get('card') if isinstance(act.get('card'), dict) else None
    if isinstance(card, dict):
        bits.append(f"{card.get('name') or '?'}({card.get('faction') or '—'},"
                    f"{card.get('cost')}金,槽{card.get('slot') or '?'})")
    if act.get('char_id'):
        bits.append(f"char_id={act['char_id']}")
    if act.get('reason'):
        bits.append(f"reason={act['reason']}")
    rest = {k: v for k, v in act.items()
            if k not in ('card', 'char_id', 'reason', '__type__', 'route_tag')}
    if card is not None:
        rest.pop('cost', None)  # 费用已入卡片摘要,重复
    rest = {k: v for k, v in rest.items() if v not in ('', None)}
    if rest:
        bits.append(' '.join(f'{k}={_short(v, 20)}' for k, v in rest.items()))
    return ' · '.join(bits) or _short(act, 60)


def _basis_block(rec: DecisionRecord, head: str) -> list[str]:
    """一条决策记录 → 依据块行(通用键值渲染:dict 一层键值行、嵌套紧凑
    JSON;渲染器不解释语义——schema 归各策略文档。payload 空 = 单行占位)。
    ``head`` = 组首行前缀(动作级 '- 策略依据: ' / 章级 '- ')。"""
    attrs = [f'entry={rec.entry}', f'op={rec.emitted_op}']
    if rec.emitted_reason:
        attrs.append(f'reason={rec.emitted_reason}')
    if rec.emitted_route_tag:
        attrs.append(f'route_tag={rec.emitted_route_tag}')
    out = [f'{head}{_esc(rec.dtag)}({_esc(", ".join(attrs))})']
    if not rec.payload:
        out.append('  - payload: (本帧无策略载荷)')
        return out
    out.append('  - payload:')
    for k, v in rec.payload.items():
        out.append(f'    - {_esc(str(k))}: {_esc(_short(_fmt(v), 120))}')
    return out


def _render_action(act: Action) -> list[str]:
    """动作节(render-spec §4:标题 / 策略依据块 / 动作行 / extra 逐键 /
    变化表;依据块位置 = 标题行下、状态变化表前,按回执顺序逐条——
    render-assembly §3「依据随动作节(动作前)」)。"""
    out = [f'#### {act.no} {action_cn(act.op)}'
           + (f' {act.title}' if act.title else '')]
    for rec in act.basis:
        out += _basis_block(rec, '- 策略依据: ')
    for rec in act.chain:
        # 受阻判据 = reason 非空(受阻样式挂 reason;新回执无布尔键,旧
        # journal 的 applied 键由下方排除表吞掉不显影)。
        reason = str(rec.get('reason') or '')
        warn = '⚠ ' if reason else ''
        bits = []
        if reason:
            bits.append(f'reason={reason}')
        detail = str(rec.get('detail') or '')
        if detail:
            bits.append(f'detail={_esc(_short(detail, 90))}')
        screen = str(rec.get('screen') or '')
        if screen:
            bits.append(f'画面={screen}')
        if bits:
            out.append(f'- {warn}动作: ' + ' · '.join(bits))
        for k, v in rec.items():
            if k in ('op', 'applied', 'gold_delta', 'reason', 'detail',
                     'screen'):
                continue
            if k == 'action' and isinstance(v, dict):
                out.append(f'  - action: {_esc(_action_payload_brief(v))}')
                continue
            out.append(f'  - {k}: {_esc(_short(v, 90))}')
    if act.deltas:
        out.append('')
        out += _delta_table(act.deltas)
    return out


def _render_screen(prefix: str, scr: Screen) -> list[str]:
    """画面章:`#### 0 观察` → 动作节×N → `#### 章内变化` → 尾注 → 策略评价。"""
    out = [f'### {prefix} {scr.title}', '']
    out += ['#### 0 观察', '']
    obs = _entry_lines(scr.entry, {f for f, _, _ in scr.entry_tables})
    # 本章观察道写入动态段(首写帧值;注册键已由快照显影不在此列)
    obs += [f'- {field_cn(f)} {_esc(b)}' for f, b in scr._obs_entries.items()]
    if obs:
        out += obs
    else:
        out.append('(无)')
    for f, header, rows in scr.entry_tables:
        out += ['', f'**{field_cn(f)}**', '',
                '| ' + ' | '.join(header) + ' |',
                '|' + '---|' * len(header)]
        out += ['| ' + ' | '.join(r) + ' |' for r in rows]
    if scr.strategy_records:
        # 章级策略依据:0 观察后独立小节(render-assembly §3;选择族章 =
        # 「依据为观察后的独立小节」,不破坏「0 观察 → 动作×N → 策略评价」)
        out += ['', '#### 策略依据', '']
        for rec in scr.strategy_records:
            out += _basis_block(rec, '- ')
    for act in scr.actions:
        out += ['', *_render_action(act)]
    if scr.trailing_changes:
        out += ['', '#### 章内变化', '', *_delta_table(scr.trailing_changes)]
    if scr.annots:
        out.append('')
        out += [f'- {_esc(a)}' for a in scr.annots]
    if scr._same_skipped:
        out.append(f'- 同值写入 ×{scr._same_skipped} 略(前=后,零信息)')
    if scr.has_decision:
        out += ['', '#### 策略评价', '']
    out.append('')
    return out


def render_markdown(report: Report) -> str:
    """中间表示 → markdown 全文(render-spec §1 骨架)。"""
    gid = next((v for k, v in report.meta if k == 'game_id'), '?')
    parts = [f'# 货币战争复盘 {gid}', '', '## 局头', '']
    parts += _kv_meta_lines(report)
    parts.append('')
    if not report.sections and not report.annex_unattached:
        parts += ['> 无渲染行(journal 空或被 --run 过滤)。', '']
    for sec in report.sections:
        if sec.kind == 'open':
            if not sec.screens and not sec.opening_notes:
                continue
            parts += ['## 开局', '']
            for scr in sec.screens:
                parts += _render_screen('开局', scr)
            if sec.opening_notes:
                parts += ['### 开局初始化与基线观察', '']
                parts += [f'- {_esc(a)}' for a in sec.opening_notes]
                parts.append('')
        elif sec.kind == 'node':
            node = sec.node
            head = f'## 节点 {node.plane}-{node.round} {node.kind_cn}'
            parts += [head, '']
            for scr in sec.screens:
                parts += _render_screen(f'节点 {node.plane}-{node.round} '
                                        f'{node.kind_cn}', scr)
        else:
            parts += ['## 未归节', '']
            for scr in sec.screens:
                parts += _render_screen('未归节', scr)
    if report.annex_unattached:
        parts += ['## 未归行', '']
        parts += [f'- {a}' for a in report.annex_unattached]
        parts.append('')
    parts += ['## 复盘者附加', '']
    return '\n'.join(parts) + '\n'


# ---------------------------------------------------------------------------
# CLI(pipeline §7;design §2 契约)
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI 入口;退出码 0=成功 / 2=用法错误(档案缺/切片缺/--run 未知/
    --strategy-telemetry 路径不存在)。"""
    ap = argparse.ArgumentParser(
        description='货币战争 journal → markdown 复盘渲染器(journal 行模型版)')
    ap.add_argument('--match', default=None,
                    help='game_id:只读档案切片(不回退 live journal)')
    ap.add_argument('--journal', default=None,
                    help='裸 journal 文件(标准布局 <根>/state/journal.jsonl)'
                         '或其 state 上级目录')
    ap.add_argument('--game-id', default=None,
                    help='--journal 时的对局命名(缺省取路径祖父目录名)')
    ap.add_argument('--run', default=None, help='只渲染某段 run_id(精确匹配)')
    ap.add_argument('--strategy-telemetry', default=None,
                    help='策略遥测 jsonl 文件或目录(缺省探测 journal 同根 '
                         'strategy/;目录不存在或为空 = 功能关闭)')
    ap.add_argument('--out', default=None,
                    help=f'输出 markdown 文件(缺省 = {DEEP_REVIEW_DIR}/'
                         '<game_id>.md)')
    ap.add_argument('--stdout', action='store_true', help='打印不落盘')
    args = ap.parse_args(argv)

    try:
        if bool(args.match) == bool(args.journal):
            raise _UsageError('--match 与 --journal 必须二选一')
        archive: dict[str, Any] | None = None
        journal_root: Path | None = None
        if args.match:
            rows, archive = load_archive_rows(args.match)
            stats = JournalReadStats()
            game_id = args.match
            journal_root = DEFAULT_MATCHES_DIR.parent   # live 根(matches 父级)
        else:
            jpath = Path(args.journal or '')
            rows, stats = load_journal_rows(jpath)
            game_id = args.game_id or (
                jpath.parent.parent.name if jpath.is_file()
                else jpath.name) or 'journal'
            journal_root = jpath.parent.parent if jpath.is_file() else jpath
        if args.run:
            rows = filter_by_run(rows, args.run)
        # 策略遥测:发现 → 加载(run 过滤用本局运行段 = 过滤后行 run_id 集)
        tele: StrategyTelemetry | None = None
        tpath = strategy_telemetry_path(args.strategy_telemetry, journal_root)
        if tpath is not None:
            run_ids = {str(r.get('run_id') or '') for r in rows} - {''}
            tele = load_strategy_telemetry(tpath, run_ids)
    except _UsageError as e:
        print(f'({e})', file=sys.stderr)
        return EXIT_USAGE

    report = build_report(rows, stats, game_id=game_id, archive=archive,
                          strategy=tele)
    md = render_markdown(report)
    if args.stdout:
        sys.stdout.write(md)
        return 0
    out = Path(args.out) if args.out else DEEP_REVIEW_DIR / f'{game_id}.md'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding='utf-8')
    print(f'(已写出: {out} 共 {len(md.splitlines())} 行)', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
