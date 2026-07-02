import requests
import time
from typing import List, Dict, Any

BASE_URL = "https://support.optisigns.com/api/v2/help_center"

def fetch_articles(per_page: int = 100) -> List[Dict[str, Any]]:
    """
    Lấy tất cả article đã publish (draft=false) từ Zendesk Help Center.
    Dùng offset pagination, vì số trang nhỏ (<100).
    """
    articles = []
    page = 1
    while True:
        url = f"{BASE_URL}/articles.json?per_page={per_page}&page={page}&sort_by=updated_at&sort_order=desc"
        print(f"Fetching page {page}...")
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"Lỗi: {resp.status_code} - {resp.text}")
            break
        
        data = resp.json()
        page_articles = data.get("articles", [])
        if not page_articles:
            break
        
        # Lọc draft=false (dù API đã lọc, nhưng để chắc)
        filtered = [a for a in page_articles if not a.get("draft", False)]
        articles.extend(filtered)
        
        # Nếu số bài trả về ít hơn per_page => đã hết
        if len(page_articles) < per_page:
            break
        
        page += 1
        time.sleep(0.5)  # tránh rate limit
    
    print(f"Total fetched: {len(articles)} articles")
    return articles

# Test nếu chạy trực tiếp
if __name__ == "__main__":
    all_articles = fetch_articles()
    for a in all_articles[:5]:
        print(f"- {a['title']} (ID: {a['id']})")