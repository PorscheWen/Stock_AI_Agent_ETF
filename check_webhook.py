#!/usr/bin/env python3
"""
檢查和設定 LINE Bot Webhook
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def check_webhook():
    """檢查當前 Webhook 設定"""
    token = os.environ.get("CHANNEL_STOCK_ACCESS_TOKEN", "")
    
    if not token:
        print("❌ CHANNEL_STOCK_ACCESS_TOKEN 未設定")
        return
    
    # 取得 Webhook 端點資訊
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # 檢查 Webhook 端點
        resp = requests.get(
            "https://api.line.me/v2/bot/channel/webhook/endpoint",
            headers=headers,
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            endpoint = data.get("endpoint", "未設定")
            active = data.get("active", False)
            
            print("=" * 60)
            print("📡 LINE Bot Webhook 狀態")
            print("=" * 60)
            print(f"Webhook URL: {endpoint}")
            print(f"狀態: {'✅ 已啟用' if active else '❌ 未啟用'}")
            print()
            
            # 測試 Webhook
            test_resp = requests.post(
                "https://api.line.me/v2/bot/channel/webhook/test",
                headers=headers,
                json={},
                timeout=10
            )
            
            if test_resp.status_code == 200:
                test_result = test_resp.json()
                success = test_result.get("success", False)
                status_code = test_result.get("statusCode", 0)
                
                print("🧪 Webhook 測試結果")
                print(f"結果: {'✅ 成功' if success else '❌ 失敗'}")
                print(f"HTTP Status: {status_code}")
                
                if not success:
                    print()
                    print("⚠️ Webhook 測試失敗，請檢查：")
                    print("1. Render 服務是否正在運作")
                    print("2. 環境變數 CHANNEL_STOCK_SECRET 是否正確")
                    print("3. LINE Developers Console 的 Webhook URL 是否正確")
            else:
                print(f"❌ 無法測試 Webhook：{test_resp.status_code}")
                
        else:
            print(f"❌ 取得 Webhook 資訊失敗：{resp.status_code}")
            print(resp.text)
            
    except Exception as e:
        print(f"❌ 錯誤：{e}")
    
    print()
    print("=" * 60)
    print("📝 手動設定步驟：")
    print("=" * 60)
    print("1. 前往 LINE Developers Console:")
    print("   https://developers.line.biz/console/")
    print()
    print("2. 選擇您的 Bot > Messaging API 設定")
    print()
    webhook_url = os.environ.get("CHANNEL_STOCK_URL", "")
    if webhook_url:
        print(f"3. Webhook URL 設定為：")
        print(f"   {webhook_url}")
    else:
        print("3. Webhook URL 設定為：")
        print("   https://stock-ai-agent-etf.onrender.com/webhook")
    print()
    print("4. 啟用「Use webhook」")
    print()
    print("5. 點擊「Verify」測試連線")
    print("=" * 60)

if __name__ == "__main__":
    check_webhook()
