import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

class Loto6Scraper:
    URL = 'https://takarakuji.rakuten.co.jp/backnumber/loto6/'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    @classmethod
    def fetch_latest_draws(cls):
        """
        Webから最新の当選情報をスクレイピングしてリストで返します。
        リストの先頭が最新の回号になります。
        """
        try:
            response = requests.get(cls.URL, headers=cls.HEADERS, timeout=10)
            if response.status_code != 200:
                print(f"⚠️ HTTP Error: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            tables = soup.find_all('table', class_='tblType02')
            
            draws = []
            for table in tables:
                draw_data = cls._parse_table(table)
                if draw_data:
                    draws.append(draw_data)
            
            # 回号の降順でソート
            draws.sort(key=lambda x: x['draw_number'], reverse=True)
            return draws
        except Exception as e:
            print(f"❌ Scraper Error: {e}")
            return []

    @classmethod
    def _parse_table(cls, table):
        """
        テーブルを解析して当選情報を抽出します。
        """
        try:
            draw_number = None
            draw_date = None
            numbers = []
            bonus_number = None
            carryover = 0

            rows = table.find_all('tr')
            for row in rows:
                th = row.find('th')
                if not th:
                    continue
                
                header_text = th.get_text(strip=True)
                
                # 1. 回号
                if "回号" in header_text:
                    # 回号はth[colspan="6"]に入っている
                    draw_th = row.find('th', colspan="6") or row.find_all('th')[1]
                    draw_text = draw_th.get_text(strip=True)
                    match = re.search(r'第(\d+)回', draw_text)
                    if match:
                        draw_number = int(match.group(1))

                # 2. 抽せん日
                elif "抽せん日" in header_text:
                    td = row.find('td')
                    date_text = td.get_text(strip=True) if td else ""
                    match = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', date_text)
                    if match:
                        draw_date = f"{match.group(1)}/{int(match.group(2)):02d}/{int(match.group(3)):02d}"

                # 3. 本数字
                elif "本数字" in header_text:
                    spans = row.find_all('span', class_='loto-font-large')
                    for span in spans:
                        val = span.get_text(strip=True)
                        if val.isdigit():
                            numbers.append(int(val))
                    numbers.sort()

                # 4. ボーナス数字
                elif "ボーナス数字" in header_text:
                    span = row.find('span', class_='loto-font-large')
                    if span:
                        val = span.get_text(strip=True).replace('(', '').replace(')', '').replace('（', '').replace('）', '')
                        if val.isdigit():
                            bonus_number = int(val)

                # 5. キャリーオーバー
                elif "キャリーオーバー" in header_text:
                    td = row.find('td')
                    if td:
                        co_text = td.get_text(strip=True).replace(',', '').replace('円', '')
                        if co_text.isdigit():
                            carryover = int(co_text)

            # 必須情報の確認
            if draw_number and draw_date and len(numbers) == 6 and bonus_number is not None:
                return {
                    'draw_number': draw_number,
                    'draw_date': draw_date,
                    'numbers': numbers,
                    'bonus_number': bonus_number,
                    'carryover': carryover
                }
        except Exception as e:
            print(f"⚠️ Table parsing failed: {e}")
        return None

if __name__ == '__main__':
    print("--- Scraping Latest Loto6 Results ---")
    draws = Loto6Scraper.fetch_latest_draws()
    print(f"Scraped {len(draws)} draws successfully.")
    for d in draws[:2]:
        print(f"\n第{d['draw_number']}回 ({d['draw_date']})")
        print(f"本数字: {d['numbers']}")
        print(f"ボーナス: {d['bonus_number']}")
        print(f"キャリーオーバー: {d['carryover']:,}円")
