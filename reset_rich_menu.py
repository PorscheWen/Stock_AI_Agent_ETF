#!/usr/bin/env python3
"""
【已棄用】重新設定 Rich Menu（修正字型亂碼）

⚠️ 注意：本專案已改為 GitHub Actions 推播模式，不再使用 Rich Menu
此腳本保留僅供參考
"""
import os
from dotenv import load_dotenv

load_dotenv()

def reset_rich_menu():
    """刪除舊 Rich Menu 並建立新的"""
    from linebot_utils.rich_menu import delete_all_rich_menus, setup_rich_menu
    
    print("=" * 70)
    print("🔄 重新設定 Rich Menu")
    print("=" * 70)
    
    # 步驟 1: 刪除舊的 Rich Menu
    print("\n步驟 1/2: 刪除舊的 Rich Menu...")
    try:
        count = delete_all_rich_menus()
        print(f"✅ 已刪除 {count} 個舊的 Rich Menu")
    except Exception as e:
        print(f"⚠️ 刪除失敗（可能沒有舊選單）: {e}")
    
    # 步驟 2: 建立新的 Rich Menu
    print("\n步驟 2/2: 建立新的 Rich Menu（含中文字型）...")
    try:
        rich_menu_id = setup_rich_menu()
        print(f"✅ Rich Menu 設定成功！")
        print(f"   ID: {rich_menu_id}")
        print()
        print("🎉 完成！請打開 LINE Bot 查看底部選單。")
        print("   中文字應該正確顯示，不會是方框亂碼。")
    except Exception as e:
        print(f"❌ 設定失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print("=" * 70)
    print("📱 測試步驟")
    print("=" * 70)
    print("""
1. 打開 LINE Bot 聊天室
2. 查看底部的 Rich Menu
3. 確認中文字正常顯示（0050、元大台灣50、全部比較等）
4. 點擊任一按鈕測試功能

如果還是顯示亂碼，請截圖給我。
    """)
    print("=" * 70)
    return True

if __name__ == "__main__":
    import sys
    
    # 檢查環境變數
    if not os.environ.get("CHANNEL_STOCK_ACCESS_TOKEN"):
        print("❌ 環境變數 CHANNEL_STOCK_ACCESS_TOKEN 未設定")
        print("   請確認 .env 檔案已正確設定")
        sys.exit(1)
    
    success = reset_rich_menu()
    sys.exit(0 if success else 1)
