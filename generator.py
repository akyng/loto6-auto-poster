import os
import sys
from google import genai
from google.genai import types

class Loto6Generator:
    @staticmethod
    def generate_trivia_tweet(weekday=None):
        """
        完全無料のGemini APIを利用して、ロト6や宝くじに関する知的な雑学、
        統計学ハック、購入者のためのマインドセット、または曜日別テーマ（直前予想・前日予想）に関するポストを自動生成します。
        文字数は140字以内（全角換算）に確実に収めます。
        """
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("⚠️ GEMINI_API_KEY is not set. Skipping trivia generation.")
            return None
        
        # クライアント初期化
        client = genai.Client(api_key=api_key)
        
        # 宣伝URL of the app
        app_url = os.getenv('X_APP_URL', 'https://onelink.to/76cms6')
        
        # 曜日別のテーマ・指示の決定
        if weekday in [0, 3]:  # 月曜日 (0)・木曜日 (3)
            # 直前予想 (抽せん日当日)
            theme_title = "直前予想 (今日が抽せん日)"
            theme_prompt = f"""本日夜はロト6の抽せん日当日です！
今夜の抽せんに向けた購入者向け「直前予想ヒント」「今日の出目選びのコツ」「今日の数字選択のインスピレーション」、または「購入時のマインドセットや開運・決断のアドバイス」をテーマにしてください。
「本日抽せん」「今夜のロト6」といった当日であることを意識させる表現を含めてください。"""
        elif weekday in [2, 6]:  # 水曜日 (2)・日曜日 (6)
            # 前日予想 (抽せん前日)
            theme_title = "前日予想 (明日が抽せん日)"
            theme_prompt = f"""明日夜はロト6の抽せん日（前日）です！
明日の抽せんに向けた「前日予想コラム」「統計学的な着目ポイント（奇数・偶数、大きい数字・小さい数字の傾向など）」「明日への数字の選び方のアドバイス」などをテーマにしてください。
「明日抽せん」「明日のロト6」といった前日であることを意識させる表現を含めてください。"""
        else:
            # 一般トリビア (火・金・土曜日)
            theme_title = "一般トリビア・雑学"
            theme_prompt = """ロト6や宝くじ、世界のユニークな富くじの面白い歴史・雑学、確率論的ハック、または購入者のモチベーションを高めるマインドセットやスマートな選び方をテーマにしてください。"""

        # プロンプトの定義
        prompt = f"""
あなたは「ロト6予測アドバイザー」です。
現在、テーマ「{theme_title}」に基づいた、知的で説得力があり、思わず読みたくなるようなX（旧Twitter）ポストを1つ作成してください。

【今回の生成指示】
{theme_prompt}

【執筆ルール】
- 読者を惹きつける洗練された日本語で書いてください。
- X（Twitter）に直接投稿できる文章にしてください。
- 最後に、アプリ「ロト6 AI予想」を自然に宣伝し、リンク {app_url} を必ず含めてください。
- 文字数はリンク（全角換算約11.5文字分＝半角23文字分）を含めて、Xの文字数制限（日本語全角140文字、英数字半角280単位）以内に確実に収めてください。日本語1文字＝2単位、英語・記号＝1単位、リンク＝23単位として、合計270単位以内で執筆してください。
- 最後にハッシュタグ「#ロト6 #宝くじ #ロト6予想」をつけてください。
- 余計な説明（「はい、作成しました」など）やクォーテーションマークは一切含めず、投稿するテキストのみを出力してください。
"""

        try:
            model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
            print(f"🧠 Generating Loto6 Trivia via Gemini ({model})...")
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                )
            )
            
            text = response.text.strip()
            
            # クォーテーションなどのクレンジング
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1].strip()
            if text.startswith('「') and text.endswith('」'):
                text = text[1:-1].strip()
                
            print(f"✨ Generated text ({len(text)} chars):\n---\n{text}\n---")
            return text
            
        except Exception as e:
            print(f"❌ Gemini generation failed: {e}")
            return None
