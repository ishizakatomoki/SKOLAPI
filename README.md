# SKOLAPI - 四季報オンラインスクレイパー

このプロジェクトは、Playwright を使用して四季報オンラインから特定の証券コードの情報を取得するPythonスクリプトです。ログイン情報のキャッシュ機能も備わっています。

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

1.  **リポジトリをクローンする**

    まず、このリポジトリをあなたのローカルマシンにクローンします。

    ```bash
    git clone https://github.com/your-username/SKOLAPI.git
    cd SKOLAPI
    ```

    > **注意**: `https://github.com/your-username/SKOLAPI.git` の部分は、このリポジトリの実際のURLに置き換えてください。

2.  **仮想環境を作成し、アクティベートする**

    プロジェクトの依存関係を管理するために、仮想環境を作成することを強く推奨します。

    ```bash
    python3 -m venv .venv
    ```

    仮想環境をアクティベートします。

    *   macOS / Linux:
        ```bash
        source .venv/bin/activate
        ```
    *   Windows:
        ```bash
        .venv\Scripts\activate
        ```

3.  **必要なライブラリをインストールする**

    仮想環境がアクティベートされた状態で、`requirements.txt` に記載されているすべての依存関係をインストールします。

    ```bash
    pip install -r requirements.txt
    ```

    Playwright のブラウザドライバもインストールする必要があります。

    ```bash
    playwright install
    ```

4.  **`.env` ファイルを設定する**

    四季報オンラインにログインするためのIDとパスワードを設定する必要があります。プロジェクトのルートディレクトリに `.env` という名前のファイルを作成し、以下の形式であなたのログイン情報を記述してください。

    ```
    SHIKIHO_ID=あなたの四季報オンラインID
    SHIKIHO_PASSWORD=あなたの四季報オンラインパスワード
    ```

    > **重要**: `.env` ファイルはGitの管理対象外 (`.gitignore` に含まれています) なので、誤って公開リポジトリにアップロードされる心配はありません。

### 🏃 スクリプトの実行

すべてのセットアップが完了したら、スクリプトを実行できます。

```bash
python shikiho_scraper.py [証券コード]
```

例: 証券コード `2914` の情報を取得する場合

```bash
python shikiho_scraper.py 2914
```

初回実行時にはログイン処理が行われ、そのセッション情報が `playwright_user_data/state.json` に保存されます。2回目以降の実行では、このキャッシュされたセッションが利用され、ログインの手間が省かれます。キャッシュが無効になった場合は、自動的に再ログインが行われます。

### 🧹 クリーンアップ

仮想環境を終了するには、以下のコマンドを実行します。

```bash
deactivate
```

プロジェクトディレクトリを削除することで、すべてのファイルと仮想環境を削除できます。
