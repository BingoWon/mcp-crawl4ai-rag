#!/usr/bin/env python3
"""
测试Apple文档双井号分块策略
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chunking import SmartChunker


def test_real_apple_doc():
    """测试真实的Apple文档内容"""
    print("🧪 测试真实Apple文档分块...")
    
    apple_doc = """# Accounts
Help users access and manage their external accounts from within your app, without requiring them to enter login credentials.
iOS 5.0+iPadOS 5.0+Mac Catalyst 13.0+macOS 10.8+
Deprecated
The Accounts framework is deprecated. For new apps, instead of using Accounts, contact the provider of the service you integrate with, to get access to their SDK or documentation about managing accounts with their service.
## Overview
The Accounts framework provides access to user accounts stored in the Accounts database, which is managed by the system. An account stores the login credentials of a particular service, such as LinkedIn, and you use those credentials to authenticate with the service. When you integrate the Accounts framework into your app, you don’t need to store account logins yourself. Instead, the user grants your app access to use their account login credentials, bypassing the need to type their username and password. If no account for a particular service exists in the user’s Accounts database, you can let them create and save an account from within your app.
## Topics
### Account Management
`classACAccountStore`
The object you use to request, manage, and store the user’s account information.
`classACAccount`
The information associated with one of the user’s accounts.
`classACAccountCredential`
A credential object that encapsulates the information needed to authenticate a user.
### Account Types
`classACAccountType`
An object that encapsulates information about all accounts of a particular type.
### Errors
`structACErrorCode`
Codes for errors that may occur.
`letACErrorDomain: String`
The error domain for the Accounts framework.
### Deprecated
API ReferenceDeprecated Symbols
Avoid using deprecated symbols in your apps.
"""
    
    chunker = SmartChunker()
    chunks = chunker.chunk_text_simple(apple_doc)
    
    print(f"分块结果: {len(chunks)} 个块")
    print()
    
    for i, chunk in enumerate(chunks, 1):
        print(f"=== 块 {i} ===")
        print(f"长度: {len(chunk)} 字符")
        
        # 检查结构
        lines = chunk.split('\n')
        has_title = any(line.startswith('# ') for line in lines)
        has_overview = any(line.strip() == '## Overview' for line in lines)
        section_headers = [line for line in lines if line.startswith('## ') and line.strip() != '## Overview']
        
        print(f"包含大标题: {'✅' if has_title else '❌'}")
        print(f"包含Overview: {'✅' if has_overview else '❌'}")
        print(f"章节标题: {section_headers[0] if section_headers else '无'}")
        print(f"内容预览: {chunk}...")
        print()
    
    # 验证预期结果
    expected_sections = [
        "Choose a playback approach",
        "Configure video player to play immersive media", 
        "Size video for the shared space",
        "Customize playback controls",
        "Preserve motion comfort"
    ]
    
    # assert len(chunks) == len(expected_sections), f"应该有{len(expected_sections)}个块，实际有{len(chunks)}个"
    
    # 验证每个块都包含完整结构
    for chunk in chunks:
        assert "## Overview" in chunk, "每个块都应该包含Overview"
    
    print("✅ 真实Apple文档分块测试通过！")


if __name__ == "__main__":
    test_real_apple_doc()
