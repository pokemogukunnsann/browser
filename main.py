from flask import Flask, request, render_template_string, redirect, url_for, session
import requests
import json
import http.cookiejar as cookiejar
# 🚨 Playwrightをインポート
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

app = Flask(__name__)
# 🚨 セッションを使うための秘密鍵を設定
app.secret_key = 'your_super_secret_key_kakaomame' 
print(f"app.secret_key:{app.secret_key}")

# --- HTMLテンプレート（Pythonの文字列として定義） ---
# ⚠️ User-AgentはPlaywrightで設定するため、ここでは不要なカスタムヘッダーは削除
INDEX_HTML_WITH_JS = """
<!doctype html>
<title>🌐 Web Browser (Playwright)</title>
<h1>🌐 URL入力フォームとブラウザ情報取得</h1>
<p>アクセスしたいURLを入力してください。ブラウザ情報を取得し、ヘッドレスブラウザでアクセスします。</p>
<form method="POST" action="/submit_url" id="browser-form">
    <label for="base_url">ベースURL (例: example.com):</label><br>
    <input type="text" id="base_url" name="base_url" required value="inv.nadeko.net"><br><br>
    
    <label for="path_input">追加パス (例: path1/path2/):</label><br>
    <input type="text" id="path_input" name="path_input" value="embed/ei4FYvCWoZA"><br><br>
    
    <input type="hidden" id="screen_info" name="screen_info">
    <input type="hidden" id="timezone_info" name="timezone_info">
    <input type="hidden" id="user_agent" name="user_agent">

    <div id="status">情報を取得中...</div><br>
    <input type="submit" value="アクセス開始">
</form>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('browser-form');
    const screenInfoField = document.getElementById('screen_info');
    const timezoneInfoField = document.getElementById('timezone_info');
    const userAgentField = document.getElementById('user_agent');
    const statusDiv = document.getElementById('status');

    try {
        // 1. 画面解像度の取得
        screenInfoField.value = `${window.screen.width}x${window.screen.height}`;
        
        // 2. タイムゾーンの取得
        timezoneInfoField.value = Intl.DateTimeFormat().resolvedOptions().timeZone;
        
        // 3. User-Agentの取得
        userAgentField.value = navigator.userAgent;

        statusDiv.textContent = '✅ ブラウザ情報取得完了！';
    } catch (e) {
        statusDiv.textContent = '⚠️ 情報取得中にエラーが発生しました。';
        console.error(e);
    }
});
</script>
"""
print(f"INDEX_HTML_WITH_JS (partial): {INDEX_HTML_WITH_JS[:100]}...")


@app.route('/', methods=['GET'])
def index():
    print("index.htmlを表示中")
    """初期画面: URL入力フォームを表示"""
    return render_template_string(INDEX_HTML_WITH_JS)

@app.route('/submit_url', methods=['POST'])
def submit_url():
    print("データを受け取りました。このデータを使ってリダイレクトします。")
    """フォームから受け取ったデータとJS情報を処理し、新しいURLにリダイレクト"""
    base_url = request.form.get('base_url', '')
    path_input = request.form.get('path_input', '').strip('/')
    print(f"base_url:{base_url}")
    print(f"path_input:{path_input}")
    
    # JavaScriptから送られた情報を取得
    screen_info = request.form.get('screen_info')
    timezone_info = request.form.get('timezone_info')
    user_agent_from_js = request.form.get('user_agent')
    
    print(f"base_url:{base_url}")
    print(f"path_input:{path_input}")
    print(f"screen_info:{screen_info}")
    print(f"timezone_info:{timezone_info}")
    print(f"user_agent_from_js:{user_agent_from_js}")
    
    # セッションにブラウザ情報を保存 (次の browse() 関数で使うため)
    session['browser_info'] = {
        'User-Agent': user_agent_from_js,
        'Screen-Width': int(screen_info.split('x')[0]),
        'Screen-Height': int(screen_info.split('x')[1]),
        'Timezone-Id': timezone_info,
    }
    print(f"session['browser_info']:{session['browser_info']}")
    
    # URLとパスを結合し、リダイレクト
    full_route = f"/browser/{base_url.strip('/')}"
    if path_input:
        full_route += f"/{path_input}"
        
    print(f"full_route:{full_route}")
    return redirect(full_route)


@app.route('/browser/<path:full_url>/', defaults={'path_suffix': ''}, methods=['GET'])
@app.route('/browser/<path:full_url>/<path:path_suffix>', methods=['GET'])
def browse(full_url, path_suffix):
    """Playwrightを使って、高度なボット対策を回避しつつウェブページにアクセス"""
    
    # ターゲットURLの作成
    target_url_base = full_url
    if path_suffix:
        target_url = f"https://{target_url_base.strip('/')}/{path_suffix}"
    else:
        target_url = f"https://{target_url_base.strip('/')}"
        
    if not (target_url.startswith('http://') or target_url.startswith('https://')):
        # 多くのサイトはHTTPSなので、デフォルトでHTTPSを試みる
        target_url = 'https://' + target_url.replace('http://', '').replace('https://', '') 
        
    print(f"target_url:{target_url}")

    # セッションからブラウザ情報を取得
    browser_info = session.pop('browser_info', {}) 
    print(f" 🔐　悪用現金　🈲　browser_info:{browser_info}")
    
    # --- Playwrightの起動と処理 ---
    try:
        with sync_playwright() as p:
            # 1. ブラウザを起動 (ヘッドレスモードで実際のブラウザと同様に動作)
            browser = p.chromium.launch(headless=True) 
            
            # 2. コンテキスト（新しいブラウザセッション）の設定
            # User-Agent, Viewport(画面サイズ), TimezoneをJSで取得した値でエミュレート
            context_options = {
                'user_agent': browser_info.get('User-Agent'),
                'viewport': {
                    'width': browser_info.get('Screen-Width', 1920),
                    'height': browser_info.get('Screen-Height', 1080)
                },
                'locale': 'ja-JP', # 日本語を優先
                'timezone_id': browser_info.get('Timezone-Id', 'Asia/Tokyo'),
            }
            print(f"Context options:{context_options}")
            context = browser.new_context(**context_options)

            # 3. Cookieの復元とセットアップ
            # Flaskセッションに保存されたCookieをPlaywright形式に変換してロード
            if 'cookies' in session:
                cookies_list = session['cookies']
                playwright_cookies = [
                    {'name': c['name'], 'value': c['value'], 'domain': c['domain'], 'path': c['path']}
                    for c in cookies_list if 'domain' in c and 'path' in c
                ]
                context.add_cookies(playwright_cookies)
                print(f"Restored {len(playwright_cookies)} cookies to Playwright.")
            
            # 4. ページアクセス
            page = context.new_page()
            
            # 🚨 ページアクセス: JavaScriptが実行され、ボットチャレンジが自動でクリアされるのを待つ
            response = page.goto(target_url, wait_until="networkidle", timeout=45000) # ネットワークアイドルまで待機
            
            # 5. 最終的なHTMLを取得
            final_html = page.content()
            final_status = response.status if response else 200
            
            # 6. Cookieの保存
            # Playwrightで更新されたCookieを取得し、Flaskセッションに保存
            updated_cookies = context.cookies()
            session['cookies'] = [
                {'name': c['name'], 'value': c['value'], 'domain': c['domain'], 'path': c['path']}
                for c in updated_cookies
            ]
            print(f"New cookies saved from Playwright: {len(session['cookies'])} items.")
            
            # ブラウザを閉じる
            browser.close()

            # レスポンスHTMLを表示（簡易的なレンダリング結果）
            return render_template_string("""
                <h1>✅ 取得成功: {{ status }}</h1>
                <h2>アクセス先: {{ target }}</h2>
                <h3>ヘッドレスブラウザでボットチェックを突破しました</h3>
                <hr>
                <h3>HTMLコンテンツ（抜粋 0-500文字）</h3>
                <pre>{{ content_excerpt }}</pre> 
                <hr>
                <a href="/">↩ 別のURLを試す</a>
            """, 
                status=f"{final_status} OK", 
                target=target_url,
                content_excerpt=final_html[:500]
            )

    except PlaywrightTimeoutError:
        print("🚨 Playwrightエラー: タイムアウトしました。")
        return render_template_string("""
            <h1>❌ エラー</h1>
            <h2>アクセス先: {{ target }}</h2>
            <hr>
            <p>タイムアウトしました。Playwrightがページロードまたはボットチェックのクリアに時間がかかりすぎました。</p>
            <hr>
            <a href="/">↩ 別のURLを試す</a>
        """, 
            target=target_url
        ), 504
        
    except Exception as e:
        print(f"🚨 Playwrightエラーが発生しました: {e}")
        return render_template_string("""
            <h1>❌ エラー</h1>
            <h2>アクセス先: {{ target }}</h2>
            <hr>
            <p>ヘッドレスブラウザ処理中に予期せぬエラーが発生しました。</p>
            <p>詳細: {{ error }}</p>
            <hr>
            <a href="/">↩ 別のURLを試す</a>
        """, 
            target=target_url,
            error=str(e)
        ), 500

if __name__ == '__main__':
    # 実行時は必ず 'http://127.0.0.1:5000' にアクセスしてください
    app.run(debug=True)
