# 숏폼 드라마 자동 기획 시스템

숏폼(고등학교 청춘 로맨스) 드라마를 규칙엔진 + AI 추천으로 기획하는 시스템. 세계관·여주는 통제변수로 고정하고, 남캐(트리거)와 에피소드를 실험 단위로 대량 생성·검증한다.

## 구조

```
00_규칙엔진/        규칙엔진 — 크롤링 성과에서 상황/설정/반응률 순위 산출
  engine.py         라벨 매핑(내부 영문 ID → 한글 표시: 상황·설정·반응률)
  규칙_최신.json/.md 최신 규칙(성과 기준선)
  schema.md         데이터 스키마 정의
01_세계관.json      고정 상수 — 세계관(world_highschool)
02_여주.json        고정 상수 — 여주(heroine_harin)
_고정설정_템플릿.json  세계관+여주 입력폼(world/heroine 두 블록)
03_캐릭터/          캐릭터=폴더. 각 폴더에 character.json + episodes/ + 파생물
  _템플릿/          입력 브리프(캐릭터 5-STEP · 에피소드 3-STEP)
04_심사위원/        judge.py, rubric.md
_scripts/           빌드/추천 파이프라인
  recommend.py      추천 이유 생성 (method=rule, llm 교체형)
  build_story.py    메인스토리 자동 요약(_story.json)
  build_relations.py 관계성 자동 생성(_relations.json)
  build_performance.py / build_all.py / validate_schema.py / _common.py
app-shell.html      로그인 이후 대시보드 UI (정적 레이아웃 쉘)
_폼_시안/           캐릭터/에피소드 생성폼 시안
schema_v2_설계.md   / 추천AI_설계.md   설계 문서
```

## 핵심 개념

- **고정 상수**: 세계관·여주는 각 1개 고정(변인 통제). primary_trigger는 고유 제약 없음 — 캐릭터끼리 같은 트리거를 비교하는 게 실험 목적.
- **기획 브리프**: 사람은 STEP(캐릭터 1~5 / 에피소드 1~3)만 정하고, 나머지(beats 등)는 AI가 규칙_최신 기반으로 생성 후 사람이 수정.
- **추천 이유**: `recommend.py`가 채움. **데이터 칩**(숫자·규칙엔진 고정, 환각 불가) + **판단 칩**(트리거 선택·궁합·감정선). `method`/`model`/`prompt_version`으로 추적, rule↔llm 교체형.
- **자동 파생**: 메인스토리(_story.json)·관계성(_relations.json)은 수동 입력이 아니라 캐릭터+에피소드에서 자동 요약.
- `_` 접두사 필드는 폼 스캐폴딩 — 저장 레코드에서 제거.

## UI (app-shell.html)

정적 미리보기 쉘(OAuth·저장·AI 없음, 탭 전환만 동작). 구성: AI 설정 · 고정 상수 · 현황 KPI · 관계성 · 메인스토리(접이식 트리) · 발행 캐릭터 · 에피소드(캐릭터별 드롭다운, 수정/삭제) · 생성폼(캐릭터 5-STEP / 에피소드 3-STEP → AI 초안, "통째 추천" 버튼).
