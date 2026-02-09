"""
数据模型定义
使用 Pydantic 定义项目中使用的数据结构
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class NoteData(BaseModel):
    """小红书笔记数据模型"""
    url: str = Field(description="笔记URL")
    title: str = Field(default="", description="笔记标题")
    content: str = Field(default="", description="笔记正文内容")
    images: List[str] = Field(default_factory=list, description="图片URL列表")
    author: Optional[str] = Field(default=None, description="作者名称")
    likes: Optional[int] = Field(default=None, description="点赞数")
    collected_at: datetime = Field(default_factory=datetime.now, description="采集时间")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.xiaohongshu.com/explore/123456",
                "title": "示例标题",
                "content": "示例正文内容",
                "images": ["https://example.com/image1.jpg"]
            }
        }


class RemixStyle(BaseModel):
    """改写风格配置"""
    style_type: Literal["attractive", "knowledge", "emotional", "custom"] = Field(
        default="attractive",
        description="风格类型: attractive=吸引眼球, knowledge=干货分享, emotional=情感共鸣, custom=自定义"
    )
    custom_prompt: str = Field(default="", description="自定义补充提示词")


class RemixedContent(BaseModel):
    """改写后的内容模型"""
    original_title: str = Field(description="原标题")
    new_title: str = Field(default="", description="新标题")
    original_content: str = Field(description="原文内容")
    new_content: str = Field(default="", description="新内容")
    generated_images: List[str] = Field(default_factory=list, description="AI生成的图片URL列表")
    style_used: Optional[RemixStyle] = Field(default=None, description="使用的改写风格")
    created_at: datetime = Field(default_factory=datetime.now, description="生成时间")


class RemixOptions(BaseModel):
    """改写选项模型"""
    style: RemixStyle = Field(default_factory=RemixStyle, description="改写风格配置")
    generate_image: bool = Field(default=True, description="是否生成图片")
    image_count: int = Field(default=1, ge=1, le=4, description="生成图片数量")
