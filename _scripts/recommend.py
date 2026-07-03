#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
추천 이유 생성기 — 캐릭터/에피소드의 recommendation 객체를 만든다.
결과: { for, label, reasons[], method, model, prompt_version, generated_at }

★ LLM 교체 대비 구조 (build_story.py와 동일 컨벤션):
   assemble_context → build_prompt → recommend_rule / recommend_llm → 출력
   - "rule" : 현재 기본값. 규칙_최신.json 성과 + 아키타입 매핑표 (비용 0·결정론적)
   - "llm"  : 나중에 recommend_llm() 안에 LLM 호출만 구현하면 됨 (프롬프트는 build_prompt로 준비됨)
   입력 수집·데이터 칩·저장 형식은 백엔드와 무관하게 재사용된다.

핵심 원칙: **데이터 칩(숫자)은 규칙엔진이 확정**한다. LLM으로 바꿔도 이 칩은 변형 금지.
           LLM은 트리거 판단 + 궁합·감정선 '판단 칩'만 담당(설계: 추천AI_설계.md).

실행:
  python3 _scripts/recommend.py all                       # 전 캐릭터+에피소드 미리보기
  python3 _scripts/recommend.py char char_seojun --json    # 캐릭터 recommendation JSON
  python3 _scripts/recommend.py ep char_seojun ep_02 --json # 에피소드 recommendation JSON
  python3 _scripts/recommend.py tag protective_claim_or_rescue  # 데이터 칩만
  python3 _scripts/recommend.py char char_seojun --apply   # 파일에 recommendation 기록
  python3 _scripts/recommend.py char char_seojun --print-prompt  # LLM 프롬프트만 확인
  (--method llm : llm 백엔드. 미구현 상태면 rule로 자동 폴백)
"""
import os, sys, glob, json, argparse, datetime
from _common import ROOT, CHAR_DIR, read_json, write_json, load_rules, char_dirs, load_character, load_episodes

PROMPT_VERSION = "reco_v1"
BASELINE_SAVE = 0.34   # 표기용(실값은 규칙_최신.json baseline 사용)

# 아키타입 ↔ 트리거 궁합 매핑 (rule 백엔드의 '판단 칩' 규칙. llm 전환 시 참고 지식으로 재사용 가능)
ARCHETYPE_AFFINITY = {
    "얼음 회장님": ["jealousy_possession_or_rival", "love_confession_or_desire"],
    "다정한 소꿉친구": ["protective_claim_or_rescue"],
    "나쁜남자·일진": ["jealousy_possession_or_rival", "threat_danger_or_revenge"],
    "열혈 직진남": ["choice_ultimatum_or_deadline", "love_confession_or_desire"],
    "미스터리 전학생": ["secret_lie_or_reveal", "forbidden_love"],
}


# ---------- 공통 헬퍼: 규칙엔진 조회 ----------
def _ranked(rules, key):
    rows = rules.get(key, [])
    return sorted(rows, key=lambda r: (r["median_er"] is not None, r["median_er"]), reverse=True)


def find_entry(rules, tag):
    for key in ("trigger_ranking_grammar", "trope_ranking"):
        rows = _ranked(rules, key)
        for i, r in enumerate(rows, start=1):
            if r["tag"] == tag:
                return r, i, len(rows)
    return None, None, None


def label_of(rules, tag):
    e, _, _ = find_entry(rules, tag)
    return (e.get("label") if e else None) or tag


def used_triggers(exclude_char=None):
    used = set()
    for cdir in char_dirs():
        ch = load_character(cdir) or {}
        if exclude_char and ch.get("id") == exclude_char:
            continue
        for k in ("primary_trigger", "secondary_trigger"):
            if ch.get(k):
                used.add(ch[k])
        for ep in load_episodes(cdir):
            if ep.get("target_trigger"):
                used.add(ep["target_trigger"])
    return used


def pct_bucket(rank, total):
    p = rank / total
    for thr, txt in ((0.05, "5%"), (0.10, "10%"), (0.25, "25%"), (0.50, "50%")):
        if p <= thr:
            return txt
    return None


# ---------- 데이터 칩 (사실 · 백엔드 공통, 변형 금지) ----------
def data_chips(rules, tag, is_unused):
    """규칙엔진 근거 칩. (강점칩, 주의칩) 튜플 반환."""
    base = rules["baseline"]
    entry, rank, total = find_entry(rules, tag)
    strong, notes = [], []
    if entry is None:
        return [], [f"⚠ '{tag}' 은(는) 규칙엔진 랭킹에 없음 — 데이터 근거 없음"]

    if rank == 1:
        strong.append("몰입도(ER) 전체 1위")
    else:
        bucket = pct_bucket(rank, total)
        if bucket in ("5%", "10%"):
            strong.append(f"최근 성과 상위 {bucket}")
        else:
            strong.append(f"몰입도(ER) 상위권 ({rank}/{total})")

    sr = entry.get("median_save_rate")
    if sr is not None:
        if sr >= base["median_save_rate"] + 0.08:
            strong.append("저장률 최상위")
        elif sr >= base["median_save_rate"]:
            strong.append("저장률 baseline 상회")
        else:
            notes.append("⚠ 저장률 baseline 미만 — 저장 유도 필요")

    mv = entry.get("median_views")
    if mv is not None:
        if mv >= base["median_views"]:
            strong.append("도달(조회수) 강함")
        else:
            notes.append("⚠ 도달 낮음 — 초반 훅 보강 필요")

    n = entry.get("n")
    if entry.get("low_sample"):
        strong.append(f"표본 적은 블루오션(실험가치↑, n={n}편)")
    elif n:
        strong.append(f"검증 표본 충분(n={n}편)")

    if is_unused:
        strong.append("아직 안 쓴 트리거")
    return strong, notes


# ---------- 1) 입력 수집 (백엔드 공통) ----------
def assemble_context(entity, char, eps, ep=None):
    """recommend_rule / recommend_llm 어느 쪽이든 이 구조화 입력을 받는다."""
    if entity == "character":
        subject = char.get("primary_trigger", "")
        for_field = "primary_trigger"
        prior_target, this_emotion = None, None
    else:  # episode
        subject = ep.get("target_trigger", "")
        for_field = "target_trigger"
        prev = [e for e in sorted(eps, key=lambda x: x.get("id", "")) if e.get("id", "") < ep.get("id", "")]
        prior_target = prev[-1].get("target_trigger") if prev else None
        this_emotion = ep.get("emotion_shift") or None

    return {
        "entity": entity,
        "for_field": for_field,
        "subject_trigger": subject,
        "candidates": [char.get("primary_trigger"), char.get("secondary_trigger")],
        "character": {k: char.get(k) for k in (
            "id", "name", "archetype", "primary_trigger", "secondary_trigger",
            "gap_surface", "gap_hidden", "taboo_barrier")},
        "prior_target": prior_target,
        "this_emotion": this_emotion,
        "is_unused": subject not in used_triggers(exclude_char=char.get("id")),
    }


# ---------- 2) 프롬프트 (LLM 교체용 · 지금은 미사용이지만 준비) ----------
def build_prompt(ctx, rules):
    c = ctx["character"]
    facts_strong, facts_notes = data_chips(rules, ctx["subject_trigger"], ctx["is_unused"])
    facts = "\n".join(f"  - {x}" for x in facts_strong + facts_notes) or "  - (없음)"
    system = (
        "너는 숏폼 드라마 기획 추천가다. 아래 캐릭터/에피소드와 '확정된 데이터 칩'을 보고, "
        "이 트리거를 추천하는 이유를 기획자가 이해하는 짧은 칩으로 정리하라. "
        "규칙: (1) 데이터 칩은 그대로 인용하고 숫자를 새로 만들지 말 것 "
        "(2) 궁합·감정선 같은 판단 칩만 추가(최대 3개) (3) 한국어 한 줄 칩."
    )
    user = (
        f"[대상] {ctx['entity']} · for={ctx['for_field']}\n"
        f"[캐릭터] {c['name']} · {c['archetype']} / 갭 겉={c['gap_surface']} 속={c['gap_hidden']}\n"
        f"[금기] {c['taboo_barrier']}\n"
        f"[추천 트리거] {label_of(rules, ctx['subject_trigger'])} ({ctx['subject_trigger']})\n"
        f"[직전 화 트리거] {ctx['prior_target']} / [이번 감정변화] {ctx['this_emotion']}\n"
        f"[확정 데이터 칩]\n{facts}\n\n"
        "출력: reasons 배열(문자열 칩들)만 JSON으로."
    )
    return {"system": system, "user": user}


# ---------- 3) 추천 백엔드 (교체 지점) ----------
def _judgment_rule(ctx, rules):
    """rule 백엔드의 판단 칩 — 아키타입 매핑표·금기·시퀀스 규칙에서 결정론적으로."""
    c, tag, chips = ctx["character"], ctx["subject_trigger"], []
    if ctx["entity"] == "episode" and tag and tag == c.get("primary_trigger"):
        chips.append("현재 캐릭터와 궁합이 좋음")
    if tag in ARCHETYPE_AFFINITY.get(c.get("archetype", ""), []):
        chips.append(f"'{c['archetype']}' 아키타입과 궁합이 좋음")
    if c.get("taboo_barrier"):
        chips.append("금기 설정과 결합해 긴장↑")
    if ctx["entity"] == "episode" and ctx["this_emotion"]:
        chips.append(f"다음 감정선({ctx['this_emotion']})으로 자연스럽게 이어짐")
    return chips


def recommend_rule(ctx, rules):
    strong, notes = data_chips(rules, ctx["subject_trigger"], ctx["is_unused"])
    reasons = strong + _judgment_rule(ctx, rules) + notes   # 강점 → 판단 → ⚠주의 순
    return reasons, None  # (reasons, model)


def recommend_llm(ctx, rules):
    """★ 나중에 여기만 구현하면 LLM 추천으로 전환된다.
    build_prompt(ctx, rules)를 LLM에 보내고, 응답의 reasons 배열을 반환.
    반드시 데이터 칩(data_chips)은 그대로 유지·병합하고, 판단 칩만 LLM이 쓰게 할 것.
    API 키는 환경변수 주입 권장(하드코딩 금지)."""
    _ = build_prompt(ctx, rules)
    raise NotImplementedError(
        "LLM 추천 미구현. recommend_llm()에서 build_prompt 결과를 LLM에 보내고 "
        "reasons 배열을 return 하도록 구현하세요. 데이터 칩은 data_chips()로 고정.")


BACKENDS = {"rule": recommend_rule, "llm": recommend_llm}


# ---------- 4) 조립 (백엔드 공통) ----------
def build_recommendation(entity, char, eps, method="rule", ep=None):
    rules = load_rules()
    ctx = assemble_context(entity, char, eps, ep)
    used = method
    try:
        reasons, model = BACKENDS[method](ctx, rules)
    except NotImplementedError:
        reasons, model = recommend_rule(ctx, rules)
        used = "rule (llm 미구현 폴백)"
    return {
        "for": ctx["for_field"],
        "label": label_of(rules, ctx["subject_trigger"]),
        "reasons": reasons,
        "method": used,
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def _find_char_dir(char_id):
    d = os.path.join(CHAR_DIR, char_id)
    return d if os.path.isdir(d) else None


def _apply(path, obj):
    """authored 파일의 recommendation 키를 갱신(위치 유지, 없으면 추가)."""
    d = read_json(path)
    d["recommendation"] = obj
    write_json(path, d)


# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["all", "char", "ep", "tag"])
    ap.add_argument("a", nargs="?", help="char_id 또는 트리거태그")
    ap.add_argument("b", nargs="?", help="ep_id (mode=ep)")
    ap.add_argument("--method", choices=["rule", "llm"], default="rule")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--apply", action="store_true", help="대상 파일에 recommendation 기록")
    ap.add_argument("--print-prompt", action="store_true")
    args = ap.parse_args()
    rules = load_rules()

    def emit(obj, path=None):
        if args.print_prompt:
            return  # 프롬프트 모드는 아래서 처리
        if args.json:
            print(json.dumps(obj, ensure_ascii=False, indent=2))
        else:
            print(f"추천: {obj['label']}   (method={obj['method']})")
            print("추천 이유:")
            for r in obj["reasons"]:
                print(f"  - {r}")
        if args.apply and path:
            _apply(path, obj)
            print(f"  → 기록: {os.path.relpath(path, ROOT)}")

    if args.mode == "tag":
        strong, notes = data_chips(rules, args.a, args.a not in used_triggers())
        print(f"[{label_of(rules, args.a)}] 데이터 칩:")
        for x in strong + notes:
            print(f"  - {x}")
        return

    if args.mode == "char":
        cdir = _find_char_dir(args.a)
        char, eps = load_character(cdir), load_episodes(cdir)
        if args.print_prompt:
            p = build_prompt(assemble_context("character", char, eps), rules)
            print("=== SYSTEM ===\n" + p["system"] + "\n\n=== USER ===\n" + p["user"]); return
        emit(build_recommendation("character", char, eps, args.method),
             os.path.join(cdir, "character.json"))
        return

    if args.mode == "ep":
        cdir = _find_char_dir(args.a)
        char, eps = load_character(cdir), load_episodes(cdir)
        ep = next((e for e in eps if e.get("id") == args.b), None)
        if ep is None:
            print(f"에피소드 {args.b} 없음"); return
        if args.print_prompt:
            p = build_prompt(assemble_context("episode", char, eps, ep), rules)
            print("=== SYSTEM ===\n" + p["system"] + "\n\n=== USER ===\n" + p["user"]); return
        emit(build_recommendation("episode", char, eps, args.method, ep),
             os.path.join(cdir, "episodes", f"{args.b}.json"))
        return

    # all: 미리보기
    for cdir in char_dirs():
        char, eps = load_character(cdir), load_episodes(cdir)
        rc = build_recommendation("character", char, eps, args.method)
        print(f"[{char['id']}] 캐릭터 → {rc['label']}: {', '.join(rc['reasons'])}")
        for ep in sorted(eps, key=lambda e: e.get("id", "")):
            re = build_recommendation("episode", char, eps, args.method, ep)
            print(f"    {ep['id']} → {re['label']}: {', '.join(re['reasons'])}")


if __name__ == "__main__":
    main()
