"""遗器对账报告器:常量 RELIC_SETS × 国内 content_id × 国际服 en/id 映射,stdout 报告零落盘。

中间权威表 JSON 已废除(2026-11-12):原产出 references/relics-full.json 无人程序化
消费(纯人工审阅用),现改为直接对账报告——relic 常量是手工维护流程,报告喂人工改常量。

输入(先跑同目录两个 fetch 脚本刷新):
  .debug/game_data/relic/wiki/cnwiki_relic_list.json     国内 channel 30 列表
  .debug/game_data/relic/wiki/hoyowiki_relic_id_map.json 国际服 zh/en 互连映射

报告内容(项目根目录运行):
    uv run python skills/sr-od-dev-relic-data/scripts/build_relic_authority_table.py
  - 常量每条 vs 两侧 wiki 的对账结果(source=wiki/manual、en/id 回填情况、译名别名)
  - 输入侧未消费词条 = 常量缺失或撞键,人工按报告补常量(§1 步骤 3-4)

挂接架构见 skill SKILL.md §2(id 是中枢键,两源只在 id 上会合)。
仅标准库,项目根目录运行。
"""
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # Windows 控制台默认 GBK,中文输出会乱码

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from sr_od.mys.sr_relic_sets import RELIC_SETS  # noqa: E402

CACHE = PROJECT_ROOT / '.debug' / 'game_data' / 'relic' / 'wiki'

# 常量名 → intl 词条名（译名差异别名;国际服本地化与国服名不一致时人工登记,
# 按 entry_page_id 对齐）。 intl 名「停止转动的萨尔索图」= 国服「停转的萨尔索图」。
INTL_ALIAS: dict[str, str] = {
    '停转的萨尔索图': '停止转动的萨尔索图',
}


def norm_cn(name: str) -> str:
    """连表键归一化:折叠空白(BOM/半角逗号由 fetch 脚本在 intl 侧清理)。"""
    return re.sub(r'\s+', '', name)


def main() -> int:
    cn_list = json.loads((CACHE / 'cnwiki_relic_list.json').read_text(encoding='utf-8'))
    intl_map = json.loads((CACHE / 'hoyowiki_relic_id_map.json').read_text(encoding='utf-8'))

    cn_by_name: dict[str, dict] = {norm_cn(e['name']): e for e in cn_list}
    consumed_cn: set[int] = set()
    consumed_intl: set[str] = set()
    manual_sets: list[str] = []
    empty_id: list[str] = []
    alias_rows: list[str] = []

    for relic_set in RELIC_SETS:
        key = norm_cn(relic_set.set_name)
        cn_row = cn_by_name.get(key)
        intl_key = norm_cn(INTL_ALIAS.get(relic_set.set_name, relic_set.set_name))
        intl_row = intl_map.get(intl_key)
        if cn_row is not None:
            consumed_cn.add(cn_row['content_id'])
        if intl_row is not None:
            consumed_intl.add(intl_row['hoyowiki_page_id'])
        if cn_row is None:
            manual_sets.append(relic_set.set_name)
        if not relic_set.id:
            empty_id.append(relic_set.set_name)
        if intl_key != key:
            alias_rows.append(f'{relic_set.set_name} → intl「{INTL_ALIAS[relic_set.set_name]}」')

    # 对账:输入侧未消费的条目 = 常量缺失或撞键,人工审阅
    unconsumed_cn = [e for e in cn_list if e['content_id'] not in consumed_cn]
    unconsumed_intl = [(v['hoyowiki_page_id'], k) for k, v in intl_map.items()
                       if v['hoyowiki_page_id'] not in consumed_intl]
    if unconsumed_cn:
        print(f'⚠ 国内 wiki 未对上常量的词条 {len(unconsumed_cn)}: {unconsumed_cn}')
    if unconsumed_intl:
        print(f'⚠ 国际服未对上常量的词条 {len(unconsumed_intl)}: {unconsumed_intl}')
    print(f'常量 {len(RELIC_SETS)} 条 | manual(wiki 未收录) {len(manual_sets)}: {manual_sets}')
    print(f'空 id {len(empty_id)}(国际服未同步,宁缺勿错): {empty_id}')
    if alias_rows:
        print(f'译名别名 {len(alias_rows)}: {alias_rows}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
