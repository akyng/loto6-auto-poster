# Loto6 Oracle X (Twitter) 自動投稿ボット

このバックエンドシステムは、最新のロト6当選番号およびキャリーオーバー発生時の速報を自動スクレイピングし、X（旧Twitter）アカウント `@loto6oracl_AI` に自動でツイート投稿を行うPythonスクリプトです。

---

## 📂 ディレクトリ構成

- `config.py`: `.env` から環境変数を読み込み・検証するモジュール
- `scraper.py`: 楽天・みずほ銀行のロト6当選データを収集するスクレイピングサービス
- `bot.py`: 自動投稿のコア処理（新着チェック、ツイート生成、キャッシュ制御）
- `test_connection.py`: X APIとの接続状態を確認する自己診断診断ツール
- `cache.json`: 重複投稿防止用のキャッシュファイル（最後に投稿した回号を自動記録）
- `.env`: APIキーやアクセストークンなどの認証情報（すでに設定済み）

---

## 🚀 セットアップ手順

### 1. 依存ライブラリのインストール
Macのターミナルを開き、`backend` ディレクトリへ移動して以下のコマンドを実行してください。

```bash
cd "/Users/user/Desktop/Loto6 Oracle/backend"
pip3 install -r requirements.txt
```

### 2. X API 接続テストの実行
APIキーが正常に機能しているかテストします。

```bash
python3 test_connection.py
```

> [!CAUTION]
> **❌ Tweepy API Error: 402 Payment Required が発生した場合**
> 
> Xの現在のAPI利用規約により、Free（無料）プランのアカウントであっても、**X Developer Console (`console.x.com`) で最低限のクレジット（デポジット金）がチャージされていない場合**にこのエラーが発生します。
> 
> **【解決方法】**
> 1. **[X Developer Portal](https://console.x.com/)** にログインします。
> 2. メニューから **「Billing」** または **「Credits」** のセクションに進みます。
> 3. アカウントに最低額のクレジット（通常5ドル〜）をチャージします。
> 
> チャージ完了後、`test_connection.py` を再実行すると正常にテスト投稿ができるようになります。

---

## ☁️ 🛠️ GitHub Actions での 24時間完全自動運転（推奨・完全無料）

GitHub Actions を利用することで、ご自身のPCの電源を切っていても、**24時間完全自動で結果発表（毎週月曜・木曜夜）を検知してXに即時自動ツイート**させることができます。
また、二重投稿防止用のキャッシュファイル（`cache.json`）も、GitHub Actionsが自動的にコミット＆プッシュして更新を同期してくれるため、ストレージ管理も不要です。

### 1. リポジトリの作成とアップロード
1. お手持ちの GitHub アカウントで、新しく **Private（非公開）** または **Public（公開）** のリポジトリを作成します。
   > [!WARNING]
   > `.env` にはAPIキー等の機密情報が含まれるため、**Private（非公開）リポジトリ**として作成することを強く推奨します。
2. 作成したリポジトリに、この `backend` フォルダの中身すべてをアップロード（プッシュ）します。
   *（`.github/workflows/loto6_bot.yml` が自動的に実行環境のトリガーとなります）*

### 2. GitHub Secrets (環境変数) の登録
APIキーなどの機密情報を安全に保持するため、GitHubのリポジトリ設定に登録します。
1. GitHub上のリポジトリ画面で **「Settings」** ⚙️ タブを開きます。
2. 左メニューから **「Secrets and variables」** ➡️ **「Actions」** を選択します。
3. **「New repository secret」** ボタンを押し、以下の5つの変数を1つずつ登録します。

| Secret の名前 | 設定する値（`.env` に書いてある値） |
| :--- | :--- |
| `X_API_KEY` | `AQIirC5omWbZfg...` (Consumer Key) |
| `X_API_KEY_SECRET` | `0Iq4ViG0SbwNy...` (Consumer Secret) |
| `X_ACCESS_TOKEN` | `205591664373...` (Access Token) |
| `X_ACCESS_TOKEN_SECRET` | `udnuQ8vLVphU8...` (Access Token Secret) |
| `X_APP_URL` | `https://onelink.to/76cms6` (スマートリンクURL) |

### 3. 書き込み権限（Workflow Permissions）の有効化
ボットが自動投稿した後に、二重投稿防止用の `cache.json` の更新履歴をGitHubに自動保存（Git Push）させるための設定です。
1. **「Settings」** ➡️ **「Actions」** ➡️ **「General」** を開きます。
2. 画面の一番下までスクロールし、**「Workflow permissions」** セクションを見つけます。
3. **「Read and write permissions」**（読み取りおよび書き込み権限）にチェックを入れます。
4. **「Save」** ボタンを押して保存します。

これで設定はすべて完了です！以降、毎時0分にGitHubのサーバーが起動し、自動チェックとツイート投稿を勝手に行ってくれます。
*※リポジトリの「Actions」タブから、いつでも実行状況やログを確認したり、「Run workflow」ボタンから手動で即時実行させることも可能です。*

---

## 💻 🛠️ 自動運転のスケジュール設定 (Mac Cron Job - ローカル実行)

ご自身のMacが起動しているときだけ動かすローカルな自動運転設定です。

### 1. タスクの登録手順
ターミナルで以下のコマンドを入力してcron編集画面を開きます：

```bash
crontab -e
```

### 2. 設定の書き込み
以下の設定を貼り付けて保存します（毎時0分に自動チェックを行います）：

```text
0 * * * * cd "/Users/user/Desktop/Loto6 Oracle/backend" && python3 bot.py >> bot.log 2>&1
```

*※実行ログは同じフォルダ内の `bot.log` に自動的に蓄積されます。*

---

## 📝 自動生成されるツイートサンプル

### ① 当選番号速報（新着検知時）
```text
【第2102回 ロト6 当選番号速報】
📅 抽せん日: 2026/05/14

🎨 本数字: 18, 21, 25, 28, 30, 43
💎 ボーナス数字: (8)

次回AI予想はアプリ「ロト6 AI予想」にお任せください！🔮✨
#ロト6 #Loto6 #当選番号速報
```

### ② キャリーオーバー発生情報（キャリーオーバーが存在する場合）
```text
【ロト6 キャリーオーバー発生中！🔥】
第2102回 抽せん結果、次回へのキャリーオーバーが発生しています！

現在のキャリーオーバー額：
✨ 23,538,243 円 ✨

一攫千金のビッグチャンス！🔮
最新のロト6 AI予想アプリをダウンロードして、次回の神予想を今すぐチェック！🚀
#ロト6 #キャリーオーバー #Loto6
```

---

## 📈 当選予想実績の自動集計 (aggregate_stats.py)

このスクリプトは、アプリユーザーが生成したAI予想実績（`predictions_raw` コレクション）を、Webからスクレイピングした最新の当選結果と突合・集集計し、アプリ表示用の `global_stats` コレクションを更新するバッチ処理スクリプトです。
集計完了した生の予想データはFirestoreから自動削除されるため、**データベース容量をほぼゼロに維持し、Firestoreの無料枠のみで永続運用可能**な設計になっています。

### 🚀 セットアップ手順

#### 1. サービスアカウントキーの配置
1. **[Firebase Console](https://console.firebase.google.com/)** にアクセスし、プロジェクトを開きます。
2. 設定アイコン（歯車）⚙️ ➡️ **「プロジェクトの設定」** ➡️ **「サービス アカウント」** タブを開きます。
3. **「新しい秘密鍵の生成」** ボタンを押し、JSONキーファイルをダウンロードします。
4. ダウンロードしたファイルを `service_account.json` にリネームし、`backend` フォルダの直下に配置します。
   *(※このJSONファイルにはデータベースのフルアクセス権限が含まれるため、Git等で公開リポジトリにアップロードしないようご注意ください。)*

#### 2. 手動での集計テスト実行
ターミナルで `backend` ディレクトリへ移動し、以下のコマンドを実行します：

```bash
python3 aggregate_stats.py
```

実行に成功すると、最新の当選結果との突合が行われ、`global_stats` ドキュメントが自動更新/生成されます。

### ☁️ 🛠️ GitHub Actions での定期自動集計設定
Xボットの自動運転と同様に、GitHub Actions で定期実行（例：毎日深夜）させる場合は、以下のように設定します。

1. **GitHub Secretsへの登録**
   `service_account.json` の中身（テキスト全体）を、GitHub Secretsに `FIREBASE_SERVICE_ACCOUNT_JSON` という名前で登録します。
2. **GitHub Actions ワークフローの追加**
   `.github/workflows/aggregate_stats.yml` などを作成し、毎日深夜に自動実行するように設定します。（以下は設定例）

```yaml
name: Aggregate Stats
on:
  schedule:
    - cron: '30 18 * * *' # 日本時間 毎日午前3:30 (UTC 18:30)
  workflow_dispatch: # 手動実行用

jobs:
  run-aggregator:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
      - name: Create credentials file
        run: |
          echo '${{ secrets.FIREBASE_SERVICE_ACCOUNT_JSON }}' > backend/service_account.json
      - name: Run Aggregator
        run: |
          python backend/aggregate_stats.py
```
