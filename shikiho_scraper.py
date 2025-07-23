import os
import sys
import json
import argparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from dotenv import load_dotenv

# --- 定数定義 ---
LOGIN_URL = "https://shikiho.toyokeizai.net/"
SSO_CHECK_URL = "https://api-shikiho.toyokeizai.net/sso/v1/sso/check"
API_BASE_URL = "https://api-shikiho.toyokeizai.net/stocks/v1/stocks"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
STORAGE_STATE_PATH = "playwright_user_data/state.json" # ログイン状態を保存するファイル 

# --- 関数定義 ---

def fetch_shikiho_data(page, stock_code):
    """
    Playwrightのページオブジェクトを使用して、四季報のAPIからデータを取得する。
    Cookieやヘッダーは現在のブラウザコンテキストから自動的に引き継がれる。
    """
    final_result = {}

    try:
        # --- 1. SSO認証チェック ---
        print(f"\n認証チェック(SSO)を実行します: {SSO_CHECK_URL}")
        sso_response = page.request.get(SSO_CHECK_URL, headers={
            "Referer": "https://shikiho.toyokeizai.net/"
        })
        if not sso_response.ok:
            raise PlaywrightError(f"SSOチェックに失敗しました: {sso_response.status} {sso_response.status_text}")
        print("認証チェック(SSO)に成功しました。")
        # print(json.dumps(await sso_response.json(), indent=2, ensure_ascii=False)) # デバッグ用

        # --- 2. ヘッダー情報APIの取得 ---
        headers_url = f"{API_BASE_URL}/{stock_code}/headers"
        print(f"\nAPIにリクエストを送信します: {headers_url}")
        headers_response = page.request.get(headers_url, headers={
            "Referer": f"https://shikiho.toyokeizai.net/stocks/{stock_code}"
        })
        if not headers_response.ok:
            raise PlaywrightError(f"/headers APIの取得に失敗: {headers_response.status} {headers_response.status_text}")
        
        header_data = headers_response.json()
        if "company_name_j" in header_data:
            final_result["社名"] = header_data["company_name_j"]
        if "shimen_articles" in header_data:
            final_result["四季報記事"] = header_data["shimen_articles"]
        print("/headers APIの取得に成功しました。")

        # --- 3. 最新情報APIの取得 ---
        latest_url = f"{API_BASE_URL}/{stock_code}/latest"
        print(f"\nAPIにリクエストを送信します: {latest_url}")
        latest_response = page.request.get(latest_url, headers={
            "Referer": f"https://shikiho.toyokeizai.net/stocks/{stock_code}"
        })
        if not latest_response.ok:
            raise PlaywrightError(f"/latest APIの取得に失敗: {latest_response.status} {latest_response.status_text}")

        latest_data = latest_response.json()
        if "shimen_results" in latest_data:
            final_result["shimen_results"] = latest_data["shimen_results"]
        print("/latest APIの取得に成功しました。")

        return final_result

    except PlaywrightError as e:
        print(f"\nエラー: APIリクエスト中にエラーが発生しました。\n{e}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description="四季報オンラインから指定した証券コードの情報を取得します。")
    parser.add_argument("stock_code", type=str, help="証券コード (例: 7256)")
    args = parser.parse_args()

    user_id = os.getenv("SHIKIHO_ID")
    password = os.getenv("SHIKIHO_PASSWORD")

    if not user_id or not password:
        print("エラー: 環境変数 SHIKIHO_ID と SHIKIHO_PASSWORD を設定してください。", file=sys.stderr)
        print("または、スクリプトと同じディレクトリに .env ファイルを作成し、SHIKIHO_ID と SHIKIHO_PASSWORD を記述してください。", file=sys.stderr)
        sys.exit(1)

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            
            # ログイン状態のキャッシュを試みる
            perform_login = False
            if os.path.exists(STORAGE_STATE_PATH):
                print(f"既存のログイン状態をロードします: {STORAGE_STATE_PATH}")
                context = browser.new_context(user_agent=USER_AGENT, storage_state=STORAGE_STATE_PATH)
                page = context.new_page()
                
                # キャッシュされたセッションが有効か確認
                try:
                    print("キャッシュされたセッションの有効性を確認します...")
                    page.goto(SSO_CHECK_URL, wait_until="domcontentloaded", timeout=10000)
                    # Check if the current URL is still the login page or contains "login"
                    if page.url == LOGIN_URL or "login" in page.url:
                        print("キャッシュされたセッションは無効です。再ログインします。")
                        perform_login = True
                    else:
                        print("キャッシュされたセッションは有効です。")
                        perform_login = False
                except PlaywrightTimeoutError:
                    print("セッション有効性確認がタイムアウトしました。再ログインします。")
                    perform_login = True
                except PlaywrightError as e:
                    print(f"セッション有効性確認中にエラーが発生しました: {e}。再ログインします。")
                    perform_login = True
            else:
                print("既存のログイン状態が見つかりません。新規ログインします。")
                context = browser.new_context(user_agent=USER_AGENT)
                page = context.new_page()
                perform_login = True

            if perform_login:
                print("Playwrightを起動してログインを開始します...")
                page.goto(LOGIN_URL, wait_until="domcontentloaded")
                page.get_by_role("button", name="ログイン").first.click()
                page.get_by_role("button", name="ログイン").nth(1).click()

                iframe_locator = page.frame_locator('iframe[name^="piano-id-"]')
                iframe_locator.get_by_role("textbox", name="email").fill(user_id)
                iframe_locator.get_by_role("textbox", name="パスワード").fill(password)
                iframe_locator.get_by_role("button", name="ログイン").click()

                print("ログイン処理後、ページのネットワークが安定するのを待機します...")
                page.wait_for_load_state("networkidle", timeout=20000)
                
                # ログイン成功後、状態を保存
                os.makedirs(os.path.dirname(STORAGE_STATE_PATH), exist_ok=True)
                context.storage_state(path=STORAGE_STATE_PATH)
                print(f"新しいログイン状態を保存しました: {STORAGE_STATE_PATH}")
            
            print("ログインに成功し、ページが安定しました。")

            # --- データ取得処理 ---
            shikiho_data = fetch_shikiho_data(page, args.stock_code)

            browser.close()

            # --- 最終結果の表示 ---
            if shikiho_data:
                print("\n--- 最終取得データ ---")
                if "社名" in shikiho_data:
                    print(f"社名: {shikiho_data['社名']}")
                    del shikiho_data["社名"]
                if "四季報記事" in shikiho_data:
                    print("四季報記事:")
                    for article in shikiho_data['四季報記事']:
                        print(article)
                    del shikiho_data["四季報記事"]

                if "shimen_results" in shikiho_data:
                    from tabulate import tabulate
                    print("\n--- 四季報データ (shimen_results) ---")
                    print(tabulate(shikiho_data["shimen_results"], headers="firstrow", tablefmt="grid"))
                    del shikiho_data["shimen_results"]
                print(json.dumps(shikiho_data, indent=2, ensure_ascii=False))
            else:
                print("\nエラー: データの取得に失敗しました。", file=sys.stderr)
                sys.exit(1)

        except TimeoutError:
            print("\nエラー: 処理がタイムアウトしました。ログインプロセスやサイトの構造を確認してください。", file=sys.stderr)
            sys.exit(1)
        except PlaywrightError as e:
            print(f"\nエラー: Playwrightの操作中にエラーが発生しました。\n{e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    load_dotenv() # .envファイルをロード
    main()