import json
import os
from loguru import logger
from apis.xhs_pc_apis import XHS_Apis
from xhs_utils.common_util import init
from xhs_utils.data_util import handle_note_info, download_note, save_to_xlsx


class Data_Spider():
    def __init__(self):
        self.xhs_apis = XHS_Apis()

    @staticmethod
    def _apply_rate_limit(rate_limiter):
        if rate_limiter is not None:
            rate_limiter.wait()

    @staticmethod
    def _emit_progress(callback, message):
        if callback is not None:
            try:
                callback(message)
            except Exception:
                pass

    def spider_note(self, note_url: str, cookies_str: str, proxies=None, rate_limiter=None):
        """
        爬取一个笔记的信息
        :param note_url:
        :param cookies_str:
        :return:
        """
        note_info = None
        try:
            self._apply_rate_limit(rate_limiter)
            success, msg, res_json = self.xhs_apis.get_note_info(note_url, cookies_str, proxies)
            if success:
                try:
                    items = res_json.get('data', {}).get('items', [])
                except Exception:
                    items = []
                if not items:
                    success = False
                    msg = "笔记详情为空，可能 token 无效或权限受限"
                else:
                    note_info = items[0]
                    note_info['url'] = note_url
                    note_info = handle_note_info(note_info)
        except Exception as e:
            success = False
            msg = e
        logger.info(f'爬取笔记信息 {note_url}: {success}, msg: {msg}')
        return success, msg, note_info

    def spider_some_note(self, notes: list, cookies_str: str, base_path: dict, save_choice: str, excel_name: str = '', proxies=None, rate_limiter=None, progress_callback=None, max_notes: int | None = None):
        """
        爬取一些笔记的信息
        :param notes:
        :param cookies_str:
        :param base_path:
        :return:
        """
        if (save_choice == 'all' or save_choice == 'excel') and excel_name == '':
            raise ValueError('excel_name 不能为空')
        if max_notes and max_notes > 0:
            notes = notes[:max_notes]
        note_list = []
        total = len(notes)
        for idx, note_url in enumerate(notes, start=1):
            success, msg, note_info = self.spider_note(note_url, cookies_str, proxies, rate_limiter)
            title = None
            if note_info is not None:
                title = note_info.get('title', '无标题') or '无标题'
            display_title = title or '无标题'
            if note_info is not None and success:
                note_list.append(note_info)
                self._emit_progress(progress_callback, f"[{idx}/{total}] {display_title}")
            else:
                self._emit_progress(progress_callback, f"[{idx}/{total}] 下载失败: {msg}")
        for note_info in note_list:
            if save_choice == 'all' or 'media' in save_choice:
                download_note(note_info, base_path['media'], save_choice)
        if save_choice == 'all' or save_choice == 'excel':
            file_path = os.path.abspath(os.path.join(base_path['excel'], f'{excel_name}.xlsx'))
            save_to_xlsx(note_list, file_path)


    def spider_user_all_note(self, user_url: str, cookies_str: str, base_path: dict, save_choice: str, excel_name: str = '', proxies=None, rate_limiter=None, progress_callback=None):
        """
        爬取一个用户的所有笔记
        :param user_url:
        :param cookies_str:
        :param base_path:
        :return:
        """
        note_list = []
        try:
            self._apply_rate_limit(rate_limiter)
            success, msg, all_note_info = self.xhs_apis.get_user_all_notes(user_url, cookies_str, proxies)
            if success:
                logger.info(f'用户 {user_url} 作品数量: {len(all_note_info)}')
                for simple_note_info in all_note_info:
                    note_url = f"https://www.xiaohongshu.com/explore/{simple_note_info['note_id']}?xsec_token={simple_note_info['xsec_token']}"
                    note_list.append(note_url)
            if save_choice == 'all' or save_choice == 'excel':
                excel_name = user_url.split('/')[-1].split('?')[0]
            self._emit_progress(progress_callback, f"用户任务共 {len(note_list)} 条，开始下载…")
            self.spider_some_note(note_list, cookies_str, base_path, save_choice, excel_name, proxies, rate_limiter, progress_callback)
        except Exception as e:
            success = False
            msg = e
        logger.info(f'爬取用户所有视频 {user_url}: {success}, msg: {msg}')
        return note_list, success, msg

    def spider_user_all_note_selenium(self, user_url: str, cookies_str: str, base_path: dict, save_choice: str, excel_name: str = '', proxies=None, rate_limiter=None, progress_callback=None, max_notes: int | None = None, max_scroll_times: int | None = None):
        """
        使用 Selenium 爬取一个用户的所有笔记，仅影响用户采集模块，其他模块仍走原有 API 方案。
        该模式下直接解析页面 HTML 获取笔记信息，不再依赖 /feed 接口；为降低风险，不下载视频文件。
        """
        try:
            # 使用 Selenium 获取每条笔记的完整详情页 URL（包含 token），然后复用原有 feed 解析逻辑，保持数据结构一致。
            from xhs_utils.selenium_user_spider import get_user_note_links_with_selenium
        except ImportError as e:
            logger.error(f"导入 Selenium 用户采集模块失败: {e}")
            raise

        note_urls: list[str] = []
        success = True
        msg = ""
        try:
            self._apply_rate_limit(rate_limiter)
            all_urls = get_user_note_links_with_selenium(
                user_url,
                cookies_str,
                max_scroll_times=max_scroll_times or 0,
                proxies=proxies,
            )
            if max_notes and max_notes > 0:
                note_urls = all_urls[:max_notes]
            else:
                note_urls = all_urls

            if not note_urls:
                success = False
                msg = "未从用户主页获取到任何笔记链接"
                logger.error(f"Selenium URL 模式未获取到笔记链接: {user_url}")
            else:
                logger.info(f"Selenium URL 模式采集，用户 {user_url} 链接数量: {len(note_urls)}")

            if save_choice == 'all' or save_choice == 'excel':
                excel_name = user_url.split('/')[-1].split('?')[0]

            self._emit_progress(progress_callback, f"Selenium 用户任务共 {len(note_urls)} 条，开始下载…（仅图片，不含视频文件）")

            # 强制只下载图片，避免视频请求
            media_save_choice = 'media-image' if save_choice in ('all', 'media', 'media-image') else save_choice
            if note_urls:
                self.spider_some_note(
                    note_urls,
                    cookies_str,
                    base_path,
                    media_save_choice,
                    excel_name,
                    proxies,
                    rate_limiter,
                    progress_callback,
                    max_notes=max_notes,
                )
        except Exception as e:
            success = False
            msg = e
            logger.error(f"Selenium 爬取用户所有笔记执行异常 (URL 模式) {user_url}: {e}")
        logger.info(f'Selenium 爬取用户所有笔记 (URL 模式) {user_url}: {success}, msg: {msg}')
        return note_urls, success, msg

    def spider_some_search_note(self, query: str, require_num: int, cookies_str: str, base_path: dict, save_choice: str, sort_type_choice=0, note_type=0, note_time=0, note_range=0, pos_distance=0, geo: dict = None,  excel_name: str = '', proxies=None, rate_limiter=None, progress_callback=None):
        """
            指定数量搜索笔记，设置排序方式和笔记类型和笔记数量
            :param query 搜索的关键词
            :param require_num 搜索的数量
            :param cookies_str 你的cookies
            :param base_path 保存路径
            :param sort_type_choice 排序方式 0 综合排序, 1 最新, 2 最多点赞, 3 最多评论, 4 最多收藏
            :param note_type 笔记类型 0 不限, 1 视频笔记, 2 普通笔记
            :param note_time 笔记时间 0 不限, 1 一天内, 2 一周内天, 3 半年内
            :param note_range 笔记范围 0 不限, 1 已看过, 2 未看过, 3 已关注
            :param pos_distance 位置距离 0 不限, 1 同城, 2 附近 指定这个必须要指定 geo
            返回搜索的结果
        """
        note_list = []
        try:
            self._apply_rate_limit(rate_limiter)
            success, msg, notes = self.xhs_apis.search_some_note(query, require_num, cookies_str, sort_type_choice, note_type, note_time, note_range, pos_distance, geo, proxies)
            if success:
                notes = list(filter(lambda x: x['model_type'] == "note", notes))
                logger.info(f'搜索关键词 {query} 笔记数量: {len(notes)}')
                for note in notes:
                    note_url = f"https://www.xiaohongshu.com/explore/{note['id']}?xsec_token={note['xsec_token']}"
                    note_list.append(note_url)
            if save_choice == 'all' or save_choice == 'excel':
                excel_name = query
            self._emit_progress(progress_callback, f"搜索结果共 {len(note_list)} 条，开始下载…")
            self.spider_some_note(note_list, cookies_str, base_path, save_choice, excel_name, proxies, rate_limiter, progress_callback)
        except Exception as e:
            success = False
            msg = e
        logger.info(f'搜索关键词 {query} 笔记: {success}, msg: {msg}')
        return note_list, success, msg

if __name__ == '__main__':
    """
        此文件为爬虫的入口文件，可以直接运行。
        直接执行 main.py 时，将优先读取 GUI 的 gui_settings.json 配置，
        并询问你使用哪种模式：批量笔记 / 用户全集 (Selenium) / 搜索下载。
        apis/xhs_pc_apis.py 为爬虫的 api 文件，包含小红书的全部数据接口。
        apis/xhs_creator_apis.py 为小红书创作者中心的 api 文件。
    """
    from gui_app.config_manager import ConfigManager
    from gui_app.rate_limiter import RateLimiter

    config_manager = ConfigManager()
    cookies_str, base_path = config_manager.reload()
    if not cookies_str:
        print("未在 .env 中找到 COOKIES，请先在 GUI 或 .env 中配置后再运行 main.py。")
        raise SystemExit(1)

    settings = config_manager.load_gui_settings()

    # 全局代理
    proxy_raw = (settings.get('proxy') or '').strip()
    proxies = {'http': proxy_raw, 'https': proxy_raw} if proxy_raw else None

    # 全局频率限制
    max_per_window = int(settings.get('max_per_window', 0) or 0)
    try:
        min_interval = float(settings.get('min_interval', 0.0) or 0.0)
    except Exception:
        min_interval = 0.0
    rate_limiter = None
    if max_per_window > 0 or min_interval > 0:
        rate_limiter = RateLimiter(max_per_window or None, window_seconds=600, min_interval=min_interval)

    # 全局笔记数量上限
    max_notes_cfg = int(settings.get('max_notes', 0) or 0)
    max_notes = max_notes_cfg if max_notes_cfg > 0 else None

    data_spider = Data_Spider()

    def progress(msg: str) -> None:
        try:
            print(msg)
        except Exception:
            pass

    def run_batch_notes() -> None:
        raw = settings.get('note_urls', '').strip()
        if not raw:
            print("GUI 配置中没有批量笔记链接，请在 gui_settings.json 或 GUI 中先配置。")
            return
        note_urls = [line.strip() for line in raw.splitlines() if line.strip()]
        save_choice = settings.get('note_save_choice', 'all') or 'all'
        excel_name = settings.get('note_excel_name', 'notes') or 'notes'
        data_spider.spider_some_note(
            note_urls, cookies_str, base_path, save_choice, excel_name, proxies, rate_limiter, progress, max_notes=max_notes
        )

    def run_user_all_selenium() -> None:
        user_url = (settings.get('user_url') or '').strip()
        if not user_url:
            user_url = input("请输入用户主页 URL: ").strip()
        if not user_url:
            print("用户主页 URL 为空，已取消。")
            return
        save_choice = settings.get('user_save_choice', 'all') or 'all'
        excel_name = settings.get('user_excel_name', '') or ''
        scroll_times = int(settings.get('user_scroll_times', 0) or 0)
        data_spider.spider_user_all_note_selenium(
            user_url,
            cookies_str,
            base_path,
            save_choice,
            excel_name,
            proxies,
            rate_limiter,
            progress,
            max_notes=max_notes,
            max_scroll_times=scroll_times or None,
        )

    def run_search() -> None:
        query = (settings.get('search_query') or '').strip()
        if not query:
            query = input("请输入搜索关键词: ").strip()
        if not query:
            print("搜索关键词为空，已取消。")
            return

        try:
            query_num = int(settings.get('search_query_num', 10) or 10)
        except Exception:
            query_num = 10
        if max_notes is not None and query_num > max_notes:
            query_num = max_notes

        save_choice = settings.get('search_save_choice', 'all') or 'all'

        # 映射 GUI 文本到内部枚举
        sort_label = settings.get('search_sort', '综合排序')
        sort_options = {'综合排序': 0, '最新': 1, '最多点赞': 2, '最多评论': 3, '最多收藏': 4}
        sort_type_choice = sort_options.get(sort_label, 0)

        note_type_label = settings.get('search_note_type', '不限')
        note_type_options = {'不限': 0, '视频笔记': 1, '普通笔记': 2}
        note_type = note_type_options.get(note_type_label, 0)

        note_time_label = settings.get('search_note_time', '不限')
        note_time_options = {'不限': 0, '一天内': 1, '一周内': 2, '半年内': 3}
        note_time = note_time_options.get(note_time_label, 0)

        note_range_label = settings.get('search_note_range', '不限')
        note_range_options = {'不限': 0, '已看过': 1, '未看过': 2, '已关注': 3}
        note_range = note_range_options.get(note_range_label, 0)

        pos_label = settings.get('search_pos_distance', '不限')
        pos_distance_options = {'不限': 0, '同城': 1, '附近': 2}
        pos_distance = pos_distance_options.get(pos_label, 0)

        geo = None
        lat_raw = (settings.get('search_geo_lat') or '').strip()
        lng_raw = (settings.get('search_geo_lng') or '').strip()
        if lat_raw or lng_raw:
            try:
                geo = {'latitude': float(lat_raw), 'longitude': float(lng_raw)}
            except Exception:
                print("GUI 配置中的 Geo 坐标无效，将忽略 Geo。")
                geo = None

        data_spider.spider_some_search_note(
            query,
            query_num,
            cookies_str,
            base_path,
            save_choice,
            sort_type_choice,
            note_type,
            note_time,
            note_range,
            pos_distance,
            geo=geo,
            proxies=proxies,
            rate_limiter=rate_limiter,
            progress_callback=progress,
        )

    while True:
        print("\n请选择运行模式：")
        print("1. 批量笔记 (使用 GUI 配置的笔记链接)")
        print("2. 用户全集 (Selenium 模式，使用 GUI 配置的用户 URL)")
        print("3. 搜索下载 (使用 GUI 配置的搜索条件)")
        print("0. 退出")
        choice = input("输入序号并回车: ").strip()

        if choice == '1':
            run_batch_notes()
        elif choice == '2':
            run_user_all_selenium()
        elif choice == '3':
            run_search()
        elif choice in ('0', 'q', 'Q'):
            break
        else:
            print("无效选择，请重新输入。")
