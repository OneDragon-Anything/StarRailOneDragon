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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sr_od.application.currency_war.cw_chars import CHARACTERS
from sr_od.application.currency_war.cw_factions import FACTIONS
from sr_od.application.currency_war.cw_line_defs import _CORE_TRIO
from sr_od.application.currency_war.cw_system_cards import SYSTEM_CARDS
from sr_od.application.currency_war.cw_win_features import features_from_deployed

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
        bow: dict[str, int] = base['bow']
        th = {int(k): v for k, v in base['tier_hist'].items()}
        base.update({
            'star2_plus': sum(v for k, v in base['star_hist'].items()
                              if int(k) >= 2),
            'tier_sum': sum(k * v for k, v in th.items()),
            'n_tier1': th.get(1, 0),
            'n_tier2': th.get(2, 0),
            'engine_trio': sum(bow.get(c, 0) for c in _TRIO),
            'dot_pieces': sum(bow.get(c, 0) for c in _DOT_POOL),
            'seele': bow.get(_SEELE, 0),
        })
        return base

    def _vectorize(self, feats: dict[str, Any], node_type: str) -> list[float]:
        """特征 dict + node_type → 模型列序向量(round_num 缺省按 P1 均值 0)。"""
        assert self._cols is not None
        row = dict(feats)
        row['round_num'] = row.get('round_num', 0)
        for nt in _NODE_TYPES:
            row[f'nt_{nt}'] = 1 if node_type == nt else 0
        return [float(row.get(c, 0)) for c in self._cols]

    def predict(self, feats: dict[str, Any], node_type: str) -> dict[str, Any] | None:
        """影子预测:**不生效,只记录**——返回预测并落 shadow_log。

        本方法不被 sim 结算分派器调用(C7 验收边界④:win_model 上线前
        仅作离线分析件);返回 ``{'killed': bool, 'killed_prob': float}``
        供漂移监控对拍,无模型时返回 None。
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
        out = {'killed': prob >= 0.5, 'killed_prob': prob,
               'model_id': self.version.model_id, 'node_type': node_type}
        _MODEL_DIR.mkdir(parents=True, exist_ok=True)
        with _SHADOW_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps(out, ensure_ascii=False) + '\n')
        return out
