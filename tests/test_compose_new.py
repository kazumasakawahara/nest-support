"""N-18：新しい compose の中身の検査（起動しない）。2026-11-05 河原さんの条件。

1. データの置き場は新しい名前のフォルダ。前の DB の跡（neo4j_data/・neo4j_backup/・生活困窮者支援の跡・.quarantine/）をマウントしない
2. ポートは 7687・7688 以外（tsunagu-net の 17474・17687・27474・27687、前の 7474・7475 も避ける）。待ち受けは 127.0.0.1 だけ
3. APOC を入れない。プラグインのフォルダもマウントしない
5. restart は "no"（tests/test_compose_restart.py）
ほか：前のコンテナと同じ compose のプロジェクトにしない（down などで前のコンテナに触れないため）。イメージは版と digest で固定。
起動の後の接続の試験は、河原さんが compose を見てから起動したあとに足す。
2026-11-12 河原さん（案 A。台帳 G-103）：DB を使う試験の専用の DB（neo4j-test。127.0.0.1:36474・36687。profile "test"）を足した。
サービスは 3 つ、ポートは 6 つになった。試験用の DB は profile があるので、ふだんの up -d・down では動かない。
"""
import re
from pathlib import Path

COMPOSE = Path(__file__).resolve().parents[1] / "docker-compose.yml"
FORBIDDEN_PORTS = {"7474", "7475", "7687", "7688", "17474", "17687", "27474", "27687",
                   "47474", "47687", "48687", "39687"}  # 2026-11-12：tsunagu-net の使い捨て・バックアップの試験の使い捨て
OLD_TRACES = ("neo4j_data", "neo4j_backup", "neo4j_logs", "neo4j_plugins", "neo4j_livelihood", ".quarantine")


def _lines():
    return [l for l in COMPOSE.read_text(encoding="utf-8").splitlines() if l.strip() and not l.lstrip().startswith("#")]


def _items(key):
    """`key:` の下の `- …` の並び（どのサービスのものもまとめて）。"""
    out, inside, indent = [], False, 0
    for line in _lines():
        stripped = line.lstrip()
        if stripped.startswith(key + ":"):
            inside, indent = True, len(line) - len(stripped)
            continue
        if inside:
            if stripped.startswith("- ") and len(line) - len(stripped) > indent:
                out.append(stripped[2:].strip().strip('"'))
            else:
                inside = False
    return out


def test_project_name_is_separate_from_the_old_one():
    assert any(re.fullmatch(r"name:\s*nest-redesign", l) for l in _lines())
    assert not any("nest-support-neo4j" in l for l in _lines())


def test_two_services_personal_and_resource():
    names = [l.strip()[:-1] for l in _lines() if re.fullmatch(r"  [a-z][a-z0-9-]*:", l)]
    assert names == ["neo4j-personal", "neo4j-resource", "neo4j-test"]  # 2026-11-12 neo4j-test を足した（台帳 G-103）


def test_the_test_db_is_in_the_test_profile_on_its_own_ports():
    text = COMPOSE.read_text(encoding="utf-8")
    block = text.split("\n  neo4j-test:\n", 1)[1]
    assert 'profiles: ["test"]' in block and "container_name: nest-redesign-test" in block
    assert '"127.0.0.1:36474:7474"' in block and '"127.0.0.1:36687:7687"' in block
    assert "${NEST_PERSONAL_PASSWORD:?" in block  # 新しい設定を足さない（中身を読まずに済む）
    for other in ("profiles:",):
        assert other not in text.split("\n  neo4j-test:\n", 1)[0]  # 試走と資源の側は profile を持たない


def test_ports_listen_on_localhost_only_and_avoid_taken_ports():
    ports = _items("ports")
    assert len(ports) == 6, ports  # 2026-11-12：試験用の DB の 2 つを足した
    for p in ports:
        m = re.fullmatch(r"127\.0\.0\.1:(\d+):(7474|7687)", p)
        assert m, p
        assert m.group(1) not in FORBIDDEN_PORTS, p
    assert len({p.split(":")[1] for p in ports}) == 6


def test_data_folders_are_new_and_old_traces_are_not_mounted():
    volumes = _items("volumes")
    assert volumes, "volumes が無い"
    for v in volumes:
        assert v.startswith("./nest_neo4j_"), v
    text = "\n".join(_lines())
    for trace in OLD_TRACES:
        assert trace not in text, trace


def test_no_apoc_and_no_plugins():
    text = "\n".join(_lines()).lower()
    assert "apoc" not in text and "plugins" not in text


def test_image_is_pinned_by_version_and_digest():
    images = [l.split("image:", 1)[1].strip() for l in _lines() if l.strip().startswith("image:")]
    assert len(images) == 3 and len(set(images)) == 1  # 2026-11-12：試験用の DB も同じ版
    for img in images:
        assert re.fullmatch(r"neo4j:5\.26\.\d+-community@sha256:[0-9a-f]{64}", img), img


def test_passwords_come_from_outside_the_repository():
    auth = [l for l in _lines() if "NEO4J_AUTH" in l]
    assert len(auth) == 3  # 2026-11-12：試験用の DB は個人の側と同じ NEST_PERSONAL_PASSWORD
    for l in auth:
        assert re.search(r"\$\{NEST_[A-Z_]+_PASSWORD:\?", l), l


def test_new_data_folders_are_ignored_by_git():
    ignore = (COMPOSE.parent / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "nest_neo4j_*/" in ignore


def test_usage_reporting_is_off_for_both_dbs():
    """2026-11-06（N-33 の試験で見つけた。台帳 G-75）：Neo4j は既定で匿名の利用の情報を Neo4j 社に送る
    （dbms.usage_report.enabled の既定は true。Neo4j Operations Manual）。docs/external-api.md に無い送信なので、二つとも止める"""
    lines = [l.strip() for l in _lines()]
    assert lines.count('NEO4J_dbms_usage__report_enabled: "false"') == 3  # 2026-11-12：試験用の DB も止める
