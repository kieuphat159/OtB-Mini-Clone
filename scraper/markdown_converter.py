import hashlib
import re
import os
from markdownify import markdownify as md
from typing import Dict, Any

def clean_html(html_body: str) -> str:
    """
    Loại bỏ script, style, comment HTML còn sót (dù Zendesk body thường đã sạch).
    """
    # Xóa script và style tags
    html_body = re.sub(r'<script.*?>.*?</script>', '', html_body, flags=re.DOTALL | re.IGNORECASE)
    html_body = re.sub(r'<style.*?>.*?</style>', '', html_body, flags=re.DOTALL | re.IGNORECASE)
    # Xóa HTML comments
    html_body = re.sub(r'<!--.*?-->', '', html_body, flags=re.DOTALL)
    return html_body

def html_to_markdown(html_body: str) -> str:
    """
    Chuyển HTML thành Markdown sạch, giữ heading, code block, list, table, link.
    """
    cleaned = clean_html(html_body)
    # markdownify sẽ giữ cấu trúc, relative links
    markdown_text = md(cleaned, heading_style="ATX")
    # Xóa các dòng trống thừa (tùy chọn)
    markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
    return markdown_text.strip()

def generate_slug(title: str) -> str:
    """
    Tạo slug từ title: lowercase, thay space bằng dấu gạch ngang, bỏ ký tự đặc biệt.
    """
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)  # chỉ giữ chữ, số, space, -
    slug = re.sub(r'[-\s]+', '-', slug)   # thay space và nhiều gạch ngang thành một
    slug = slug.strip('-')
    return slug

def compute_content_hash(markdown_content: str) -> str:
    """
    Tính SHA-256 của nội dung Markdown (không tính front-matter).
    """
    return hashlib.sha256(markdown_content.encode('utf-8')).hexdigest()

def convert_article(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nhận một article dict từ Zendesk, trả về dict gồm:
      - slug: tên file
      - front_matter: YAML front-matter
      - markdown_body: nội dung markdown (không có front-matter)
      - content_hash: hash của markdown_body
      - full_markdown: toàn bộ nội dung file (front-matter + body + Article URL)
    """
    title = article.get('title', 'Untitled')
    body_html = article.get('body', '')
    article_id = article.get('id')
    html_url = article.get('html_url', '')
    updated_at = article.get('updated_at', '')
    section_id = article.get('section_id', '')

    # Chuyển HTML -> Markdown
    markdown_body = html_to_markdown(body_html)
    
    # Tính hash
    content_hash = compute_content_hash(markdown_body)
    
    # Tạo slug
    slug = generate_slug(title)
    # Đảm bảo slug không bị trùng (có thể thêm id nếu trùng, nhưng tạm thời dùng slug)
    # Nếu slug rỗng, dùng article_id
    if not slug:
        slug = str(article_id)
    
    # Front-matter YAML
    front_matter = f"""---
article_id: {article_id}
title: "{title}"
url: "{html_url}"
section: "{section_id}"
updated_at: "{updated_at}"
content_hash: "{content_hash}"
---
"""
    # Dòng Article URL ở cuối
    article_url_line = f"\n\nArticle URL: {html_url}"
    
    full_markdown = front_matter + markdown_body + article_url_line
    
    return {
        'slug': slug,
        'front_matter': front_matter,
        'markdown_body': markdown_body,
        'content_hash': content_hash,
        'full_markdown': full_markdown,
        'article_id': article_id,
        'html_url': html_url
    }

def save_article_markdown(converted: Dict[str, Any], output_dir: str = "data/articles"):
    """
    Lưu markdown vào file.
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{converted['slug']}.md"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(converted['full_markdown'])
    return filepath