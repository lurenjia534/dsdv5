# 安全繁转简脚本

该脚本用于**原地**将 JSON 文件中的繁体字转换为简体，使用 OpenCC 完成转换，同时**保护原文件的 CRLF**（若 CRLF 数量变化会跳过该文件）。

## 依赖

- 已安装 `opencc` 命令行工具

## 基本用法

```bash
python3 safe_opencc_convert.py
```

默认会遍历当前目录下的一级文件夹，递归处理其中所有 `.json`。

## 参数说明

`--config t2s.json`  
指定 OpenCC 配置，默认 `t2s.json`。

`--dry-run`  
只输出变更，不写入文件。

`--include-hidden`  
包含隐藏目录和隐藏文件（默认不处理）。

## 示例

### 1) 原地转换（默认）

```bash
python3 safe_opencc_convert.py
```

### 2) 只处理指定目录或文件

```bash
python3 safe_opencc_convert.py "Echoes of Oblivion.esp"
python3 safe_opencc_convert.py "Echoes of Oblivion.esp/0_SSEAT.json"
```

### 3) 先预览变更（不写入）

```bash
python3 safe_opencc_convert.py --dry-run
```

## 输出说明

- `UPDATED`：文件已写入转换结果
- `OK`：无变化
- `SKIP (CRLF changed)`：检测到 CRLF 数量变化，自动跳过
