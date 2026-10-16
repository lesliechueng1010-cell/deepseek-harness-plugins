# dsh-startup-screen + 通行口令闸门 · 交接包

本包含且仅含**一个项目**：DeepSeek Harness 插件 `dsh-startup-screen` 1.1.0
（上游 MIT © 沈宏宏 · <https://github.com/6shenhonghong9/dsh-startup-screen>），
外加本机对其第 2 步「身份资料确认」增加的**通行口令闸门**补丁。

生成时间：2026-10-16 23:44
生成方式：本包由本机工作区里的打包脚本生成，**该脚本不随包提供**；包内 `patch/` 只含口令闸门本身的实现与断言脚本。

## 与上游的差异（只有这两处）

| 文件 | 改动 |
|---|---|
| `lib/index.js` | `DEFAULTS` 登记 `password`。宿主侧 `normalize()` **只保留 DEFAULTS 里已有的键**，而整个配置是 `safeJson(cfg)` 注入页面的，所以这是口令能到达浏览器的必要一步 |
| `lib/splash.js` | 页侧 `DEFAULTS` 同步该键；第 2 步身份卡增加「访问口令」输入行；`waitAction()` 在配了口令时要求输入匹配才放行 |
| `lib/splash.css` | 口令行、聚焦下划线、错口令抖动（`ACCESS DENIED`）的样式 |

**没配口令时行为与上游逐行等价**（按钮 / Enter / 空格任一都能过）。

## 安装

1. **推荐**：在 DSH 里用内置插件管理器，填入本目录的**绝对路径**；
2. 或先**完全退出**桌面端，执行 `dsh plugin --profile desktop add "<本目录绝对路径>"`，
   并确认包名已进入 `~/.dsh/profiles/desktop/package.json` 的 `dsh.profile.bundles`；
3. 重启 Harness。启动动画只在启动时播一次。

## 通行口令

口令来自 `~/.dsh/dsh-startup.json`：

```json
{ "password": "你的口令" }
```

- 必须是 JSON **字符串**。带前导零的口令只有字符串写法才保得住，写成数字会被吃掉、永远比对不上。
- 文件必须是**无 BOM 的 UTF-8**：插件的 `JSON.parse(fs.readFileSync(...,'utf8'))` 遇到 BOM 会抛错，
  而该抛错被 `try/catch` 静默吞掉 —— 表现为"口令写了但完全不生效"。用 `patch/set-password.py` 写入可避开。
- `""` 或删除该键 = 保持上游行为（点按钮 / 回车即通过）。
- 设置页的「重置」按钮走 `writeConfig(DEFAULTS)`，**会清空口令**；日常保存是 `{...current, ...patch}` 合并，不会。
- 门禁拦的是**序列**：跳过按钮 / Esc / 超时兜底仍然有效（上游"绝不锁黑屏"的设计），
  所以它防的是顺手跳过，不是安全边界。要不可绕过需关掉跳过与所有兜底，代价是忘记口令即无法进入。

## 逐条对应打包指令

| 指令要求排除 | 本包的处理 |
|---|---|
| `node_modules` | 插件目录内不含（本机以 link 方式安装，依赖不落在插件目录） |
| `.git` | 不含（原工作区未初始化 git） |
| 日志文件 | 按后缀 `*.log` / `*.tmp` 与临时文件排除；插件目录内本来也没有 |
| 密钥 / token | 全包按密钥形态扫描（`sk-*`、`ghp_*`、`AKIA*`、`PRIVATE KEY`、长 `Bearer`）→ 0 命中；唯一的口令已替换为 `<PASSPHRASE>` |
| 个人配置（身份名等） | 个人配置位于 `~/.dsh/dsh-startup.json`，**不在本包内**（包内只有插件本体）。包内出现的 `OPERATOR` / `0000` 是**上游公开的默认值**——上游自带测试即以二者为断言（`test/smoke-host.mjs` 断言"默认身份名称 = OPERATOR"、reset 后恢复该值），并非从本机读取的个人数据，故原样保留。若要改成中性默认值，需同时改上游 3 条测试断言，请先确认 |

## 上游许可与第三方素材（公开分发前必读）

- 上游代码与文案是 **MIT**（见 `LICENSE`，Copyright (c) 2026 沈宏宏）。MIT 允许修改与再分发，
  条件是**保留版权与许可声明** —— 若你公开本包的衍生版本，请保留 `LICENSE` 原文并在 README 注明来源与改动。
- ⚠️ **`lib/assets/*.mp3`（6 段人声 + 2 个音效）不在 MIT 范围内**：上游 README 免责声明第二条明示
  "音频素材（人声与音效）取自第三方视频"，第五条明示"开源许可仅覆盖作者原创的代码与文案，**不覆盖**上述第三方素材"。
  **对外公开分发前请删除或替换这些文件**；删除后插件会自动回落到 TTS / 现场合成音，不会报错。
- 上游 README 另声明"仅供学习交流 / 未授权任何商业用途"。MIT 文本本身允许商用，与该声明存在张力；
  实操上建议尊重作者声明。同时不要给上游代码部分附加比 MIT 更严格的限制。
- 画面中包含 DeepSeek 标识 —— 商标范畴，保留"非官方、与权利方无关"的声明。

## 本包做过什么

| 处理 | 内容 |
|---|---|
| 剔除 | `_orig-backup/`（补丁前备份）、`dsh-startup-screen-1.1.0.tgz`（补丁前预打包）、tar 解压产生的乱码 `.cmd`、日志与临时文件 |
| 脱敏 | 配置里的口令 → `<PASSPHRASE>`；本机地址 → `<MACHINE-IP>`；绝对路径中的账户名 → `%USERPROFILE%` / `%WORKSPACE%` |
| 未包含 | 其它任何插件或项目（鲸鱼挂件、玻璃背景、早期自研启动画面等一律不在本包内） |
| 打包后校验 | 逐文件反查敏感串（0 命中）+ 范围断言（归档内不得出现其它项目名） |

## 目录

```
dsh-startup-screen/
├── HANDOFF.md          本文件
├── LICENSE             上游 MIT 原文（未改动）
├── README.md           上游说明（未改动）
├── package.json  cordis.patch.yml
├── lib/                插件本体（含口令闸门补丁；assets/ 为上游音频，见上方警告）
├── preview/  test/  DESKTOP.md  INSTALL.md  AUDIO-FIELDS.md  open-preview.sh   上游原样保留
└── patch/              口令闸门的实现与验证工具
    ├── patch-password-gate.py   对干净上游副本重新打补丁（逐条断言命中，锚点缺失即拒绝写入）
    ├── test-password-gate.mjs   从补丁后的 lib/splash.js 抽出真实函数执行 15 条断言
    ├── test-config-plumbing.mjs 抽出宿主侧 DEFAULTS + normalize() 执行断言（断言值从配置读，不含明文）
    └── set-password.py          写入口令（无 BOM，写完反解校验）
```

> `preview/` 是上游的独立预览页：它按上游设计用应用内路由 `/dsh-startup/asset/...` 读音频，
> 因此**脱离 DSH 直接打开会有画面没声音**。若要在 DSH 外播放，需把音频基址改成相对路径
> （`%WORKSPACE%` 下的 `tools/export-desktop.py` 做过这件事，本包不含该脚本）。

## 验证状况（如实标注）

| 项 | 状态 |
|---|---|
| 口令闸门逻辑（抽取补丁后 `lib/splash.js` 的真实函数，15 条断言） | 通过 |
| 配置链路（抽取宿主侧 `DEFAULTS` + `normalize()`，9 条断言） | 通过 |
| `lib/splash.js` / `lib/index.js` 语法（`node --check`） | 通过 |
| 口令输入框的实际渲染版式 | **未验证**（构建机无可用浏览器） |

## patch/ 脚本使用注意

脚本内的本机路径已脱敏为 `%USERPROFILE%` / `%WORKSPACE%`，**不能直接运行**：
它们默认插件位于 `%WORKSPACE%\plugins\dsh-startup-screen`，请按目标机路径改回。
`patch-password-gate.py` 会对 7 处锚点逐一断言"恰好命中一次"，命中数不符即整体拒绝写入，
所以对已打过补丁的副本重跑是安全的（它会失败而不是重复插入）。
