#!/usr/bin/env python3
"""
YouTube Subtitles Extractor for Apple Developer Channel
YouTube字幕提取器 - Apple Developer频道专用

功能：
- 提取YouTube视频字幕（优先人工生成，备选自动生成英文）
- 输出纯文本格式，无时间戳，无分段
- 支持单个视频测试和批量处理
"""

import os
import sys
import subprocess
import re
import json
import time
import random
from pathlib import Path
from typing import Optional, List, Dict
import argparse


class YouTubeSubtitleExtractor:
    """YouTube字幕提取器"""
    
    def __init__(self, output_dir: str = "subtitles"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def extract_subtitle_for_video(self, video_id: str) -> Optional[Dict[str, str]]:
        """
        提取单个视频的字幕和标题

        Args:
            video_id: YouTube视频ID

        Returns:
            包含标题和字幕的字典，如果提取失败返回None
        """
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        print(f"🎬 处理视频: {video_id}")
        print(f"📺 URL: {video_url}")

        # 获取视频标题
        video_title = self._get_video_title(video_url)
        if not video_title:
            print(f"❌ 无法获取视频 {video_id} 的标题")
            return None

        print(f"📋 视频标题: {video_title}")

        # 检查可用的字幕
        available_subs = self._get_available_subtitles(video_url)
        if not available_subs:
            print(f"❌ 视频 {video_id} 没有可用字幕")
            return None

        print(f"📝 可用字幕: {', '.join(available_subs)}")

        # 按优先级选择字幕
        subtitle_lang = self._select_best_subtitle(available_subs)
        if not subtitle_lang:
            print(f"❌ 视频 {video_id} 没有合适的英文字幕")
            return None

        print(f"✅ 选择字幕: {subtitle_lang} (优先级: {'手动制作' if self._is_manual_subtitle(subtitle_lang) else '自动生成'})")

        # 下载字幕
        subtitle_content = self._download_subtitle(video_url, subtitle_lang, video_id)
        if subtitle_content:
            print(f"✅ 字幕提取成功: {len(subtitle_content)} 字符")
            return {
                "context": video_title,
                "content": subtitle_content
            }
        else:
            print("❌ 字幕提取失败")
            return None

    def _get_video_title(self, video_url: str) -> Optional[str]:
        """获取视频标题"""
        try:
            cmd = [
                "yt-dlp",
                "--get-title",
                "--cookies-from-browser", "chrome",
                video_url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                print(f"⚠️ 获取视频标题失败: {result.stderr}")
                return None

            title = result.stdout.strip()
            return title if title else None

        except subprocess.TimeoutExpired:
            print("⚠️ 获取视频标题超时")
            return None
        except Exception as e:
            print(f"⚠️ 获取视频标题出错: {e}")
            return None

    def _is_manual_subtitle(self, lang: str) -> bool:
        """判断是否为手动制作的字幕"""
        # 自动生成字幕的标识符
        auto_indicators = ['auto', 'orig', 'a.']
        return not any(indicator in lang.lower() for indicator in auto_indicators)

    def _get_available_subtitles(self, video_url: str) -> List[str]:
        """获取视频可用的字幕列表"""
        try:
            cmd = [
                "yt-dlp",
                "--list-subs",
                "--cookies-from-browser", "chrome",  # 使用Chrome浏览器的cookies
                video_url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"⚠️ 获取字幕列表失败: {result.stderr}")
                return []
            
            # 解析字幕列表
            subtitles = []
            lines = result.stdout.split('\n')
            
            for line in lines:
                # 查找字幕语言行，格式类似: "en-US    English (United States)"
                if re.match(r'^[a-z]{2}(-[A-Z]{2})?\s+', line):
                    lang_code = line.split()[0]
                    subtitles.append(lang_code)
            
            return subtitles
            
        except subprocess.TimeoutExpired:
            print("⚠️ 获取字幕列表超时")
            return []
        except Exception as e:
            print(f"⚠️ 获取字幕列表出错: {e}")
            return []
    
    def _select_best_subtitle(self, available_subs: List[str]) -> Optional[str]:
        """
        选择最佳字幕语言
        优先级：人工生成英文 > 自动生成英文
        """
        # 优先级列表：人工生成的英文字幕
        manual_priority = ['en', 'en-US', 'en-GB', 'en-CA', 'en-AU']
        
        # 检查人工生成的英文字幕
        for lang in manual_priority:
            if lang in available_subs:
                return lang
        
        # 如果没有人工生成的，查找自动生成的英文字幕
        # yt-dlp中自动生成的字幕通常有特殊标记，但我们先尝试标准英文代码
        auto_priority = ['en-orig', 'en-auto', 'a.en', 'auto-en']
        
        for lang in auto_priority:
            if lang in available_subs:
                return lang
        
        # 最后尝试任何包含'en'的字幕
        for lang in available_subs:
            if 'en' in lang.lower():
                return lang
        
        return None
    
    def _download_subtitle(self, video_url: str, lang: str, video_id: str) -> Optional[str]:
        """下载并处理字幕"""
        try:
            # 临时文件路径
            temp_subtitle_file = self.output_dir / f"{video_id}_{lang}.vtt"
            
            # 下载字幕
            cmd = [
                "yt-dlp",
                "--write-subs",
                "--write-auto-subs",  # 也尝试自动生成的字幕
                "--sub-langs", lang,
                "--sub-format", "vtt",  # 使用VTT格式，更容易解析
                "--skip-download",  # 只下载字幕，不下载视频
                "--cookies-from-browser", "chrome",  # 使用Chrome浏览器的cookies
                "-o", str(self.output_dir / f"{video_id}.%(ext)s"),
                video_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                print(f"⚠️ 下载字幕失败: {result.stderr}")
                return None
            
            # 查找下载的字幕文件
            subtitle_files = list(self.output_dir.glob(f"{video_id}*.vtt"))
            if not subtitle_files:
                print(f"⚠️ 未找到下载的字幕文件")
                return None
            
            subtitle_file = subtitle_files[0]  # 使用第一个找到的文件
            
            # 处理字幕内容
            processed_content = self._process_subtitle_content(subtitle_file)
            
            # 清理临时文件
            try:
                subtitle_file.unlink()
            except:
                pass
            
            return processed_content
            
        except subprocess.TimeoutExpired:
            print("⚠️ 下载字幕超时")
            return None
        except Exception as e:
            print(f"⚠️ 下载字幕出错: {e}")
            return None
    
    def _process_subtitle_content(self, subtitle_file: Path) -> str:
        """
        处理字幕内容，移除时间戳和格式标记
        输出纯文本内容
        """
        try:
            with open(subtitle_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 处理VTT格式字幕
            lines = content.split('\n')
            subtitle_text = []
            
            for line in lines:
                line = line.strip()
                
                # 跳过VTT头部信息
                if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
                    continue
                
                # 跳过时间戳行 (格式: 00:00:00.000 --> 00:00:00.000)
                if '-->' in line:
                    continue
                
                # 跳过空行和数字行（序号）
                if not line or line.isdigit():
                    continue
                
                # 清理HTML标签和格式标记
                line = re.sub(r'<[^>]+>', '', line)  # 移除HTML标签
                line = re.sub(r'\{[^}]+\}', '', line)  # 移除样式标记
                line = re.sub(r'&[a-zA-Z]+;', '', line)  # 移除HTML实体
                
                # 清理多余的空格
                line = ' '.join(line.split())
                
                if line:
                    subtitle_text.append(line)
            
            # 合并所有文本，用空格连接
            final_text = ' '.join(subtitle_text)
            
            # 最终清理：移除多余空格，确保句子间有适当间隔
            final_text = re.sub(r'\s+', ' ', final_text)
            final_text = final_text.strip()
            
            return final_text
            
        except Exception as e:
            print(f"⚠️ 处理字幕内容出错: {e}")
            return ""
    
    def save_subtitle_to_file(self, video_id: str, subtitle_data: Dict[str, str]) -> str:
        """保存字幕到JSON文件"""
        output_file = self.output_dir / f"{video_id}.json"

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(subtitle_data, f, ensure_ascii=False, indent=2)

            print(f"💾 字幕已保存: {output_file}")
            return str(output_file)

        except Exception as e:
            print(f"❌ 保存字幕失败: {e}")
            return ""

    def batch_extract_subtitles(self, video_ids_file: str,
                               output_dir: str = "subtitles",
                               delay_min: float = 2.0,
                               delay_max: float = 5.0,
                               max_retries: int = 3) -> Dict[str, int]:
        """
        批量提取字幕

        Args:
            video_ids_file: 视频ID列表文件路径
            output_dir: 输出目录
            delay_min: 最小延迟时间（秒）
            delay_max: 最大延迟时间（秒）
            max_retries: 最大重试次数

        Returns:
            统计结果字典
        """
        # 设置输出目录
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # 读取视频ID列表
        video_ids = self._load_video_ids(video_ids_file)
        if not video_ids:
            print("❌ 无法读取视频ID列表")
            return {"total": 0, "success": 0, "failed": 0, "skipped": 0}

        print(f"📋 准备处理 {len(video_ids)} 个视频")
        print(f"⏱️ 延迟设置: {delay_min}-{delay_max} 秒")
        print(f"🔄 最大重试次数: {max_retries}")
        print(f"📁 输出目录: {output_dir}")
        print("=" * 60)

        # 统计信息
        stats = {"total": len(video_ids), "success": 0, "failed": 0, "skipped": 0}
        failed_videos = []

        # 进度文件
        progress_file = self.output_dir / "progress.json"
        processed_videos = self._load_progress(progress_file)

        for i, video_id in enumerate(video_ids, 1):
            print(f"\n[{i}/{len(video_ids)}] 处理视频: {video_id}")

            # 检查是否已处理
            output_file = self.output_dir / f"{video_id}.json"
            if output_file.exists():
                print(f"⏭️ 跳过已存在的文件: {output_file}")
                stats["skipped"] += 1
                continue

            # 检查是否在失败列表中
            if video_id in processed_videos.get("failed", []):
                print(f"⏭️ 跳过之前失败的视频: {video_id}")
                stats["skipped"] += 1
                continue

            # 尝试提取字幕
            success = False
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        print(f"🔄 重试 {attempt + 1}/{max_retries}")

                    subtitle_data = self.extract_subtitle_for_video(video_id)

                    if subtitle_data:
                        # 保存文件
                        saved_file = self.save_subtitle_to_file(video_id, subtitle_data)
                        if saved_file:
                            print(f"✅ 成功: {video_id}")
                            stats["success"] += 1
                            success = True
                            break

                except Exception as e:
                    print(f"⚠️ 尝试 {attempt + 1} 失败: {e}")

                # 重试前等待
                if attempt < max_retries - 1:
                    retry_delay = random.uniform(delay_min * 2, delay_max * 2)
                    print(f"⏳ 重试前等待 {retry_delay:.1f} 秒...")
                    time.sleep(retry_delay)

            if not success:
                print(f"❌ 失败: {video_id}")
                stats["failed"] += 1
                failed_videos.append(video_id)
                # 更新失败列表
                self._save_failed_video(progress_file, video_id)

            # 随机延迟，避免被检测
            # if i < len(video_ids):  # 最后一个视频不需要延迟
            #     delay = random.uniform(delay_min, delay_max)
            #     print(f"⏳ 等待 {delay:.1f} 秒...")
            #     time.sleep(delay) 

        # 输出最终统计
        print("\n" + "=" * 60)
        print("📊 批量处理完成统计:")
        print(f"   总计: {stats['total']}")
        print(f"   成功: {stats['success']}")
        print(f"   失败: {stats['failed']}")
        print(f"   跳过: {stats['skipped']}")
        print(f"   成功率: {stats['success'] / stats['total'] * 100:.1f}%")

        if failed_videos:
            print(f"\n❌ 失败的视频 ({len(failed_videos)} 个):")
            for video_id in failed_videos[:10]:  # 只显示前10个
                print(f"   - {video_id}")
            if len(failed_videos) > 10:
                print(f"   ... 还有 {len(failed_videos) - 10} 个")

        return stats

    def _load_video_ids(self, file_path: str) -> List[str]:
        """加载视频ID列表"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                video_ids = [line.strip() for line in f if line.strip()]
            return video_ids
        except Exception as e:
            print(f"❌ 读取视频ID文件失败: {e}")
            return []

    def _load_progress(self, progress_file: Path) -> Dict:
        """加载进度信息"""
        try:
            if progress_file.exists():
                with open(progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {"failed": []}

    def _save_failed_video(self, progress_file: Path, video_id: str):
        """保存失败的视频ID"""
        try:
            progress = self._load_progress(progress_file)
            if "failed" not in progress:
                progress["failed"] = []
            if video_id not in progress["failed"]:
                progress["failed"].append(video_id)

            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 保存进度失败: {e}")


def test_single_video(video_id: str):
    """测试单个视频的字幕提取"""
    print(f"🧪 测试模式：提取视频 {video_id} 的字幕")
    print("=" * 50)

    extractor = YouTubeSubtitleExtractor("test_output")

    # 提取字幕
    subtitle_data = extractor.extract_subtitle_for_video(video_id)

    if subtitle_data:
        # 保存到文件
        output_file = extractor.save_subtitle_to_file(video_id, subtitle_data)

        print("\n" + "=" * 50)
        print("✅ 测试完成！")
        print(f"📁 输出文件: {output_file}")
        print(f"📋 视频标题: {subtitle_data['context']}")
        print(f"📊 字幕长度: {len(subtitle_data['content'])} 字符")
        print("📝 前200字符预览:")
        print("-" * 30)
        content = subtitle_data['content']
        print(content[:200] + "..." if len(content) > 200 else content)
        print("-" * 30)

        return True
    else:
        print("\n" + "=" * 50)
        print("❌ 测试失败：无法提取字幕")
        return False


def batch_process_videos(video_list_file: str):
    """批量处理视频"""
    print(f"🚀 开始批量处理视频字幕提取...")
    print(f"📋 视频列表文件: {video_list_file}")

    extractor = YouTubeSubtitleExtractor()

    # 执行批量提取
    stats = extractor.batch_extract_subtitles(
        video_ids_file=video_list_file,
        output_dir="subtitles",
        delay_min=2.0,  # 最小延迟2秒
        delay_max=5.0,  # 最大延迟5秒
        max_retries=3   # 最大重试3次
    )

    print(f"\n🎉 批量处理完成！")
    return stats["success"] > 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="YouTube字幕提取器")
    parser.add_argument("--test", type=str, help="测试模式：提取指定视频ID的字幕")
    parser.add_argument("--batch", type=str, help="批量模式：处理视频ID列表文件")
    parser.add_argument("--video-list", type=str, help="视频ID列表文件路径（兼容旧参数）")

    args = parser.parse_args()

    if args.test:
        # 测试模式
        success = test_single_video(args.test)
        sys.exit(0 if success else 1)

    elif args.batch or args.video_list:
        # 批量处理模式
        video_file = args.batch or args.video_list
        success = batch_process_videos(video_file)
        sys.exit(0 if success else 1)

    else:
        print("请指定操作模式：")
        print("  测试模式: python extract_subtitles.py --test VIDEO_ID")
        print("  批量模式: python extract_subtitles.py --batch video_ids.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()
