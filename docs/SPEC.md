# 「しつもんしてね」仕様書

最終更新: 2026-11-12（第3版）
対象: `http://192.168.0.4/ask/`（LXC 101 `draw-pad`）
ソース: `ask/index.html`、`ask-server/ask_proxy.py`、`ask-server/nginx-draw-pad.conf`

---

## 1. 目的と範囲

家庭内 LAN の iPad から、子ども（幼児〜小学生）と中学生が「なぜ？」を
1 問ずつ質問し、Web の公的資料で裏づけを取った答えを読むためのツール。

- 画面は **1 問 1 答**。新しい質問をすると前の答えは消える。
- ブラウザーには履歴を残さない（`localStorage` / `IndexedDB` / Cookie を使わない）。
- 質問と答えは **サーバー側にのみ** 全件記録する。
- API キーはブラウザーへ渡さない。ブラウザーが触れるのは同一オリジンの `/ask/api/` だけ。

範囲外: 音声入力（`getUserMedia` は HTTPS 必須のため未実装）、複数ターンの会話、
ログイン、外部公開。

---

## 2. 画面仕様

### 2.1 構成（上から順）

| 要素 | id | 内容 |
| --- | --- | --- |
| 戻るボタン | — | `← どうぐいちらん`（44px の丸ボタン、`/` へ） |
| 見出し | — | `？ しつもんしてね` |
| 使用量バー | `usage` | `きょうの トークン` / `きょうの 費用` / `のこり N 回` / `この しつもん` |
| 質問カード | `ask-form` | モード切替、きょうの なぜ？（`daily`）、入力欄、`おしえて！`、`けす`、文字数カウンター |
| 分野タブ | `cats` | モード別の分野切り替えタブ（`すべて`＋5〜6分野） |
| 質問例 | `chips` | 選択中の分野から 5 問のチップ＋`ほかの しつもんを みる` |
| 進行表示 | `thinking` | `しらべているよ…`（`aria-live="polite"`） |
| 答え | `answer` | 本文（`answer-text`）、注意書き（`notice`）、クリック可能な出典リンク（`sources`）、`よみあげ`、`もういちど` |
| エラー | `error` | `role="alert"`。通信失敗・上限・混雑をやわらかく表示 |
| 管理者画面ボタン | `admin-toggle` | ページ最下部の `おうちの ひとへ（管理・ログ）` |
| 管理者パネル | `admin-panel` | モデル選択、表示する文の長さ（文数・字数）、パスワード設定、検索ログ一覧（日時・質問・回答・消費トークン） |

### 2.2 モード

| | こども向け（`kid`） | 中学生向け（`teen`） |
| --- | --- | --- |
| 対象 | 幼児〜小学生 | 中学生 |
| 文数・字数 | 4 文 / 420 字 | 6 文 / 600 字 |
| 文体 | ひらがな多め、`〜だよ` | `〜です・ます` の説明文 |
| ふりがな | あり | あり（`rt` は 0.42em） |
| 生成トークン上限 | 800 | 1,100 |
| 読み上げ | rate 0.88 / pitch 1.15 / 文間 220ms | rate 1.00 / pitch 1.00 / 文間 150ms |

切り替えは `mode-kid` / `mode-teen` の 2 ボタン。`aria-pressed` と `body.teen` が連動し、
質問例・文体・読み上げパラメータが同時に入れ替わる。切り替え時に答えと読み上げは破棄する。

### 2.3 「きょうの なぜ？」と分野別の質問例チップ

- **きょうの なぜ？（`daily`）**:
  - モード切替のすぐ下に、その日の季節（春 3〜5月 / 夏 6〜8月 / 秋 9〜11月 / 冬 12〜2月）に合った質問を日付シード（`YYYYMMDD`）で 1 問ピックアップして表示する（`renderDaily`）。
  - こども向けは `きょうの なぜ？`、中学生向けは `M月D日の なぜ？` のバッジを付け、押すとそのまま質問を送信する。
- **分野タブ（`cats`）**:
  - こども向け: `すべて`（400） / `しぜん・うちゅう`（76） / `いきもの`（51） / `からだ・たべもの`（47） / `くらし・のりもの`（126） / `がっこうの まなび`（100）。
  - 中学生向け: `すべて`（400） / `物理・化学`（74） / `生物・人体`（50） / `地学・宇宙・環境`（74） / `数学・情報`（47） / `歴史・社会・経済`（125） / `ことば・芸術`（30）。
  - タブを押すと `aria-pressed` が切り替わり、その分野のプールから 5 問を即座に選び直す（`renderCategories` → `renderChips`）。
- **質問例チップ（`chips`）**:
  - 選択中の分野プールから **重複なしで 5 問** をランダムに選ぶ（`renderChips`）。
  - 選び直す契機: ページを開いたとき / 分野タブを切り替えたとき / 「けす」/ 「ほかの しつもんを みる」。
  - チップを押すと入力欄へ転記し、そのまま送信する。
  - プール・分野定義・日替わり選出はすべてブラウザー内の静的処理のみ。サーバー呼び出しも費用も発生しない。

### 2.4 使用量表示

- 起動時に `GET /ask/api/usage` を 1 回呼び、回答ごとにレスポンスの `estimate` で更新する。
- `きょうの トークン`: 当日の合計トークン（カンマ区切り）。
- `きょうの 費用`: `spend.json` の当日累計（USD、小数 2 桁）。
- `のこり N 回`: `(ASK_DAILY_USD_MAX − 当日費用) ÷ 1 問あたり平均` の切り捨て。
  平均は当日の実測（`tokens.json` の `cost` ÷ `measured`）。実測が無い日は `ASK_PER_QUESTION_EST`。
- `この しつもん`: 直前の 1 問で使ったトークン。
- 取得できない項目は `—`。

### 2.5 読み上げ・音声入力（Web Speech API）

外部サービスを使わない。ブラウザー標準の Web Speech API のみで動作する。

- **読み上げ（`speechSynthesis`）**:
  - 話者: `lang` が `ja` の音声から `VOICE_PREFERENCE`
    （`kyoko` → `o-ren` → `nanami` → `haruka` → `ayumi` → `sayaka` → `mizuki` → `google 日本語`）の順で選ぶ。
    見つからなければ `ja` の先頭。`voiceschanged` で選び直す。
  - 文分割: `SENTENCE_RE` で文に分け、`<span class="sent">` に入れる（ふりがなは各文の内側）。
  - 読み上げは 1 文ずつ `SpeechSynthesisUtterance` を作り、`onend` の後 `文間` ms 待って次へ。
  - 読み上げ中の文には `class="sent spoken"`（薄い緑の帯）。
  - `speakingGen` の世代番号で、新しい質問・「けす」・モード切替時に古い発話を確実に破棄する。
  - 読み上げ用文字列は `toSpeechText` で作る（`漢字(よみ)` → 漢字、かっこ書き除去、空白圧縮）。
- **音声入力（`SpeechRecognition` / `webkitSpeechRecognition`）**:
  - 文字入力が苦手な幼児・低学年向けに、画面の「こえで きく（マイクボタン）」から声で質問可能。
  - `interimResults: true` により、発話中の言葉がリアルタイムにテキストエリアに反映される。
  - 発話終了（`onend`）で自動的に録音停止・テキスト確定。非対応ブラウザーではボタンを自動非表示。

### 2.6 「つぎは これを きいてみる？」（関連質問・深掘りチップ）

- 回答受信時、その内容を踏まえて子どもが次に興味を持ちそうな関連疑問（2〜3問）をチップとして自動表示。
- チップをクリックすると質問欄にテキストが入り、そのまま自動送信されて次の回答をスムーズに調べられる。
- 疑問文にはルビ（`<ruby>`）が付き、モード（こども向け/中学生向け）に応じた適切な深さの疑問が提示される。

### 2.7 状態と操作

| 操作 | 挙動 |
| --- | --- |
| 送信 | 入力 2 文字以上で `POST /ask/api/ask`。二重送信は無効化。 |
| 音声入力 | 「こえで きく」を押して話す。認識結果が質問欄に入り、終了時にフォーカス。 |
| 関連質問 | チップをタップすると質問欄にセットされ、自動で次の回答を調べる。 |
| 成功 | 答えを差し替え、ふりがなを付け、関連質問と出典を表示し、自動で読み上げる |
| 失敗 | `error` にメッセージ。答えは消さない（直前の答えを保持） |
| `けす` | 入力・答え・出典・関連質問・読み上げを消し、チップを選び直す |
| `もういちど` | 同じ質問を再送する |
| 文字数 | 120 文字まで（`maxlength="160"` の textarea を JS 側で 120 に制限し、`n / 120` を表示） |

### 2.8 デザインの共通ルール（全 8 ページ共通）

- `.back` 丸ボタン（44px、`← どうぐいちらん`）。
- `h1`: `clamp(30px, 5.2vw, 44px)`、`font-weight: 740`、`letter-spacing: -.05em`。
- `.lead` / `.intro`: 15px、行間 1.8。
- body の余白: `24px clamp(16px, 4vw, 54px) 32px`（スマホは `14px …`）。
- カード: 角丸 20px、`0 8px 28px rgb(39 43 31 / 5%)`。

### 2.8 保存しないもの

`localStorage`、`sessionStorage`、`IndexedDB`、Cookie を一切使わない。
リロードすると質問も答えも消える（記録はサーバー側に残る）。

---

## 3. 質問プール

| プール | 定数 | 件数 | 記法 |
| --- | --- | --- | --- |
| こども | `QUESTIONS` | 400 | ひらがな中心。ふりがな前提。 |
| 中学生 | `TEEN_QUESTIONS` | 400 | 漢字かな交じり。 |

### 3.1 内訳

こども（400 問）

- しぜん・てんき 14 / きせつ 8 / しょくぶつ 8 / どうぶつ 19 / からだ 15 / たべもの 8
- うちゅう 8 / しくみ・のりもの 12 / ことば・くらし 8 / ちがく・しぜん 32
- くらし・るーる 18 / おかね・くらし 25 / むかしの はなし 25
- 小学校の学習内容 100（`// しょうがっこうで まなぶ こと` 以降）
  - こくご・ことば 15 / さんすう 25 / りか 21 / しゃかい 19 / せいかつ・たいいく・おんがく 20
- 身近な疑問・追加分 100
  - からだ・けんこう 15 / どうぶつ・いきもの 15 / しょくぶつ・たべもの 15 /
    しぜん・うちゅう・のりもの 15 / くらし・みのまわり 15 / ことば・あそび・がっこう 15 /
    ちきゅう・いきもの・ふしぎ 10

中学生（400 問）

- ぶつり 22 / かがく 21 / せいぶつ 22 / ちがく・うちゅう 23 / すうがく 8 /
  じょうほう・ぎじゅつ 4 / せいじ・こうみん 18 / ちしつ・ちきゅうかがく 22 /
  はってん 10 / きんゆう・けいざい 25 / れきし 25
- 小学校の学習内容 100（`// しょうがく こうがくねん` 以降）
  - こくご 12 / さんすう 20 / りか 30 / しゃかい 28 / おんがく・ずこう・たいいく・がいこくご 10
- 応用・現代社会の疑問・追加分 100
  - すうがく・じょうほう・ぎじゅつ 15 / ぶつり・かがく 15 / せいぶつ・いがく・からだ 15 /
    ちがく・うちゅう・かんきょう 15 / ちり・れきし・こくさい 15 /
    せいじ・ほうりつ・けいざい 15 / ことば・ぶんか・げいじゅつ 10

### 3.2 制約

- 同一プール内・プール間とも重複させない（`renderChips` が 5 問そろわなくなる）。
- 追加時は 8 文字インデントの `"…",` を 1 行ずつ並べる。カテゴリはコメントで区切る。
- サーバー側の変更は不要。追加だけならデプロイ後すぐ反映される。

---

## 4. API 仕様

すべて同一オリジン（`/ask/api/`）。認証なし。LAN 内のみ。

### 4.1 `GET /ask/api/usage`

当日の累計を返す。nginx で GET のみ許可。

```json
{
  "ok": true,
  "spend": 0.565702,
  "per_question": 0.008894,
  "remaining": 49,
  "daily_max": 1.0,
  "tokens": { "prompt": 0, "completion": 0, "total": 140985,
              "questions": 0, "cost": 0.0, "measured": 0 }
}
```

### 4.2 `POST /ask/api/ask`

リクエスト（`Content-Type: application/json`、本文 4,096 バイトまで）

```json
{ "question": "なぜ そらは あおいの？", "mode": "kid" }
```

- `question`: 2〜120 文字（超過分は切り捨て）。制御文字は空白に置換。
- `mode`: `kid` | `teen`。不正値は `kid`。

成功時（200）

```json
{
  "answer": "…（ふりがな付きの本文）",
  "verdict": "supported | partly | unsupported | unverified | unchecked | declined | blocked",
  "sources": ["mext.go.jp", "…"],
  "source_links": [{"host": "mext.go.jp", "url": "https://…", "title": "…"}],
  "related_questions": ["関連する質問1（ふりがな付き）", "質問2"],
  "notice": null,
  "cost": 0.008894,
  "tokens": { "prompt": 3906, "completion": 267, "total": 4173, "today": 140985 },
  "estimate": { "spend": 0.565702, "per_question": 0.008894,
                "remaining": 49, "daily_max": 1.0, "tokens": { "…": 0 } }
}
```

`verdict` の意味

| 値 | 意味 | 画面 |
| --- | --- | --- |
| `supported` | 資料で裏づけられた | そのまま表示 |
| `partly` | 一部だけ裏づけ | そのまま表示 |
| `unsupported` | 裏づけ不足 | `fixed_answer` があれば差し替え＋注意書き。無ければ「しらべられなかった」 |
| `unverified` | 検証できなかった | 注意書きのみ |
| `unchecked` | 検証処理が失敗 | 注意書きのみ |
| `declined` | 入口の分類で辞退 | 定型文（性的・自傷・犯罪手順・政治意見） |
| `blocked` | 最終安全チェックで遮断 | 定型文 |

エラー

| status | `error` | 画面の文言 |
| --- | --- | --- |
| 400 | `empty` / `bad-body` / `bad-json` | `しりたい ことを かいてね。` など |
| 429 | `rate` | `いま たくさん きいてくれて いるね。…` |
| 503 | `busy` / `budget` | `いま いそがしいみたい。…` / `きょうは たくさん おしゃべりしたから…` |
| 502 | `upstream` | `ごめんね。いま しらべられなかったよ。…` |
| 404 | `not-found` | — |

### 4.3 保護者・管理者用 API（`/ask/api/admin/*`）

- `GET /ask/api/admin/state`: 設定値・モデル候補（`catalog`）・使用量・直近の検索ログ（日時・質問・回答・消費トークン）を返す。パスワード設定時は `X-Admin-Token` ヘッダーが無ければ `{"locked": true, "has_password": true}` のみ返す。
- `POST /ask/api/admin/auth`: パスワードを照合し、メモリ内セッショントークン（有効 12 時間）と状態一式を返す。
- `POST /ask/api/admin/config`: プロバイダー（`provider`: `google` または `openrouter`）、APIキー（`google_api_key` または `openrouter_api_key`）、回答モデル（`answer_model`）、検証モデル（`verify_model`）、こども・中学生それぞれの最大文数（`kid_sentences` / `teen_sentences`）と最大文字数（`kid_chars` / `teen_chars`）を `config.json` に保存し即時反映する。
- `POST /ask/api/admin/password`: 管理者パスワード（4〜64 文字、空欄で解除）を PBKDF2-HMAC-SHA256（120,000 回反復＋16 バイト乱数ソルト）でハッシュ化して `config.json` に保存する。

### 4.4 `GET /ask/api/health`

LXC 内（127.0.0.1）専用。`{"ok": true, "spend": {…}}`。

### 4.4 制限

| 項目 | 値 | 実装 |
| --- | --- | --- |
| レート | 6 問 / 60 秒 / 送信元 IP | `ask_proxy.py` の `rate_ok` |
| 同時実行 | 2 | `MAX_CONCURRENT`（待ち 8 秒で 503） |
| 1 日の費用 | `ASK_DAILY_USD_MAX`（既定 1.00 USD） | 超過で 503 `budget` |
| 本文 | 4,096 バイト | `BODY_MAX` |
| nginx | 20 r/m、burst 10 | `limit_req_zone ask_api` |

送信元 IP は、転送元がループバックのときだけ `X-Real-IP` を信頼する
（nginx 経由の全リクエストが `127.0.0.1` 扱いになり、家中で 1 つの制限に
まとまってしまうのを防ぐ）。IPv4/IPv6 の文字種を検査してから採用する。

---

## 5. 回答パイプライン

1. **分類＋Web検索要否判定＋検索語生成**（`classify_and_rewrite_ex`、1 コール）
   `category`、`needs_search`（時事・統計等の検索要否）、`query` を同時に作る。
   `sexual` / `selfharm` / `crime_howto` / `politics_opinion` はここで確定し、以降の外部呼び出しをせず定型文を返す。
2. **常識回答＋知識ベリファイ（`needs_search == false` の場合、省トークン経路）**
   - `ask_with_knowledge`: Web 検索プラグインを使わず、確かな常識・教科書の知識だけで回答を生成する（モデル自身が検索必要と判断した場合は `NEED_SEARCH` を出力して 3. へ自動フォールバック）。
   - `verify_knowledge`: 検証モデル（`verify_model`）の知識で事実関係と読みがな（`wrong_readings`）を照合する。`unsupported`（知識だけでは裏づけ不可）と判定された場合は 3. の Web 検索経路へ自動フォールバックする。
3. **検索付き回答＋資料ベリファイ（`needs_search == true` またはフォールバック時）**
   - `ask_with_search`: `web` プラグイン＋`SITE_BIAS`（公的機関を優先する `site:` 指定）。公的機関の出典が `MIN_PUBLIC_SOURCES`（2）未満なら、指定なしで 1 回だけ再検索する。
   - `verify`: 回答と検索スニペットを突き合わせ、`supported` / `partly` / `unsupported` と `fixed_answer`、`wrong_readings`、`missing_readings`（ふりがな漏れ漢字）を返す。
4. **ふりがな保証と文数・字数の整形**（`sentences`、`find_unannotated_kanji`、`fill_missing_ruby`）
   - 回答モデルのプロンプトで「すべての漢字に『漢字(よみ)』の形式で読みがなを付けること（ふりがなのない漢字の放置を厳禁）」を最優先ルールとして強制。
   - ベリファイモデルが `missing_readings` を検出した場合は `fixed_answer` でふりがな付き修正文を提供し、採用する。
   - 難問や時事ニュースで生成モデル・ベリファイモデルがふりがなを落とした場合でも、`find_unannotated_kanji` で未注記漢字を検出し、`fill_missing_ruby` が文章内容を変えずにルビだけを自動補完する。
   - `wrong_readings`（誤った読み）は正規表現でその場で読みだけ外す。
5. **最終安全チェック**（`safety_check`、政治・犯罪系のみ）
   `unsafe` なら `blocked` にして定型文へ。
6. **記録**（`_finish` → `log_qa`）
   成功・失敗を問わず、`answer_type`（`knowledge` / `search`）を含めて 1 リクエスト 1 行を残す。

タイムアウト: 回答 45 秒、検証 25 秒。

---

## 6. 安全方針

| 種類 | 入口の判定 | 応答 |
| --- | --- | --- |
| 性的な内容 | `SEXUAL_RE` と分類 | 辞退（定型文） |
| 自傷・死にたい | `SELFHARM_RE` と分類 | 辞退。大人・相談窓口へ |
| 犯罪の手順 | `CRIME_HOWTO_RE` と分類 | 辞退。手順・回避のこつは書かない |
| 犯罪の理由・仕組み | `crime_fact` | 事実として回答（手順は書かない） |
| 政治の意見・評価 | `POLITICS_RE` と分類 | 辞退。制度・事実は中立に回答 |
| 政治の制度・事実 | `politics_fact` | 中立に回答（`POLITICS_ADDENDUM`） |

- 正規表現は「明らかなもの」を外部送信前に止めるための第一関門。判断の主軸は分類モデル。
- `safety_check` は回答本文の最終確認。政治・犯罪カテゴリでのみ呼ぶ。
- 辞退文はモード別（`DECLINE_MESSAGES` / `DECLINE_MESSAGES_TEEN`）。

---

## 7. プロバイダー・モデル・上限・環境変数

### 7.1 対応プロバイダー

1. **Google AI Studio（Gemini 無料枠あり）**:
   - エンドポイント: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
   - 回答モデル候補: `gemini-2.5-flash`（標準・おすすめ）、`gemini-2.5-flash-lite`（高速・軽量）、`gemini-2.0-flash`（安定）
   - 検証モデル候補: `gemini-2.5-flash-lite`（高速検証）、`gemini-2.5-flash`（標準検証）、`gemini-2.0-flash`
   - Web 検索: `tools: [{"googleSearch": {}}]`（Google Search Grounding）による公的サイト引用
   - 費用: **無料枠（1日 1,500 回まで費用 $0.00）**
2. **OpenRouter（多様なオープンモデル・従量課金）**:
   - エンドポイント: `https://openrouter.ai/api/v1/chat/completions`
   - モデル候補: `z-ai/glm-5.3-flash`, `google/gemini-2.5-flash`, `openai/gpt-6-luna`, `qwen/qwen3.5-flash-02-23`, `mistralai/ministral-8b-2512` 等
   - Web 検索: `plugins: [{"id": "web"}]`

### 7.2 環境変数

`/etc/draw-pad/ai/ai.env`（`root:draw-pad-ai` 640）またはローカル環境

| 変数 | 既定 | 用途 |
| --- | --- | --- |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | — | Google AI Studio API キー |
| `OPENROUTER_API_KEY` | — | OpenRouter API キー |
| `ASK_ANSWER_MODEL` | `z-ai/glm-5.3-flash` | OpenRouter 回答標準モデル |
| `ASK_ANSWER_FALLBACK` | `qwen/qwen3.5-flash-02-23` | 回答の代替 |
| `ASK_QUERY_MODEL` | `z-ai/glm-5.3-flash` | 分類＋検索語 |
| `ASK_VERIFY_MODEL` | `mistralai/ministral-8b-2512` | OpenRouter 検証標準モデル |
| `ASK_WEB_RESULTS` | `5` | 検索件数 |
| `ASK_DAILY_USD_MAX` | `1.00` | 1 日の費用上限（OpenRouter 利用時） |
| `ASK_PER_QUESTION_EST` | `0.0085` | 実測が無い日の 1 問単価 |
| `ASK_LOG_KEEP_DAYS` | `180` | 記録の保持日数 |
| `ASK_LISTEN_HOST` / `ASK_LISTEN_PORT` | `127.0.0.1` / `8787` | 待ち受け |
| `ASK_STATE_DIR` | `/var/lib/draw-pad-ai` または `./data` | 状態と記録 |

---

## 8. 記録と状態

`/var/lib/draw-pad-ai/`

| ファイル | 内容 |
| --- | --- |
| `qa/qa-YYYY-MM-DD.jsonl` | 1 リクエスト 1 行。180 日で自動削除。 |
| `spend.json` | 日付ごとの累計費用（USD） |
| `tokens.json` | 当日の `prompt` / `completion` / `total` / `questions` / `cost` / `measured` |

`qa-*.jsonl` のフィールド

```json
{"ts":"2026-11-12T12:36:00+09:00","ip":"192.168.0.20","mode":"kid",
 "category":"ok","q":"…","query":"…","a":"…","verdict":"supported",
 "notice":null,"sources":["mext.go.jp"],"cost":0.008894,"tokens":4173,
 "status":200,"ms":8612}
```

- 記録は応答を返す直前に行う（失敗リクエストも残る）。
- パーミッションは 700/600（`root:draw-pad-ai`）。バックアップ対象。

---

## 9. セキュリティ

- nginx: `allow 127.0.0.1; allow 192.168.0.0/24; deny all;`。
- メソッド制限: `/ask/api/usage` は GET のみ、`/ask/api/*` は POST のみ。
- CSP: `default-src 'none'`。`script-src` は **7 ページ分の SHA-256 ハッシュ**のみ。
  `connect-src 'self'`、`style-src 'unsafe-inline'`、`img-src` はページ別、
  `base-uri 'none'`、`frame-ancestors 'none'`、`form-action 'none'`。
- 秘密情報は HTML に置かない。API キーは systemd の `EnvironmentFile` 経由でプロセスだけが持つ。
- 回答本文から URL・ドメイン名・Markdown 装飾を除去してから表示する。
- 例外: `/mnt` などへの外部公開はしない。`0.0.0.0` では待ち受けない。

### CSP ハッシュの更新（スクリプトを変えたとき）

1. ページの `<script>…</script>` の**本文だけ**を取り、改行を LF に正規化する。
2. UTF-8 バイト列の SHA-256 を Base64 化し、`sha256-…` にする。
3. `nginx-draw-pad.conf` の該当ハッシュを差し替える（7 件のうち 1 件）。
4. 配置 → `nginx -t` → `systemctl reload nginx` → 実際に動くか確認。

---

## 10. 非機能

| 項目 | 実測・目標 |
| --- | --- |
| 応答時間 | 5〜20 秒（検索＋回答＋検証の合計）。中央値 8 秒前後 |
| 1 問のトークン | 4,000〜9,000 |
| 1 問の費用 | $0.008〜0.009 |
| 1 日の上限 | $1.00（約 110 問） |
| 同時利用 | 2 リクエストまで |
| メモリ | LXC 192 MB。systemd の名前空間系サンドボックスは使わない（226/NAMESPACE） |

---

## 11. 変更手順（要約）

1. `E:\AI\draw-pad` のファイルを編集する。
2. スクリプトを変えたら CSP ハッシュを再計算し、`ask-server/nginx-draw-pad.conf` を更新する。
3. `scp` で proxmox へ送り、`pct push 101` で LXC へ配置する。
4. 旧版を `*.previous.*` に控えてから上書きする。
5. `nginx -t` → `systemctl reload nginx`。
6. 検証: 全 8 ルート 200、配信 HTML とローカルのバイト一致、CSP 7 ハッシュ、
   ヘッドレス Chrome の DOM（チップ 5 件・使用量バー・コンソールエラーなし）、
   実 API 1 問（`verdict` と出典）。

---

## 12. 既知の制約

- HTTP のため音声入力（`getUserMedia`）は使えない。HTTPS 化とローカル CA の信頼が前提。
- 読み上げは端末の音声に依存する。iOS Safari は自動再生が制限される。
- 回答は生成モデル由来のため、`supported` でも表現の揺れがある。
  事実の最終確認は出典リンクと大人の目で行う。
- 質問プールはブラウザー内の静的配列。増やすとページサイズが増える（現在 約 87 KB）。
