"""書き込みの案の入口（N-12〜N-16。ADR-001 D6、約束 4）。DB を使わない。AI を使わない点検。

Claude が語り・書面・自分の面談記録から作った「書き込みの案」（JSON）を原文と突き合わせて点検し、
通ればゲートへの依頼を作る。手本：tsunagu-net の tsunagu/gate/intake.py（読むだけ）。

案の形：
  {"documentKind": "ProvisionDocument" | "OwnCaseRecord",
   "providerName": "…"（情報提供の書面のときだけ。原文に書かれた提供元の名前。機関 ID は書かない。N-24）,
   "clientId": "CLI-…"（既にいる本人。職員が選ぶ）,
   "receivedOn": "YYYY-MM-DD"（書面を受けた日。任意）,
   "newPeople": [{"ref", "familyName"?, "givenName"?, "familyNameKana"?, "givenNameKana"?}]（任意）,
   "facts": [{"quote", "text"?, "recordKind", "certainty", "providerCertainty"?, "informantKind",
              "aboutDate"?, "heardOn"?, "toldBy"?}],
   "involvements": [...]（任意。下の N-24a）,
   "ngActions": [{"quote", "action", "riskLevel", "reason"?}]（任意。禁忌の候補。G-63）,
   "carePreferences": [{"quote", "category", "instruction", "priority"?}]（任意。推奨ケアの候補。G-63）,
   "supportLog": {"quote", "date", "contactKind"?, "situation", "action"?, "nextAction"?, "note"?}（任意。面接記録。正典 v0.13）}

点検：
- quote は原文にそのまま有ること（空白・改行の違いだけは無視する）（N-12）
- 原本の指紋（documentHash）は、ここで原文から作る。案に書かせない（N-12）
- text を書くなら、quote に無い数字（日付・回数・金額・年齢・体重など）を含まないこと。全角の数字は半角と同じに数える。
  数字を足さない言い換えは警告して通す。text を書かなければ quote をそのまま本文にする（N-13）
- 確度は原文の印で決める：quote の直後（同じ行）の【…】。推測＞伝聞・未確認＞本人の話＞確認済み の順で弱いほうを採る。
  印が無ければ Unspecified。知らない印は推測で読み替えずに止める。自分の記録では certainty がこれと同じこと。
  書面では providerCertainty がこれと同じで、certainty が受けた側の確度（receiver_certainty）と同じこと。上げも下げも止める（N-14）
- 人は、既にいる人の ID（PER-…）か、案の中の新しい人の名札（英小文字で始め、英字・数字・ハイフンだけ。重複の無いもの。点検が使う名札は除く）か、本人（client）だけで指す。
  名前で既にいる人に結び付けない。新しい人は AiExtracted（Pending）で作る（D8。N-16）
- 提供元の機関は、案に機関 ID を書かせない（名前の一致だけで orgId を入れない）。原文の名前（providerName）から
  org_candidates.by_name で候補を出し、職員が選んだ機関 ID を provider_org_id で渡す。渡すまでは未確定で、依頼を作らない（N-24。D3）
- 機関の名前が無い言及（「区役所の窓口で」）は involvements [{"quote", "kind", "orgId"?, "concerns"?}] に書く（N-24a）。quote は事実の引用のどれか
  （その記録を根拠に結ぶ）。orgId は担当機関の推定（org_estimate.estimate。estimate で渡す）の候補の中からだけ。無ければ機関未確定。
  確度は書かせず、機関の名前の無い関わりはいつも Inference・終わり方 Unknown・AI 由来（Pending）。
  orgName のある関わりは、根拠の記録（同じ引用の事実）の確度を写す（SEMANTICS SEM-REC-05。2026-11-11 河原さん）。
  終わり方（howEnded）は orgName のある関わりにだけ、Ongoing だけを書ける。終わった値は止める（2026-11-12 河原さん）。候補から選んだら、推定の根拠（inferenceBasis）を推定の結果から付ける（案には書かせない）。後見は推定で作らない。推定の注記は結果の notes に載せる
- 禁忌・推奨ケアの候補（G-63。正典 v0.9）：quote は案の事実の引用のどれかで、その記録を根拠に結ぶ（EVIDENCED_BY）。
  根拠が同じ案の中に無い候補は作らない。確度は書かせない（根拠の記録の確度を引き継ぐ。§6）。本文に引用に無い数字を足さない。
  いつも AI 由来（Pending）。本人から MUST_AVOID・REQUIRES で結ぶ
- 事実の recordKind・informantKind は必須で、正典の列挙値のどれか。見立て（certainty Inference）で informantKind が無ければ、
  もとになった情報源を書くよう理由を出して止める（確認点 L-0 の決めごと 6・9。SEMANTICS SEM-REC-04）
- 自分の記録の見立ての記録の種類は、話し手に合わせる（Self・Family・Neighbor なら Interview、Agency なら Observation、
  DocumentOnly なら Document）。合わなければ正しい組み合わせを出して止める（2026-11-12 河原さん。台帳 G-100・G-101）
- 根拠が見立て（Inference）の記録だけの候補は、禁忌は止め、推奨ケアは注意を出して通す（決めごと 8）
- 新しい人（newPeople）は、どれかの事実の toldBy か関わりの concerns に使う。使われない人は止める（決めごと 10。N-46 #10 の注意から変えた）
- 面接記録（supportLog。決めごと 1〜5）：面接 1 回に 0 か 1 件。quote は案の事実の引用のどれか（その記録を根拠に結ぶ）。date は実在する日、
  situation は必須、contactKind は書くなら正典の列挙値。effectiveness は書かせない（判定は職員）。本文に原文全体に無い数字を足さない。
  AI 由来（Pending）で、本人に ABOUT、職員に AUTHORED_BY、根拠の記録に EVIDENCED_BY で結ぶ
- 案に、上の形に無い項目があれば止める。snake_case などの別の綴りも直さない（N-15）。ゲートの検証（validate.py）も同じ考え方
"""
import copy
import datetime as dt
import hashlib
import re
from pathlib import Path

from nest import canon, ids, semantics

DOC_KINDS = ("ProvisionDocument", "OwnCaseRecord")
# 見立て（確度 Inference）の記録の種類は、もとになった情報に合わせる（SEMANTICS SEM-REC-04。台帳 G-100・G-101）。
# 自分の記録だけ。情報提供の書面の見立ては決めていない
VIEW_RECORD_KIND = {"Self": "Interview", "Family": "Interview", "Neighbor": "Interview",
                    "Agency": "Observation", "DocumentOnly": "Document"}
TOP_KEYS = {"documentKind", "providerName", "clientId", "receivedOn", "newPeople", "facts", "involvements",
            "ngActions", "carePreferences", "supportLog"}
# 面接記録の欄（確認点 L-0。正典 v0.13）。effectiveness は案に書かせない（決めごと 5）
SUPPORT_LOG_KEYS = {"quote", "date", "contactKind", "situation", "action", "nextAction", "note"}
SUPPORT_LOG_TEXTS = ("situation", "action", "nextAction", "note")
FULL_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# 禁忌・推奨ケアの候補（G-63）：案の欄 → (ラベル, 本人からの関係, 項目, 本文として数字を確かめる項目)
CANDIDATES = {"ngActions": ("NgAction", "MUST_AVOID", {"quote", "action", "riskLevel", "reason"}, ("action", "reason")),
              "carePreferences": ("CarePreference", "REQUIRES", {"quote", "category", "instruction", "priority"},
                                  ("category", "instruction"))}
# orgName（原文に書かれた機関の名前）・serviceTypeName は任意（2026-11-11 河原さん）。機関 ID は案に書かせない（N-24）
# howEnded は名前のある関わりに Ongoing だけ（2026-11-12 河原さん。SEM-REC-05）
INVOLVEMENT_KEYS = {"quote", "kind", "orgId", "concerns", "orgName", "serviceTypeName", "howEnded"}
ENDED = ("Lapsed", "DeclinedByPerson", "EndedByAgency")
ORG_NAME_MIN = 2  # 候補を引く名前の短さの下限（nest.org_candidates.MIN_LENGTH と同じ）
SCHEMA = Path(__file__).resolve().parents[2] / "docs" / "SCHEMA.md"
# 推定の結果の basis → 関わりの inferenceBasis（正典 v0.6。台帳 G-57）。住所も区のコードも持たない
INFERENCE_BASIS = {"AtTheTime": "ResidenceAreaAtTheTime", "CurrentFallback": "CurrentResidenceArea"}
FACT_KEYS = {"quote", "text", "recordKind", "certainty", "providerCertainty", "informantKind", "aboutDate", "heardOn", "toldBy"}
PERSON_KEYS = {"ref", "familyName", "givenName", "familyNameKana", "givenNameKana"}
# 名札（newPeople の ref）。依頼の中の目印で、照会の文には入らない。途中の大文字は許す（2026-11-11 河原さん）
REF = re.compile(r"^[a-z][A-Za-z0-9-]*$")
# 点検が自分で付ける名札。新しい人の名札に使うとぶつかる
RESERVED_REF = re.compile(r"^(client|provider|support-log|(fact|involvement|ngAction|carePreference|estimated-org)-\d+)$")
REF_RULE = "英小文字で始め、英字・数字・ハイフンだけ（例：supportWorker、mother、sister-2）"
DIGITS = re.compile(r"[0-9０-９]+")
WIDE = str.maketrans("０１２３４５６７８９", "0123456789")
MARK = re.compile(r"^\s*【([^】]+)】")
# 原文の確度の印。弱い順。docs/SEMANTICS.md SEM-ENUM-02 から読む（台帳 G-47）
WEAKEST_FIRST = tuple(semantics.certainty_marks())


def _norm(text):
    return re.sub(r"\s+", "", text or "")


def _in_original(quote, original):
    return _norm(quote) in _norm(original)


def _digits(text):
    return {d.translate(WIDE) for d in DIGITS.findall(text or "")}


def mark_of(quote, original):
    """quote の直後（同じ行）の印から確度を決める。印が無ければ Unspecified。知らない印なら None。
    印は文の直後（句点「。」の後）に置くので、引用が句点を落としていれば句点を一つだけ越えて読む（N-46。2026-11-09 河原さん）。"""
    for line in original.splitlines():
        flat = _norm(line)
        pos = flat.find(_norm(quote))
        if pos < 0:
            continue
        rest = flat[pos + len(_norm(quote)):]
        if rest.startswith("。") and not _norm(quote).endswith("。"):
            rest = rest[1:]
        m = MARK.match(rest)
        if not m:
            return "Unspecified"
        for word, value in WEAKEST_FIRST:
            if word in m.group(1):
                return value
        return None
    return "Unspecified"


def receiver_certainty(provider):
    """他の機関から受けた事実の、受けた側から見た確度。提供元より強くしない（ADR D4、tsunagu-net BRS-44 と同じ）。"""
    return provider if provider in ("Inference", "Unspecified") else "Hearsay"


def _check_involvements(p, estimate, errors):
    """N-24a。関わりの案の点検。concerns は誰の関わりか（既定は本人。既にいる人の PER-… か newPeople の ref。正典 v0.7。台帳 G-60）。"""
    people = {x.get("ref") for x in p.get("newPeople") or []}
    quotes = {_norm(f.get("quote")) for f in p.get("facts") or [] if isinstance(f.get("quote"), str)}
    offered = {c["orgId"]: c.get("kind") for c in (estimate or {}).get("candidates", [])}
    kinds = canon.load(SCHEMA)["enums"]["involvementKind"]
    for n, inv in enumerate(p.get("involvements") or [], start=1):
        where = "関わり %d" % n
        if not isinstance(inv, dict):
            errors.append("%s: オブジェクトでなければならない" % where)
            continue
        for k in sorted(set(inv) - INVOLVEMENT_KEYS):
            errors.append("%s: %s という項目は無い（確度は書かない。点検が決める。窓口までは絞らない）" % (where, k))
        if _norm(inv.get("quote")) not in quotes:
            errors.append("%s: quote は案の事実の引用のどれか（根拠の記録に結ぶ）" % where)
        if inv.get("kind") not in kinds:
            errors.append("%s: kind %r は involvementKind のどれか" % (where, inv.get("kind")))
        elif inv["kind"] == "Guardianship":
            errors.append("%s: 後見（Guardianship）は推定で作らない" % where)
        org = inv.get("orgId")
        if org is not None and org not in offered:
            errors.append("%s: orgId %r は担当機関の推定の候補に無い（候補の中から選ぶ。選べなければ書かない）" % (where, org))
        name = inv.get("orgName")
        if name is not None:
            if not isinstance(name, str) or len(_norm(name)) < ORG_NAME_MIN:
                errors.append("%s: orgName は原文に書かれた機関の名前（%d 字以上の文字列。%r）" % (where, ORG_NAME_MIN, name))
            elif _norm(name) not in _norm(inv.get("quote") if isinstance(inv.get("quote"), str) else ""):
                errors.append("%s: orgName %r がこの関わりの quote（根拠の記録の引用）に無い（引用に書かれた名前だけを写す）" % (where, name))
        if name is not None and org is not None:
            errors.append("%s: orgName と orgId（住所からの推定の候補）を一つの関わりに両方書かない（確度の決まりが違う。SEM-REC-05）" % where)
        if name is not None and p.get("documentKind") == "ProvisionDocument":
            errors.append("%s: 情報提供の書面の関わりに orgName を書いたときの扱いは決めていない（決めるまで止める）" % where)
        ended = inv.get("howEnded")
        if ended is not None:
            if name is None:
                errors.append("%s: howEnded は機関の名前（orgName）のある関わりにだけ書ける（名前の無い関わりはいつも Unknown）" % where)
            elif ended in ENDED:
                errors.append("%s: howEnded %r：終わった関わりは今は案に書けない。事実の記録としては入る" % (where, ended))
            elif ended != "Ongoing":
                errors.append("%s: howEnded に書けるのは Ongoing だけ（原文から今も続いていると読めるとき。%r）" % (where, ended))
        service = inv.get("serviceTypeName")
        if service is not None and (not isinstance(service, str) or not service.strip()):
            errors.append("%s: serviceTypeName は原文に書かれたサービスの種類の文字列（%r）" % (where, service))
        target = inv.get("concerns")
        if target is not None and not (ids.is_valid_id(target, "PER") or target in people):
            errors.append("%s: concerns %r は既にいる人の ID（PER-…）か newPeople の ref（名前で結び付けない）" % (where, target))
        elif target is not None and org is not None:
            errors.append("%s: 住所からの推定で選んだ機関では、本人以外の人の関わりを作らない（住所が本人と違うことがある）" % where)
        if org is not None and org in offered and offered[org] == "GuardianshipCenter" and inv.get("kind") != "Consultation":
            errors.append("%s: 成年後見センターを推定で選んだ関わりは Consultation だけ（後見制度の相談の窓口。%r は作らない）" % (where, inv.get("kind")))


def _check_candidates(p, errors, warnings):
    """G-63。禁忌・推奨ケアの候補は、同じ案の事実の引用を根拠に指す。確度を持たせない。引用に無い数字を足さない。
    根拠が見立て（Inference）の記録だけなら、禁忌は止め、推奨ケアは注意を出して通す（確認点 L-0 の決めごと 8）。"""
    quotes = {_norm(f.get("quote")): f.get("quote") for f in p.get("facts") or [] if isinstance(f.get("quote"), str)}
    views = {_norm(f.get("quote")) for f in p.get("facts") or [] if isinstance(f.get("quote"), str) and f.get("certainty") == "Inference"}
    for key, (label, _, keys, texts) in CANDIDATES.items():
        for n, cand in enumerate(p.get(key) or [], start=1):
            where = "%s %d" % (key, n)
            if not isinstance(cand, dict):
                errors.append("%s: オブジェクトでなければならない" % where)
                continue
            for k in sorted(set(cand) - keys):
                note = "確度は根拠の事実のものを引き継ぐ" if k == "certainty" else "直さずに止める"
                errors.append("%s: %s という項目は無い（%s）" % (where, k, note))
            quote = quotes.get(_norm(cand.get("quote")))
            if quote is None:
                errors.append("%s: quote は案の事実の引用のどれか（根拠の記録に結ぶ。根拠が案に無ければ候補にしない）" % where)
                continue
            extra = sorted(set().union(*(_digits(cand.get(t)) for t in texts)) - _digits(quote))
            if extra:
                errors.append("%s: 原文の引用に無い数字 %s がある（補わない）" % (where, "・".join(extra)))
            if _norm(quote) in views and label == "NgAction":
                errors.append("%s: 根拠が見立て（確度 推測）の記録だけの禁忌は作らない（推測だけで禁忌にしない）。"
                              "事実として残し、確かめてから禁忌の案にする" % where)
            elif _norm(quote) in views:
                warnings.append("%s: 根拠が見立て（確度 推測）の記録だけの推奨ケア。承認の前に、試してよい支え方か確かめる" % where)


def _check_support_log(p, original, errors):
    """確認点 L-0 の決めごと 1〜5（正典 v0.13。SEMANTICS SEM-REC-04）。面接 1 回＝supportLog 1 件。"""
    log = p.get("supportLog")
    if log is None:
        return
    if not isinstance(log, dict):
        errors.append("supportLog: 面接 1 回に一つのオブジェクト（一覧にしない）")
        return
    for k in sorted(set(log) - SUPPORT_LOG_KEYS):
        note = "効果の判定は職員が行う。案に書かない" if k == "effectiveness" else "直さずに止める"
        errors.append("supportLog: %s という項目は無い（%s）" % (k, note))
    quotes = {_norm(f.get("quote")) for f in p.get("facts") or [] if isinstance(f.get("quote"), str)}
    if not isinstance(log.get("quote"), str) or not log["quote"].strip():
        errors.append("supportLog: 必須の quote が無い（接触の一文。案の事実の引用のどれか）")
    elif _norm(log["quote"]) not in quotes:
        errors.append("supportLog: quote は案の事実の引用のどれか（接触の一文を事実にして、その記録を根拠に結ぶ）")
    date = log.get("date")
    if date is None:
        errors.append("supportLog: 必須の date が無い（接触の日。YYYY-MM-DD）")
    else:
        try:
            ok = isinstance(date, str) and bool(FULL_DATE.match(date)) and bool(dt.date.fromisoformat(date))
        except ValueError:
            ok = False
        if not ok:
            errors.append("supportLog: date %r は実在する日（YYYY-MM-DD）でない（補わない）" % (date,))
    if not isinstance(log.get("situation"), str) or not log["situation"].strip():
        errors.append("supportLog: 必須の situation が無い（どこで・誰と。同席者は役割の名前で）")
    kinds = canon.load(SCHEMA)["enums"]["contactKind"]
    if "contactKind" in log and log["contactKind"] not in kinds:
        errors.append("supportLog: contactKind %r は %s のどれか（合わなければ書かない。読み替えない）"
                      % (log["contactKind"], "・".join(kinds)))
    extra = sorted(set().union(*(_digits(log.get(t)) for t in SUPPORT_LOG_TEXTS if isinstance(log.get(t), str))) - _digits(original))
    if extra:
        errors.append("supportLog: 原文に無い数字 %s がある（補わない）" % "・".join(extra))


def check(proposal, original, actor_staff_id, request_id, provider_org_id=None, estimate=None):
    """返り値 {"ok", "errors", "warnings", "request"}。止めるときは request が None。
    provider_org_id は、職員が候補から選んだ提供元の機関 ID（情報提供の書面のとき）。選んでいなければ needsProviderChoice を返す。"""
    p = copy.deepcopy(proposal)
    errors, warnings = [], []
    if not isinstance(p, dict) or not isinstance(original, str) or not original.strip():
        return {"ok": False, "errors": ["案はオブジェクト、原文は空でない文字列"], "warnings": [], "request": None}
    for k in sorted(set(p) - TOP_KEYS):
        if k == "providerOrgId":
            errors.append("案に機関 ID（providerOrgId）を書かない。原文の名前（providerName）を書き、候補から職員が選ぶ（N-24）")
        else:
            errors.append("案に %s という項目は無い（直さずに止める）" % k)
    refs = set()
    for person in p.get("newPeople") or []:
        for k in sorted(set(person) - PERSON_KEYS):
            errors.append("newPeople に %s という項目は無い（直さずに止める）" % k)
        ref = person.get("ref")
        if not isinstance(ref, str) or not REF.match(ref):
            errors.append("newPeople の ref %r は使えない：%s" % (ref, REF_RULE))
        elif RESERVED_REF.match(ref):
            errors.append("newPeople の ref %r は点検が使う名札なので使えない：別の名札にする（%s）" % (ref, REF_RULE))
        elif ref in refs:
            errors.append("newPeople の ref %r が重複している：一人に一つの名札にする" % ref)
        refs.add(ref)
    kind = p.get("documentKind")
    if kind not in DOC_KINDS:
        errors.append("documentKind は %s のどれか（%r）" % ("／".join(DOC_KINDS), kind))
    name = p.get("providerName")
    needs_choice = None
    if kind == "ProvisionDocument":
        if not isinstance(name, str) or not name.strip():
            errors.append("情報提供の書面には、原文の提供元の名前（providerName）が要る")
        elif not _in_original(name, original):
            errors.append("提供元の名前が原文に無い（%s）" % name[:30])
        if provider_org_id is None:
            needs_choice = name
            errors.append("提供元の機関が未確定。候補（org_candidates.by_name）から職員が選び、provider_org_id で渡す")
        elif not ids.is_valid_org_id(provider_org_id):
            errors.append("職員が選んだ提供元は機関 ID（ORG-…）でなければならない（%r）" % (provider_org_id,))
    if kind == "OwnCaseRecord" and (name is not None or provider_org_id is not None):
        errors.append("自分の記録に提供元（providerName・provider_org_id）を書かない")
    if not ids.is_valid_id(p.get("clientId"), "CLI"):
        errors.append("clientId は既にいる本人の ID（CLI-…）")
    facts = p.get("facts") or []
    enums = canon.load(SCHEMA)["enums"]
    if not facts:
        errors.append("事実（facts）が無い")
    for n, f in enumerate(facts, start=1):
        where = "事実 %d" % n
        for k in sorted(set(f) - FACT_KEYS):
            errors.append("%s: %s という項目は無い（直さずに止める）" % (where, k))
        quote = f.get("quote")
        if not isinstance(quote, str) or not quote.strip():
            errors.append("%s: 原文の該当箇所（引用 quote）が要る" % where)
            continue
        if not _in_original(quote, original):
            errors.append("%s: 引用が原文に無い（%s）" % (where, quote[:30]))
            continue
        text = f.get("text")
        if text is not None and _norm(text) != _norm(quote):
            extra = sorted(_digits(text) - _digits(quote))
            if extra:
                errors.append("%s: 本文に原文の引用に無い数字 %s がある（補わない）" % (where, "・".join(extra)))
            else:
                warnings.append("%s: 本文は引用の言い換え。承認の前に原文と見比べる" % where)
        told = f.get("toldBy")
        if told is not None and not (told == "client" or ids.is_valid_id(told, "PER") or told in refs):
            errors.append("%s: toldBy の %r は既にいる人の ID（PER-…）・newPeople の ref・client のどれでもない（名前で結び付けない）" % (where, told))
        if "informantKind" not in f and f.get("certainty") == "Inference":
            errors.append("%s: 見立て（確度 推測）には、もとになった情報源を informantKind に書く（本人の話なら Self、"
                          "家族の話なら Family、近隣・知人の話なら Neighbor、職員の観察なら Agency、記録だけなら DocumentOnly）" % where)
        for key, enum in (("recordKind", "recordKind"), ("informantKind", "informantKind")):
            if key not in f:
                if not (key == "informantKind" and f.get("certainty") == "Inference"):
                    errors.append("%s: 必須の %s が無い（%s のどれか）" % (where, key, "・".join(enums[enum])))
            elif f[key] not in enums[enum]:
                errors.append("%s: %s %r は %s のどれか（読み替えない）" % (where, key, f[key], "・".join(enums[enum])))
        marked = mark_of(quote, original)
        if marked is None:
            errors.append("%s: 原文の印を読めない（知らない印）。推測で読み替えない" % where)
            continue
        if kind == "ProvisionDocument":
            if f.get("providerCertainty") != marked:
                errors.append("%s: 提供元の確度 %r が原文の印（%s）と違う（格上げも格下げもしない）" % (where, f.get("providerCertainty"), marked))
            want = receiver_certainty(marked)
            if f.get("certainty") != want:
                errors.append("%s: 受けた側の確度は %s（他の機関からの情報。%r は書けない）" % (where, want, f.get("certainty")))
        else:
            if "providerCertainty" in f:
                errors.append("%s: 自分の記録に提供元の確度を書かない" % where)
            want_kind = VIEW_RECORD_KIND.get(f.get("informantKind"))
            if f.get("certainty") == "Inference" and want_kind and f.get("recordKind") != want_kind:
                errors.append("%s: 見立て（確度 推測）の記録の種類は、もとになった情報に合わせる（Self・Family・Neighbor なら Interview、"
                              "Agency なら Observation、DocumentOnly なら Document）。informantKind %s なら recordKind は %s（%r は書けない）"
                              % (where, f["informantKind"], want_kind, f.get("recordKind")))
            if f.get("certainty") != marked:
                errors.append("%s: 確度 %r が原文の印（%s）と違う（格上げも格下げもしない）" % (where, f.get("certainty"), marked))
    _check_involvements(p, estimate, errors)
    _check_candidates(p, errors, warnings)
    _check_support_log(p, original, errors)
    used = {f.get("toldBy") for f in facts} | {inv.get("concerns") for inv in p.get("involvements") or [] if isinstance(inv, dict)}
    for ref in sorted(r for r in refs if isinstance(r, str) and r not in used):  # N-46 #10。確認点 L-0 の決めごと 10 で止める形に
        errors.append("newPeople の %s は、どの事実の toldBy にも、どの関わりの concerns にも使われていない"
                      "（根拠の記録にも本人にも結ばれない人になる）。どの事実の toldBy か関わりの concerns に書くか、案から外す" % ref)
    notes = list((estimate or {}).get("notes", [])) if p.get("involvements") else []
    if errors:
        out = {"ok": False, "errors": errors, "warnings": warnings, "request": None, "notes": notes}
        if needs_choice is not None:
            out["needsProviderChoice"] = needs_choice
        return out
    return {"ok": True, "errors": [], "warnings": warnings, "notes": notes,
            "request": _request(p, original, actor_staff_id, request_id, provider_org_id, estimate)}


def _request(p, original, actor_staff_id, request_id, provider_org_id, estimate=None):
    doc_hash = hashlib.sha256(original.encode("utf-8")).hexdigest()
    client = {"label": "Client", "id": p["clientId"]}
    staff = {"label": "Staff", "id": actor_staff_id}
    nodes, rels = [], []
    if p["documentKind"] == "ProvisionDocument":
        nodes.append({"ref": "provider", "label": "Organization", "origin": "Human", "properties": {"orgId": provider_org_id}})
    for person in p.get("newPeople") or []:
        nodes.append({"ref": person["ref"], "label": "Person", "origin": "AiExtracted",
                      "properties": {k: v for k, v in person.items() if k != "ref"}})
    for n, f in enumerate(p["facts"], start=1):
        ref = "fact-%d" % n
        props = {"kind": f.get("recordKind"), "text": f.get("text") or f["quote"], "quote": f["quote"],
                 "certainty": f.get("certainty"), "informantKind": f.get("informantKind"), "documentHash": doc_hash}
        for k in ("aboutDate", "heardOn"):
            if f.get(k):
                props[k] = f[k]
        if p["documentKind"] == "ProvisionDocument":
            props["providerCertainty"] = f.get("providerCertainty")
            if p.get("receivedOn"):
                props["receivedOn"] = p["receivedOn"]
            rels.append({"type": "PROVIDED_BY", "from": ref, "to": "provider"})
        nodes.append({"ref": ref, "label": "Record", "origin": "AiExtracted", "properties": props})
        rels.append({"type": "ABOUT", "from": ref, "to": client})
        rels.append({"type": "AUTHORED_BY", "from": ref, "to": staff})
        told = f.get("toldBy")
        if told == "client":
            rels.append({"type": "TOLD_BY", "from": ref, "to": client})
        elif told:
            rels.append({"type": "TOLD_BY", "from": ref, "to": {"label": "Person", "id": told} if told.startswith("PER-") else told})
    fact_refs = {_norm(f["quote"]): "fact-%d" % n for n, f in enumerate(p["facts"], start=1)}
    orgs = {provider_org_id: "provider"} if p["documentKind"] == "ProvisionDocument" else {}
    for n, inv in enumerate(p.get("involvements") or [], start=1):
        ref = "involvement-%d" % n
        nodes.append({"ref": ref, "label": "Involvement", "origin": "AiExtracted",
                      "properties": {"kind": inv["kind"], "howEnded": "Unknown", "certainty": "Inference"}})
        if inv.get("orgName"):  # 名前のある関わりは根拠の記録の確度を写す。強くしない（SEM-REC-05）
            evidence = next(n for n in nodes if n["ref"] == fact_refs[_norm(inv["quote"])])
            nodes[-1]["properties"]["certainty"] = evidence["properties"]["certainty"]
            if inv.get("howEnded") == "Ongoing":
                nodes[-1]["properties"]["howEnded"] = "Ongoing"
        if inv.get("serviceTypeName"):
            nodes[-1]["properties"]["serviceTypeName"] = inv["serviceTypeName"].strip()
        target = inv.get("concerns")
        rels.append({"type": "CONCERNS", "from": ref,
                     "to": client if target is None else {"label": "Person", "id": target} if target.startswith("PER-") else target})
        rels.append({"type": "EVIDENCED_BY", "from": ref, "to": fact_refs[_norm(inv["quote"])]})
        if inv.get("orgId"):
            basis = INFERENCE_BASIS.get((estimate or {}).get("basis"))
            if basis:
                nodes[-1]["properties"]["inferenceBasis"] = basis
            if inv["orgId"] not in orgs:
                orgs[inv["orgId"]] = "estimated-org-%d" % n
                nodes.append({"ref": orgs[inv["orgId"]], "label": "Organization", "origin": "AiExtracted",
                              "properties": {"orgId": inv["orgId"]}})
            rels.append({"type": "HAS_INVOLVEMENT", "from": orgs[inv["orgId"]], "to": ref})
    for key, (label, rel, _, _) in CANDIDATES.items():
        for n, cand in enumerate(p.get(key) or [], start=1):
            ref = "%s-%d" % (label[0].lower() + label[1:], n)
            nodes.append({"ref": ref, "label": label, "origin": "AiExtracted",
                          "properties": {k: v for k, v in cand.items() if k != "quote"}})
            rels.append({"type": rel, "from": client, "to": ref})
            rels.append({"type": "EVIDENCED_BY", "from": ref, "to": fact_refs[_norm(cand["quote"])]})
    log = p.get("supportLog")
    if log is not None:
        nodes.append({"ref": "support-log", "label": "SupportLog", "origin": "AiExtracted",
                      "properties": {k: v for k, v in log.items() if k != "quote"}})
        rels.append({"type": "ABOUT", "from": "support-log", "to": client})
        rels.append({"type": "AUTHORED_BY", "from": "support-log", "to": staff})
        rels.append({"type": "EVIDENCED_BY", "from": "support-log", "to": fact_refs[_norm(log["quote"])]})
    return {"requestId": request_id, "actorStaffId": actor_staff_id, "nodes": nodes, "relationships": rels}
