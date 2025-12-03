import threading
from typing import Callable, Dict, List, Optional

from gui_app.rate_limiter import RateLimiter
from main import Data_Spider


class SpiderController:
    """Thin controller that executes crawler actions in background threads."""

    def __init__(self, log_callback: Callable[[str], None]) -> None:
        self.log_callback = log_callback
        self.spider = Data_Spider()
        self._worker: Optional[threading.Thread] = None

    def is_busy(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def run_notes_task(
        self,
        note_urls: List[str],
        cookies: str,
        base_paths: Dict[str, str],
        save_choice: str,
        excel_name: str,
        proxies: Optional[Dict[str, str]] = None,
        rate_limiter: Optional[RateLimiter] = None,
        max_notes: Optional[int] = None,
    ) -> bool:
        return self._start_task(
            '批量笔记任务',
            lambda: self.spider.spider_some_note(
                note_urls,
                cookies,
                base_paths,
                save_choice,
                excel_name,
                proxies,
                rate_limiter,
                self.log_callback,
                max_notes=max_notes,
            ),
        )

    def run_user_task(
        self,
        user_url: str,
        cookies: str,
        base_paths: Dict[str, str],
        save_choice: str,
        excel_name: str,
        proxies: Optional[Dict[str, str]] = None,
        rate_limiter: Optional[RateLimiter] = None,
        scroll_times: Optional[int] = None,
        max_notes: Optional[int] = None,
    ) -> bool:
        return self._start_task(
            '用户全集任务 (Selenium 模式)',
            lambda: self.spider.spider_user_all_note_selenium(
                user_url,
                cookies,
                base_paths,
                save_choice,
                excel_name,
                proxies,
                rate_limiter,
                self.log_callback,
                max_notes=max_notes,
                max_scroll_times=scroll_times,
            ),
        )

    def run_search_task(
        self,
        query: str,
        query_num: int,
        cookies: str,
        base_paths: Dict[str, str],
        save_choice: str,
        sort_type: int,
        note_type: int,
        note_time: int,
        note_range: int,
        pos_distance: int,
        geo: Optional[Dict[str, float]],
        proxies: Optional[Dict[str, str]] = None,
        rate_limiter: Optional[RateLimiter] = None,
        max_notes: Optional[int] = None,
    ) -> bool:
        effective_num = query_num
        if max_notes and max_notes > 0:
            effective_num = min(query_num, max_notes)

        return self._start_task(
            '搜索任务',
            lambda: self.spider.spider_some_search_note(
                query,
                effective_num,
                cookies,
                base_paths,
                save_choice,
                sort_type,
                note_type,
                note_time,
                note_range,
                pos_distance,
                geo,
                excel_name='',
                proxies=proxies,
                rate_limiter=rate_limiter,
                progress_callback=self.log_callback,
            ),
        )

    def _start_task(self, description: str, task: Callable[[], None]) -> bool:
        if self.is_busy():
            self.log_callback('已有任务在执行，请等待完成后再试。')
            return False

        def runner() -> None:
            try:
                self.log_callback(f'{description}开始执行...')
                task()
                self.log_callback(f'{description}执行完成。')
            except Exception as exc:  # pragma: no cover - surfaced给用户
                self.log_callback(f'{description}失败: {exc}')
            finally:
                self._worker = None

        self._worker = threading.Thread(target=runner, daemon=True)
        self._worker.start()
        return True

