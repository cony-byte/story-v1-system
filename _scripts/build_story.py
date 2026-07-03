#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메인스토리 자동요약 — 캐릭터 + 에피소드를 묶어 캐릭터별 메인스토리(_story.json) 생성.

★ LLM 교체 대비 구조: 요약 단계가 '백엔드'로 분리되어 있다.
   - "rule"  : 현재 기본값. 규칙 기반 f-string (비용 0·결정론적)
   - "llm"   : 나중에 summarize_llm() 안에 LLM 호출만 구현하면 됨 (프롬프트는 이미 build_prompt로 준비됨)
   나머지 파이프라인(입력 수집 assemble_context / 저장 형식)은 백엔드와 무관하게 그대로 재사용된다.

실행:
  python3 _scripts/build_story.py                    # rule 방식으로 전체 생성
  python3 _scripts/build_story.py --method llm        # llm 방식(미구현시 rule로 폴백)
  python3 _scripts/build_story.py --print-prompt char_seojun   # LLM에 보낼 프롬프트만 확인
"""
import os, sys, json, argparse, datetime
from collections import Counter
from _common import (char_dirs, load_character, load_episodes, load_rules,
                     load_heroine, write_json)

PROMPT_VERSION = "story_v1"


# ---------- 1) 입력 수집 (백엔드 공통) ----------
def assemble_context(char, eps):
    """요약기에 넘길 구조화된 입력. LLM/규칙 어느 쪽이든 이걸 받는다.
    여주는 고정 상수 02_여주.json에서 읽는다(하드코딩 금지)."""
    eps_sorted = sorted(eps, key=lambda e: e.get("id", ""))
    heroine = load_heroine().get("name", "여주")
    return {
        "character": {k: char.get(k) for k in (
            "id", "name", "archetype", "goal", "primary_trigger", "secondary_trigger",
            "gap_surface", "gap_hidden", "signature_action", "first3s_hook",
            "tension_partner", "taboo_barrier")},
        "heroine": heroine,
        "episodes": [{
            "id": e["id"], "title": e.get("title", ""),
            "target_trigger": e.get("target_trigger", ""),
            "emotion_shift": e.get("emotion_shift", ""),
            "core_event": e.get("core_event", ""),
            "logline": e.get("logline", ""),
            "beats": e.get("beats", {}),
        } for e in eps_sorted],
    }


def trigger_label(rules, tag):
    for t in rules["trigger_ranking_grammar"] + rules["trope_ranking"]:
        if t["tag"] == tag:
            return t["label"]
    return tag


def central_trigger(ctx):
    trigs = [e["target_trigger"] for e in ctx["episodes"] if e["target_trigger"]]
    if trigs:
        return Counter(trigs).most_common(1)[0][0]
    return ctx["character"].get("primary_trigger", "")


# ---------- 2) 프롬프트 생성 (LLM 교체용 · 지금은 미사용이지만 미리 준비) ----------
def build_prompt(ctx, rules):
    """LLM에 보낼 프롬프트. summarize_llm()이 이걸 그대로 쓴다."""
    c = ctx["character"]
    central_lbl = trigger_label(rules, central_trigger(ctx))
    eps_lines = "\n".join(
        f"- [{e['id']}] {e['title']} / 트리거:{trigger_label(rules, e['target_trigger'])}"
        f" / 감정변화:{e['emotion_shift']} / 핵심사건:{e['core_event']}\n    로그라인: {e['logline']}"
        for e in ctx["episodes"]
    )
    system = (
        "너는 숏폼 드라마 기획 요약가다. 아래 남자 캐릭터와 그의 에피소드들을 읽고, "
        "여주와의 관계 축을 중심으로 시리즈 전체를 관통하는 '메인스토리'를 2~3문장으로 요약하라. "
        "과장·클리셰 없이 캐릭터의 갭(겉↔속)과 중심 트리거가 드러나게 쓴다. 한국어."
    )
    user = (
        f"[여주] {ctx['heroine']}\n"
        f"[남캐] {c['name']} · {c['archetype']}\n"
        f"- 중심 트리거: {central_lbl}\n"
        f"- 갭: 겉={c['gap_surface']} / 속={c['gap_hidden']}\n"
        f"- 시그니처: {c['signature_action']}\n"
        f"- 첫3초 훅: {c['first3s_hook']}\n"
        f"- 텐션 상대: {c['tension_partner']} / 금기: {c['taboo_barrier']}\n\n"
        f"[에피소드 {len(ctx['episodes'])}개]\n{eps_lines}\n\n"
        "출력: 메인스토리 요약(2~3문장)만."
    )
    return {"system": system, "user": user}


# ---------- 3) 요약 백엔드 (교체 지점) ----------
def summarize_rule(ctx, rules):
    """현재 기본: 규칙 기반 f-string. 비용 0·결정론적."""
    c = ctx["character"]
    central_lbl = trigger_label(rules, central_trigger(ctx))
    return (f"{c['archetype']} '{c['name']}'이(가) {ctx['heroine']}을(를) 두고 "
            f"'{central_lbl}' 트리거를 회수하는 {len(ctx['episodes'])}부작 시리즈.")


def summarize_llm(ctx, rules):
    """★ 나중에 여기만 구현하면 LLM 요약으로 전환된다.
    build_prompt(ctx, rules)로 프롬프트를 만들어 LLM에 보내고, 응답 텍스트(str)를 반환하면 끝.
    정적 파일 구조라 API 키는 환경변수 등으로 주입 권장(키 하드코딩 금지)."""
    _ = build_prompt(ctx, rules)  # prompt = _  → LLM 호출부에 전달
    raise NotImplementedError(
        "LLM 요약 미구현. summarize_llm() 안에서 build_prompt(ctx, rules) 결과를 "
        "LLM에 보내고 응답 텍스트를 return 하도록 구현하세요.")


SUMMARIZERS = {"rule": summarize_rule, "llm": summarize_llm}


# ---------- 4) 저장 (백엔드 공통) ----------
def build_one(cdir, rules, method):
    char = load_character(cdir)
    eps = load_episodes(cdir)
    ctx = assemble_context(char, eps)
    central = central_trigger(ctx)

    used = method
    try:
        logline = SUMMARIZERS[method](ctx, rules)
    except NotImplementedError:
        logline = summarize_rule(ctx, rules)   # llm 미구현 시 rule로 폴백(파이프라인 안 끊김)
        used = "rule (llm 미구현 폴백)"

    story = {
        "character_id": char["id"],
        "title": f"{char.get('name','')} — {trigger_label(rules, central)}",
        "central_trigger": central,
        "logline": logline,
        "arc": [{"episode_id": e["id"], "title": e["title"], "logline": e["logline"]}
                for e in ctx["episodes"]],
        "n_episodes": len(ctx["episodes"]),
        "summary_method": used,      # 어떤 백엔드로 요약됐는지
        "model": None,               # llm 전환 시 모델명 기록
        "prompt_version": PROMPT_VERSION,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "_note": "build_story.py 자동 생성물. 직접 수정하지 말 것.",
    }
    write_json(os.path.join(cdir, "_story.json"), story)
    return story


def main(method="rule"):
    rules = load_rules()
    results = [build_one(c, rules, method) for c in char_dirs()]
    print(f"메인스토리 자동요약 완료: {len(results)} 캐릭터 (method={method})")
    for s in results:
        print(f"  {s['title']}  ({s['n_episodes']}화) · {s['summary_method']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=["rule", "llm"], default="rule")
    ap.add_argument("--print-prompt", metavar="char_id", help="해당 캐릭터의 LLM 프롬프트만 출력")
    args = ap.parse_args()

    if args.print_prompt:
        rules = load_rules()
        for c in char_dirs():
            ch = load_character(c)
            if ch["id"] == args.print_prompt:
                p = build_prompt(assemble_context(ch, load_episodes(c)), rules)
                print("=== SYSTEM ===\n" + p["system"] + "\n\n=== USER ===\n" + p["user"])
                break
        else:
            print(f"캐릭터 {args.print_prompt} 없음")
    else:
        main(args.method)
