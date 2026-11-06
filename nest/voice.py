"""field-ui の音声の置き場所と消す道具（計画 N-37。2026-11-06 河原さん。止まる点 F-1、台帳 G-74）。

- 置き場所はリポジトリの nest_voice_data/（.gitignore。権限 700、Time Machine の対象外。doctor.sh が点検する）。
  音声は要配慮個人情報になりうる。外のサービスに置かない
- 音声の名前は「文字起こしの sha256 ＋ 拡張子」。職員がその文字起こしをそのまま原文にして intake で案を作ると、
  Record.documentHash が同じ値になる（nest/gate/intake.py は原文の sha256 を documentHash にする）
- 消す：その documentHash の Record が承認された（status が Active）音声と、置いてから 30 日を過ぎた音声。
  DB の Record（documentHash を含む）には触れない。文字起こしを直してから案にすると値が合わないので、30 日で消える
- 既定は数えるだけ。scripts/purge_voice.py --write で消す。DB を読めなくても、30 日を過ぎたものは消す
"""
import hashlib
import os
import re
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VOICE_DIR = REPO / "nest_voice_data"
KEEP_DAYS = 30
NAME = re.compile(r"([0-9a-f]{64})\.(webm|ogg|oga|mp3|m4a|mp4|wav|aac|flac)")
APPROVED = """MATCH (r:Record) WHERE r.documentHash IN $hashes AND r.status = 'Active'
RETURN DISTINCT r.documentHash AS h"""


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def ensure_dir(root, runner=None):
    runner = runner or run  # 呼ぶときに引く（試験で差し替えられるように）
    root = Path(root)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    runner(["tmutil", "addexclusion", str(root)])


def transcript_hash(transcript):
    return hashlib.sha256(transcript.encode("utf-8")).hexdigest()


def store(src, transcript, suffix, root=VOICE_DIR, runner=None):
    """アップロードされた音声を置き場所へ移す。返り値は documentHash になる値（文字起こしの sha256）。"""
    ensure_dir(root, runner)
    digest = transcript_hash(transcript)
    dest = Path(root) / (digest + suffix)
    shutil.move(str(src), dest)
    os.chmod(dest, 0o600)
    os.utime(dest)  # 置いた時から 30 日を数える
    return digest


def files(root):
    root = Path(root)
    return sorted(p for p in root.iterdir() if p.is_file() and NAME.fullmatch(p.name)) if root.is_dir() else []


def plan(root, approved, now):
    """消すもの（承認済み・30 日過ぎ）と残すものの名前。approved は承認された documentHash の集合。"""
    limit = (now - timedelta(days=KEEP_DAYS)).timestamp()
    out = {"approved": [], "expired": [], "kept": []}
    for p in files(root):
        if NAME.fullmatch(p.name).group(1) in approved:
            out["approved"].append(p.name)
        elif p.stat().st_mtime < limit:
            out["expired"].append(p.name)
        else:
            out["kept"].append(p.name)
    return out


def approved_hashes(driver, hashes, database="neo4j"):
    """承認された（status が Active の）Record の documentHash のうち、hashes にあるもの。読むだけ。"""
    with driver.session(database=database) as s:
        return s.execute_read(lambda tx: {r["h"] for r in tx.run(APPROVED, hashes=sorted(hashes))})


def purge(root, approved_of, write=False, now=None):
    """approved_of(hashes) は承認された documentHash を返す。読めなければ 30 日過ぎだけを消す。"""
    now = now or datetime.now()
    errors = []
    hashes = {NAME.fullmatch(p.name).group(1) for p in files(root)}
    try:
        approved = approved_of(hashes) if hashes else set()
    except Exception as e:
        approved = set()
        errors.append("DB を読めないので、承認済みは確かめていない（%s）。30 日を過ぎたものだけ消す" % type(e).__name__)
    out = plan(root, approved, now)
    if write:
        for name in out["approved"] + out["expired"]:
            (Path(root) / name).unlink()
    out.update(write=write, errors=errors)
    return out
