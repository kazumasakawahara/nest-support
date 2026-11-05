"""ゲートの検証（N-15。約束 4-3・4-4、ADR-001 D6）。DB には触れない。

依頼の形：
  {"requestId", "actorStaffId", "nodes": [{"ref", "label", "origin", "properties"}],
   "relationships": [{"type", "from", "to", "properties"}]}
  リレーションの両端は、同じ依頼のノードの ref か、既にあるノード {"label", "id"}。

規則（正典 docs/SCHEMA.md の machine-check JSON から読む）：
- ラベル・リレーションは正典にあるものだけ。旧い名前（PROHIBITED など）は読み替えずに止める
- 項目名は正典にあるものだけ。snake_case などの別の綴りは直さずに止める（tsunagu-net は直すが、nest-support は止める。計画 N-15）
- 列挙値で直すのは、大文字・小文字の違いと、確度の日本語名だけ。直したことを返す。ほかの値（riskLevel の「高」など）は止める
- ID・registeredAt・status・origin の外の共通項目・sourceHash はゲートが付ける。依頼に含まれていたら止める
  （Organization の orgId は資源の側の ID なので依頼で渡す。linkedAt はゲートが付ける）
- 埋め込みの項目（名前が embedding で始まる・終わる）は止める（D10）
- 日付は正典の types のとおり。形の違うもの・時差の無い日時は補わずに止める
- 後見の類型は kind が Guardianship の関わりにだけ書ける
- 終わり方 Transitioned は、任意後見受任者（guardianshipType VoluntaryGuardianshipContracted）と任意代理（kind AgencyContract）の関わりにだけ書ける（正典 v0.8。台帳 G-62）
- 住所からの推定（inferenceBasis を持つ関わり）で作れる種類は Consultation と Administrative だけ。契約や選任で決まる関わりは住所から推し量れない（台帳 G-62・G-57）
- AI 由来（origin AiExtracted）のノードは Pending で作る。ほかは Active。機関の写し（Organization。公開 ID への参照）だけは AI 由来でも Active（止まる点 4。台帳 G-59）。返す nodes に status を添え、書き込み（N-20）がそれを使う（約束 4-5。N-16）
- 既にあるノードは {"label", "id"} だけで指す。名前を添えたり名前で指したりしたら止める（D8。N-16）
- 情報提供の書面の記録：PROVIDED_BY を持つ記録は providerCertainty を持ち、certainty は receiver_certainty の値に限る。
  PROVIDED_BY の無い記録は providerCertainty を持たない。documentHash は SHA-256 の 16 進 64 字
手本：tsunagu-net の tsunagu/gate/validate.py（読むだけ）。
"""
import datetime as dt
import re
from pathlib import Path

from nest import canon, ids
from nest.gate.intake import receiver_certainty

REPO = Path(__file__).resolve().parents[2]
SCHEMA = REPO / "docs" / "SCHEMA.md"
GATE_ONLY_LABELS = {"AuditLog"}
GATE_ONLY_RELATIONSHIPS = {"AUDIT_FOR", "ACTED_BY", "APPROVED"}
GATE_MANAGED = {"registeredAt", "status", "origin", "sourceHash"}
GATE_MANAGED_REL = {"CONTRADICTS": {"raisedAt", "resolvedAt", "resolution", "resolvedBy"},
                    "EVIDENCED_BY": {"linkedBy", "at"}}
EXTERNAL_ID_PROP = {"Organization": "orgId"}
GATE_MANAGED_BY_LABEL = {"Organization": {"linkedAt"}}
# 確度の日本語名（tsunagu-net の SEMANTICS ENU-03 と同じ。nest-support の SEMANTICS ができたらそちらから読む。N-27）
# 住所からの推定で作れる関わりの種類（2026-11-05 河原さん。台帳 G-62）
INFERABLE_KINDS = ("Consultation", "Administrative")
CERTAINTY_JA = {"確認済み": "Confirmed", "伝聞": "Hearsay", "本人の話": "SelfReport", "推測": "Inference", "確度の記載なし": "Unspecified"}
EMBEDDING = re.compile(r"^embedding|embedding$", re.I)
FULL_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DOCUMENT_HASH = re.compile(r"^[0-9a-f]{64}$")


class _Checker:
    def __init__(self):
        self.c = canon.load(SCHEMA)
        self.personal = self.c["personal"]
        self.bindings = self.c["enumBindings"]
        self.types = self.c.get("types", {})
        self.errors, self.corrections = [], []

    def _lookup(self, table, owner, prop):
        return table.get("%s.%s" % (owner, prop)) or table.get("*.%s" % prop)

    def check_value(self, where, owner, prop, value):
        enum = self._lookup(self.bindings, owner, prop)
        if enum is None:
            return value
        allowed = self.c["enums"][enum]
        if value in allowed:
            return value
        fixed = None
        if isinstance(value, str):
            fixed = next((a for a in allowed if a.lower() == value.strip().lower()), None)
            if fixed is None and enum == "certainty":
                fixed = CERTAINTY_JA.get(value.strip())
        if fixed:
            self.corrections.append("%s: %s.%s の値 %r を %r に直した" % (where, owner, prop, value, fixed))
            return fixed
        self.errors.append("%s: %s.%s の値 %r は列挙値 %s に無い（推測で読み替えない）" % (where, owner, prop, value, enum))
        return value

    def check_type(self, where, owner, prop, value):
        typ = self._lookup(self.types, owner, prop)
        if typ == "Date":
            if isinstance(value, str) and FULL_DATE.match(value):
                try:
                    return dt.date.fromisoformat(value)
                except ValueError:
                    pass
            if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
                return value
            self.errors.append("%s: %s.%s の値 %r は日付（YYYY-MM-DD の実在する日）でない" % (where, owner, prop, value))
        elif typ == "DateTime":
            parsed = value if isinstance(value, dt.datetime) else None
            if isinstance(value, str):
                try:
                    parsed = dt.datetime.fromisoformat(value)
                except ValueError:
                    parsed = None
            if parsed is None:
                self.errors.append("%s: %s.%s の値 %r は日時（ISO 8601）でない" % (where, owner, prop, value))
            elif parsed.tzinfo is None:
                self.errors.append("%s: %s.%s の値 %r に時差が無い（推測で補わない）" % (where, owner, prop, value))
            else:
                return parsed
        elif typ == "Integer" and not (isinstance(value, int) and not isinstance(value, bool)):
            self.errors.append("%s: %s.%s の値 %r は整数でない" % (where, owner, prop, value))
        elif typ == "Boolean" and not isinstance(value, bool):
            self.errors.append("%s: %s.%s の値 %r は真偽値でない" % (where, owner, prop, value))
        elif typ == "List" and not isinstance(value, list):
            self.errors.append("%s: %s.%s の値 %r は一覧でない" % (where, owner, prop, value))
        return value

    def check_props(self, where, owner, spec, props, managed):
        out = {}
        allowed = set(spec["required"]) | set(spec["optional"])
        for name, value in (props or {}).items():
            if EMBEDDING.search(name):
                self.errors.append("%s: 埋め込みの項目 %s は置けない（D10）" % (where, name))
                continue
            if name in managed:
                self.errors.append("%s: %s はゲートが付ける。依頼に含めない" % (where, name))
                continue
            if name not in allowed:
                self.errors.append("%s: %s に %s という項目は無い（直さずに止める）" % (where, owner, name))
                continue
            out[name] = self.check_type(where, owner, name, self.check_value(where, owner, name, value))
        for name in sorted(set(spec["required"]) - managed):
            if out.get(name) in (None, "", []):
                self.errors.append("%s: 必須の %s が無い" % (where, name))
        return out


def existing_id_ok(label, value):
    if label in EXTERNAL_ID_PROP:
        return ids.is_valid_org_id(value)
    return label in ids.LABEL_PREFIX and ids.is_valid_id(value, ids.LABEL_PREFIX[label])


def validate(req):
    ck = _Checker()
    nodes_out, labels_by_ref = [], {}
    for n, node in enumerate(req.get("nodes", []), start=1):
        where = "ノード %d（%s）" % (n, node.get("ref"))
        label, ref = node.get("label"), node.get("ref")
        if not ref or ref in labels_by_ref:
            ck.errors.append("%s: ref が無いか重複している" % where)
            continue
        if label in GATE_ONLY_LABELS:
            ck.errors.append("%s: %s は依頼では作れない" % (where, label))
            continue
        spec = ck.personal["nodes"].get(label)
        if spec is None:
            ck.errors.append("%s: ラベル %s は正典に無い（読み替えない）" % (where, label))
            continue
        if node.get("origin") not in ck.c["enums"]["origin"]:
            ck.errors.append("%s: origin %r が正しくない" % (where, node.get("origin")))
        managed = set(GATE_MANAGED) | GATE_MANAGED_BY_LABEL.get(label, set())
        if label in EXTERNAL_ID_PROP:
            if not ids.is_valid_org_id((node.get("properties") or {}).get(EXTERNAL_ID_PROP[label])):
                ck.errors.append("%s: %s の orgId は資源の側の機関 ID（ORG-…）" % (where, label))
        else:
            managed |= set(spec["unique"])
        props = ck.check_props(where, label, spec, node.get("properties"), managed)
        labels_by_ref[ref] = label
        # 機関の写し（公開 ID への参照）は AI 由来でも Active。判断は Pending の関わりの側で承認する（止まる点 4。台帳 G-59）
        status = "Pending" if node.get("origin") == "AiExtracted" and label not in EXTERNAL_ID_PROP else "Active"
        nodes_out.append({"ref": ref, "label": label, "origin": node.get("origin"), "status": status, "properties": props})

    rels_out = []
    for n, rel in enumerate(req.get("relationships", []), start=1):
        rtype = rel.get("type")
        where = "リレーション %d（%s）" % (n, rtype)
        if rtype in GATE_ONLY_RELATIONSHIPS:
            ck.errors.append("%s: %s は依頼では作れない" % (where, rtype))
            continue
        spec = ck.personal["relationships"].get(rtype)
        if spec is None:
            ck.errors.append("%s: リレーション %s は正典に無い（旧い名前を読み替えない）" % (where, rtype))
            continue
        ends = []
        for side in ("from", "to"):
            end = rel.get(side)
            if isinstance(end, dict):
                if set(end) != {"label", "id"} or not existing_id_ok(end.get("label"), end.get("id")):
                    ck.errors.append("%s: %s 側の既にあるノードの ID が正しくない（%r）" % (where, side, end))
                    ends.append(None)
                else:
                    ends.append(end["label"])
            elif end in labels_by_ref:
                ends.append(labels_by_ref[end])
            else:
                ck.errors.append("%s: %s 側の ref %r が依頼の中に無い" % (where, side, end))
                ends.append(None)
        if None not in ends:
            frm, to = ends
            if ("*" not in spec["from"] and frm not in spec["from"]) or ("*" not in spec["to"] and to not in spec["to"]):
                ck.errors.append("%s: %s は %s → %s をつなげない（正典は %s → %s）" % (
                    where, rtype, frm, to, "／".join(spec["from"]), "／".join(spec["to"])))
        props = ck.check_props(where, rtype, spec, rel.get("properties"), GATE_MANAGED_REL.get(rtype, set()))
        rels_out.append({"type": rtype, "from": rel.get("from"), "to": rel.get("to"), "properties": props})

    _check_guardianship(ck, nodes_out)
    _check_concerns_person(ck, nodes_out, rels_out)
    _check_provided(ck, nodes_out, rels_out)
    return {"ok": not ck.errors, "errors": ck.errors, "corrections": ck.corrections,
            "nodes": nodes_out, "relationships": rels_out, "requestId": req.get("requestId")}


def _check_guardianship(ck, nodes):
    for n in nodes:
        p = n["properties"]
        if n["label"] == "Involvement" and "guardianshipType" in p and p.get("kind") != "Guardianship":
            ck.errors.append("ノード %s: guardianshipType は kind が Guardianship の関わりにだけ書ける（kind %r）" % (n["ref"], p.get("kind")))
        if n["label"] == "Involvement" and "inferenceBasis" in p and p.get("certainty") != "Inference":
            ck.errors.append("ノード %s: inferenceBasis は確度が Inference の関わりにだけ書ける（certainty %r）" % (n["ref"], p.get("certainty")))
        if n["label"] == "Involvement" and "inferenceBasis" in p and p.get("kind") not in INFERABLE_KINDS:
            ck.errors.append("ノード %s: 住所からの推定（inferenceBasis）で作れる関わりは %s だけ（kind %r は契約や選任で決まるので推し量らない）"
                             % (n["ref"], "・".join(INFERABLE_KINDS), p.get("kind")))
        if (n["label"] == "Involvement" and p.get("howEnded") == "Transitioned" and p.get("kind") != "AgencyContract"
                and p.get("guardianshipType") != "VoluntaryGuardianshipContracted"):
            ck.errors.append("ノード %s: howEnded Transitioned は任意後見受任者（VoluntaryGuardianshipContracted）と任意代理（AgencyContract）の関わりにだけ書ける" % n["ref"])


def _check_concerns_person(ck, nodes, rels):
    """本人以外の人（Person）に向けた関わり（正典 v0.7。台帳 G-60）：根拠の記録が要る、住所からの推定では作らない、いつも Pending。"""
    labels = {n["ref"]: n["label"] for n in nodes}

    def label_of(end):
        return end.get("label") if isinstance(end, dict) else labels.get(end)
    for n in nodes:
        if n["label"] != "Involvement":
            continue
        ref = n["ref"]
        to_person = any(r["type"] == "CONCERNS" and r["from"] == ref and label_of(r["to"]) == "Person" for r in rels)
        if not to_person:
            continue
        if not any(r["type"] == "EVIDENCED_BY" and r["from"] == ref for r in rels):
            ck.errors.append("ノード %s: 本人以外の人に向けた関わりには、原文の引用の根拠（EVIDENCED_BY → Record）が要る" % ref)
        if "inferenceBasis" in n["properties"]:
            ck.errors.append("ノード %s: 住所からの推定（inferenceBasis）では、本人以外の人の関わりを作らない（住所が本人と違うことがある）" % ref)
        n["status"] = "Pending"


def _check_provided(ck, nodes, rels):
    for n in nodes:
        if n["label"] != "Record":
            continue
        p, ref = n["properties"], n["ref"]
        provided = [r for r in rels if r["type"] == "PROVIDED_BY" and r["from"] == ref]
        if len(provided) > 1:
            ck.errors.append("ノード %s: 提供元（PROVIDED_BY）は一つだけ（%d）" % (ref, len(provided)))
        if provided:
            if "providerCertainty" not in p:
                ck.errors.append("ノード %s: 情報提供の書面の記録は、提供元の確度（providerCertainty）を持つ" % ref)
            elif p.get("certainty") != receiver_certainty(p["providerCertainty"]):
                ck.errors.append("ノード %s: 受けた側の確度は %s（提供元の確度 %s より強くしない）。%s は書けない"
                                 % (ref, receiver_certainty(p["providerCertainty"]), p["providerCertainty"], p.get("certainty")))
        elif "providerCertainty" in p:
            ck.errors.append("ノード %s: 提供元（PROVIDED_BY）の無い記録に、提供元の確度を書かない" % ref)
        if "documentHash" in p and not (isinstance(p["documentHash"], str) and DOCUMENT_HASH.match(p["documentHash"])):
            ck.errors.append("ノード %s: documentHash は SHA-256 の 16 進 64 字（%r）" % (ref, p["documentHash"]))
