import requests
import os
import re
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_news(query="코스피 경제", display=20):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": display, "sort": "date"}
    response = requests.get(url, headers=headers, params=params)
    return response.json().get("items", [])

def clean_text(text):
    return re.sub(r"<.*?>", "", text).strip()

def judge_market(title, description):
    prompt = f"""
다음 뉴스를 보고 주식 시장이 상승할지 하락할지 판단해줘.
반드시 JSON 형식으로만 답해줘. 다른 말은 하지 마.

{{
  "result": "상승" or "하락",
  "reason": "한 줄 설명"
}}

뉴스 제목: {title}
뉴스 내용: {description}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"} 
    )
    return json.loads(response.choices[0].message.content)

def process_news():
    keywords = ["코스피", "금리", "환율", "경기 침체", "기업 실적", "전쟁", "유가"]
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
            judgment = judge_market(title, description)

            result.append({
                "title": title,
                "description": description[:150],
                "date": item["pubDate"],
                "link": item["originallink"],
                "result": judgment["result"],
                "reason": judgment["reason"],
            })

    with open("news_data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"완료! 총 {len(result)}개 뉴스 저장됨")

if __name__ == "__main__":
    process_news()