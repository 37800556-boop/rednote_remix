"""
RedNote Remix - 小红书二创工具
主应用程序入口

使用 Streamlit 构建桌面端 Web 应用
"""
import streamlit as st
import logging
import os
import re
from typing import Optional
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

from models import NoteData, RemixedContent, RemixStyle, RemixOptions
from services.scraper import scrape_note
from services.ai_text import DeepSeekGenerator
from services.ai_image import JimengGenerator
from utils import (
    clean_text, generate_image_prompt, truncate_text,
    format_display_content, validate_url, is_xiaohongshu_url
)

# ====================================
# 页面配置
# ====================================
st.set_page_config(
    page_title="RedNote Remix - 小红书二创工具",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================================
# 初始化 Session State
# ====================================
def init_session_state():
    """初始化 Streamlit Session State"""
    if "deepseek_api_key" not in st.session_state:
        # 从环境变量读取，如果没有则使用空字符串
        st.session_state.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")

    if "jimeng_api_key" not in st.session_state:
        # 从环境变量读取，如果没有则使用空字符串
        st.session_state.jimeng_api_key = os.getenv("JIMENG_API_KEY", "")

    if "xhs_cookies" not in st.session_state:
        # 从环境变量读取 Cookie，如果没有则使用空字符串
        st.session_state.xhs_cookies = os.getenv("XHS_COOKIES", "")

    if "current_note" not in st.session_state:
        st.session_state.current_note: Optional[NoteData] = None

    if "remixed_content" not in st.session_state:
        st.session_state.remixed_content: Optional[RemixedContent] = None

    if "generating_text" not in st.session_state:
        st.session_state.generating_text = False

    if "generating_image" not in st.session_state:
        st.session_state.generating_image = False


init_session_state()

# ====================================
# URL 提取函数
# ====================================
def extract_url_from_input(user_input: str) -> Optional[str]:
    """
    从用户输入中提取 URL

    支持混合格式输入，例如：
    - "标题... http://xhslink.com/xyz 打开小红书..."
    - 纯净的 URL

    Args:
        user_input: 用户输入的文本

    Returns:
        提取到的 URL，未找到则返回 None
    """
    if not user_input:
        return None

    # 正则表达式提取 http 或 https 链接
    # 支持的格式：http://... 或 https://...
    pattern = r'(https?://[a-zA-Z0-9.=&_%/-]+)'
    match = re.search(pattern, user_input)

    if match:
        url = match.group(1)
        logging.info(f"从输入中提取到 URL: {url}")
        return url

    return None

# ====================================
# 侧边栏配置
# ====================================
with st.sidebar:
    st.title("🔧 配置面板")

    st.divider()

    st.subheader("API 配置")

    # DeepSeek API Key
    deepseek_key = st.text_input(
        "DeepSeek API Key",
        type="password",
        value=st.session_state.deepseek_api_key,
        help="用于文本生成的 DeepSeek API Key"
    )
    st.session_state.deepseek_api_key = deepseek_key

    # Jimeng API Key
    jimeng_key = st.text_input(
        "Jimeng API Key",
        type="password",
        value=st.session_state.jimeng_api_key,
        help="用于图片生成的火山引擎即梦 API Key"
    )
    st.session_state.jimeng_api_key = jimeng_key

    # Jimeng Endpoint ID
    if "jimeng_endpoint_id" not in st.session_state:
        st.session_state.jimeng_endpoint_id = os.getenv("JIMENG_ENDPOINT_ID", "")

    jimeng_endpoint_id = st.text_input(
        "Jimeng Endpoint ID",
        value=st.session_state.jimeng_endpoint_id,
        help="火山引擎推理接入点 ID (格式: ep-xxxxxxxx)"
    )
    st.session_state.jimeng_endpoint_id = jimeng_endpoint_id

    st.divider()

    st.subheader("爬虫配置（可选）")

    # 小红书 Cookie
    xhs_cookies = st.text_area(
        "小红书 Cookie（可选）",
        value=st.session_state.xhs_cookies,
        help="用于访问需要登录的内容。在浏览器中登录小红书后，按 F12 -> Application -> Cookies -> 复制所有 Cookie",
        height=80
    )
    st.session_state.xhs_cookies = xhs_cookies

    with st.expander("📖 如何获取 Cookie？"):
        st.markdown("""
        1. 在浏览器中打开小红书并登录
        2. 按 F12 打开开发者工具
        3. 切换到「Application」或「应用」标签
        4. 左侧找到「Cookies」 -> https://www.xiaohongshu.com
        5. 复制所有 Cookie（格式：name1=value1; name2=value2; ...）

        **或者使用浏览器插件：**
        - 安装「EditThisCookie」插件
        - 登录小红书后点击插件图标
        - 点击「导出」并复制内容
        """)

    st.divider()

    st.subheader("当前状态")

    # 显示 AI 服务状态
    deepseek_status = "✅ 已配置" if st.session_state.deepseek_api_key else "⚠️ 未配置"
    st.text(f"DeepSeek: {deepseek_status}")

    jimeng_status = "✅ 已配置" if st.session_state.jimeng_api_key and st.session_state.jimeng_endpoint_id else "⚠️ 未配置"
    st.text(f"Jimeng: {jimeng_status}")

    st.divider()

    st.markdown("""
    ### 📖 使用说明

    1. 输入小红书笔记 URL
    2. 点击「开始解析」获取原文
    3. 选择改写风格
    4. 点击「生成新文本」改写内容
    5. 点击「生成新图片」创建配图
    6. 使用复制按钮获取结果
    """)

# ====================================
# 主界面
# ====================================
st.title("🎨 RedNote Remix")
st.caption("小红书内容二创工具 - AI 驱动的文本改写与图片生成")

st.divider()

# URL 输入区域
col1, col2 = st.columns([4, 1])
with col1:
    url_input = st.text_area(
        "请输入小红书笔记 URL 或分享内容",
        placeholder="支持直接粘贴小红书分享的内容，例如：\n标题... http://xhslink.com/xyz 打开小红书...\n\n或直接输入 URL",
        help="可以直接粘贴小红书 APP 复制的分享内容，工具会自动提取 URL",
        height=100
    )
with col2:
    st.write("")  # 占位，对齐按钮
    st.write("")
    if st.button("🔍 开始解析", width="stretch"):
        # 从混合输入中提取 URL
        extracted_url = extract_url_from_input(url_input)

        if extracted_url:
            st.info(f"📎 已提取 URL: {extracted_url}")

            if is_xiaohongshu_url(extracted_url):
                try:
                    with st.spinner("正在解析笔记..."):
                        # 传递 Cookie（如果有）
                        cookies = st.session_state.xhs_cookies if st.session_state.xhs_cookies else None
                        st.session_state.current_note = scrape_note(extracted_url, cookies=cookies)
                        st.session_state.remixed_content = None
                    st.success("✅ 解析成功！")
                except Exception as e:
                    st.error(f"❌ 解析失败: {str(e)}")
            else:
                st.warning("⚠️ 提取的 URL 不是小红书链接，请检查输入")
        else:
            st.warning("⚠️ 未检测到有效 URL，请确保输入包含 http:// 或 https:// 开头的链接")

# 内容显示区域
if st.session_state.current_note:
    note = st.session_state.current_note

    # 创建两列布局
    left_col, right_col = st.columns(2)

    # ================================
    # 左列：原文内容
    # ================================
    with left_col:
        st.subheader("📄 原文内容")

        # 显示所有图片
        if note.images:
            st.caption(f"📷 共 {len(note.images)} 张图片")
            for idx, img_url in enumerate(note.images):
                st.image(img_url, caption=f"图片 {idx + 1}", width="stretch")

        # 标题
        st.markdown(f"**标题:** {note.title}")

        # 正文
        with st.expander("查看完整正文", expanded=True):
            st.write(format_display_content(note.content, max_lines=10))

        # 元信息
        if note.author:
            st.caption(f"作者: {note.author}")
        if note.likes:
            st.caption(f"👍 {note.likes} 点赞")

    # ================================
    # 右列：二创内容
    # ================================
    with right_col:
        st.subheader("✨ 二创生成")

        # 改写风格选择
        style_options = {
            "attractive": "🎯 吸引眼球",
            "knowledge": "📚 干货分享",
            "emotional": "💝 情感共鸣",
            "custom": "🎨 自定义"
        }

        selected_style = st.selectbox(
            "选择改写风格",
            options=list(style_options.keys()),
            format_func=lambda x: style_options[x],
            index=0
        )

        # 自定义提示词
        custom_prompt = ""
        if selected_style == "custom":
            custom_prompt = st.text_area(
                "自定义提示词",
                placeholder="描述你想要的风格...",
                help="例如：幽默风趣、年轻化表达、网络流行语等"
            )

        # 补充提示词
        additional_prompt = st.text_input(
            "补充要求（可选）",
            placeholder="例如：增加emoji、添加话题标签...",
            help="对生成内容的额外要求"
        )

        st.divider()

        # 生成按钮区域
        btn_col1, btn_col2 = st.columns(2)

        # 生成新文本按钮
        with btn_col1:
            if st.button("✍️ 生成新文本", width="stretch"):
                if not st.session_state.deepseek_api_key:
                    st.error("❌ 请先在侧边栏配置 DeepSeek API Key")
                else:
                    st.session_state.generating_text = True

        # 生成新图片按钮
        with btn_col2:
            if st.button("🖼️ 生成新图片", width="stretch"):
                if not st.session_state.jimeng_api_key or not st.session_state.jimeng_endpoint_id:
                    st.error("❌ 请先在侧边栏配置 Jimeng API Key 和 Endpoint ID")
                else:
                    st.session_state.generating_image = True

        # ================================
        # 文本生成处理
        # ================================
        if st.session_state.generating_text:
            try:
                with st.spinner("正在生成新文本..."):
                    # 创建风格对象
                    style = RemixStyle(
                        style_type=selected_style,
                        custom_prompt=f"{custom_prompt} {additional_prompt}".strip()
                    )

                    # 调用 DeepSeek
                    generator = DeepSeekGenerator(st.session_state.deepseek_api_key)
                    result = generator.generate(note.title, note.content, style)

                    # 创建/更新二创内容
                    if st.session_state.remixed_content is None:
                        st.session_state.remixed_content = RemixedContent(
                            original_title=note.title,
                            new_title=result["new_title"],
                            original_content=note.content,
                            new_content=result["new_content"],
                            style_used=style
                        )
                    else:
                        st.session_state.remixed_content.new_title = result["new_title"]
                        st.session_state.remixed_content.new_content = result["new_content"]
                        st.session_state.remixed_content.style_used = style

                st.success("✅ 文本生成成功！")
                st.session_state.generating_text = False

                # 重新运行以显示结果
                st.rerun()

            except Exception as e:
                st.error(f"❌ 生成失败: {str(e)}")
                st.session_state.generating_text = False

        # ================================
        # 图片生成处理
        # ================================
        if st.session_state.generating_image:
            try:
                with st.spinner("正在生成新图片..."):
                    # 生成图片提示词
                    image_prompt = generate_image_prompt(
                        st.session_state.remixed_content.new_title if st.session_state.remixed_content else note.title,
                        st.session_state.remixed_content.new_content if st.session_state.remixed_content else note.content,
                        selected_style
                    )

                    # 调用 Jimeng
                    generator = JimengGenerator(
                        api_key=st.session_state.jimeng_api_key,
                        endpoint_id=st.session_state.jimeng_endpoint_id
                    )
                    image_urls = generator.generate(image_prompt, count=1)

                    # 更新二创内容
                    if st.session_state.remixed_content:
                        st.session_state.remixed_content.generated_images = image_urls
                    else:
                        # 如果还没有文本，先创建一个空的内容对象
                        st.session_state.remixed_content = RemixedContent(
                            original_title=note.title,
                            new_title="",
                            original_content=note.content,
                            new_content="",
                            generated_images=image_urls,
                            style_used=RemixStyle(style_type=selected_style)
                        )

                st.success("✅ 图片生成成功！")
                st.session_state.generating_image = False
                st.rerun()

            except Exception as e:
                st.error(f"❌ 生成失败: {str(e)}")
                st.session_state.generating_image = False

        # ================================
        # 显示生成结果
        # ================================
        if st.session_state.remixed_content:
            result = st.session_state.remixed_content

            st.divider()
            st.markdown("### 📝 生成结果")

            # 新标题
            st.markdown("**新标题:**")
            title_col, copy_col = st.columns([4, 1])
            with title_col:
                st.write(result.new_title)
            with copy_col:
                if st.button("📋", key="copy_title", help="复制标题"):
                    st.code(result.new_title, language=None)

            # 新正文
            st.markdown("**新正文:**")
            content_col, copy_col2 = st.columns([4, 1])
            with content_col:
                st.write(format_display_content(result.new_content, max_lines=10))
            with copy_col2:
                if st.button("📋", key="copy_content", help="复制正文"):
                    st.code(result.new_content, language=None)

            # 生成的图片
            if result.generated_images:
                st.markdown("**生成的图片:**")
                for idx, img_url in enumerate(result.generated_images):
                    st.image(img_url, caption=f"生成图片 {idx + 1}", width="stretch")

# ====================================
# 页脚
# ====================================
st.divider()
st.caption("RedNote Remix v1.0 - 使用 Streamlit + Playwright + AI 构建")
