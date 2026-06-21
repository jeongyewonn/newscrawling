import requests
import os
import re
import json
from dotenv import load_dotenv
import yfinance as yf
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from openai import OpenAI

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

# OpenAI로 종목명 + 티커 추출
def extract_stocks(title, description):
    prompt = f"""
다음 뉴스에서 언급된 한국 주식 종목명과 야후파이낸스 티커를 추출해줘.
반드시 JSON 형식으로만 답해줘. 다른 말은 하지 마.

{{"stocks": [
    {{"name": "삼성전자", "ticker": "005930.KS"}},
    {{"name": "SK하이닉스", "ticker": "000660.KS"}}
]}}

종목이 없으면 {{"stocks": []}}

뉴스 제목: {title}
뉴스 내용: {description}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content).get("stocks", [])
    except Exception as e:
        print(f"종목 추출 실패: {e}")
        return []

# 주가 변화 조회
def get_stock_change(ticker, date_str):
    try:
        date = parsedate_to_datetime(date_str)
        start = date - timedelta(days=5)
        end = date + timedelta(days=1)

        stock = yf.Ticker(ticker)
        hist = stock.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))

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
        print(f"주가 조회 실패 ({ticker}): {e}")

    return None

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
            stocks = extract_stocks(title, description)

            stock_results = []
            for stock in stocks:
                ticker = stock.get("ticker")
                stock_name = stock.get("name")
                if ticker:
                    change = get_stock_change(ticker, item["pubDate"])
                    if change:
                        stock_results.append({
                            "name": stock_name,
                            **change
                        })

            # 종목이 없으면 코스피 전체로 대체
            if not stock_results:
                change = get_stock_change("^KS11", item["pubDate"])
                if change:
                    stock_results.append({
                        "name": "코스피",
                        **change
                    })

            result.append({
                "title": title,
                "description": description[:150],
                "date": item["pubDate"],
                "link": item["originallink"],
                "stocks": stock_results,
            })

    with open("news_data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"완료! 총 {len(result)}개 뉴스 저장됨")

if __name__ == "__main__":
    process_news()