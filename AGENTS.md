# SMT2 项目指南

## 项目概述

SMT2 是一个基于 PySide6 的 Windows 桌面悬浮面板应用，集成了系统监控、待办事项管理和工具箱功能。详见 [README.md](README.md)。

## 构建和运行

```bash
# 安装依赖（注意：非标准格式，需逐行执行）
pip install jieba pyside6 wmi pywin32 pandas python-docx

# 开发运行
python main.py

# Nuitka 打包（单文件，优化体积和速度）
python -m nuitka --onefile ^
  --output-filename=SMT2.exe ^
  --output-dir=output ^
  --enable-plugin=pyside6 ^
  --include-package-data=jieba ^
  --include-package=pandas ^
  --follow-import-to=need ^
  --nofollow-import-to=torch ^
  --nofollow-import-to=numba ^
  --nofollow-import-to=IPython ^
  --nofollow-import-to=pytest ^
  --nofollow-import-to=unittest ^
  --nofollow-import-to=setuptools ^
  --nofollow-import-to=pip ^
  --nofollow-import-to=wheel ^
  --noinclude-setuptools-mode=nofollow ^
  --noinclude-pytest-mode=nofollow ^
  --noinclude-unittest-mode=nofollow ^
  --noinclude-IPython-mode=nofollow ^
  --lto=yes ^
  --assume-yes-for-downloads ^
  --disable-console ^
  --windows-icon-from-ico=resources/tray.png ^
  main.py
```

## 架构

```text
main.py                     ← 入口：初始化配置→QApp→MainWidget→SystemTray
src/
├── configs/                ← 配置读写（base_config / defaul_config）
├── themes/                 ← 新主题系统（策略模式，用于主面板）
├── tray/                   ← 系统托盘图标
├── utils/                  ← 工具类（性能监控/路径/标签提取/自启/置顶）
└── views/
    ├── main_views/         ← 主窗口：性能面板+待办面板+嵌入模式
    ├── toolbox_views/      ← 工具箱：设置/Excel→Word/可视化主题编辑器
    └── components/         ← 可复用 UI 组件（如 Switch）
```

### 关键架构要点

- **双 ThemeManager 并存**：`src/themes/` 中的新系统（策略模式，`ThemeDefinition` 抽象基类，用于主面板的 `PerformancePanel.paintEvent()` 委托绘制）与 `src/utils/theme_manager.py` 中的旧系统（QSS 文件切换，用于工具箱窗口）是**两个不同的主题系统**，修改时注意区分。
- **数据流**：`main.py` 初始化 → `MainWidget` 托管各面板 → `SystemTrayIcon` 控制切换 → 各 Widget 通过 `theme_manager.add_listener()` 响应主题变更。
- **配置分层**：只读模板 `resources/default_properties.json` → 用户可写 `%APPDATA%/SMT2/properties.json`。首次运行由 `AppPaths` 自动复制。

## 编码约定

- **导入风格**：全部使用绝对导入 `from src.xxx import yyy`，无 `src/__init__.py`
- **配置**：`AppPaths` 统一管理路径，自动适配开发环境 vs Nuitka `--onefile` 打包（`sys._MEIPASS`）
- **主题颜色令牌**：字符串键 → `[r, g, b, a]` 值，定义在 `default_properties.json` 的 `colors` 字段中
- **信号/槽**：PySide6 Signal 命名如 `mode_changed`、`todos_changed`、`component_selected`
- **禁止使用文本图标（Emoji）**：UI 中不得使用 Emoji 字符作为图标（如 🚀、🔔、🟢、⏰ 等），这类文本图标会让项目有明显 AI 生成质感。统一使用纯文字描述、主题颜色形状、或系统图标资源替代。

## 注意事项

1. **`resources/requirements.txt` 非标准格式**：内容是 `pip install xxx` 指令而非 `package==version`，无法直接用 `pip install -r` 安装
2. **`defaul_config` 拼写错误**：文件名和类名缺少 "t"（应为 `default`），这是历史遗留，修改需同步更新所有引用
3. **jieba 内存问题**：v2.0.2 因 jieba 词典导致 185MB 内存占用，`LightweightTagExtractor`（`src/utils/lightweight_tag_extractor.py`）作为轻量替代方案
4. **Nuitka 打包**：`--output-filename=SMT2.exe` 指定输出文件名；`--lto=yes` 启用链接时优化减小体积；`--nofollow-import-to` 排除 torch/numba/IPython/pytest 等不必要依赖；`--noinclude-*-mode=nofollow` 排除标准库测试框架
