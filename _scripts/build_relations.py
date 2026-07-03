#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
관계성 자동 생성 (텍스트·숫자형) — 캐릭터+에피소드+여주에서 관계를 도출.
출력: 루트 _relations.json (파생물, 손대지 말 것)
  - table : A) 행=캐릭터 (트리거·에피소드·여주·라이벌·트리거공유)
  - summary : C) 숫자 요약 (분포·겹침·라이벌쌍·평균)

SVG 지도 대신 표/숫자로 보여주기 위한 데이터. 앱은 이 파일만 읽어 렌더.

실행: python3 _scripts/build_relations.py
"""
import os, datetime
from collections import Counter
from _common import (ROOT, char_dirs, load_character, load_episodes,
                     load_heroine, load_rules, write_json)


def trigger_label(rules, tag):
    for t in rules["trigger_ranking_grammar"] + rules["trope_ranking"]:
        if t["tag"] == tag:
            return t["label"]
    return tag or "—"


def build():
    rules = load_rules()
    heroine = load_heroine().get("name", "여주")

    chars = []
    for cdir in char_dirs():
        c = load_character(cdir)
        eps = load_episodes(cdir)
        chars.append({"c": c, "eps": eps})

    names = [x["c"].get("name", "") for x in chars]

    # 트리거별 캐릭터(공유군) 매핑
    by_trigger = {}
    for x in chars:
        by_trigger.setdefault(x["c"].get("primary_trigger", ""), []).append(x["c"].get("name", ""))

    table = []
    rival_pairs = set()
    for x in chars:
        c, eps = x["c"], x["eps"]
        name = c.get("name", "")
        prim = c.get("primary_trigger", "")
        shared = [n for n in by_trigger.get(prim, []) if n != name]
        # 라이벌: tension_partner에 등장하는 '다른 캐릭터 이름'
        tp = c.get("tension_partner", "") or ""
        rival_chars = [n for n in names if n and n != name and n in tp]
        for rn in rival_chars:
            rival_pairs.add(tuple(sorted([name, rn])))
        table.append({
            "character_id": c.get("id", ""),
            "name": name,
            "trigger": prim,
            "trigger_label": trigger_label(rules, prim),
            "n_episodes": len(eps),
            "episode_ids": [e.get("id", "") for e in eps],
            "heroine": heroine,
            "tension_partner": tp,
            "rival_chars": rival_chars,
            "shared_trigger_with": shared,
        })

    dist = Counter(t["trigger_label"] for t in table)
    overlap = sum(1 for v in by_trigger.values() if len(v) > 1)
    n_ep_total = sum(t["n_episodes"] for t in table)

    summary = {
        "n_characters": len(table),
        "heroine": heroine,
        "all_to_heroine": len(table),  # 남캐 전원이 고정 여주 상대
        "trigger_distribution": dict(dist),
        "trigger_overlap_groups": overlap,     # 같은 1차 트리거를 쓰는 그룹 수
        "rival_pairs": [list(p) for p in sorted(rival_pairs)],
        "avg_episodes_per_char": round(n_ep_total / len(table), 2) if table else 0,
        "total_episodes": n_ep_total,
    }

    out = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "summary": summary,
        "table": table,
        "_note": "build_relations.py 자동 생성물. 관계성(텍스트·숫자형). 직접 수정하지 말 것.",
    }
    write_json(os.path.join(ROOT, "_relations.json"), out)
    return out


def main():
    out = build()
    s = out["summary"]
    print("관계성 생성 완료:", s["n_characters"], "캐릭터")
    print(f"  여주({s['heroine']}) 상대 남캐 {s['all_to_heroine']}명 · 평균 {s['avg_episodes_per_char']}화/명 · 겹치는 트리거 그룹 {s['trigger_overlap_groups']}")
    print("  트리거 분포:", ", ".join(f"{k} {v}" for k, v in s["trigger_distribution"].items()))
    print("  라이벌쌍:", s["rival_pairs"] or "없음")
    print("  [표]")
    for t in out["table"]:
        rv = ("/라이벌 " + ",".join(t["rival_chars"])) if t["rival_chars"] else ""
        sh = (" · 트리거공유 " + ",".join(t["shared_trigger_with"])) if t["shared_trigger_with"] else ""
        print(f"    {t['name']:<5} | {t['trigger_label']:<14} | {t['n_episodes']}화 | →{t['heroine']}{rv}{sh}")


if __name__ == "__main__":
    main()
