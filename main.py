import os
import sys
import time
import warnings

# 忽略urllib3的OpenSSL警告 (必须在导入requests之前设置)
warnings.filterwarnings("ignore", message=r"urllib3 v2.*")

import requests
import cookie_auto_login
import subtitle_extractor

def clear_screen():
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

def check_login_status(silent=False):
    """
    检查Cookie是否有效
    返回: (is_valid, username)
    """
    # 尝试加载Cookie
    if not subtitle_extractor.load_cookie_from_file():
        if not silent:
            print("❌ 未找到Cookie文件")
        return False, None

    # 验证Cookie有效性
    headers = subtitle_extractor.get_headers_with_cookie("") # BVID为空仅获取Header
    try:
        # 使用导航接口检查登录状态
        url = "https://api.bilibili.com/x/web-interface/nav"
        resp = requests.get(url, headers=headers, timeout=5).json()
        
        if resp.get('code') == 0:
            data = resp.get('data', {})
            if data.get('isLogin'):
                uname = data.get('uname', '未知用户')
                if not silent:
                    print(f"✅ Cookie有效，当前用户: {uname}")
                return True, uname
            else:
                if not silent:
                    print("⚠️  Cookie已失效 (未登录状态)")
                return False, None
        else:
            if not silent:
                print(f"⚠️  接口访问失败: {resp.get('message')}")
            return False, None
    except Exception as e:
        if not silent:
            print(f"⚠️  网络请求异常: {e}")
        return False, None

def run_subtitle_extraction_mode():
    while True:
        print("\n" + "="*40)
        print("   B站字幕提取工具 - 主菜单")
        print("="*40)
        print("1. 提取单个视频 (BVID)")
        print("2. 批量提取视频")
        print("3. 手动解析 JSON")
        print("4. 重新登录/刷新Cookie")
        print("5. 退出程序")
        print("="*40)
        
        choice = input("\n请输入选项 [1-5]: ").strip()
        
        if choice == '1':
            bvid = input("\n请输入视频BVID (例如 BV1ZL411o7LZ): ").strip()
            if bvid:
                # 使用 return_raw=True 获取原始数据以便保存多种格式
                result, error = subtitle_extractor.get_bilibili_subtitle(bvid, return_raw=True)
                
                if result:
                    # 保存三种格式
                    base_name = f"{bvid}_字幕"
                    
                    # 保存 TXT
                    txt_content = subtitle_extractor.generate_txt(result)
                    subtitle_extractor.save_subtitle_to_file(txt_content, f"{base_name}.txt")
                    
                    # 保存 SRT
                    srt_content = subtitle_extractor.generate_srt(result)
                    subtitle_extractor.save_subtitle_to_file(srt_content, f"{base_name}.srt")
                    
                    # 保存 VTT
                    vtt_content = subtitle_extractor.generate_vtt(result)
                    subtitle_extractor.save_subtitle_to_file(vtt_content, f"{base_name}.vtt")
                    
                    print(f"\n✅ 已自动保存为 TXT/SRT/VTT 三种格式")
                else:
                    print(error)
            
            input("\n按回车键继续...")

        elif choice == '2':
            print("\n请输入多个BVID (用空格、逗号或换行分隔)")
            print("输入完成后，按两次回车结束:")
            
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            
            raw_text = " ".join(lines)
            # 使用简单的正则提取
            import re
            bvid_list = re.findall(r"(BV[a-zA-Z0-9]+)", raw_text)
            
            if bvid_list:
                print(f"\n检测到 {len(bvid_list)} 个BVID，开始处理...")
                subtitle_extractor.batch_get_subtitles(bvid_list)
            else:
                print("未检测到有效的BVID")
            
            input("\n按回车键继续...")

        elif choice == '3':
            print("\n请粘贴从浏览器F12 Network复制的字幕JSON内容:")
            print("输入完成后，按两次回车结束:")
            
            json_lines = []
            while True:
                line = input()
                if not line and json_lines: # 空行且已有内容则结束
                    break
                if line:
                    json_lines.append(line)
            
            json_text = "\n".join(json_lines)
            if json_text:
                subtitle_extractor.parse_subtitle_json(json_text)
            else:
                print("未输入内容")
                
            input("\n按回车键继续...")

        elif choice == '4':
            force_relogin()
            input("\n按回车键继续...")

        elif choice == '5':
            print("退出程序。")
            sys.exit(0)

        else:
            print("无效选项，请重试。")
            time.sleep(1)

def force_relogin():
    print("\n" + "-"*40)
    print("开始重新登录...")
    print("-"*40)
    cookie_auto_login.auto_get_cookie()
    # 重新加载Cookie
    subtitle_extractor.load_cookie_from_file()
    check_login_status()

def main():
    print("正在初始化 B站字幕提取工具...")
    
    # 1. 检测Cookie
    is_valid, uname = check_login_status(silent=True)
    
    if not is_valid:
        print("\n⚠️  检测到未登录或Cookie已失效")
        choice = input("是否立即进行登录? (y/n) [y]: ").strip().lower()
        if choice in ('', 'y'):
            force_relogin()
        else:
            print("⚠️  将以未登录模式继续 (可能无法获取AI字幕)")
    
    elif uname:
        print(f"✅ 已登录: {uname}")

    # 2. 进入主功能循环
    run_subtitle_extraction_mode()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序已退出。")
        sys.exit(0)
