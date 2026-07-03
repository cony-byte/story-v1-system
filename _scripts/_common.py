# -*- coding: utf-8 -*-
"""공용 헬퍼: 경로·로더."""
import json, os, glob, statistics

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
CHAR_DIR = os.path.join(ROOT, "03_캐릭터")


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 3) if xs else None


def char_dirs():
    """char_* 폴더 경로 리스트 (템플릿 제외)."""
    out = []
    for d in sorted(glob.glob(os.path.join(CHAR_DIR, "*"))):
        if os.path.isdir(d) and os.path.basename(d).startswith("char_"):
            out.append(d)
    return out


def load_character(cdir):
    p = os.path.join(cdir, "character.json")
    return read_json(p) if os.path.exists(p) else None


def load_episodes(cdir):
    eps = []
    for p in sorted(glob.glob(os.path.join(cdir, "episodes", "*.json"))):
        eps.append(read_json(p))
    return eps


def load_rules():
    return read_json(os.path.join(ROOT, "00_규칙엔진", "규칙_최신.json"))


def load_world():
    """고정 상수: 세계관."""
    return read_json(os.path.join(ROOT, "01_세계관.json"))


def load_heroine():
    """고정 상수: 여주."""
    return read_json(os.path.join(ROOT, "02_여주.json"))
