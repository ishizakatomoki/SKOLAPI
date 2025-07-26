import os
import sys
import json
import argparse
import asyncio
import time
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# --- 定数定義 ---
LOGIN_URL = "https://shikiho.toyokeizai.net/"
SSO_CHECK_URL = "https://api-shikiho.toyokeizai.net/sso/v1/sso/check"
API_BASE_URL = "https://api-shikiho.toyokeizai.net/stocks/v1/stocks"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
STORAGE_STATE_PATH = "playwright_user_data/state.json"
CONCURRENT_LIMIT = 3  # 同時実行数

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

async def fetch_shikiho_articles(page, stock_code):
    """指定された証券コードの四季報記事のみを取得（非同期版）"""
    try:
        # SSO認証チェック
        sso_response = await page.request.get(SSO_CHECK_URL, headers={
            "Referer": "https://shikiho.toyokeizai.net/"
        })
        if not sso_response.ok:
            raise PlaywrightError(f"SSOチェックに失敗しました: {sso_response.status}")

        # ヘッダー情報APIから記事を取得
        headers_url = f"{API_BASE_URL}/{stock_code}/headers"
        headers_response = await page.request.get(headers_url, headers={
            "Referer": f"https://shikiho.toyokeizai.net/stocks/{stock_code}"
        })
        if not headers_response.ok:
            raise PlaywrightError(f"/headers APIの取得に失敗: {headers_response.status}")

        header_data = await headers_response.json()
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

async def perform_login(page, user_id, password):
    """ログイン処理を実行（非同期版）"""
    print("Playwrightを起動してログインを開始します...")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded")
    await page.get_by_role("button", name="ログイン").first.click()
    await page.get_by_role("button", name="ログイン").nth(1).click()

    iframe_locator = page.frame_locator('iframe[name^="piano-id-"]')
    await iframe_locator.get_by_role("textbox", name="email").fill(user_id)
    await iframe_locator.get_by_role("textbox", name="パスワード").fill(password)
    await iframe_locator.get_by_role("button", name="ログイン").click()

    print("ログイン処理後、1秒待機して処理を継続します...")
    await page.wait_for_timeout(1000)

async def process_stock_code(semaphore, page, stock_code, progress, task, console):
    """個別の証券コードを処理（セマフォ制御付き）"""
    async with semaphore:
        try:
            progress.update(task, description=f"[cyan]処理中: {stock_code}")
            
            result = await fetch_shikiho_articles(page, stock_code)
            
            if "エラー" in result:
                console.print(f"[red]エラー: {stock_code} - {result['エラー']}")
            else:
                article_count = len(result.get("四季報記事", []))
                console.print(f"[green]成功: {stock_code} ({result.get('社名', 'N/A')}) - 記事数: {article_count}")
            
            # 処理間の短い待機
            await asyncio.sleep(0.5)
            
            return result
            
        except Exception as e:
            error_result = {
                "証券コード": stock_code,
                "社名": "",
                "四季報記事": [],
                "エラー": str(e)
            }
            console.print(f"[red]エラー: {stock_code} - {e}")
            return error_result
        finally:
            progress.advance(task)

async def main_async():
    parser = argparse.ArgumentParser(description="複数社の四季報記事を非同期で一括取得します。")
    parser.add_argument("file_path", type=str, help="証券コードリストファイル (JSON または CSV)")
    parser.add_argument("--output", "-o", type=str, default="shikiho_articles_async.json", help="出力ファイル名")
    parser.add_argument("--concurrent", "-c", type=int, default=CONCURRENT_LIMIT, help="同時実行数")
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
        print(f"同時実行数: {args.concurrent}")
    except Exception as e:
        print(f"エラー: ファイルの読み込みに失敗しました: {e}", file=sys.stderr)
        sys.exit(1)

    console = Console()
    results = []
    errors = []

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
            
            # ログイン状態の管理
            perform_login_flag = False
            if os.path.exists(STORAGE_STATE_PATH):
                print(f"既存のログイン状態をロードします: {STORAGE_STATE_PATH}")
                context = await browser.new_context(user_agent=USER_AGENT, storage_state=STORAGE_STATE_PATH)
                page = await context.new_page()
                
                try:
                    await page.goto(SSO_CHECK_URL, wait_until="domcontentloaded", timeout=10000)
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
                context = await browser.new_context(user_agent=USER_AGENT)
                page = await context.new_page()
                perform_login_flag = True

            if perform_login_flag:
                await perform_login(page, user_id, password)
                os.makedirs(os.path.dirname(STORAGE_STATE_PATH), exist_ok=True)
                await context.storage_state(path=STORAGE_STATE_PATH)
                print(f"新しいログイン状態を保存しました: {STORAGE_STATE_PATH}")

            print("ログインに成功し、非同期データ取得を開始します。")

            # セマフォで同時実行数を制限
            semaphore = asyncio.Semaphore(args.concurrent)

            # プログレスバーで進捗表示
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task(f"[cyan]四季報記事を非同期取得中...", total=len(stock_codes))

                # 非同期タスクを作成
                tasks = []
                for stock_code in stock_codes:
                    task_coro = process_stock_code(semaphore, page, stock_code, progress, task, console)
                    tasks.append(task_coro)

                # 全タスクを並行実行
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # エラーを処理
                processed_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        error_result = {
                            "証券コード": stock_codes[i],
                            "社名": "",
                            "四季報記事": [],
                            "エラー": str(result)
                        }
                        processed_results.append(error_result)
                        errors.append(f"{stock_codes[i]}: {result}")
                    else:
                        processed_results.append(result)
                        if "エラー" in result:
                            errors.append(f"{result['証券コード']}: {result['エラー']}")

            await browser.close()

            # 結果を保存
            output_data = {
                "取得日時": datetime.now().isoformat(),
                "総社数": len(stock_codes),
                "成功社数": len([r for r in processed_results if "エラー" not in r]),
                "エラー社数": len(errors),
                "同時実行数": args.concurrent,
                "エラー詳細": errors,
                "データ": processed_results
            }

            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            console.print(f"\n[bold green]非同期処理完了！[/bold green]")
            console.print(f"結果を保存しました: {args.output}")
            console.print(f"総社数: {len(stock_codes)}")
            console.print(f"成功: {len([r for r in processed_results if 'エラー' not in r])}社")
            console.print(f"エラー: {len(errors)}社")
            console.print(f"同時実行数: {args.concurrent}")
            
            if errors:
                console.print(f"\n[bold red]エラーが発生した会社:[/bold red]")
                for error in errors:
                    console.print(f"  {error}")

        except Exception as e:
            console.print(f"[bold red]エラー: {e}[/bold red]")
            sys.exit(1)

def main():
    """メイン関数（非同期処理を実行）"""
    load_dotenv()
    asyncio.run(main_async())

if __name__ == "__main__":
    main() 