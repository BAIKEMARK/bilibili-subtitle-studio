"""
B站Cookie获取工具

优先使用本机浏览器自动登录；若无法启动Chrome，则自动切换到二维码扫码登录。
"""

import io
import os
import sys
import time
import webbrowser

import requests

# 仅在非导入模式下（直接运行脚本）强制设置UTF-8输出，避免Windows控制台乱码
if __name__ == "__main__":
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    import qrcode
except ImportError:
    qrcode = None


OUTPUT_COOKIE_FILE = "cookie.txt"


def save_cookie_to_file(sessdata, bili_jct, output_file=OUTPUT_COOKIE_FILE):
    """保存最小可用Cookie到文件。"""
    cookie_string = f"SESSDATA={sessdata}; bili_jct={bili_jct}"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(cookie_string)
    return cookie_string


def print_qr_in_terminal(qr_url):
    """在终端打印ASCII二维码。"""
    if qrcode is None:
        print("\n⚠️  未安装qrcode库，无法在终端显示二维码")
        print(f"请手动打开链接完成扫码: {qr_url}")
        return

    qr = qrcode.QRCode(border=1)
    qr.add_data(qr_url)
    qr.make(fit=True)
    print("\n请使用B站App扫码登录（终端二维码）：\n")
    qr.print_ascii(invert=True)
    print()


def try_get_cookie_by_qrcode(wait_seconds=180):
    """使用B站官方二维码登录接口获取Cookie。"""
    session = requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Referer": "https://passport.bilibili.com/login",
    }

    print("\n正在申请二维码...")
    resp = session.get(
        "https://passport.bilibili.com/x/passport-login/web/qrcode/generate",
        headers=headers,
        timeout=15,
    )
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"二维码生成失败: {data}")

    qr_url = data["data"]["url"]
    qrcode_key = data["data"]["qrcode_key"]

    print_qr_in_terminal(qr_url)
    print(f"📱 扫码登录链接: {qr_url}")
    print("\n两种登录方式选一种：")
    print("  1️⃣  用B站App扫上方的二维码（推荐）")
    print("  2️⃣  或复制上方链接到浏览器手动登录")
    print("\n等待扫码/登录确认...")
    poll_url = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
    start_time = time.time()
    last_status = None

    while time.time() - start_time < wait_seconds:
        poll_resp = session.get(
            poll_url,
            params={"qrcode_key": qrcode_key},
            headers=headers,
            timeout=15,
        )
        poll_data = poll_resp.json()

        if poll_data.get("code") != 0:
            raise RuntimeError(f"轮询失败: {poll_data}")

        status_code = poll_data.get("data", {}).get("code")
        if status_code != last_status:
            if status_code == 86101:
                print("状态: 未扫码")
            elif status_code == 86090:
                print("状态: 已扫码，请在手机上确认")
            elif status_code == 86038:
                print("状态: 二维码已过期")
                break
            last_status = status_code

        if status_code == 0:
            print("✅ 扫码登录成功，正在提取Cookie...")
            success_url = poll_data.get("data", {}).get("url", "")
            if success_url:
                try:
                    print(f"   访问确认URL: {success_url[:80]}...")
                    resp = session.get(success_url, headers=headers, timeout=15, allow_redirects=True)
                    print(f"   响应状态码: {resp.status_code}")
                except Exception as e:
                    print(f"   访问确认URL失败: {e}")
            break

        time.sleep(2)

    print("\n正在从Session提取Cookie...")
    
    # 处理多个同名cookie的情况
    sessdata = None
    bili_jct = None
    
    for cookie in session.cookies:
        if cookie.name == "SESSDATA" and not sessdata:
            sessdata = cookie.value
        elif cookie.name == "bili_jct" and not bili_jct:
            bili_jct = cookie.value
    
    if sessdata:
        print(f"✅ 成功提取SESSDATA: {sessdata[:20]}...")
    else:
        print("⚠️  未能从Session提取SESSDATA")
        print(f"   调试: 当前所有Cookies列表:")
        for cookie in session.cookies:
            print(f"     - {cookie.name}: {cookie.value[:30]}...")
        
    if bili_jct:
        print(f"✅ 成功提取bili_jct: {bili_jct[:20]}...")
    else:
        print("⚠️  未能从Session提取bili_jct")

    return sessdata, bili_jct


def auto_get_cookie():
    """自动获取Cookie，仅使用二维码模式。"""
    print("=" * 60)
    print("B站Cookie自动获取工具")
    print("=" * 60)
    
    print("\n说明：为确保自动获取Cookie成功，请使用下方的二维码扫码登录。")
    print("（由于浏览器安全限制，无法自动检测您在桌面浏览器中的登录状态）")
    print("\n步骤：")
    print("1. 打开手机B站App")
    print("2. 扫描下方二维码")
    print("3. 在手机上确认登录")
    print("4. 脚本将自动检测并获取Cookie")
    print("-" * 60)

    try:
        sessdata, bili_jct = try_get_cookie_by_qrcode(wait_seconds=180)
    except Exception as e:
        print(f"\n❌ 二维码登录失败: {e}")
        sessdata, bili_jct = None, None

    if sessdata and bili_jct:
        save_cookie_to_file(sessdata, bili_jct)
        print("\n" + "=" * 60)
        print("✅ Cookie获取成功！")
        print("=" * 60)
        print(f"\nSESSDATA: {sessdata[:20]}...")
        print(f"bili_jct: {bili_jct}")
        print(f"\n已保存到: {os.path.abspath(OUTPUT_COOKIE_FILE)}")
        print("\n现在可以运行字幕提取工具了！")
        print("  python subtitle_extractor.py")
    else:
        print("\n❌ 未找到必要的Cookie（SESSDATA/bili_jct）")
        print("请重试，并在扫码后确认授权")


if __name__ == "__main__":
    auto_get_cookie()
