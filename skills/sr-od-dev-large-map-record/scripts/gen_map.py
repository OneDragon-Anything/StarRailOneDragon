# -*- coding: utf-8 -*-
"""通用地图生成: uv run gen_map.py <map_id> <截图路径> <输出目录名>
管线: 官方 info/point 拉取(带缓存) → SIFT 定标(全图, 护栏: |rot|<0.5) → raw(噪声背景)+mask → 锚点 lm_pos。
"""
import io
import json
import os
import sys

import numpy as np
import cv2
import requests
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
WORK = os.path.join(REPO, '.debug', 'temp', 'animestudio')
APP_VERSION = 'de16a09fca4e0ab89acf69fe0c12514f'
BASE = 'https://api-static.mihoyo.com/common/srmap/sr_map/v1'
PARAMS = f'app_sn=sr_map&lang=zh-cn&app_version={APP_VERSION}'

MAP_ID = int(sys.argv[1])
SHOT = sys.argv[2]
OUT = os.path.join(WORK, 'mys_probe', sys.argv[3])
os.makedirs(OUT, exist_ok=True)

info_p = os.path.join(WORK, 'mys_probe', f'map_info_{MAP_ID}.json')
pts_p = os.path.join(WORK, 'mys_probe', f'map_point_{MAP_ID}.json')
if os.path.exists(info_p):
    info = json.load(io.open(info_p, encoding='utf-8'))
    pts = json.load(io.open(pts_p, encoding='utf-8'))
else:
    info = requests.get(f'{BASE}/map/info?map_id={MAP_ID}&{PARAMS}', timeout=20).json()
    pts = requests.get(f'{BASE}/map/point/list?map_id={MAP_ID}&{PARAMS}', timeout=20).json()
    io.open(info_p, 'w', encoding='utf-8').write(json.dumps(info, ensure_ascii=False))
    io.open(pts_p, 'w', encoding='utf-8').write(json.dumps(pts, ensure_ascii=False))
detail = json.loads(info['data']['info']['detail'])
origin = detail['origin']
url = detail['slices'][0][0]['url']
arr = np.array(Image.open(io.BytesIO(requests.get(url, timeout=60).content)).convert('RGBA'))
base_bgr = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)
base_alpha = arr[:, :, 3]
base_gray = cv2.cvtColor(base_bgr, cv2.COLOR_BGR2GRAY)
print(f'底图: {base_bgr.shape[1]}x{base_bgr.shape[0]} origin={origin}')

plist = pts['data']['point_list']
labels = {lb['id']: lb['name'] for lb in pts['data']['label_list']}
anchors = [(p['x_pos'], p['y_pos']) for p in plist if '锚' in labels.get(p['label_id'], '')]
print(f'锚点: {len(anchors)} 个')

shot = cv2.imread(SHOT)
assert shot is not None, SHOT
shot_gray = cv2.cvtColor(shot, cv2.COLOR_BGR2GRAY)
sift = cv2.SIFT_create(nfeatures=10000)
bf = cv2.BFMatcher()
kp1, d1 = sift.detectAndCompute(shot_gray, None)
kp2, d2 = sift.detectAndCompute(base_gray, None)


def translation_vote(src, dst, bin_px=16, top_k=3):
    """位移投票: 真匹配共享同一位移, 幽灵/混层导致的错配散开 — 取最大簇下标集。"""
    disp = dst - src
    keys = np.floor(disp / bin_px).astype(np.int64)
    from collections import Counter
    cnt = Counter(map(tuple, keys))
    out = []
    for key, _n in cnt.most_common(top_k):
        sel = (keys[:, 0] == key[0]) & (keys[:, 1] == key[1])
        out.append(sel)
    return out


def sim_fit(src_i, dst_i):
    sc = src_i - src_i.mean(axis=0)
    dc = dst_i - dst_i.mean(axis=0)
    s = (sc * dc).sum() / (sc * sc).sum()
    cross = (sc[:, 0] * dc[:, 1] - sc[:, 1] * dc[:, 0]).sum()
    rot = np.degrees(np.arctan2(cross, (sc * dc).sum()))
    t = dst_i.mean(axis=0) - s * src_i.mean(axis=0)
    resid = np.hypot(*(src_i * s + t - dst_i).T)
    return s, t, rot, resid


calib = None
# 两级策略: 常规 RANSAC 多档 ratio; 仍退化 (双层合成页 -> 位移混合) 则平移投票分簇。
for ratio in (0.75, 0.7, 0.62, 0.55, 0.5):
    pairs = []
    for mp in bf.knnMatch(d1, d2, k=2):
        if len(mp) == 2 and mp[0].distance < ratio * mp[1].distance:
            pairs.append((mp[0].queryIdx, mp[0].trainIdx))
    if len(pairs) < 12:
        continue
    src = np.array([kp1[i].pt for i, _ in pairs], dtype=np.float64)
    dst = np.array([kp2[j].pt for _, j in pairs], dtype=np.float64)
    H, inl = cv2.findHomography(src, dst, cv2.RANSAC, 4.0, maxIters=20000, confidence=0.9999)
    ok = False
    if inl is not None and int(inl.sum()) >= 12:
        inl_mask = inl.ravel().astype(bool)
        src_i, dst_i = src[inl_mask], dst[inl_mask]
        s, t, rot, resid = sim_fit(src_i, dst_i)
        print(f'  [ransac] ratio={ratio}: inliers={int(inl_mask.sum())} scale={s:.5f} rot={rot:.3f} 残差={resid.mean():.2f}')
        if abs(rot) < 0.5 and 0.1 < s < 4.0 and int(inl_mask.sum()) >= 12 and resid.mean() < 3.0:
            calib = (s, t, rot, int(inl_mask.sum()))
            ok = True
    if not ok:
        # 平移投票: 按簇拟合, 护栏通过即收
        for ki, sel in enumerate(translation_vote(src, dst)):
            if sel.sum() < 12:
                continue
            s, t, rot, resid = sim_fit(src[sel], dst[sel])
            print(f'  [vote{ki}] ratio={ratio}: cluster={int(sel.sum())} scale={s:.5f} rot={rot:.3f} 残差={resid.mean():.2f}')
            if abs(rot) < 0.5 and 0.1 < s < 4.0 and int(sel.sum()) >= 10 and resid.mean() < 3.0:
                calib = (s, t, rot, int(sel.sum()))
                ok = True
                break
    if ok:
        break
assert calib is not None, '定标失败: RANSAC 与平移投票均未收出合法解'
s, t, rot, n_inl = calib
print(f'SIFT 定标: scale={s:.5f} rot={rot:.3f} 内点={n_inl}')

bh, bw = base_bgr.shape[:2]
corners = np.array([[0, 0], [bw, 0], [0, bh], [bw, bh]], dtype=np.float64)
gc = (corners - t) / s
min_xy, max_xy = gc.min(axis=0), gc.max(axis=0)
off_x, off_y = 20 - min_xy[0], 20 - min_xy[1]
canvas_w = int(max_xy[0] - min_xy[0]) + 40
canvas_h = int(max_xy[1] - min_xy[1]) + 40
inv_s = 1.0 / s
M = np.array([[inv_s, 0, -t[0] / s + off_x], [0, inv_s, -t[1] / s + off_y]], dtype=np.float64)
rng = np.random.default_rng(20260912)
alpha_warp = cv2.warpAffine((base_alpha > 10).astype(np.uint8) * 255, M, (canvas_w, canvas_h), borderValue=0)
raw = rng.integers(201, 210, (canvas_h, canvas_w, 3), dtype=np.uint8)
content = cv2.warpAffine(base_bgr, M, (canvas_w, canvas_h), borderValue=0)
raw[alpha_warp > 10] = content[alpha_warp > 10]
mask_src = (((base_gray < 100) | ((base_gray >= 100) & (base_gray < 180))) & (base_alpha > 10)).astype(np.uint8) * 255
mask = cv2.warpAffine(mask_src, M, (canvas_w, canvas_h), borderValue=0)
n, lbl, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=4)
for lb in range(1, n):
    if stats[lb, cv2.CC_STAT_AREA] < 500:
        mask[lbl == lb] = 0

sp_rows = []
for i, (bx, by) in enumerate(sorted(anchors), 1):
    gx, gy = (bx + origin[0] - t[0]) / s + off_x, (by + origin[1] - t[1]) / s + off_y
    sp_rows.append({'num': i, 'official': [bx, by], 'lm_pos': [round(gx, 1), round(gy, 1)]})
    print(f'锚{i}: 官方({bx:.0f},{by:.0f}) -> lm_pos=({gx:.0f},{gy:.0f})')

cv2.imwrite(os.path.join(OUT, 'raw.png'), raw)
cv2.imwrite(os.path.join(OUT, 'mask.png'), mask)
with open(os.path.join(OUT, 'calib.json'), 'w', encoding='utf-8') as f:
    json.dump({'map_id': MAP_ID, 'origin': origin, 'scale': s, 't': list(t),
               'off': [off_x, off_y], 'canvas': [canvas_w, canvas_h],
               'inliers': int(inl_mask.sum()), 'rot_deg': rot, 'shot': os.path.basename(SHOT),
               'sp': sp_rows}, f, ensure_ascii=False, indent=1)
print(f'产物: {OUT}')






