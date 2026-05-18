import os
import sys
from google import genai
from google.genai import types

class Loto6Generator:
    @staticmethod
    def generate_trivia_tweet():
        """
        完全無料のGemini APIを利用して、ロト6や宝くじに関する知的な雑学、
        統計学ハック、または購入者のためのマインドセットに関するポストを自動生成します。
        文字数は140字以内（全角換算）に確実に収めます。
        """
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("⚠️ GEMINI_API_KEY is not set. Skipping trivia generation.")
            return None
        
        # クライアント初期化
        client = genai.Client(api_key=api_key)
        
        # 宣伝URLの取得
        app_url = os.getenv('X_APP_URL', 'https://onelink.to/loto6oracle')
        
        # プロンプトの定義
        prompt = f"""
あなたは「ロト6予測アドバイザー」です。
ロト6や宝くじに関する、知的で説得力があり、思わず読みたくなるような雑学、統計データ分析ハック、または購入時のマインドセットに関するポストを1つ作成してください。

【テーマのヒント（魅力的なものを1つ選んでください）】
1. 統計的なデータ（例：ロト6の出目出現率の傾向、奇数偶数の黄金バランスなど一般的な統計）
2. 確率論から見たスマートな選び方（例：連続する数字の出やすさ、偏りの心理など）
3. 世界や日本の面白い宝くじの歴史や雑学
4. 夢を追う購入者のための幸福感やメンタル面のアドバイス

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
