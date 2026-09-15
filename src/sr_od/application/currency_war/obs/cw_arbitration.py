"""观察层读数多源仲裁·统一注册面(15 号稿 §2.4,批 A)。

设计出处 = ``docs/develop/sr_od/application/currency_war/strategy-docs/15_observation_multisource_arbitration.md``
§2.2(量纲分类与泛化规则)/§2.4(统一注册面)。病灶 = 家族内六处成型仲裁各自
私写裁决规则/分歧带/留证键,判读侧要拼多文件才能回答「这个量现在怎么裁」;
本模块把「裁决规则 + 分歧带 + 分键」收敛为声明式注册表,证据通道**不新建**
——原始证据行仍走 ``kernel.cw_observe.obs_conflict``,不一致率分键仍走
``telemetry.defects``,注册面只统一「谁在什么键下调用它们」。

**批 A 严格零行为变更**:迁移语义不变性由对拍测试锁(注册面语义/迁移
对拍:deployed 全格对拍 + board 分歧帧×帧态矩阵)钉死;裁决值/schema/分键
锁死,obs_conflict 的 verdict 提示文本允许随迁移改写(A13 声明,对拍不锁)。

量纲四类(§2.2):count(计数,朝声明方向取值或弃权)/nominal(标称,优先级+
否决+帧态门)/scalar(连续标量,显式通道优先序)/layout(布局,实测>推导+
未知态)。hp/level 通道仲裁**暂不迁**(§5/§8⑥:先例最复杂迁移收益最低);
布局三信号归批 B,本模块先立 ``DIM_LAYOUT`` 与 unknown verdict 的注册面形态。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# ===== 量纲类常量(§2.2 四类;值即注册声明,判读按字符串聚合)=====

DIM_COUNT: str = 'count'
DIM_NOMINAL: str = 'nominal'
DIM_SCALAR: str = 'scalar'
DIM_LAYOUT: str = 'layout'

# ===== verdict 五态(§2.4)=====

VERDICT_OK: str = 'ok'                  # 双源齐且一致(带内零差)
VERDICT_NOISE: str = 'noise'            # 带内分歧(合法读数差,不行动不留证)
VERDICT_ARBITRATED: str = 'arbitrated'  # 真分歧,已按规则采信
VERDICT_REJECTED: str = 'rejected'      # 缺席源弃权(单源可用,另一源缺席)
VERDICT_UNKNOWN: str = 'unknown'        # 全源弃权(布局未知态等;批 B 主消费)


@dataclass(frozen=True)
class ArbitrationRule:
    """单量仲裁声明(§2.4 注册面 schema;对拍锁 schema 面)。

    - ``combine``:类内泛化规则的量实例(纯函数,``**readings`` 按源名传参),
      返回 ``(采信值, 是否真分歧)``;
    - ``band``:分歧带,带内 = 合法读数差(噪声,不行动不留证);
    - ``defect_kind``:不一致率分键(defects 台账 kind);
    - ``obs_field``:证据层 obs_conflict 的 field 键;
    - ``fail_closed_side``:计数/布局类必填的「廉价侧/弃权语义」声明 + 依据
      (防后人照抄 min;A14:弃权也是合法方向,如 cap 失读=拒信 None 门失效)。
    """
    key: str
    dim_class: str
    sources: list[str]
    combine: Callable[..., tuple[Any, bool]]
    band: float = 0
    defect_kind: str = ''
    obs_field: str = ''
    fail_closed_side: str = ''


_RULES: dict[str, ArbitrationRule] = {}


def register(rule: ArbitrationRule) -> None:
    """注册一条仲裁规则(同 key 覆盖 = 显式改声明;测试经 monkeypatch 清表)。"""
    _RULES[rule.key] = rule


def get_rule(key: str) -> ArbitrationRule | None:
    """取规则(消费方需要多产物裁决——如 board 的 merged+decisions——经本
    入口取 combine 直调;``arbitrate`` 只覆盖 (value, verdict, divergent)
    三元组形态)。"""
    return _RULES.get(key)


def registered_keys() -> list[str]:
    """已注册量键(分键互不混流锁的清点面)。"""
    return sorted(_RULES)


# ===== 裁决内核(迁移自私写法;批 A 前后逐字节等价,对拍钉死)=====

def combine_deployed_count(paddle_x: int | None,
                           cv_occupied: int | None) -> tuple[int | None, bool]:
    """deployed 计数双源仲裁内核(计数类;原 ``cw_observation.
    arbitrate_deployed_count`` 私写法原样迁入,规则依据见该函数 docstring
    ——取低值 fail-closed + spread>1 告警带,零新阈值)。"""
    if paddle_x is None and cv_occupied is None:
        return None, False
    if paddle_x is None:
        return cv_occupied, False
    if cv_occupied is None:
        return paddle_x, False
    return min(paddle_x, cv_occupied), abs(paddle_x - cv_occupied) > 1


def combine_board_frame_gated(badge_ocr: dict[str, int],
                              computed: dict[str, int],
                              prep_like: bool,
                              board_honest: bool) -> tuple[dict[str, int], list[tuple[str, str, bool]]]:
    """board 阵营计数帧态门仲裁内核(标称类②画面事实优先 + 帧态门,§1 行 8)。

    - computed(tracked 身份全集)= 底座;badge_ocr(可视区徽标 OCR)= 画面
      事实,分歧时备战帧覆写(W287 裁决翻转,ADR-0417);
    - 非备战帧/动画帧(``prep_like``/``board_honest`` 任一为假):双源皆不
      可信 → 不裁不覆保底座(W285 overlay 干扰 2/6 实证防新错);
    - badge 有 computed 无 = tracked 漏阵营(强信号),备战帧同样覆入。

    :return: ``(merged, decisions)``;decisions = ``[(faction, kind, take_badge)]``
        按 badge_ocr 迭代序,kind ∈ ``'ocr_only'``(badge 有 computed 无)/
        ``'count_mismatch'``(计数不等),take_badge = 该分歧是否覆写。
        留证(obs_conflict)由调用方按 decisions 发射(本内核纯裁决零副作用)。
    """
    merged = dict(computed)
    decisions: list[tuple[str, str, bool]] = []
    for faction, ocr_c in badge_ocr.items():
        calc_c = computed.get(faction)
        if calc_c is None:
            take = prep_like and board_honest
            decisions.append((faction, 'ocr_only', take))
            if take:
                merged[faction] = ocr_c
        elif calc_c != ocr_c:
            take = prep_like and board_honest
            decisions.append((faction, 'count_mismatch', take))
            if take:
                merged[faction] = ocr_c
    return merged, decisions


# ===== 注册表(批 A 迁移两量;fail_closed_side 依据均为已定谳实证)=====

register(ArbitrationRule(
    key='deployed_count',
    dim_class=DIM_COUNT,
    sources=['paddle_x', 'cv_occupied'],
    combine=combine_deployed_count,
    band=1,
    defect_kind='deployed_count_2src_divergence',
    obs_field='deployed_count_2src',
    fail_closed_side=('取低值 min:paddle=游戏计数器真值,CV 占用为像素推断;'
                      '高估→「板满」假判合法化 no-op 死锁(贵,实机停机局实证);'
                      '低估→多试一次拖拽被游戏拒(廉价)。分歧告警带 |Δ|>1 '
                      '沿用既有留证判据(spread≤1=合法读数差)'),
))

register(ArbitrationRule(
    key='board_faction_count',
    dim_class=DIM_NOMINAL,
    sources=['badge_ocr', 'computed'],
    combine=lambda badge_ocr, computed, prep_like, board_honest:
        _board_rule_combine(badge_ocr, computed, prep_like, board_honest),
    band=0,
    defect_kind='board_divergence',
    obs_field='board',
    fail_closed_side=('非备战帧/动画帧双源弃权,保 computed 底座(帧态门;'
                      'W285 overlay 干扰 2/6 实证);备战帧徽标覆写'
                      '(W287 裁决翻转:徽标=画面事实)'),
))


def _board_rule_combine(badge_ocr: dict[str, int], computed: dict[str, int],
                        prep_like: bool, board_honest: bool,
                        ) -> tuple[dict[str, int], bool]:
    """:func:`combine_board_frame_gated` 的 (value, divergent) 投影
    (arbitrate 三元组形态用;decisions 细节经 :func:`get_rule` 直调 combine
    的同内核获取)。divergent = 存在任一分歧 faction(无论是否覆写)。"""
    merged, decisions = combine_board_frame_gated(
        badge_ocr, computed, prep_like, board_honest)
    return merged, bool(decisions)


# ===== 统一裁决入口(§2.4)=====

def arbitrate(key: str, readings: dict[str, Any],
              ctx: Any = None) -> tuple[Any, str, bool]:
    """按注册规则裁决 → ``(采信值, verdict, 是否真分歧)``。

    - verdict 语义:双源齐且一致=ok;带内分歧=noise(调用方不行动不留证);
      带外分歧=arbitrated(调用方按键留证+分键);缺席源=rejected(单源
      可用,弃权声明生效);全源缺席=unknown(布局未知态等,批 B 主消费)。
    - ``ctx`` 预留(证据发射的帧上下文);批 A 证据发射仍在各消费点
      (行数/分键逐字节不变是验收第一判据),注册面统一发射点随批 B 收口。
    - 未注册 key → KeyError(禁静默:注册面漏登记要当场炸,不是退直调)。
    """
    rule = _RULES.get(key)
    if rule is None:
        raise KeyError(f'仲裁规则未注册: {key}(注册面漏登记)')
    value, divergent = rule.combine(**readings)
    present = {s: readings[s] for s in rule.sources
               if readings.get(s) is not None}
    if not present:
        verdict = VERDICT_UNKNOWN
    elif divergent:
        verdict = VERDICT_ARBITRATED
    elif len(present) < len(rule.sources):
        verdict = VERDICT_REJECTED
    elif len({repr(v) for v in present.values()}) > 1:
        verdict = VERDICT_NOISE
    else:
        verdict = VERDICT_OK
    return value, verdict, divergent
