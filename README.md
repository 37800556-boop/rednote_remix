# RedNote Remix - 小红书二创工具

一个基于 Streamlit 的本地桌面端 Web 应用，用于小红书内容的 AI 改写和图片生成。

## 功能特性

- 🔍 **智能爬取**: 使用 Playwright 爬取小红书笔记内容
- ✍️ **AI 改写**: 支持多种风格（吸引眼球、干货分享、情感共鸣、自定义）
- 🖼️ **图片生成**: AI 生成配图
- 📋 **一键复制**: 方便复制生成结果

## 技术架构

```
rednote_remix/
├── app.py                  # Streamlit 主应用入口
├── models.py              # Pydantic 数据模型
├── utils.py               # 辅助工具函数
├── requirements.txt       # 项目依赖
├── .env.example          # 配置文件模板
├── services/             # 服务层
│   ├── __init__.py
│   ├── scraper.py        # Playwright 爬虫服务
│   ├── ai_text.py        # 文本生成服务（策略模式）
│   └── ai_image.py       # 图片生成服务（策略模式）
```

### 设计模式

使用 **策略模式** 设计 AI 服务层，便于扩展：

- `TextGenerator` (抽象基类) → `DeepSeekGenerator` / `GeminiGenerator`(预留)
- `ImageGenerator` (抽象基类) → `JimengGenerator` / `NanobananaGenerator`(预留)

## 安装步骤

### 1. 克隆项目

```bash
cd rednote_remix
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 安装 Playwright 浏览器

```bash
playwright install chromium
```

### 4. 配置 API Keys

在侧边栏中输入：
- **DeepSeek API Key**: 用于文本生成
- **Jimeng API Key**: 用于图片生成（当前为 Mock 实现）

## 运行应用

```bash
streamlit run app.py
```

应用将在浏览器中自动打开：`http://localhost:8501`

## 使用说明

1. 输入小红书笔记 URL（如：`https://www.xiaohongshu.com/explore/...`）
2. 点击「开始解析」获取原文
3. 选择改写风格
4. 点击「生成新文本」改写内容
5. 点击「生成新图片」创建配图
6. 使用复制按钮获取结果

## API 配置说明

### DeepSeek API

访问 [DeepSeek 开放平台](https://platform.deepseek.com/) 获取 API Key。

### Jimeng API

> 注意：当前 Jimeng 生成器为 Mock 实现，返回占位图片。

需要接入真实 API 时，请编辑 `services/ai_image.py` 中的 `JimengGenerator.generate()` 方法：

```python
# 1. 填入真实的 API Endpoint
self.api_endpoint = "https://api.jimeng.example.com/v1/generate"

# 2. 配置请求头
self.headers = {
    "Authorization": f"Bearer {self.api_key}",
    "Content-Type": "application/json"
}

# 3. 实现 API 调用逻辑
# 参考 TODO 注释部分
```

## 扩展指南

### 添加新的文本生成服务

```python
# services/ai_text.py
class YourGenerator(TextGenerator):
    def generate(self, original_title, original_content, style):
        # 实现你的逻辑
        pass

    def get_name(self):
        return "YourService"

    def is_configured(self):
        return self.api_key is not None
```

### 添加新的图片生成服务

```python
# services/ai_image.py
class YourImageGenerator(ImageGenerator):
    def generate(self, prompt, count):
        # 实现你的逻辑
        pass

    def get_name(self):
        return "YourImageService"

    def is_configured(self):
        return self.api_key is not None
```

## 注意事项

1. 请遵守小红书平台规则，合理使用爬虫功能
2. API Key 请妥善保管，不要泄露
3. 建议使用无头模式运行（默认已启用）

## 许可证

MIT License
