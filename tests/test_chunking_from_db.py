#!/usr/bin/env python3
"""
数据库Chunking测试脚本

从PostgreSQL的pages表中随机选取一个page的content进行chunking测试，
生成详细的效果报告。
"""

import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

# 导入必要的模块
from chunking.chunker import SmartChunker
from database.client import create_database_client

async def get_largest_pages_content(count: int = 100):
    """从pages表中获取content最大的前N个pages"""
    client = create_database_client()

    try:
        # 初始化数据库连接
        await client.initialize()

        # 查询content最大的前N个pages
        results = await client.fetch_all("""
            SELECT url, content
            FROM pages
            WHERE content IS NOT NULL
            AND content != ''
            AND LENGTH(content) > 1000
            AND (url = 'https://developer.apple.com/documentation'
                 OR url LIKE 'https://developer.apple.com/documentation/%')
            ORDER BY LENGTH(content) DESC
            LIMIT $1
        """, count)

        if results:
            pages = []
            for result in results:
                pages.append({
                    'url': result['url'],
                    'content': result['content']
                })
            return pages
        else:
            print("❌ 没有找到符合条件的page记录")
            return []

    except Exception as e:
        print(f"❌ 数据库查询失败: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        await client.close()

def analyze_chunks(chunks):
    """分析chunks的统计信息"""
    if not chunks:
        return {
            'total_chunks': 0,
            'total_size': 0,
            'avg_size': 0,
            'min_size': 0,
            'max_size': 0,
            'size_distribution': {}
        }
    
    sizes = [len(chunk) for chunk in chunks]
    total_size = sum(sizes)
    
    # 大小分布统计
    size_ranges = {
        '0-1000': 0,
        '1001-2000': 0,
        '2001-2500': 0,
        '2501-3000': 0,
        '3001+': 0
    }
    
    for size in sizes:
        if size <= 1000:
            size_ranges['0-1000'] += 1
        elif size <= 2000:
            size_ranges['1001-2000'] += 1
        elif size <= 2500:
            size_ranges['2001-2500'] += 1
        elif size <= 3000:
            size_ranges['2501-3000'] += 1
        else:
            size_ranges['3001+'] += 1
    
    return {
        'total_chunks': len(chunks),
        'total_size': total_size,
        'avg_size': total_size // len(chunks),
        'min_size': min(sizes),
        'max_size': max(sizes),
        'size_distribution': size_ranges
    }

def analyze_context_inheritance(chunks):
    """分析context继承情况"""
    context_info = []
    
    for i, chunk in enumerate(chunks):
        try:
            data = json.loads(chunk)
            context = data.get('context', '')
            content = data.get('content', '')
            
            context_info.append({
                'chunk_id': i + 1,
                'context_length': len(context),
                'content_length': len(content),
                'context_preview': context[:100] if context else '',
                'content_preview': content[:100] if content else ''
            })
        except json.JSONDecodeError:
            context_info.append({
                'chunk_id': i + 1,
                'context_length': 0,
                'content_length': len(chunk),
                'context_preview': '',
                'content_preview': chunk[:100]
            })
    
    return context_info

def generate_batch_report(all_results, batch_stats, output_file):
    """生成批量测试的详细报告"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report_lines = [
        "=" * 80,
        "Apple文档智能分块器 - 数据库大规模测试报告（前100最大文档）",
        "=" * 80,
        f"生成时间: {timestamp}",
        f"测试策略: 新智能分块器（动态自适应策略）",
        f"数据来源: PostgreSQL数据库按content大小降序排列",
        "",
        "📊 批量测试统计摘要",
        "-" * 40,
        f"测试页面总数: {batch_stats['total_pages']}",
        f"生成chunks总数: {batch_stats['total_chunks']}",
        f"平均每页chunks: {batch_stats['avg_chunks_per_page']:.1f}",
        "",
        "📄 原始内容统计",
        "-" * 40,
        f"总原始内容: {batch_stats['total_original_size']:,} 字符",
        f"平均页面大小: {batch_stats['avg_original_size']:,} 字符",
        f"最小页面大小: {batch_stats['min_original_size']:,} 字符",
        f"最大页面大小: {batch_stats['max_original_size']:,} 字符",
        "",
        "📈 Chunk大小统计",
        "-" * 40,
        f"总chunk大小: {batch_stats['total_chunk_size']:,} 字符",
        f"平均chunk大小: {batch_stats['avg_chunk_size']:,} 字符",
        f"最小chunk大小: {batch_stats['min_chunk_size']:,} 字符",
        f"最大chunk大小: {batch_stats['max_chunk_size']:,} 字符",
        "",
        "📊 Chunk大小分布",
        "-" * 40,
    ]

    # 添加大小分布统计
    total_chunks = batch_stats['total_chunks']
    for size_range, count in batch_stats['size_distribution'].items():
        percentage = (count / total_chunks * 100) if total_chunks > 0 else 0
        report_lines.append(f"{size_range:>12}: {count:>4} chunks ({percentage:>5.1f}%)")

    report_lines.extend([
        "",
        "📝 详细页面分析",
        "-" * 40,
    ])

    # 添加每个页面的详细分析
    for i, result in enumerate(all_results, 1):
        report_lines.extend([
            f"页面 {i}: {result['url']}",
            f"  原始大小: {result['original_size']:,} 字符",
            f"  生成chunks: {result['chunk_count']} 个",
            f"  Chunk大小: {min(result['chunk_sizes'])}-{max(result['chunk_sizes'])} 字符",
            f"  平均大小: {sum(result['chunk_sizes'])//len(result['chunk_sizes'])} 字符",
            ""
        ])

    report_lines.extend([
        "🔍 Context/Content分析示例",
        "-" * 40,
    ])

    # 添加前3个页面的Context分析示例
    for i, result in enumerate(all_results[:3], 1):
        report_lines.extend([
            f"=== 页面 {i} Context分析 ===",
            f"URL: {result['url']}",
        ])

        for j, info in enumerate(result['context_info'][:2], 1):  # 只显示前2个chunks
            report_lines.extend([
                f"  Chunk {j}:",
                f"    Context长度: {info['context_length']} 字符",
                f"    Content长度: {info['content_length']} 字符",
                f"    Context预览: {info['context_preview']}",
                f"    Content预览: {info['content_preview']}",
                ""
            ])

    report_lines.append("=" * 80)

    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

def generate_report(page_info, chunks, stats, context_info, output_file):
    """生成详细的测试报告"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report_lines = [
        "=" * 80,
        "多级递进Chunking测试报告",
        "=" * 80,
        f"生成时间: {timestamp}",
        f"页面URL: {page_info['url']}",
        "",
        "📊 原始内容信息",
        "-" * 40,
        f"原始内容长度: {len(page_info['content'])} 字符",
        f"原始内容预览: {page_info['content'][:200]}...",
        "",
        "📈 Chunking统计结果",
        "-" * 40,
        f"生成chunks数量: {stats['total_chunks']}",
        f"总字符数: {stats['total_size']}",
        f"平均chunk大小: {stats['avg_size']} 字符",
        f"最小chunk大小: {stats['min_size']} 字符",
        f"最大chunk大小: {stats['max_size']} 字符",
        "",
        "📊 大小分布统计",
        "-" * 40,
    ]
    
    for size_range, count in stats['size_distribution'].items():
        percentage = (count / stats['total_chunks'] * 100) if stats['total_chunks'] > 0 else 0
        report_lines.append(f"{size_range:>12}: {count:>3} chunks ({percentage:>5.1f}%)")
    
    report_lines.extend([
        "",
        "🔍 Context继承分析",
        "-" * 40,
    ])
    
    for info in context_info:
        report_lines.extend([
            f"Chunk {info['chunk_id']}:",
            f"  Context长度: {info['context_length']} 字符",
            f"  Content长度: {info['content_length']} 字符",
            f"  Context预览: {info['context_preview']}",
            f"  Content预览: {info['content_preview']}",
            ""
        ])
    
    report_lines.extend([
        "📝 详细Chunks内容",
        "-" * 40,
    ])
    
    for i, chunk in enumerate(chunks):
        report_lines.extend([
            f"=== Chunk {i+1} ({len(chunk)} 字符) ===",
            chunk,
            ""
        ])
    
    report_lines.append("=" * 80)
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

def analyze_batch_results(all_results):
    """分析批量测试结果"""
    if not all_results:
        return {}

    # 收集所有统计数据
    all_chunk_sizes = []
    all_original_sizes = []
    total_pages = len(all_results)
    total_chunks = 0

    for result in all_results:
        all_original_sizes.append(result['original_size'])
        all_chunk_sizes.extend(result['chunk_sizes'])
        total_chunks += result['chunk_count']

    # 计算全局统计
    batch_stats = {
        'total_pages': total_pages,
        'total_chunks': total_chunks,
        'avg_chunks_per_page': total_chunks / total_pages,
        'total_original_size': sum(all_original_sizes),
        'avg_original_size': sum(all_original_sizes) // total_pages,
        'min_original_size': min(all_original_sizes),
        'max_original_size': max(all_original_sizes),
        'total_chunk_size': sum(all_chunk_sizes),
        'avg_chunk_size': sum(all_chunk_sizes) // len(all_chunk_sizes) if all_chunk_sizes else 0,
        'min_chunk_size': min(all_chunk_sizes) if all_chunk_sizes else 0,
        'max_chunk_size': max(all_chunk_sizes) if all_chunk_sizes else 0,
    }

    # 大小分布统计
    size_ranges = {
        '0-1000': 0,
        '1001-2000': 0,
        '2001-3000': 0,
        '3001-4000': 0,
        '4001-5000': 0,
        '5001+': 0
    }

    for size in all_chunk_sizes:
        if size <= 1000:
            size_ranges['0-1000'] += 1
        elif size <= 2000:
            size_ranges['1001-2000'] += 1
        elif size <= 3000:
            size_ranges['2001-3000'] += 1
        elif size <= 4000:
            size_ranges['3001-4000'] += 1
        elif size <= 5000:
            size_ranges['4001-5000'] += 1
        else:
            size_ranges['5001+'] += 1

    batch_stats['size_distribution'] = size_ranges
    return batch_stats

async def main():
    """主函数 - 批量测试"""
    print("🚀 开始数据库批量Chunking测试...")

    # 1. 获取最大content的页面
    test_count = 1000  # 测试100个页面
    print(f"📊 从数据库获取content最大的前 {test_count} 个页面...")
    pages = await get_largest_pages_content(test_count)
    if not pages:
        print("❌ 无法获取页面内容，测试终止")
        return

    print(f"✅ 获取到 {len(pages)} 个页面")

    # 2. 批量执行chunking
    print("🔧 执行批量智能chunking...")
    chunker = SmartChunker()
    all_results = []

    for i, page in enumerate(pages, 1):
        print(f"处理页面 {i}/{len(pages)}: {page['url']}...")

        chunks = chunker.chunk_text(page['content'])
        stats = analyze_chunks(chunks)
        context_info = analyze_context_inheritance(chunks)

        # 收集结果
        result = {
            'url': page['url'],
            'original_size': len(page['content']),
            'chunk_count': len(chunks),
            'chunk_sizes': [len(chunk) for chunk in chunks],
            'chunks': chunks,
            'stats': stats,
            'context_info': context_info
        }
        all_results.append(result)

    print(f"✅ 批量Chunking完成: 处理了 {len(all_results)} 个页面")

    # 3. 分析批量结果
    print("📈 分析批量结果...")
    batch_stats = analyze_batch_results(all_results)

    # 4. 生成详细报告
    output_file = project_root / 'tests' / f'chunking_batch_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    print(f"📝 生成详细报告: {output_file}")

    generate_batch_report(all_results, batch_stats, output_file)

    print("🎉 批量测试完成！")
    print(f"📊 批量统计摘要:")
    print(f"   - 测试页面数: {batch_stats['total_pages']}")
    print(f"   - 总chunks数: {batch_stats['total_chunks']}")
    print(f"   - 平均每页chunks: {batch_stats['avg_chunks_per_page']:.1f}")
    print(f"   - 平均chunk大小: {batch_stats['avg_chunk_size']} 字符")
    print(f"   - Chunk大小范围: {batch_stats['min_chunk_size']} - {batch_stats['max_chunk_size']} 字符")
    print(f"📄 详细报告: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
