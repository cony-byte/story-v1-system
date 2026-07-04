#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
규칙엔진 (v1)
로우데이터/ + 발행성과/ 폴더의 모든 CSV를 흡수 → 영상단위 집계
→ 상황/설정 ER 순위 · 컷 지표 · 훅 지표 재계산
→ 규칙_최신.json + 규칙_최신.md 산출

새 CSV를 폴더에 떨구고 이 스크립트만 다시 실행하면 규칙이 갱신된다.
크롤링(source=crawl)과 자체발행(source=own_published)을 같은 통계에 합산하되,
자체발행분은 따로도 집계해 '예측 vs 실제'에 쓴다.

실행:  python3 engine.py
"""
import csv, json, glob, os, statistics, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
CRAWL_DIR = os.path.join(BASE, "로우데이터")
OWN_DIR   = os.path.join(BASE, "발행성과")

# 태그(내부 영문 ID) → 영상 기획용 한글 표시 라벨.
# 내부 ID(tag)는 절대 바꾸지 말 것. 여기 label만 UI/뷰에 노출된다.
# 새 태그가 데이터에 등장하면 반드시 여기에 한글 라벨을 추가한다.
TRIGGER_LABEL = {
    # --- 대사문법 상황 ---
    "jealousy_possession_or_rival":        "① 독점욕·질투",
    "protective_claim_or_rescue":          "② 위기구원",
    "choice_ultimatum_or_deadline":        "④ 직진·최후통첩",
    "forbidden_love":                      "⑤ 금기의 긴장",
    "love_confession_or_desire":           "고백·욕망",
    "threat_danger_or_revenge":            "위협·위험·복수",
    "emotional_question_or_confrontation": "감정추궁·대립",
    "breakup_rejection_or_distance":       "이별·거절",
    "marriage_family_or_pregnancy":        "결혼·가족·임신",
    "general_dialogue":                    "일반 대화",
    "humiliation_status_drop_or_bullying": "굴욕·추락·괴롭힘",
    "misunderstanding_or_accusation":      "오해·누명",
    "power_money_or_status":               "권력·돈·지위",
    "secret_lie_or_reveal":                "비밀·거짓말·폭로",
    "apology_regret_or_sacrifice":         "사과·후회·희생",
    # --- 로맨스 설정 ---
    "love_triangle_or_rival":               "① 독점욕·질투(설정)",
    "danger_rescue_romance":                "② 위기구원(설정)",
    "protective_male_or_partner":           "② 보호남(설정)",
    "forced_choice_or_ultimatum":           "④ 직진(설정)",
    "breakup_sacrifice_or_noble_idiot":     "이별·희생(착한 바보)",
    "marriage_contract_or_family_pressure": "계약결혼·집안 압박",
    "general_romance":                      "일반 로맨스",
    "misunderstanding_to_reconciliation":   "오해→화해",
    "class_gap_cinderella":                 "신분차·신데렐라",
    "revenge_betrayal_or_payback":          "복수·배신·응징",
    "secret_identity_or_hidden_truth":      "정체 은폐·숨겨진 진실",
    "boss_employee_or_power_romance":       "상사·부하·권력 로맨스",
    # --- 훅 유형 (script_hook_type · v2) ---
    "emotional_question_hook":              "감정 질문형 훅",
    "confession_or_desire_hook":            "고백·욕망형 훅",
    "jealousy_rival_hook":                  "질투·라이벌형 훅",
    "marriage_family_hook":                 "결혼·가족형 훅",
    "ultimatum_hook":                       "최후통첩형 훅",
    "power_or_money_hook":                  "권력·돈형 훅",
    "breakup_or_sacrifice_hook":            "이별·희생형 훅",
    "threat_or_protection_hook":            "위협·보호형 훅",
    "identity_reveal_hook":                 "정체 폭로형 훅",
    "misunderstanding_hook":                "오해·누명형 훅",
    "humiliation_reversal_hook":            "굴욕·반전형 훅",
    "first_encounter_hook":                 "첫 만남형 훅",
    "crisis_rescue_hook":                   "위기구원형 훅",
    "status_quo_break_hook":                "일상 파괴 선언형 훅",
    "general_hook":                         "일반 훅",
    # --- 스토리 구동 (script_story_type) ---
    "emotion_reaction_driven":              "감정 리액션 중심",
    "dialogue_conflict_driven":             "대사 갈등 중심",
    "power_status_romance":                 "권력·지위 로맨스",
    "jealousy_rival_drama":                 "질투·라이벌극",
    "fast_cut_tension_driven":              "빠른 컷 긴장형",
    "danger_protection_drama":              "위기·보호극",
    "secret_reveal_betrayal_drama":         "비밀·배신극",
    "marriage_family_drama":                "결혼·가족극",
    "general_romance_drama":                "일반 로맨스극",
    # --- 비주얼 훅 (visual_hook_type · v2, 자동화 크롤링분 대비 선등록) ---
    "face_closeup_gaze":                    "클로즈업·시선형",
    "physical_contact":                     "신체 접촉형",
    "action_or_chase":                      "동작·추격형",
    "luxury_or_spectacle":                  "배경·과시형",
    "text_card_setup":                      "자막 카드형",
    "transformation_reveal":                "변신·리빌형",
    "general_visual":                       "일반 비주얼",
    # --- 남주 유형 (male_lead_type · v2, 선등록) ---
    "dominant_possessive":                  "집착·독점형",
    "protective_rescuer":                   "위기구원·보호형",
    "cold_to_warm":                         "냉정→다정형",
    "devoted_straightforward":              "직진·헌신형",
    "powerful_status":                      "권력·재벌형",
    "dangerous_forbidden":                  "위험·금기형",
    "unknown":                              "판별 불가",
    # --- v2.1 신설 태그 ---
    "recap_narration":                      "내레이션 리캡",
    "sweet_daily_or_flirting":              "갈등 없는 달달·플러팅",
    "sweet_flirting_or_daily":              "달달·플러팅 대사",
}


def label_of(tag):
    """표시용 한글 라벨. 매핑이 없으면 눈에 띄게 표시해 라벨 추가를 유도한다
    (영문 ID가 조용히 UI에 노출되는 것을 방지)."""
    return TRIGGER_LABEL.get(tag, f"\u27e8\ubbf8\ubd84\ub958:{tag}\u27e9")

def to_float(x):
    try:
        return float(str(x).replace("%", "").strip())
    except (ValueError, TypeError):
        return None

def median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 3) if xs else None

def load_rows(path, source):
    """CSV 1개 → 영상단위 dict 리스트 (첫 행 기준 dedupe)"""
    vids = {}
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            vid = r.get("source_video_id") or r.get("ep_id")
            if not vid:
                continue
            if vid in vids:
                continue
            vids[vid] = {
                "video_id": vid,
                "source": source,
                "views": to_float(r.get("ranking_views") or r.get("views")),
                "er": to_float(r.get("ranking_ER%_(save+share+cmt)/views") or r.get("er_pct")),
                "save_rate": to_float(r.get("ranking_save_rate%") or r.get("save_rate_pct")),
                "grammar_tags": [t.strip() for t in (r.get("script_dialogue_grammar_tags") or "").split("|") if t.strip()],
                "trope_tags":   [t.strip() for t in (r.get("script_romance_trope_tags") or "").split("|") if t.strip()],
                "hook_type":  (r.get("script_hook_type") or "").strip(),
                "story_type": (r.get("script_story_type") or "").strip(),
                "cut_count":  to_float(r.get("summary_cut_count")),
                "video_len":  to_float(r.get("summary_estimated_video_end_time")),
                "first3s_closeup": to_float(r.get("summary_first_3s_closeup_ratio")),
                "closeup_ratio":   to_float(r.get("summary_closeup_ratio")),
                "first_cut_dur":   to_float(r.get("summary_first_cut_duration")),
                "two_person_ratio": to_float(r.get("summary_two_person_ratio")),
                "content_type": (r.get("content_type") or "").strip(),
            }
    return list(vids.values())

def load_all(content_type=None):
    vids = []
    for p in sorted(glob.glob(os.path.join(CRAWL_DIR, "*.csv"))):
        vids += load_rows(p, "crawl")
    for p in sorted(glob.glob(os.path.join(OWN_DIR, "*.csv"))):
        vids += load_rows(p, "own_published")
    # video_id 중복 제거 (여러 CSV 걸쳐) — content_type 있는 행이 없는 행에 우선
    uniq = {}
    for v in vids:
        prev = uniq.get(v["video_id"])
        if prev and prev["content_type"] and not v["content_type"]:
            continue
        uniq[v["video_id"]] = v
    vids = list(uniq.values())
    if content_type:
        vids = [v for v in vids if v["content_type"] == content_type]
    return vids

def rank_by_tag(vids, field, min_n=4):
    """태그별 median ER/save_rate/views 집계 후 ER 내림차순 정렬"""
    buckets = {}
    for v in vids:
        vals = v[field] if isinstance(v[field], list) else ([v[field]] if v[field] else [])
        for t in vals:
            buckets.setdefault(t, []).append(v)
    out = []
    for tag, vs in buckets.items():
        ers = [x["er"] for x in vs]
        if not [e for e in ers if e is not None]:
            continue
        out.append({
            "tag": tag,
            "label": label_of(tag),
            "n": len(vs),
            "median_er": median(ers),
            "median_save_rate": median([x["save_rate"] for x in vs]),
            "median_views": median([x["views"] for x in vs]),
            "low_sample": len(vs) < min_n,
        })
    return sorted(out, key=lambda x: (x["median_er"] is not None, x["median_er"]), reverse=True)

def cut_metrics(vids):
    """분석 완료 영상만 → ER 기준 상/하위 1/3 컷 지표 비교"""
    analyzed = [v for v in vids if v["cut_count"] is not None and v["er"] is not None]
    analyzed.sort(key=lambda x: x["er"])
    n = len(analyzed)
    if n < 6:
        return {"n_analyzed": n, "note": "표본 부족"}
    third = max(1, n // 3)
    bottom, top = analyzed[:third], analyzed[-third:]
    def agg(group):
        return {
            "median_cut_count":     median([x["cut_count"] for x in group]),
            "median_video_len":     median([x["video_len"] for x in group]),
            "median_first3s_closeup": median([x["first3s_closeup"] for x in group]),
            "median_closeup_ratio": median([x["closeup_ratio"] for x in group]),
            "median_first_cut_dur": median([x["first_cut_dur"] for x in group]),
            "median_two_person":    median([x["two_person_ratio"] for x in group]),
        }
    return {"n_analyzed": n, "top_third": agg(top), "bottom_third": agg(bottom)}

def build(content_type=None):
    vids = load_all(content_type)
    own = [v for v in vids if v["source"] == "own_published"]
    baseline = {
        "median_er": median([v["er"] for v in vids]),
        "median_save_rate": median([v["save_rate"] for v in vids]),
        "median_views": median([v["views"] for v in vids]),
    }
    rules = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "content_type_filter": content_type or "none",
        "n_videos_total": len(vids),
        "n_own_published": len(own),
        "baseline": baseline,
        "trigger_ranking_grammar": rank_by_tag(vids, "grammar_tags"),
        "trope_ranking":           rank_by_tag(vids, "trope_tags"),
        "story_type_ranking":      rank_by_tag(vids, "story_type"),
        "hook_type_ranking":       rank_by_tag(vids, "hook_type"),
        "cut_metrics":             cut_metrics(vids),
    }
    # 자체발행 별도 집계 (예측 vs 실제)
    if own:
        rules["own_published_summary"] = {
            "n": len(own),
            "median_er": median([v["er"] for v in own]),
            "median_save_rate": median([v["save_rate"] for v in own]),
        }
    return rules

def write_md(rules):
    b = rules["baseline"]
    L = []
    L.append("# 규칙_최신 (자동 생성)\n")
    ct = rules.get("content_type_filter", "none")
    ct_note = f" · content_type={ct} 필터" if ct != "none" else ""
    L.append(f"> 생성 시각: {rules['generated_at']} · 분석 영상 {rules['n_videos_total']}편 "
             f"(자체발행 {rules['n_own_published']}편 포함){ct_note}\n")
    L.append(f"**전체 기준선** — 반응률 중앙값 {b['median_er']}% · 저장률 {b['median_save_rate']}% · 조회수 {b['median_views']}\n")

    L.append("\n## 상황 순위 (대사문법 태그 · 반응률 중앙값)\n")
    L.append("| 상황 | n | 반응률% | 저장률% | 조회수 |")
    L.append("|---|---|---|---|---|")
    for t in rules["trigger_ranking_grammar"]:
        flag = " ⚠️저표본" if t["low_sample"] else ""
        L.append(f"| {t['label']}{flag} | {t['n']} | {t['median_er']} | {t['median_save_rate']} | {t['median_views']} |")

    L.append("\n## 설정 순위 (저장·공유 견인 · 반응률 중앙값)\n")
    L.append("| 설정 | n | 반응률% | 저장률% |")
    L.append("|---|---|---|---|")
    for t in rules["trope_ranking"]:
        flag = " ⚠️저표본" if t["low_sample"] else ""
        L.append(f"| {t['label']}{flag} | {t['n']} | {t['median_er']} | {t['median_save_rate']} |")

    cm = rules["cut_metrics"]
    if "top_third" in cm:
        L.append(f"\n## 컷/연출 지표 — 상위 1/3 vs 하위 1/3 (분석 {cm['n_analyzed']}편)\n")
        L.append("| 지표 | 상위 1/3 | 하위 1/3 |")
        L.append("|---|---|---|")
        t, bo = cm["top_third"], cm["bottom_third"]
        L.append(f"| 총 컷 수 | {t['median_cut_count']} | {bo['median_cut_count']} |")
        L.append(f"| 영상 길이(초) | {t['median_video_len']} | {bo['median_video_len']} |")
        L.append(f"| 첫3초 클로즈업 비중 | {t['median_first3s_closeup']} | {bo['median_first3s_closeup']} |")
        L.append(f"| 전체 클로즈업 비중 | {t['median_closeup_ratio']} | {bo['median_closeup_ratio']} |")
        L.append(f"| 첫 컷 길이(초) | {t['median_first_cut_dur']} | {bo['median_first_cut_dur']} |")
        L.append(f"| 투샷 비중 | {t['median_two_person']} | {bo['median_two_person']} |")

    if "own_published_summary" in rules:
        o = rules["own_published_summary"]
        L.append(f"\n## 자체발행 성과 (예측 vs 실제 · {o['n']}편)\n")
        L.append(f"- 자체발행 반응률 중앙값 {o['median_er']}% (전체 기준선 {b['median_er']}%)")
        L.append(f"- 자체발행 저장률 중앙값 {o['median_save_rate']}%")

    L.append("\n---\n*이 파일은 engine.py가 자동 생성한다. 직접 수정하지 말 것.*")
    return "\n".join(L)

if __name__ == "__main__":
    import sys
    ct = None
    if "--content-type" in sys.argv:
        ct = sys.argv[sys.argv.index("--content-type") + 1]
    rules = build(ct)
    with open(os.path.join(BASE, "규칙_최신.json"), "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
    with open(os.path.join(BASE, "규칙_최신.md"), "w", encoding="utf-8") as f:
        f.write(write_md(rules))
    print("규칙 갱신 완료:", rules["n_videos_total"], "편")
    print("상황 1위:", rules["trigger_ranking_grammar"][0]["label"],
          rules["trigger_ranking_grammar"][0]["median_er"], "%")
