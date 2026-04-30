"""
dashboard.html をパスワード付き暗号化版に変換する。
出力 HTML はブラウザで開くとパスワード入力画面が表示され、
正しいパスワードを入れると Web Crypto API で復号して内容を表示する。

使い方:
  python3 encrypt_dashboard.py <PASSWORD> [入力ファイル] [出力ファイル]
  デフォルト: dashboard.html → dashboard_encrypted.html
"""
import os, sys, base64, hashlib, json
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

PBKDF2_ITERATIONS = 200000
PBKDF2_KEY_LEN = 32  # 256-bit
SALT_LEN = 16
IV_LEN = 12  # GCM standard

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>JIHS Dashboard - Login</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {
    background: #f5f7fa;
    font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
    margin: 0; min-height: 100vh;
    display: flex; align-items: center; justify-content: center;
  }
  .login-box {
    background: white; padding: 40px 36px;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    width: 320px; text-align: center;
  }
  h1 { font-size: 18px; color: #333; margin: 0 0 8px; }
  p.sub { color: #666; font-size: 13px; margin: 0 0 24px; }
  input[type=password] {
    width: 100%; padding: 12px 14px; box-sizing: border-box;
    border: 1.5px solid #d0d7de; border-radius: 8px;
    font-size: 15px; outline: none;
    transition: border-color 0.15s;
  }
  input[type=password]:focus { border-color: #0969da; }
  button {
    width: 100%; padding: 12px; margin-top: 12px;
    background: #0969da; color: white; border: none; border-radius: 8px;
    font-size: 15px; font-weight: 600; cursor: pointer;
    transition: background 0.15s;
  }
  button:hover { background: #0552b1; }
  button:disabled { background: #94a3b8; cursor: not-allowed; }
  .err { color: #cf222e; font-size: 13px; margin-top: 12px; min-height: 18px; }
  .lock { font-size: 28px; margin-bottom: 12px; }
</style>
</head>
<body>
<div class="login-box" id="login">
  <div class="lock">🔒</div>
  <h1>JIHS 感染症ダッシュボード</h1>
  <p class="sub">アクセスにはパスワードが必要です</p>
  <input type="password" id="pw" placeholder="パスワードを入力" autofocus>
  <button id="btn">ログイン</button>
  <div class="err" id="err"></div>
</div>
<script>
const ENC_PAYLOAD = __PAYLOAD__;

async function deriveKey(password, salt) {
  const enc = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw', enc.encode(password), {name: 'PBKDF2'}, false, ['deriveKey']
  );
  return crypto.subtle.deriveKey(
    {name: 'PBKDF2', salt: salt, iterations: __ITERATIONS__, hash: 'SHA-256'},
    keyMaterial,
    {name: 'AES-GCM', length: 256},
    false,
    ['decrypt']
  );
}

function b64ToBytes(s) {
  const bin = atob(s);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return arr;
}

async function tryDecrypt(pw) {
  const salt = b64ToBytes(ENC_PAYLOAD.salt);
  const iv = b64ToBytes(ENC_PAYLOAD.iv);
  const ct = b64ToBytes(ENC_PAYLOAD.ct);
  const key = await deriveKey(pw, salt);
  try {
    const ptBuf = await crypto.subtle.decrypt({name: 'AES-GCM', iv: iv}, key, ct);
    const html = new TextDecoder().decode(ptBuf);
    // Verify decryption sanity (decrypted text must start with valid HTML marker)
    if (!html.includes('<html') && !html.includes('<!DOCTYPE')) {
      throw new Error('decrypt sanity check failed');
    }
    document.open();
    document.write(html);
    document.close();
    // Persist for the session
    sessionStorage.setItem('jihs_pw_ok', '1');
  } catch (e) {
    document.getElementById('err').textContent = 'パスワードが違います';
    document.getElementById('btn').disabled = false;
    document.getElementById('pw').value = '';
    document.getElementById('pw').focus();
  }
}

document.getElementById('btn').addEventListener('click', async () => {
  const pw = document.getElementById('pw').value;
  if (!pw) return;
  document.getElementById('btn').disabled = true;
  document.getElementById('err').textContent = '';
  await tryDecrypt(pw);
});
document.getElementById('pw').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') document.getElementById('btn').click();
});
</script>
</body>
</html>
"""


def encrypt_file(password: str, in_path: str, out_path: str):
    with open(in_path, 'rb') as f:
        plaintext = f.read()

    salt = get_random_bytes(SALT_LEN)
    iv = get_random_bytes(IV_LEN)

    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt,
                              PBKDF2_ITERATIONS, PBKDF2_KEY_LEN)

    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    ct, tag = cipher.encrypt_and_digest(plaintext)

    # Web Crypto AES-GCM expects ciphertext+tag concatenated
    ct_with_tag = ct + tag

    payload = {
        'salt': base64.b64encode(salt).decode(),
        'iv':   base64.b64encode(iv).decode(),
        'ct':   base64.b64encode(ct_with_tag).decode(),
    }

    html = HTML_TEMPLATE \
        .replace('__PAYLOAD__', json.dumps(payload)) \
        .replace('__ITERATIONS__', str(PBKDF2_ITERATIONS))

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'  ✅ 暗号化完了: {in_path} ({len(plaintext):,} bytes) → {out_path} ({len(html):,} bytes)')
    print(f'  Salt: {payload["salt"]}, IV: {payload["iv"]}')


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 encrypt_dashboard.py <PASSWORD> [input.html] [output.html]')
        sys.exit(1)
    password = sys.argv[1]
    in_path = sys.argv[2] if len(sys.argv) > 2 else 'dashboard.html'
    out_path = sys.argv[3] if len(sys.argv) > 3 else 'dashboard_encrypted.html'
    encrypt_file(password, in_path, out_path)


if __name__ == '__main__':
    main()
