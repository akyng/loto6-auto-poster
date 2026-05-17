import sys
import os
import tweepy

# プロジェクトルートを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config

def main():
    print("--- X (Twitter) API Connection Test ---")
    try:
        # 設定を検証
        Config.validate()
        print("✅ Environment variables loaded successfully.")
    except Exception as e:
        print(f"❌ Configuration Error: {e}")
        sys.exit(1)

    try:
        print("🔌 Connecting to X API (V2)...")
        # Tweepy v2 クライアント初期化
        client = tweepy.Client(
            consumer_key=Config.API_KEY,
            consumer_secret=Config.API_KEY_SECRET,
            access_token=Config.ACCESS_TOKEN,
            access_token_secret=Config.ACCESS_TOKEN_SECRET
        )
        
        # 接続テスト用にテストツイートを投稿
        print("📝 Attempting to post a test tweet...")
        test_text = "X API Connection Test: SUCCESS! 🤖✨\nLoto6 Oracle自動投稿ボット接続完了。"
        
        response = client.create_tweet(text=test_text)
        
        print("\n🎉 SUCCESS! Tweet posted successfully.")
        print(f"Tweet ID: {response.data['id']}")
        print(f"Posted Text: \n{test_text}")
    except tweepy.TweepyException as e:
        print(f"\n❌ Tweepy API Error: {e}")
        print("💡 Hint: Please double-check your credentials in backend/.env and make sure the App has 'Read and Write' permissions in Developer Portal.")
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")

if __name__ == '__main__':
    main()
