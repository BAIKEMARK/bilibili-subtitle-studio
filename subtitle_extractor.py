import requests
import json
import sys
import io
import time
import hashlib
import os
from urllib.parse import urlencode

# 仅在非导入模式下（直接运行脚本）强制设置UTF-8输出，避免Windows控制台乱码
if __name__ == "__main__":
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# WBI签名缓存
_wbi_keys_cache = None
_wbi_keys_cache_time = 0

# Cookie缓存（用于登录状态）
_user_cookie = None


def load_cookie_from_file(cookie_file="cookie.txt"):
    """
    从文件加载Cookie

    使用方法：
    1. 登录B站
    2. 按F12打开开发者工具 → Application标签页
    3. Cookies → https://www.bilibili.com
    4. 复制SESSDATA和bili_jct的值
    5. 保存到cookie.txt文件，格式：SESSDATA=xxx; bili_jct=xxx
    """
    global _user_cookie

    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 优先从脚本所在目录查找，再从当前工作目录查找
    possible_paths = [
        os.path.join(script_dir, cookie_file),  # 脚本所在目录
        cookie_file,  # 当前工作目录
    ]

    for path in possible_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                _user_cookie = f.read().strip()
                print(f"✅ 已加载Cookie文件: {path}")
                return True
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"❌ 加载Cookie失败 ({path}): {str(e)}")
            continue

    print(f"⚠️  未找到Cookie文件: {cookie_file}")
    print(f"   提示：可以在脚本所在目录或当前目录放入B站登录Cookie以获取AI字幕")
    return False


def get_headers_with_cookie(bvid):
    """获取带Cookie的请求头"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Referer': f'https://www.bilibili.com/video/{bvid}',
        'Accept': 'application/json, text/plain, */*'
    }

    if _user_cookie:
        headers['Cookie'] = _user_cookie

    return headers


def _build_auth_hint(api_response=None, subtitles=None):
    """根据接口返回信息构建登录态/权限提示。"""
    hints = []

    if _user_cookie:
        code = None
        message = ""
        login_mid = None

        if isinstance(api_response, dict):
            code = api_response.get('code')
            message = str(api_response.get('message', ''))
            data = api_response.get('data', {})
            if isinstance(data, dict):
                login_mid = data.get('login_mid')

        if code in (-101, -111, 61000) or ('未登录' in message):
            hints.append("Cookie 可能失效，请重新获取并更新 cookie.txt")
        elif login_mid in (0, None):
            hints.append("Cookie 可能失效（当前请求未识别到登录状态），请重新获取 cookie.txt")
    else:
        hints.append("未检测到有效 Cookie，部分 AI 字幕接口可能无法访问")

    if subtitles:
        locked_count = sum(1 for sub in subtitles if sub.get('is_lock'))
        if locked_count > 0:
            hints.append("账号权限不足，当前字幕处于锁定状态（可能需要更高账号权限）")

    if not hints:
        return ""
    return "\n   诊断：" + "；".join(hints)


def get_wbi_keys(headers):
    """
    获取WBI签名的密钥对

    WBI是B站的反爬虫机制，需要从nav接口获取img_key和sub_key
    """
    global _wbi_keys_cache, _wbi_keys_cache_time

    # 缓存1小时
    current_time = time.time()
    if _wbi_keys_cache and (current_time - _wbi_keys_cache_time) < 3600:
        return _wbi_keys_cache

    try:
        url = "https://api.bilibili.com/x/web-interface/nav"
        response = requests.get(url, headers=headers, timeout=10).json()

        if response.get('code') == 0:
            data = response.get('data', {})
            if 'wbi_img' in data:
                wbi_img = data['wbi_img']
                img_url = wbi_img.get('img_url', '')
                sub_url = wbi_img.get('sub_url', '')

                # 从URL中提取key
                img_key = img_url.split('/')[-1].split('.')[0]
                sub_key = sub_url.split('/')[-1].split('.')[0]

                keys = {'img_key': img_key, 'sub_key': sub_key}
                _wbi_keys_cache = keys
                _wbi_keys_cache_time = current_time
                return keys
    except Exception:
        pass

    return None


def generate_wbi_signature(params, wbi_keys):
    """
    生成WBI签名

    Args:
        params: 请求参数字典
        wbi_keys: 包含img_key和sub_key的字典

    Returns:
        签名后的完整URL参数字符串
    """
    # 混淆密钥顺序：img_key + sub_key
    mixin_key = wbi_keys['img_key'] + wbi_keys['sub_key']

    # 添加时间戳到参数中
    params['wts'] = int(time.time())

    # 按key排序参数
    params_sorted = dict(sorted(params.items()))

    # 生成签名：MD5(排序后的查询字符串 + mixin_key)
    query = urlencode(params_sorted)
    wbi_sign = hashlib.md5((query + mixin_key).encode()).hexdigest()

    # 添加签名到参数
    params_sorted['wbi_sign'] = wbi_sign

    return urlencode(params_sorted)


def format_time_srt(seconds):
    """Format seconds (float) to SRT timestamp: 00:00:00,000"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def format_time_vtt(seconds):
    """Format seconds (float) to VTT timestamp: 00:00:00.000"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

def generate_srt(subtitles):
    """Generate SRT content from subtitle list"""
    lines = []
    for i, sub in enumerate(subtitles, 1):
        if 'from' not in sub or 'to' not in sub:
            continue
        start = format_time_srt(float(sub['from']))
        end = format_time_srt(float(sub['to']))
        content = sub['content']
        lines.append(f"{i}\n{start} --> {end}\n{content}\n")
    return "\n".join(lines)

def generate_vtt(subtitles):
    """Generate VTT content from subtitle list"""
    lines = ["WEBVTT\n"]
    for sub in subtitles:
        if 'from' not in sub or 'to' not in sub:
            continue
        start = format_time_vtt(float(sub['from']))
        end = format_time_vtt(float(sub['to']))
        content = sub['content']
        lines.append(f"{start} --> {end}\n{content}\n")
    return "\n".join(lines)

def generate_txt(subtitles):
    """Generate TXT content from subtitle list"""
    return "\n".join(sub['content'] for sub in subtitles)

def get_bilibili_subtitle(bvid, prefer_ai=True, return_raw=False):
    """
    获取B站视频字幕

    Args:
        bvid: 视频的BVID
        prefer_ai: 是否优先使用AI字幕（默认True）
        return_raw: 是否返回原始字幕数据列表（字典列表），默认为False（返回拼接文本）

    Returns:
        如果 return_raw=False (默认):
            字幕文本字符串，如果失败则返回错误信息(❌开头)
        如果 return_raw=True:
            (字幕列表, 错误信息) 的元组。
            成功时: (list, None)
            失败时: (None, error_msg)
    """
    # 获取带Cookie的请求头
    headers = get_headers_with_cookie(bvid)

    try:
        # 第一步：获取视频的 cid
        print(f"📡 正在获取视频 {bvid} 的信息...")
        url_cid = f"https://api.bilibili.com/x/player/pagelist?bvid={bvid}"
        res_cid = requests.get(url_cid, headers=headers, timeout=10).json()

        if res_cid['code'] != 0:
            msg = f"❌ 获取视频信息失败：{res_cid.get('message', '未知错误')}"
            return (None, msg) if return_raw else msg

        cid = res_cid['data'][0]['cid']
        print(f"✅ 获取到 cid: {cid}")

        body = None

        # 第二步：尝试获取 AI 字幕（如果优先）
        if prefer_ai:
            print("🔍 正在查找 AI 字幕...")
            # 尝试多个可能的AI字幕接口
            body = _get_ai_subtitle(bvid, cid, headers)
            if body:
                print("✅ 成功获取 AI 字幕")
            else:
                print("⚠️  未找到 AI 字幕，尝试查找 CC 字幕...")

        # 第三步：获取 CC 字幕（手动上传的字幕）或当AI字幕失败时
        if not body:
            print("🔍 正在查找 CC 字幕...")
            url_info = f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}"
            res_info = requests.get(url_info, headers=headers, timeout=10).json()

            # 检查是否有字幕
            subtitles = res_info['data'].get('subtitle', {}).get('subtitles', [])
            if not subtitles:
                auth_hint = _build_auth_hint(api_response=res_info, subtitles=subtitles)
                msg = "❌ 该视频没有提供字幕（包括 AI 字幕和 CC 字幕）。\n   提示：如果是嵌入视频画面内的硬字幕，需要使用 OCR 工具提取。\n   如果视频有AI字幕，请配置cookie.txt文件以登录B站账号。" + auth_hint
                return (None, msg) if return_raw else msg

            # 显示可用字幕列表
            print(f"📝 找到 {len(subtitles)} 个字幕")
            for idx, sub in enumerate(subtitles):
                lang = sub.get('lan_doc') or sub.get('lan') or sub.get('lang') or '未知'
                print(f"   [{idx}] {lang}")

            # 第四步：下载第一个字幕（通常是中文）
            sub_url = subtitles[0].get('subtitle_url') or subtitles[0].get('subtitle_url_v2', '')

            # 如果subtitle_url为空，尝试用其他方式获取AI字幕
            if not sub_url or sub_url == '':
                print("   ⚠️  字幕URL为空，尝试使用备用方式获取AI字幕...")
                try:
                    # 新版接口里，AI字幕URL通常出现在x/player/wbi/v2的subtitle字段
                    fallback_url = f"https://api.bilibili.com/x/player/wbi/v2?bvid={bvid}&cid={cid}"
                    fallback_response = requests.get(fallback_url, headers=headers, timeout=10)
                    if fallback_response.status_code == 200:
                        fallback_data = fallback_response.json()
                        fallback_subs = fallback_data.get('data', {}).get('subtitle', {}).get('subtitles', [])
                        if fallback_subs:
                            sub_url = fallback_subs[0].get('subtitle_url') or fallback_subs[0].get('subtitle_url_v2', '')
                except Exception:
                    pass

                if not sub_url:
                    auth_hint = _build_auth_hint(api_response=res_info, subtitles=subtitles)
                    msg = "❌ 无法获取字幕URL，该视频的AI字幕可能无法通过API访问。\n   提示：可以使用模式3手动从浏览器F12复制字幕JSON。" + auth_hint
                    return (None, msg) if return_raw else msg

            if sub_url.startswith('//'):
                sub_url = 'https:' + sub_url

            print(f"⬇️  正在下载字幕...")
            res_sub = requests.get(sub_url, headers=headers, timeout=10).json()
            body = res_sub['body']

        # 结果处理
        print(f"✅ 成功获取 {len(body)} 条字幕")
        
        if return_raw:
            return body, None
        
        # 默认返回纯文本，兼容旧逻辑
        result = generate_txt(body)
        return result

    except requests.exceptions.Timeout:
        msg = "❌ 请求超时，请检查网络连接"
        return (None, msg) if return_raw else msg
    except requests.exceptions.RequestException as e:
        msg = f"❌ 网络请求失败：{str(e)}"
        return (None, msg) if return_raw else msg
    except json.JSONDecodeError:
        msg = "❌ 解析响应数据失败，API 可能已更新"
        return (None, msg) if return_raw else msg
    except Exception as e:
        msg = f"❌ 发生未知错误：{str(e)}"
        return (None, msg) if return_raw else msg


def _get_ai_subtitle(bvid, cid, headers):
    """
    获取 AI 自动生成的字幕 - 返回解析好的字幕列表
    """
    # 方法1: 从可用的播放器接口获取字幕URL并下载
    try:
        ai_info_url = f"https://api.bilibili.com/x/player/wbi/v2?bvid={bvid}&cid={cid}"
        ai_info = requests.get(ai_info_url, headers=headers, timeout=10).json()
        subtitles = ai_info.get('data', {}).get('subtitle', {}).get('subtitles', [])

        for sub in subtitles:
            # type=1通常表示AI字幕
            if sub.get('type') == 1:
                sub_url = sub.get('subtitle_url') or sub.get('subtitle_url_v2', '')
                if not sub_url:
                    continue
                if sub_url.startswith('//'):
                    sub_url = 'https:' + sub_url
                sub_response = requests.get(sub_url, headers=headers, timeout=10).json()
                if 'body' in sub_response:
                    return sub_response['body']
    except Exception:
        pass

    # 方法2: 尝试普通接口
    try:
        view_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        response = requests.get(view_url, headers=headers, timeout=10).json()

        if response.get('code') == 0:
            data = response.get('data', {})
            # 检查subtitle信息
            if 'subtitle' in data:
                subtitle_info = data['subtitle']
                if 'subtitles' in subtitle_info and subtitle_info['subtitles']:
                    # 下载第一个字幕
                    sub_url = subtitle_info['subtitles'][0]['subtitle_url']
                    if sub_url.startswith('//'):
                        sub_url = 'https:' + sub_url
                    sub_response = requests.get(sub_url, headers=headers, timeout=10).json()
                    if 'body' in sub_response:
                        return sub_response['body']
    except Exception:
        pass

    return None



OUTPUT_DIR = "subtitles_output"


def save_subtitle_bundle(subtitles, bvid, output_dir=OUTPUT_DIR):
    """按 BVID 目录保存 TXT/SRT/VTT 三种字幕格式。"""
    if not subtitles:
        return False, "", []

    safe_bvid = (bvid or "unknown").strip() or "unknown"
    target_dir = os.path.join(output_dir, safe_bvid)

    files = {
        f"{safe_bvid}.txt": generate_txt(subtitles),
        f"{safe_bvid}.srt": generate_srt(subtitles),
        f"{safe_bvid}.vtt": generate_vtt(subtitles),
    }

    failed = []
    for filename, content in files.items():
        filepath = os.path.join(target_dir, filename)
        ok = save_subtitle_to_file(content, filepath)
        if not ok:
            failed.append(filepath)

    return len(failed) == 0, os.path.abspath(target_dir), failed

def save_subtitle_to_file(text, filename="subtitle.txt"):
    """
    将字幕保存到文件
    
    如果不包含路径，默认保存到 subtitles_output 文件夹
    """
    try:
        # 如果是纯文件名（不含路径分隔符），则保存到默认输出目录
        if os.sep not in filename:
            # 确保输出目录存在
            if not os.path.exists(OUTPUT_DIR):
                os.makedirs(OUTPUT_DIR)
            filepath = os.path.join(OUTPUT_DIR, filename)
        else:
            # 如果包含路径，直接使用该路径
            # 同时也确保其父目录存在
            parent_dir = os.path.dirname(filename)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            filepath = filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        
        # 获取绝对路径用于展示
        abs_path = os.path.abspath(filepath)
        print(f"💾 字幕已保存到: {abs_path}")
        return True
    except Exception as e:
        print(f"❌ 保存文件失败：{str(e)}")
        return False



def parse_subtitle_json(json_text, return_raw=False):
    """
    解析从浏览器F12复制的字幕JSON数据
    """
    try:
        # 清理可能的多余字符
        json_text = json_text.strip()
        if json_text.startswith('```'):
            # 移除markdown代码块标记
            lines = json_text.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines[-1].startswith('```'):
                lines = lines[:-1]
            json_text = '\n'.join(lines)

        data = json.loads(json_text)

        # 尝试提取body中的字幕
        body = None
        if 'body' in data:
            body = data['body']
        elif 'data' in data and 'body' in data['data']:
            body = data['data']['body']

        if body:
            print(f"✅ 成功解析 {len(body)} 条字幕")
            if return_raw:
                return body, None
            
            result = generate_txt(body)
            return result
        else:
            msg = "❌ JSON中未找到body数据，请确认复制的是正确的字幕接口"
            print(msg)
            return (None, msg) if return_raw else msg

    except json.JSONDecodeError as e:
        msg = f"❌ JSON解析失败：{str(e)}\n   请确保复制了完整的JSON数据"
        print(msg)
        return (None, msg) if return_raw else None
    except Exception as e:
        msg = f"❌ 解析失败：{str(e)}"
        print(msg)
        return (None, msg) if return_raw else None


def batch_get_subtitles(bvid_list, formats=None):
    """
    批量获取多个视频的字幕

    Args:
        bvid_list: BVID列表
        formats: 要保存的格式列表，如 ['txt', 'srt', 'vtt']。如果不传则默认保存所有。

    Returns:
        字典，key为bvid，value为字幕文本或错误信息
    """
    if formats is None:
        formats = ['txt', 'srt', 'vtt']

    results = {}
    total = len(bvid_list)

    print(f"\n{'='*60}")
    print(f"开始批量获取 {total} 个视频的字幕")
    print(f"目标格式: {', '.join(formats)}")
    print(f"{'='*60}\n")

    for idx, bvid in enumerate(bvid_list, 1):
        print(f"\n[{idx}/{total}] 处理视频: {bvid}")
        print("-" * 60)

        subtitle, error = get_bilibili_subtitle(bvid, prefer_ai=True, return_raw=True)

        if subtitle:
            results[bvid] = generate_txt(subtitle)

            if set(formats) >= {"txt", "srt", "vtt"}:
                save_subtitle_bundle(subtitle, bvid)
            else:
                base_name = f"{bvid}_字幕"
                if 'txt' in formats:
                    txt = generate_txt(subtitle)
                    save_subtitle_to_file(txt, f"{base_name}.txt")
                if 'srt' in formats:
                    srt = generate_srt(subtitle)
                    save_subtitle_to_file(srt, f"{base_name}.srt")
                if 'vtt' in formats:
                    vtt = generate_vtt(subtitle)
                    save_subtitle_to_file(vtt, f"{base_name}.vtt")
        else:
            results[bvid] = error
            print(error)

        # 短暂延迟，避免请求过快
        if idx < total:
            time.sleep(1)

    # 打印总结
    print(f"\n{'='*60}")
    print("批量获取完成！")
    print(f"{'='*60}")
    success_count = sum(1 for v in results.values() if v and not v.startswith("❌"))
    print(f"成功: {success_count}/{total}")
    print(f"失败: {total - success_count}/{total}")

    return results

# ============ 使用示例 ============
if __name__ == "__main__":
    print("=" * 60)
    print("B站字幕提取工具 v2.0")
    print("=" * 60)

    # 尝试加载Cookie（可选）
    load_cookie_from_file()

    print("\n请选择使用模式：")
    print("1. 单个视频获取字幕")
    print("2. 批量获取字幕（多个BVID）")
    print("3. 手动粘贴JSON（从浏览器F12复制）")

    choice = input("\n请输入选项（1/2/3）：").strip()

    if choice == "1":
        # 模式1：单个视频获取字幕
        bvid = input("\n请输入视频BVID（例如：BV1ZL411o7LZ）：").strip()
        if not bvid:
            print("未输入BVID，使用默认测试视频")
            bvid = "BV1ZL411o7LZ"

        # 获取字幕（优先AI字幕，如果没有则获取CC字幕）
        subtitle_text = get_bilibili_subtitle(bvid, prefer_ai=True)

        # 打印或保存字幕
        if subtitle_text and not subtitle_text.startswith("❌"):
            print("\n" + "="*50)
            print("字幕内容预览（前500字符）：")
            print("="*50)
            print(subtitle_text[:500])

            # 保存到文件
            save_subtitle_to_file(subtitle_text, f"{bvid}_字幕.txt")
        else:
            print(subtitle_text)
            print("\n提示：如果视频有字幕但无法自动获取，请选择模式3手动粘贴")

    elif choice == "2":
        # 模式2：批量获取字幕
        print("\n请输入BVID列表，多个BVID用空格、逗号或换行分隔")
        print("示例：BV1ZL411o7LZ BV1fT411B7od BV1Fk4y1v7fQ")
        print("\n输入完成后按回车：")
        print("-" * 60)

        input_text = input().strip()

        # 解析BVID列表（支持空格、逗号、换行分隔）
        import re
        bvid_list = re.findall(r'BV[\w]+', input_text)

        if not bvid_list:
            print("未检测到有效的BVID，使用默认测试列表")
            bvid_list = ["BV1ZL411o7LZ", "BV1fT411B7od", "BV1Fk4y1v7fQ"]

        print(f"\n检测到 {len(bvid_list)} 个BVID：")
        for idx, bvid in enumerate(bvid_list, 1):
            print(f"  {idx}. {bvid}")

        confirm = input("\n确认开始批量获取？(y/n): ").strip().lower()
        if confirm == 'y':
            batch_get_subtitles(bvid_list)
        else:
            print("已取消")

    elif choice == "3":
        # 模式3：手动粘贴JSON
        print("\n请按以下步骤操作：")
        print("1. 用浏览器打开视频页面并登录")
        print("2. 按F12打开开发者工具 → Network标签页")
        print("3. 刷新页面，在Filter中搜索'subtitle'或'ai_subtitle'")
        print("4. 点击字幕请求 → Response标签页")
        print("5. 右键 → Copy → Copy response")
        print("\n请粘贴复制的JSON数据（输入完成后按Ctrl+Z然后回车）：")
        print("-" * 60)

        # 读取多行输入
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass

        json_text = '\n'.join(lines)
        subtitle_text = parse_subtitle_json(json_text)

        if subtitle_text:
            print("\n" + "="*50)
            print("字幕内容预览（前500字符）：")
            print("="*50)
            print(subtitle_text[:500])

            filename = input("\n请输入保存的文件名（直接回车使用默认：subtitle.txt）：").strip()
            if not filename:
                filename = "subtitle.txt"
            save_subtitle_to_file(subtitle_text, filename)
    else:
        print("无效的选项！")