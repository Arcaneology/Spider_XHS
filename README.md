<p align="center">
  <a href="https://github.com/cv-cat/Spider_XHS" target="_blank" align="center" alt="Go to XHS_Spider Website">
    <picture>
      <img width="220" src="https://github.com/user-attachments/assets/b817a5d2-4ca6-49e9-b7b1-efb07a4fb325" alt="Spider_XHS logo">
    </picture>
  </a>
</p>

<div align="center">
    <a href="https://www.python.org/">
        <img src="https://img.shields.io/badge/python-3.7%2B-blue" alt="Python 3.7+">
    </a>
    <a href="https://nodejs.org/zh-cn/">
        <img src="https://img.shields.io/badge/nodejs-18%2B-blue" alt="NodeJS 18+">
    </a>
</div>

# Spider_XHS

本仓库在原项目基础上补充了桌面图形界面（Tkinter），便于非命令行用户配置 Cookies、输出目录和搜索/下载参数。核心爬虫能力保持不变。

## 功能概览（原项目精简版）
- 小红书 PC：二维码/手机号登录，笔记图文和视频无水印下载，用户主页/喜欢/收藏/评论/消息等数据获取。
- 创作者平台：二维码/验证码登录，作品上传（图集、视频）及自有作品查看。
- 数据输出：媒体文件按目录落盘，笔记元数据可导出为 Excel，支持代理与简单频率控制。

## 环境要求
- Python 3.7+
- Node.js 18+（`PyExecJS` 调用 `static/*.js` 时需要）
- （可选）Docker 24+

## 安装依赖
```
pip install -r requirements.txt
npm install
```

## 配置 Cookies
在项目根目录创建或编辑 `.env`，写入浏览器抓到的登录后 Cookies：
```
COOKIES="your_cookie_string"
```
启动 GUI 后也可以用“读取 Cookies / 保存 Cookies”按钮与 `.env` 互相同步（不会保存到 git）。

## 启动桌面版
```
python -m gui_app
```
打开后即可在窗口内完成全部配置和任务下发。

### 界面说明
- **全局配置**：输入 Cookies，设置媒体输出目录、Excel 输出目录、可选代理；可配置频率限制（每 10 分钟最大请求数、单次最小间隔）与全局笔记数量上限。关闭窗口会把非 Cookies 配置保存在 `gui_settings.json` 供下次启动使用。
- **批量笔记**：每行粘贴一个笔记链接，选择保存模式（all/media/media-video/media-image/excel）和 Excel 文件名，点击“开始下载”。
- **用户全集**：填写用户主页 URL，可选 Excel 名称与页面下拉次数（0 为不限），点击“获取所有笔记”。
- **搜索下载**：输入关键词和数量，选择排序、笔记类型/时间/范围、位置筛选（同城/附近需填写经纬度），选择保存模式后点击“执行搜索并下载”。
- **日志与任务**：下方“运行日志”实时显示进度；有任务执行时会阻止重复启动。

## 命令行运行（保留）
配置好 `.env` 后可直接运行默认流程：
```
python main.py
```

## Docker（可选）
```
docker build -t spider_xhs .
docker run --env-file .env spider_xhs
```

## 提示
- 请勿提交真实 Cookies 或代理信息到仓库。
- 下载/上传行为需遵守平台规则，示例配置仅供学习测试。


