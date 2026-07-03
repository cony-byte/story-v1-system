#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""파생물 재생성. 현재 활성: 메인스토리 자동요약. 실행: python3 _scripts/build_all.py

후순위(보류): 성과 롤업(build_performance.py), IP 후보 선정, 심사위원 채점(judge.py).
필요해지면 아래에 build_performance 등을 다시 추가한다.
"""
import build_story, build_relations

if __name__ == "__main__":
    print("== 메인스토리 자동요약 =="); build_story.main()
    print("== 관계성(텍스트·숫자) =="); build_relations.main()
    print("== 완료 ==")
