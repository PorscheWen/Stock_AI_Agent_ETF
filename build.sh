#!/bin/bash
# Render 部署腳本 - 安裝中文字型和 Python 依賴

set -e  # 遇到錯誤立即退出

echo "📦 開始部署..."

# 檢查是否為 Render 環境（或其他 Debian/Ubuntu 系統）
if command -v apt-get &> /dev/null; then
    echo "🔤 安裝中文字型..."
    
    # 更新包列表
    apt-get update -qq
    
    # 安裝 Noto Sans CJK 字型（包含繁體中文）
    apt-get install -y -qq fonts-noto-cjk fonts-noto-cjk-extra
    
    echo "✅ 中文字型安裝完成"
    
    # 列出已安裝的字型（除錯用）
    fc-list | grep -i noto | grep -i tc | head -3 || echo"⚠️ 字型列表查詢失敗"
else
    echo "⚠️ 非 Linux 環境，跳過字型安裝"
fi

echo "📚 安裝 Python 依賴..."
pip install -q -r requirements.txt

echo "✅ 部署完成！"
