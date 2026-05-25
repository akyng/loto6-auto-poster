import os
import json
import time
import tweepy
from config import Config

class Loto6Publisher:
    """
    ロト6自動投稿エンジン
    API投稿 (tweepy), ブラウザ自動投稿 (playwright), または テスト出力 (dryrun) をサポートします。
    """
    def __init__(self):
        # 動作モード
        self.publish_mode = os.getenv('PUBLISH_MODE', 'dryrun').lower()
        
        # X API Credentials (APIモード時のみ初期化)
        if self.publish_mode == 'api':
            self.client = tweepy.Client(
                consumer_key=Config.API_KEY,
                consumer_secret=Config.API_KEY_SECRET,
                access_token=Config.ACCESS_TOKEN,
                access_token_secret=Config.ACCESS_TOKEN_SECRET
            )
        else:
            self.client = None

    def publish_thread(self, tweets: list) -> list:
        """
        ツイートスレッド（単一または複数）を投稿します。
        tweets: 投稿テキストのリスト (例: ['1つ目の投稿', '2つ目の投稿'])
        """
        if not tweets:
            print("[Warning] 投稿するコンテンツが空です。")
            return []

        # 1. DRYRUN モード
        if self.publish_mode == 'dryrun':
            print("\n================ [DRYRUN MODE] ================ ")
            for idx, text in enumerate(tweets):
                print(f"■ ポスト {idx + 1}:\n{text}")
                print("-" * 40)
            print("================================================\n")
            return [f"dryrun_id_{i}" for i in range(len(tweets))]

        # 2. API モード (tweepy.Client)
        elif self.publish_mode == 'api':
            print(f"📣 APIを使用して投稿を開始中... (全 {len(tweets)} ポスト)")
            try:
                published_ids = []
                parent_id = None
                
                for idx, text in enumerate(tweets):
                    if idx == 0:
                        # 最初のポスト
                        response = self.client.create_tweet(text=text)
                        parent_id = response.data['id']
                        published_ids.append(parent_id)
                        print(f"✅ ポスト 1 成功! Tweet ID: {parent_id}")
                    else:
                        # 2つ目以降（リプライで繋ぐ）
                        time.sleep(2)
                        response = self.client.create_tweet(text=text, in_reply_to_tweet_id=parent_id)
                        tweet_id = response.data['id']
                        published_ids.append(tweet_id)
                        print(f"✅ ポスト {idx + 1} 成功! Tweet ID: {tweet_id}")
                
                return published_ids
            except Exception as e:
                print(f"[Error] API投稿中にエラーが発生しました: {e}")
                raise e

        # 3. BROWSER モード (Playwright)
        elif self.publish_mode == 'browser':
            return self._publish_browser(tweets)
            
        else:
            raise ValueError(f"無効な PUBLISH_MODE です: {self.publish_mode}")

    def _publish_browser(self, tweets: list) -> list:
        import threading
        result_box = {}
        
        def worker():
            try:
                result_box["result"] = self._publish_browser_internal(tweets)
            except Exception as e:
                result_box["error"] = e
                
        t = threading.Thread(target=worker)
        t.start()
        t.join()
        
        if "error" in result_box:
            raise result_box["error"]
        return result_box["result"]

    def _publish_browser_internal(self, tweets: list) -> list:
        """
        Playwrightによる堅牢なブラウザ自動投稿（単一＆スレッド両対応）
        """
        from playwright.sync_api import sync_playwright
        
        cookie_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'loto6_cookies.json')
        print(f"[*] Playwrightブラウザ自動化を使用してロト6スレッド投稿を開始 (クッキー: {cookie_path})...")
        
        if not os.path.exists(cookie_path):
            raise FileNotFoundError(f"クッキーファイル '{cookie_path}' が見つかりません。まずクッキーを生成してください。")
            
        published_ids = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1280, 'height': 1200})
            
            # クッキーの読み込みとサニタイズ
            with open(cookie_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            
            cleaned_cookies = []
            for c in cookies:
                if "sameSite" in c:
                    val = c["sameSite"]
                    if val is None or str(val).lower() in ["no_restriction", "none"]:
                        c["sameSite"] = "None"
                    elif str(val).lower() == "lax":
                        c["sameSite"] = "Lax"
                    elif str(val).lower() == "strict":
                        c["sameSite"] = "Strict"
                    else:
                        del c["sameSite"]
                cleaned_cookies.append(c)
                
            context.add_cookies(cleaned_cookies)
            page = context.new_page()
            page.set_default_timeout(45000)
            
            try:
                # 投稿ページに遷移
                page.goto("https://x.com/compose/post")
                print("[*] X投稿画面のロードを6秒間待機中...")
                time.sleep(6)
                
                # ログイン状態の検証
                if "login" in page.url or "i/flow" in page.url:
                    print("[!] ログインクッキーが失効している可能性があります。")
                    browser.close()
                    raise ValueError(
                        f"❌ Xへのログインセッション（クッキー）が失効しています。\n"
                        f"ローカル環境で 'generate_cookies.py' を実行してクッキーを再生成し、\n"
                        f"GitHub のリポジトリシークレット (X_COOKIE_JSON) を最新のクッキー情報に更新してください。"
                    )
                
                # 投稿モーダルエリア（ダイアログ）の読み込み完了を直接待機
                page.wait_for_selector('div[role="dialog"] [data-testid="tweetTextarea_0"]', timeout=30000)
                time.sleep(1)
                
                # 投稿するスレッドの配列を出力
                print(f"[*] 投稿用スレッドの配列 (全 {len(tweets)} ポスト):")
                for i, tw in enumerate(tweets):
                    print(f"   - ポスト #{i+1} (文字数: {len(tw)}): {repr(tw)}")
                
                # 1. 親ポストを入力
                print(f"[*] 1つ目のポストを入力中 (文字数: {len(tweets[0])})...")
                first_textbox = page.locator('div[role="dialog"] [data-testid="tweetTextarea_0"]').first
                first_textbox.wait_for(timeout=15000)
                first_textbox.click()
                time.sleep(1)  # フォーカスとアクティブ化の時間を確保
                first_textbox.focus()
                time.sleep(1)  # フォーカスがブラウザ側で登録されるのを確実に待つ
                page.keyboard.type(tweets[0])
                time.sleep(1)
                
                # 🌟 ハッシュタグ補完ドロップダウンと透明な傍受レイヤーを閉じるために Escape を送信
                print("[*] ハッシュタグ自動補完オーバーレイを閉じるため Escape キーを送信中...")
                page.keyboard.press("Escape")
                time.sleep(1)
                
                # 2. スレッド（2つ目以降 of ツイート）の追加
                for idx, tweet_text in enumerate(tweets[1:], start=1):
                    print(f"[*] 返信ツリー（子ポスト #{idx+1}）を追加中...")
                    add_button = page.locator('div[role="dialog"] [data-testid="addButton"]').first
                    add_button.wait_for(timeout=10000)
                    
                    # 🌟 ボタンが disabled もしくは aria-disabled="true" かチェックして React クラッシュを防ぐ
                    is_disabled = add_button.evaluate('node => node.disabled || node.getAttribute("aria-disabled") === "true"')
                    if is_disabled:
                        raise Exception("スレッド追加ボタン（addButton）が無効化されています。入力テキストがXの制限文字数（日本語140文字）を超過している可能性があります。")
                        
                    add_button.click(force=True)  # 物理クリック＋オーバーレイ強制突破
                    print("[*] スレッド追加ボタンをクリックしました。")
                    time.sleep(3)
                    
                    current_textbox = page.locator(f'div[role="dialog"] [data-testid="tweetTextarea_{idx}"]').first
                    current_textbox.wait_for(timeout=10000)
                    print(f"[*] 子ポスト #{idx+1} を入力中... (ダイアログ内のインデックス {idx} を検出)")
                    current_textbox.click()
                    time.sleep(1)
                    current_textbox.focus()
                    time.sleep(1)  # フォーカスがブラウザ側で登録されるのを確実に待つ
                    page.keyboard.type(tweet_text)
                    time.sleep(1)
                
                # XがURLリンクプレビューを生成するのを十分待機（青いローディングスピナー消滅待ち）
                print("[*] リンクプレビュー解析のため8秒間待機中...")
                time.sleep(8)
                
                # 3. 送信ボタンをクリックと送信完了の待ち合わせ (最大4回のインテリジェントリトライ)
                modal_closed = False
                for attempt in range(4):
                    print(f"[*] ポストスレッドを送信中... (試行 {attempt + 1}/4)")
                    post_button = page.locator('div[role="dialog"] [data-testid="tweetButton"]').first
                    post_button.wait_for(timeout=10000)
                    post_button.evaluate('node => node.click()')
                    
                    try:
                        # 投稿テキストエリアが画面から消える（送信成功）のを5秒監視
                        page.locator('div[role="dialog"] [data-testid="tweetTextarea_0"]').first.wait_for(state="hidden", timeout=5000)
                        print("[✔] 投稿モーダルが閉じられたことを確認しました！")
                        modal_closed = True
                        break
                    except Exception:
                        print("[!] 5秒以内にモーダルが閉じなかったため、再送信を試みます。")
                
                if not modal_closed:
                    raise Exception("送信ボタンをクリックしましたが、モーダルが閉じられず送信を完了できませんでした。")
                
                time.sleep(5)  # 最終送信バッファ待機
                print("[+] Xへのブラウザ自動スレッド投稿が完了しました！")
                published_ids = [f"browser_loto6_{i+1}" for i in range(len(tweets))]
                
            except Exception as e:
                print(f"[Error] ブラウザ自動投稿中にエラーが発生しました: {e}")
                try:
                    screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'screenshot_error.png')
                    page.screenshot(path=screenshot_path)
                    print(f"[!] エラー画面のスクリーンショットを保存しました: {screenshot_path}")
                except Exception as se:
                    print(f"⚠️ スクリーンショット保存中にエラーが発生しました: {se}")
                raise e
            finally:
                browser.close()
                
        return published_ids
