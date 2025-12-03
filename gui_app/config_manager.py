import json
import os
from pathlib import Path
from typing import Dict, Tuple

from xhs_utils.common_util import init as cli_init


class ConfigManager:
    """Manage cookies, output directories and GUI settings shared between CLI and GUI."""

    def __init__(self) -> None:
        self.cookies_str: str = ''
        self.base_paths: Dict[str, str] = {}
        root_dir = Path(__file__).resolve().parents[1]
        self.env_path = root_dir / '.env'
        self.gui_settings_path = root_dir / 'gui_settings.json'
        self.reload()

    def reload(self) -> Tuple[str, Dict[str, str]]:
        """Reload cookies and default directories using existing CLI helper."""
        cookies, base_paths = cli_init()
        self.cookies_str = cookies or ''
        self.base_paths = {key: os.path.abspath(path) for key, path in base_paths.items()}
        return self.cookies_str, self.get_base_paths()

    def get_cookies(self) -> str:
        return self.cookies_str

    def set_cookies(self, value: str) -> None:
        self.cookies_str = value or ''

    def save_cookies_to_env(self, value: str) -> str:
        sanitized = value or ''
        cookie_line = self._format_cookie_line(sanitized)
        env_lines = []
        if self.env_path.exists():
            env_lines = self.env_path.read_text(encoding='utf-8').splitlines()
        updated = False
        new_lines = []
        for line in env_lines:
            if line.startswith('COOKIES='):
                new_lines.append(cookie_line)
                updated = True
            elif line.strip():
                new_lines.append(line)
        if not updated:
            new_lines.append(cookie_line)
        self.env_path.write_text('\r\n'.join(new_lines) + '\r\n', encoding='utf-8')
        self.cookies_str = sanitized
        return self.cookies_str

    def get_base_paths(self) -> Dict[str, str]:
        return dict(self.base_paths)

    def update_base_paths(self, media_path: str, excel_path: str) -> Dict[str, str]:
        media = self._ensure_directory(media_path)
        excel = self._ensure_directory(excel_path)
        self.base_paths = {'media': media, 'excel': excel}
        return self.get_base_paths()

    # GUI settings (excluding cookies) ----------------------------------

    def load_gui_settings(self) -> Dict[str, object]:
        """Load persisted GUI settings from JSON (excluding cookies)."""
        if not self.gui_settings_path.exists():
            return {}
        try:
            return json.loads(self.gui_settings_path.read_text(encoding='utf-8'))
        except Exception:
            return {}

    def save_gui_settings(self, settings: Dict[str, object]) -> None:
        """Persist GUI settings to JSON (excluding cookies)."""
        try:
            self.gui_settings_path.write_text(
                json.dumps(settings, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
        except Exception:
            # 配置失败不应影响主流程，忽略写入错误
            pass

    @staticmethod
    def _ensure_directory(path: str) -> str:
        normalized = os.path.abspath(path)
        os.makedirs(normalized, exist_ok=True)
        return normalized

    @staticmethod
    def _format_cookie_line(value: str) -> str:
        escaped = value.replace('"', '\\"')
        return f'COOKIES="{escaped}"'
