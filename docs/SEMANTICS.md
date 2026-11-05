# nest-support 意味の文書（SEMANTICS）

正典 `docs/SCHEMA.md` が扱わない、業務上の意味・運用の規則・列挙値の日本語の表示名を置く（正典 §1、ADR-001 D1）。
列挙値の日本語の表示名は計画 N-27 で足す。今あるのは担当機関の推定（計画 N-24a）の節だけ。

## 担当機関の推定（N-24a。2026-11-05 河原さんの指示）

語りの「区役所の窓口で」のように機関の名前が無い言及に、本人の住所の区で絞った資源の側の機関の候補を添え、
Claude が確度 `Inference` の関わり（`Involvement`）の案を作れるようにする。埋め込み（文の近さ）は使わない。選ぶ根拠は住所。

### SEM-AREA-01 住所から団体コード（区）を出す

- ゲートが `Residence` を登録するとき、住所の文から 6 桁の団体コードを出して `areaCode` に持つ（`nest/area_code.py`）。依頼に `areaCode` があって住所から出した値と違えば止める
- 手元だけで出す。住所の文を外（ジオコーディングなど）に送らない
- 住所を Unicode の NFKC にそろえ、空白を除き、先頭の「福岡県」を外してから、表の名前（「北九州市小倉北区」「遠賀郡芦屋町」「芦屋町」など）が**住所の先頭に一致する**もののうち、いちばん長いものを採る
- 一致しなければ空。区の名前だけ（「小倉北区…」）・町名だけからは推測しない。空なら推定は機関未確定に倒す

**表の出どころと版**

| 項目 | 値 |
|---|---|
| ファイル | `nest/data/area-codes-kitakyushu-2026-10-25.json`（40 行） |
| 出どころ | 総務省「都道府県コード及び市区町村コード」令和6年1月1日現在（https://www.soumu.go.jp/denshijiti/code.html ） |
| 写し元 | tsunagu-net の `docs/reference/area-codes-kitakyushu-2026-10-25.json`（コミット `74ac35a`。読むだけ。変えずにそのまま写した） |
| 指紋（SHA-256） | `a7700fd45f8e7811964531344bcf0584022de9c6b7fde0f02df6212fa7e291db`（`nest/area_code.py` が読むたびに確かめる） |
| 範囲 | 北九州市と 7 区、近隣の市町村（tsunagu-net の ADR-001 D10 の範囲と、その表にある近隣） |

範囲の外の住所は空になる（機関未確定）。範囲を広げるときは表を差し替え、指紋とこの節を同時に直す。

### SEM-AREA-02 どの住所で推定するか

- 過去の言及は、言及の時期（記録の `aboutDate`）に住んでいた住所（`since` ≦ 時期 ＜ `until`）の区で推定する
- 当時の住所が記録に無いとき（`since` が空のものは当時の住所に数えない）は、今の住所（`until` が空のもの）で推定し、「今の住所で推定した」旨を案の注記（点検の結果の `notes`）に書く。職員は承認の前にそれを見る
- 言及の時期が分からないときも、今の住所で推定し、その旨を書く
- 今の住所が無い・二つある・区が出ていないときは、候補を出さない（機関未確定）
- 使う住所は承認済み（`status: Active`）のものだけ

### SEM-AREA-03 候補の絞り方

- 資源の側で、その区と、`PART_OF` で上にある市を `SERVES` で担当する機関のうち、`status: Active` で、種類が次の相談窓口のもの：
  `DisabilityDivision`・`ElderlyDivision`・`CommunityGeneralSupportCenter`・`HardshipSupportDesk`・`WelfareOffice`・`BasicConsultationCenter`・`CareInsuranceDivision`・`MentalHealthDesk`（台帳 G-57）
- 担当の根拠（`servesBasis`：`Designated`／`PresumedByLocation`）と、区の一部だけを担当するか（`partOfArea`）を候補に添える。`PresumedByLocation` を `Designated` に格上げしない（tsunagu-net BRS-23）
- 点数づけをしない。区の担当を先に、市の担当を後に、名前の順に並べる
- Claude に渡すのは候補の `orgId` と名前だけ（公開情報）。区コード・住所・根拠は渡さない（`docs/external-api.md` NEXT-01）

### SEM-AREA-04 案と確定

- Claude は語りの文脈で候補から一つ選ぶか、選ばない（機関未確定）。候補の外の機関 ID は点検（`intake.check`）が止める
- 関わりの確度はいつも `Inference`、終わり方は `Unknown`。案に確度を書かせない。AI 由来なので `Pending`。職員が承認して初めて確定する（N-21）
- 後見（`Guardianship`）は推定で作らない
- 窓口（`Window`）までは絞らない。機関の単位で止め、窓口は未確定にする。間違った窓口を確定させない
