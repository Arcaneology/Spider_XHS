import os
import re
import urllib.parse
from typing import List, Tuple

import requests
from loguru import logger

# 兼容从项目根目录或 example 目录运行脚本时的导入路径
try:
    from xhs_utils.cookie_util import trans_cookies
    from xhs_utils.xhs_util import get_common_headers
except ModuleNotFoundError:
    import sys

    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from xhs_utils.cookie_util import trans_cookies
    from xhs_utils.xhs_util import get_common_headers


def load_url_and_cookie(txt_path: str) -> Tuple[str, str]:
    """
    从示例 txt 文件中读取用户主页 URL 和 Cookie。
    Read user profile URL and Cookie from the example txt file.
    """
    if not os.path.isfile(txt_path):
        raise FileNotFoundError(f"示例文件不存在: {txt_path}")

    with open(txt_path, "r", encoding="utf-8") as f:
        content = f.read()

    url_match = re.search(r'URL:"([^"]+)"', content)
    cookie_match = re.search(r'Cookie:"([^"]+)"', content)

    if not url_match:
        raise ValueError("示例文件中未找到 URL 字段")
    if not cookie_match:
        raise ValueError("示例文件中未找到 Cookie 字段")

    url = url_match.group(1).strip()
    cookie_str = cookie_match.group(1).strip()

    # 允许在 txt 中额外指定 NoteQuery:"xsec_token=...&xsec_source=pc_user"
    logger.info(f"从示例文件读取到 URL: {url}")
    return url, cookie_str


def extract_note_urls_from_html(html: str) -> List[str]:
    """
    从用户主页 HTML 中提取所有笔记链接。
    尽量保留页面中已有的 query（如果存在 xsec_token 则直接复用），
    不再尝试拼接统一的 token/query。

    Extract all note URLs from user profile HTML.
    Prefer using note_id + xsec_token pairs if present.
    """
    note_urls = set()

    # 绝对链接
    for match in re.findall(r'https://www\\.xiaohongshu\\.com/explore/[0-9a-zA-Z]+[^"\\s"]*', html):
        note_urls.add(match)

    # 相对链接 /explore/xxx
    for match in re.findall(r'href="(/explore/[^"\\s]*)"', html):
        full = urllib.parse.urljoin("https://www.xiaohongshu.com", match)
        note_urls.add(full)

    return sorted(note_urls)


def fetch_profile_html(url: str, cookie_str: str) -> str:
    """
    使用给定的 URL 和 Cookie 请求用户主页 HTML。
    Fetch user profile HTML using given URL and Cookie.
    """
    headers = get_common_headers()
    cookies = trans_cookies(cookie_str)

    logger.info("开始请求用户主页 HTML…")
    resp = requests.get(url, headers=headers, cookies=cookies, timeout=15)
    logger.info(f"请求完成，status_code={resp.status_code}")

    resp.raise_for_status()
    return resp.text


def main():
    """
    简单调试脚本：
    - 从 example/用户全集.txt 中读取 URL 和 Cookie
    - 请求用户主页 HTML
    - 提取所有 /explore/ 笔记链接并打印

    Simple debug script:
    - Read URL and Cookie from example/用户全集.txt
    - Fetch user profile HTML
    - Extract all /explore/ note URLs and print them
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    txt_path = os.path.join(base_dir, "用户全集.txt")

    url, cookie_str = load_url_and_cookie(txt_path)

    try:
        html = fetch_profile_html(url, cookie_str)
    except Exception as e:
        logger.error(f"请求用户主页失败: {e}")
        return

    note_urls = extract_note_urls_from_html(html)
    logger.info(f"共提取到 {len(note_urls)} 条笔记链接（不包含统一 xsec_token，仅用于调试 note_id）")

    for u in note_urls:
        print(u)


if __name__ == "__main__":
    main()
