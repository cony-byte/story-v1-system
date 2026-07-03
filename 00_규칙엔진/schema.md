# 데이터 스키마 (v2 — 캐릭터 검증 실험 구조)

이 워크스페이스의 **데이터 모델**이다. 모든 파일은 이 스키마를 따른다.
목적: **매력적인 남캐를 대량 생성 → 검증 → IP 후보 선정.** 드라마(에피소드)는 캐릭터를 검증하기 위한 실험 도구다.

## 설계 원칙

1. **세계관·여주는 고정 상수(통제변수)**다. 각각 1개만 존재하며 바뀌지 않는다.
2. **캐릭터(남캐)가 실험 변수**다. 대량 생성되며, 각 캐릭터는 폴더 하나 = 자기완결 실험 레코드.
3. **에피소드는 캐릭터에 물리적으로 종속**된다 (`캐릭터폴더/episodes/`).
4. **손으로 관리하는 링크는 `episode.character_id` 하나뿐.** 나머지(메인스토리·성과·IP후보)는 전부 자동 생성 파생물.
5. **`_` 접두사 = 자동 생성물.** 직접 수정하지 않는다 (`규칙_최신.json`과 동일 철학).

## 파이프라인

```
세계관(고정) → 남캐 생성 → 에피소드 3~5개 → 메인스토리 자동요약 → 성과 측정 → IP 후보 선정
```

## 폴더 구조

```
기획-v1/
├── 00_규칙엔진/          검증 기준 (engine.py, 규칙_최신.json/.md, 로우데이터/, 발행성과/)
├── 01_세계관.json        ← 고정 1개
├── 02_여주.json          ← 고정 1개
├── 03_캐릭터/            ← 남캐 독립 DB
│    └── char_{슬러그}/
│         ├── character.json        (남캐 정의 · authored)
│         ├── episodes/
│         │    ├── ep_01.json       (시행 · authored · storyboard 내포)
│         │    └── ep_02.json …
│         ├── _story.json           (메인스토리 자동요약 · 파생)
│         └── _performance.json     (성과 자동롤업 · 파생)
├── 04_심사위원/          rubric.md + judge.py
├── _scripts/            build_story.py · build_performance.py · build_ip.py
└── _IP후보.json          전체 캐릭터 성과 랭킹 (자동 · 최종 산출물)
```

## 엔티티

### 1. world 세계관 — `01_세계관.json` (고정 1개)
```
id, name, tone, setting, localization_rules[], _fixed=true, created_at, updated_at
```

### 2. heroine 여주 — `02_여주.json` (고정 1개)
```
id, world_id, name, grade_class, profile, role, _fixed=true, created_at, updated_at
```

> **입력폼**: 세계관·여주는 각 1개 고정 상수라, 둘을 한 파일로 입력하는 폼 `_고정설정_템플릿.json`(루트) 하나만 둔다.
> `world` 블록 → `01_세계관.json`, `heroine` 블록 → `02_여주.json`으로 저장. 최초 1회 세팅.
> 여주 이름 등은 스크립트가 `02_여주.json`에서 읽는다(하드코딩 금지).

### 3. character 남캐 — `03_캐릭터/{id}/character.json`
```
id            : char_{영문슬러그} (폴더명과 일치)
world_id      : "world_highschool" (고정)
heroine_id    : "heroine_harin" (고정)
goal          : 캐릭터 목표 (설렘 | 저장유도 | 댓글유도) — 입력폼 STEP1. 비우면 AI 추천
name, grade_class, archetype
primary_trigger   : 1차 트리거 (규칙_최신.json 트리거 키). ★고유 제약 없음 — 캐릭터 비교가 실험 목적
secondary_trigger : 2차 트리거
gap_surface   : 겉모습 (강함)
gap_hidden    : 여주 앞에서만 (약함)
signature_action, first3s_hook
tension_partner : 관계 텐션 상대 (여주/라이벌). ※ 입력폼 필드명과 일치 (구 rival)
taboo_barrier : 금기·장벽 (있으면)
recommendation : 이 캐릭터(특히 primary_trigger)를 왜 추천했는지 기획 언어로. ↓ "추천 이유 칩" 참고
                 { for:"primary_trigger", label:"② 위기구원", reasons:[ "칩", … ],
                   method:"rule"|"llm", model:(llm이면 모델명 else null), prompt_version }
status        : draft | reviewed | published
created_at, updated_at
```
※ v1의 `episode_ids[]`는 삭제. 캐릭터의 에피소드는 폴더(`episodes/`)로 자동 조회.
※ 입력폼은 `03_캐릭터/_템플릿/character.json`. `_`-접두사 필드(_brief·_goal_playbook·_ai_rules 등)는 폼 스캐폴딩이며 저장 레코드엔 남기지 않는다.

### 4. episode 에피소드 — `03_캐릭터/{id}/episodes/ep_NN.json`
```
id            : ep_NN (캐릭터 폴더가 네임스페이스. 전역 고유성은 경로로 보장)
character_id  : 소속 남캐 ID ← 유일한 authored 링크
goal          : 이번 화 목표 (설렘 | 저장유도 | 댓글유도) — 입력폼 STEP1
title, target_trigger
emotion_shift : 감정 변화 (예: 무관심 → 독점욕) — 입력폼 STEP3. BUILD→PAYOFF 곡선에 반영
core_event    : 핵심 사건 — 입력폼 STEP4. BUILD/PAYOFF 중심
logline
recommendation : 이 화의 target_trigger를 왜 추천했는지 기획 언어로. ↓ "추천 이유 칩" 참고
                 { for:"target_trigger", label:"④ 직진·최후통첩", reasons:[ "칩", … ],
                   method:"rule"|"llm", model, prompt_version }
beats         : HOOK/SETUP/BUILD/PAYOFF/HOOKOUT (객체)
storyboard    : { format, cuts[] } 또는 null  ← 에피소드 내포(후순위). v9 섹션A 컷 계약
judge_score   : 최근 심사 점수 (0~100, 미평가면 null)
status        : draft | reviewed | published
── 발행 성과 (발행 후 채움 · 크롤링 CSV와 동일 지표) ──
published_at
metrics       : { views, likes, comments, shares, saves, duration_s, er_pct, save_rate_pct }
created_at, updated_at
```
※ v1의 `story_id`, `storyboard_id` 삭제. 스토리는 파생(_story.json), 스토리보드는 내포(storyboard).
※ 입력폼은 `03_캐릭터/_템플릿/episodes/ep_01.json`. `story_id`·`storyboard_id`(v1 잔재)는 폼에서 제거됨. 스토리보드는 `storyboard` 필드로 내포(후순위·null 가능).

### 5. _story.json (파생) — `03_캐릭터/{id}/_story.json`
`build_story.py`가 캐릭터 정의 + 에피소드 beats를 묶어 자동 생성.
```
character_id, title(자동), central_trigger(최빈 target_trigger),
logline(자동요약), arc[](에피소드별 로그라인),
summary_method("rule" | "llm"), model(llm이면 모델명, 아니면 null),
prompt_version, generated_at
```
> **요약 백엔드 교체 대비**: `build_story.py`는 입력수집(assemble_context) → 프롬프트(build_prompt) → 요약(summarize_rule/summarize_llm) → 저장으로 분리돼 있다.
> 지금은 `rule`(규칙 기반 f-string, 비용 0). 나중에 `summarize_llm()`에 LLM 호출만 구현하면 `--method llm`으로 전환된다(프롬프트는 이미 준비됨). `summary_method`/`model` 필드로 무엇이 생성했는지 추적한다.

### 6. _performance.json (파생) — `03_캐릭터/{id}/_performance.json`
`build_performance.py`가 캐릭터의 발행 에피소드 metrics를 롤업.
```
character_id, n_episodes, n_published,
median_er, median_save_rate, median_views, total_views,
character_score, vs_baseline_er, generated_at
```

### 7. _IP후보.json (파생, 최종 산출물) — 루트
`build_ip.py`가 전체 캐릭터 성과를 정렬.
```
generated_at, baseline_er,
ranking[] : { rank, character_id, name, character_score, median_er, median_views, n_published, ip_candidate(bool) }
```

## 추천 이유 칩 (recommendation.reasons)

AI가 트리거를 추천할 때 **왜 좋은지**를 통계 숫자 나열이 아니라 **기획자가 바로 이해하는 한 줄 칩**으로 담는다.
각 칩은 아래 어휘 중 하나를 쓰되, 반드시 데이터/설정 근거가 있어야 한다 (근거 없는 칩 금지).

| 칩 (기획 언어) | 근거 · 판정 기준 | 출처 |
|---|---|---|
| `최근 성과 상위 N%` | 트리거 ER 랭킹 백분위 (상위 5/10/25%) | 규칙_최신.json `trigger_ranking_grammar` |
| `몰입도(ER) 1위` / `상위권` | ER 랭킹 순위 | 규칙_최신.json |
| `저장률 최상위` | save_rate 랭킹 상위 & baseline(0.34) 상회 | 규칙_최신.json |
| `도달(조회수) 강함` | median_views 상위 & baseline(108,250) 상회 | 규칙_최신.json |
| `검증 표본 충분(n=N편)` | n≥4 & low_sample=false | 규칙_최신.json |
| `표본 적은 블루오션(실험가치↑)` | low_sample=true (아직 덜 검증됨) | 규칙_최신.json |
| `아직 안 쓴 트리거` | 다른 캐릭터/에피소드가 사용하지 않은 트리거 (포트폴리오 다양성) | 03_캐릭터/ 교차 조회 |
| `{아키타입}과 궁합이 좋음` | 아키타입 ↔ 트리거 매핑표(ARCHETYPE_AFFINITY) | rule 판단칩 |
| `금기 설정과 결합해 긴장↑` | taboo_barrier 존재 | rule 판단칩 |
| `현재 캐릭터와 궁합이 좋음` | 이번 화 target == 캐릭터 primary_trigger | rule 판단칩 (에피소드) |
| `다음 감정선({A}→{B})으로 자연스럽게 이어짐` | 이번 화 emotion_shift 존재 | rule 판단칩 (에피소드) |
| ⚠ `도달 낮음 — 초반 훅 보강 필요` | median_views < baseline(108,250) | 데이터칩 |
| ⚠ `저장률 baseline 미만 — 저장 유도 필요` | save_rate < baseline(0.34) | 데이터칩 |

칩은 두 종류다: **데이터칩**(규칙엔진 성과 = 사실, 변형 금지) + **판단칩**(궁합·감정선 등).

- **개수:** 3~5개 권장. 강점 → 판단 → ⚠주의 순. baseline 미달 지표는 강점칩 금지, ⚠칩으로만.
- **`label`:** 규칙_최신.json `label` 그대로 인용 (예: `② 위기구원`). 새 라벨 창작 금지.
- **생성:** `_scripts/recommend.py`가 만든다. `char {id}` / `ep {id} {ep}` / `tag {트리거}` / `all`.
  - 데이터칩 = 규칙엔진에서 계산. 판단칩 = 매핑표 규칙에서 계산. 둘 다 결정론적.

### 추천 백엔드 (rule → llm 교체 대비, `_story.json`과 동일 철학)

`recommend.py`는 `assemble_context → build_prompt → recommend_rule / recommend_llm → 조립`으로 분리돼 있다.
- 지금은 `method="rule"` (규칙엔진 + 아키타입 매핑표, 비용 0·결정론적).
- 나중에 `recommend_llm()`에 LLM 호출만 구현하면 `--method llm`으로 전환된다(프롬프트는 build_prompt로 준비됨).
- **핵심 계약:** LLM으로 바꿔도 **데이터칩(숫자)은 data_chips()가 고정**한다. LLM은 트리거 판단 + 판단칩만 담당(→ `추천AI_설계.md`).
- recommendation 객체의 `method`/`model`/`prompt_version` 필드로 무엇이 생성했는지 추적한다.

## 크롤링/발행 통일 지표 (규칙엔진 입력)

| 통일 필드 | 크롤링 CSV 컬럼 | 발행 metrics 필드 |
|---|---|---|
| video_id | source_video_id | ep_id |
| views | ranking_views | views |
| er_pct | ranking_ER%_(save+share+cmt)/views | er_pct |
| save_rate_pct | ranking_save_rate% | save_rate_pct |
| source | "crawl" | "own_published" |

> 발행 에피소드의 `metrics`가 채워지면, engine.py가 이를 크롤링 영상과 동일한 데이터 포인트로 흡수(피드백 루프).
> 참고: v1의 `관계성(relationship)` 엔티티는 확정 파이프라인에서 제외됨(필요 시 후속 추가).
