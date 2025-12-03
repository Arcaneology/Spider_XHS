import os
import time
import urllib.parse
from typing import List, Set, Dict, Any

from loguru import logger

from xhs_utils.cookie_util import trans_cookies


def _build_chrome_driver(proxies: dict | None = None):
    """
    创建一个 Chrome WebDriver，并根据需要配置代理。
    使用 webdriver-manager 自动管理驱动版本，减少环境差异。
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError as e:
        raise ImportError("selenium 或 webdriver-manager 未安装，请先运行: "
                          "pip install selenium webdriver-manager") from e

    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    # 降低浏览器日志噪音，并允许使用 SwiftShader 以减少 WebGL 相关警告
    options.add_argument("--log-level=3")
    options.add_argument("--disable-logging")
    options.add_argument("--enable-unsafe-swiftshader")

    # 默认使用无头模式，方便批量采集；如需可视化调试，可以设置环境变量关闭
    headless_flag = os.getenv("XHS_SELENIUM_HEADLESS", "1")
    if headless_flag != "0":
        options.add_argument("--headless=new")

    if proxies and isinstance(proxies, dict):
        http_proxy = proxies.get("http") or proxies.get("https")
        if http_proxy:
            options.add_argument(f"--proxy-server={http_proxy}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    driver.set_script_timeout(30)
    return driver


def _inject_cookies(driver, cookies_str: str):
    """
    将项目中使用的 cookies 字符串注入到浏览器中，复用现有登录状态。
    """
    cookies = trans_cookies(cookies_str)
    for name, value in cookies.items():
        try:
            driver.add_cookie(
                {
                    "name": name,
                    "value": value,
                    "domain": ".xiaohongshu.com",
                    "path": "/",
                }
            )
        except Exception as e:
            logger.warning(f"注入 cookie 失败: {name}, error={e}")


def get_user_note_links_with_selenium(
    user_url: str,
    cookies_str: str,
    max_scroll_times: int = 30,
    scroll_pause: float = 1.5,
    proxies: dict | None = None,
) -> List[str]:
    """
    使用 Selenium 打开用户主页并下拉，提取所有笔记链接。
    仅用于用户全集采集，不影响其他模块。
    """
    try:
        from selenium.webdriver.common.by import By
    except ImportError as e:
        raise ImportError("selenium 未安装，请先运行: pip install selenium") from e

    driver = _build_chrome_driver(proxies)
    note_links: Set[str] = set()

    try:
        logger.info("Selenium 打开小红书首页，准备注入 Cookie")
        driver.get("https://www.xiaohongshu.com/")
        _inject_cookies(driver, cookies_str)

        driver.get(user_url)
        logger.info(f"Selenium 打开用户主页: {user_url}")

        profile_handle = driver.current_window_handle
        processed_hrefs: Set[str] = set()

        last_height = 0
        stable_rounds = 0
        # 0 或以下表示不限次，由页面高度稳定来结束循环
        unlimited_scroll = not max_scroll_times or max_scroll_times <= 0
        scroll_count = 0

        while True:
            scroll_count += 1
            time.sleep(scroll_pause)

            anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='/explore/']")
            new_hrefs = []
            for a in anchors:
                href = a.get_attribute("href")
                if href and "/explore/" in href and href not in processed_hrefs:
                    processed_hrefs.add(href)
                    new_hrefs.append(href)

            # 逐个打开新标签，获取带 token 的完整 URL，然后关闭标签返回用户主页
            for href in new_hrefs:
                try:
                    driver.execute_script("window.open(arguments[0], '_blank');", href)
                    time.sleep(scroll_pause)
                    handles = driver.window_handles
                    if len(handles) <= 1:
                        continue
                    detail_handle = [h for h in handles if h != profile_handle][-1]
                    driver.switch_to.window(detail_handle)
                    time.sleep(scroll_pause)
                    full_url = driver.current_url or ""
                    if "/explore/" in full_url:
                        note_links.add(full_url)
                except Exception as e:
                    logger.warning(f"Selenium 打开笔记详情失败: href={href}, error={e}")
                finally:
                    try:
                        if driver.current_window_handle != profile_handle:
                            driver.close()
                            driver.switch_to.window(profile_handle)
                    except Exception:
                        try:
                            driver.switch_to.window(profile_handle)
                        except Exception:
                            pass

            logger.info(f"第 {scroll_count} 次滚动，当前已提取笔记链接数量: {len(note_links)}")

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)
            new_height = driver.execute_script("return document.body.scrollHeight") or 0

            if new_height == last_height:
                stable_rounds += 1
            else:
                stable_rounds = 0
            last_height = new_height

            if stable_rounds >= 2:
                logger.info("页面高度不再变化，多次滚动无新内容，停止下拉")
                break

            if not unlimited_scroll and scroll_count >= max_scroll_times:
                logger.info(f"已达到配置的最大下拉次数 {max_scroll_times}，停止下拉")
                break

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    return sorted(note_links)


def get_user_notes_with_selenium(
    user_url: str,
    cookies_str: str,
    max_scroll_times: int = 30,
    scroll_pause: float = 2.0,
    proxies: dict | None = None,
    max_notes: int | None = None,
) -> List[Dict[str, Any]]:
    """
    使用 Selenium 打开用户主页，逐条打开笔记详情页，并直接从 HTML 中提取笔记信息。
    仅用于用户全集采集，避免依赖 /feed 接口和 token。
    """
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError as e:
        raise ImportError("selenium 未安装，请先运行: pip install selenium") from e

    driver = _build_chrome_driver(proxies)
    note_infos: List[Dict[str, Any]] = []

    def _extract_note_from_page() -> Dict[str, Any]:
        """
        在当前详情页中执行 JS，尽量从 DOM 中提取笔记信息。
        """
        script = """
        (function() {
            var data = {};
            try {
                data.url = window.location.href || '';
                var path = window.location.pathname || '';
                var m = path.match(/\\/explore\\/([0-9a-zA-Z]+)/);
                data.note_id = m ? m[1] : '';

                var title = '';
                var h1 = document.querySelector('h1');
                if (h1) { title = h1.innerText || h1.textContent || ''; }
                data.title = title;

                var nickname = '';
                var userLink = document.querySelector('a[href*="/user/profile/"]');
                if (userLink) { nickname = userLink.innerText || userLink.textContent || ''; }
                data.nickname = nickname;
                data.home_url = userLink ? (userLink.href || '') : '';

                // 简单提取正文作为描述
                var desc = '';
                var article = document.querySelector('article');
                if (!article) {
                    article = document.querySelector('[class*="content"],[class*="Content"]');
                }
                if (article) { desc = article.innerText || article.textContent || ''; }
                data.desc = desc;

                // 收集页面上的图片，尽量过滤头像类图片
                var imgs = Array.prototype.slice.call(document.querySelectorAll('img'));
                var imageUrls = [];
                imgs.forEach(function(img) {
                    var src = img.getAttribute('src') || img.getAttribute('data-src') || '';
                    if (!src) return;
                    // 粗略过滤头像等非内容图片
                    if (src.indexOf('avatar') !== -1 || src.indexOf('profile') !== -1) return;
                    if (imageUrls.indexOf(src) === -1) {
                        imageUrls.push(src);
                    }
                });
                data.image_list = imageUrls;

                // 判断是否为视频笔记（页面存在 <video> 即视为视频）
                var hasVideo = !!document.querySelector('video');
                data.note_type = hasVideo ? '视频' : '图集';

                // 点赞/收藏/评论/分享等数量如果不好直接拿，就先置为 0
                data.liked_count = 0;
                data.collected_count = 0;
                data.comment_count = 0;
                data.share_count = 0;

                // 标签和 IP 归属地暂时留空/未知
                data.tags = [];
                data.ip_location = '未知';

                // 上传时间暂时留空，由前端渲染为字符串，不易稳定解析
                data.upload_time = '';
            } catch (e) {
                data.error = String(e);
            }
            return data;
        })();
        """
        raw = driver.execute_script(script)
        return raw or {}

    try:
        logger.info("Selenium 打开小红书首页，准备注入 Cookie (HTML 模式)")
        driver.get("https://www.xiaohongshu.com/")
        _inject_cookies(driver, cookies_str)

        driver.get(user_url)
        logger.info(f"Selenium 打开用户主页 (HTML 模式): {user_url}")

        wait = WebDriverWait(driver, 30)

        # 等待首屏至少有一条 explore 链接出现
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/explore/']")))
        except Exception:
            logger.warning("用户主页未检测到任何 /explore/ 链接，可能需要检查 Cookies 或页面结构")

        collected_hrefs: List[str] = []
        seen_hrefs: Set[str] = set()

        last_height = 0
        stable_rounds = 0
        unlimited_scroll = not max_scroll_times or max_scroll_times <= 0
        scroll_count = 0

        while True:
            scroll_count += 1
            time.sleep(scroll_pause)

            anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='/explore/']")
            logger.info(f"第 {scroll_count} 次滚动前，检测到 explore 链接数量: {len(anchors)}")
            for a in anchors:
                href = a.get_attribute("href")
                if href and "/explore/" in href and href not in seen_hrefs:
                    seen_hrefs.add(href)
                    collected_hrefs.append(href)

            if max_notes is not None and len(collected_hrefs) >= max_notes:
                logger.info(f"已从列表收集到 {len(collected_hrefs)} 条链接，达到最大笔记数量 {max_notes}")
                break

            logger.info(f"第 {scroll_count} 次滚动 (HTML 模式)，当前收集到的链接数量: {len(collected_hrefs)}")

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)
            new_height = driver.execute_script("return document.body.scrollHeight") or 0

            if new_height == last_height:
                stable_rounds += 1
            else:
                stable_rounds = 0
            last_height = new_height

            if stable_rounds >= 2:
                logger.info("页面高度不再变化，多次滚动无新内容，停止下拉 (HTML 模式)")
                break

            if not unlimited_scroll and scroll_count >= max_scroll_times:
                logger.info(f"已达到配置的最大下拉次数 {max_scroll_times}，停止下拉 (HTML 模式)")
                break

        # 根据收集到的链接逐条打开详情页解析内容
        for href in collected_hrefs:
            if max_notes is not None and len(note_infos) >= max_notes:
                break
            try:
                driver.get(href)
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
                except Exception:
                    pass
                time.sleep(scroll_pause)
                data = _extract_note_from_page()
                if not data or not data.get("note_id"):
                    continue

                # 补全字段，尽量与 handle_note_info 结构对齐
                data["note_url"] = data.get("url", "")
                home_url = data.get("home_url") or ""
                user_id = ""
                try:
                    parsed = urllib.parse.urlparse(home_url)
                    user_id = parsed.path.rstrip("/").split("/")[-1]
                except Exception:
                    user_id = ""
                data["user_id"] = user_id
                data["avatar"] = data.get("avatar", "")
                data.setdefault("video_cover", None)
                data.setdefault("video_addr", None)
                data.setdefault("tags", [])
                data.setdefault("upload_time", data.get("upload_time", ""))

                note_infos.append(data)
                logger.info(f"Selenium 已解析笔记 {data.get('note_id')}，当前累计数量: {len(note_infos)}")
            except Exception as e:
                logger.warning(f"Selenium 打开笔记详情失败 (HTML 模式): href={href}, error={e}")

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    return note_infos
