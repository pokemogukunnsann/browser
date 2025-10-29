import os
import re
import json
import urllib.parse
from flask import Flask, request, redirect, url_for, session, render_template_string
from playwright.sync_api import sync_playwright

# Flaskアプリケーションの初期化
app = Flask(__name__)

# 💡 ユーザー情報に基づき、シークレットキーを特定の値に設定
app.secret_key = 'your_super_secret_key_kakaomame'
print(f"app.secret_key:{app.secret_key}")

# Playwrightで取得したHTMLコンテンツを格納するグローバル変数（簡易的なキャッシュとして使用）
# 🚨 実際の本番環境ではデータベースやRedisなどを使用してください
global_html_content = ""

# 基本的なHTMLテンプレート（JavaScriptでブラウザ情報を取得・送信する機能付き）
INDEX_HTML_WITH_JS = """
<!doctype html>
<title>🌐 Web Browser (Playwright)</title>
<h1>🌐 URL入力フォームとブラウザ情報取得</h1>
<p>アクセスしたいURLを入力してください（例: inv.nadeko.net/embed/ei4FYvCWoZA）</p>

<form id="url-form" method="POST" action="/submit_url">
    <input type="text" id="url_input" name="url_input" placeholder="URLを入力" style="width: 80%; padding: 10px;">
    <button type="submit" style="padding: 10px;">アクセス開始</button>
    <input type="hidden" id="screen_info" name="screen_info">
    <input type="hidden" id="timezone_info" name="timezone_info">
    <input type="hidden" id="user_agent_from_js" name="user_agent_from_js">
</form>

<hr>
<h2>⬇️ 最新のブラウザ情報とコンテンツ ⬇️</h2>

{% if html_content %}
    <details open>
        <summary>✅ 取得成功: 200 OK</summary>
        <p><strong>アクセス先:</strong> {{ target_url }}</p>
        <p><strong>状況:</strong> ヘッドレスブラウザでボットチェックを突破しました</p>
        <p><strong>HTMLコンテンツ（抜粋 0-500文字）</strong></p>
        <pre>{{ html_content[:500] | e }}...</pre>
        <a href="/">↩ 別のURLを試す</a>
    </details>
{% elif error_message %}
    <details open>
        <summary>❌ エラーが発生しました</summary>
        <p style="color: red;"><strong>エラーメッセージ:</strong> {{ error_message | e }}</p>
        <a href="/">↩ 別のURLを試す</a>
    </details>
{% else %}
    <p>URLを入力してPlaywrightによるアクセスを開始してください。</p>
{% endif %}

<script>
    // フォーム送信前にブラウザ情報を取得して隠しフィールドに格納
    document.addEventListener('DOMContentLoaded', function() {
        const screenInfoField = document.getElementById('screen_info');
        const timezoneInfoField = document.getElementById('timezone_info');
        const userAgentField = document.getElementById('user_agent_from_js');

        screenInfoField.value = `${window.screen.width}x${window.screen.height}`;
        timezoneInfoField.value = Intl.DateTimeFormat().resolvedOptions().timeZone;
        userAgentField.value = navigator.userAgent;
    });
</script>
"""
# テンプレートの抜粋を出力（デバッグ用）
print(f"INDEX_HTML_WITH_JS (partial): {INDEX_HTML_WITH_JS[:250]}")

# --- ルーティング ---

@app.route('/')
def index():
    """トップページ: URL入力フォームを表示"""
    print("index.htmlを表示中")
    return render_template_string(
        INDEX_HTML_WITH_JS,
        html_content=global_html_content,
        target_url=session.get('target_url')
    )

@app.route('/submit_url', methods=['POST'])
def submit_url():
    """フォームデータを受け取り、Playwright実行ルートへリダイレクト"""
    global global_html_content
    global_html_content = ""  # コンテンツをリセット

    url_input = request.form.get('url_input', '').strip()
    screen_info = request.form.get('screen_info')
    timezone_info = request.form.get('timezone_info')
    user_agent_from_js = request.form.get('user_agent_from_js')

    # ユーザー入力を解析
    match = re.match(r'^(?:https?://)?([^/]+)(/.*)?$', url_input)
    
    if not match:
        return render_template_string(INDEX_HTML_WITH_JS, error_message="無効なURL形式です。")

    base_url = match.group(1)
    path_input = match.group(2) if match.group(2) else ''

    print("データを受け取りました。このデータを使ってリダイレクトします。")
    print(f"base_url:{base_url}")
    print(f"path_input:{path_input}")
    
    # セッションにブラウザ情報を保存 (Playwrightに渡すため)
    width, height = map(int, screen_info.split('x')) if screen_info and 'x' in screen_info else (1920, 1080)
    
    session['browser_info'] = {
        'User-Agent': user_agent_from_js,
        'Screen-Width': width,
        'Screen-Height': height,
        'Timezone-Id': timezone_info
    }
    print(f"base_url:{base_url}")
    print(f"path_input:{path_input}")
    print(f"screen_info:{screen_info}")
    print(f"timezone_info:{timezone_info}")
    print(f"user_agent_from_js:{user_agent_from_js}")
    print(f"session['browser_info']:{session['browser_info']}")

    # Playwright実行ルートへリダイレクト
    full_route = f'/browser/{base_url}{path_input}'
    print(f"full_route:{full_route}")
    return redirect(full_route)


@app.route('/browser/<path:full_url_path>')
def browser_access(full_url_path):
    """Playwrightでウェブページにアクセスし、結果をセッションに保存"""
    global global_html_content
    browser_info = session.get('browser_info', {})

    # URLの再構築 (常にHTTPSを試みる)
    target_url = f"https://{full_url_path}"
    session['target_url'] = target_url # テンプレート表示用に保存
    print(f"target_url:{target_url}")
    print(f" 🔐　悪用現金　🈲　browser_info:{browser_info}") # ユーザー情報の確認

    # Playwrightによるウェブアクセス
    try:
        with sync_playwright() as p:
            # 💡 Render/Docker環境での安定化と軽量化のためのオプション
            # --no-sandbox, --disable-setuid-sandbox, --disable-dev-shm-usage は必須
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox', 
                    '--disable-setuid-sandbox', 
                    '--disable-dev-shm-usage'
                ]
            )
            
            # ブラウザ情報をコンテキストオプションとして設定
            context = browser.new_context(
                user_agent=browser_info.get('User-Agent', None),  # フォームから取得したUA
                viewport={
                    'width': browser_info.get('Screen-Width', 1920), 
                    'height': browser_info.get('Screen-Height', 1080)
                },
                locale='ja-JP',
                timezone_id=browser_info.get('Timezone-Id', 'Asia/Tokyo')
            )
            print(f"Context options:{context.options}")

            page = context.new_page()

            # 💡 ボット対策突破のため、ネットワークが落ち着くまで待機し、タイムアウトも長めに設定
            page.goto(
                target_url, 
                wait_until="networkidle", 
                timeout=60000 # 60秒
            )

            # 最終的なHTMLを取得
            html_content = page.content()
            global_html_content = html_content  # グローバル変数に保存

            # クッキーの処理は省略（必要に応じて追加してください）
            print(f"New cookies saved from Playwright: 0 items.")
            
            browser.close()

    except Exception as e:
        error_msg = f"Playwrightエラーが発生しました: {e}"
        print(f"🚨 {error_msg}")
        return render_template_string(INDEX_HTML_WITH_JS, error_message=error_msg)

    # 成功したらトップページにリダイレクトして結果を表示
    return redirect(url_for('index'))

# --- アプリケーション実行 ---

if __name__ == '__main__':
    # 開発環境での実行
    app.run(debug=True)

# Renderデプロイでは gunicorn main:app が実行される
# gunicorn main:app --timeout 180 --workers 1 の実行を想定
