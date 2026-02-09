"""
AI 文本生成服务模块
使用策略模式设计，支持多种文本生成服务
"""
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from openai import OpenAI

from models import RemixStyle

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TextGenerator(ABC):
    """
    文本生成器抽象基类

    定义所有文本生成服务必须实现的接口
    使用策略模式，便于扩展新的 AI 服务
    """

    @abstractmethod
    def generate(self, original_title: str, original_content: str, style: RemixStyle) -> Dict[str, str]:
        """
        生成改写后的文本

        Args:
            original_title: 原标题
            original_content: 原文内容
            style: 改写风格配置

        Returns:
            包含 new_title 和 new_content 的字典
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """获取服务名称"""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """检查是否已配置（API Key 等）"""
        pass


class DeepSeekGenerator(TextGenerator):
    """
    DeepSeek 文本生成器实现

    使用 OpenAI 兼容接口调用 DeepSeek API
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 DeepSeek 生成器

        Args:
            api_key: DeepSeek API Key
        """
        self.api_key = api_key
        self._client = None
        self.base_url = "https://api.deepseek.com"

        if self.api_key:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

    def generate(self, original_title: str, original_content: str, style: RemixStyle) -> Dict[str, str]:
        """
        使用 DeepSeek 生成改写文本

        Args:
            original_title: 原标题
            original_content: 原文内容
            style: 改写风格配置

        Returns:
            包含 new_title 和 new_content 的字典
        """
        if not self.is_configured():
            raise ValueError("DeepSeek API Key 未配置")

        # 构建风格提示词
        style_prompts = {
            "attractive": "吸引眼球: 使用夸张、疑问、对比等手法，制造悬念和好奇心",
            "knowledge": "干货分享: 条理清晰，分点阐述，突出实用性和专业性",
            "emotional": "情感共鸣: 使用感性语言，讲述故事，引发读者情感共鸣",
            "custom": "自定义风格"
        }

        base_prompt = style_prompts.get(style.style_type, "")

        # 构建 system prompt
        system_prompt = f"""你是一位专业的小红书内容创作者。请根据以下要求改写内容：

改写风格: {base_prompt}
{f'额外要求: {style.custom_prompt}' if style.custom_prompt and style.style_type == 'custom' else ''}

改写要求:
1. 标题要简洁有力，符合小红书风格（可使用emoji）
2. 正文要保持原文核心信息，但用全新的表达方式
3. 可以适当添加小红书常用的表达方式和标签
4. 输出必须是严格的 JSON 格式

输出格式:
{{
  "new_title": "新标题",
  "new_content": "新正文内容"
}}
"""

        # 构建 user prompt
        user_prompt = f"""原标题: {original_title}

原文内容:
{original_content}

请改写以上内容，输出 JSON 格式。"""

        try:
            logger.info(f"调用 DeepSeek API 生成内容，风格: {style.style_type}")

            response = self._client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            logger.info("DeepSeek 生成成功")
            return {
                "new_title": result.get("new_title", ""),
                "new_content": result.get("new_content", "")
            }

        except Exception as e:
            logger.error(f"DeepSeek 生成失败: {e}")
            raise

    def get_name(self) -> str:
        return "DeepSeek"

    def is_configured(self) -> bool:
        return self._client is not None


class GeminiGenerator(TextGenerator):
    """
    Gemini 文本生成器实现（预留）

    用于未来扩展 Gemini API 支持
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Gemini 生成器

        Args:
            api_key: Gemini API Key
        """
        self.api_key = api_key
        # TODO: 初始化 Gemini 客户端
        # import google.generativeai as genai
        # genai.configure(api_key=api_key)
        # self._model = genai.GenerativeModel('gemini-pro')

    def generate(self, original_title: str, original_content: str, style: RemixStyle) -> Dict[str, str]:
        """
        使用 Gemini 生成改写文本（待实现）

        Args:
            original_title: 原标题
            original_content: 原文内容
            style: 改写风格配置

        Returns:
            包含 new_title 和 new_content 的字典
        """
        # TODO: 实现 Gemini API 调用逻辑
        raise NotImplementedError("Gemini 生成器尚未实现，需要配置 API 并实现调用逻辑")

        # 示例实现（伪代码）:
        # prompt = self._build_prompt(original_title, original_content, style)
        # response = self._model.generate_content(prompt)
        # result = json.loads(response.text)
        # return {"new_title": result["new_title"], "new_content": result["new_content"]}

    def get_name(self) -> str:
        return "Gemini"

    def is_configured(self) -> bool:
        return self.api_key is not None


class TextServiceFactory:
    """
    文本服务工厂

    用于创建和管理不同的文本生成器
    """

    _generators: Dict[str, TextGenerator] = {}

    @classmethod
    def register_generator(cls, name: str, generator: TextGenerator):
        """注册生成器"""
        cls._generators[name] = generator

    @classmethod
    def get_generator(cls, name: str = "deepseek") -> TextGenerator:
        """
        获取指定名称的生成器

        Args:
            name: 生成器名称 (deepseek, gemini)

        Returns:
            TextGenerator 实例
        """
        generator = cls._generators.get(name)
        if not generator:
            raise ValueError(f"未找到生成器: {name}")
        return generator

    @classmethod
    def create_deepseek(cls, api_key: str) -> DeepSeekGenerator:
        """创建 DeepSeek 生成器"""
        generator = DeepSeekGenerator(api_key)
        cls.register_generator("deepseek", generator)
        return generator

    @classmethod
    def create_gemini(cls, api_key: str) -> GeminiGenerator:
        """创建 Gemini 生成器（预留）"""
        generator = GeminiGenerator(api_key)
        cls.register_generator("gemini", generator)
        return generator


def create_text_generator(service_name: str, api_key: str) -> TextGenerator:
    """
    创建文本生成器的便捷函数

    Args:
        service_name: 服务名称 (deepseek, gemini)
        api_key: API Key

    Returns:
        TextGenerator 实例
    """
    if service_name.lower() == "deepseek":
        return TextServiceFactory.create_deepseek(api_key)
    elif service_name.lower() == "gemini":
        return TextServiceFactory.create_gemini(api_key)
    else:
        raise ValueError(f"不支持的服务: {service_name}")
