# 추천 AI 설계 — 하이브리드(규칙엔진 + LLM)

> 목적: 캐릭터/에피소드 생성 시 `recommendation` 필드를 **AI가 채우도록** 붙인다.
> 원칙: **숫자는 규칙엔진이, 말은 AI가.** AI는 통계를 만들지 않는다.
> 상태: 설계 문서(코드 미착수). 승인되면 이 계약대로 스크립트/프롬프트를 만든다.
> 작성: 2026-07-03 · 저장: 로컬 전용

---

## 1. 한 줄 요약

recommend.py가 **데이터 근거 칩(숫자)**을 확정해 넘기고, LLM은 **트리거 선택 + 판단 칩(궁합·감정선)**만 쓴다.
→ 통계 환각 0, AI는 기획 판단만 담당.

## 2. 역할 분담 (누가 무엇을)

| 구성요소 | 담당 | 산출 | 성격 |
|---|---|---|---|
| **규칙엔진** (규칙_최신.json) | 성과 통계 집계 | ER/저장률/조회수/표본 랭킹 | 결정론 · 사실 |
| **recommend.py** | 데이터 칩 계산 | "성과 상위 N%", "미사용 트리거" 등 | 결정론 · 사실 |
| **LLM (추천 AI)** | ① 트리거 선택 ② 판단 칩 작성 | 궁합·감정선·갭 칩 + 최종 recommendation 객체 | 판단 · 생성 |

핵심 경계: **LLM은 데이터 칩을 수정·생성하지 않는다.** recommend.py가 준 칩을 그대로 얹고, 판단 칩만 덧붙인다.

## 3. 데이터 흐름

```
캐릭터/에피소드 맥락 (아키타입·갭·직전 화 감정선 …)
        │
        ▼
recommend.py  ──(후보 트리거별 데이터 칩 + 성과 수치)──┐
        │                                              │
        ▼                                              ▼
   규칙_최신.json                               LLM 프롬프트에 주입
                                                       │
                                                       ▼
             LLM: 트리거 1개 선택 + 판단 칩 작성 + 데이터 칩 병합
                                                       │
                                                       ▼
                            recommendation { for, label, reasons[] }
                                                       │
                                                       ▼
                          character.json / ep_NN.json 에 기록 (로컬)
```

## 4. 입력 계약 (LLM에 주는 것)

1. **후보 트리거 성과표** — recommend.py가 전 트리거에 대해 뽑은 데이터 칩 + 원수치(ER 순위, 저장률, 조회수, n, low_sample, 미사용 여부).
2. **캐릭터 맥락** — archetype, gap_surface/gap_hidden, taboo_barrier, secondary_trigger.
3. **(에피소드) 시퀀스 맥락** — 같은 캐릭터의 직전 화 target_trigger·emotion_shift(감정선 연결 판단용), 이미 쓴 트리거 목록.
4. **어휘 제약** — schema.md "추천 이유 칩" 어휘표. 판단 칩은 이 어휘 안에서만.

## 5. 출력 계약 (LLM이 내는 것)

schema.md와 동일한 recommendation 객체. 규칙 3가지:

```json
{
  "for": "primary_trigger",
  "label": "규칙_최신.json label 그대로",
  "reasons": ["데이터 칩(recommend.py 원본 그대로)", "판단 칩(어휘표 내)", "..."]
}
```

- **데이터 칩은 변형 금지** — recommend.py 문자열을 그대로 복사.
- **판단 칩은 3개 이하** — 강점 위주, 필요 시 ⚠ 칩 포함.
- **label은 규칙엔진 값 인용** — 새 라벨 창작 금지.

## 6. 가드레일 (환각 차단)

1. **후처리 검증기**: LLM 출력의 데이터 칩이 recommend.py 원본 집합에 실제로 있는지 대조. 없는 숫자 칩이 나오면 거부·재생성.
2. **트리거 화이트리스트**: `label`/`for`가 규칙_최신.json·스키마 값과 일치하는지 확인.
3. **정직성 규칙**: baseline 미달 지표(도달·저장률)는 강점 칩으로 못 쓰고 ⚠ 칩으로만.

## 6-1. 현재 구현 상태 (2026-07-03)

**구조는 이미 rule↔llm 교체형으로 완성**됐다 (`_scripts/recommend.py`, `_story.json`과 동일 컨벤션).

```
assemble_context → build_prompt → recommend_rule / recommend_llm → 조립(build_recommendation)
```

- `method="rule"` (기본): 규칙엔진 데이터칩 + 아키타입 매핑표 판단칩. 지금 작동. 비용 0.
- `method="llm"`: `recommend_llm()`이 아직 stub(NotImplementedError) → 자동으로 rule 폴백.
- LLM을 붙일 때 손댈 곳은 **`recommend_llm()` 하나뿐.** `build_prompt()`가 프롬프트를 이미 만들어 둔다.
- 데이터칩은 `data_chips()`가 고정 → LLM으로 바꿔도 숫자 환각 불가.
- 결과에 `method`/`model`/`prompt_version` 기록.

즉 지금은 **순수 규칙 기반으로 돌아가고, LLM은 함수 하나 채우면 켜지는** 상태다.

## 7. 실행 형태 (LLM 켤 때 택1)

- **A. 로컬 스크립트 + API** — `_scripts/recommend_ai.py`가 recommend.py 결과를 프롬프트에 넣어 Anthropic API 호출 → recommendation 객체 반환. 자동화 가능, API 키 필요, 전 과정 로컬.
- **B. 이 대화/Cowork** — 현재처럼 챗에서 생성. 세팅·키 불필요, 수동.

두 형태 모두 위 입·출력 계약은 동일하다. A는 그 계약을 코드로 고정한 것.

## 8. 남은 결정 사항

- 궁합 판단을 LLM 자유판단으로 둘지 vs **아키타입↔트리거 매핑표**로 규칙화할지.
- 자체발행 표본(현재 0편)이 쌓이면 판단 칩 일부를 데이터 칩으로 승격하는 기준.
- 실행 형태 A/B 확정.

## 9. 다음 단계

1. 이 설계 승인.
2. (A 선택 시) recommend_ai.py + 검증기 초안.
3. 샘플 1캐릭터로 예측 vs 수동작성 비교, 프롬프트 튜닝.
