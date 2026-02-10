"""
AI 图片生成服务模块
使用策略模式设计，支持多种图片生成服务
"""
import logging
import random
from abc import ABC, abstractmethod
from typing import List, Optional
import requests

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImageGenerator(ABC):
    """
    图片生成器抽象基类

    定义所有图片生成服务必须实现的接口
    使用策略模式，便于扩展新的 AI 服务
    """

    @abstractmethod
    def generate(self, prompt: str, count: int = 1, size: str = "1920x1920", **kwargs) -> List[str]:
        """
        生成图片

        Args:
            prompt: 图片生成提示词
            count: 生成图片数量
            size: 图片尺寸，格式 "宽x高"，如 "1920x1920"

        Returns:
            图片 URL 列表
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


class JimengGenerator(ImageGenerator):
    """
    即梦 (Jimeng) 图片生成器实现

    使用火山引擎 Ark 平台的 Doubao-Seedream-4.5 模型
    支持 OpenAI SDK 兼容接口
    """

    # 火山引擎 Ark API 配置
    ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

    def __init__(self, api_key: Optional[str] = None, endpoint_id: Optional[str] = None):
        """
        初始化即梦生成器

        Args:
            api_key: 火山引擎 API Key
            endpoint_id: 推理接入点 ID (格式: ep-xxxxxxxx) - 必填，用作模型名称
        """
        self.api_key = api_key
        self.endpoint_id = endpoint_id

        # 构建完整的 API URL
        # 格式: https://ark.cn-beijing.volces.com/api/v3/images/generations
        self.api_endpoint = f"{self.ARK_BASE_URL}/images/generations"

        # HTTP 请求头
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def generate(self, prompt: str, count: int = 1, size: str = "1920x1920", reference_image: Optional[str] = None) -> List[str]:
        """
        使用火山引擎即梦 API 生成图片

        Args:
            prompt: 图片生成提示词
            count: 生成图片数量
            size: 图片尺寸，格式 "宽x高"，如 "1920x1920"
            reference_image: 参考图片 URL（用于图生图）

        Returns:
            图片 URL 列表

        Raises:
            ValueError: API 配置不完整
            requests.RequestException: API 请求失败
        """
        if not self.api_key:
            raise ValueError("API Key 未配置，请在侧边栏设置火山引擎 API Key")

        if not self.endpoint_id:
            raise ValueError("Endpoint ID 未配置，请在侧边栏设置火山引擎推理接入点 ID")

        logger.info(f"即梦图片生成: prompt='{prompt}', count={count}, size={size}")

        try:
            image_urls = []

            # 火山引擎 Ark API 兼容 OpenAI images/generations 格式
            # 参考文档: https://www.volcengine.com/docs/82379/1541523
            # 注意: 使用自定义推理接入点时，model 参数应使用 endpoint_id
            for i in range(count):
                payload = {
                    "model": self.endpoint_id,  # 使用 endpoint_id 作为模型名称
                    "prompt": prompt,
                    "n": 1,  # 每次请求生成 1 张图片
                    "size": size  # 图片尺寸，格式 "宽x高"
                }

                # 如果提供了参考图片，添加到请求中（图生图）
                if reference_image:
                    payload["image"] = reference_image
                    logger.info(f"使用参考图片进行图生图: {reference_image}")

                logger.debug(f"发送请求到: {self.api_endpoint}")
                logger.debug(f"请求参数: {payload}")

                response = requests.post(
                    self.api_endpoint,
                    headers=self.headers,
                    json=payload,
                    timeout=120  # 图片生成可能需要较长时间
                )

                # 检查 HTTP 状态码
                response.raise_for_status()

                result = response.json()
                logger.debug(f"API 响应: {result}")

                # 从响应中提取图片 URL
                # 火山引擎 API 响应格式 (兼容 OpenAI):
                # {
                #   "data": [
                #     {
                #       "url": "https://..."
                #     }
                #   ]
                # }
                if "data" in result and len(result["data"]) > 0:
                    image_url = result["data"][0].get("url", "")
                    if image_url:
                        image_urls.append(image_url)
                        logger.info(f"成功生成图片 {i + 1}/{count}: {image_url}")
                    else:
                        logger.warning(f"图片 {i + 1}/{count} 响应中没有 URL")
                else:
                    logger.warning(f"图片 {i + 1}/{count} 响应格式异常: {result}")

            if not image_urls:
                raise ValueError("未能从 API 响应中提取到图片 URL")

            logger.info(f"即梦生成完成，共 {len(image_urls)} 张图片")
            return image_urls

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP 错误: {e.response.status_code}"
            try:
                error_detail = e.response.json()
                error_msg += f" - {error_detail.get('error', {}).get('message', '未知错误')}"
            except:
                if e.response.text:
                    error_msg += f" - {e.response.text[:200]}"
            logger.error(f"即梦 API 调用失败: {error_msg}")
            raise ValueError(error_msg) from e

        except requests.exceptions.Timeout:
            logger.error("即梦 API 请求超时")
            raise ValueError("图片生成请求超时，请稍后重试")

        except requests.exceptions.RequestException as e:
            logger.error(f"即梦 API 请求失败: {e}")
            raise ValueError(f"API 请求失败: {str(e)}") from e

        except Exception as e:
            logger.error(f"即梦图片生成失败: {e}")
            raise

    def get_name(self) -> str:
        return "Jimeng (火山引擎 Seedream 4.5)"

    def is_configured(self) -> bool:
        return self.api_key is not None and self.endpoint_id is not None


class NanobananaGenerator(ImageGenerator):
    """
    Nanobanana 图片生成器实现（预留）

    用于未来扩展 Nanobanana API 支持
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Nanobanana 生成器

        Args:
            api_key: Nanobanana API Key
        """
        self.api_key = api_key
        # TODO: 初始化 Nanobanana 客户端
        # self.api_endpoint = "https://api.nanobanana.example.com/v1/generate"

    def generate(self, prompt: str, count: int = 1) -> List[str]:
        """
        使用 Nanobanana 生成图片（待实现）

        Args:
            prompt: 图片生成提示词
            count: 生成图片数量

        Returns:
            图片 URL 列表
        """
        # TODO: 实现 Nanobanana API 调用逻辑
        raise NotImplementedError("Nanobanana 生成器尚未实现，需要配置 API 并实现调用逻辑")

        # 示例实现（伪代码）:
        # image_urls = []
        # for i in range(count):
        #     response = requests.post(
        #         self.api_endpoint,
        #         headers={"Authorization": f"Bearer {self.api_key}"},
        #         json={"prompt": prompt}
        #     )
        #     image_urls.append(response.json()["url"])
        # return image_urls

    def get_name(self) -> str:
        return "Nanobanana"

    def is_configured(self) -> bool:
        return self.api_key is not None


class ImageServiceFactory:
    """
    图片服务工厂

    用于创建和管理不同的图片生成器
    """

    _generators: dict = {}

    @classmethod
    def register_generator(cls, name: str, generator: ImageGenerator):
        """注册生成器"""
        cls._generators[name] = generator

    @classmethod
    def get_generator(cls, name: str = "jimeng") -> ImageGenerator:
        """
        获取指定名称的生成器

        Args:
            name: 生成器名称 (jimeng, nanobanana)

        Returns:
            ImageGenerator 实例
        """
        generator = cls._generators.get(name)
        if not generator:
            raise ValueError(f"未找到生成器: {name}")
        return generator

    @classmethod
    def create_jimeng(cls, api_key: str) -> JimengGenerator:
        """创建即梦生成器"""
        generator = JimengGenerator(api_key)
        cls.register_generator("jimeng", generator)
        return generator

    @classmethod
    def create_nanobanana(cls, api_key: str) -> NanobananaGenerator:
        """创建 Nanobanana 生成器（预留）"""
        generator = NanobananaGenerator(api_key)
        cls.register_generator("nanobanana", generator)
        return generator


def create_image_generator(service_name: str, api_key: str) -> ImageGenerator:
    """
    创建图片生成器的便捷函数

    Args:
        service_name: 服务名称 (jimeng, nanobanana)
        api_key: API Key

    Returns:
        ImageGenerator 实例
    """
    if service_name.lower() == "jimeng":
        return ImageServiceFactory.create_jimeng(api_key)
    elif service_name.lower() == "nanobanana":
        return ImageServiceFactory.create_nanobanana(api_key)
    else:
        raise ValueError(f"不支持的服务: {service_name}")
