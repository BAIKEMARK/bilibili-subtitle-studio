"""
B站Cookie全自动获取工具
直接运行即可，自动打开浏览器并提取Cookie
"""

import sys
import time
import io

# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
except ImportError:
    print("请先安装selenium: pip install selenium")
    sys.exit(1)


def auto_get_cookie():
    """自动获取Cookie"""
    print("=" * 60)
    print("B站Cookie自动获取工具")
    print("=" * 60)
    print("\n正在启动Chrome浏览器...")

    # 配置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # 启动浏览器
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("✅ 浏览器已启动")
    except Exception as e:
        print(f"\n❌ 无法启动浏览器: {str(e)}")
        print("\n请确保:")
        print("1. 已安装Chrome浏览器")
        print("2. ChromeDriver版本匹配")
        sys.exit(1)

    try:
        # 打开B站登录页面
        print("\n正在打开B站登录页面...")
        driver.get("https://passport.bilibili.com/login")

        print("\n" + "=" * 60)
        print("请完成登录操作：")
        print("  1. 使用手机B站扫码登录（推荐）")
        print("  2. 或使用账号密码登录")
        print("=" * 60)
        print("\n等待登录中...")
        print("(登录成功后会自动提取Cookie)\n")

        # 等待用户登录
        max_wait_time = 300  # 最多等待5分钟
        start_time = time.time()
        logged_in = False

        while time.time() - start_time < max_wait_time:
            try:
                # 检查是否已登录（URL变化）
                if "passport" not in driver.current_url:
                    print("\n✅ 检测到登录成功！")
                    logged_in = True
                    break
                time.sleep(1)

                # 每10秒显示一次等待时间
                elapsed = int(time.time() - start_time)
                if elapsed % 10 == 0 and elapsed > 0:
                    print(f"等待中... ({elapsed}s / 300s)")
            except Exception:
                pass

        if not logged_in:
            print("\n⚠️  等待超时，请手动确认...")
            input("按回车继续...")

        # 提取Cookie
        print("\n正在提取Cookie...")
        cookies = driver.get_cookies()

        sessdata = None
        bili_jct = None

        for cookie in cookies:
            if cookie['name'] == 'SESSDATA':
                sessdata = cookie['value']
            elif cookie['name'] == 'bili_jct':
                bili_jct = cookie['value']

        if sessdata and bili_jct:
            # 保存到文件
            cookie_string = f"SESSDATA={sessdata}; bili_jct={bili_jct}"

            with open('cookie.txt', 'w', encoding='utf-8') as f:
                f.write(cookie_string)

            print("\n" + "=" * 60)
            print("✅ Cookie获取成功！")
            print("=" * 60)
            print(f"\nSESSDATA: {sessdata[:20]}...")
            print(f"bili_jct: {bili_jct}")
            print(f"\n已保存到: cookie.txt")
            print("\n现在可以运行字幕提取工具了！")
            print("  python subtitle_extractor.py")
        else:
            print("\n❌ 未找到必要的Cookie")
            print("请确保已经完成登录")

    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n浏览器将在30秒后关闭...")
        print("如需立即关闭，请按Ctrl+C")
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            pass

        try:
            driver.quit()
            print("浏览器已关闭")
        except:
            pass


if __name__ == "__main__":
    auto_get_cookie()
