import io
import os
import re
import time
from contextlib import redirect_stdout

import streamlit as st

import subtitle_extractor as core

try:
    from streamlit_cookies_manager import EncryptedCookieManager
except Exception:
    EncryptedCookieManager = None


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
    expires_at = st.session_state.get("cookie_expires_at", 0)
    cookie_value = st.session_state.get("cookie_value", "")

    if cookie_value and expires_at and time.time() >= expires_at:
        st.session_state["cookie_value"] = ""
        st.session_state["cookie_expires_at"] = 0
        st.session_state["cookie_keys"] = []
        core._user_cookie = None
        return False, "Cookie 已自动过期清除"

    if cookie_value:
        core._user_cookie = cookie_value
        return True, "Cookie 已就绪（仅会话内存）"

    core._user_cookie = None
    return False, "未检测到可用 Cookie，AI 字幕可能无法访问"


def set_cookie_from_ui(cookie_text, ttl_minutes=10, allow_file=False):
    cookie_text = (cookie_text or "").strip()
    if cookie_text:
        minimized_cookie, kept_keys = build_minimal_cookie(cookie_text)
        if not minimized_cookie:
            st.session_state["cookie_value"] = ""
            st.session_state["cookie_expires_at"] = 0
            st.session_state["cookie_keys"] = []
            core._user_cookie = None
            return False, "Cookie 格式无效或未包含必要字段（至少需要 SESSDATA）"

        st.session_state["cookie_value"] = minimized_cookie
        st.session_state["cookie_expires_at"] = int(time.time()) + int(ttl_minutes * 60)
        st.session_state["cookie_keys"] = kept_keys
        core._user_cookie = minimized_cookie
        return True, f"Cookie 已更新（字段最小化: {', '.join(kept_keys)}）"

    if allow_file:
        loaded, _ = capture_run(core.load_cookie_from_file)
        if loaded and core._user_cookie:
            minimized_cookie, kept_keys = build_minimal_cookie(core._user_cookie)
            if minimized_cookie:
                st.session_state["cookie_value"] = minimized_cookie
                st.session_state["cookie_expires_at"] = int(time.time()) + int(ttl_minutes * 60)
                st.session_state["cookie_keys"] = kept_keys
                core._user_cookie = minimized_cookie
                return True, "已从本地 cookie.txt 加载并最小化"

    return apply_session_cookie()


def clear_cookie_session():
    st.session_state["cookie_value"] = ""
    st.session_state["cookie_expires_at"] = 0
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


def render_result_block(title, result):
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
        st.text_area("字幕内容", content, height=260)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                label="📄 下载字幕 TXT",
                data=content,
                file_name="subtitle.txt",
                mime="text/plain",
                use_container_width=True,
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
                )
            with col3:
                vtt_content = core.generate_vtt(raw_data)
                st.download_button(
                    label="📝 下载字幕 VTT",
                    data=vtt_content,
                    file_name="subtitle.vtt",
                    mime="text/plain",
                    use_container_width=True,
                )
    else:
        st.error(content or "获取失败")



def main():
    st.set_page_config(page_title="B站字幕提取工具", page_icon="📝", layout="wide")
    st.title("B站字幕提取工具")
    st.caption("支持单视频、批量和手动粘贴 JSON 三种模式")

    cookie_store = init_browser_cookie_store()

    with st.sidebar:
        st.header("运行配置")

        remember_cookie = st.toggle("记住 Cookie 到浏览器（下次自动回填）", value=False)

        remembered_cookie = ""
        if remember_cookie and cookie_store is not None:
            remembered_cookie = (cookie_store.get(BROWSER_COOKIE_KEY) or "").strip()

        cookie_text = st.text_area(
            "Cookie（云端可选，输入后仅保存在会话内存）",
            value=remembered_cookie,
            height=140,
            placeholder="SESSDATA=xxx; bili_jct=xxx",
            help="默认仅保存在当前会话内存。开启上方选项后可保存到浏览器并自动回填。",
        )
        cookie_ttl = st.slider("Cookie 会话有效期（分钟）", min_value=1, max_value=60, value=10)
        allow_file_cookie = st.toggle("允许从 cookie.txt 读取（仅本地）", value=False)
        prefer_ai = st.toggle("优先 AI 字幕", value=True)
        auto_save = st.toggle("自动保存到本地文件", value=False)

        col_apply, col_clear, col_forget = st.columns(3)
        with col_apply:
            apply_clicked = st.button("应用 Cookie", use_container_width=True)
        with col_clear:
            clear_clicked = st.button("清除 Cookie", use_container_width=True)
        with col_forget:
            forget_clicked = st.button("清除浏览器记忆", use_container_width=True)

        if clear_clicked:
            clear_cookie_session()
            st.info("已清除 Cookie 会话")

        if forget_clicked:
            if cookie_store is not None and BROWSER_COOKIE_KEY in cookie_store:
                del cookie_store[BROWSER_COOKIE_KEY]
                cookie_store.save()
                st.info("已清除浏览器保存的 Cookie")
            else:
                st.info("当前未检测到浏览器记忆")

        if apply_clicked:
            ok, msg = set_cookie_from_ui(cookie_text, ttl_minutes=cookie_ttl, allow_file=allow_file_cookie)

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
            expires_at = st.session_state.get("cookie_expires_at", 0)
            remain = max(0, int(expires_at - time.time()))
            st.success(f"{cookie_status_msg}，剩余 {remain}s")
            if keys:
                st.caption(f"当前保留字段: {', '.join(keys)}")
        else:
            st.warning(cookie_status_msg)

        if remember_cookie and cookie_store is None:
            st.caption("浏览器记忆组件不可用，请先安装 streamlit-cookies-manager。")

        st.caption("安全提示：云端模式下请勿开启日志共享，不要复用高权限主账号。")

    tab_single, tab_batch, tab_json = st.tabs(["单个视频", "批量视频", "手动 JSON"])

    with tab_single:
        st.subheader("单个视频获取")
        bvid = st.text_input("输入 BVID", value="BV1ZL411o7LZ")

        if st.button("开始提取", type="primary", use_container_width=True):
            if not bvid.strip():
                st.warning("请先输入 BVID")
            else:
                with st.spinner("正在获取字幕..."):
                    result_tuple, logs = capture_run(core.get_bilibili_subtitle, bvid.strip(), prefer_ai, return_raw=True)
                
                # Unpack tuple for auto-save logic
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

                render_result_block("结果", (raw_data, content) if raw_data else content)
                
                if auto_save and content and not content.startswith("❌"):
                    filename = f"{bvid.strip()}_字幕.txt"
                    ok, _ = capture_run(core.save_subtitle_to_file, content, filename)
                    if ok:
                        # 构造正确的显示路径 (因为core.save_subtitle_to_file可能会修改保存位置)
                        display_path = os.path.join(core.OUTPUT_DIR, filename)
                        st.info(f"已保存到: {os.path.abspath(display_path)}")
                    if raw_data:
                        # Auto save other formats
                        srt_content = core.generate_srt(raw_data)
                        capture_run(core.save_subtitle_to_file, srt_content, f"{bvid.strip()}_字幕.srt")
                        vtt_content = core.generate_vtt(raw_data)
                        capture_run(core.save_subtitle_to_file, vtt_content, f"{bvid.strip()}_字幕.vtt")

                with st.expander("查看运行日志"):
                    st.code(logs or "(无日志)")

    with tab_batch:
        st.subheader("批量获取字幕")
        raw_input = st.text_area(
            "输入多个 BVID（空格/逗号/换行分隔）",
            value="BV1ZL411o7LZ\nBV1fT411B7od\nBV1Fk4y1v7fQ",
            height=120,
        )

        if st.button("批量提取", use_container_width=True):
            bvid_list = parse_bvid_list(raw_input)
            if not bvid_list:
                st.warning("未检测到有效 BVID")
            else:
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

                    if auto_save and ok:
                        # 保存三种格式
                        capture_run(core.save_subtitle_to_file, content, f"{item}_字幕.txt")
                        if raw_data:
                            srt = core.generate_srt(raw_data)
                            capture_run(core.save_subtitle_to_file, srt, f"{item}_字幕.srt")
                            vtt = core.generate_vtt(raw_data)
                            capture_run(core.save_subtitle_to_file, vtt, f"{item}_字幕.vtt")

                    progress.progress(idx / len(bvid_list))

                st.dataframe(rows, use_container_width=True)
                with st.expander("查看批量运行日志"):
                    st.code("\n".join(all_logs) or "(无日志)")

    with tab_json:
        st.subheader("手动粘贴 JSON")
        st.caption("从浏览器开发者工具 Network 的字幕接口响应中复制 JSON 到下方")
        json_text = st.text_area("粘贴 JSON", height=240)

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

                render_result_block("解析结果", (raw_data, content) if raw_data else content)
                with st.expander("查看解析日志"):
                    st.code(logs or "(无日志)")

    st.divider()
    st.caption("仅供学习交流使用，请遵守平台规则与法律法规。")


if __name__ == "__main__":
    main()
