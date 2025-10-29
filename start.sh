#!/bin/sh

# ファイル名: start.sh

# --- 1. インストールとセットアップ ---

echo "必要なPythonライブラリをインストールします..."
# Flask, requests, playwright をインストール
pip install Flask requests playwright

echo "Playwrightのブラウザ（Chromium）バイナリをインストールします..."
# Playwrightが使用するブラウザの実行ファイルをインストール
playwright install chromium

# --- 2. Flaskアプリの起動 ---

echo "Flaskアプリ (main.py) を起動します..."
# 既に存在することを前提として実行
python main.py
