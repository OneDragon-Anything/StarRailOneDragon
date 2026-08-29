"""货币战争 胜率模型 · 影子模式适配类(win_model M1,W30)。

契约 C7(``契约包_C1-C7.md`` §C7,草案级)接口形状落地:``WinModelVersion``
(version/model_id 字段)+ ``features`` / ``predict``。

**影子模式(本文件现状,硬边界)**:
- ``predict`` **不接任何 sim 结算路径**——不修改输入、不被结算分派器调用
  (sim 默认结算件仍是 Δ池回放);调用只把预测落 ``shadow_log`` 供离线
  对拍「模型预测 vs 实机结果」漂移监控(C7 消费方之三);
- 模型本体 = W30 训练的 P1 域 killed 分类探针(LR+L2,joblib,位于
  ``.debug/temp/currency_war/cw_dev/win_model_v0/``,gitignored 区);
  模型文件缺失时 ``available=False``,``predict`` 直接返回 None(不抛)。

标签源 = ``outcomes.killed``(实机结算真值,W23 定);特征集 fs1 见
``w30_meta.json`` 的 feature_cols(引擎数/板深/羁绊档位/node_type 先验)。
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_factions import FACTIONS
from sr_od.application.currency_war.kernel.cw_line_defs import _CORE_TRIO
from sr_od.application.currency_war.kernel.cw_system_cards import SYSTEM_CARDS
from sr_od.application.currency_war.telemetry.cw_win_features import (
    features_from_deployed,
)

#: 模型产物目录(W30 训练输出;gitignored,模型走运行时资产惯例不进 git)。
_MODEL_DIR = Path('.debug/temp/currency_war/cw_dev/win_model_v0')
_MODEL_PATH = _MODEL_DIR / 'w30_lr_killed.joblib'
_META_PATH = _MODEL_DIR / 'w30_meta.json'
_SHADOW_LOG = _MODEL_DIR / 'shadow_predictions.jsonl'

#: 引擎实体单一源(W47 统一化,原先三组具名字面量改 import/派生):
#: - 铁三角 = ``cw_line_defs._CORE_TRIO`` 注册表真值(注册表 import 不复制);
#: - DOT 件池 = ``FACTIONS['持续伤害']`` 成员的 ≤2 费子集(过渡件口径,
#:   海瑟音4/黑天鹅5 是终局件不进池);
#: - 希儿 = ``SYSTEM_CARDS['seele'].engine_required``(卡注册表)。
_TRIO = tuple(sorted(_CORE_TRIO))
_DOT_POOL = tuple(sorted(
    m for m in FACTIONS['持续伤害'].members()
    if m in CHARACTERS and CHARACTERS[m].cost <= 2))
_SEELE = SYSTEM_CARDS['seele'].engine_required[0]
_NODE_TYPES = ('普通战斗', '遭遇', 'boss')

# ── plaza 先验面样本权重口径(W495 逐篇语料接入,单一源)──────────────
#: 无 use 计数帖的基础权重(=遥测行权重 1,先验面最低话语权)。
PLAZA_BASE_WEIGHT: float = 1.0
#: 先验面份额:plaza 全量权重和归一到「等效遥测局数」的倍数。
#: =1.0 即先验面与遥测集同话语权(Beta 收缩 α=n 的等价量级,
#: 与 cw_coarse_battle.PLAZA_SHARE_MAX=0.25 的「先验不主导」精神一致
#: ——粗模型按单元封顶,影子模型按全集配平,都是防 784 篇生存者语料
#: 淹没带负样本的实机校准锚)。
PLAZA_PRIOR_FACE_N: float = 1.0


def plaza_sample_weight(use: int) -> float:
    """单篇 plaza 帖 → 原始样本权重(use 计数对数压缩;归一在训练侧做)。

    口径与边界:
    - ``use>0 → PLAZA_BASE_WEIGHT + ln(1+use)``——头部帖(万人使用)话语权
      高但被对数压扁:原值 use 可达数千,直接作权重会令先验面权重和
      超遥测集 4 个数量级,校准锚失效;ln(1+3000)≈8,压缩后头部/尾部
      权重比 ~8:1,保留「头部帖更可信」的排序而不淹没;
    - ``use<=0(无计数帖)→ PLAZA_BASE_WEIGHT``——仍是一条赢家结构样本,
      只取基础话语权。
    返回的是**原始权重**;训练消费前须经 :func:`plaza_prior_weights`
    按先验面份额归一,禁直接进 loss(否则份额口径漂移)。
    """
    u = max(int(use), 0)
    if u <= 0:
        return PLAZA_BASE_WEIGHT
    import math
    return PLAZA_BASE_WEIGHT + math.log1p(u)


def plaza_post_features(post: Any) -> dict[str, Any]:
    """单篇 plaza 帖明细(cw_plaza_posts.PlazaPost)→ 胜率模型特征行。

    特征面 = ``ShadowKilledModel.features`` 全量列(deployed 口径对齐:
    帖的 Final 阶段 units 逐个转 ``{char_id, star, equips}`` 后过
    ``features_from_deployed``)+ plaza 附加列:

    - ``plaza_use`` / ``plaza_weight_raw``:use 计数与原始权重
      (:func:`plaza_sample_weight`;归一在训练侧,见上);
    - ``n_carry``:Final carry 数(帖结构特征,通常 1);
    - ``n_labels`` / ``n_portals`` / ``n_augs``:节奏标签/门户/投资实选
      计数(密度代理;词表级 one-hot 留给 Phase B 特征条件化再升)。

    缺字段兜底:equips/traits 等元组缺省为空 → 对应计数自然为 0;
    注册表外角色名由 ``unknown_char_count`` 披露(不抛、不猜),与实机
    OCR 识别形变残留同口径。**标签恒为胜**(赢家发帖,生存者偏差——
    本函数不产标签,训练侧固定 y=1,声明见 cw_plaza_posts docstring)。
    """
    eq_map = dict(post.equips)
    deployed = [
        {'char_id': name, 'star': star, 'equips': list(eq_map.get(name, []))}
        for name, star, _cost, _pos, _is_carry in post.units
    ]
    base = features_from_deployed(deployed)
    feats = dict(_engine_columns(base))
    feats.update({
        'plaza_use': int(post.use),
        'plaza_weight_raw': plaza_sample_weight(post.use),
        'n_carry': len(post.carries),
        'n_labels': len(post.labels),
        'n_portals': len(post.portals),
        'n_augs': len(post.augs),
    })
    return feats


def _engine_columns(base: dict[str, Any]) -> dict[str, Any]:
    """基础特征 dict → 追加引擎覆盖度派生列(单一源,features() 共用)。

    engine_trio/dot_pieces/seele 实体出处见模块头「引擎实体单一源」注释。
    """
    bow: dict[str, int] = base['bow']
    th = {int(k): v for k, v in base['tier_hist'].items()}
    return {
        **base,
        'star2_plus': sum(v for k, v in base['star_hist'].items() if int(k) >= 2),
        'tier_sum': sum(k * v for k, v in th.items()),
        'n_tier1': th.get(1, 0),
        'n_tier2': th.get(2, 0),
        'engine_trio': sum(bow.get(c, 0) for c in _TRIO),
        'dot_pieces': sum(bow.get(c, 0) for c in _DOT_POOL),
        'seele': bow.get(_SEELE, 0),
    }


def plaza_prior_weights(feats_rows: list[dict[str, Any]],
                        n_telemetry: int) -> list[float]:
    """plaza 特征行集 → 归一后样本权重(先验面份额口径)。

    全集权重线性缩放到 ``PLAZA_PRIOR_FACE_N * n_telemetry``——先验面与
    遥测集的话语权比固定,内部相对排序(头部帖对数压缩)不变;行内
    权重和为 0 的退化输入(空集)原样返回空表。
    """
    raw = [float(r.get('plaza_weight_raw', PLAZA_BASE_WEIGHT)) for r in feats_rows]
    total = sum(raw)
    if total <= 0 or not raw:
        return raw
    scale = PLAZA_PRIOR_FACE_N * max(int(n_telemetry), 1) / total
    return [w * scale for w in raw]


#: 概率再校准(Platt scaling)的 clip 下/上界:logit 变换前夹住概率,
#: 防 p=0/1 的 ±inf(遥测锚里均衡 LR 输出极端值的行会被 clip 而非爆掉)。
_PLATT_PROB_EPS: float = 1e-6


@dataclass(frozen=True)
class PlattCalibrator:
    """Platt 概率再校准层:``p → sigmoid(a·logit(p) + b)``。

    设计(为什么是 Platt 而非温度缩放):W495 影子对拍实测的失真形态是
    「排序能力好、概率整体下压、高分段欠冲且对先验面份额不敏感」——
    偏移主导 + 尺度分量并存,单参数温度缩放(1/T)表达不了纯偏移;
    Platt 双参数严格包含温度缩放为特例(a=1/T, b=0),故选 Platt。

    拟合纪律(硬边界):参数只允许由 ``fit_platt_scaling`` 在**带负样本的
    遥测锚**上拟合;plaza 先验面是恒胜标签的生存者语料,禁参与拟合
    (否则校准学到的只是先验面的分布,不是实机校准)。

    默认参数 ``a=1, b=0`` = 恒等映射,``apply`` 对任意 p 逐位不变——
    校准层关闭态的零漂移锚。
    """

    a: float = 1.0
    b: float = 0.0

    def apply(self, prob: float) -> float:
        """单点概率过校准;输入越界或非有限时原样返回(不做静默修正)。"""
        p = float(prob)
        if not (0.0 <= p <= 1.0) or not math.isfinite(p):
            return p
        if self.a == 1.0 and self.b == 0.0:
            return p  # 恒等短路:数值与语义双零漂移
        z = math.log(p / (1.0 - p)) if 0.0 < p < 1.0 else (
            -742.0 if p == 0.0 else 742.0)  # float64 logit 极限,防 overflow
        return 1.0 / (1.0 + math.exp(-max(min(self.a * z + self.b, 742.0),
                                          -742.0)))


def fit_platt_scaling(y_true: list[int], probs: list[float]) -> PlattCalibrator:
    """在遥测锚上拟合 Platt 校准参数(纯函数:只读入参,零 IO,零随机)。

    模型:一维 logistic 回归 ``P(y=1) = σ(a·logit(p) + b)``,拟合器 =
    sklearn LogisticRegression(近无正则 C=1e6,lbfgs 确定性求解,
    不传 random_state——同入参必同参,可锁)。输入要求:
    - ``y_true`` 含 0/1 两类且与 ``probs`` 等长、非空(单类/退化输入无法
      定偏移与尺度,原样返回恒等 = 校准层自动降级关闭,不抛);
    - ``probs`` 越界/非有限行直接剔除后再拟合(与 ``apply`` 的防御同口径)。

    返回的校准器默认可直接过 ``PlattCalibrator.apply``;调用方负责保证
    probs 来自**带负样本的遥测锚**(survivorship 面禁入,见类 docstring)。
    """
    # strict=True:锚行数不齐是调用方错误,宁可炸不可静默截断负样本
    pairs = [(float(p), int(y)) for p, y in zip(probs, y_true, strict=True)
             if 0.0 <= float(p) <= 1.0 and math.isfinite(float(p))
             and int(y) in (0, 1)]
    if not pairs:
        return PlattCalibrator()
    ys = [y for _, y in pairs]
    if len(set(ys)) < 2:
        return PlattCalibrator()
    z = []
    for p, _ in pairs:
        pc = min(max(p, _PLATT_PROB_EPS), 1.0 - _PLATT_PROB_EPS)
        z.append(math.log(pc / (1.0 - pc)))
    # 重依赖懒加载(与 predict 的 joblib 同纪律):本模块被影子面外的
    # 代码 import,不在模块顶挂 numpy/sklearn。
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    lr = LogisticRegression(penalty='l2', C=1e6, max_iter=2000, tol=1e-8,
                            solver='lbfgs')
    lr.fit(np.array(z).reshape(-1, 1), np.array(ys))
    return PlattCalibrator(a=float(lr.coef_[0][0]), b=float(lr.intercept_[0]))


@dataclass(frozen=True)
class WinModelVersion:
    """C7 版本指纹(接口形状冻结;标签源可替换位=label_source)。"""

    model_id: str
    feature_set: str
    trained_on: str
    label_source: str


class ShadowKilledModel:
    """W30 P1 域 killed 分类探针的影子模式包装(C7 接口形状)。

    用法(仅离线分析/漂移监控,不进结算路径):
        model = ShadowKilledModel()
        feats = model.features(deployed)          # deployed → 特征向量
        outcome = model.predict(feats, 'boss')    # 预测 + 落 shadow_log
    """

    def __init__(self) -> None:
        self.version = self._load_version()
        self._model: Any = None
        self._cols: list[str] | None = None

    @staticmethod
    def _load_version() -> WinModelVersion:
        if _META_PATH.exists():
            meta = json.loads(_META_PATH.read_text(encoding='utf-8'))
            return WinModelVersion(
                model_id=meta.get('model_id', 'unknown'),
                feature_set=f"fs1:{len(meta.get('feature_cols', []))}cols",
                trained_on=meta.get('trained_on', 'unknown'),
                label_source=meta.get('label_source', 'unknown'),
            )
        return WinModelVersion('unavailable', 'fs1', '', '')

    @property
    def available(self) -> bool:
        """模型文件是否就位(缺失=影子件静默降级,不影响任何调用方)。"""
        return _MODEL_PATH.exists() and _META_PATH.exists()

    def features(self, deployed: list[dict]) -> dict[str, Any]:
        """战前上场名单 → 特征向量(C7 features 契约的 deployed 输入形态)。

        输出 = ``features_from_deployed`` 全量特征 + 引擎覆盖度派生列
        (engine_trio/dot_pieces/seeile 见模块头单一源注释)。
        node_type 不在此(训练表侧 join 的先验,``predict`` 单独收)。
        """
        base = features_from_deployed(deployed)
        return _engine_columns(base)

    def _vectorize(self, feats: dict[str, Any], node_type: str) -> list[float]:
        """特征 dict + node_type → 模型列序向量(round_num 缺省按 P1 均值 0)。"""
        assert self._cols is not None
        row = dict(feats)
        row['round_num'] = row.get('round_num', 0)
        for nt in _NODE_TYPES:
            row[f'nt_{nt}'] = 1 if node_type == nt else 0
        return [float(row.get(c, 0)) for c in self._cols]

    def predict(self, feats: dict[str, Any], node_type: str,
                calibrator: PlattCalibrator | None = None) -> dict[str, Any] | None:
        """影子预测:**不生效,只记录**——返回预测并落 shadow_log。

        本方法不被 sim 结算分派器调用(C7 验收边界④:win_model 上线前
        仅作离线分析件);返回 ``{'killed': bool, 'killed_prob': float}``
        供漂移监控对拍,无模型时返回 None。

        ``calibrator``:可选 Platt 校准层(:func:`fit_platt_scaling` 的产物,
        只许遥测锚拟合);默认 None = 不校准,与未引入校准层前的行为
        逐一相同(概率/阈值/日志全零漂移)。传入恒等参数
        ``PlattCalibrator()`` 同样零漂移。
        """
        if not self.available:
            return None
        if self._model is None:
            import joblib
            self._model = joblib.load(_MODEL_PATH)
            meta = json.loads(_META_PATH.read_text(encoding='utf-8'))
            self._cols = meta['feature_cols']
        prob = float(self._model.predict_proba(
            [self._vectorize(feats, node_type)])[0][1])
        if calibrator is not None:
            prob = calibrator.apply(prob)
        out = {'killed': prob >= 0.5, 'killed_prob': prob,
               'model_id': self.version.model_id, 'node_type': node_type}
        _MODEL_DIR.mkdir(parents=True, exist_ok=True)
        with _SHADOW_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps(out, ensure_ascii=False) + '\n')
        return out
