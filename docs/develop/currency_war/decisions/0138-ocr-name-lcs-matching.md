# 0138 OCR 名归一用框架 LCS 相似匹配(str_utils,非全等)

## Status

accepted(2026-08-15;用户指出:靠文本识别的匹配要用 str_utils 相似匹配,全文本匹配容易配不上)

## Context

图鉴采集的名字匹配最初用精确 in + 自写 difflib(ADR-0137 清洗脚本),对 OCR 艺术小字的系统性形变(狸↔禄/摊、垠↔银、•↔·、全半角冒号)大量失配。框架早有标准工具 str_utils.find_best_match_by_lcs(round_by_ocr 的 lcs_percent 同源)——没查项目工具是流程违规。

## Considered Options

- 匹配方式:全等/包含(现状)vs **LCS 相似度 th=0.5**(与框架 OCR 判定同哲学,对形变鲁棒)。
- 防误配守卫(实测「胜利，还」会偶合高分匹配到「返利」):①长度差 ≤3;②效果文本 LCS ≥0.5 二次验证(非包含式 —— 注册表效果与图鉴原文有措辞差时,包含会误杀正确映射,实测「他们获得师徒」vs「获师徒羁绊」)。

## Decision

1. harvest_invest_codex._canon_name:find_best_match_by_lcs(0.5)+ 长度守卫 + 效果 LCS 守卫;守卫不过保留 raw(codex-new 人工核路径)。
2. ADR-0137 六条新条目的注册表效果文本换图鉴原文(手写压缩版过短会稀释效果守卫的 LCS)。

验证:飞光•传剑→飞光·传剑 / 步狸村之谜→步禄村之谜 / 胜利，还→保留(防误配);CW 全套 393 passed。

## 教训(入口文件已带,此处记 CW 专属)

- CW 所有「OCR 文本 → 注册表/规范名」的匹配一律走 str_utils 相似匹配(组件如 round_by_ocr 的 lcs_percent;脚本/工具同 find_best_match_by_lcs),别写全等/包含/in。
