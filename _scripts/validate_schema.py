#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
스키마 검증기 — 모든 캐릭터/에피소드 레코드의 필드명이 v2 스키마와 일치하는지 검사.
입력폼(_템플릿/character.json, _템플릿/episodes/ep_01.json)의 필드명이 바뀌어도 이 스크립트로 정합성을 확인한다.

- `_` 접두사 필드(폼 안내·AI 규칙 등 스캐폴딩)는 검사에서 무시한다.
- 필수 필드 누락 / 예상 밖(잉여) 필드를 리포트한다.
- v1 잔재 링크 필드(episode_ids/story_id/storyboard_id)는 v2 설계 위반으로 별도 경고.

실행:
  python3 _scripts/validate_schema.py                 # 로컬 03_캐릭터 전체 검사
  python3 _scripts/validate_schema.py 폼파일.json char # 임의 파일을 캐릭터 스키마로 검사 (ep/char)
"""
import json, os, glob, sys
from _common import CHAR_DIR

CHAR_FIELDS = ["id", "world_id", "heroine_id", "goal", "name", "grade_class",
               "archetype", "primary_trigger", "secondary_trigger", "gap_surface",
               "gap_hidden", "signature_action", "first3s_hook", "tension_partner",
               "taboo_barrier", "recommendation", "status", "created_at", "updated_at"]
EP_FIELDS = ["id", "character_id", "goal", "title", "target_trigger", "emotion_shift",
             "core_event", "logline", "recommendation", "beats", "storyboard", "judge_score",
             "status", "published_at", "metrics", "created_at", "updated_at"]
# v1 잔재(양방향 링크) — v2에서는 제거되어야 함
RELICS = {"episode_ids", "story_id", "storyboard_id"}
METRIC_FIELDS = {"views", "likes", "comments", "shares", "saves", "duration_s", "er_pct", "save_rate_pct"}
BEAT_KEYS = {"HOOK", "SETUP", "BUILD", "PAYOFF", "HOOKOUT"}
REC_FIELDS = {"for", "label", "reasons"}


def check(record, expected, label):
    keys = {k for k in record if not k.startswith("_")}  # 폼 스캐폴딩(_*) 무시
    exp = set(expected)
    missing = [k for k in expected if k not in keys]
    extra = sorted(keys - exp)
    relic = [k for k in extra if k in RELICS]
    other = [k for k in extra if k not in RELICS]
    ok = not missing and not extra
    msgs = []
    if missing:
        msgs.append(f"❌ 누락: {missing}")
    if relic:
        msgs.append(f"⚠️ v1 잔재 링크(제거 대상): {relic}")
    if other:
        msgs.append(f"➕ 예상 밖 필드: {other}")
    # 하위 구조 검사
    if "metrics" in record and isinstance(record["metrics"], dict):
        mm = METRIC_FIELDS - set(record["metrics"])
        if mm:
            msgs.append(f"metrics 누락: {sorted(mm)}")
    if "beats" in record and isinstance(record["beats"], dict):
        bm = BEAT_KEYS - set(record["beats"])
        if bm:
            msgs.append(f"beats 누락: {sorted(bm)}")
    if "recommendation" in record and isinstance(record["recommendation"], dict):
        rm = REC_FIELDS - set(record["recommendation"])
        if rm:
            msgs.append(f"recommendation 누락: {sorted(rm)}")
            ok = False
    status = "✅ OK" if ok else "  ".join(msgs)
    return ok, f"[{label}] {status}"


def validate_local():
    results = []
    for p in sorted(glob.glob(os.path.join(CHAR_DIR, "char_*", "character.json"))):
        d = json.load(open(p, encoding="utf-8"))
        results.append(check(d, CHAR_FIELDS, os.path.relpath(p, CHAR_DIR)))
    for p in sorted(glob.glob(os.path.join(CHAR_DIR, "char_*", "episodes", "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        results.append(check(d, EP_FIELDS, os.path.relpath(p, CHAR_DIR)))
    return results


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        path = sys.argv[1]
        kind = sys.argv[2] if len(sys.argv) >= 3 else "char"
        d = json.load(open(path, encoding="utf-8"))
        ok, msg = check(d, CHAR_FIELDS if kind == "char" else EP_FIELDS, os.path.basename(path))
        print(msg)
        sys.exit(0 if ok else 1)

    results = validate_local()
    for _, msg in results:
        print(msg)
    bad = [m for ok, m in results if not ok]
    print(f"\n=== 검증 결과: {len(results)-len(bad)}/{len(results)} 통과",
          "✅ 전부 정상" if not bad else f"· {len(bad)}건 문제")
    sys.exit(0 if not bad else 1)
