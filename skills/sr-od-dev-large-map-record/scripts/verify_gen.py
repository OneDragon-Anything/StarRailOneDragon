# -*- coding: utf-8 -*-
"""gen 目录通用验证: CUT门(纯官方) + 锚点真值裁判 + 贴回 + 复测。
用法: uv run verify_gen.py <gen_dir>
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
ICON = os.path.join(REPO, 'assets', 'template', 'mm_icon')
CUT = (285, 190, 1300, 930)
G = os.path.join(WORK, 'mys_probe', sys.argv[1])
cal = json.load(io.open(os.path.join(G, 'calib.json'), encoding='utf-8'))
OFF = np.array(cal['off'])
S1 = cal['scale']
T1 = np.array(cal['t'])
MAP_ID = cal['map_id']
my_raw = cv2.imread(os.path.join(G, 'raw.png'))
shot = cv2.imread(os.path.join(REPO, '.debug', 'sr_od_mcp', 'screenshot', cal['shot']))
pts = json.load(io.open(os.path.join(WORK, 'mys_probe', f'map_point_{MAP_ID}.json'), encoding='utf-8'))
labels = {lb['id']: lb['name'] for lb in pts['data']['label_list']}


def base_to_shot(bx, by):
    return (bx + cal['origin'][0] - T1[0]) / S1, (by + cal['origin'][1] - T1[1]) / S1


def gate(raw_img, tag):
    sp = shot[CUT[1]:CUT[3], CUT[0]:CUT[2]]
    px1, py1 = int(CUT[0] - 60 + OFF[0]), int(CUT[1] - 60 + OFF[1])
    pw, ph = int(sp.shape[1] + 120), int(sp.shape[0] + 120)
    cv_ = np.random.default_rng(7).integers(201, 210, (ph, pw, 3), dtype=np.uint8)
    sx, sy = max(0, -px1), max(0, -py1)
    dx, dy = max(0, px1), max(0, py1)
    w_ = min(pw - sx, raw_img.shape[1] - dx)
    h_ = min(ph - sy, raw_img.shape[0] - dy)
    cv_[sy:sy + h_, sx:sx + w_] = raw_img[dy:dy + int(h_), dx:dx + int(w_)]
    res = cv2.matchTemplate(cv_, sp, cv2.TM_CCOEFF_NORMED)
    res = np.nan_to_num(res, nan=0.0, posinf=0.0, neginf=0.0)
    _, mx, _, _ = cv2.minMaxLoc(res)
    print(f'{tag}: {mx:.4f}')
    return mx


gate(my_raw, '纯官方 CUT门')

# 锚点真值裁判
tpl = cv2.imread(os.path.join(ICON, 'mm_tp_03', 'raw.png'))
m = cv2.imread(os.path.join(ICON, 'mm_tp_03', 'mask.png'), cv2.IMREAD_GRAYSCALE)
ys, xs = np.where(m > 0)
toff = ((xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2)
anchors = [(p['x_pos'], p['y_pos']) for p in pts['data']['point_list'] if '锚' in labels.get(p['label_id'], '')]
for i, (bx, by) in enumerate(sorted(anchors), 1):
    gx, gy = base_to_shot(bx, by)
    if not (0 <= gx < 1920 and 60 <= gy < 1000):
        print(f'锚{i}: 投影 ({gx:.0f},{gy:.0f}) 出屏/超区')
        continue
    rx1, ry1 = int(gx - 80), int(gy - 80)
    roi = shot[ry1:int(gy + 80 + tpl.shape[0]), rx1:int(gx + 80 + tpl.shape[1])]
    if roi.shape[0] < tpl.shape[0] or roi.shape[1] < tpl.shape[1]:
        continue
    r2 = cv2.matchTemplate(roi, tpl, cv2.TM_CCOEFF_NORMED, mask=m)
    r2 = np.nan_to_num(r2, nan=0.0, posinf=0.0, neginf=0.0)
    _, mxc, _, locc = cv2.minMaxLoc(r2)
    tx, ty = rx1 + locc[0] + toff[0], ry1 + locc[1] + toff[1]
    print(f'锚{i}: 投影 ({gx:.0f},{gy:.0f}) 真值 ({tx:.0f},{ty:.0f}) 误差 {np.hypot(tx - gx, ty - gy):.1f}px conf={mxc:.3f}')

# 贴回 (全视角单帧)
info = json.load(io.open(os.path.join(WORK, 'mys_probe', f'map_info_{MAP_ID}.json'), encoding='utf-8'))
detail = json.loads(info['data']['info']['detail'])
arr = np.array(Image.open(io.BytesIO(requests.get(detail['slices'][0][0]['url'], timeout=60).content)).convert('RGBA'))
bh, bw = arr.shape[:2]
inv_s = 1.0 / S1
M = np.array([[inv_s, 0, -T1[0] / S1 + OFF[0]], [0, inv_s, -T1[1] / S1 + OFF[1]]], dtype=np.float64)
alpha_full = cv2.warpAffine(((arr[:, :, 3] > 10).astype(np.uint8) * 255), M,
                            (my_raw.shape[1], my_raw.shape[0]), borderValue=0)
VIEW = (0, 100, 1430, 1015)
UI_RECTS = [(0, 20, 230, 100), (10, 550, 130, 1020), (500, 940, 970, 1020)]
vx1, vy1, vx2, vy2 = VIEW
sub = shot[vy1:vy2, vx1:vx2]
ox, oy = int(0 + OFF[0]), int(100 + OFF[1])
hh, ww = sub.shape[:2]
sx1, sy1 = max(0, -ox), max(0, -oy)
ox, oy = max(0, ox), max(0, oy)
ww = min(ww - sx1, my_raw.shape[1] - ox)
hh = min(hh - sy1, my_raw.shape[0] - oy)
sub = sub[sy1:sy1 + hh, sx1:sx1 + ww]
pmask = (alpha_full[oy:oy + hh, ox:ox + ww] > 10).astype(np.uint8) * 255
for (ux1, uy1, ux2, uy2) in UI_RECTS:
    if uy2 > vy1 and uy1 < vy2 and ux2 > vx1 and ux1 < vx2:
        r1, r2 = max(0, uy1 - vy1 - sy1), min(hh, uy2 - vy1 - sy1)
        c1, c2 = max(0, ux1 - vx1 - sx1), min(ww, ux2 - vx1 - sy1)
        if r2 > r1 and c2 > c1:
            pmask[r1:r2, c1:c2] = 0
pmask = cv2.GaussianBlur(pmask, (0, 0), 2)
a = (pmask.astype(np.float32) / 255.0)[..., None]
region = my_raw[oy:oy + hh, ox:ox + ww].astype(np.float32)
my_raw[oy:oy + hh, ox:ox + ww] = (sub.astype(np.float32) * a + region * (1 - a)).clip(0, 255).astype(np.uint8)
cv2.imwrite(os.path.join(G, 'raw_overlaid.png'), my_raw)
gate(my_raw, '贴回后 CUT门')

