import io
import os
import re
import time
import zipfile
from contextlib import redirect_stdout

import streamlit as st
import requests

import subtitle_extractor as core

try:
    import qrcode
except ImportError:
    qrcode = None

try:
    from streamlit_cookies_manager import EncryptedCookieManager
except Exception:
    EncryptedCookieManager = None

# 判断运行环境 (通过环境变量，或默认检测)
# 如果是 Render, Streamlit Cloud, Heroku 等平台，通常会有特定 ENV
# 这里我们定义一个简单的 ENV 开关 'BILI_STUDIO_MODE'
# 'local' = 本地模式 (默认，注重文件操作，扫码)
# 'web' = 网页部署模式 (注重浏览器Cookie，隐藏本地文件操作)
APP_MODE = os.getenv("BILI_STUDIO_MODE", "local")

ALLOWED_COOKIE_KEYS = {
    "SESSDATA",
    "bili_jct",
    "DedeUserID",
    "DedeUserID__ckMd5",
    "buvid3",
}

BROWSER_COOKIE_KEY = "bili_cookie"


def capture_run(func, *args, **kwargs):
    """执行函数并捕获终端日志输出，便于在界面中展示。"""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = func(*args, **kwargs)
    logs = buffer.getvalue()
    return result, logs


def parse_bvid_list(text):
    return re.findall(r"BV[0-9A-Za-z]+", text or "")


def generate_subtitle_content_by_format(subtitles, fmt):
    if fmt == "txt":
        return core.generate_txt(subtitles)
    if fmt == "srt":
        return core.generate_srt(subtitles)
    if fmt == "vtt":
        return core.generate_vtt(subtitles)
    return ""


def build_subtitle_zip(batch_success, fmt, selected_bvid=None):
    """构建字幕 ZIP 二进制数据。

    Args:
        batch_success: {bvid: subtitles}
        fmt: txt/srt/vtt
        selected_bvid: 仅打包某一个 BVID；为 None 时打包全部
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        items = batch_success.items()
        if selected_bvid:
            subtitles = batch_success.get(selected_bvid)
            items = [(selected_bvid, subtitles)] if subtitles else []

        for bvid, subtitles in items:
            content = generate_subtitle_content_by_format(subtitles, fmt)
            if not content:
                continue
            filename = f"{bvid}/{bvid}.{fmt}"
            zf.writestr(filename, content)

    buffer.seek(0)
    return buffer.getvalue()


def parse_cookie_string(cookie_text):
    cookie_dict = {}
    for part in (cookie_text or "").split(";"):
        item = part.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and value:
            cookie_dict[key] = value
    return cookie_dict


def build_minimal_cookie(cookie_text):
    cookie_dict = parse_cookie_string(cookie_text)
    kept = {k: v for k, v in cookie_dict.items() if k in ALLOWED_COOKIE_KEYS}
    if not kept:
        return "", []
    merged = "; ".join(f"{k}={v}" for k, v in kept.items())
    return merged, sorted(kept.keys())


def apply_session_cookie():
    cookie_value = st.session_state.get("cookie_value", "")

    if cookie_value:
        core._user_cookie = cookie_value
        return True, "Cookie 已就绪"

    core._user_cookie = None
    return False, "未检测到可用 Cookie，AI 字幕可能无法访问"


def set_cookie_from_ui(cookie_text, allow_file=False):
    cookie_text = (cookie_text or "").strip()
    if cookie_text:
        minimized_cookie, kept_keys = build_minimal_cookie(cookie_text)
        if not minimized_cookie:
            st.session_state["cookie_value"] = ""
            st.session_state["cookie_keys"] = []
            core._user_cookie = None
            return False, "Cookie 格式无效或未包含必要字段（至少需要 SESSDATA）"

        st.session_state["cookie_value"] = minimized_cookie
        st.session_state["cookie_keys"] = kept_keys
        core._user_cookie = minimized_cookie
        return True, f"Cookie 已更新（字段最小化: {', '.join(kept_keys)}）"

    if allow_file:
        loaded, _ = capture_run(core.load_cookie_from_file)
        if loaded and core._user_cookie:
            minimized_cookie, kept_keys = build_minimal_cookie(core._user_cookie)
            if minimized_cookie:
                st.session_state["cookie_value"] = minimized_cookie
                st.session_state["cookie_keys"] = kept_keys
                core._user_cookie = minimized_cookie
                return True, "已从本地 cookie.txt 加载并最小化"

    return apply_session_cookie()


def clear_cookie_session():
    st.session_state["cookie_value"] = ""
    st.session_state["cookie_keys"] = []
    core._user_cookie = None


def init_browser_cookie_store():
    """初始化浏览器加密Cookie存储。"""
    if EncryptedCookieManager is None:
        return None

    password = os.getenv("APP_COOKIE_STORE_PASSWORD", "bili-subtitle-local-store")
    store = EncryptedCookieManager(prefix="bili-subtitle/", password=password)
    if not store.ready():
        st.stop()
    return store


def render_result_block(title, result, key_prefix="result"):
    st.subheader(title)
    
    content = ""
    raw_data = None
    
    # Check if result is (data, error) tuple from return_raw=True
    if isinstance(result, tuple) and len(result) == 2:
        raw_data, error = result
        if error:
            content = error
        else:
            # Generate TXT for display
            content = core.generate_txt(raw_data)
    else:
        # Legacy string result
        content = result

    if content and not content.startswith("❌"):
        st.success("字幕获取成功")
        st.text_area("字幕内容", content, height=260, key=f"{key_prefix}_content")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                label="📄 下载字幕 TXT",
                data=content,
                file_name="subtitle.txt",
                mime="text/plain",
                use_container_width=True,
                key=f"{key_prefix}_download_txt",
            )
        
        if raw_data:
            with col2:
                srt_content = core.generate_srt(raw_data)
                st.download_button(
                    label="🌐 下载字幕 SRT",
                    data=srt_content,
                    file_name="subtitle.srt",
                    mime="text/plain",
                    use_container_width=True,
                    key=f"{key_prefix}_download_srt",
                )
            with col3:
                vtt_content = core.generate_vtt(raw_data)
                st.download_button(
                    label="📝 下载字幕 VTT",
                    data=vtt_content,
                    file_name="subtitle.vtt",
                    mime="text/plain",
                    use_container_width=True,
                    key=f"{key_prefix}_download_vtt",
                )
    else:
        st.error(content or "获取失败")



def perform_qr_login(cookie_store, remember_cookie, save_cookie_file):
    """扫码登录逻辑封装"""
    if qrcode is None:
        st.error("未安装 qrcode 库，无法生成二维码。请运行 `pip install qrcode`")
        return

    st.info("请使用 B站 App 扫描下方二维码登录")
    
    # 1. 获取二维码 URL
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": "https://passport.bilibili.com/login",
        }
        resp = session.get(
            "https://passport.bilibili.com/x/passport-login/web/qrcode/generate",
            headers=headers,
            timeout=10,
        )
        data = resp.json()
        if data.get("code") != 0:
            st.error(f"二维码生成失败: {data}")
            return
        
        qr_url = data["data"]["url"]
        qrcode_key = data["data"]["qrcode_key"]
        
        # 2. 生成二维码图片
        qr = qrcode.QRCode(box_size=10, border=1)
        qr.add_data(qr_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 显示二维码
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        st.image(img_buffer.getvalue(), caption="请使用手机 B站 App 扫码", width=200)
        
        status_placeholder = st.empty()
        
        # 3. 轮询状态 (最多等待 180秒)
        poll_url = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
        start_time = time.time()
        
        while time.time() - start_time < 180:
            poll_resp = session.get(
                poll_url,
                params={"qrcode_key": qrcode_key},
                headers=headers,
                timeout=10,
            )
            poll_data = poll_resp.json()
            
            if poll_data.get("code") != 0:
                status_placeholder.error(f"轮询错误: {poll_data}")
                break
                
            code = poll_data.get("data", {}).get("code")
            
            if code == 86101:
                status_placeholder.text("状态: 等待扫码...")
            elif code == 86090:
                status_placeholder.info("状态: 已扫码，请在手机上确认")
            elif code == 86038:
                status_placeholder.warning("状态: 二维码已过期，请刷新重试")
                break
            elif code == 0:
                status_placeholder.success("✅ 登录成功！正在提取 Cookie...")
                
                # 提取 Cookie
                sessdata = None
                bili_jct = None
                for cookie in session.cookies:
                    if cookie.name == "SESSDATA":
                        sessdata = cookie.value
                    elif cookie.name == "bili_jct":
                        bili_jct = cookie.value
                
                if sessdata and bili_jct:
                    # 构造 Cookie 字符串
                    cookie_str = f"SESSDATA={sessdata}; bili_jct={bili_jct}"
                    
                    # 本地模式可选保存到 cookie.txt
                    if save_cookie_file and APP_MODE == "local":
                        # 明确保存到当前工作目录（避免被归档到 subtitles_output）
                        cookie_path = os.path.abspath("cookie.txt")
                        try:
                            with open(cookie_path, "w", encoding="utf-8") as f:
                                f.write(cookie_str)
                            st.toast(f"Cookie 已保存到: {cookie_path}")
                        except Exception as e:
                            st.error(f"保存 cookie.txt 失败: {e}")
                    
                    # 应用到会话
                    set_cookie_from_ui(cookie_str)
                    
                    # 如果勾选了记住到浏览器 (Web模式下默认行为)
                    if remember_cookie and cookie_store is not None:
                        cookie_store[BROWSER_COOKIE_KEY] = st.session_state.get("cookie_value", "")
                        cookie_store.save()
                        if APP_MODE == "web":
                            st.toast("Cookie 已安全保存到您的浏览器中")
                    
                    st.rerun() # 刷新页面
                else:
                    st.error("未能从会话中提取有效 Cookie，请重试")
                break
            
            time.sleep(2)
            
    except Exception as e:
        st.error(f"发生错误: {str(e)}")


def main():
    st.set_page_config(page_title="B站字幕提取工具", page_icon="📝", layout="wide")
    st.title("B站字幕提取工具")
    st.caption("支持单视频、批量和手动粘贴 JSON 三种模式")

    cookie_store = init_browser_cookie_store()

    with st.sidebar:
        st.header("运行配置")
        
        # 模式自适应UI：根据APP_MODE决定默认值和可见性
        is_local = (APP_MODE == "local")
        
        # 本地模式无需配置 Cookie 记忆，默认开启文件保存
        # Web模式默认开启浏览器记忆
        if is_local:
            remember_cookie = False
        else:
            remember_cookie = True # Web模式默认记住到浏览器
            
        # 获取浏览器缓存的Cookie
        remembered_cookie = ""
        if cookie_store is not None:
            remembered_cookie = (cookie_store.get(BROWSER_COOKIE_KEY) or "").strip()
            
        # --- 扫码登录模块 Start ---
        with st.expander("📱 扫码登录 (推荐)", expanded=True):
            if st.button("获取登录二维码", use_container_width=True):
                # 本地模式保存 cookie.txt，Web模式不写服务端文件
                perform_qr_login(cookie_store, remember_cookie, is_local) 
        # --- 扫码登录模块 End ---

        cookie_text = st.text_area(
            "Cookie (或手动输入)",
            value=remembered_cookie,
            height=100,
            placeholder="SESSDATA=xxx; bili_jct=xxx",
            help="扫码登录成功后会自动填充此处",
        )
        
        # 仅在本地模式显示"从文件读取"选项，且默认开启
        if is_local:
            allow_file_cookie = True
            # st.info("已启用本地 cookie.txt 自动读取")
        else:
            allow_file_cookie = False

        prefer_ai = st.toggle("优先 AI 字幕", value=True)
        
        
        col_apply, col_clear = st.columns(2)
        with col_apply:
            apply_clicked = st.button("应用/刷新 Cookie", use_container_width=True)
        with col_clear:
            clear_clicked = st.button("清除当前会话", use_container_width=True)
            
        # 仅在 Web 模式提供清除浏览器记忆
        if not is_local:
            if st.button("清除浏览器记忆", use_container_width=True):
                 if cookie_store is not None and BROWSER_COOKIE_KEY in cookie_store:
                    del cookie_store[BROWSER_COOKIE_KEY]
                    cookie_store.save()
                    st.info("已清除浏览器保存的 Cookie")
        
        if clear_clicked:
            clear_cookie_session()
            st.info("已清除 Cookie 会话")



        if apply_clicked:
            ok, msg = set_cookie_from_ui(cookie_text, allow_file=allow_file_cookie)

            if ok and remember_cookie and cookie_store is not None:
                cookie_store[BROWSER_COOKIE_KEY] = st.session_state.get("cookie_value", "")
                cookie_store.save()
                msg = f"{msg}；已保存到浏览器"

            if "无效" in msg:
                st.error(msg)
            else:
                st.success(msg)

        cookie_ready, cookie_status_msg = apply_session_cookie()
        if cookie_ready:
            keys = st.session_state.get("cookie_keys", [])
            
            st.success(f"{cookie_status_msg}")
                
            if keys:
                st.caption(f"当前保留字段: {', '.join(keys)}")
        else:
             # 如果本地模式且启用了自动加载文件，尝试自动加载一次（仅在尚未加载时）
            if is_local and allow_file_cookie and not st.session_state.get("cookie_auto_loaded", False):
                ok, msg = set_cookie_from_ui(cookie_text, allow_file=True)
                if ok:
                     st.session_state["cookie_auto_loaded"] = True
                     st.rerun()
                else:
                     # 尝试加载失败，标记一下避免无限重试，但显示警告
                     st.session_state["cookie_auto_loaded"] = True
                     st.warning(cookie_status_msg)
            else:
                st.warning(cookie_status_msg)

        if not is_local and remember_cookie and cookie_store is None:
            st.caption("浏览器记忆组件不可用，请先安装 streamlit-cookies-manager。")

        if not is_local:
            st.caption("安全提示：云端模式下请勿开启日志共享，不要复用高权限主账号。")

    tab_single, tab_batch, tab_json = st.tabs(["单个视频", "批量视频", "手动 JSON"])

    with tab_single:
        st.subheader("单个视频获取")
        bvid = st.text_input("输入 BVID", value="", placeholder="例如：BV1ZL411o7LZ")

        if "single_result_state" not in st.session_state:
            st.session_state["single_result_state"] = None

        if st.button("开始提取", type="primary", use_container_width=True):
            if not bvid.strip():
                st.warning("请先输入 BVID")
            else:
                with st.spinner("正在获取字幕..."):
                    result_tuple, logs = capture_run(core.get_bilibili_subtitle, bvid.strip(), prefer_ai, return_raw=True)
                
                # 解析返回值
                raw_data = None
                content = None
                if isinstance(result_tuple, tuple) and len(result_tuple) == 2:
                    raw_data, error = result_tuple
                    if raw_data:
                        content = core.generate_txt(raw_data)
                    else:
                        content = error
                else:
                    content = result_tuple

                st.session_state["single_result_state"] = {
                    "bvid": bvid.strip(),
                    "raw_data": raw_data,
                    "content": content,
                    "logs": logs,
                }

        single_state = st.session_state.get("single_result_state")
        if single_state:
            current_bvid = single_state.get("bvid", "")
            current_raw_data = single_state.get("raw_data")
            current_content = single_state.get("content")
            current_logs = single_state.get("logs", "")

            render_result_block(
                "结果",
                (current_raw_data, current_content) if current_raw_data else current_content,
                key_prefix="single_result",
            )
            
            # --- 一键下载 / 保存 ---
            if current_raw_data and current_bvid:
                st.caption("分格式下载见上方预览区，或使用下方按钮批量操作：")
                col_save_action = st.container()
                
                # 本地模式：提供保存到本地目录的功能
                if is_local:
                    if col_save_action.button("📂 保存到本地目录（TXT + SRT + VTT）", use_container_width=True, type="primary"):
                        ok, save_dir, failed = core.save_subtitle_bundle(current_raw_data, current_bvid)
                        if ok:
                            st.success(f"已保存到: {save_dir}")
                        else:
                            st.error(f"保存失败，目录: {save_dir}，失败文件数: {len(failed)}")
                
                # Web模式（或通用）：提供打包下载功能
                else:
                    # 将单个视频的数据打包成 {bvid: data} 形式供 build_subtitle_zip 使用
                    single_batch_data = {current_bvid: current_raw_data}
                    
                    # 我们需要打包 txt, srt, vtt 三种格式
                    # 为了方便，我们可以循环生成三个文件的 ZIP 或者直接把三个文件通过 zipfile 打包
                    # 这里复用 build_subtitle_zip 有点麻烦，因为它一次只打一种格式
                    # 所以我们在下面手动构建一个包含三格式的 ZIP
                    
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                        zf.writestr(f"{current_bvid}.txt", core.generate_txt(current_raw_data))
                        zf.writestr(f"{current_bvid}.srt", core.generate_srt(current_raw_data))
                        zf.writestr(f"{current_bvid}.vtt", core.generate_vtt(current_raw_data))
                    
                    zip_data = zip_buffer.getvalue()
                    
                    col_save_action.download_button(
                        label="📦 一键下载所有格式 (ZIP)",
                        data=zip_data,
                        file_name=f"{current_bvid}_all_formats.zip",
                        mime="application/zip",
                        use_container_width=True,
                        type="primary"
                    )

            with st.expander("查看运行日志"):
                st.code(current_logs or "(无日志)")

    with tab_batch:
        st.subheader("批量获取字幕")
        raw_input = st.text_area(
            "输入多个 BVID（空格/逗号/换行分隔）",
            value="",
            placeholder="例如：BV1ZL411o7LZ\nBV1fT411B7od\nBV1Fk4y1v7fQ",
            height=120,
        )

        if "batch_last_success" not in st.session_state:
            st.session_state["batch_last_success"] = {}

        if st.button("批量提取", use_container_width=True):
            bvid_list = parse_bvid_list(raw_input)
            if not bvid_list:
                st.warning("未检测到有效 BVID")
            else:
                st.session_state["batch_last_success"] = {}
                st.write(f"检测到 {len(bvid_list)} 个 BVID")
                rows = []
                all_logs = []
                progress = st.progress(0)

                for idx, item in enumerate(bvid_list, 1):
                    # 改用return_raw=True以获取多格式数据
                    result_tuple, logs = capture_run(core.get_bilibili_subtitle, item, prefer_ai, return_raw=True)
                    all_logs.append(f"==== {item} ====\n{logs}")
                    
                    raw_data = None
                    content = None
                    if isinstance(result_tuple, tuple) and len(result_tuple) == 2:
                        raw_data, error = result_tuple
                        if raw_data:
                            content = core.generate_txt(raw_data)
                        else:
                            content = error
                    else:
                        content = result_tuple

                    ok = bool(content and not content.startswith("❌"))
                    rows.append({
                        "BVID": item,
                        "状态": "成功" if ok else "失败",
                        "信息": (content[:120] + "...") if content and len(content) > 120 else (content or ""),
                    })

                    if ok and raw_data:
                        st.session_state["batch_last_success"][item] = raw_data

                    progress.progress(idx / len(bvid_list))

                st.dataframe(rows, use_container_width=True)
                with st.expander("查看批量运行日志"):
                    st.code("\n".join(all_logs) or "(无日志)")

        batch_success = st.session_state.get("batch_last_success", {})
        if batch_success:
            st.divider()
            
            # --- 优化后的批量操作区 ---
            # 使用 container 将结果单独框起来，增加视觉层级
            results_container = st.container(border=True)
            with results_container:
                st.subheader("Results / 结果导出")
                st.write(f"🎉 成功提取 {len(batch_success)} 个视频字幕，请选择导出方式：")
                
                # 定义通用格式选项
                fmt_options = ["txt", "srt", "vtt"]

                # 分为两列：左侧单文件下载，右侧批量打包
                col_single, col_all = st.columns(2, gap="large")

                # 左列：单个视频下载 (直接提供文件，不打包)
                with col_single:
                    st.markdown("##### 📂 单个导出")
                    st.caption("选择特定视频，单独下载字幕文件")
                    
                    bvid_options = sorted(batch_success.keys())
                    pick_bvid = st.selectbox("选择视频 (BVID)", bvid_options, key="batch_pick_bvid")
                    pick_fmt = st.selectbox("选择格式", fmt_options, key="batch_pick_format_single")
                    
                    # 动态生成内容
                    if pick_bvid and pick_fmt:
                        subtitles = batch_success.get(pick_bvid)
                        file_content = generate_subtitle_content_by_format(subtitles, pick_fmt)
                        file_ext = pick_fmt

                        st.download_button(
                            label=f"⬇️ 下载 {pick_bvid}.{file_ext}",
                            data=file_content,
                            file_name=f"{pick_bvid}_字幕.{file_ext}",
                            mime="text/plain",
                            use_container_width=True,
                            key="batch_download_single_file",
                            type="secondary" 
                        )

                # 右列：批量 ZIP 打包
                with col_all:
                    st.markdown("##### 📦 批量打包")
                    st.caption("将所有成功提取的字幕打包为 ZIP 下载")
                    
                    all_fmt = st.selectbox("统一格式", fmt_options, key="batch_all_format_zip")
                    
                    # 生成 ZIP
                    all_zip_data = build_subtitle_zip(batch_success, all_fmt)
                    
                    st.download_button(
                        label=f"⬇️ 打包下载全部 ({all_fmt.upper()})",
                        data=all_zip_data,
                        file_name=f"all_subtitles_{all_fmt}.zip",
                        mime="application/zip",
                        use_container_width=True,
                        key="batch_download_all_zip",
                        type="primary" # 突出显示
                    )

    with tab_json:
        st.subheader("手动粘贴 JSON")
        st.caption("从浏览器开发者工具 Network 的字幕接口响应中复制 JSON 到下方")
        json_text = st.text_area("粘贴 JSON", height=240)

        if "json_result_state" not in st.session_state:
            st.session_state["json_result_state"] = None

        if st.button("解析 JSON", use_container_width=True):
            if not json_text.strip():
                st.warning("请先粘贴 JSON")
            else:
                result_tuple, logs = capture_run(core.parse_subtitle_json, json_text, return_raw=True)
                
                # Unpack
                raw_data = None
                content = None
                if isinstance(result_tuple, tuple) and len(result_tuple) == 2:
                    raw_data, error = result_tuple
                    if raw_data:
                        content = core.generate_txt(raw_data)
                    else:
                        content = error
                else:
                    content = result_tuple

                st.session_state["json_result_state"] = {
                    "raw_data": raw_data,
                    "content": content,
                    "logs": logs,
                }

        json_state = st.session_state.get("json_result_state")
        if json_state:
            json_raw_data = json_state.get("raw_data")
            json_content = json_state.get("content")
            json_logs = json_state.get("logs", "")

            render_result_block(
                "解析结果",
                (json_raw_data, json_content) if json_raw_data else json_content,
                key_prefix="json_result",
            )
            with st.expander("查看解析日志"):
                st.code(json_logs or "(无日志)")

    st.divider()
    st.caption("仅供学习交流使用，请遵守平台规则与法律法规。")


if __name__ == "__main__":
    main()
