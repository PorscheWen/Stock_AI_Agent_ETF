#!/usr/bin/env python3
"""
Render 服務診斷工具 - 檢查所有必要設定
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def check_render_service():
    """檢查 Render 服務狀態"""
    base_url = "https://stock-ai-agent-etf.onrender.com"
    
    print("=" * 70)
    print("🔍 Render 服務診斷")
    print("=" * 70)
    
    # 1. 檢查首頁
    print("\n1️⃣ 檢查服務是否運作...")
    try:
        resp = requests.get(f"{base_url}/", timeout=10)
        if resp.status_code == 200:
            print(f"   ✅ 服務運作中：{resp.text.strip()}")
        else:
            print(f"   ❌ 服務異常：HTTP {resp.status_code}")
    except Exception as e:
        print(f"   ❌ 無法連線：{e}")
        return
    
    # 2. 檢查 Health Check
    print("\n2️⃣ 檢查健康狀態...")
    try:
        resp = requests.get(f"{base_url}/health", timeout=10)
        if resp.status_code == 200:
            print(f"   ✅ Health Check 通過")
        else:
            print(f"   ❌ Health Check 失敗：HTTP {resp.status_code}")
    except Exception as e:
        print(f"   ⚠️ Health Check 錯誤：{e}")
    
    # 3. 測試 Webhook（預期會失敗，因為沒有正確的 signature）
    print("\n3️⃣ 測試 Webhook 端點...")
    try:
        resp = requests.post(
            f"{base_url}/webhook",
            json={},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if resp.status_code == 400:
            print(f"   ✅ Webhook 正常（回傳 400 是正常的，因為缺少 LINE signature）")
        elif resp.status_code == 500:
            print(f"   ❌ Webhook 內部錯誤（500）")
            print(f"   ⚠️ 這表示 Render 環境變數設定有問題！")
            print(f"\n   可能原因：")
            print(f"   - CHANNEL_STOCK_SECRET 未設定或錯誤")
            print(f"   - DATABASE_URL 連線失敗")
            print(f"   - 缺少其他必要環境變數")
        else:
            print(f"   ⚠️ Webhook 回應異常：HTTP {resp.status_code}")
    except Exception as e:
        print(f"   ❌ Webhook 測試失敗：{e}")
    
    # 4. 建議檢查項目
    print("\n" + "=" * 70)
    print("📋 Render 環境變數檢查清單")
    print("=" * 70)
    print("\n前往 Render Dashboard > stock-ai-agent-etf > Environment")
    print("確認以下環境變數都已正確設定：\n")
    
    required_vars = [
        ("CHANNEL_STOCK_SECRET", "256e8e8c2dfc910a03bdf156cbe3f50d", True),
        ("CHANNEL_STOCK_ACCESS_TOKEN", "rqOc/NrQJkz7ID8Q...(很長)", True),
        ("DATABASE_URL", "postgresql://...", True),
    ]
    
    optional_vars = [
        ("PUSH_SECRET", "(選用)", False),
        ("ANTHROPIC_API_KEY", "(選用)", False),
    ]
    
    print("【必要】")
    for var, example, required in required_vars:
        status = "✅" if required else "☑️"
        print(f"  {status} {var:30s} = {example}")
    
    print("\n【選用】")
    for var, example, required in optional_vars:
        print(f"  ☑️ {var:30s} = {example}")
    
    print("\n" + "=" * 70)
    print("🔧 解決步驟")
    print("=" * 70)
    print("""
1. 確認 CHANNEL_STOCK_SECRET 和 CHANNEL_STOCK_ACCESS_TOKEN 已新增
   
2. 檢查值是否完整複製（特別是 ACCESS_TOKEN 很長）
   
3. 點擊「Save Changes」後等待重新部署完成
   
4. 查看 Render Logs：
   - 點擊 Render Dashboard 上方的「Logs」
   - 尋找錯誤訊息（紅色文字）
   - 查看是否有 "CHANNEL_STOCK_SECRET" 或 "DATABASE" 相關錯誤
   
5. 如果看到資料庫錯誤，確認：
   - PostgreSQL 服務是否正常運作
   - DATABASE_URL 是否正確連接
    """)
    
    print("=" * 70)
    print("💡 提示")
    print("=" * 70)
    print("""
如果更新環境變數後還是 500 錯誤，請：

1. 在 Render Dashboard 點擊「Manual Deploy」> 「Clear build cache & deploy」
   強制重新部署
   
2. 或者暫時將 app.py 中的錯誤處理改為顯示詳細錯誤訊息
   （但正式環境不建議這樣做）
    """)
    print("=" * 70)

if __name__ == "__main__":
    check_render_service()
