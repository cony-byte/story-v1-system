#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 심사위원 — 자동검사 파트 (rubric v2 A항목 60점)
v2 구조: 에피소드는 03_캐릭터/{char}/episodes/ep_NN.json, 스토리보드는 에피소드에 내포.
질적검사(B항목 40점)는 Claude가 rubric.md B표를 보고 판정.

실행: python3 04_심사위원/judge.py char_seojun/ep_01
      python3 04_심사위원/judge.py ep_01 char_seojun   (캐릭터 지정)
"""
import json, os, sys, glob, re

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
CHAR_DIR = os.path.join(ROOT, "03_캐릭터")
RULES = json.load(open(os.path.join(ROOT, "00_규칙엔진", "규칙_최신.json"), encoding="utf-8"))

VALID_FRAMING = {"전신", "미디엄", "클로즈업", "인서트"}
VALID_GAZE = {"나를 본다", "나를 안 본다", "나를 보다가 안 본다", "얼굴X"}
VALID_ANGLE = {"아이레벨", "로우앵글", "하이앵글"}
TIME_GRID_30 = ["0-3s","3-6s","6-9s","9-12s","12-15s","15-18s","18-21s","21-24s","24-27s","27-30s"]
BEAT_KEYS = ["HOOK", "SETUP", "BUILD", "PAYOFF", "HOOKOUT"]


def read(p):
    return json.load(open(p, encoding="utf-8"))


def find_episode(spec):
    """spec: 'char_x/ep_01' 또는 'ep_01' → (episode dict, char dir)."""
    if "/" in spec:
        cslug, epid = spec.split("/", 1)
        p = os.path.join(CHAR_DIR, cslug, "episodes", epid + ".json")
        if os.path.exists(p):
            return read(p), os.path.join(CHAR_DIR, cslug)
    # 전역 검색
    for p in glob.glob(os.path.join(CHAR_DIR, "char_*", "episodes", "*.json")):
        d = read(p)
        if d.get("id") == spec or os.path.basename(p) == spec + ".json":
            return d, os.path.dirname(os.path.dirname(p))
    return None, None


def trigger_ok(tag):
    base = RULES["baseline"]["median_er"]
    for t in RULES["trigger_ranking_grammar"]:
        if t["tag"] == tag:
            return (t["median_er"] is not None and t["median_er"] >= base), t["median_er"]
    return False, None


def judge(spec):
    ep, cdir = find_episode(spec)
    if not ep:
        return {"error": f"에피소드 {spec} 없음"}
    char = read(os.path.join(cdir, "character.json"))
    sb = ep.get("storyboard")

    score, avail, items, fixes = 0, 0, [], []

    # A1 캐릭터 정의 완결성
    need = ["archetype", "primary_trigger", "gap_hidden", "first3s_hook"]
    missing = [k for k in need if not char.get(k)]
    avail += 12
    if not missing:
        score += 12; items.append("A1 ✅ 캐릭터 정의 완결 (12)")
    else:
        items.append(f"A1 ❌ 캐릭터 필드 누락: {missing} (0)")
        fixes.append(f"A1: character.json에 {missing} 채우기.")

    # A2 target_trigger 유효성
    ok, er = trigger_ok(ep.get("target_trigger", ""))
    avail += 12
    if ok:
        score += 12; items.append(f"A2 ✅ target_trigger 기준선 이상 (ER {er}%) (12)")
    else:
        items.append(f"A2 ❌ target_trigger 약함/부재 (ER {er}) (0)")
        fixes.append("A2: 규칙_최신 트리거순위에서 기준선 ER 이상 트리거로 교체.")

    # A3 beats 완결
    beats = ep.get("beats", {})
    miss_b = [k for k in BEAT_KEYS if not beats.get(k)]
    avail += 8
    if not miss_b:
        score += 8; items.append("A3 ✅ 5비트 완결 (8)")
    else:
        items.append(f"A3 ❌ beats 누락: {miss_b} (0)")
        fixes.append(f"A3: beats에 {miss_b} 채우기.")

    # A4~A6 스토리보드 (있을 때만)
    if not sb:
        items.append("A4~A6 ⏭️ 스토리보드 없음 → N/A (후순위)")
    else:
        cuts = sb.get("cuts", [])
        avail += 28
        # A4 컷수/시간
        a4 = True
        fmt = sb.get("format", "")
        if "30초" in fmt or "10컷" in fmt:
            if len(cuts) != 10:
                a4 = False
        times = [c.get("time") for c in cuts]
        if times[:10] != TIME_GRID_30[:len(times)]:
            a4 = False
        if a4:
            score += 10; items.append(f"A4 ✅ 컷수·시간그리드 일치 ({len(cuts)}컷) (10)")
        else:
            items.append(f"A4 ❌ 컷수/시간그리드 불일치 ({len(cuts)}컷) (0)")
            fixes.append("A4: 10컷 + 3초 고정 그리드(0-3s…27-30s)로 맞출 것.")
        # A5 출력계약
        a5_bad = []
        for c in cuts:
            g = c.get("gen_beats", "")
            if c.get("framing") != "인서트" and len(re.findall(r"[①②③④⑤]", g)) < 2:
                a5_bad.append(f"컷{c.get('cut')}: gen_beats 비트 2개 미만")
            e = c.get("edit_subtitle", "")
            if re.search(r"\d+s\b", e):
                a5_bad.append(f"컷{c.get('cut')}: 자막에 타임스탬프")
            if any(k in e for k in ["SFX", "효과음", "배경음", "BGM"]):
                a5_bad.append(f"컷{c.get('cut')}: 자막에 사운드")
        if not a5_bad:
            score += 10; items.append("A5 ✅ v9 출력계약 준수 (10)")
        else:
            items.append(f"A5 ❌ 출력계약 위반 {len(a5_bad)}건 (0)")
            fixes.append("A5: " + "; ".join(a5_bad[:4]))
        # A6 옵션값
        a6_bad = []
        for c in cuts:
            if c.get("framing") not in VALID_FRAMING: a6_bad.append(f"컷{c.get('cut')} framing")
            if c.get("gaze") not in VALID_GAZE: a6_bad.append(f"컷{c.get('cut')} gaze")
            if c.get("angle") not in VALID_ANGLE: a6_bad.append(f"컷{c.get('cut')} angle")
        if not a6_bad:
            score += 8; items.append("A6 ✅ framing/gaze/angle 옵션값 (8)")
        else:
            items.append(f"A6 ❌ 옵션값 위반 {len(a6_bad)}건 (0)")
            fixes.append("A6: " + ", ".join(a6_bad[:5]))

    pct = round(score / avail * 60, 1) if avail else 0
    return {
        "episode": ep.get("id"), "character": char.get("id"),
        "raw_score": score, "available": avail,
        "A_score_60": pct,
        "items": items, "fixes": fixes,
        "storyboard_present": bool(sb),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python3 judge.py char_seojun/ep_01  (또는 ep_01)")
        sys.exit(1)
    spec = sys.argv[1]
    if len(sys.argv) >= 3 and "/" not in spec:
        spec = sys.argv[2] + "/" + spec
    r = judge(spec)
    print(json.dumps(r, ensure_ascii=False, indent=2))
