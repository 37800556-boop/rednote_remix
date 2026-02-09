"""
RedNote Remix - 小红书二创工具
主应用程序入口

极简主义 UI 设计 - 类似 Gemini 风格
"""
import streamlit as st
import logging
import os
import re
import json
import subprocess
from typing import Optional
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# ====================================
# 自动安装 Playwright 浏览器（云端环境）
# ====================================
def ensure_playwright_browser():
    """确保 Playwright 浏览器已安装"""
    try:
        from playwright.sync_api import sync_playwright
        # 尝试启动浏览器，如果失败则安装
        with sync_playwright() as p:
            try:
                # 浏览器是否已安装
                browser = p.chromium.launch(headless=True)
                browser.close()
            except Exception:
                # 浏览器未安装，自动安装
                import sys
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    except Exception as e:
        logging.warning(f"Playwright 浏览器检查失败: {e}")

# 只在云端环境（非 Windows）中运行自动安装
if os.environ.get('STREAMLIT_SERVER_URL') or os.name != 'nt':
    try:
        ensure_playwright_browser()
    except:
        pass  # 静默失败，不影响应用启动

from models import NoteData, RemixedContent, RemixStyle, RemixOptions
from services.scraper import scrape_note
from services.ai_text import DeepSeekGenerator
from services.ai_image import JimengGenerator
from utils import (
    clean_text, generate_image_prompt, truncate_text,
    format_display_content, validate_url, is_xiaohongshu_url
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ====================================
# CSS 注入 - 极简现代风格
# ====================================
st.markdown("""
<style>
    /* 隐藏 Streamlit 默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 隐藏 Streamlit 默认的部署提示 */
    .stDeployButton {display: none;}

    /* 全局样式 */
    .main {
        padding-top: 2rem;
        max-width: 1200px;
        margin: 0 auto;
    }

    /* 大标题样式 - 居中、极简 */
    h1 {
        text-align: center !important;
        font-weight: 300 !important;
        letter-spacing: -0.02em !important;
        margin-bottom: 0.5rem !important;
    }

    /* 副标题样式 */
    .caption {
        text-align: center !important;
        color: #666 !important;
        font-size: 0.9rem !important;
        margin-bottom: 3rem !important;
    }

    /* 输入框样式 - 大圆角、柔和阴影 */
    .stTextArea > div > div > textarea,
    .stTextInput > div > div > input {
        border-radius: 16px !important;
        border: 1px solid #e0e0e0 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
        padding: 16px !important;
        font-size: 15px !important;
        transition: all 0.3s ease !important;
    }

    .stTextArea > div > div > textarea:focus,
    .stTextInput > div > div > input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 4px 20px rgba(99,102,241,0.15) !important;
        outline: none !important;
    }

    /* 按钮样式 - 大圆角、渐变 */
    .stButton > button {
        border-radius: 12px !important;
        padding: 12px 32px !important;
        font-weight: 500 !important;
        border: none !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(0,0,0,0.15) !important;
    }

    /* 主按钮样式 */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
    }

    /* 生成结果卡片样式 */
    .result-card {
        background: #fafafa;
        border-radius: 20px;
        padding: 24px;
        margin: 16px 0;
        border: 1px solid #f0f0f0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.03);
    }

    /* 图片画廊样式 - 朋友圈九宫格 + 纯CSS悬浮效果 */
    .gallery-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 16px 0;
    }

    .gallery-img-wrapper {
        display: inline-block;
        position: relative;
        border-radius: 8px;
        overflow: visible;
    }

    .gallery-img {
        display: block;
        border-radius: 8px;
        border: 1px solid #eee;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.2s ease;
        cursor: pointer;
    }

    /* 纯CSS悬浮效果 - 适度的放大 */
    .gallery-img-wrapper:hover .gallery-img {
        transform: scale(2.5);
        z-index: 999;
        box-shadow: 0 20px 40px rgba(0,0,0,0.4);
        position: relative;
    }

    /* 分隔线样式 */
    hr {
        border: none;
        border-top: 1px solid #f0f0f0;
        margin: 2rem 0;
    }

    /* 选择框样式 */
    .stSelectbox > div > div > select {
        border-radius: 12px !important;
        border: 1px solid #e0e0e0 !important;
    }

    /* 复选框样式 */
    .checkbox-container {
        display: flex;
        gap: 20px;
        margin: 16px 0;
        flex-wrap: wrap;
    }

    .checkbox-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        background: #f8f9fa;
        border-radius: 10px;
        transition: all 0.2s ease;
    }

    .checkbox-item:hover {
        background: #e9ecef;
    }

    /* 状态消息样式 */
    .stSuccess, .stInfo, .stWarning, .stError {
        border-radius: 12px !important;
        padding: 16px 24px !important;
        border: none !important;
    }

    /* 侧边栏样式 */
    .css-1d391kg {
        background: #fafafa;
    }

    /* expander 样式 */
    .streamlit-expanderHeader {
        background: #f8f9fa !important;
        border-radius: 12px !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ====================================
# 页面配置
# ====================================
st.set_page_config(
    page_title="RedNote Remix",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ====================================
# 初始化 Session State
# ====================================
def init_session_state():
    """初始化 Streamlit Session State"""
    if "deepseek_api_key" not in st.session_state:
        st.session_state.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")

    if "jimeng_api_key" not in st.session_state:
        st.session_state.jimeng_api_key = os.getenv("JIMENG_API_KEY", "")

    if "jimeng_endpoint_id" not in st.session_state:
        st.session_state.jimeng_endpoint_id = os.getenv("JIMENG_ENDPOINT_ID", "")

    if "xhs_cookies" not in st.session_state:
        st.session_state.xhs_cookies = os.getenv("XHS_COOKIES", "")

    if "current_note" not in st.session_state:
        st.session_state.current_note: Optional[NoteData] = None

    if "remixed_content" not in st.session_state:
        st.session_state.remixed_content: Optional[RemixedContent] = None

    if "generating_text" not in st.session_state:
        st.session_state.generating_text = False

    if "generating_image" not in st.session_state:
        st.session_state.generating_image = False

    if "config_panel_open" not in st.session_state:
        st.session_state.config_panel_open = False


init_session_state()

# ====================================
# URL 提取函数
# ====================================
def extract_url_from_input(user_input: str) -> Optional[str]:
    """从用户输入中提取 URL"""
    if not user_input:
        return None

    pattern = r'(https?://[a-zA-Z0-9.=&_%/?-]+)'
    match = re.search(pattern, user_input)

    if match:
        url = match.group(1)
        logging.info(f"从输入中提取到 URL: {url}")
        return url

    return None


# ====================================
# 图片画廊渲染函数
# ====================================
import requests
import io
import base64

def fetch_image_as_base64(url, timeout=10):
    """下载图片并转换为 base64"""
    try:
        # 模拟浏览器请求，绕过防盗链
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.xiaohongshu.com/',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        # 转换为 base64
        image_data = base64.b64encode(response.content).decode('utf-8')
        return f"data:image/jpeg;base64,{image_data}"
    except Exception as e:
        logger.error(f"下载图片失败 {url}: {e}")
        return None

def render_gallery(images, title="图片"):
    """渲染图片画廊 - 朋友圈九宫格风格 + 纯CSS悬浮效果"""
    if not images:
        return

    count = len(images)

    # 下载所有图片并转换为 base64
    base64_images = []
    with st.spinner("加载图片中..."):
        for img_url in images:
            base64_data = fetch_image_as_base64(img_url)
            if base64_data:
                base64_images.append(base64_data)
            else:
                # 下载失败，使用占位图
                base64_images.append(None)

    # 使用 HTML 显示 base64 图片
    if count == 1:
        # 单图：大图显示
        if base64_images[0]:
            st.markdown(f"""
<div style="text-align:center;">
    <img src="{base64_images[0]}" style="width:100%;max-width:500px;height:auto;border-radius:8px;" alt="图片1">
</div>
""", unsafe_allow_html=True)
        else:
            st.error("图片加载失败")
    elif count == 2:
        # 两图：左右排列
        col1, col2 = st.columns(2)
        with col1:
            if base64_images[0]:
                st.markdown(f'<img src="{base64_images[0]}" style="width:100%;height:200px;object-fit:cover;border-radius:8px;">', unsafe_allow_html=True)
            else:
                st.error("图片1加载失败")
        with col2:
            if base64_images[1]:
                st.markdown(f'<img src="{base64_images[1]}" style="width:100%;height:200px;object-fit:cover;border-radius:8px;">', unsafe_allow_html=True)
            else:
                st.error("图片2加载失败")
    elif count == 4:
        # 四图：2x2网格
        col1, col2 = st.columns(2)
        with col1:
            if base64_images[0]:
                st.markdown(f'<img src="{base64_images[0]}" style="width:100%;height:140px;object-fit:cover;border-radius:8px;margin-bottom:8px;">', unsafe_allow_html=True)
            if base64_images[1]:
                st.markdown(f'<img src="{base64_images[1]}" style="width:100%;height:140px;object-fit:cover;border-radius:8px;">', unsafe_allow_html=True)
        with col2:
            if base64_images[2]:
                st.markdown(f'<img src="{base64_images[2]}" style="width:100%;height:140px;object-fit:cover;border-radius:8px;margin-bottom:8px;">', unsafe_allow_html=True)
            if base64_images[3]:
                st.markdown(f'<img src="{base64_images[3]}" style="width:100%;height:140px;object-fit:cover;border-radius:8px;">', unsafe_allow_html=True)
    else:
        # 默认：3列九宫格布局
        rows = (count + 2) // 3

        for row in range(rows):
            cols = st.columns(3)
            for col in range(3):
                idx = row * 3 + col
                if idx < count:
                    with cols[col]:
                        if base64_images[idx]:
                            st.markdown(f'<img src="{base64_images[idx]}" style="width:100%;height:120px;object-fit:cover;border-radius:8px;">', unsafe_allow_html=True)
                        else:
                            st.caption(f"图片{idx+1}加载失败")


# ====================================
# 侧边栏 - 精简版，仅保留 API 配置
# ====================================
with st.sidebar:
    st.markdown("### 🔑 API 配置")
    st.markdown("---")

    # DeepSeek API Key
    deepseek_key = st.text_input(
        "DeepSeek API Key",
        type="password",
        value=st.session_state.deepseek_api_key
    )
    st.session_state.deepseek_api_key = deepseek_key

    # Jimeng API Key
    jimeng_key = st.text_input(
        "Jimeng API Key",
        type="password",
        value=st.session_state.jimeng_api_key
    )
    st.session_state.jimeng_api_key = jimeng_key

    # Jimeng Endpoint ID
    jimeng_endpoint_id = st.text_input(
        "Jimeng Endpoint ID",
        value=st.session_state.jimeng_endpoint_id
    )
    st.session_state.jimeng_endpoint_id = jimeng_endpoint_id

    # 小红书 Cookie
    with st.expander("🍪 Cookie (可选)"):
        xhs_cookies = st.text_area(
            "小红书 Cookie",
            value=st.session_state.xhs_cookies,
            height=80
        )
        st.session_state.xhs_cookies = xhs_cookies

        st.markdown("""
        <small style="color: #999;">
        在浏览器中登录小红书后，按 F12 → Application → Cookies 复制
        </small>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 状态指示
    ds_ready = bool(st.session_state.deepseek_api_key)
    jm_ready = bool(st.session_state.jimeng_api_key and st.session_state.jimeng_endpoint_id)

    st.markdown(f"""
    <div style="display: flex; gap: 8px; align-items: center;">
        <span style="font-size: 12px;">DeepSeek:</span>
        <span style="color: {'#10b981' if ds_ready else '#f59e0b'}; font-size: 12px;">
            {'● 就绪' if ds_ready else '● 未配置'}
        </span>
    </div>
    <div style="display: flex; gap: 8px; align-items: center; margin-top: 8px;">
        <span style="font-size: 12px;">Jimeng:</span>
        <span style="color: {'#10b981' if jm_ready else '#f59e0b'}; font-size: 12px;">
            {'● 就绪' if jm_ready else '● 未配置'}
        </span>
    </div>
    """, unsafe_allow_html=True)

# ====================================
# 主界面 - 极简居中布局
# ====================================

# 主容器 - Gemini 风格
st.markdown("""
<div style="max-width: 800px; margin: 0 auto; padding: 2rem 0;">
    <div style="text-align: center; margin-bottom: 2.5rem;">
        <h1 style="font-size: 3rem; font-weight: 500; color: #1a1a1a; margin-bottom: 0.5rem; letter-spacing: -0.02em;">
            你的小红书私人助手
        </h1>
    </div>
</div>
""", unsafe_allow_html=True)

# Gemini 风格输入框 CSS
st.markdown("""
<style>
    /* 表单容器 */
    .stForm {
        max-width: 680px;
        margin: 0 auto;
    }

    /* 输入框外层 - 渐变背景 */
    .stForm [data-testid="stTextArea"] > div {
        background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%) !important;
        border-radius: 26px !important;
        padding: 5px !important;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08) !important;
    }

    /* 输入框内层 - 白色背景 */
    .stForm [data-testid="stTextArea"] > div > div {
        background: white !important;
        border-radius: 22px !important;
        border: none !important;
    }

    /* 文本区域 */
    .stForm [data-testid="stTextArea"] textarea {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        font-size: 15px !important;
        line-height: 1.5 !important;
        color: #1a1a1a !important;
        padding: 14px 20px !important;
    }

    .stForm [data-testid="stTextArea"] textarea:focus {
        box-shadow: none !important;
    }

    .stForm [data-testid="stTextArea"] textarea::placeholder {
        color: #9ca3af !important;
    }

    /* 提交按钮 */
    .stForm [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 20px !important;
        padding: 10px 24px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 8px rgba(102,126,234,0.3) !important;
    }

    .stForm [data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 15px rgba(102,126,234,0.4) !important;
    }

    /* 悬浮配置按钮 - 左下角 */
    .config-toggle-wrapper {
        position: fixed;
        bottom: 20px;
        left: 20px;
        z-index: 999;
    }

    .config-toggle-btn {
        width: 50px;
        height: 50px;
        border-radius: 50%;
        background: #666;
        border: none;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        cursor: pointer;
        font-size: 20px;
        color: white;
        transition: all 0.2s ease;
    }

    .config-toggle-btn:hover {
        background: #555;
    }

    /* 隐藏配置按钮的默认样式 */
    .config-toggle-wrapper [data-testid="stVerticalBlock"] {
        background: transparent !important;
        box-shadow: none !important;
        border: none !important;
    }

    .config-toggle-wrapper .stButton {
        background: transparent !important;
        box-shadow: none !important;
        border: none !important;
    }

    /* 配置面板样式 */
    .config-expander-section {
        position: fixed;
        bottom: 80px;
        left: 20px;
        z-index: 998;
        max-width: 400px;
    }

    /* 隐藏侧边栏 */
    [data-testid="stSidebar"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# 配置持久化 JavaScript - 在 CSS 之后单独注入
config_to_save = json.dumps(st.session_state.get('_config_to_save', {}))
clear_config_flag = str(st.session_state.get('_clear_config', False)).lower()

# 清除清除标志
if st.session_state.get('_clear_config', False):
    st.session_state._clear_config = False

st.markdown(f"""
<script>
// 配置持久化 - 使用 localStorage
const CONFIG_KEY = 'rednote_remix_config';
const CONFIG_TO_SAVE = {config_to_save};
const CLEAR_CONFIG_FLAG = {clear_config_flag};

// 保存配置到 localStorage
function saveConfigToBrowser(configData) {{
    if (configData && Object.keys(configData).length > 0) {{
        localStorage.setItem(CONFIG_KEY, JSON.stringify(configData));
        console.log('配置已保存到本地存储', configData);
        return true;
    }}
    return false;
}}

// 如果有配置需要保存，立即执行
if (CONFIG_TO_SAVE && Object.keys(CONFIG_TO_SAVE).length > 0) {{
    saveConfigToBrowser(CONFIG_TO_SAVE);
}}

// 清除配置
function clearConfigFromBrowser() {{
    localStorage.removeItem(CONFIG_KEY);
    console.log('已清除本地存储的配置');
}}

if (CLEAR_CONFIG_FLAG === 'true') {{
    clearConfigFromBrowser();
}}

// 从 localStorage 加载配置
function loadConfigFromBrowser() {{
    const saved = localStorage.getItem(CONFIG_KEY);
    if (saved) {{
        try {{
            return JSON.parse(saved);
        }} catch (e) {{
            console.error('解析保存的配置失败', e);
            return null;
        }}
    }}
    return null;
}}

// 页面加载时尝试恢复配置并填充到输入框
document.addEventListener('DOMContentLoaded', function() {{
    const config = loadConfigFromBrowser();
    if (config) {{
        console.log('从本地存储加载配置', config);
        window.savedConfig = config; // 保存到全局变量供后续使用
    }} else {{
        window.savedConfig = null;
    }}
}});

// 监听 Streamlit 渲染完成后尝试填充配置
const observer = new MutationObserver(function() {{
    const config = window.savedConfig;
    if (!config) return;

    // 填充 DeepSeek API Key (password input)
    const deepseekInput = document.querySelector('input[placeholder*="DeepSeek"], input[aria-label*="DeepSeek"]');
    if (deepseekInput && config.deepseek_api_key && deepseekInput.value !== config.deepseek_api_key) {{
        deepseekInput.value = config.deepseek_api_key;
        deepseekInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
        deepseekInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
        console.log('已填充 DeepSeek API Key');
    }}

    // 填充 Jimeng API Key (password input) - 寻找第二个 password input
    const allPasswordInputs = document.querySelectorAll('input[type="password"]');
    if (allPasswordInputs.length >= 2 && config.jimeng_api_key) {{
        const jimengInput = allPasswordInputs[1]; // 第二个密码框
        if (jimengInput.value !== config.jimeng_api_key) {{
            jimengInput.value = config.jimeng_api_key;
            jimengInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            jimengInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
            console.log('已填充 Jimeng API Key');
        }}
    }}

    // 填充 Jimeng Endpoint ID
    const endpointInputs = document.querySelectorAll('input[type="text"]');
    endpointInputs.forEach(function(input) {{
        if ((input.placeholder?.includes('Endpoint') || input.ariaLabel?.includes('Endpoint')) && config.jimeng_endpoint_id) {{
            input.value = config.jimeng_endpoint_id;
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            console.log('已填充 Jimeng Endpoint ID');
        }}
    }});

    // 填充 Cookie
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(function(area) {{
        if ((area.placeholder?.includes('Cookie') || area.ariaLabel?.includes('Cookie')) && config.xhs_cookies) {{
            area.value = config.xhs_cookies;
            area.dispatchEvent(new Event('input', {{ bubbles: true }}));
            area.dispatchEvent(new Event('change', {{ bubbles: true }}));
            console.log('已填充 Cookie');
        }}
    }});
}});

observer.observe(document.body, {{ childList: true, subtree: true }});
</script>
""", unsafe_allow_html=True)

# 使用 Form 组件将输入框和按钮组合在一起
with st.form("url_form", clear_on_submit=True):
    url_input = st.text_area(
        "输入链接",
        placeholder="粘贴小红书链接或分享内容...",
        height=70,
        label_visibility="collapsed"
    )
    submitted = st.form_submit_button("开始解析", use_container_width=True)

    if submitted:
        extracted_url = extract_url_from_input(url_input)

        if extracted_url:
            if is_xiaohongshu_url(extracted_url):
                try:
                    with st.spinner("解析中..."):
                        cookies = st.session_state.xhs_cookies if st.session_state.xhs_cookies else None
                        st.session_state.current_note = scrape_note(extracted_url, cookies=cookies)
                        st.session_state.remixed_content = None
                    st.success("✓ 解析成功")
                    st.rerun()
                except Exception as e:
                    st.error(f"解析失败: {str(e)}")
            else:
                st.warning("请输入有效的小红书链接")
        else:
            st.warning("未检测到链接")

# 悬浮配置按钮
st.markdown('<div class="config-toggle-wrapper">', unsafe_allow_html=True)
if st.button("⚙", key="config_toggle"):
    st.session_state.config_panel_open = not st.session_state.config_panel_open
st.markdown("</div>", unsafe_allow_html=True)

# 配置面板（点击按钮后显示）
if st.session_state.config_panel_open:
    with st.expander("🔑 API 配置", expanded=True):
        # DeepSeek API Key
        deepseek_key = st.text_input(
            "DeepSeek API Key",
            type="password",
            value=st.session_state.deepseek_api_key
        )
        st.session_state.deepseek_api_key = deepseek_key

        # Jimeng API Key
        jimeng_key = st.text_input(
            "Jimeng API Key",
            type="password",
            value=st.session_state.jimeng_api_key
        )
        st.session_state.jimeng_api_key = jimeng_key

        # Jimeng Endpoint ID
        jimeng_endpoint_id = st.text_input(
            "Jimeng Endpoint ID",
            value=st.session_state.jimeng_endpoint_id
        )
        st.session_state.jimeng_endpoint_id = jimeng_endpoint_id

        # 小红书 Cookie
        with st.expander("🍪 Cookie (可选)"):
            xhs_cookies = st.text_area(
                "小红书 Cookie",
                value=st.session_state.xhs_cookies,
                height=60
            )
            st.session_state.xhs_cookies = xhs_cookies

        # 保存配置按钮
        col_save, col_clear = st.columns(2)
        with col_save:
            save_clicked = st.button("💾 保存到浏览器", use_container_width=True, key="save_config_btn")
        with col_clear:
            clear_clicked = st.button("🗑️ 清除保存", use_container_width=True, key="clear_config_btn")

        # 保存按钮 - 将配置保存到 localStorage
        if save_clicked:
            config_data = {
                "deepseek_api_key": st.session_state.deepseek_api_key,
                "jimeng_api_key": st.session_state.jimeng_api_key,
                "jimeng_endpoint_id": st.session_state.jimeng_endpoint_id,
                "xhs_cookies": st.session_state.xhs_cookies
            }
            # 传递给 JavaScript
            st.session_state._config_to_save = config_data
            st.success("✓ 配置已保存，刷新页面后自动加载")
            st.rerun()

        # 清除按钮
        if clear_clicked:
            st.session_state._clear_config = True
            st.session_state._config_to_save = {}
            st.success("✓ 已清除浏览器保存的配置")
            st.rerun()

        # 从 localStorage 加载配置
        if "config_loaded" not in st.session_state:
            st.session_state.config_loaded = False

        # 状态指示
        ds_ready = bool(st.session_state.deepseek_api_key)
        jm_ready = bool(st.session_state.jimeng_api_key and st.session_state.jimeng_endpoint_id)

        st.markdown(f"""
        <div style="display: flex; gap: 20px; margin-top: 10px;">
            <div style="display: flex; gap: 5px; align-items: center;">
                <span style="font-size: 12px;">DeepSeek:</span>
                <span style="color: {'#10b981' if ds_ready else '#f59e0b'}; font-size: 12px;">
                    {'● 已配置' if ds_ready else '● 未配置'}
                </span>
            </div>
            <div style="display: flex; gap: 5px; align-items: center;">
                <span style="font-size: 12px;">Jimeng:</span>
                <span style="color: {'#10b981' if jm_ready else '#f59e0b'}; font-size: 12px;">
                    {'● 已配置' if jm_ready else '● 未配置'}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ====================================
# 内容区域 - 左右分栏
# ====================================
if st.session_state.current_note:
    note = st.session_state.current_note

    # 分栏布局
    left_col, right_col = st.columns(2)

    # -------------------------------
    # 左列：原文展示
    # -------------------------------
    with left_col:
        st.markdown("### 📄 原文")

        # 使用 HTML 画廊渲染图片
        if note.images:
            render_gallery(note.images, "原文图片")

        # 标题和内容
        st.markdown(f"**{note.title}**")

        with st.expander("正文内容", expanded=True):
            st.markdown(format_display_content(note.content, max_lines=8))

        # 元信息
        meta_info = ""
        if note.author:
            meta_info += f"👤 {note.author}"
        if note.likes:
            if meta_info:
                meta_info += " · "
            meta_info += f"👍 {note.likes}"
        if meta_info:
            st.caption(meta_info)

    # -------------------------------
    # 右列：施展魔法 - 简化版
    # -------------------------------
    with right_col:
        st.markdown("### ✨ 施展魔法")

        # 单一操作选择器
        action_type = st.selectbox(
            "选择操作",
            options=["改写标题", "改写正文", "生成配图"],
            label_visibility="visible"
        )

        # 根据选择显示不同的界面
        if action_type == "改写标题":
            # 标题改写界面
            col_model, _ = st.columns([3, 1])
            with col_model:
                model_select = st.selectbox(
                    "选择模型",
                    options=["deepseek-chat", "deepseek-reasoner"],
                    label_visibility="visible"
                )

            instruction = st.text_area(
                "改写要求",
                placeholder="描述你想要的标题风格，例如：\n• 更有悬念，制造好奇心\n• 更简洁有力\n• 加入数字或疑问句...",
                height=80,
                label_visibility="collapsed"
            )

            if st.button("生成新标题", use_container_width=True, key="gen_title"):
                if not st.session_state.deepseek_api_key:
                    st.error("请先在侧边栏配置 DeepSeek API Key")
                else:
                    try:
                        with st.spinner("生成中..."):
                            style = RemixStyle(style_type="custom", custom_prompt=instruction)
                            generator = DeepSeekGenerator(st.session_state.deepseek_api_key)
                            result = generator.generate(note.title, note.content, style, model=model_select)

                            if st.session_state.remixed_content is None:
                                st.session_state.remixed_content = RemixedContent(
                                    original_title=note.title,
                                    new_title=result["new_title"],
                                    original_content=note.content,
                                    new_content="",
                                    style_used=style
                                )
                            else:
                                st.session_state.remixed_content.new_title = result["new_title"]
                                st.session_state.remixed_content.style_used = style

                        st.success("✓ 生成成功")
                        st.rerun()
                    except Exception as e:
                        st.error(f"生成失败: {str(e)}")

        elif action_type == "改写正文":
            # 正文改写界面
            col_model, _ = st.columns([3, 1])
            with col_model:
                model_select = st.selectbox(
                    "选择模型",
                    options=["deepseek-chat", "deepseek-reasoner"],
                    label_visibility="visible"
                )

            instruction = st.text_area(
                "改写要求",
                placeholder="描述你想要的正文风格，例如：\n• 更口语化，像朋友聊天\n• 更专业，加入数据分析\n• 更有趣，加入个人经历...",
                height=80,
                label_visibility="collapsed"
            )

            if st.button("生成新正文", use_container_width=True, key="gen_content"):
                if not st.session_state.deepseek_api_key:
                    st.error("请先在侧边栏配置 DeepSeek API Key")
                else:
                    try:
                        with st.spinner("生成中..."):
                            style = RemixStyle(style_type="custom", custom_prompt=instruction)
                            generator = DeepSeekGenerator(st.session_state.deepseek_api_key)
                            result = generator.generate(note.title, note.content, style, model=model_select)

                            if st.session_state.remixed_content is None:
                                st.session_state.remixed_content = RemixedContent(
                                    original_title=note.title,
                                    new_title="",
                                    original_content=note.content,
                                    new_content=result["new_content"],
                                    style_used=style
                                )
                            else:
                                st.session_state.remixed_content.new_content = result["new_content"]
                                st.session_state.remixed_content.style_used = style

                        st.success("✓ 生成成功")
                        st.rerun()
                    except Exception as e:
                        st.error(f"生成失败: {str(e)}")

        elif action_type == "生成配图":
            # 图片生成界面
            col_model, _ = st.columns([3, 1])
            with col_model:
                image_model = st.selectbox(
                    "选择模型",
                    options=["jimeng"],
                    label_visibility="visible",
                    disabled=True
                )

            instruction = st.text_area(
                "生成指令",
                placeholder="描述你想要的图片风格，例如：\n• 温暖治愈风格\n• 赛博朋克风格\n• 日系清新风格...",
                height=60,
                label_visibility="collapsed"
            )

            # 参考图片选择
            if note.images:
                st.markdown("**参考图（可选）**")
                ref_options = ["全部重新生成"] + [f"图片 {i+1}" for i in range(len(note.images))]
                ref_selection = st.radio(
                    "参考图",
                    options=ref_options,
                    horizontal=True,
                    label_visibility="collapsed"
                )

                if ref_selection != "全部重新生成":
                    idx = int(ref_selection.split()[1]) - 1
                    st.session_state.selected_reference_image = note.images[idx]
                    st.image(note.images[idx], width=100, caption="参考图预览")
                else:
                    if "selected_reference_image" in st.session_state:
                        del st.session_state.selected_reference_image

            if st.button("生成配图", use_container_width=True, key="gen_image"):
                if not st.session_state.jimeng_api_key or not st.session_state.jimeng_endpoint_id:
                    st.error("请先在侧边栏配置 Jimeng API Key")
                else:
                    try:
                        with st.spinner("生成中..."):
                            # 生成图片提示词
                            base_title = st.session_state.remixed_content.new_title if st.session_state.remixed_content and st.session_state.remixed_content.new_title else note.title
                            base_content = st.session_state.remixed_content.new_content if st.session_state.remixed_content and st.session_state.remixed_content.new_content else note.content

                            image_prompt = generate_image_prompt(base_title, base_content, "custom")
                            if instruction:
                                image_prompt += f"。风格要求：{instruction}"

                            # 调用 Jimeng
                            generator = JimengGenerator(
                                api_key=st.session_state.jimeng_api_key,
                                endpoint_id=st.session_state.jimeng_endpoint_id
                            )

                            reference_image = st.session_state.get("selected_reference_image")
                            image_urls = generator.generate(image_prompt, count=1, reference_image=reference_image)

                            # 更新二创内容
                            if st.session_state.remixed_content:
                                st.session_state.remixed_content.generated_images = image_urls
                            else:
                                st.session_state.remixed_content = RemixedContent(
                                    original_title=note.title,
                                    original_content=note.content,
                                    generated_images=image_urls,
                                    style_used=RemixStyle(style_type="custom")
                                )

                        st.success("✓ 生成成功")
                        st.rerun()
                    except Exception as e:
                        st.error(f"生成失败: {str(e)}")

        # ---------------------------
        # 生成结果展示
        # ---------------------------
        if st.session_state.remixed_content:
            result = st.session_state.remixed_content

            st.markdown("---")
            st.markdown("### 📝 魔法成果")

            # 新标题
            if result.new_title:
                st.markdown("**标题**")
                col_t, col_copy = st.columns([5, 1])
                with col_t:
                    st.markdown(f"{result.new_title}")
                with col_copy:
                    if st.button("复制", key="copy_t", use_container_width=True):
                        st.code(result.new_title)

            # 新正文
            if result.new_content:
                st.markdown("**正文**")
                col_c, col_copy2 = st.columns([5, 1])
                with col_c:
                    st.markdown(format_display_content(result.new_content, max_lines=8))
                with col_copy2:
                    if st.button("复制", key="copy_c", use_container_width=True):
                        st.code(result.new_content)

            # 生成的图片
            if result.generated_images:
                st.markdown("**配图**")

                # 为每张图片显示下载按钮
                for idx, img_url in enumerate(result.generated_images):
                    col_img, col_dl = st.columns([5, 1])

                    with col_img:
                        st.markdown(f"""
<div class="gallery-img-wrapper">
    <img class="gallery-img" src="{img_url}" style="width:100%;max-width:300px;height:auto;border-radius:8px;border:1px solid #eee;" alt="生成图片{idx + 1}">
</div>
""", unsafe_allow_html=True)

                    with col_dl:
                        # 创建下载链接
                        st.markdown(f"""
<a href="{img_url}" download="rednote_remix_{idx + 1}.jpg" target="_blank">
    <button style="width:100%;padding:8px 16px;border-radius:8px;border:none;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;cursor:pointer;font-weight:500;transition:all 0.3s ease;">
        下载
    </button>
</a>
""", unsafe_allow_html=True)

# 页脚 - 极简
st.markdown("""
---
<center>
    <small style="color: #ccc;">RedNote Remix · Built with Streamlit & AI</small>
</center>
""", unsafe_allow_html=True)
