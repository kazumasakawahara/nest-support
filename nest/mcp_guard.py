"""読み取りだけの MCP の包みの歯止め（N-22。ADR-001 D6・D11-2、external-api NEXT-02）。個人の側と資源の側で共有する。

Community 版には DB の側の権限が無いので、ここで止める。手本：tsunagu-net の枝 claude/tender-dijkstra-xo3wwc の
コミット d8e6e2d の tsunagu/mcp_resource.py（読むだけ）。
- 受け取った Cypher を先に EXPLAIN にかけ、問い合わせの種類（query_type）が読み取り（r）でなければ実行しない。歯止めはここ。
  実行のときの routing_="r"（読み取りのトランザクション）は保険で、アクセス制御にはならない（tsunagu-net G-14）
- 種類が r でも、計画に LOAD CSV があれば実行しない（DB から外への通信・ファイル読みになる）
- 手続きの呼び出しは許可の一覧（ALLOWED_PROCEDURES）だけ。apoc.* は入れない
- 計画が読めないときは実行しない（閉じる側に倒す）。EXPLAIN・PROFILE つきと空も拒否する
- 返す行は流しながら MAX_ROWS で止める。全部を受け取ってから切らない。Cypher に行数の制限を差し込まない
個人の側だけ（personal=True）：
- 注釈（// と /* */）、実名・かな・電話・住所・生年月日（SENSITIVE）の項目の名前を含む問い合わせ、properties()・keys()・{.*}、
  動的な項目の読み（n[k]・n['…']）を、実行の前に拒否する
- 返すノード・マップから SENSITIVE の項目を外す。返す値のうち、DB にある SENSITIVE の値とそっくり同じ文字列は伏せる
- 記録の原文全体（text）は返さない。引用（quote）は自由な Cypher では読ませず、求められたときだけ専用の道具で
  QUOTE_MAX 字までを返す（2026-11-06 河原さん。台帳 G-42 (1)。語りの中の人は役割の名前で書く運用と両方）
- 包みが動く条件（require_personal_allowed）：NEXT-02 の歯止め（機能の設定と契約の確認の記録）がそろうか、
  つないでいる DB に架空の印（NestLiveProbe。台帳 G-51）があるときだけ。どちらも無ければ拒否する（台帳 G-54 (3)）
  この歯止めは Claude へ送る経路（MCP の包み、caller="mcp"。既定）のため。外に送らない画面（field-ui・SOS、caller="screen"）は
  歯止めを通さず、伏せ字（run_read の personal=True）だけを当てる。知らない呼び出し元は拒否する（2026-11-06 河原さん。台帳 G-85）
  架空の DB に印を置くのは人の手（ゲートを通さない）：CREATE (:NestLiveProbe {fictional: true})
"""
import re

from mcp.server.mcpserver.exceptions import ToolError

MAX_ROWS = 500
MASK = "［伏せ字］"
REFUSED_PREFIXES = ("EXPLAIN", "PROFILE")
DENIED_OPERATORS = frozenset({"LoadCSV"})
ALLOWED_PROCEDURES = frozenset({"db.labels", "db.relationshipTypes", "db.propertyKeys"})
SENSITIVE = ("familyName", "givenName", "familyNameKana", "givenNameKana", "phone", "address", "birthDate")
# 個人の側で、返さない（text）・専用の道具でだけ返す（quote）項目
RECORD_TEXT = ("text", "quote")
TEXT_ACCESS = re.compile(r"\.\s*`?(text|quote)`?(?![\w$])")
QUOTE_MAX = 200
FICTIONAL_MARK = "MATCH (m:NestLiveProbe) RETURN count(m) > 0 AS marked"
WHOLE_PROPERTIES = re.compile(r"\b(properties|keys)\s*\(|\{\s*\.\s*\*", re.I)
# 角かっこの前がこれらの語なら、一覧の書き方（[1, 2]）であって、項目の読みではない
LIST_KEYWORDS = frozenset({"RETURN", "WITH", "IN", "WHERE", "AND", "OR", "NOT", "XOR", "UNWIND", "CASE", "WHEN", "THEN",
                           "ELSE", "YIELD", "DISTINCT", "BY", "CONTAINS", "IS", "SKIP"})
# この字の後の角かっこは一覧の書き方（[1, 2]）。区切り・演算子・開きかっこ
LIST_OPENERS = frozenset("(,[{=|:+-*<>%^")
INDEX_ONLY = re.compile(r"\s*(-?\d+\s*(\.\.\s*-?\d*\s*)?|\.\.\s*-?\d+\s*)\]")


class NotReadOnly(ToolError):
    """読み取り以外、または個人の側で返さない項目に触れる問い合わせ。"""


def _operators(plan):
    stack = [plan]
    while stack:
        node = stack.pop()
        if not isinstance(node, dict):
            raise NotReadOnly("計画が読めないので実行しない")
        op = str(node.get("operatorType", "")).split("@")[0]
        details = str((node.get("args") or {}).get("Details", ""))
        yield op, details
        stack.extend(node.get("children") or [])


def _procedure_name(details):
    if "(" not in details:
        return ""
    return details.split("(")[0].strip()


def check_plan(plan):
    if not isinstance(plan, dict) or not plan:
        raise NotReadOnly("計画が取れないので実行しない")
    for op, details in _operators(plan):
        if not op:
            raise NotReadOnly("計画が読めないので実行しない")
        if op in DENIED_OPERATORS:
            raise NotReadOnly("LOAD CSV は使えない（DB から外への通信・ファイル読みになるため）")
        if op == "ProcedureCall" and _procedure_name(details) not in ALLOWED_PROCEDURES:
            raise NotReadOnly("許可の一覧に無い手続きは呼ばない（使えるのは %s）" % "・".join(sorted(ALLOWED_PROCEDURES)))


def _dynamic_access(text):
    """n[k]・n['x']・(n)[…] のような、名前を文字で組み立てられる項目の読みを見つける。
    角かっこは、一覧の書き方と分かる位置（文の始め・演算子や区切りの後・LIST_KEYWORDS の語の後）だけ通し、
    ほかの位置では数の添字（xs[0]・xs[1..2]）のときだけ通す（閉じる側に倒す）。"""
    for m in re.finditer(r"\[", text):
        before = text[:m.start()].rstrip()
        if not before or before[-1] in LIST_OPENERS:
            continue
        # 語は、後ろに続く識別子の字（日本語の字・数字・$ を含む）をまるごと取り、英字だけで LIST_KEYWORDS と同じときだけ通す
        word = re.search(r"[\w$]+$", before)
        if word and re.fullmatch(r"[A-Za-z]+", word.group(0)) and word.group(0).upper() in LIST_KEYWORDS:
            continue
        if not INDEX_ONLY.match(text, m.end()):
            return True
    return False


def check_personal_text(text):
    if "//" in text or "/*" in text:
        raise NotReadOnly("個人の側では注釈（// と /* */）を使わない（点検をすり抜ける形になるため）")
    low = text.lower()
    for name in SENSITIVE:
        if name.lower() in low:
            raise NotReadOnly("個人の側では %s を読まない（実名・かな・電話・住所・生年月日は返さない）" % name)
    if TEXT_ACCESS.search(text):
        raise NotReadOnly("個人の側では記録の原文（text）と引用（quote）を読まない。引用は read_quote で求める（台帳 G-42）")
    if WHOLE_PROPERTIES.search(text):
        raise NotReadOnly("個人の側では properties()・keys()・{.*} を使わない（返さない項目まで出るため）")
    if _dynamic_access(text):
        raise NotReadOnly("個人の側では項目を名前の文字で読まない（n[k] など）。n.項目名 で読む")


def check_read_only(driver, query, params, personal=False, database="neo4j"):
    text = (query or "").strip()
    if not text:
        raise NotReadOnly("問い合わせが空")
    if text.upper().startswith(REFUSED_PREFIXES):
        raise NotReadOnly("EXPLAIN・PROFILE を付けずに渡す")
    if personal:
        check_personal_text(text)
    _, summary, _ = driver.execute_query("EXPLAIN " + text, params or {}, database_=database)
    if summary.query_type != "r":
        raise NotReadOnly("読み取り以外の問い合わせ（種類 %s）は実行しない" % summary.query_type)
    check_plan(getattr(summary, "plan", None))
    return text


def to_plain(value, personal, sensitive_values=frozenset()):
    """ドライバの値を JSON にできる形にする。個人の側では SENSITIVE の項目と、その値とそっくり同じ文字列を伏せる。"""
    if hasattr(value, "labels") and hasattr(value, "items"):  # Node
        out = {"_labels": sorted(value.labels)}
        out.update(_props(value.items(), personal, sensitive_values))
        return out
    if hasattr(value, "type") and hasattr(value, "items") and hasattr(value, "start_node"):  # Relationship
        out = {"_type": value.type}
        out.update(_props(value.items(), personal, sensitive_values))
        return out
    if hasattr(value, "nodes") and hasattr(value, "relationships"):  # Path
        return {"nodes": [to_plain(n, personal, sensitive_values) for n in value.nodes],
                "relationships": [to_plain(r, personal, sensitive_values) for r in value.relationships]}
    if isinstance(value, dict):
        return _props(value.items(), personal, sensitive_values)
    if isinstance(value, (list, tuple)):
        return [to_plain(v, personal, sensitive_values) for v in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = value if isinstance(value, str) else str(value.isoformat() if hasattr(value, "isoformat") else value)
    if personal and text in sensitive_values:
        return MASK
    return text


def _props(items, personal, sensitive_values):
    return {k: to_plain(v, personal, sensitive_values) for k, v in items
            if not (personal and (k in SENSITIVE or k in RECORD_TEXT))}


SENSITIVE_VALUES = ("MATCH (n) UNWIND [k IN $names WHERE n[k] IS NOT NULL | n[k]] AS v "
                    "RETURN collect(DISTINCT toString(v)) AS vs")


def stream_rows(tx, text, params, personal, sensitive_values=frozenset()):
    """結果を流しながら読み、MAX_ROWS 行で止める。"""
    rows = []
    for record in tx.run(text, params or {}):
        rows.append({k: to_plain(v, personal, sensitive_values) for k, v in record.items()})
        if len(rows) >= MAX_ROWS:
            break
    return rows


def run_read(driver, query, params, personal, database="neo4j"):
    text = check_read_only(driver, query, params, personal=personal, database=database)

    def work(tx):
        values = frozenset()
        if personal:
            values = frozenset(list(tx.run(SENSITIVE_VALUES, names=list(SENSITIVE)))[0]["vs"])
        return stream_rows(tx, text, params, personal, values)

    with driver.session(database=database) as s:
        return s.execute_read(work)


CALLERS = ("mcp", "screen")


def require_personal_allowed(driver, database="neo4j", caller="mcp"):
    """個人の側の包みが動いてよいかを確かめる（台帳 G-54 (3)・G-85）。

    caller="mcp"（既定）：NEXT-02 がそろうか、架空の印のある DB のときだけ。caller="screen"：外に送らない画面なので通す。
    """
    if caller not in CALLERS:
        raise NotReadOnly("知らない呼び出し元（%s）なので読まない" % caller)
    if caller == "screen":
        return
    from nest import egress
    try:
        egress.authorize("NEXT-02")
        return
    except egress.EgressDenied as e:
        reason = str(e)
    records, _, _ = driver.execute_query(FICTIONAL_MARK, {}, database_=database, routing_="r")
    if records and records[0]["marked"]:
        return
    raise NotReadOnly("NEXT-02 の歯止めがそろっていない（%s）。架空の印（NestLiveProbe）のある DB でもないので読まない" % reason)


def cap_quote(quote):
    """引用を QUOTE_MAX 字までにする（台帳 G-42 (1)）。"""
    text = quote or ""
    return {"quote": text[:QUOTE_MAX], "truncated": len(text) > QUOTE_MAX}
