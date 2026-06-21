import requests
import os
import re
import json
from dotenv import load_dotenv
import yfinance as yf
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# 뉴스 가져오기
def get_news(query="코스피 경제", display=20):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": display, "sort": "date"}
    response = requests.get(url, headers=headers, params=params)
    return response.json().get("items", [])

# HTML 태그 제거
def clean_text(text):
    return re.sub(r"<.*?>", "", text).strip()

# 실제 주가 변화로 상승/하락 판단
def get_market_change(date_str):
    try:
        date = parsedate_to_datetime(date_str)
        start = date - timedelta(days=5)  # 주말/공휴일 고려해서 5일 전부터
        end = date + timedelta(days=1)

        ticker = yf.Ticker("^KS11")  # 코스피 지수
        hist = ticker.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))

        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            curr_close = hist['Close'].iloc[-1]
            change = curr_close - prev_close
            change_pct = (change / prev_close) * 100
            return {
                "result": "상승" if change > 0 else "하락",
                "change_pct": round(change_pct, 2),
                "prev_close": round(prev_close, 2),
                "curr_close": round(curr_close, 2),
            }
    except Exception as e:
        print(f"주가 조회 실패: {e}")
    
    return {
        "result": "판단불가",
        "change_pct": 0,
        "prev_close": 0,
        "curr_close": 0,
    }

# 전체 전처리 파이프라인
def process_news():
    keywords = ["코스피", "금리", "환율", "경기 침체", "기업 실적"]
    result = []
    seen = set()

    for keyword in keywords:
        items = get_news(keyword)
        for item in items:
            title = clean_text(item["title"])
            if title in seen:
                continue
            seen.add(title)

            description = clean_text(item["description"])
            market = get_market_change(item["pubDate"])

            result.append({
                "title": title,
                "description": description[:150],
                "date": item["pubDate"],
                "link": item["originallink"],
                "result": market["result"],
                "change_pct": market["change_pct"],
                "prev_close": market["prev_close"],
                "curr_close": market["curr_close"],
            })

    with open("news_data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"완료! 총 {len(result)}개 뉴스 저장됨")

if __name__ == "__main__":
    process_news()