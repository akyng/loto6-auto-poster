#!/usr/bin/env python3
import os
import sys
import re
from google import genai
from google.genai import types

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from publisher import Loto6Publisher

def calculate_tweet_weight(text: str) -> int:
    weight = 0
    for char in text:
        if ord(char) <= 127:
            weight += 1
        else:
            weight += 2
    return weight

def main():
    print("===========================================================")
    print("     🔮 --- Loto6 Custom Post (Logic & Trivia) --- 🔮       ")
    print("===========================================================")

    # 1. Validate config
    Config.validate()
    
    # 2. Initialize Gemini Client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY is not set.")
        sys.exit(1)
    client = genai.Client(api_key=api_key)
    # 1.5. Load cache history
    import json
    cache_path = os.path.join(os.path.dirname(__file__), 'cache.json')
    cache_data = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load cache: {e}")
            
    history = cache_data.get('trivia_history', [])
    history_instruction = ""
    if history:
        history_instruction = "\n【注意：以下の最近の投稿内容とトピックや切り口、構成が重複しないように、別の雑学・アプローチで新しく作成してください】\n"
        for h in history:
            h_clean = h.replace('\n', ' ').strip()
            history_instruction += f"- {h_clean[:120]}\n"

    # 3. Create Custom Prompt for Loto6 Logic / Trivia
    app_url = Config.APP_URL
    prompt = f"""
あなたに「ロト6統計分析スペシャリスト」として、X（旧Twitter）で、ロト6購入者に向けて「ロト6の統計・数値選択ロジックに関する超有益な豆知識」を紹介するポストを作成してください。
今回は、特に「ブックマーク保存」や「いいね」を誘発してインプレッションを爆発的（100以上）に伸ばすためのバズる投稿を目指します。

【テーマのヒント】
- 連番（例: 14と15など）が出現する驚異の確率（実は約80%で連番が含まれること）や、
- 下1桁（末尾）が放置・同じ数字（例: 04, 14, 24など）が含まれる確率、
- あるいは「合計値」がどのレンジに収まりやすいか（大半が95〜152の間に収まるという統計データ）など、
購入者が「明日の選択肢に今すぐ使える具体的かつ説得力のある数値統計」を1つ取り上げてください。
{history_instruction}

【執筆ルール】
- 冒頭にインパクトのあるフック（例：「ロト6で絶対に知っておくべき統計の真実」や「偶然だと思っていませんか？」など）を配置してください。
- 専門的すぎず、直感的で分かりやすく、知的な驚きを与える内容にしてください。
- ハッシュタグは絶対に含めないでください（プログラム側で結合するため）。
- 最後に、アプリ「ロト6 AI予想」を自然に宣伝し、リンク {app_url} を必ず含めてください。
- 文字数はリンク（全角換算約11.5文字分＝半角23文字分）を含めて、Xの文字数制限（日本語全角140文字、英数字半角280単位）以内に確実に収めてください。日本語1文字＝2単位、英語・記号＝1単位、リンク＝23単位として、合計270単位以内で執筆してください。
- 余計な説明（「はい、作成しました」など）やクォーテーションマークは一切含めず、投稿するテキストのみを出力してください。
"""

    print("🧠 Generating Loto6 Trivia via Gemini...")
    try:
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        response = client.models.generate_content(
            model=gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.8,
            )
        )
        trivia_text = response.text.strip()
        
        # クレンジング
        if trivia_text.startswith('"') and trivia_text.endswith('"'):
            trivia_text = trivia_text[1:-1].strip()
        if trivia_text.startswith('「') and trivia_text.endswith('」'):
            trivia_text = trivia_text[1:-1].strip()
            
    except Exception as e:
        print(f"❌ Gemini generation failed: {e}")
        sys.exit(1)

    print(f"✨ [Approved Loto6 Text]:\n---\n{trivia_text}\n---")

    # 4. Split thread and attach link in reply (Same logic as bot.py for impression maximization)
    if app_url in trivia_text:
        parts = trivia_text.split(app_url)
        main_part = parts[0].strip()
        main_part = re.sub(r'(無料ダウンロードはこちらから|アプリ「ロト6 AI予想」を自然に宣伝し、リンク|アプリ「ロト6 AI予想」は?こちらから|👉|👇)\s*$', '', main_part).strip()
        
        # 1ポスト目（リンクなし・ハッシュタグ厳選1個）
        post1 = f"{main_part}\n\n#ロト6予想"
        
        # 140文字（280ウェイト）制限の動的自動トリミング
        max_weight = 280
        while calculate_tweet_weight(post1) > max_weight and len(main_part) > 10:
            main_part = main_part[:-1].strip()
            main_part = re.sub(r'[、。，．！★☆！?？]+$', '', main_part)
            post1 = f"{main_part}...\n\n#ロト6予想"
        
        # 2ポスト目（リプライにリンク・タグ格納）
        post2 = f"ロト6の最新AI予想アプリはこちらからチェック！👇\n{app_url}\n\n#ロト6 #宝くじ"
        
        tweets_to_post = [post1, post2]
    else:
        tweets_to_post = [trivia_text]

    # 5. Publish to X
    try:
        publisher = Loto6Publisher()
        published_ids = publisher.publish_thread(tweets_to_post)
        
        if len(published_ids) == len(tweets_to_post):
            print("🎉 Custom Loto6 post successfully published!")
            
            # Save to trivia_history
            if 'trivia_history' not in cache_data:
                cache_data['trivia_history'] = []
            cache_data['trivia_history'].append(tweets_to_post[0])
            if len(cache_data['trivia_history']) > 10:
                cache_data['trivia_history'] = cache_data['trivia_history'][-10:]
            
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                print("💾 Updated cache history.")
            except Exception as e:
                print(f"⚠️ Failed to save cache: {e}")
            
            # Chatwork notification disabled
            print("⚠️ Chatwork notification is disabled.")
        else:
            print("⚠️ Custom Loto6 post was partially published or failed.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Publishing Engine error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
