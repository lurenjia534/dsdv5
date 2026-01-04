# check_trad.py 用法说明

## 依赖与运行位置

- 依赖：系统已安装 `opencc` 命令行工具（例如 `opencc --version` 可用）。
- 运行位置：在项目根目录执行（脚本会遍历当前目录下**一级文件夹**中的所有 `.json`）。

## 基本用法

```bash
python3 check_trad.py
```

默认模式会列出所有包含繁体字的 JSON 文件路径（相对路径）。

## 参数说明

`--summary`  
按一级文件夹输出 `YES/NO` 汇总，表示该文件夹是否存在包含繁体字的 JSON 文件。
在 TTY 终端下，`YES` 为红色、`NO` 为绿色；重定向/管道输出时为纯文本。

`--summary --files`  
在汇总模式下，列出命中的 JSON 路径。

`--details`  
输出每个命中文件的 JSON 路径、字符串预览，以及繁体字与位置索引。

`--one-based`  
仅在 `--details` 下生效，将位置索引改为 1 基（默认 0 基）。

`--chars`  
输出每个命中文件中**所有繁体字**（不去重）。

> 说明：`--summary`、`--details`、`--chars` 三种模式互斥，只能选择一种。

## 使用示例

### 1) 列出包含繁体字的文件

```bash
python3 check_trad.py
```

输出示例：
```
FolderA/example.json
FolderB/data/text.json
```

### 2) 按文件夹汇总

```bash
python3 check_trad.py --summary
```

输出示例：
```
FolderA  YES
FolderB  NO
```

如需列出命中的 JSON 路径：

```bash
python3 check_trad.py --summary --files
```

输出示例：
```
FolderA  YES
  FolderA/example.json
FolderB  NO
```

### 3) 列出繁体字与位置

```bash
python3 check_trad.py --details
```

输出示例：
```
FolderA/example.json
  /dialogue/0/text  這是一段測試文字
    這 x1 @0
    測 x1 @4
    試 x1 @5
```

使用 1 基位置索引：

```bash
python3 check_trad.py --details --one-based
```

### 4) 列出所有繁体字（不去重）

```bash
python3 check_trad.py --chars
```

输出示例：
```
FolderA/example.json
  這測試這測試
```

## 注意事项

- 仅扫描一级文件夹下的 `.json` 文件（会递归子目录）。
- 只检查 JSON 的**字符串值**，不检查 JSON key。
- 繁体识别基于 `opencc t2s` 的转换差异，简繁同形字不会被识别为繁体。
