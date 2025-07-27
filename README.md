# SKOLAPI - 四季報オンラインスクレイパー

このプロジェクトは、Playwright を使用して四季報オンラインから特定の証券コードの情報を取得するPythonスクリプトです。ログイン情報のキャッシュ機能も備わっています。

## 📋 機能概要

- **単一証券コード取得**: `shikiho_scraper.py` - 指定された証券コードの詳細情報を取得
- **非同期一括取得**: `shikiho_async_scraper.py` - 複数証券コードを非同期で効率的に処理
- **同期一括取得**: `shikiho_batch_scraper.py` - 複数証券コードを順次処理
- **ログイン状態キャッシュ**: セッション情報を保存し、再ログインを自動化
- **豊富な出力形式**: コンソール表示、JSONファイル出力に対応

## 🚀 はじめに

このプロジェクトをローカル環境でセットアップし、実行するための手順を説明します。

### 前提条件

*   Python 3.8 以上がインストールされていること
*   Git がインストールされていること

### 🛠️ セットアップ手順

macOS / Linux の場合、以下の1行コマンドで基本的なセットアップを完了できます。

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && playwright install
```

以下の手順に従って、プロジェクトをセットアップしてください。
1.  **`.env` ファイルを設定する**

    四季報オンラインにログインするためのIDとパスワードを設定する必要があります。プロジェクトのルートディレクトリに `.env` という名前のファイルを作成し、以下の形式であなたのログイン情報を記述してください。

    ```
    SHIKIHO_ID=あなたの四季報オンラインID
    SHIKIHO_PASSWORD=あなたの四季報オンラインパスワード
    ```

    > **重要**: `.env` ファイルはGitの管理対象外 (`.gitignore` に含まれています) なので、誤って公開リポジトリにアップロードされる心配はありません。

## 🏃 スクリプトの実行

### 1. 単一証券コードの詳細情報取得

指定された証券コードの詳細情報（社名、四季報記事、最新情報、時系列データ）を取得します。

```bash
python shikiho_scraper.py [証券コード]
```

例: 証券コード `2914` の情報を取得する場合

```bash
python shikiho_scraper.py 2914
```

### 2. 非同期一括処理（推奨）

複数の証券コードを非同期で効率的に処理します。同時実行数は3に制限されています。

```bash
python shikiho_async_scraper.py [証券コードリストファイル]
```

例: `stock_codes.json` ファイルに記載された証券コードを処理する場合

```bash
python shikiho_async_scraper.py stock_codes.json
```

### 3. 同期一括処理

複数の証券コードを順次処理します。API呼び出し間の待機時間を設定できます。

```bash
python shikiho_batch_scraper.py [証券コードリストファイル] [オプション]
```

例: 1秒間隔で処理し、結果を `results.json` に保存する場合

```bash
python shikiho_batch_scraper.py stock_codes.json --output results.json --delay 1.0
```

## 📁 ファイル形式

### 証券コードリストファイル

JSON形式またはCSV形式で証券コードリストを指定できます。

**JSON形式の例:**
```json
{
  "stock_codes": ["2914", "7203", "6758"]
}
```

**CSV形式の例:**
```csv
stock_code
2914
7203
6758
```

### 出力ファイル

- `shikiho_articles_async.json`: 非同期処理の結果
- `shikiho_articles.json`: 同期処理の結果
- `past.json`: 過去の処理結果

## 🔧 オプション

### shikiho_async_scraper.py
- `--output`: 出力ファイル名を指定（デフォルト: `shikiho_articles_async.json`）

### shikiho_batch_scraper.py
- `--output`, `-o`: 出力ファイル名を指定（デフォルト: `shikiho_articles.json`）
- `--delay`, `-d`: API呼び出し間の待機時間を秒単位で指定（デフォルト: 1.0秒）

## 🔐 ログイン状態の管理

初回実行時にはログイン処理が行われ、そのセッション情報が `playwright_user_data/state.json` に保存されます。2回目以降の実行では、このキャッシュされたセッションが利用され、ログインの手間が省かれます。キャッシュが無効になった場合は、自動的に再ログインが行われます。

## 📊 取得データ

各スクリプトで取得されるデータは以下の通りです：

### shikiho_scraper.py
- 社名
- 四季報記事
- 最新情報（shimen_results）
- 時系列データ（series）

### shikiho_async_scraper.py / shikiho_batch_scraper.py
- 証券コード
- 社名
- 四季報記事

## 🧹 クリーンアップ

仮想環境を終了するには、以下のコマンドを実行します。

```bash
deactivate
```

プロジェクトディレクトリを削除することで、すべてのファイルと仮想環境を削除できます。

## 📝 注意事項

- 四季報オンラインの利用規約を遵守してください
- 過度なアクセスは避け、適切な間隔を設けてください
- 取得したデータの取り扱いには十分注意してください
- ログイン情報は安全に管理してください

## 🤝 貢献

バグ報告や機能要望は、GitHubのIssuesページでお知らせください。

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。
