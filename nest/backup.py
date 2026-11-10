"""個人の側の DB のバックアップ（計画 N-33。2026-11-06 河原さん。止まる点 F-1、台帳 G-74）。

- 置き場所は ~/nest-backup/（リポジトリの外。権限 700、Time Machine の対象外）。バックアップは要配慮個人情報の写し。
  外のサービスに置かない（docs/external-api.md に行を足さない）。FileVault が有効であることは doctor.sh が確かめる
- 取る・戻すは、個人の側の DB を止めてから（Community 版は動いたまま書き出せない。Neo4j Operations Manual）。
  同じ版の Neo4j の像（docker-compose.yml の neo4j-personal）で neo4j-admin database dump／load を流す
- 世代は 4 つ。世代は YYYYmmdd-HHMMSS の名前のフォルダで、その中に neo4j.dump（権限 600）。古いものは、この名前の形のフォルダだけを消す
- 資源の側は取らない（tsunagu-net の配布の一式から読み直せる）
- いつ取るか：DB に書き込んだ日の作業の終わりに、DB を止めてから。廃棄（scripts/purge_client.py）の後にも取り、
  戻せることを確かめてから、消した日より前の世代を prune で消す（rm を手で打たない）
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = Path.home() / "nest-backup"
DEFAULT_DATA = REPO / "nest_neo4j_personal_data"
CONTAINER = "nest-redesign-personal"
GENERATION = re.compile(r"\d{8}-\d{6}")
KEEP = 4
DUMP = "neo4j.dump"


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def personal_image(compose_text):
    """docker-compose.yml の neo4j-personal の image（同じ版で取る・戻す）。"""
    m = re.search(r"^  neo4j-personal:\n(?:    .*\n)*?    image: (\S+)", compose_text, re.M)
    if not m:
        raise ValueError("docker-compose.yml に neo4j-personal の image が無い")
    return m.group(1)


def _running(runner):
    code, out = runner(["docker", "ps", "--format", "{{.Names}}"])
    return code != 0 or CONTAINER in out.split()


def _admin(runner, data, gen, image, *args):
    return runner(["docker", "run", "--rm", "-v", "%s:/data" % data, "-v", "%s:/backups" % gen, image,
                   "neo4j-admin", "database", *args])


def generations(root):
    return sorted(p for p in Path(root).iterdir() if p.is_dir() and GENERATION.fullmatch(p.name)) if Path(root).is_dir() else []


def _ensure_root(root, runner):
    root = Path(root)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    runner(["tmutil", "addexclusion", str(root)])


def dump(root, data, image, runner=run, now=None):
    """個人の側を書き出す。返り値 {ok, errors, generation, removed}。"""
    out = {"ok": False, "errors": [], "generation": None, "removed": []}
    if _running(runner):
        out["errors"].append("個人の側の DB（%s）が動いているか、確かめられない。止めてから取る" % CONTAINER)
        return out
    root = Path(root)
    _ensure_root(root, runner)
    gen = root / now.strftime("%Y%m%d-%H%M%S")
    gen.mkdir(mode=0o700)
    os.chmod(gen, 0o700)
    code, text = _admin(runner, data, gen, image, "dump", "neo4j", "--to-path=/backups")
    f = gen / DUMP
    if code != 0 or not f.is_file() or f.stat().st_size == 0:
        shutil.rmtree(gen)
        out["errors"].append("書き出せなかった（%s）。古い世代は消していない" % (text.strip().splitlines()[-1:] or ["ファイルが無いか空"])[0])
        return out
    os.chmod(f, 0o600)
    gens = generations(root)
    for old in gens[:-KEEP] if len(gens) > KEEP else []:
        shutil.rmtree(old)
        out["removed"].append(old.name)
    out.update(ok=True, generation=gen.name)
    return out


def restore(gen, data, image, runner=run):
    """世代のフォルダから、今の個人の側を置き換える。返り値 {ok, errors}。"""
    out = {"ok": False, "errors": []}
    gen = Path(gen)
    if not (gen / DUMP).is_file():
        out["errors"].append("%s に %s が無い" % (gen, DUMP))
        return out
    # いつもの個人の側のデータに戻すときだけ、DB を止めておく（動いている DB のデータは置き換えられない）。
    # 別のフォルダに戻して確かめるとき（N-33 の試験）は、いつもの DB に触れない
    if Path(data).resolve() == DEFAULT_DATA.resolve() and _running(runner):
        out["errors"].append("個人の側の DB（%s）が動いているか、確かめられない。止めてから戻す" % CONTAINER)
        return out
    code, text = _admin(runner, data, gen, image, "load", "neo4j", "--from-path=/backups", "--overwrite-destination=true")
    if code != 0:
        out["errors"].append("戻せなかった：%s" % (text.strip().splitlines()[-1:] or ["?"])[0])
        return out
    out["ok"] = True
    return out


def prune(root, before, write=False):
    """世代 before（在る世代の名前）より前の世代を消す。write が偽なら一覧だけ。返り値 {ok, errors, written, removed, kept}。
    廃棄（scripts/purge_client.py）の後に、新しい世代を取り、戻せることを確かめてから使う（N-46 詰まり #14）。"""
    out = {"ok": False, "errors": [], "written": False, "removed": [], "kept": []}
    gens = generations(root)
    if not GENERATION.fullmatch(before or "") or before not in [g.name for g in gens]:
        out["errors"].append("%s は在る世代の名前ではない。list で出る名前を打つ。何も消していない" % before)
        return out
    old = [g for g in gens if g.name < before]
    out["removed"] = [g.name for g in old]
    if write:
        for g in old:
            shutil.rmtree(g)
        out["written"] = True
    out["kept"] = [g.name for g in gens if g.name >= before]
    out["ok"] = True
    return out


COUNTS = "MATCH (n) UNWIND labels(n) AS label RETURN label, count(*) AS n"


def counts(driver, wait=90, sleep=None):
    """個人の側のラベルごとの数（名前・本文は読まない）。DB が起ききるまで wait 秒まで待つ。返り値 {ok, errors, counts}。
    戻した後に、戻す前の数と比べて、戻したことを確かめる（N-46 詰まり #13。待つのは #12 の再試行の行を出さないため）。"""
    import time
    sleep = sleep or time.sleep
    out = {"ok": False, "errors": [], "counts": {}}
    for _ in range(max(1, int(wait))):
        try:
            driver.verify_connectivity()
            break
        except Exception:
            sleep(1)
    else:
        out["errors"].append("個人の側の DB が %d 秒たっても起きない。up -d を打ったかを確かめる" % wait)
        return out
    rows, _, _ = driver.execute_query(COUNTS, routing_="r", database_="neo4j")
    out["counts"] = {r["label"]: r["n"] for r in sorted(rows, key=lambda r: r["label"])}
    out["ok"] = True
    return out
