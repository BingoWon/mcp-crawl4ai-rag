"""Apple内容提取器 - 专门针对Apple开发者文档的精确内容提取"""

from .apple_stealth_crawler import AppleStealthCrawler
from typing import Dict, Any
import re
from utils.logger import setup_logger

logger = setup_logger(__name__)



class AppleContentExtractor:
    """Apple开发者文档专用内容提取器"""

    def __init__(self):
        self.crawler = None

    async def __aenter__(self):
        logger.info("Initializing Apple content extractor")
        self.crawler = AppleStealthCrawler()
        await self.crawler.__aenter__()
        logger.info("Apple content extractor initialized")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.crawler:
            await self.crawler.__aexit__(exc_type, exc_val, exc_tb)
    
    async def extract_clean_content(self, url: str):
        """提取Apple文档的纯净内容"""
        logger.info(f"Extracting clean content from: {url}")
        markdown = await self.crawler.extract_content(url)
        clean_content = self._post_process_content(markdown)
        logger.info(f"Clean content extracted from: {url}")
        return clean_content
    
    def _post_process_content(self, content: str) -> str:
        """后处理内容，清理导航元素、图片内容和"See Also"部分"""
        lines = content.split('\n')

        clean_lines = []

        # 处理"See Also"截断
        see_also_index = -1
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if 'see also' in line_lower or 'see-also' in line_lower:
                see_also_index = i
                break

        if see_also_index >= 0:
            lines = lines[:see_also_index]

        for line in lines:
            # 移除图片部分，保留后面的文字：![描述](URL)文字说明
            line = re.sub(r'!\[.*?\]\([^)]+\)', '', line)

            # 清理章节标题中的URL链接
            title_url_pattern = r'^(\s*)(#{1,6})\s*\[(.*?)\]\((.*?)\)'
            match = re.match(title_url_pattern, line)
            if match:
                leading_whitespace, level, title_text, _ = match.groups()
                line = f'{leading_whitespace}{level} {title_text}'

            # 清理行内超链接：[text](url) -> text (智能处理转义括号)
            line = re.sub(r'\[([^\]]+)\]\((?:[^)\\]|\\.)*\)', r'\1', line)

            clean_lines.append(line)

        return '\n'.join(clean_lines)
    
