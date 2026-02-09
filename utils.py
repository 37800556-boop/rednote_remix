"""
辅助工具函数模块
"""
import re
import hashlib
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """
    清理文本内容

    Args:
        text: 原始文本

    Returns:
        清理后的文本
    """
    if not text:
        return ""

    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text)

    # 移除特殊表情符号（可选）
    # text = re.sub(r'[\U00010000-\U0010ffff]', '', text)

    return text.strip()


def extract_hashtags(content: str) -> List[str]:
    """
    从内容中提取话题标签

    Args:
        content: 文本内容

    Returns:
        话题标签列表
    """
    pattern = r'#(\w+)'
    hashtags = re.findall(pattern, content)
    return hashtags


def generate_image_prompt(title: str, content: str, style: str = "attractive") -> str:
    """
    根据标题和内容生成图片提示词

    Args:
        title: 标题
        content: 内容
        style: 风格

    Returns:
        图片生成提示词
    """
    # 提取关键词
    combined_text = f"{title} {content}"

    # 移除话题标签
    combined_text = re.sub(r'#\w+', '', combined_text)

    # 分词（简单实现）
    keywords = []
    for word in combined_text.split():
        if len(word) > 1 and word not in keywords:
            keywords.append(word)

    # 限制关键词数量
    keywords = keywords[:10]

    # 构建提示词
    style_map = {
        "attractive": "色彩鲜艳，吸引眼球，Instagram 风格",
        "knowledge": "简洁专业，信息图表风格",
        "emotional": "温暖柔和，情感表达"
    }

    style_desc = style_map.get(style, "高质量")

    prompt = f"{style_desc}，{' '.join(keywords)}"

    logger.info(f"生成图片提示词: {prompt}")
    return prompt


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    截断文本到指定长度

    Args:
        text: 原始文本
        max_length: 最大长度

    Returns:
        截断后的文本
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[:max_length - 3] + "..."


def validate_url(url: str) -> bool:
    """
    验证 URL 是否有效

    Args:
        url: 待验证的 URL

    Returns:
        是否有效
    """
    if not url:
        return False

    # 基本 URL 格式验证
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    if not re.match(pattern, url):
        return False

    return True


def is_xiaohongshu_url(url: str) -> bool:
    """
    验证是否为小红书 URL（支持标准链接和短链接）

    Args:
        url: 待验证的 URL

    Returns:
        是否为小红书 URL
    """
    if not url:
        return False

    url_lower = url.lower()

    # 支持的标准域名
    valid_domains = [
        'xiaohongshu.com',      # 标准链接
        'xhslink.com',           # 短链接
        'xhslink.com/o/'         # 短链接（带路径）
    ]

    return any(domain in url_lower for domain in valid_domains)


def format_display_content(content: str, max_lines: int = 5) -> str:
    """
    格式化显示内容，限制行数

    Args:
        content: 原始内容
        max_lines: 最大行数

    Returns:
        格式化后的内容
    """
    if not content:
        return ""

    lines = content.split('\n')
    if len(lines) <= max_lines:
        return content

    return '\n'.join(lines[:max_lines]) + '\n...'


def generate_unique_id(content: str) -> str:
    """
    根据内容生成唯一 ID

    Args:
        content: 内容

    Returns:
        唯一 ID (MD5 哈希)
    """
    return hashlib.md5(content.encode()).hexdigest()[:16]


def safe_int(value: any, default: int = 0) -> int:
    """
    安全地将值转换为整数

    Args:
        value: 待转换的值
        default: 默认值

    Returns:
        整数
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def copy_to_clipboard(text: str) -> bool:
    """
    将文本复制到剪贴板

    Args:
        text: 待复制的文本

    Returns:
        是否成功
    """
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except ImportError:
        logger.warning("pyperclip 未安装，无法复制到剪贴板")
        return False
    except Exception as e:
        logger.error(f"复制到剪贴板失败: {e}")
        return False


def format_size(bytes_size: int) -> str:
    """
    格式化文件大小

    Args:
        bytes_size: 字节数

    Returns:
        格式化后的大小字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"
