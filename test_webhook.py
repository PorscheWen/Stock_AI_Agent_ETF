#!/usr/bin/env python3
"""
模擬 LINE Webhook 請求測試 Render 服務
"""
import requests
import json
import hashlib
import hmac
import base64
import os
from dotenv import load_dotenv

load_dotenv()

def simulate_line_webhook():
    """模擬 LINE Bot 傳送文字訊息到 Webhook"""
    
    webhook_url = "https://stock-ai-agent-etf.onrender.com/webhook"
    channel_secret = os.environ.get("CHANNEL_STOCK_SECRET", "")
    
    if not channel_secret:
        print("❌ 本地 CHANNEL_STOCK_SECRET 未設定")
        return
    
    # 模擬 LINE webhook 請求 body
    webhook_body = {
        "events": [
            {
                "type": "message",
                "message": {
                    "type": "text",
                    "id": "test123",
                    "text": "0050"
                },
                "timestamp": 1650000000000,
                "source": {
                    "type": "user",
                    "userId": os.environ.get("CHANNEL_STOCK_USER_ID", "Utest")
                },
                "replyToken": "test-reply-token",
                "mode": "active"
            }
        ],
        "destination": "test"
    }
    
    body_str = json.dumps(webhook_body)
    
    # 計算 LINE signature
    signature = base64.b64encode(
        hmac.new(
            channel_secret.encode('utf-8'),
            body_str.encode('utf-8'),
            hashlib.sha256
        ).digest()
    ).decode('utf-8')
    
    # 發送請求
    print("=" * 70)
    print("🧪 模擬 LINE Webhook 請求")
    print("=" * 70)
    print(f"\n目標: {webhook_url}")
    print(f"訊息: 0050")
    print(f"User ID: {webhook_body['events'][0]['source']['userId']}")
    print(f"\n發送中...")
    
    try:
        response = requests.post(
            webhook_url,
            data=body_str,
            headers={
                "Content-Type": "application/json",
                "X-Line-Signature": signature,
            },
            timeout=30
        )
        
        print(f"\n回應狀態: HTTP {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Webhook 處理成功！")
            print(f"回應: {response.text}")
        elif response.status_code == 400:
            print("⚠️ 請求格式錯誤（400）")
            print(f"詳情: {response.text[:500]}")
        elif response.status_code == 500:
            print("❌ 伺服器內部錯誤（500）")
            print("\n這表示 Render 服務有錯誤！")
            print("請查看 Render Logs 獲取詳細錯誤訊息。")
            print("\n可能原因：")
            print("  1. CHANNEL_STOCK_SECRET 設定錯誤")
            print("  2. CHANNEL_STOCK_ACCESS_TOKEN 未設定")
            print("  3. DATABASE_URL 連線失敗")
            print("  4. Python 代碼錯誤")
        else:
            print(f"⚠️ 未預期的回應：{response.status_code}")
            print(f"詳情: {response.text[:500]}")
            
    except requests.exceptions.Timeout:
        print("❌ 請求逾時（超過 30 秒）")
        print("Render 服務可能正在處理，但太慢了")
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
    
    print("\n" + "=" * 70)
    print("💡 下一步")
    print("=" * 70)
    print("""
如果看到 500 錯誤：

1. 前往 Render Dashboard
   https://dashboard.render.com/

2. 點擊 stock-ai-agent-etf > Logs

3. 查看最新的紅色錯誤訊息

4. 將錯誤訊息複製給我，我會幫您解決

如果看到 200 成功：
   
   恭喜！服務正常運作。
   請在 LINE Bot 直接測試輸入「0050」
    """)
    print("=" * 70)

if __name__ == "__main__":
    simulate_line_webhook()
