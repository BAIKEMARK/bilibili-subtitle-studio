# B站字幕提取工具 v3.0

自动提取 B 站视频的 AI 字幕和 CC 字幕，支持命令行和可视化界面（Streamlit）。

## 功能特点

- 支持 AI 字幕自动提取（需要登录）
- 支持 CC 字幕（手动上传的字幕）
- 支持批量处理多个视频
- 支持手动粘贴 JSON 模式
- 自动保存字幕到文件
- 一键自动获取 Cookie
- Streamlit 可视化界面（可部署到 Streamlit Community Cloud）

## 快速开始

### 方式 A：可视化界面（推荐）

1. 安装依赖

   pip install -r requirements.txt

2. 启动界面

   streamlit run app.py

3. 打开浏览器后可使用三种模式

- 单个视频
- 批量视频
- 手动粘贴 JSON

### 方式 B：命令行模式

1. 安装依赖

   pip install -r requirements.txt

2. 获取 Cookie（首次使用）

   python cookie_auto_login.py

3. 提取字幕

   python subtitle_extractor.py

## Streamlit Community Cloud 部署（GitHub）

1. 推送代码到 GitHub

确保仓库包含以下文件：
- app.py
- subtitle_extractor.py
- requirements.txt
- .gitignore

2. 在 Streamlit Community Cloud 创建应用

- 使用 GitHub 登录 Streamlit Community Cloud
- 点击 New app
- 选择你的仓库与分支
- Main file path 填 app.py
- 点击 Deploy

3. Cookie 使用建议

- 不要把个人 Cookie 提交到仓库
- 云端运行时建议在页面侧边栏临时粘贴 Cookie
- 如果出现Cookie 可能失效提示，请重新登录并更新 Cookie

## 文件说明

B站字幕提取工具/
- app.py                    # Streamlit 可视化入口
- subtitle_extractor.py     # 主程序（核心提取逻辑）
- cookie_auto_login.py      # Cookie 自动获取工具
- requirements.txt          # 依赖列表
- cookie.txt                # 本地 Cookie 文件（不提交）
- README.md                 # 项目说明
- quick_start.md            # 快速开始指南
- {BVID}_字幕.txt           # 字幕输出文件

## 常见问题

Q: 提示账号未登录怎么办？
A: 运行 python cookie_auto_login.py 获取新的 Cookie。

Q: Cookie 有效期多久？
A: 通常 30 天左右，过期后重新获取即可。

Q: 视频有字幕但提取失败怎么办？
A:
1. 确认是软字幕（可切换），不是硬字幕（嵌入画面）
2. 刷新 Cookie：python cookie_auto_login.py
3. 使用手动 JSON 模式

Q: 出现Cookie 可能失效或权限不足怎么办？
A: 说明当前登录态或账号权限不满足，建议重新获取 Cookie 或更换账号测试。

## 版本历史

- v3.0：新增 Streamlit 可视化界面与云部署说明
- v2.0：添加批量处理、Cookie 自动获取
- v1.0：初始版本，支持基本字幕提取

## 注意事项

- Cookie 包含敏感信息，请勿分享给他人
- Cookie 有过期时间，失效后需重新获取
- 请合理使用，遵守平台规则和相关法律法规

## 许可证

仅供学习交流使用
