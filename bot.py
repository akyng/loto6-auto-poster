import sys
import os
import json
import tweepy
import time
from datetime import datetime, timezone, timedelta

# プロジェクトルートを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from scraper import Loto6Scraper

CACHE_FILE = os.path.join(os.path.dirname(__file__), 'cache.json')

def load_cache():
    """
    キャッシュファイルから自動投稿状況を読み込みます。
    新旧フォーマットのマイグレーションも行います。
    """
    default_cache = {"last_draw_number": 0, "last_posted_analysis_date": ""}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # 必須キーをマージ
                    for k, v in default_cache.items():
                        if k not in data:
                            data[k] = v
                    return data
                elif isinstance(data, int):
                    # 数値のみの旧フォーマットから移行
                    return {"last_draw_number": data, "last_posted_analysis_date": ""}
        except Exception as e:
            print(f"⚠️ Cache read error: {e}")
    return default_cache

def save_cache(data):
    """
    キャッシュファイルへ自動投稿状況を保存します。
    """
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Updated cache: {data}")
    except Exception as e:
        print(f"❌ Cache write error: {e}")

def create_tweets(draw):
    """
    ロト6の当選データから、自動投稿用のツイートテキストを作成します。
    ※Twitter API文字数制限(全角140文字/半角280文字)を考慮してスリム化しています。
    """
    draw_num = draw['draw_number']
    date = draw['draw_date']
    nums_str = ", ".join(map(str, draw['numbers']))
    bonus = draw['bonus_number']
    carryover = draw['carryover']

    # 1. 当選番号速報ツイート (約230ポイント)
    news_tweet = (
        f"【第{draw_num}回 ロト6 当選番号速報】\n"
        f"📅 抽せん日: {date}\n\n"
        f"🎨 本数字: {nums_str}\n"
        f"💎 ボーナス数字: ({bonus})\n\n"
        f"次回AI予想はアプリ「ロト6 AI予想」にお任せください！🔮✨\n"
        f"👉 {Config.APP_URL}\n\n"
        f"#ロト6 #Loto6 #当選番号速報"
    )

    # 2. キャリーオーバー発生時周知ツイート (約245ポイント)
    carryover_tweet = None
    if carryover > 0:
        carryover_tweet = (
            f"【ロト6 キャリーオーバー情報！🔥】\n"
            f"第{draw_num}回の抽せん結果、次回へのキャリーオーバーが発生中！\n\n"
            f"💰 キャリーオーバー額：\n"
            f"✨ {carryover:,} 円 ✨\n\n"
            f"次回AI予想はアプリ「ロト6 AI予想」にお任せください！🔮🚀\n"
            f"👉 {Config.APP_URL}\n\n"
            f"#ロト6 #キャリーオーバー #Loto6"
        )

    return news_tweet, carryover_tweet

def generate_analysis_tweet(draws, weekday):
    """
    ロト6の過去結果から統計分析を行い、次回抽せん前日の告知ツイートを作成します。
    ※文字数制限（全角140字以内）に確実に収まるよう極めてスリムなデザインにしています。
    """
    latest_draw = draws[0]
    draw_num = latest_draw['draw_number']
    nums = latest_draw['numbers']
    carryover = latest_draw['carryover']

    # 1. 奇数：偶数の比率
    odd_cnt = sum(1 for n in nums if n % 2 != 0)
    even_cnt = 6 - odd_cnt

    # 2. 大（23-43）：小（1-22）の比率
    high_cnt = sum(1 for n in nums if n >= 23)
    low_cnt = 6 - high_cnt

    # 3. 本数字の合計値
    sum_val = sum(nums)

    # 4. 直近4回出現数からホット・コールド数字を算出
    freq = {}
    for d in draws:
        for n in d['numbers']:
            freq[n] = freq.get(n, 0) + 1
    
    sorted_freq = sorted(freq.items(), key=lambda x: (x[1], x[0]), reverse=True)
    hot_candidates = [item[0] for item in sorted_freq if item[1] > 1]
    if len(hot_candidates) < 3:
        hot_candidates += [item[0] for item in sorted_freq if item[0] not in hot_candidates]
    hot_nums = sorted(hot_candidates[:3])

    all_appeared = set()
    for d in draws:
        all_appeared.update(d['numbers'])
    cold_candidates = [n for n in range(1, 44) if n not in all_appeared]
    cold_nums = sorted(cold_candidates[:3])

    next_day_str = "明日（月曜）" if weekday == 6 else "明日（木曜）"
    co_status = f"{carryover:,}円" if carryover > 0 else "なし"

    analysis_tweet = (
        f"【ロト6 {next_day_str}の抽せん前日分析 🔮】\n"
        f"📅 次回抽せん日: {next_day_str}\n"
        f"💰 CO額: {co_status}\n\n"
        f"📊 前回データ分析:\n"
        f"・奇数:偶数 ➡️ {odd_cnt}:{even_cnt}\n"
        f"・大:小 ➡️ {high_cnt}:{low_cnt}\n"
        f"・合計: {sum_val}\n"
        f"🔥 ホット: {', '.join(map(str, hot_nums))}\n"
        f"❄️ コールド: {', '.join(map(str, cold_nums))}\n\n"
        f"AI予想はアプリでチェック！🚀\n"
        f"👉 {Config.APP_URL}\n\n"
        f"#ロト6 #ロト6予想"
    )
    return analysis_tweet

def check_and_post_analysis(draws, cache_data, client, did_post_recently=False):
    """
    日本時間(JST)の日曜日・水曜日の20:30台(20:00〜20:59)に前日分析データを投稿します。
    """
    # 日本時間 (JST) の取得
    JST = timezone(timedelta(hours=9))
    now_jst = datetime.now(JST)

    weekday = now_jst.weekday()  # 0:月, 1:火, 2:水, 3:木, 4:金, 5:土, 6:日
    hour = now_jst.hour
    today_str = now_jst.strftime('%Y-%m-%d')

    print(f"⏰ Current JST Time: {now_jst.strftime('%Y-%m-%d %H:%M:%S')} (Weekday: {weekday})")

    # 手動テスト用のフラグ
    force_post = os.getenv('FORCE_ANALYSIS', 'false').lower() == 'true'

    # 日曜日(6) または 水曜日(2) の 20:00台、または強制フラグあり
    if force_post or (weekday in [2, 6] and hour == 20):
        last_posted_date = cache_data.get('last_posted_analysis_date', '')
        if force_post or last_posted_date != today_str:
            # 連続投稿時のウェイト（X API スパム防止）
            if did_post_recently:
                print("⏱️ Cooldown wait before posting analysis...")
                time.sleep(10)
                
            analysis_text = generate_analysis_tweet(draws, weekday)
            if force_post:
                analysis_text += f"\n\n(分析時間: {now_jst.strftime('%H:%M')})"
            
            try:
                print("📣 Posting Draw Eve Analysis to X...")
                response = client.create_tweet(text=analysis_text)
                print(f"✅ Posted successfully! Tweet ID: {response.data['id']}")
                
                # キャッシュを更新して保存
                cache_data['last_posted_analysis_date'] = today_str
                save_cache(cache_data)
            except tweepy.TweepyException as e:
                print(f"❌ X API Error during analysis posting: {e}")
            except Exception as e:
                print(f"❌ Unexpected Error: {e}")
        else:
            print("😴 Analysis tweet for today has already been posted. Skipping.")
    else:
        print("ℹ️ Not Sunday/Wednesday 20:00 JST. Skipping analysis check.")

def main():
    print("🤖 --- Loto6 Oracle X Auto-Poster Started ---")
    
    # 1. 設定の検証
    try:
        Config.validate()
    except Exception as e:
        print(f"❌ Configuration Error: {e}")
        sys.exit(1)

    # 2. X API クライアント初期化
    try:
        client = tweepy.Client(
            consumer_key=Config.API_KEY,
            consumer_secret=Config.API_KEY_SECRET,
            access_token=Config.ACCESS_TOKEN,
            access_token_secret=Config.ACCESS_TOKEN_SECRET
        )
    except Exception as e:
        print(f"❌ Failed to initialize X Client: {e}")
        sys.exit(1)

    # 3. 最新のロト6情報をスクレイピング
    print("🔄 Fetching latest Loto6 draw results from Web...")
    draws = Loto6Scraper.fetch_latest_draws()
    if not draws:
        print("❌ Scraper returned no data. Exiting.")
        sys.exit(1)

    latest_draw = draws[0]
    latest_draw_num = latest_draw['draw_number']
    print(f"📡 Web Latest Draw: 第{latest_draw_num}回")

    # 4. キャッシュから自動投稿状況を取得
    cache_data = load_cache()
    last_posted = cache_data.get('last_draw_number', 0)
    print(f"📦 Cache Last Posted Draw: 第{last_posted}回")

    # 初回実行時：キャッシュがない場合は、最新の1つ前を設定して最新回を自動投稿対象にする
    if last_posted == 0:
        print("ℹ️ First run detected. Initializing cache to previous draw to trigger a test post for the latest draw.")
        last_posted = latest_draw_num - 1
        cache_data['last_draw_number'] = last_posted
        save_cache(cache_data)

    did_post_recently = False

    # 5. 新しい回号の判定と自動結果速報の投稿 (月曜・木曜夜用)
    if latest_draw_num > last_posted:
        print(f"🚀 New draw detected! (第{latest_draw_num}回 > 第{last_posted}回)")
        news_text, carryover_text = create_tweets(latest_draw)
        
        # A. 当選番号速報の投稿
        try:
            print("📣 Posting winning numbers breaking news...")
            response = client.create_tweet(text=news_text)
            print(f"✅ Posted successfully. Tweet ID: {response.data['id']}")
            did_post_recently = True
            
            # メイン結果が成功した時点で、重複投稿防止のためにキャッシュを即座に更新
            cache_data['last_draw_number'] = latest_draw_num
            save_cache(cache_data)
            
        except tweepy.TweepyException as e:
            print(f"❌ X API Error during posting news: {e}")
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")

        # B. キャリーオーバー速報の投稿（発生している場合）
        if carryover_text and cache_data['last_draw_number'] == latest_draw_num:
            # Xの連続投稿防止のためのディレイ（10秒）
            print("⏱️ Cooldown wait before posting carryover...")
            time.sleep(10)
            
            try:
                print("📣 Carryover detected. Posting carryover info...")
                co_response = client.create_tweet(text=carryover_text)
                print(f"✅ Carryover posted successfully. Tweet ID: {co_response.data['id']}")
                did_post_recently = True
            except tweepy.TweepyException as e:
                print(f"❌ X API Error during posting carryover: {e}")
            except Exception as e:
                print(f"❌ Unexpected Error: {e}")
    else:
        print("😴 No new draw detected for result announcements.")

    # 6. 【新規追加】次回抽せん前日分析データのチェックと投稿 (日曜・水曜夜用)
    print("📊 Checking for Draw Eve Analysis (Sunday/Wednesday JST 20:30)...")
    check_and_post_analysis(draws, cache_data, client, did_post_recently=did_post_recently)
    print("🎉 Run completed successfully!")

if __name__ == '__main__':
    main()
