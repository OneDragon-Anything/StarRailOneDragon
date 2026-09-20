"""货币战争动作上报:投资确认(report_action_pick_invest_param)。

**零写族迁出·分步实现**(银狼闭环迭代 design.md §2.3,用户定稿):投资
选择上报自 ``zero_writes`` 迁出,按动作报告形态分步更新(每字段更新各落
一行遥测;单次动作报告多次写遥测 = 预期行为)。

**两相语义(效果腿幂等 = 证据闩,design §2.3①/对抗审③)**:投资屏重派
机制下动作 op 实例每派发新建、实例闩不设防——本函数按 ``evidence`` 分相:

- **发射相**(evidence 缺省,消费面 = ``CwActionPickInvestOp`` 机械链
  发出后):仅登记意图遥测(日志行;行级台账无「意图」行型,不强造),
  容器零写——确认未落地重走不重复;
- **落地相**(evidence = :data:`EVIDENCE_OVERLAY_CLOSED`,消费面 = 两屏
  handler 重入裁决出口「入口锚不在 = overlay 已关」):应用一次——
  第一步(仅策略屏)投资策略入 ``gs.active_strategies``(判重入表)+
  遥测一行;第二步按归一卡名分派效果函数(:data:`PICK_INVEST_EFFECTS`,
  容器写腿逐项落行);第三步随机腿走采样链逐步落行。

**双屏分流(对抗审②)**:``param.source`` = 发射屏别('strategy'/'portal')
——策略屏确认才入持卡面;portal 确认只走效果分派,禁入
``active_strategies``(防 portal 卡污染持卡经济聚合)。与现役 handler
确认三桥(STRATEGY_EFFECTS 经济聚合面 register_strategy/免费刷新
burst/board_rewrite)职责分离:本注册表只辖容器写腿,经济聚合照旧走
``active_strategies`` × ``cw_investments.STRATEGY_EFFECTS``,两表不合并。

动作上报函数族拆分件(每动作一文件;族规约 = 包 ``cw_action_report.
__init__`` docstring)。本包 → 容器单向依赖。
"""
from __future__ import annotations

import random
from collections.abc import Callable
from typing import Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    EQUIP_ACQUIRE_CONSEQUENCES,
    grant_bench_unit_cascade,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    LogicOutcome,
    _emit_defect,
    _validate_sig,
)

_PRODUCER = 'CwActionPickInvestParam'

#: 落地相证据值(handler 重入裁决出口传参;非空即视为落地)。
EVIDENCE_OVERLAY_CLOSED: str = 'overlay_closed'

#: 发射屏别词表(design §2.3 双屏分流;param.source 取值)。
PICK_INVEST_SOURCE_STRATEGY: str = 'strategy'
PICK_INVEST_SOURCE_PORTAL: str = 'portal'

# ===== 骇客改件采样(随机腿;collect_ore 范式:采样器常量面 + 披露键 +
# ===== rng 注入,实机缺省未播种 = 采样是猜测,sim 传流键 = 采样即世界真值)

#: 骇客改件 v0 池(卡文「获得1个随机4费骇客改件」的临时建模口径,用户
#: 拍定 = 4 费装备排除 Max 件)。**池数据缺口申报(对抗审⑧)**:
#: Equipment dataclass 无 cost 字段(实证),「4 费」口径无数据源 → 池 =
#: 硬编码名单常量,显式申报的第二真相源(名单即口径本体,披露键在册)。
#: 成员 = 银狼专属 10 件(data/cw_equipment_wear_rules_data.ITEM_WEAR_GATES
#: 键集)中名字不带 Max 后缀的 5 件。**诚实申报张力**:run_074040 实读
#: 改件 = 分身墨镜Max(属 Max 件),v0 池会猜错 → ``logic_rand_outcome``
#: 行收口兜底(不响安灯),池口径候校准批按 outcome 数据修订(与 R8 同证:
#: 「骇客改件」卡文口径 ≠ 注册表「骇客」类别,池非类别池)。
HACKER_MOD_POOL_V0: tuple[str, ...] = (
    '分身墨镜', '数据拷贝仪', '数据拷贝仪Pro', '病毒防火墙', '破解芯片',
)

#: 建模假设档披露键(在册落点 = 本常量,随局披露面消费;校准只改池常量
#: 与披露键、不动结构)。
HACKER_MOD_ASSUMPTION_KEYS: tuple[str, ...] = (
    'hacker_mod_pool_v0_cost4_no_max',
)

#: 骇客改件链翻来源域集(对抗审⑪:按「可能受影响域」裁,禁照抄 collect_ore
#: 全域——gold 不受改件影响不翻,防噪声行)。
_HACKER_MARK_DOMAINS: tuple[str, ...] = ('equips', 'bench', 'front_row',
                                         'back_row')


def roll_hacker_mod(rng: random.Random) -> str:
    """单次骇客改件身份采样(纯函数;rng 注入,sim/live 共用同一语义)。
    池 = :data:`HACKER_MOD_POOL_V0`(等概率均匀;分布形态未实测,披露键
    ``hacker_mod_pool_v0_cost4_no_max``)。"""
    return rng.choice(HACKER_MOD_POOL_V0)


# ===== 效果函数(确认落地分派面 = 容器写腿;键 = 注册表规范名)=====
# 注册纪律:效果函数只辖「确认落地后的容器写腿」(bench/装备/采样链),
# 与 cw_investments.STRATEGY_EFFECTS(持卡经济效果聚合,aggregate_economy
# 消费)职责不同不合并(对抗审⑨)。全量收录 = 推广批(design §1.4),
# 未收录卡只走第一步或零写(行为与迁移前一致 = 观察覆盖)。

#: 骇客专家:银狼 bench 腿的送出单位(卡文「获得专家顾问【银狼】」;
#: 星级未标 = 1★ 同句式先验,确定面语义——先验错 = 响停修因非随机)。
_HACKER_BENCH_GRANT: tuple[str, int] = ('银狼', 1)

#: 欢愉契约 immediate 腿的送出单位(cw_investments.ENV_GIFTS 欢愉契约行
#: chars_immediate 实证;1★ 口径同定谳 §2.2 数据拷贝仪Max 腿)。
_JOY_IMMEDIATE_GRANT: tuple[str, int] = ('银狼LV.999', 1)

#: 欢愉契约条件腿采证期临时翻来源闩的披露键 kind(design §2.7②:头号玩家
#: 触发无观察锚无采样模型,3.1① 定谳前触发帧收口自愈留证不停局;
#: **有界显式测量仪表,定谳后必须撤**——残留 = 临时闩未撤的显式信号)。
JOY_PROVISIONAL_KIND: str = 'joy_contract_provisional'


def _apply_effect_hacker_wolf(gs: GameState, *, sig: ChannelSig,
                              rng: random.Random) -> list[str]:
    """效果函数·骇客专家:银狼(策略卡参考实现;design §2.3/§2.4)。

    链序(逐步各落一行):
    1. **bench 腿**(确定性):银狼 1★ 入席 + 合成级联(涉 LV.999 级联
       自动走禁猜降级,见 merge_cascade_write);
    2. **商店池腿**(零容器写):银狼加入本局商店池——商店池无容器字段
       (逐帧观察为真值),遥测行申报(design §2.3「无容器字段则遥测行
       申报、零容器写」);
    3. **随机改件腿**(采样链):采样改件身份 → 装备入栏 → 命中后果表
       三件则链内应用获得后果(rand 通道)→ 级联;未写域按
       :data:`_HACKER_MARK_DOMAINS` 值不变翻来源(gold 不翻,对抗审⑪)。
    """
    steps: list[str] = []
    r = grant_bench_unit_cascade(gs, _HACKER_BENCH_GRANT[0],
                                 _HACKER_BENCH_GRANT[1], rand=False,
                                 evidence='pick_invest_hacker_bench',
                                 producer=_PRODUCER, sig=sig)
    steps.append(f'bench_grant:{_HACKER_BENCH_GRANT[0]}'
                 f'(placed={r.placed},merge={r.merge_steps})')
    _emit_defect(field_name='shop_pool', expected=None,
                 actual=f'{_HACKER_BENCH_GRANT[0]} 入商店池',
                 evidence='pick_invest_hacker_shop_pool', sig=sig,
                 kind='pick_invest_shop_pool_decl')
    steps.append('shop_pool_decl(零容器写)')
    # 随机改件腿(采样链;域守卫 = 未观察域跳写等观察,宁缺勿造)。
    mod = roll_hacker_mod(rng)
    written: set[str] = set()
    inv = gs.equips.value
    if inv is not None:
        gs.write_logic_rand(gs.equips, list(inv) + [mod],
                            produced_by=_PRODUCER,
                            evidence='pick_invest_hacker_mod', sig=sig)
        written.add('equips')
        steps.append(f'mod_equip:{mod}')
    else:
        steps.append(f'mod_sampled:{mod}(equips 未观察,入栏跳写)')
    if mod in EQUIP_ACQUIRE_CONSEQUENCES:
        c = grant_bench_unit_cascade(
            gs, EQUIP_ACQUIRE_CONSEQUENCES[mod][0],
            EQUIP_ACQUIRE_CONSEQUENCES[mod][1], rand=True,
            evidence=f'pick_invest_hacker_mod_{mod}', producer=_PRODUCER,
            sig=sig)
        if c.placed:
            written.update({'bench', 'front_row', 'back_row'})
        steps.append(f'mod_consequence:{mod}(placed={c.placed},'
                     f'merge={c.merge_steps})')
    # 未写域值不变翻来源(值不变标记对未知域无信息增益,同 collect_ore;
    # None 域跳写——随机态标记对「本就未知」的域无信息增益)。
    for dom in _HACKER_MARK_DOMAINS:
        if dom in written:
            continue
        fld = {'equips': gs.equips, 'bench': gs.bench,
               'front_row': gs.front_row, 'back_row': gs.back_row}[dom]
        if fld.value is None:
            continue
        gs.write_logic_rand(fld, fld.value, produced_by=_PRODUCER,
                            evidence=f'pick_invest_hacker_mark_{dom}',
                            sig=sig)
        steps.append(f'mark:{dom}')
    return steps


def _apply_effect_joy_contract(gs: GameState, *, sig: ChannelSig,
                               rng: random.Random) -> list[str]:
    """效果函数·欢愉契约(portal 卡参考实现;design §2.3/§2.7②)。

    - **immediate 腿**(确定性):银狼LV.999 1★ 入席 + 级联(chars_
      immediate 实证;涉 LV.999 级联自动走禁猜降级);
    - **条件腿**(头号玩家触发)= 采证期临时翻来源通道:bench/equips 值
      不变翻来源(披露键 :data:`JOY_PROVISIONAL_KIND`)→ 触发帧观察差异
      收口自愈留证不停局,多局拼数据;3.1① 定谳后撤闩换正式模型。
    """
    steps: list[str] = []
    r = grant_bench_unit_cascade(gs, _JOY_IMMEDIATE_GRANT[0],
                                 _JOY_IMMEDIATE_GRANT[1], rand=False,
                                 evidence='pick_invest_joy_immediate',
                                 producer=_PRODUCER, sig=sig)
    steps.append(f'immediate:{_JOY_IMMEDIATE_GRANT[0]}'
                 f'(placed={r.placed},merge={r.merge_steps})')
    _ = rng   # 采样链归 3.3 正式建模;本批无随机腿(参数位保留接口一致)
    for dom in ('bench', 'equips'):
        fld = gs.bench if dom == 'bench' else gs.equips
        if fld.value is None:
            continue
        gs.write_logic_rand(fld, fld.value, produced_by=_PRODUCER,
                            evidence='pick_invest_joy_provisional', sig=sig)
        steps.append(f'provisional_mark:{dom}')
    _emit_defect(field_name='bench', expected='joy_conditional_pending',
                 actual='joy_contract_provisional_flip',
                 evidence='pick_invest_joy_provisional', sig=sig,
                 kind=JOY_PROVISIONAL_KIND)
    return steps


PICK_INVEST_EFFECTS: dict[str, Callable[..., list[str]]] = {
    '骇客专家:银狼': _apply_effect_hacker_wolf,
    '欢愉契约': _apply_effect_joy_contract,
}
"""确认落地效果函数注册表(键 = 注册表规范名;与 STRATEGY_EFFECTS 职责
分离声明见模块头)。未收录名 = 零效果分派(只走第一步/零写)。"""


def _canon_invest_name(name: str) -> str:
    """归一卡名(分隔符形变归一 + 全角冒号→半角;注册表规范名键域)。"""
    from sr_od.application.currency_war.kernel.cw_investments import (
        normalize_invest_name,
    )
    canon = (name or '').replace('：', ':')   # OCR 全角冒号形变(骇客专家：银狼)
    return normalize_invest_name(canon)


def report_action_pick_invest_param(gs: GameState, param: Any, sig: ChannelSig,
                                    *, rng: random.Random | None = None,
                                    evidence: str = '') -> LogicOutcome:
    """投资确认上报(零写族迁出·分步实现;design §2.3 全表)。

    - **发射相**(evidence 缺省):意图遥测(日志),容器零写;
    - **落地相**(evidence = :data:`EVIDENCE_OVERLAY_CLOSED`):分步应用
      ——第一步仅策略屏(source='strategy')入持卡面(判重,归一名)+
      遥测一行;第二步效果分派(:data:`PICK_INVEST_EFFECTS`,未收录卡零
      效果);第三步随机腿采样链。portal(source='portal')禁入持卡面。
      source 缺省 ''(旧调用形态/未分流)= 零容器写,行为与迁移前一致;
    - 出参 applied=True = 动作受理(拒分支走落地相内域守卫,不整批拒)。
    """
    _validate_sig(sig, ('logic_action',))
    source = str(getattr(param, 'source', '') or '')
    canon = _canon_invest_name(str(getattr(param, 'norm_name', '') or ''))
    roll_rng = rng if rng is not None else random.Random()
    if evidence != EVIDENCE_OVERLAY_CLOSED:
        # 发射相:意图遥测(日志行;行级台账无意图行型,申报见模块头)。
        log.info('[cw-pick-invest] 意图遥测:source=%s name=%s idx=%s'
                 '(落地效果候证据闩)', source, canon,
                 getattr(param, 'idx', '?'))
        return LogicOutcome(applied=True, reason='intent_only')
    if not source:
        return LogicOutcome(applied=True, reason='landing_unrouted')
    steps: list[str] = []
    held = False
    if source == PICK_INVEST_SOURCE_STRATEGY:
        # 第一步:持卡面(判重入表;归一名落表,经济聚合读面免二次归一)。
        if canon:
            cur = list(gs.active_strategies.value or [])
            if canon not in cur:
                gs.write_logic(gs.active_strategies, cur + [canon],
                               produced_by=_PRODUCER,
                               evidence='pick_invest_strategy_held', sig=sig)
                held = True
                steps.append('active_strategies+1')
            else:
                steps.append('active_strategies:dup_skip')
    fn = PICK_INVEST_EFFECTS.get(canon)
    if fn is not None:
        steps.extend(fn(gs, sig=sig, rng=roll_rng))
    else:
        steps.append('effect:unregistered(观察覆盖)')
    log.info('[cw-pick-invest] 落地分步(source=%s name=%s): %s',
             source, canon, '; '.join(steps))
    return LogicOutcome(applied=True,
                        reason='landing_applied' if (held or steps) else
                        'landing_noop')
