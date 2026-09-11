"""货币战争配置。

策略层字段(faction/character/event 优先级等)= **meta 层,版本依赖**:游戏更新会改
阵营/角色/事件,最新数据**以米游社百科或游戏内图鉴为准**,本文件默认值仅是
2026-08 调研(`.debug/temp/currency_war/strategy_research.md`)的起步值,需随版本维护。
bot 运行时**以实机 OCR(左面板激活数、商店角色名)为真值**,本配置只做"偏好/tiebreaker"。
"""
from __future__ import annotations

from one_dragon.base.config.yaml_config import YamlConfig

# —— meta 默认值(2026-08 调研;版本更新后以米游社百科/游戏图鉴校准)——

# 成型快+稳的战力型阵营靠前(研究粗排:贝洛伯格/仙舟/盛会之星 > 巡海游侠/群攻 > 追击/狼狩)
DEFAULT_FACTION_PRIORITY: list[str] = [
    "贝洛伯格", "仙舟", "盛会之星", "昼之半神", "巡海游侠", "群攻", "追击", "狼狩",
]

# 万用核心角色(出现就抓,不限流派);费用据 cw_chars.CHARACTERS(单一源,plaza 对齐)
DEFAULT_CHARACTER_PRIORITY: list[str] = [
    # 5 费拼图(后期找)
    "昔涟", "云璃", "流萤",  # 流萤=5费(星核猎手/击破主 C)
    # 3-4 费核心辅助/主 C
    "星期日", "知更鸟", "白厄", "姬子·启行",  # 姬子·启行=3费(V4.4 列车同行核心)
    # 1-2 费前期基石(易升 3 星、成型快)
    "阿格莱雅", "藿藿", "桑博", "艾丝妲", "风堇", "卡芙卡",  # 藿藿=1费 / 卡芙卡=2费 / 风堇=2费
]

# 枚举合法值(构造时校验,typo/大小写错静默落入默认)—— 现无枚举字段;economy_mode 及其
# ALLOWED_ECONOMY 已删(node_plan spend_mode 全区间有主,config 档位是死配置)。

# boss 克制 = comp-vs-boss 机制级(comp.countered_by_bosses + boss_fit + task#73 机制建模),
# 非阵营级 —— 原 DEFAULT_BOSS_COUNTER(boss→降权阵营)错模型已删(decide_boss_priority 删时一并清)。

# 注:「净化身心克 DoT/减益」类游戏客观数据不进配置(配置=用户偏好单一职责)——
# 单一源在 cw_comps.MECHANIC_COUNTERS(经 AFFIX_MECHANIC_MAP 归一),cw_events decide_event 消费。
# 原 dot_punish_envs 配置字段已删(与注册表双源,且属版本一致的客观数据非用户偏好)。
# 保血阈值/难度阶梯(hp_safe_threshold/difficulty_hp_override)亦删:策略校准参数
# 归代码常量 cw_state.HP_SAFE_THRESHOLD / DIFFICULTY_HP_TABLE;economy_mode(死配置)/
# event_whitelist(引擎调参非用户偏好,priority/forbid 已覆盖)同批删。配置面单一源:
# docs/develop/sr_od/application/currency_war/config.md。


class CurrencyWarConfig(YamlConfig):
    """货币战争配置(入口流程 + 策略偏好)。

    策略字段都是 meta 层(版本依赖),默认值见模块顶部常量;用户可在 GUI 改,
    或版本更新后以米游社百科/游戏图鉴校准。bot 决策以实机 OCR 为主、本配置为偏好。
    """

    def __init__(self, instance_idx: int | None = None):
        YamlConfig.__init__(self, 'currency_war', instance_idx=instance_idx)
        # —— 入口/匹配(预留)——
        # —— 策略偏好(meta,版本依赖)——
        self.faction_priority: list[str] = self.get('faction_priority', DEFAULT_FACTION_PRIORITY)
        self.character_priority: list[str] = self.get('character_priority', DEFAULT_CHARACTER_PRIORITY)
        # 用户转向轴(config.md §3,用户 2026-08-17 确认全四类实体×三档):forbid 硬过滤 +
        # build_around 必含(cw_comps._passes_steering 读)+ priority 软加分(_priority_boost /
        # decide_event)。默认空 = 纯自适应。GUI setting card 待加(当前 yml 可改)。
        self.character_forbid: list[str] = self.get('character_forbid', [])
        self.character_build_around: list[str] = self.get('character_build_around', [])
        self.faction_forbid: list[str] = self.get('faction_forbid', [])
        # faction_build_around:必含阵营(成就局需要特定阵容,如 8减益 → ['减益'];
        # 多个 = 全部必含,all() 语义 —— 与角色轴 any() 不同:多羁绊成就要求同时在场)。
        self.faction_build_around: list[str] = self.get('faction_build_around', [])
        # 投资策略/环境轴(decide_event 消费:priority 加分/forbid 重罚;env 命中走 env 注册表归一)。
        self.strategy_priority: list[str] = self.get('strategy_priority', [])
        self.strategy_forbid: list[str] = self.get('strategy_forbid', [])
        self.env_priority: list[str] = self.get('env_priority', [])
        self.env_forbid: list[str] = self.get('env_forbid', [])
        # —— 开发/实验字段(不进未来 GUI,仅供 yml 调试)——
        # strategy_seed:策略内部 rng 种子(None=真随机、固定 int=A/B 复现调试)。
        # ⚠️ 只种子化策略内部蒙特卡洛 D 牌随机;游戏侧行局演化(发牌/boss/掉血)服务端决定,种子化不到。
        # strategy_id 合法值域(统一迁移批 ②:decision_v2 栈删除,值域收缩={'mandate_v1'};
        # 构造期前置校验,禁「运行拼错才炸」——存量 yml 写 'default' 会在配置
        # 加载时报错并给出迁移提示)
        strategy_id: str = self.get('strategy_id', 'mandate_v1')
        if strategy_id != 'mandate_v1':
            raise ValueError(
                f"currency_war.yml strategy_id='{strategy_id}' 非法:"
                "decision_v2 栈已随统一迁移批 ② 删除,合法值=mandate_v1(存量 yml 请改)"
                "(新核 cw4);请把实例配置里的 strategy_id 改为合法值")
        self.strategy_id: str = strategy_id
        # ev_arm 臂位(R1-1;三臂 A/B 实验设计的 mandate_v1 臂内实验因子,
        # 实验设计原文已删档,取回口径=ADR-0644——
        # skeleton_only=臂① EV 发射面旁路 / full=臂② 全开)。开发/实验
        # 字段(不进 GUI,仅 yml 调试);legacy 臂(decision_v2)不写该字段。
        ev_arm: str = self.get('ev_arm', 'full')
        if ev_arm not in ('skeleton_only', 'full'):
            raise ValueError(
                f"currency_war.yml ev_arm='{ev_arm}' 非法:"
                "合法值=skeleton_only/full(仅 mandate_v1 消费)")
        self.ev_arm: str = ev_arm
        self.strategy_seed: int | None = self.get('strategy_seed', None)
        # 可控轮数(单/多轮验证 + 采样本):跑完 N 轮停备战屏。None=跑到对局结束。
        # app._run_loop 透传给 CwLoop。
        _mr = self.get('max_rounds', None)
        self.max_rounds: int | None = int(_mr) if _mr not in (None, '', 0) else None
        # 简报 vs 实采对账开关(CwScreenPlaneIntel 采集完成后,逐位面 LCS 比对存证,
        # 不一致进 defect 台账;零决策行为)。默认开 = 验证期积累「简报 vs 真值」
        # 配对证据;稳态后可 yml 关掉。消费端 = cw_loop 实采块 + takeover 写回。
        self.briefing_reconcile: bool = self.get('briefing_reconcile', True)
        # 起局前置码哈希结构闸(ADR-0581,T-106 run6 混合码事故防线):工作树≠HEAD 拒绝
        # 起局。默认开 = 安全闸宁拦勿放;闸本体见 kernel/cw_code_hash_gate
        # (豁免名单/口径申报单一源 = ADR-0581 与闸模块 docstring)。
        self.code_hash_gate: bool = self.get('code_hash_gate', True)
        # (统一 state 影子开关已随删除波 1 销案——用户 2026-09-10 直迁
        #  裁定「journal 无条件常开,无开关」:装配段无条件武装
        #  install_state_telemetry,无影子期。yml 残留键无害,get 不再读。)
        # r347(旧路径删除):gate_* 4 flag 已删(对拍验证过,观测
        # gate 无条件化(对拍期已结束);yml 残留键无害,
        # get() 不再读)。

    def save(self) -> None:
        """持久化策略字段。"""
        self.data = {
            'faction_priority': self.faction_priority,
            'character_priority': self.character_priority,
            'character_forbid': self.character_forbid,
            'character_build_around': self.character_build_around,
            'faction_forbid': self.faction_forbid,
            'faction_build_around': self.faction_build_around,
            'strategy_priority': self.strategy_priority,
            'strategy_forbid': self.strategy_forbid,
            'env_priority': self.env_priority,
            'env_forbid': self.env_forbid,
            'strategy_id': self.strategy_id,
            'strategy_seed': self.strategy_seed,
            'ev_arm': self.ev_arm,
            # max_rounds(review C 附加发现 2026-08-16):save() 此前不含 → GUI 保存静默抹掉
            # 手写 yml 值(单/多轮验证配置丢失)。None 也要持久化(显式清空语义)。
            'max_rounds': self.max_rounds,
            'briefing_reconcile': self.briefing_reconcile,
            # code_hash_gate 也要持久化(同 max_rounds 先例):缺了则 GUI 保存
            # 静默抹掉 yml 手写的关闭值,闸被悄悄重新打开——配置丢失即行为漂移。
            'code_hash_gate': self.code_hash_gate,
            # (统一 state 影子开关键已随删除波 1 销案,save 不再写;yml 残留值无害。)
            # r347:gate_* flags 已删(无条件化),save 不再写。
        }
        YamlConfig.save(self)
