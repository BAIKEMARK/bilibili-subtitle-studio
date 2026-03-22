import io
import os
import re
from contextlib import redirect_stdout

import streamlit as st

import 字幕 as core


def capture_run(func, *args, **kwargs):
    """执行函数并捕获终端日志输出，便于在界面中展示。"""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = func(*args, **kwargs)
    logs = buffer.getvalue()
    return result, logs


def parse_bvid_list(text):
    return re.findall(r"BV[0-9A-Za-z]+", text or "")


def set_cookie_from_ui(cookie_text):
    cookie_text = (cookie_text or "").strip()
    if cookie_text:
        core._user_cookie = cookie_text
        return True
    loaded, _ = capture_run(core.load_cookie_from_file)
    return loaded


def render_result_block(title, content):
    st.subheader(title)
    if content and not content.startswith("❌"):
        st.success("字幕获取成功")
        st.text_area("字幕内容", content, height=260)
        st.download_button(
            label="下载字幕 TXT",
            data=content,
            file_name="subtitle.txt",
            mime="text/plain",
            use_container_width=True,
        )
    else:
        st.error(content or "获取失败")


def main():
    st.set_page_config(page_title="B站字幕提取工具", page_icon="📝", layout="wide")
    st.title("B站字幕提取工具")
    st.caption("支持单视频、批量和手动粘贴 JSON 三种模式")

    with st.sidebar:
        st.header("运行配置")
        cookie_text = st.text_area(
            "Cookie（可选）",
            value="",
            height=140,
            placeholder="SESSDATA=xxx; bili_jct=xxx",
            help="云端部署推荐通过这里临时输入 Cookie，不建议把 cookie.txt 上传到仓库。",
        )
        prefer_ai = st.toggle("优先 AI 字幕", value=True)
        auto_save = st.toggle("自动保存到本地文件", value=False)

        cookie_ready = set_cookie_from_ui(cookie_text)
        if cookie_ready:
            st.success("Cookie 已就绪")
        else:
            st.warning("未检测到可用 Cookie，AI 字幕可能无法访问")

    tab_single, tab_batch, tab_json = st.tabs(["单个视频", "批量视频", "手动 JSON"])

    with tab_single:
        st.subheader("单个视频获取")
        bvid = st.text_input("输入 BVID", value="BV1ZL411o7LZ")

        if st.button("开始提取", type="primary", use_container_width=True):
            if not bvid.strip():
                st.warning("请先输入 BVID")
            else:
                with st.spinner("正在获取字幕..."):
                    result, logs = capture_run(core.get_bilibili_subtitle, bvid.strip(), prefer_ai)
                render_result_block("结果", result)
                if auto_save and result and not result.startswith("❌"):
                    filename = f"{bvid.strip()}_字幕.txt"
                    ok, _ = capture_run(core.save_subtitle_to_file, result, filename)
                    if ok:
                        st.info(f"已保存到: {os.path.abspath(filename)}")
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
                    result, logs = capture_run(core.get_bilibili_subtitle, item, prefer_ai)
                    all_logs.append(f"==== {item} ====\n{logs}")
                    ok = bool(result and not result.startswith("❌"))
                    rows.append({
                        "BVID": item,
                        "状态": "成功" if ok else "失败",
                        "信息": (result[:120] + "...") if result and len(result) > 120 else (result or ""),
                    })

                    if auto_save and ok:
                        capture_run(core.save_subtitle_to_file, result, f"{item}_字幕.txt")

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
                result, logs = capture_run(core.parse_subtitle_json, json_text)
                render_result_block("解析结果", result)
                with st.expander("查看解析日志"):
                    st.code(logs or "(无日志)")

    st.divider()
    st.caption("仅供学习交流使用，请遵守平台规则与法律法规。")


if __name__ == "__main__":
    main()
