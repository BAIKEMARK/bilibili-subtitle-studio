# B站字幕提取工具 v2.0

自动提取B站视频的AI字幕和CC字幕。

## 功能特点

- ✅ 支持AI字幕自动提取（需要登录）
- ✅ 支持CC字幕（手动上传的字幕）
- ✅ 批量处理多个视频
- ✅ 手动粘贴JSON模式
- ✅ 自动保存字幕到文件
- ✅ **一键自动获取Cookie** ⭐

## 快速开始

### 步骤1：获取Cookie（首次使用）

```bash
# 安装依赖
pip install selenium

# 自动获取Cookie
python auto_get_cookie.py
```

在打开的浏览器中扫码登录，脚本会自动提取Cookie并保存。

### 步骤2：提取字幕

```bash
python 字幕.py
```

选择使用模式：
1. **单个视频** - 输入BVID获取单个视频字幕
2. **批量获取** - 输入多个BVID批量处理
3. **手动粘贴JSON** - 从浏览器F12复制字幕JSON

### 步骤3：查看结果

字幕会自动保存为 `{BVID}_字幕.txt` 文件。

## 使用方法

### 单个视频
```bash
python 字幕.py
# 选择 1
# 输入BVID：BV1ZL411o7LZ
```

### 批量提取
```bash
python 字幕.py
# 选择 2
# 输入：BV1ZL411o7LZ BV1fT411B7od BV1Fk4y1v7fQ
# 确认：y
```

支持多种分隔方式：
- 空格：`BV1ZL411o7LZ BV1fT411B7od`
- 逗号：`BV1ZL411o7LZ,BV1fT411B7od`
- 换行：每行一个BVID

## 文件说明

```
B站字幕提取工具/
├── 字幕.py                   # 主程序 - 提取字幕
├── auto_get_cookie.py        # Cookie自动获取工具 ⭐
├── cookie.txt               # Cookie文件（自动生成）
├── README.md                # 本文件
├── 开始使用.md              # 快速开始指南
└── {BVID}_字幕.txt          # 提取的字幕文件
```

## 依赖安装

```bash
pip install requests selenium
```

## 常见问题

**Q: 提示"账号未登录"怎么办？**

A: 运行 `python auto_get_cookie.py` 获取新的Cookie。

**Q: Cookie有效期多久？**

A: 通常30天左右，过期后重新运行 `auto_get_cookie.py` 即可。

**Q: AI字幕和CC字幕有什么区别？**

A:
- **AI字幕**：B站自动生成的字幕，需要登录才能获取
- **CC字幕**：UP主手动上传的字幕，无需登录

**Q: 视频有字幕但提取失败？**

A:
1. 确认是软字幕（可切换开关），不是硬字幕（嵌入视频画面）
2. 刷新Cookie：`python auto_get_cookie.py`
3. 使用模式3手动粘贴JSON

**Q: 批量处理速度太快被限制？**

A: 脚本已内置1秒延迟，如果仍被限制，可增加延迟时间。

## 示例

### 批量提取三个视频的字幕

```bash
python 字幕.py
# 选择 2
# 输入：BV1ZL411o7LZ BV1fT411B7od BV1Fk4y1v7fQ
# 确认：y
```

## 版本历史

- **v2.0** - 添加批量处理、Cookie自动获取
- **v1.0** - 初始版本，支持基本字幕提取

## 注意事项

- Cookie包含敏感信息，请勿分享给他人
- Cookie有过期时间（通常30天），失效后需重新获取
- 请合理使用，遵守B站用户协议
- 建议不要过于频繁地批量请求，避免被限流

## 许可证

仅供学习交流使用
