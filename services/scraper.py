"""
小红书爬虫服务模块
使用 Playwright 进行网页抓取
"""
import sys
import json
import re
import logging
import asyncio
from typing import Optional, Dict, Any
from playwright.sync_api import sync_playwright, Browser, Page
from bs4 import BeautifulSoup

from models import NoteData
from utils import is_xiaohongshu_url

# 修复 Windows 上的 asyncio 事件循环问题
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class XiaohongshuScraper:
    """小红书笔记爬虫"""

    # 真实浏览器 User-Agent
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self, headless: bool = True, cookies: Optional[str] = None):
        """
        初始化爬虫

        Args:
            headless: 是否使用无头模式
            cookies: 小红书 Cookie 字符串（用于登录状态）
        """
        self.headless = headless
        self.cookies = cookies
        self._browser: Optional[Browser] = None
        self._playwright = None

    def start(self):
        """启动浏览器"""
        import subprocess
        self._playwright = sync_playwright().start()
        try:
            self._browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--start-maximized',
                    '--window-size=1920,1080'
                ]
            )
        except Exception as e:
            # 浏览器未安装，尝试自动安装
            if "Executable doesn't exist" in str(e) or "doesn't exist" in str(e):
                logger.info("Playwright 浏览器未安装，正在自动安装...")
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
                # 重试启动
                self._browser = self._playwright.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--start-maximized',
                        '--window-size=1920,1080'
                    ]
                )
            else:
                raise

    def stop(self):
        """停止浏览器"""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()

    def _extract_from_initial_state(self, page: Page) -> Optional[Dict[str, Any]]:
        """
        从页面初始状态 JSON 中提取数据

        策略: 优先尝试从 <script id="initial-state"> 或 window.__INITIAL_STATE__ 中提取
        这比 CSS 选择器更稳定，因为小红书是单页应用，数据都存在初始状态中

        Args:
            page: Playwright Page 对象

        Returns:
            提取的数据字典，失败返回 None
        """
        try:
            # 方法1: 尝试从 script 标签中提取（使用 textContent 避免 JSON 序列化）
            script_content = page.evaluate("""() => {
                const script = document.getElementById('initial-state');
                return script ? script.textContent : null;
            }""")

            if script_content:
                logger.info("从 script#initial-state 提取数据")
                return json.loads(script_content)

            # 方法2: 尝试直接从页面 HTML 中提取 script 标签内容
            html = page.content()
            soup = BeautifulSoup(html, 'lxml')
            script_tag = soup.find('script', {'id': 'initial-state'})
            if script_tag and script_tag.string:
                logger.info("从 HTML 中提取 script#initial-state")
                return json.loads(script_tag.string)

            # 方法3: 尝试从 window.__INITIAL_STATE__ 提取（分块提取以避免序列化问题）
            try:
                initial_state_str = page.evaluate("""() => {
                    if (window.__INITIAL_STATE__) {
                        return JSON.stringify(window.__INITIAL_STATE__);
                    }
                    return null;
                }""")

                if initial_state_str:
                    logger.info("从 window.__INITIAL_STATE__ 提取数据（分块）")
                    return json.loads(initial_state_str)
            except Exception as e:
                logger.debug(f"window.__INITIAL_STATE__ 提取失败: {e}")

            return None

        except Exception as e:
            logger.warning(f"从初始状态提取数据失败: {e}")
            return None

    def _parse_data_from_state(self, state_data: Dict[str, Any], url: str) -> NoteData:
        """
        从初始状态数据中解析笔记信息

        Args:
            state_data: 初始状态 JSON 数据
            url: 笔记 URL

        Returns:
            NoteData 对象
        """
        # 小红书的数据结构可能在不同版本中变化
        # 这里尝试多种可能的路径
        note_data = None

        # 尝试路径1: note.noteDetailMap
        if "note" in state_data and "noteDetailMap" in state_data["note"]:
            note_map = state_data["note"]["noteDetailMap"]
            if note_map:
                first_key = next(iter(note_map))
                note_data = note_map[first_key].get("note", {})

        # 尝试路径2: 直接在顶层
        if not note_data and "noteDetail" in state_data:
            note_data = state_data["noteDetail"]

        # 尝试路径3: 其他可能的路径
        if not note_data:
            for key in state_data:
                if isinstance(state_data[key], dict) and "title" in state_data[key]:
                    note_data = state_data[key]
                    break

        if not note_data:
            raise ValueError("无法从初始状态中解析笔记数据")

        # 提取字段
        title = note_data.get("title", "")
        content = note_data.get("desc", "") or note_data.get("content", "")

        # 提取图片
        images = []
        image_list = note_data.get("imageList", note_data.get("images", []))
        for img in image_list:
            # 优先使用无水印大图
            url = img.get("urlDefault", img.get("url", ""))
            if url:
                # 将 http 协议的图片 URL 转换为 https
                url = url.replace("http://", "https://")
                images.append(url)

        author = None
        if "user" in note_data:
            author = note_data["user"].get("nickname", "")

        likes = note_data.get("likedCount", note_data.get("likeCount", 0))

        return NoteData(
            url=url,
            title=title,
            content=content,
            images=images,
            author=author,
            likes=likes
        )

    def _fallback_css_extraction(self, page: Page, url: str) -> Optional[NoteData]:
        """
        CSS 选择器回退方案

        当 JSON 提取失败时，使用 CSS 选择器抓取页面内容

        Args:
            page: Playwright Page 对象
            url: 笔记 URL

        Returns:
            NoteData 对象，失败返回 None
        """
        try:
            logger.info("使用 CSS 选择器回退方案")

            # 等待内容加载
            page.wait_for_selector("div[class*='title']", timeout=5000)

            # 获取页面 HTML
            html = page.content()
            soup = BeautifulSoup(html, 'lxml')

            # 提取标题
            title = ""
            title_selectors = [
                "div[class*='title']",
                "h1[class*='title']",
                ".note-title"
            ]
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break

            # 提取正文
            content = ""
            content_selectors = [
                "div[class*='desc']",
                "div[class*='content']",
                ".note-content"
            ]
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = content_elem.get_text(strip=True)
                    break

            # 提取图片 - 使用精确的 Playwright 方法
            images = []

            # 使用 Playwright 直接提取图片，避免 BeautifulSoup 的局限性
            try:
                # 方法1: 从笔记容器中提取图片
                # 小红书笔记图片通常在特定的容器中
                img_selectors = [
                    ".swiper-slide img",           # 轮播图容器
                    ".note-item img",              # 笔记项容器
                    "div[class*='image-list'] img", # 图片列表容器
                    "div[class*='swiper'] img",    # swiper 容器
                    ".swiper-wrapper img",         # swiper 包装器
                    "section[class*='note'] img",  # 笔记区域
                ]

                for selector in img_selectors:
                    try:
                        img_elements = page.query_selector_all(selector)
                        if img_elements:
                            logger.info(f"使用选择器 {selector} 找到 {len(img_elements)} 张图片")
                            for img_elem in img_elements:
                                # 优先获取 data-src（懒加载），然后是 src
                                src = img_elem.get_attribute('data-src') or img_elem.get_attribute('src')
                                if src:
                                    # 过滤头像和其他小图片
                                    # 排除用户头像 URL（通常包含 avatar 或 user）
                                    if not any(keyword in src.lower() for keyword in ['avatar', 'user', 'icon', 'logo']):
                                        # 只保留笔记图片（通常来自 sns-img CDN）
                                        if 'sns-img' in src or 'sns' in src or 'pic' in src or 'image' in src:
                                            src = src.replace("http://", "https://")
                                            # 去除缩略图参数
                                            if 'imageView2' in src or 'params' in src:
                                                src = src.split('?')[0]
                                            if src not in images:
                                                images.append(src)
                            if images:
                                break
                    except Exception as e:
                        logger.debug(f"选择器 {selector} 失败: {e}")
                        continue

                # 方法2: 如果方法1没找到，尝试通用的图片提取（但排除头像）
                if not images:
                    logger.info("尝试通用图片提取方法")
                    all_imgs = page.query_selector_all("img")
                    for img_elem in all_imgs:
                        src = img_elem.get_attribute('src') or img_elem.get_attribute('data-src')
                        if src:
                            # 排除明显的头像 URL
                            src_lower = src.lower()
                            if not any(k in src_lower for k in ['avatar', 'user', 'icon', 'logo']):
                                # 只保留包含笔记图片特征的 URL
                                if any(k in src_lower for k in ['sns-img', 'sns', 'pic1', 'pic2', 'pic3', 'pic4']):
                                    src = src.replace("http://", "https://")
                                    if src not in images:
                                        images.append(src)

                logger.info(f"共提取到 {len(images)} 张图片")

            except Exception as e:
                logger.error(f"Playwright 图片提取失败: {e}")

            return NoteData(
                url=url,
                title=title,
                content=content,
                images=images
            )

        except Exception as e:
            logger.error(f"CSS 提取失败: {e}")
            return None

    def scrape_note(self, url: str) -> NoteData:
        """
        爬取小红书笔记

        Args:
            url: 小红书笔记 URL（支持标准链接和短链接 xhslink.com）

        Returns:
            NoteData 对象

        Raises:
            ValueError: URL 无效或爬取失败
        """
        if not url or not is_xiaohongshu_url(url):
            raise ValueError("无效的小红书 URL（支持标准链接和短链接 xhslink.com）")

        logger.info(f"开始爬取: {url}")

        if not self._browser:
            self.start()

        # 创建新页面，设置视口和额外 HTTP 头
        page = self._browser.new_page(
            user_agent=self.USER_AGENT,
            viewport={'width': 1920, 'height': 1080}
        )

        # 设置额外的 HTTP 头
        page.set_extra_http_headers({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.xiaohongshu.com/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        })

        # 如果提供了 Cookie，则设置到页面上
        if self.cookies:
            try:
                # 解析 Cookie 字符串并设置
                # Cookie 格式: "name1=value1; name2=value2; ..."
                context = page.context
                context.add_cookies([{
                    'name': cookie.strip().split('=')[0],
                    'value': cookie.strip().split('=', 1)[1] if '=' in cookie else '',
                    'domain': '.xiaohongshu.com',
                    'path': '/',
                    'httpOnly': True,
                    'secure': True
                } for cookie in self.cookies.split(';') if '=' in cookie])
                logger.info("已设置 Cookie")
            except Exception as e:
                logger.warning(f"设置 Cookie 失败: {e}")

        try:
            # 先访问小红书首页以确保 Cookie 生效
            if self.cookies:
                page.goto('https://www.xiaohongshu.com/', wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(1000)

            # 访问目标页面（短链接会自动重定向）
            page.goto(url, wait_until="networkidle", timeout=30000)

            # 获取重定向后的真实 URL
            final_url = page.url
            logger.info(f"最终 URL: {final_url}")

            # 检测是否被重定向到登录页面
            if '/login' in final_url:
                raise ValueError(
                    "小红书要求登录才能查看此内容。建议：\n"
                    "1. 使用公开笔记链接（无需登录）\n"
                    "2. 或在浏览器中登录后，使用浏览器开发工具复制 Cookie"
                )

            # 等待页面加载
            page.wait_for_timeout(2000)

            # 策略1: 尝试从初始状态 JSON 提取
            state_data = self._extract_from_initial_state(page)

            if state_data:
                try:
                    return self._parse_data_from_state(state_data, url)
                except Exception as e:
                    logger.warning(f"解析初始状态失败: {e}，尝试 CSS 回退方案")
                    return self._fallback_css_extraction(page, url)
            else:
                # 策略2: CSS 选择器回退
                note_data = self._fallback_css_extraction(page, url)
                if note_data:
                    return note_data
                else:
                    raise ValueError("无法提取笔记数据")

        except Exception as e:
            logger.error(f"爬取失败: {e}")
            raise
        finally:
            page.close()


def scrape_note(url: str, headless: bool = True, cookies: Optional[str] = None) -> NoteData:
    """
    便捷函数: 爬取小红书笔记

    Args:
        url: 小红书笔记 URL
        headless: 是否使用无头模式
        cookies: 小红书 Cookie 字符串（用于登录状态）

    Returns:
        NoteData 对象
    """
    with XiaohongshuScraper(headless=headless, cookies=cookies) as scraper:
        return scraper.scrape_note(url)
