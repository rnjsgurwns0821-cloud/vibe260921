"""
네이버 증권 "코스피 시세상위" 종목 데이터를 최대 200개까지 크롤링하는 스크립트.
대상 페이지: https://stock.naver.com/market/stock/kr/stocklist/priceTop

주의:
    위 페이지는 Next.js로 렌더링되는 SPA라서 requests로 받은 원본 HTML에는
    종목 데이터가 전혀 들어있지 않다 (페이지가 뜬 뒤 자바스크립트가 내부 API를
    호출해서 화면을 채우는 구조). 따라서 BeautifulSoup으로 HTML 테이블을 직접
    파싱하는 방식은 동작하지 않으며, 브라우저가 실제로 호출하는 것과 동일한
    JSON API(m.stock.naver.com)를 그대로 호출해서 데이터를 가져온다.
    (API 1회 요청당 pageSize는 최대 100까지 허용되어 200개를 받으려면
    2페이지를 순회해야 한다.)

필요 패키지: requests, openpyxl
    pip install requests openpyxl
"""

import csv
import time

import requests
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

API_URL = "https://m.stock.naver.com/api/stocks/priceTop/KOSPI"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://stock.naver.com/",
}

MAX_PAGE_SIZE = 100  # 서버가 허용하는 요청당 최대 개수
TARGET_COUNT = 200  # 코스피 200


def fetch_page(page, page_size=MAX_PAGE_SIZE):
    """priceTop API에서 한 페이지 분량의 원본 JSON을 가져온다."""
    params = {"page": page, "pageSize": page_size}
    res = requests.get(API_URL, headers=HEADERS, params=params, timeout=10)
    res.raise_for_status()
    return res.json()


def crawl_kospi_price_top(target_count=TARGET_COUNT, delay=0.3):
    """코스피 시세상위 종목을 target_count개까지 수집한다."""
    results = []
    page = 1

    while len(results) < target_count:
        data = fetch_page(page)
        stocks = data.get("stocks", [])
        if not stocks:
            break

        for s in stocks:
            change_info = s.get("compareToPreviousPrice", {})
            results.append(
                {
                    "순위": len(results) + 1,
                    "종목코드": s.get("itemCode", ""),
                    "종목명": s.get("stockName", ""),
                    "현재가": s.get("closePrice", ""),
                    "전일대비": s.get("compareToPreviousClosePrice", ""),
                    "등락구분": change_info.get("text", ""),
                    "등락률(%)": s.get("fluctuationsRatio", ""),
                    "거래량": s.get("accumulatedTradingVolume", ""),
                    "거래대금": s.get("accumulatedTradingValue", ""),
                    "시가총액": s.get("marketValue", ""),
                }
            )
            if len(results) >= target_count:
                break

        print(f"[INFO] {page}페이지 수집 완료 (누적 {len(results)}건)")
        page += 1
        time.sleep(delay)  # 서버 부하 방지를 위한 딜레이

    return results


def save_to_csv(rows, filename="naver_kospi_price_top200.csv"):
    if not rows:
        print("[WARN] 저장할 데이터가 없습니다.")
        return
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"[INFO] 결과 저장 완료: {filename}")


def save_to_excel(rows, filename="naver_kospi_price_top200.xlsx"):
    """크롤링 결과를 엑셀(.xlsx) 파일로 저장한다."""
    if not rows:
        print("[WARN] 저장할 데이터가 없습니다.")
        return

    headers = list(rows[0].keys())
    column_widths = [6, 10, 16, 12, 12, 10, 10, 14, 16, 18]

    wb = Workbook()
    ws = wb.active
    ws.title = "코스피_시세상위"

    ws.append(headers)
    for col, width in enumerate(column_widths, start=1):
        ws.column_dimensions[get_column_letter(col)].width = width
        cell = ws.cell(row=1, column=col)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = "A2"

    for row_data in rows:
        ws.append(list(row_data.values()))
        row_idx = ws.max_row
        for col in range(1, len(headers) + 1):
            ws.cell(row=row_idx, column=col).alignment = Alignment(
                horizontal="center", vertical="center"
            )

    wb.save(filename)
    print(f"[INFO] 결과 저장 완료: {filename}")


if __name__ == "__main__":
    rows = crawl_kospi_price_top(TARGET_COUNT)
    for row in rows[:10]:
        print(row)
    save_to_csv(rows)
    save_to_excel(rows)
