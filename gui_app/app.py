import tkinter as tk

from tkinter import ttk, filedialog, messagebox

from tkinter.scrolledtext import ScrolledText

from queue import Empty, Queue

from typing import Dict, Optional



from gui_app.config_manager import ConfigManager

from gui_app.controller import SpiderController

from gui_app.rate_limiter import RateLimiter





class SpiderGUI(tk.Tk):

    def __init__(self) -> None:

        super().__init__()

        self.title('Spider XHS GUI')

        self.geometry('900x700')

        self.minsize(860, 640)



        self.config_manager = ConfigManager()

        self.log_queue: "Queue[str]" = Queue()

        self.controller = SpiderController(self._enqueue_log)



        self.cookies_text: ScrolledText
        self.media_var = tk.StringVar()
        self.excel_var = tk.StringVar()
        self.proxy_var = tk.StringVar()
        self.max_per_window_var = tk.IntVar(value=60)
        self.min_interval_var = tk.DoubleVar(value=2.0)
        # 全局笔记数量上限 (0 为不限)
        self.max_notes_var = tk.IntVar(value=0)


        self.save_choices = ('all', 'media', 'media-video', 'media-image', 'excel')

        self.sort_options = {

            '综合排序': 0,

            '最新': 1,

            '最多点赞': 2,

            '最多评论': 3,

            '最多收藏': 4,

        }

        self.note_type_options = {'不限': 0, '视频笔记': 1, '普通笔记': 2}

        self.note_time_options = {'不限': 0, '一天内': 1, '一周内': 2, '半年内': 3}

        self.note_range_options = {'不限': 0, '已看过': 1, '未看过': 2, '已关注': 3}

        self.pos_distance_options = {'不限': 0, '同城': 1, '附近': 2}



        self._build_layout()

        self._load_defaults()

        self.after(200, self._poll_log_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)



    # Layout helpers -----------------------------------------------------

    def _build_layout(self) -> None:

        self._build_settings_frame()

        self._build_notebook()

        self._build_log_section()



    def _build_settings_frame(self) -> None:
        frame = ttk.LabelFrame(self, text='全局配置 (.env 默认值可在此修改)')
        frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(frame, text='Cookies').grid(row=0, column=0, sticky=tk.NW, padx=5, pady=5)
        self.cookies_text = ScrolledText(frame, height=3)
        self.cookies_text.grid(row=0, column=1, columnspan=3, sticky=tk.EW, padx=5, pady=5)

        ttk.Button(frame, text='读取 Cookies', command=self._reload_defaults).grid(row=0, column=4, sticky=tk.NE, padx=5, pady=5)
        ttk.Button(frame, text='保存 Cookies', command=self._save_cookies_to_env).grid(row=0, column=5, sticky=tk.NE, padx=5, pady=5)

        ttk.Label(frame, text='媒体输出目录（下载的图片/视频保存位置）').grid(row=1, column=0, columnspan=6, sticky=tk.W, padx=5, pady=(10, 0))
        ttk.Entry(frame, textvariable=self.media_var).grid(row=2, column=0, columnspan=5, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(frame, text='浏览', command=lambda: self._select_directory(self.media_var)).grid(row=2, column=5, padx=5, pady=5)

        ttk.Label(frame, text='Excel报表目录（生成的 Excel 保存位置）').grid(row=3, column=0, columnspan=6, sticky=tk.W, padx=5, pady=(10, 0))
        ttk.Entry(frame, textvariable=self.excel_var).grid(row=4, column=0, columnspan=5, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(frame, text='浏览', command=lambda: self._select_directory(self.excel_var)).grid(row=4, column=5, padx=5, pady=5)

        ttk.Label(frame, text='代理 (可选，例如 http://user:pass@host:port)').grid(row=5, column=0, columnspan=6, sticky=tk.W, padx=5, pady=(10, 0))
        ttk.Entry(frame, textvariable=self.proxy_var).grid(row=6, column=0, columnspan=6, sticky=tk.EW, padx=5, pady=5)

        ttk.Label(frame, text='频率限制 (控制每10分钟的最大请求数与最小间隔)').grid(row=7, column=0, columnspan=6, sticky=tk.W, padx=5, pady=(10, 0))
        ttk.Label(frame, text='每10分钟最多请求数 (0 表示不限)').grid(row=8, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Spinbox(frame, from_=0, to=600, textvariable=self.max_per_window_var, width=10).grid(row=8, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(frame, text='最小请求间隔/秒 (0 表示不限)').grid(row=8, column=2, sticky=tk.W, padx=5, pady=5)
        ttk.Spinbox(frame, from_=0, to=60, increment=0.5, textvariable=self.min_interval_var, width=10).grid(row=8, column=3, sticky=tk.W, padx=5, pady=5)
        ttk.Label(frame, text='笔记最大爬取数量 (0 表示不限)').grid(row=9, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Spinbox(frame, from_=0, to=100000, textvariable=self.max_notes_var, width=10).grid(row=9, column=1, sticky=tk.W, padx=5, pady=5)

        for idx in range(6):
            frame.columnconfigure(idx, weight=1)

    def _build_notebook(self) -> None:

        notebook = ttk.Notebook(self)

        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)



        self.note_tab = ttk.Frame(notebook)

        self.user_tab = ttk.Frame(notebook)

        self.search_tab = ttk.Frame(notebook)



        notebook.add(self.note_tab, text='批量笔记')

        notebook.add(self.user_tab, text='用户全集')

        notebook.add(self.search_tab, text='搜索下载')



        self._build_note_tab()

        self._build_user_tab()

        self._build_search_tab()



    def _build_note_tab(self) -> None:

        ttk.Label(self.note_tab, text='笔记链接 (每行一个 URL)').pack(anchor=tk.W, padx=5, pady=5)

        self.note_urls_text = ScrolledText(self.note_tab, height=8)

        self.note_urls_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)



        form = ttk.Frame(self.note_tab)

        form.pack(fill=tk.X, padx=5, pady=5)



        ttk.Label(form, text='保存选项').grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        self.note_save_var = tk.StringVar(value='all')

        ttk.Combobox(form, values=self.save_choices, textvariable=self.note_save_var, state='readonly').grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)



        ttk.Label(form, text='Excel 文件名').grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)

        self.note_excel_var = tk.StringVar(value='notes')

        ttk.Entry(form, textvariable=self.note_excel_var).grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)



        ttk.Button(self.note_tab, text='开始下载', command=self._handle_notes_submit).pack(anchor=tk.E, padx=5, pady=10)



    def _build_user_tab(self) -> None:

        form = ttk.Frame(self.user_tab)

        form.pack(fill=tk.X, padx=5, pady=10)



        ttk.Label(form, text='用户主页 URL').grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        self.user_url_var = tk.StringVar()

        ttk.Entry(form, textvariable=self.user_url_var).grid(row=0, column=1, columnspan=3, sticky=tk.EW, padx=5, pady=5)



        ttk.Label(form, text='保存选项').grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)

        self.user_save_var = tk.StringVar(value='all')

        ttk.Combobox(form, values=self.save_choices, textvariable=self.user_save_var, state='readonly').grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)



        ttk.Label(form, text='Excel 文件名 (可选)').grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.user_excel_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.user_excel_var).grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)

        ttk.Label(form, text='页面下拉次数 (0 表示不限)').grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.user_scroll_times_var = tk.IntVar(value=0)
        ttk.Spinbox(form, from_=0, to=1000, textvariable=self.user_scroll_times_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Button(self.user_tab, text='获取所有笔记', command=self._handle_user_submit).pack(anchor=tk.E, padx=5, pady=10)

        for idx in range(4):
            form.columnconfigure(idx, weight=1)



    def _build_search_tab(self) -> None:

        form = ttk.Frame(self.search_tab)

        form.pack(fill=tk.X, padx=5, pady=10)



        ttk.Label(form, text='关键词').grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        self.query_var = tk.StringVar()

        ttk.Entry(form, textvariable=self.query_var).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)



        ttk.Label(form, text='数量').grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)

        self.query_num_var = tk.IntVar(value=10)

        ttk.Spinbox(form, from_=1, to=1000, textvariable=self.query_num_var).grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)



        ttk.Label(form, text='排序').grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)

        self.sort_var = tk.StringVar(value='综合排序')

        ttk.Combobox(form, values=list(self.sort_options.keys()), textvariable=self.sort_var, state='readonly').grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)



        ttk.Label(form, text='笔记类型').grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)

        self.note_type_var = tk.StringVar(value='不限')

        ttk.Combobox(form, values=list(self.note_type_options.keys()), textvariable=self.note_type_var, state='readonly').grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)



        ttk.Label(form, text='时间范围').grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)

        self.note_time_var = tk.StringVar(value='不限')

        ttk.Combobox(form, values=list(self.note_time_options.keys()), textvariable=self.note_time_var, state='readonly').grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)



        ttk.Label(form, text='笔记范围').grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)

        self.note_range_var = tk.StringVar(value='不限')

        ttk.Combobox(form, values=list(self.note_range_options.keys()), textvariable=self.note_range_var, state='readonly').grid(row=2, column=3, sticky=tk.W, padx=5, pady=5)



        ttk.Label(form, text='位置').grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)

        self.pos_distance_var = tk.StringVar(value='不限')

        ttk.Combobox(form, values=list(self.pos_distance_options.keys()), textvariable=self.pos_distance_var, state='readonly').grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)



        ttk.Label(form, text='Geo 纬度').grid(row=3, column=2, sticky=tk.W, padx=5, pady=5)

        self.geo_lat_var = tk.StringVar()

        ttk.Entry(form, textvariable=self.geo_lat_var).grid(row=3, column=3, sticky=tk.W, padx=5, pady=5)



        ttk.Label(form, text='Geo 经度').grid(row=3, column=4, sticky=tk.W, padx=5, pady=5)

        self.geo_lng_var = tk.StringVar()

        ttk.Entry(form, textvariable=self.geo_lng_var).grid(row=3, column=5, sticky=tk.W, padx=5, pady=5)



        ttk.Label(form, text='保存选项').grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)

        self.search_save_var = tk.StringVar(value='all')

        ttk.Combobox(form, values=self.save_choices, textvariable=self.search_save_var, state='readonly').grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)



        ttk.Button(self.search_tab, text='执行搜索并下载', command=self._handle_search_submit).pack(anchor=tk.E, padx=5, pady=10)



        for idx in range(6):

            form.columnconfigure(idx, weight=1)



    def _build_log_section(self) -> None:

        frame = ttk.LabelFrame(self, text='运行日志')

        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)



        self.log_text = ScrolledText(frame, height=10, state='disabled')

        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)



        ttk.Button(frame, text='清空日志', command=self._clear_logs).pack(anchor=tk.E, padx=5, pady=5)



    # Default handling ---------------------------------------------------

    def _load_defaults(self) -> None:

        cookies, base_paths = self.config_manager.reload()

        self.cookies_text.delete('1.0', tk.END)

        self.cookies_text.insert(tk.END, cookies)

        self.media_var.set(base_paths.get('media', ''))

        self.excel_var.set(base_paths.get('excel', ''))

        # 覆盖为上次 GUI 退出时保存的设置（不包含 Cookies）
        settings = self.config_manager.load_gui_settings()
        if settings:
            # 全局设置
            self.media_var.set(settings.get('media_path', self.media_var.get()))
            self.excel_var.set(settings.get('excel_path', self.excel_var.get()))
            self.proxy_var.set(settings.get('proxy', ''))
            self.max_per_window_var.set(int(settings.get('max_per_window', self.max_per_window_var.get())))
            self.min_interval_var.set(float(settings.get('min_interval', self.min_interval_var.get())))
            self.max_notes_var.set(int(settings.get('max_notes', self.max_notes_var.get())))
            # 用户全集页的下拉次数默认值
            if hasattr(self, 'user_scroll_times_var'):
                self.user_scroll_times_var.set(int(settings.get('user_scroll_times', self.user_scroll_times_var.get())))
            # 批量笔记页
            note_urls = settings.get('note_urls', '')
            if note_urls and hasattr(self, 'note_urls_text'):
                self.note_urls_text.delete('1.0', tk.END)
                self.note_urls_text.insert(tk.END, note_urls)
            note_save_choice = settings.get('note_save_choice')
            if note_save_choice in self.save_choices:
                self.note_save_var.set(note_save_choice)
            self.note_excel_var.set(settings.get('note_excel_name', self.note_excel_var.get()))
            # 用户全集页
            self.user_url_var.set(settings.get('user_url', self.user_url_var.get()))
            user_save_choice = settings.get('user_save_choice')
            if user_save_choice in self.save_choices:
                self.user_save_var.set(user_save_choice)
            self.user_excel_var.set(settings.get('user_excel_name', self.user_excel_var.get()))
            # 搜索下载页
            self.query_var.set(settings.get('search_query', self.query_var.get()))
            try:
                self.query_num_var.set(int(settings.get('search_query_num', self.query_num_var.get())))
            except Exception:
                pass
            search_save_choice = settings.get('search_save_choice')
            if search_save_choice in self.save_choices:
                self.search_save_var.set(search_save_choice)
            # 映射排序 / 类型等选项时需要做反查，只有在 key 存在时才设置
            search_sort = settings.get('search_sort')
            if search_sort in self.sort_options:
                self.sort_var.set(search_sort)
            search_note_type = settings.get('search_note_type')
            if search_note_type in self.note_type_options:
                self.note_type_var.set(search_note_type)
            search_note_time = settings.get('search_note_time')
            if search_note_time in self.note_time_options:
                self.note_time_var.set(search_note_time)
            search_note_range = settings.get('search_note_range')
            if search_note_range in self.note_range_options:
                self.note_range_var.set(search_note_range)
            search_pos_distance = settings.get('search_pos_distance')
            if search_pos_distance in self.pos_distance_options:
                self.pos_distance_var.set(search_pos_distance)
            self.geo_lat_var.set(settings.get('search_geo_lat', self.geo_lat_var.get()))
            self.geo_lng_var.set(settings.get('search_geo_lng', self.geo_lng_var.get()))



    def _reload_defaults(self) -> None:

        self._load_defaults()

        self._append_log('已从 .env 重新加载配置')

    def _save_cookies_to_env(self) -> None:
        cookies = self.cookies_text.get('1.0', tk.END).strip()
        self.config_manager.save_cookies_to_env(cookies)
        self._append_log('已将 Cookies 写入 .env')
        messagebox.showinfo('保存成功', 'Cookies 已写入 .env，重启后会自动加载。')

    def _save_gui_settings(self) -> None:
        """Persist GUI settings (excluding cookies) to JSON."""
        settings = {
            # 全局设置
            'media_path': self.media_var.get().strip(),
            'excel_path': self.excel_var.get().strip(),
            'proxy': self.proxy_var.get().strip(),
            'max_per_window': int(self.max_per_window_var.get() or 0),
            'min_interval': float(self.min_interval_var.get() or 0.0),
            'max_notes': int(self.max_notes_var.get() or 0),
            # 批量笔记页
            'note_urls': self.note_urls_text.get('1.0', tk.END).strip() if hasattr(self, 'note_urls_text') else '',
            'note_save_choice': self.note_save_var.get() if hasattr(self, 'note_save_var') else '',
            'note_excel_name': self.note_excel_var.get() if hasattr(self, 'note_excel_var') else '',
            # 用户全集页
            'user_url': self.user_url_var.get() if hasattr(self, 'user_url_var') else '',
            'user_save_choice': self.user_save_var.get() if hasattr(self, 'user_save_var') else '',
            'user_excel_name': self.user_excel_var.get() if hasattr(self, 'user_excel_var') else '',
            # 搜索下载页
            'search_query': self.query_var.get() if hasattr(self, 'query_var') else '',
            'search_query_num': int(self.query_num_var.get() or 0) if hasattr(self, 'query_num_var') else 0,
            'search_save_choice': self.search_save_var.get() if hasattr(self, 'search_save_var') else '',
            'search_sort': self.sort_var.get() if hasattr(self, 'sort_var') else '',
            'search_note_type': self.note_type_var.get() if hasattr(self, 'note_type_var') else '',
            'search_note_time': self.note_time_var.get() if hasattr(self, 'note_time_var') else '',
            'search_note_range': self.note_range_var.get() if hasattr(self, 'note_range_var') else '',
            'search_pos_distance': self.pos_distance_var.get() if hasattr(self, 'pos_distance_var') else '',
            'search_geo_lat': self.geo_lat_var.get() if hasattr(self, 'geo_lat_var') else '',
            'search_geo_lng': self.geo_lng_var.get() if hasattr(self, 'geo_lng_var') else '',
        }
        if hasattr(self, 'user_scroll_times_var'):
            settings['user_scroll_times'] = int(self.user_scroll_times_var.get() or 0)
        self.config_manager.save_gui_settings(settings)



    # Utility interactions -----------------------------------------------

    def _select_directory(self, var: tk.StringVar) -> None:

        path = filedialog.askdirectory()

        if path:

            var.set(path)



    def _clear_logs(self) -> None:

        self.log_text.configure(state='normal')

        self.log_text.delete('1.0', tk.END)

        self.log_text.configure(state='disabled')



    def _append_log(self, message: str) -> None:

        self.log_text.configure(state='normal')

        self.log_text.insert(tk.END, f'{message}\n')

        self.log_text.see(tk.END)

        self.log_text.configure(state='disabled')



    def _enqueue_log(self, message: str) -> None:

        self.log_queue.put(message)



    def _poll_log_queue(self) -> None:

        try:

            while True:

                message = self.log_queue.get_nowait()

                self._append_log(message)

        except Empty:

            pass

        self.after(200, self._poll_log_queue)

    def _on_close(self) -> None:
        """Save GUI settings then close the window."""
        try:
            self._save_gui_settings()
        except Exception:
            # 保存失败不阻塞关闭
            pass
        self.destroy()



    # Validation helpers -------------------------------------------------

    def _get_common_inputs(self) -> Optional[Dict[str, object]]:

        cookies = self.cookies_text.get('1.0', tk.END).strip()

        if not cookies:

            messagebox.showerror('缺少 Cookies', '请先在顶部输入有效的 COOKIES 字符串。')

            return None



        defaults = self.config_manager.get_base_paths()

        media_path = self.media_var.get().strip() or defaults.get('media', '')

        excel_path = self.excel_var.get().strip() or defaults.get('excel', '')



        if not media_path or not excel_path:

            messagebox.showerror('路径未设置', '请配置媒体和 Excel 输出目录。')

            return None



        base_paths = self.config_manager.update_base_paths(media_path, excel_path)

        proxies = self._build_proxies(self.proxy_var.get())

        rate_limiter = self._build_rate_limiter()

        max_notes = max(0, int(self.max_notes_var.get() or 0))

        return {
            'cookies': cookies,
            'base_paths': base_paths,
            'proxies': proxies,
            'rate_limiter': rate_limiter,
            'max_notes': max_notes,
        }



    @staticmethod

    def _build_proxies(raw: str) -> Optional[Dict[str, str]]:

        value = (raw or '').strip()

        if not value:

            return None

        return {'http': value, 'https': value}



    def _build_rate_limiter(self) -> Optional[RateLimiter]:

        max_per_window = max(0, int(self.max_per_window_var.get() or 0))

        try:

            min_interval = float(self.min_interval_var.get())

        except tk.TclError:

            min_interval = 0.0

        min_interval = max(min_interval, 0.0)

        if max_per_window == 0 and min_interval == 0:

            return None

        return RateLimiter(max_per_window or None, window_seconds=600, min_interval=min_interval)



    def _ensure_idle(self) -> bool:

        if self.controller.is_busy():

            messagebox.showinfo('任务执行中', '已有任务在运行，请等待完成。')

            return False

        return True



    # Submission handlers -----------------------------------------------

    def _handle_notes_submit(self) -> None:

        if not self._ensure_idle():

            return



        lines = self.note_urls_text.get('1.0', tk.END).splitlines()

        note_urls = [line.strip() for line in lines if line.strip()]

        if not note_urls:

            messagebox.showerror('缺少 URL', '请至少输入一个笔记链接。')

            return



        save_choice = self.note_save_var.get()

        excel_name = self.note_excel_var.get().strip()

        if save_choice in ('all', 'excel') and not excel_name:

            messagebox.showerror('需要 Excel 名称', '保存模式包含 Excel 时必须提供文件名。')

            return



        common = self._get_common_inputs()

        if not common:

            return



        self.controller.run_notes_task(
            note_urls,
            common['cookies'],
            common['base_paths'],
            save_choice,
            excel_name,
            common['proxies'],
            common['rate_limiter'],
            common['max_notes'],
        )



    def _handle_user_submit(self) -> None:

        if not self._ensure_idle():

            return



        user_url = self.user_url_var.get().strip()

        if not user_url:

            messagebox.showerror('缺少用户链接', '请输入有效的用户主页 URL。')

            return



        save_choice = self.user_save_var.get()

        excel_name = self.user_excel_var.get().strip()

        scroll_times = max(0, int(self.user_scroll_times_var.get() or 0))

        common = self._get_common_inputs()

        if not common:

            return

        self.controller.run_user_task(

            user_url,

            common['cookies'],

            common['base_paths'],

            save_choice,

            excel_name,

            common['proxies'],

            common['rate_limiter'],

            scroll_times,

            common['max_notes'],

        )



    def _handle_search_submit(self) -> None:

        if not self._ensure_idle():

            return



        query = self.query_var.get().strip()

        if not query:

            messagebox.showerror('缺少关键词', '请输入要搜索的关键词。')

            return



        query_num = max(1, self.query_num_var.get())

        save_choice = self.search_save_var.get()

        sort_type = self.sort_options[self.sort_var.get()]

        note_type = self.note_type_options[self.note_type_var.get()]

        note_time = self.note_time_options[self.note_time_var.get()]

        note_range = self.note_range_options[self.note_range_var.get()]

        pos_distance = self.pos_distance_options[self.pos_distance_var.get()]



        geo = None

        lat_raw = self.geo_lat_var.get().strip()

        lng_raw = self.geo_lng_var.get().strip()

        if lat_raw or lng_raw:

            try:

                geo = {'latitude': float(lat_raw), 'longitude': float(lng_raw)}

            except ValueError:

                messagebox.showerror('Geo 坐标错误', '请输入有效的经纬度数值。')

                return



        if pos_distance in (1, 2) and not geo:

            messagebox.showerror('缺少 Geo', '同城/附近筛选需要同时提供经纬度。')

            return



        common = self._get_common_inputs()

        if not common:

            return



        self.controller.run_search_task(

            query,

            query_num,

            common['cookies'],

            common['base_paths'],

            save_choice,

            sort_type,

            note_type,

            note_time,

            note_range,

            pos_distance,

            geo,

            common['proxies'],

            common['rate_limiter'],

            common['max_notes'],

        )





def run_gui() -> None:

    app = SpiderGUI()

    app.mainloop()





if __name__ == '__main__':

    run_gui()

