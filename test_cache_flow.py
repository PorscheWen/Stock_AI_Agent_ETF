#!/usr/bin/env python3
"""測試 ETF 查詢功能（快取機制）"""
import os
from dotenv import load_dotenv
from data.db import get_analysis, clear_all_cache

load_dotenv()

def test_cache_flow():
    """測試快取流程"""
    print("=" * 60)
    print("🧪 測試快取流程")
    print("=" * 60)
    
    # 1. 檢查當前快取
    symbols = ["0050", "00631L", "009816", "00981A"]
    print("\n📊 當前快取狀態：")
    for symbol in symbols:
        cached = get_analysis(symbol)
        if cached:
            analysis, updated_at = cached
            print(f"  ✅ {symbol}: {updated_at} (動作: {analysis.get('final_action', 'N/A')})")
        else:
            print(f"  ❌ {symbol}: 無快取")
    
    # 2. 提示測試步驟
    print("\n" + "=" * 60)
    print("📋 手動測試步驟：")
    print("=" * 60)
    print("\n1️⃣ 在 LINE Bot 中輸入: 0050")
    print("   預期行為：")
    print("   - 如果有快取: 立即顯示快取結果 + 提示「輸入刷新 0050 取得最新結果」")
    print("   - 如果無快取: 先顯示「⏳ 尚無 0050 快取，正在分析中...」")
    print("                然後會收到完整的 Flex 卡片分析結果（使用 push）")
    
    print("\n2️⃣ 測試刷新功能：")
    print("   輸入: 刷新 0050")
    print("   預期: 先顯示「⏳ 正在重新分析 0050，請稍候...」")
    print("         然後收到最新的 Flex 卡片結果")
    
    print("\n3️⃣ 測試全部 ETF：")
    print("   輸入: 分析")
    print("   預期: 顯示所有 ETF 的 Carousel 卡片")
    print("         如果有 ETF 沒有快取，會先分析再顯示")
    
    # 3. 詢問是否清除快取
    print("\n" + "=" * 60)
    print("🗑️  快取管理")
    print("=" * 60)
    choice = input("\n是否清除所有快取以測試無快取流程？(y/N): ").strip().lower()
    if choice == 'y':
        clear_all_cache()
        print("✅ 所有快取已清除")
        print("\n現在在 LINE Bot 中輸入 '0050' 應該會觸發即時分析流程")
    else:
        print("⏭️  保留現有快取")
    
    print("\n" + "=" * 60)
    print("✅ 測試準備完成！請在 LINE Bot 中進行手動測試")
    print("=" * 60)

if __name__ == "__main__":
    test_cache_flow()
