"""N-27a〜h：読み取りのスキル 8 本の照会を、正典 docs/SCHEMA.md の JSON（§11）と突き合わせる。DB を使わない。

照会の置き場所：SKILL.md の ```cypher（個人の側。道具 read_personal_cypher）と ```cypher-resource（資源の側。read_resource_cypher）、
スキルの中の *.cypher と scripts/*.py の三重引用符の文字列（MATCH を含むもの）。
- 書き込みの句（CREATE・MERGE・SET・DELETE・REMOVE・FOREACH・LOAD CSV・CALL）が無い。書くのはゲートだけ
- ラベル・リレーション・プロパティが正典にある（個人の側）。資源の側は nest が読む 3 つのラベルだけ
- 包みが止めるもの（実名・かな・電話・住所・生年月日の項目、text・quote、properties()・keys()・{.*}、注釈）を書かない
- 前の構成（ポート 7687・7688・7474・7475、mcp__neo4j、execute_query、neo4j-shared、埋め込み、lib/）を書かない
"""
import re
import subprocess
from pathlib import Path

import pytest

from nest import canon, mcp_guard

REPO = Path(__file__).resolve().parents[1]
C = canon.load(REPO / "docs" / "SCHEMA.md")
P = C["personal"]
SKILLS = ["neo4j-support-db", "visit-prep", "emergency-protocol", "data-quality-agent", "resilience-checker",
          "onboarding-wizard", "ecomap-generator", "insight-agent"]
LABELS = set(P["nodes"])
RELS = set(P["relationships"])
PROPS = set(P["commonRequired"]) | {k for n in P["nodes"].values() for k in n["required"] + n["optional"]} | \
    {k for r in P["relationships"].values() for k in r["required"] + r["optional"]}
RESOURCE_LABELS = {"Organization", "OrgName", "Area"}
RESOURCE_RELS = {"HAS_NAME", "PART_OF", "SERVES"}
WRITE = re.compile(r"\b(CREATE|MERGE|SET|DELETE|DETACH|REMOVE|FOREACH|CALL)\b|LOAD\s+CSV", re.I)
STRING = re.compile(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"")
OLD_PORT = re.compile(r"(?<!\d)(7687|7688|7474|7475)(?!\d)")
OLD = ("mcp__neo4j", "execute_query", "neo4j-shared", "embedding", "semantic_search", "lib/",
       "ServiceProvider", "Supporter", "KeyPerson)", ":KeyPerson", "Hospital", "Guardian)", ":Guardian", "AuditLog {")


def _tracked(skill):
    out = subprocess.run(["git", "ls-files", "claude-skills/" + skill], cwd=REPO, capture_output=True, text=True, check=True)
    return out.stdout.split()


def _queries(skill):
    """[(場所, 側, 照会)]。"""
    out = []
    skill_md = (REPO / "claude-skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    for m in re.finditer(r"```(cypher(?:-resource)?)\n(.*?)```", skill_md, re.S | re.I):
        out.append(("SKILL.md", "resource" if m.group(1).lower().endswith("resource") else "personal", m.group(2)))
    for path in _tracked(skill):
        if path.endswith(".cypher"):
            out.append((path, "personal", (REPO / path).read_text(encoding="utf-8")))
        elif path.endswith(".py"):
            for m in re.finditer(r'"""(.*?)"""', (REPO / path).read_text(encoding="utf-8"), re.S):
                if re.search(r"\bMATCH\b", m.group(1)):
                    out.append((path, "personal", m.group(1)))
    return out


def _problems(side, query):
    bare = STRING.sub("''", query)
    found = []
    if WRITE.search(bare):
        found.append("書き込みの句 %s" % WRITE.search(bare).group(0))
    labels = set(re.findall(r"[:|]\s*`?([A-Z][a-z][A-Za-z]*)`?", bare))
    rels = set(re.findall(r"[:|]\s*`?([A-Z][A-Z_]+)\b`?", bare))
    if side == "resource":
        found += ["資源の側に無いラベル %s" % x for x in sorted(labels - RESOURCE_LABELS)]
        found += ["資源の側に無いリレーション %s" % x for x in sorted(rels - RESOURCE_RELS)]
        return found
    found += ["正典に無いラベル %s" % x for x in sorted(labels - LABELS)]
    found += ["正典に無いリレーション %s" % x for x in sorted(rels - RELS)]
    props = set(re.findall(r"\b[a-z_]\w*\.`?([A-Za-z_]\w*)`?(?!\s*\()", bare))
    for body in re.findall(r"\(\s*\w*\s*:[\w|`]+\s*\{([^}]*)\}", bare) + re.findall(r"\[\s*\w*\s*:[\w|`]+\s*\{([^}]*)\}", bare):
        props |= set(re.findall(r"(\w+)\s*:", body))
    found += ["正典に無いプロパティ %s" % x for x in sorted(props - PROPS)]
    for name in mcp_guard.SENSITIVE + mcp_guard.RECORD_TEXT:
        if re.search(r"\b%s\b" % name, bare):
            found.append("包みが止める項目 %s" % name)
    for pat in (r"properties\s*\(", r"keys\s*\(", r"\{\s*\.\*\s*\}", r"//", r"/\*"):
        if re.search(pat, bare):
            found.append("包みが止める書き方 %s" % pat)
    return found


@pytest.mark.parametrize("skill", SKILLS)
def test_queries_match_the_canon_and_only_read(skill):
    queries = _queries(skill)
    assert queries, "照会が一つも無い"
    bad = [(where, side, p) for where, side, q in queries for p in _problems(side, q)]
    assert not bad, bad


@pytest.mark.parametrize("skill", SKILLS)
def test_skill_uses_the_new_read_tools_and_no_old_setup(skill):
    text = (REPO / "claude-skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    assert "read_personal_cypher" in text and "displayCode" in text
    for path in _tracked(skill):
        if path.endswith((".md", ".py", ".cypher", ".html")):
            body = (REPO / path).read_text(encoding="utf-8", errors="replace")
            hits = [w for w in OLD if w in body] + OLD_PORT.findall(body)
            assert not hits, (path, hits)
            if path.endswith(".py"):
                assert not re.search(r"^\s*(import|from)\s+neo4j\b", body, re.M), path


def test_the_checker_catches_old_queries():
    assert _problems("personal", "MATCH (c:Client {name: $name})-[:PROHIBITED]->(n:NgAction) RETURN n.action")
    assert _problems("personal", "MATCH (c:Client) SET c.status = 'Active'")
    assert _problems("personal", "MATCH (r:Record) RETURN r.quote")
    assert _problems("personal", "MATCH (c:Client)-[:HAS_KEY_PERSON]->(k:KeyPerson) RETURN k")
    assert not _problems("personal", "MATCH (c:Client {displayCode: $code})-[:MUST_AVOID]->(n:NgAction) "
                                     "WHERE n.status IN ['Active', 'Pending'] RETURN n.action, n.riskLevel")
    assert not _problems("resource", "MATCH (o:Organization {orgId: $id}) RETURN o.name")
    assert OLD_PORT.findall("bolt://localhost:7687") and not OLD_PORT.findall("127.0.0.1:37687")
