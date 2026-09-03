"""Neo4j パスワードのローテーション（正典ファイル連動）

正典: ~/.config/nest/neo4j.env（NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD の3行、chmod 600）

手順:
    1. 正典ファイルから接続情報を読む（.env や環境変数は見ない）
    2. 新パスワードを getpass で対話入力（2回、エコーなし）
    3. 現パスワードで接続確認
    4. system データベースで `ALTER CURRENT USER SET PASSWORD FROM $old TO $new` を
       パラメータ渡しで実行
    5. 成功後、正典ファイルの NEO4J_PASSWORD 行だけを書き換える（chmod 600 維持、
       同ディレクトリの一時ファイル経由で原子的に置換）
    6. 新パスワードで接続確認

    URI・ユーザー名・パスワードの値は一切出力しない。

使い方:
    uv run python scripts/rotate_password.py

注意:
    - 実行後、開いているシェルは古い値を保持している。`source ~/.config/nest/neo4j.env`
      で読み直すこと（~/.zshrc が起動時に読む）。
    - docker-compose.yml の NEO4J_AUTH は初回起動時にしか効かないので、既存 DB の
      パスワード変更はこのスクリプトで行う。
"""

import getpass
import os
import stat
import sys
import tempfile
from pathlib import Path

from neo4j import GraphDatabase

CANON = Path.home() / ".config" / "nest" / "neo4j.env"
REQUIRED = ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD")


def load_env_file(path: Path) -> dict:
    """KEY=VALUE 形式のファイルを読む。コメント・空行は無視。前後の引用符は外す。"""
    values = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key] = value
    missing = [k for k in REQUIRED if not values.get(k)]
    if missing:
        raise SystemExit(f"正典ファイルに不足があります: {', '.join(missing)} ({path})")
    return values


def write_password(path: Path, new_password: str) -> None:
    """NEO4J_PASSWORD 行だけを差し替え、他の行はそのまま保つ。mode 600 を維持する。"""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    replaced = False
    out = []
    for line in lines:
        stripped = line.lstrip()
        prefix = line[: len(line) - len(stripped)]
        if stripped.startswith("NEO4J_PASSWORD=") or stripped.startswith("export NEO4J_PASSWORD="):
            head = "export NEO4J_PASSWORD=" if stripped.startswith("export ") else "NEO4J_PASSWORD="
            newline = "\n" if line.endswith("\n") else ""
            out.append(f"{prefix}{head}{new_password}{newline}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        raise RuntimeError("NEO4J_PASSWORD 行が見つかりません")

    fd, tmp_name = tempfile.mkstemp(prefix=".neo4j.env.", dir=str(path.parent))
    try:
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("".join(out))
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def verify_connection(uri: str, user: str, password: str) -> None:
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        with driver.session(database="system") as session:
            session.run("RETURN 1").consume()


def change_password(uri: str, user: str, old: str, new: str) -> None:
    with GraphDatabase.driver(uri, auth=(user, old)) as driver:
        with driver.session(database="system") as session:
            session.run(
                "ALTER CURRENT USER SET PASSWORD FROM $old TO $new",
                old=old,
                new=new,
            ).consume()


def prompt_new_password(current: str) -> str:
    first = getpass.getpass("新しいパスワード: ")
    second = getpass.getpass("新しいパスワード（確認）: ")
    if first != second:
        raise SystemExit("2回の入力が一致しません。中止します。")
    if not first:
        raise SystemExit("空のパスワードは設定できません。中止します。")
    if len(first) < 8:
        raise SystemExit("Neo4j の既定では8文字以上が必要です。中止します。")
    if first == current:
        raise SystemExit("現在のパスワードと同じです。中止します。")
    return first


def main() -> int:
    if not CANON.exists():
        print(f"正典ファイルがありません: {CANON}", file=sys.stderr)
        return 1
    mode = stat.S_IMODE(CANON.stat().st_mode)
    if mode & 0o077:
        print(f"警告: {CANON} の権限が {oct(mode)} です（600 を推奨）", file=sys.stderr)

    env = load_env_file(CANON)
    uri, user, old = env["NEO4J_URI"], env["NEO4J_USERNAME"], env["NEO4J_PASSWORD"]

    print(f"正典ファイル: {CANON}")
    try:
        verify_connection(uri, user, old)
    except Exception as exc:  # 値を含みうるメッセージは出さない
        print(f"現在の認証情報で接続できません: {type(exc).__name__}", file=sys.stderr)
        return 1
    print("現在の認証情報で接続確認: OK")

    new = prompt_new_password(old)

    try:
        change_password(uri, user, old, new)
    except Exception as exc:
        print(f"パスワード変更に失敗しました（正典ファイルは変更していません）: {type(exc).__name__}", file=sys.stderr)
        return 1
    print("DB 側のパスワード変更: OK")

    try:
        write_password(CANON, new)
    except Exception as exc:
        print(
            "DB 側は変更済みですが正典ファイルの書き換えに失敗しました。"
            f"手動で NEO4J_PASSWORD 行を更新してください: {type(exc).__name__}",
            file=sys.stderr,
        )
        return 2
    print("正典ファイルの書き換え: OK（mode 600）")

    try:
        verify_connection(uri, user, new)
    except Exception as exc:
        print(f"新しい認証情報での接続確認に失敗しました: {type(exc).__name__}", file=sys.stderr)
        return 2
    print("新しい認証情報で接続確認: OK")
    print("開いているシェルでは `source ~/.config/nest/neo4j.env` で読み直してください。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
