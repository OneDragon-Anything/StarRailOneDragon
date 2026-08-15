"""货币战争 · 攻略广场 API 采集工具(可复用,版本更新重跑)。

== 数据源(2026-08-15 破解,免登录公开 API) ==
米游社活动页 act.miyoushe.com/sr/event/currency-wars/ 的后端:
  GET  {BASE}/game/config?game=hkrpg          → V<x.y> 官方全量配置
  POST {BASE}/game/lineup/index               → 攻略列表(cursor 分页,每条含完整三阶段阵容)
  GET  {BASE}/game/lineup/detail?id=<id>      → 单篇详情(列表已含同等结构,一般不用)
  BASE = https://act-api-takumi.miyoushe.com/event/rpgcurrencywar
必需 header: x-rpc-currencywar-tourn: tourn(缺了 retcode!=0)。

lineup/index 请求体关键字段:
  order: 'Hot' | 'Recommend'(其余值 -502);page/limit 服务端封顶 10/页;
  分页用 data.next_page_token 回传(cursor,非页码);
  role_ids: [1009, ...] / trait_ids: [1001, ...] 可按角色/羁绊筛选(id 见 config)。

== 图片 URL ↔ 本地图片的映射方法(核心约定) ==
**稳定键 = 数字 id**(role 1009=艾丝妲 / equip 35030102=火力风暴潮),
icon URL 是 id 的派生物(带资源 hash,**版本更新会变**),名字也可能改。因此:
  1. 本地图片一律存 icons/<kind>/<id>.png(id 命名,URL/改名都不破映射);
  2. id ↔ name ↔ icon_url 映射存 manifest_v<版本>.json,重跑 config 时
     自动 diff 旧 manifest,输出 新增/移除/URL变更/改名 报告;
  3. URL 变了 → 重跑 icons 子命令按 id 重下覆盖,id 不变映射不破;
  4. 无 id 场景(游戏截图识别)→ SIFT 对 icons/ 库匹配(2026-08-15 实证:
     游戏内 58px icon ↔ 官方 128px icon,头像/装备 4/4 命中;
     ⚠️ 特权/普通同 art 装备 SIFT 同分(如 35040102≈35030102),需框色二次仲裁)。

== 用法(项目根运行) ==
  uv run python tools/cw/plaza_fetch.py config            # 拉 config + manifest
  uv run python tools/cw/plaza_fetch.py lineups --order Hot --pages 5
  uv run python tools/cw/plaza_fetch.py lineups --traits 1001 --pages 3  # 按羁绊筛
  uv run python tools/cw/plaza_fetch.py icons             # 下载/更新 icon 库(幂等)
  浏览器版(免环境): tools/cw/plaza_harvest.js 粘 console 运行
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

BASE = "https://act-api-takumi.miyoushe.com/event/rpgcurrencywar/game"
OUT_DIR = Path(".debug/temp/currency_war/plaza")
HEADERS = {
    "Content-Type": "application/json",
    "x-rpc-currencywar-tourn": "tourn",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://act.miyoushe.com/",
    "Origin": "https://act.miyoushe.com",
}


def _get(path: str) -> dict:
    req = urllib.request.Request(f"{BASE}/{path}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE}/{path}", data=json.dumps(body).encode(), headers=HEADERS
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _check(d: dict, what: str) -> dict:
    if d.get("retcode") != 0:
        raise RuntimeError(f"{what} 失败: retcode={d.get('retcode')} msg={d.get('message')}")
    return d["data"]


def fetch_config() -> dict:
    """拉 config + 生成 manifest(id↔name↔icon 映射,URL 变化 diff 报告)。"""
    data = _check(_get("config?game=hkrpg"), "config")
    version = data.get("rpg_game_big_version", "?")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"config_v{version}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    manifest: dict = {"version": version, "role": {}, "equip": {}}
    for r in data["role_list"]:
        manifest["role"][str(r["id"])] = {
            "name": r["name"], "icon": r["icon"], "big_icon": r.get("big_icon", "")
        }
    for e in data["equipment_list"]:
        manifest["equip"][str(e["id"])] = {
            "name": e["name"], "icon": e["icon"], "big_icon": e.get("big_icon", "")
        }
    mpath = OUT_DIR / f"manifest_v{version}.json"
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    olds = sorted(OUT_DIR.glob("manifest_v*.json"), reverse=True)[1:]
    if olds:
        old = json.loads(olds[0].read_text(encoding="utf-8"))
        changed = []
        for kind in ("role", "equip"):
            for rid, info in manifest[kind].items():
                prev = old.get(kind, {}).get(rid)
                if prev is None:
                    changed.append(f"  + {kind} {rid} {info['name']}(新增)")
                elif prev["icon"] != info["icon"]:
                    changed.append(f"  ~ {kind} {rid} {info['name']} icon URL 变更")
                elif prev["name"] != info["name"]:
                    changed.append(f"  ~ {kind} {rid} 改名 {prev['name']} -> {info['name']}")
            for rid in set(old.get(kind, {})) - set(manifest[kind]):
                changed.append(f"  - {kind} {rid} {old[kind][rid]['name']}(移除)")
        print(f"[manifest] v{version} vs {olds[0].name}: '无变化' if not changed else ''")
        for line in changed[:30]:
            print(line)
    print(f"[config] {len(data['role_list'])}角色 {len(data['equipment_list'])}装备 v{version} -> {out.name}")
    print(f"[manifest] -> {mpath.name}")
    return data


def fetch_lineups(order: str = "Hot", pages: int = 5, role_ids: list | None = None,
                  trait_ids: list | None = None, match_hard: bool = False,
                  sleep_s: float = 0.5) -> list:
    """cursor 分页采集攻略列表(每条已含完整三阶段阵容)。

    match_hard=True = 服务端高难(困难/Challenge)阵容筛选(A8 实战数据定向通道);
    输出文件名带 Hard 标记,与普通采集不混。
    """
    tag = "Hard" if match_hard else ""
    if role_ids:
        tag += "R" + "-".join(map(str, role_ids))
    if trait_ids:
        tag += "T" + "-".join(map(str, trait_ids))
    out_path = OUT_DIR / f"lineups_{order}{tag}.jsonl"
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_items: list = []
    token = ""
    seen: set = set()
    for page in range(1, pages + 1):
        body = {
            "game": "hkrpg", "page": str(page), "limit": "10",
            "lineup_type": "Tourn", "next_page_token": token,
            "role_ids": role_ids or [], "trait_ids": trait_ids or [],
            "match_change_job": False, "match_hard": match_hard, "order": order,
        }
        data = _check(_post("lineup/index", body), f"lineup/index p{page}")
        items = data.get("list") or []
        new = [x for x in items if x["id"] not in seen]
        seen.update(x["id"] for x in new)
        all_items.extend(new)
        token = data.get("next_page_token") or ""
        head = new[0]["title"][:22] if new else ""
        print(f"[lineup] p{page}: {len(new)} 新增(总 {len(all_items)}) {head}")
        if not new or not token:
            print(f"[lineup] 结束: {'无更多(cursor 空)' if not token else '无新增(游标环)'}")
            break
        time.sleep(sleep_s)

    with out_path.open("w", encoding="utf-8") as f:
        for x in all_items:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print(f"[lineup] {len(all_items)} 篇 -> {out_path.name}")
    return all_items


def download_icons(force: bool = False, sleep_s: float = 0.15) -> None:
    """按 manifest 下载 icon 到 icons/<kind>/<id>.png(幂等,id 命名=URL 变也不破映射)。"""
    mans = sorted(OUT_DIR.glob("manifest_v*.json"))
    if not mans:
        raise RuntimeError("无 manifest,先跑 config 子命令")
    manifest = json.loads(mans[-1].read_text(encoding="utf-8"))
    n_new = n_skip = 0
    for kind in ("role", "equip"):
        d = OUT_DIR / "icons" / kind
        d.mkdir(parents=True, exist_ok=True)
        for rid, info in manifest[kind].items():
            dst = d / f"{rid}.png"
            if dst.exists() and not force:
                n_skip += 1
                continue
            req = urllib.request.Request(info["icon"], headers={
                "User-Agent": HEADERS["User-Agent"], "Referer": HEADERS["Referer"]})
            with urllib.request.urlopen(req, timeout=20) as resp:
                dst.write_bytes(resp.read())
            n_new += 1
            time.sleep(sleep_s)
    print(f"[icons] 新下 {n_new} / 跳过 {n_skip} -> {OUT_DIR / 'icons'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="攻略广场采集(config/lineups/icons)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("config", help="拉 game/config + 生成 manifest")
    p_line = sub.add_parser("lineups", help="采集攻略列表(jsonl)")
    p_line.add_argument("--order", default="Hot", choices=["Hot", "Recommend"])
    p_line.add_argument("--pages", type=int, default=5)
    p_line.add_argument("--roles", type=int, nargs="*", help="role id 筛选")
    p_line.add_argument("--traits", type=int, nargs="*", help="trait id 筛选(如 1001 列车同行)")
    p_line.add_argument("--hard", action="store_true", help="高难(困难)阵容筛选(A8 定向)")
    p_icon = sub.add_parser("icons", help="下载/更新 icon 库")
    p_icon.add_argument("--force", action="store_true", help="强制重下(默认幂等跳过)")
    args = parser.parse_args()

    if args.cmd == "config":
        fetch_config()
    elif args.cmd == "lineups":
        fetch_lineups(args.order, args.pages, args.roles, args.traits, args.hard)
    elif args.cmd == "icons":
        download_icons(args.force)


if __name__ == "__main__":
    main()
