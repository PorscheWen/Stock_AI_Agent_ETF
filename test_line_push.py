#!/usr/bin/env python3
"""
測試 LINE 推播功能
使用方式：python test_line_push.py
"""
import os
from dotenv import load_dotenv
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
)

load_dotenv()

def test_line_push():
    """測試 LINE 推播是否正常"""
    
    # 1. 檢查環境變數
    print("🔍 檢查環境變數...")
    
    secret = os.environ.get("CHANNEL_STOCK_SECRET", "")
    token = os.environ.get("CHANNEL_STOCK_ACCESS_TOKEN", "")
    user_id = os.environ.get("CHANNEL_STOCK_USER_ID", "")
    
    if not secret:
        print("❌ CHANNEL_STOCK_SECRET 未設定")
        return False
    else:
        print(f"✅ CHANNEL_STOCK_SECRET: {secret[:10]}...")
    
    if not token:
        print("❌ CHANNEL_STOCK_ACCESS_TOKEN 未設定")
        return False
    else:
        print(f"✅ CHANNEL_STOCK_ACCESS_TOKEN: {token[:20]}...")
    
    if not user_id:
        print("❌ CHANNEL_STOCK_USER_ID 未設定")
        return False
    else:
        print(f"✅ CHANNEL_STOCK_USER_ID: {user_id}")
    
    # 2. 測試推播
    print("\n📤 發送測試訊息...")
    try:
        config = Configuration(access_token=token)
        api = MessagingApi(ApiClient(config))
        
        api.push_message(PushMessageRequest(
            to=user_id,
            messages=[TextMessage(text="✅ LINE 推播測試成功！\n\nETF AI Bot 已正確設定。")]
        ))
        
        print("✅ 推播成功！請檢查您的 LINE 訊息。")
        return True
        
    except Exception as e:
        print(f"❌ 推播失敗：{e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("LINE 推播測試工具")
    print("=" * 50)
    
    success = test_line_push()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 測試完成！推播功能正常。")
    else:
        print("⚠️ 測試失敗，請檢查設定。")
    print("=" * 50)
