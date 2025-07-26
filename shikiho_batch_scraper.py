import os
import sys
import json
import argparse
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# --- 定数定義 ---
LOGIN_URL = "https://shikiho.toyokeizai.net/"
SSO_CHECK_URL = "https://api-shikiho.toyokeizai.net/sso/v1/sso/check"
API_BASE_URL = "https://api-shikiho.toyokeizai.net/stocks/v1/stocks"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
STORAGE_STATE_PATH = "playwright_user_data/state.json"

def load_stock_codes(file_path):
    """JSONまたはCSVファイルから証券コードリストを読み込む"""
    if file_path.endswith('.json'):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('stock_codes', [])
    elif file_path.endswith('.csv'):
        import csv
        stock_codes = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stock_codes.append(row['stock_code'])
        return stock_codes
    else:
        raise ValueError("サポートされているファイル形式は JSON または CSV です")

def fetch_shikiho_articles(page, stock_code):
    """指定された証券コードの四季報記事のみを取得"""
    try:
        # SSO認証チェック
        sso_response = page.request.get(SSO_CHECK_URL, headers={
            "Referer": "https://shikiho.toyokeizai.net/"
        })
        if not sso_response.ok:
            raise PlaywrightError(f"SSOチェックに失敗しました: {sso_response.status}")

        # ヘッダー情報APIから記事を取得
        headers_url = f"{API_BASE_URL}/{stock_code}/headers"
        headers_response = page.request.get(headers_url, headers={
            "Referer": f"https://shikiho.toyokeizai.net/stocks/{stock_code}"
        })
        if not headers_response.ok:
            raise PlaywrightError(f"/headers APIの取得に失敗: {headers_response.status}")

        header_data = headers_response.json()
        result = {
            "証券コード": stock_code,
            "社名": header_data.get("company_name_j", ""),
            "四季報記事": header_data.get("shimen_articles", [])
        }
        
        return result

    except PlaywrightError as e:
        return {
            "証券コード": stock_code,
            "社名": "",
            "四季報記事": [],
            "エラー": str(e)
        }

def perform_login(page, user_id, password):
    """ログイン処理を実行"""
    print("Playwrightを起動してログインを開始します...")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    page.get_by_role("button", name="ログイン").first.click()
    page.get_by_role("button", name="ログイン").nth(1).click()

    iframe_locator = page.frame_locator('iframe[name^="piano-id-"]')
    iframe_locator.get_by_role("textbox", name="email").fill(user_id)
    iframe_locator.get_by_role("textbox", name="パスワード").fill(password)
    iframe_locator.get_by_role("button", name="ログイン").click()

    print("ログイン処理後、1秒待機して処理を継続します...")
    page.wait_for_timeout(1000)

def main():
    parser = argparse.ArgumentParser(description="複数社の四季報記事を一括取得します。")
    parser.add_argument("file_path", type=str, help="証券コードリストファイル (JSON または CSV)")
    parser.add_argument("--output", "-o", type=str, default="shikiho_articles.json", help="出力ファイル名")
    parser.add_argument("--delay", "-d", type=float, default=1.0, help="API呼び出し間の待機時間（秒）")
    args = parser.parse_args()

    user_id = os.getenv("SHIKIHO_ID")
    password = os.getenv("SHIKIHO_PASSWORD")

    if not user_id or not password:
        print("エラー: 環境変数 SHIKIHO_ID と SHIKIHO_PASSWORD を設定してください。", file=sys.stderr)
        sys.exit(1)

    # 証券コードリストを読み込み
    try:
        stock_codes = load_stock_codes(args.file_path)
        print(f"証券コード {len(stock_codes)} 社を読み込みました")
    except Exception as e:
        print(f"エラー: ファイルの読み込みに失敗しました: {e}", file=sys.stderr)
        sys.exit(1)

    console = Console()
    results = []
    errors = []

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            
            # ログイン状態の管理
            perform_login_flag = False
            if os.path.exists(STORAGE_STATE_PATH):
                print(f"既存のログイン状態をロードします: {STORAGE_STATE_PATH}")
                context = browser.new_context(user_agent=USER_AGENT, storage_state=STORAGE_STATE_PATH)
                page = context.new_page()
                
                try:
                    page.goto(SSO_CHECK_URL, wait_until="domcontentloaded", timeout=10000)
                    if page.url == LOGIN_URL or "login" in page.url:
                        print("キャッシュされたセッションは無効です。再ログインします。")
                        perform_login_flag = True
                    else:
                        print("キャッシュされたセッションは有効です。")
                        perform_login_flag = False
                except PlaywrightTimeoutError:
                    print("セッション有効性確認がタイムアウトしました。再ログインします。")
                    perform_login_flag = True
                except PlaywrightError as e:
                    print(f"セッション有効性確認中にエラーが発生しました: {e}。再ログインします。")
                    perform_login_flag = True
            else:
                print("既存のログイン状態が見つかりません。新規ログインします。")
                context = browser.new_context(user_agent=USER_AGENT)
                page = context.new_page()
                perform_login_flag = True

            if perform_login_flag:
                perform_login(page, user_id, password)
                os.makedirs(os.path.dirname(STORAGE_STATE_PATH), exist_ok=True)
                context.storage_state(path=STORAGE_STATE_PATH)
                print(f"新しいログイン状態を保存しました: {STORAGE_STATE_PATH}")

            print("ログインに成功し、データ取得を開始します。")

            # プログレスバーで進捗表示
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task(f"[cyan]四季報記事を取得中...", total=len(stock_codes))

                for i, stock_code in enumerate(stock_codes):
                    progress.update(task, description=f"[cyan]処理中: {stock_code} ({i+1}/{len(stock_codes)})")
                    
                    try:
                        result = fetch_shikiho_articles(page, stock_code)
                        results.append(result)
                        
                        if "エラー" in result:
                            errors.append(f"{stock_code}: {result['エラー']}")
                            console.print(f"[red]エラー: {stock_code} - {result['エラー']}")
                        else:
                            article_count = len(result.get("四季報記事", []))
                            console.print(f"[green]成功: {stock_code} ({result.get('社名', 'N/A')}) - 記事数: {article_count}")
                        
                        # API呼び出し間の待機
                        if i < len(stock_codes) - 1:  # 最後の会社以外は待機
                            time.sleep(args.delay)
                            
                    except Exception as e:
                        error_result = {
                            "証券コード": stock_code,
                            "社名": "",
                            "四季報記事": [],
                            "エラー": str(e)
                        }
                        results.append(error_result)
                        errors.append(f"{stock_code}: {e}")
                        console.print(f"[red]エラー: {stock_code} - {e}")
                    
                    progress.advance(task)

            browser.close()

            # 結果を保存
            output_data = {
                "取得日時": datetime.now().isoformat(),
                "総社数": len(stock_codes),
                "成功社数": len([r for r in results if "エラー" not in r]),
                "エラー社数": len(errors),
                "エラー詳細": errors,
                "データ": results
            }

            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            console.print(f"\n[bold green]処理完了！[/bold green]")
            console.print(f"結果を保存しました: {args.output}")
            console.print(f"総社数: {len(stock_codes)}")
            console.print(f"成功: {len([r for r in results if 'エラー' not in r])}社")
            console.print(f"エラー: {len(errors)}社")
            
            if errors:
                console.print(f"\n[bold red]エラーが発生した会社:[/bold red]")
                for error in errors:
                    console.print(f"  {error}")

        except Exception as e:
            console.print(f"[bold red]エラー: {e}[/bold red]")
            sys.exit(1)

if __name__ == "__main__":
    load_dotenv()
    main() 