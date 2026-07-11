import os
import re
import json
import requests
from datetime import datetime, time, timedelta
import pytz
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, firestore

# Timezone
JST = pytz.timezone('Asia/Tokyo')

# Baseline seed stats (pure 0 starting counts for genuine user tracking)
BASELINE_STATS = {
    'loto6': {
        'totalGenerations': 0,
        'methods': {
            'oracle': {'count': 0, 'wins': {}},
            'normal': {'count': 0, 'wins': {}},
            'filter': {'count': 0, 'wins': {}},
            'judge': {'count': 0, 'wins': {}},
        }
    },
    'loto7': {
        'totalGenerations': 0,
        'methods': {
            'oracle': {'count': 0, 'wins': {}},
            'normal': {'count': 0, 'wins': {}},
            'filter': {'count': 0, 'wins': {}},
            'judge': {'count': 0, 'wins': {}},
        }
    },
    'miniLoto': {
        'totalGenerations': 0,
        'methods': {
            'oracle': {'count': 0, 'wins': {}},
            'normal': {'count': 0, 'wins': {}},
            'filter': {'count': 0, 'wins': {}},
            'judge': {'count': 0, 'wins': {}},
        }
    }
}

class RakutenLotteryScraper:
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    @classmethod
    def fetch_draw_history(cls, lottery_type):
        """Scrapes the latest draws from Rakuten Takarakuji including past months of the current year."""
        path = 'loto6' if lottery_type == 'loto6' else ('loto7' if lottery_type == 'loto7' else 'mini')
        
        urls = [f'https://takarakuji.rakuten.co.jp/backnumber/{path}/']
        try:
            # Dynamically append past months of the current year to build a complete history for aggregation
            now = datetime.now(JST)
            current_year = now.year
            current_month = now.month
            for m in range(1, current_month):
                urls.append(f'https://takarakuji.rakuten.co.jp/backnumber/{path}/{current_year}{m:02d}/')
        except Exception as e:
            print(f"⚠️ Error preparing monthly URLs: {e}")
            
        draws_map = {}
        for url in urls:
            try:
                response = requests.get(url, headers=cls.HEADERS, timeout=10)
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                tables = soup.find_all('table', class_='tblType02')
                
                for table in tables:
                    draw_data = cls._parse_table(table, lottery_type)
                    if draw_data:
                        draws_map[draw_data['draw_number']] = draw_data
            except Exception as e:
                print(f"❌ Scraper Error for {lottery_type} at {url}: {e}")
        
        draws = list(draws_map.values())
        draws.sort(key=lambda x: x['draw_number'], reverse=True)
        return draws

    @classmethod
    def _parse_table(cls, table, lottery_type):
        try:
            draw_number = None
            draw_date = None
            numbers = []
            bonus_numbers = []

            rows = table.find_all('tr')
            for row in rows:
                th = row.find('th')
                if not th:
                    continue
                header_text = th.get_text(strip=True)
                
                # 1. Draw number
                if "回号" in header_text:
                    draw_th = row.find('th', colspan=lambda x: x is not None) or row.find_all('th')[1]
                    draw_text = draw_th.get_text(strip=True)
                    match = re.search(r'第(\d+)回', draw_text)
                    if match:
                        draw_number = int(match.group(1))

                # 2. Draw date
                elif "抽せん日" in header_text:
                    td = row.find('td')
                    date_text = td.get_text(strip=True) if td else ""
                    match = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', date_text)
                    if match:
                        # Parse date and set time to 18:30 JST (Standard draw release time)
                        dt = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)), 18, 30)
                        draw_date = JST.localize(dt)

                # 3. Main numbers (Mini Loto might have both main and bonus here)
                elif "本数字" in header_text:
                    spans = row.find_all('span', class_='loto-font-large')
                    for span in spans:
                        val = span.get_text(strip=True)
                        clean_val = val.replace('(', '').replace(')', '').replace('（', '').replace('）', '')
                        if clean_val.isdigit():
                            num = int(clean_val)
                            if '(' in val or '（' in val or 'loto-highlight' in span.get('class', []):
                                bonus_numbers.append(num)
                            else:
                                numbers.append(num)
                    numbers.sort()

                # 4. Bonus numbers
                elif "ボーナス数字" in header_text:
                    spans = row.find_all('span', class_='loto-font-large')
                    for span in spans:
                        val = span.get_text(strip=True).replace('(', '').replace(')', '').replace('（', '').replace('）', '')
                        if val.isdigit():
                            bonus_numbers.append(int(val))

            pick_count = 6 if lottery_type == 'loto6' else (7 if lottery_type == 'loto7' else 5)
            bonus_count = 1 if lottery_type != 'loto7' else 2

            if draw_number and draw_date and len(numbers) == pick_count and len(bonus_numbers) == bonus_count:
                return {
                    'draw_number': draw_number,
                    'draw_date': draw_date,
                    'numbers': numbers,
                    'bonus_numbers': bonus_numbers
                }
        except Exception as e:
            print(f"⚠️ Table parsing failed: {e}")
        return None

def check_winning_grade(lottery_type, pick, winning_numbers, bonus_numbers):
    """Compares the pick against the winning results and returns the winning grade (1-6) or None."""
    pick_set = set(pick)
    win_set = set(winning_numbers)
    bonus_set = set(bonus_numbers)

    match_count = len(pick_set.intersection(win_set))
    bonus_match_count = len(pick_set.intersection(bonus_set))

    if lottery_type == 'loto6':
        if match_count == 6:
            return 1
        elif match_count == 5 and bonus_match_count >= 1:
            return 2
        elif match_count == 5:
            return 3
        elif match_count == 4:
            return 4
        elif match_count == 3:
            return 5

    elif lottery_type == 'loto7':
        if match_count == 7:
            return 1
        elif match_count == 6 and bonus_match_count >= 1:
            return 2
        elif match_count == 6:
            return 3
        elif match_count == 5:
            return 4
        elif match_count == 4:
            return 5
        elif match_count == 3 and bonus_match_count >= 1:
            return 6

    elif lottery_type == 'miniLoto':
        if match_count == 5:
            return 1
        elif match_count == 4 and bonus_match_count >= 1:
            return 2
        elif match_count == 4:
            return 3
        elif match_count == 3:
            return 4

    return None

def generate_daily_mock_predictions(db, count_per_method=50):
    """
    Generates mock predictions daily for all three lottery types and inserts them into predictions_raw.
    This simulates user activity and ensures the global statistics are populated with higher win counts.
    """
    import random
    print(f"🔮 Generating {count_per_method} daily mock predictions per method for all lottery types...")
    
    methods = ['oracle', 'normal', 'filter', 'judge']
    lottery_configs = {
        'loto6': {'pick': 6, 'max': 43, 'db_name': 'ロト6'},
        'loto7': {'pick': 7, 'max': 37, 'db_name': 'ロト7'},
        'miniLoto': {'pick': 5, 'max': 31, 'db_name': 'ミニロト'}
    }
    
    now_utc = datetime.now(pytz.utc)
    predictions = []
    
    for ltype, config in lottery_configs.items():
        for method in methods:
            for _ in range(count_per_method):
                numbers = sorted(random.sample(range(1, config['max'] + 1), config['pick']))
                predictions.append({
                    'lotteryType': config['db_name'],
                    'method': method,
                    'numbers': numbers,
                    'timestamp': now_utc
                })
                
    # Write to Firestore in batches
    batch_size = 400
    total_written = 0
    for i in range(0, len(predictions), batch_size):
        batch = db.batch()
        chunk = predictions[i : i + batch_size]
        for pred in chunk:
            doc_ref = db.collection('predictions_raw').document()
            batch.set(doc_ref, pred)
        batch.commit()
        total_written += len(chunk)
        
    print(f"✅ Successfully wrote {total_written} mock predictions to 'predictions_raw'.")

def main():
    print("🚀 Starting Lottery Prediction Statistics Aggregator...")

    # Initialize Firebase Admin SDK
    cred_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'service_account.json')
    if os.path.exists(cred_path):
        print(f"📦 Loading service account credentials from {cred_path}")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    else:
        print("ℹ️ No service_account.json found. Attempting to use default credentials...")
        try:
            firebase_admin.initialize_app()
        except Exception as e:
            print(f"❌ Failed to initialize Firebase: {e}")
            print("Please place the Google Cloud Service Account JSON key at backend/service_account.json")
            return

    db = firestore.client()

    # Step 0: Generate daily mock predictions to simulate user activity and boost statistics
    try:
        import random
        # 3 lottery types (Loto 6, Loto 7, Mini Loto) * 4 methods = 12 combinations.
        # To get 5,000 to 10,000 total generations, select a random target and divide by 12.
        target_total = random.randint(5000, 10000)
        count_per_method = target_total // 12
        generate_daily_mock_predictions(db, count_per_method=count_per_method)
    except Exception as e:
        print(f"⚠️ Failed to generate mock predictions: {e}")

    # Step 1: Scrape Known Draw History for Loto 6, Loto 7, and Mini Loto
    lottery_types = ['loto6', 'loto7', 'miniLoto']
    draw_histories = {}
    
    for ltype in lottery_types:
        print(f"🌐 Scraping latest draws for {ltype}...")
        draws = RakutenLotteryScraper.fetch_draw_history(ltype)
        if not draws:
            print(f"❌ Could not scrape history for {ltype}, skipping.")
            continue
        draw_histories[ltype] = draws
        print(f"✅ Loaded {len(draws)} draws. Latest draw: 第{draws[0]['draw_number']}回 on {draws[0]['draw_date'].strftime('%Y-%m-%d')}")

    # Load/Initialize stats data maps from Firestore for all lottery types.
    # This guarantees that we check and update draw numbers even if no new predictions are made.
    stats_data_map = {}
    for ltype in lottery_types:
        history = draw_histories.get(ltype)
        if not history:
            continue

        stats_doc_ref = db.collection('global_stats').document(ltype)
        stats_snapshot = stats_doc_ref.get()

        if stats_snapshot.exists:
            stats_data = stats_snapshot.to_dict()
        else:
            print(f"🌱 Document global_stats/{ltype} does not exist. Seeding with baseline data...")
            baseline = BASELINE_STATS[ltype]
            stats_data = {
                'totalGenerations': baseline['totalGenerations'],
                'lastUpdated': firestore.SERVER_TIMESTAMP,
                'latestDraw': {
                    'drawNumber': history[0]['draw_number'],
                    'wins': {}
                },
                'methods': {}
            }
            for method, mstats in baseline['methods'].items():
                stats_data['methods'][method] = {
                    'count': mstats['count'],
                    'wins': {str(grade): count for grade, count in mstats['wins'].items()}
                }

        # Ensure latest draw wins structure exists
        latest_draw = history[0]
        latest_draw_num = latest_draw['draw_number']

        # Ensure methods structures exist
        for m in ['oracle', 'normal', 'filter', 'judge']:
            if m not in stats_data['methods']:
                stats_data['methods'][m] = {'count': 0, 'wins': {}}

        # If the stored draw number is older/different than the latest scraped draw,
        # we reset the latestDraw stats immediately.
        stored_draw_num = stats_data.get('latestDraw', {}).get('drawNumber', 0)
        if stored_draw_num != latest_draw_num:
            print(f"🔄 New draw detected for {ltype}: stored {stored_draw_num} -> latest {latest_draw_num}. Resetting latestDraw stats.")
            stats_data['latestDraw'] = {
                'drawNumber': latest_draw_num,
                'wins': {}
            }
            stats_data['_dirty'] = True

        stats_data_map[ltype] = stats_data

    # Step 2: Fetch and Process Raw Unprocessed Predictions from Firestore in batches
    print("🔍 Querying unprocessed prediction logs from 'predictions_raw'...")
    predictions_ref = db.collection('predictions_raw')
    
    total_processed = 0
    last_doc = None
    
    while True:
        # Use order_by and start_after pagination to prevent infinite loops on skipped docs
        query = predictions_ref.order_by('timestamp')
        if last_doc:
            query = query.start_after(last_doc)
        query = query.limit(500)
        docs = query.get()

        if not docs:
            print("💤 No more new predictions to process.")
            break

        print(f"📈 Found {len(docs)} new predictions to process in this batch.")

        for doc in docs:
            last_doc = doc
            data = doc.to_dict()
            ltype = data.get('lotteryType')
            
            # Map Japanese names to English keys if necessary
            if ltype == 'ロト6':
                ltype = 'loto6'
            elif ltype == 'ロト7':
                ltype = 'loto7'
            elif ltype == 'ミニロト':
                ltype = 'miniLoto'
                
            if ltype not in lottery_types:
                # Malformed/unrecognized lottery type, delete it to prevent infinite loop
                print(f"⚠️ Deleting unrecognized/malformed prediction log: ID={doc.id}, lotteryType={ltype}")
                doc.reference.delete()
                total_processed += 1
                continue

            history = draw_histories.get(ltype)
            stats_data = stats_data_map.get(ltype)
            if not history or not stats_data:
                continue

            method = data.get('method')
            numbers = data.get('numbers')
            ts = data.get('timestamp')

            if not method or not numbers or not ts:
                # Corrupt log, delete it
                doc.reference.delete()
                total_processed += 1
                continue

            # Convert Firestore timestamp to JST datetime
            if isinstance(ts, datetime):
                pred_time = ts.replace(tzinfo=pytz.utc).astimezone(JST)
            else:
                pred_time = datetime.now(JST)

            # Match target draw based on date-time
            # Target draw is the earliest draw whose draw date is after the prediction generation time
            target_draw = None
            for draw in reversed(history):  # Oldest to newest
                if draw['draw_date'] > pred_time:
                    target_draw = draw
                    break

            # If no future draw was found, it belongs to an upcoming draw whose results are not yet available.
            # We skip it and leave it in predictions_raw to be evaluated when its results are published.
            if not target_draw:
                continue

            # Verify matches against the matched target draw
            win_grade = check_winning_grade(ltype, numbers, target_draw['numbers'], target_draw['bonus_numbers'])

            # 1. Update overall counters
            stats_data['totalGenerations'] += 1
            stats_data['methods'][method]['count'] += 1

            if win_grade:
                grade_str = str(win_grade)
                
                # 2. Update method win counts
                m_wins = stats_data['methods'][method]['wins']
                m_wins[grade_str] = m_wins.get(grade_str, 0) + 1

                # 3. If it matched the latest draw, update the latest draw banner wins
                latest_draw_num = history[0]['draw_number']
                if target_draw['draw_number'] == latest_draw_num:
                    ld_wins = stats_data['latestDraw']['wins']
                    ld_wins[grade_str] = ld_wins.get(grade_str, 0) + 1

            # Delete processed log to keep database storage footprint clean
            doc.reference.delete()
            total_processed += 1
            stats_data['_dirty'] = True

    # Step 3: Save any modified/dirty global stats back to Firestore
    for ltype in lottery_types:
        stats_data = stats_data_map.get(ltype)
        if stats_data and stats_data.get('_dirty'):
            stats_data.pop('_dirty', None)  # Clean up helper key
            stats_data['lastUpdated'] = firestore.SERVER_TIMESTAMP
            
            stats_doc_ref = db.collection('global_stats').document(ltype)
            stats_doc_ref.set(stats_data)
            print(f"💾 Successfully updated Firestore stats for {ltype} (Latest draw: 第{stats_data['latestDraw']['drawNumber']}回)")

    print(f"\n🏁 Aggregation completed successfully! Total processed and deleted logs: {total_processed}")

if __name__ == '__main__':
    main()
