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
    
    apple_doc = """  *  Accounts 
  * ACAccountStore Deprecated


Class
# ACAccountStore
The object you use to request, manage, and store the user’s account information.
iOS 6.0–15.0DeprecatediPadOS 6.0–15.0DeprecatedMac Catalyst 13.1–15.0DeprecatedmacOS 10.8–12.0Deprecated
```
classACAccountStore
```

Deprecated
Use appropriate non-Apple SDK corresponding to the type of account you want to reference instead
## Overview
The `ACAccountStore` class provides an interface for accessing, managing, and storing accounts. To create and retrieve accounts from the Accounts database, you must create an `ACAccountStore` object. Each `ACAccount` object belongs to a single account store object.
## Topics
### Requesting Access
[`funcrequestAccessToAccounts(with: ACAccountType!, options: [AnyHashable : Any]!, completion: ((Bool, (any Error)?) -> Void)!)`](https://developer.apple.com/documentation/accounts/acaccountstore/requestaccesstoaccounts\(with:options:completion:\))
Obtains permission to access protected user properties.
`typealiasACAccountStoreRequestAccessCompletionHandler`
Specifies a handler to call when access is granted or denied.
### Getting Accounts
`varaccounts: NSArray!`
The accounts managed by this account store.
`funcaccount(withIdentifier: String!) -> ACAccount!`
Returns the account with the specified identifier.
[`funcaccounts(with: ACAccountType!) -> [Any]!`](https://developer.apple.com/documentation/accounts/acaccountstore/accounts\(with:\))
Returns all accounts of the specified type.
### Getting Account Types
`funcaccountType(withAccountTypeIdentifier: String!) -> ACAccountType!`
Returns an account type that matches the specified identifier.
### Saving Accounts
`funcsaveAccount(ACAccount!, withCompletionHandler: ((Bool, (any Error)?) -> Void)!)`
Saves an account to the Accounts database.
`typealiasACAccountStoreSaveCompletionHandler`
Specifies a handler to call when an Accounts database operation is complete.
### Renewing Account Credentials
`funcrenewCredentials(for: ACAccount!, completion: ((ACAccountCredentialRenewResult, (any Error)?) -> Void)!)`
Renews account credentials when the credentials are no longer valid.
`typealiasACAccountStoreCredentialRenewalHandler`
Specifies a handler to call when credentials are renewed.
`enumACAccountCredentialRenewResult`
Status codes of credential renewal requests.
### Removing Accounts
`funcremoveAccount(ACAccount!, withCompletionHandler: ((Bool, (any Error)?) -> Void)!)`
Removes an account from the account store.
`typealiasACAccountStoreRemoveCompletionHandler`
Specifies a handler to call when an account is removed from the store.
## Relationships
### Inherits From
  * `NSObject`


### Conforms To
  * `CVarArg`
  * `CustomDebugStringConvertible`
  * `CustomStringConvertible`
  * `Equatable`
  * `Hashable`
  * `NSObjectProtocol`
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
        print(f"内容预览: {chunk}")
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
