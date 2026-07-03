#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
성과 자동 롤업 — 각 캐릭터의 발행 에피소드 metrics를 캐릭터 단위로 집계.
출력: 각 캐릭터 폴더의 _performance.json (파생물, 손대지 말 것)

실행: python3 _scripts/build_performance.py
"""
import os, datetime
from _common import char_dirs, load_character, load_episodes, load_rules, median, write_json


def build_one(cdir):
    char = load_character(cdir)
    eps = load_episodes(cdir)
    published = [e for e in eps if e.get("status") == "published" and e.get("metrics", {}).get("er_pct") is not None]
    m = lambda k: median([e["metrics"].get(k) for e in published])
    views = [e["metrics"].get("views") for e in published if e["metrics"].get("views") is not None]
    med_er = m("er_pct")
    perf = {
        "character_id": char["id"],
        "name": char.get("name", ""),
        "n_episodes": len(eps),
        "n_published": len(published),
        "median_er": med_er,
        "median_save_rate": m("save_rate_pct"),
        "median_views": m("views"),
        "total_views": round(sum(views)) if views else None,
        # 점수: 발행 에피소드 ER 중앙값 (미측정이면 None)
        "character_score": med_er,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "_note": "build_performance.py 자동 생성물. 직접 수정하지 말 것.",
    }
    base = load_rules()["baseline"]["median_er"]
    perf["vs_baseline_er"] = round(med_er - base, 3) if med_er is not None else None
    write_json(os.path.join(cdir, "_performance.json"), perf)
    return perf


def main():
    results = [build_one(c) for c in char_dirs()]
    print("성과 롤업 완료:", len(results), "캐릭터")
    for p in sorted(results, key=lambda x: (x["character_score"] is not None, x["character_score"] or 0), reverse=True):
        print(f"  {p['name']:<6} score={p['character_score']} (발행 {p['n_published']}/{p['n_episodes']}화)")


if __name__ == "__main__":
    main()
