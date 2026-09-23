# 编程题判卷模式、流程与系统实现说明

> 更新时间：2026-09-14  
> 适用系统：Python Platform 2.0  
> 当前结论：系统已经完成“标准输入/输出模式”的远程运行和自动判卷基础能力；函数调用、程序填空、结构化返回值等能力已完成模式设计，但尚未接入正式判卷链路。

## 1. 编程题判卷的核心问题

编程题判卷并不是简单地把一段代码发送到 Piston，然后看程序能不能运行。系统需要先明确四件事：

1. 学生提交的代码是什么形式；
2. 测试程序如何调用学生代码；
3. 测试数据如何传递给学生代码；
4. 程序结果采用什么规则比较。

不同题型的区别主要不在于是否使用 Piston，而在于“代码入口”和“结果比较方式”不同。

## 2. 判卷模式分类

### 2.1 标准输入/输出模式

这是当前系统已经实现的模式，适合要求学生编写完整程序的题目。

学生代码：

```python
a, b = map(int, input().split())
print(a + b)
```

测试用例：

```json
{
  "stdin": "3 5",
  "expected_output": "8",
  "weight": 1
}
```

执行过程：

```text
学生代码 → main.py
测试用例 stdin → 标准输入
程序 stdout → 与 expected_output 比较
```

这种模式下不需要教师提供测试脚本，也不需要使用 `assert`。教师只需填写输入和期望输出。

### 2.2 普通函数调用模式

适合题目要求学生实现一个函数的情况，例如：

```python
def square_sum(*args):
    return sum(x * x for x in args)
```

系统不能只运行这段代码，因为函数没有被调用。判卷器需要自动生成通用测试入口：

```python
from student_solution import square_sum

result = square_sum(1, 2, 3)
print(result)
```

配置示例：

```json
{
  "execution_mode": "function",
  "function_name": "square_sum",
  "args": [1, 2, 3],
  "kwargs": {},
  "expected_value": 14,
  "weight": 1
}
```

对于可变长度参数，`args` 中的每个元素应当作为一个独立的位置参数传入，而不是把整个列表作为一个参数传入。

#### 函数名必须保持一致

`function_name` 是判卷器调用学生代码的固定入口。例如配置为：

```json
{
  "function_name": "square_sum"
}
```

后端会根据配置调用：

```python
from student_solution import square_sum

result = square_sum(1, 2, 3)
```

如果学生将函数名改成其他名称，例如 `sum_square`，判卷器就无法导入和调用原函数。此时不应把题目直接判为 0 分，而应提示函数入口错误。

函数题的前端代码编辑器需要在题目上方显示明确提示：

> 请保留函数名 `square_sum`，只修改函数内部代码。修改函数名会导致系统无法调用和判卷。

正式判卷前，后端还应进行入口校验：

1. 检查学生代码能否正常解析；
2. 检查配置中的函数是否存在；
3. 检查函数名是否与 `function_name` 完全一致；
4. 检查函数是否能够被调用。

函数名不存在时，建议使用独立状态：

```text
function_not_found
```

并向学生提示：

> 未找到指定函数 `square_sum`，请检查函数名是否被修改。

后续可以为函数题提供带固定函数签名的起始代码，并限制学生主要修改函数体，减少误改函数名的情况。当前系统的函数调用模式尚未接入正式判卷，因此上述提示、入口校验和错误状态属于函数判卷实现时必须补充的能力。

### 2.3 代码片段自动包装模式

有些题目要求学生填写一段代码，但学生提交的内容本身不包含函数定义，也不通过 `input()` 接收输入。例如学生只需要编写：

```python
answer = sum(numbers)
```

这段代码不能直接作为独立程序判卷，也不能直接导入函数。系统应根据教师配置，自动把学生代码包装到统一函数中：

```python
def solve(numbers):
    answer = sum(numbers)
    return answer

result = solve([1, 2, 3])
```

建议将这种模式命名为：

```text
wrapped_body
```

配置示例：

```json
{
  "execution_mode": "wrapped_body",
  "function_name": "solve",
  "parameter_names": ["numbers"],
  "args": [[1, 2, 3]],
  "kwargs": {},
  "return_variable": "answer",
  "return_type": "number",
  "expected_value": 6
}
```

如果题目不需要输入，但学生代码通过约定变量返回结果，可以配置空参数：

```json
{
  "execution_mode": "wrapped_body",
  "function_name": "solve",
  "parameter_names": [],
  "args": [],
  "return_variable": "answer"
}
```

该模式下：

- 学生只提交函数体代码；
- 后端自动添加函数定义、参数和调用入口；
- 学生代码不应包含 `return`，而应给约定的返回变量赋值；
- 没有 `input()` 时，测试数据通过函数参数或预置变量提供；
- 多个测试用例可以使用不同参数重复执行同一段学生代码。

后端可以使用 `textwrap.indent` 等方式统一缩进并生成包装入口，不需要教师为每道题创建加工 `.py` 文件。由于自动包装会改变代码作用域，教师需要明确学生代码是“完整程序”“完整函数”还是“函数体片段”。

如果学生代码包含顶层 `return`、依赖未配置的全局变量，或缩进/语法不完整，系统应在包装或编译阶段给出代码结构错误，而不是把它当作 Piston 服务不可用。

### 2.4 程序填空/模板函数模式

适合题目提供一段代码，学生只需将 `_` 替换成正确代码的情况。

例如题目提供：

```python
def fact(string):
    answer = []
    a = string._
    answer.append(a)
    return answer
```

学生提交的是补全后的完整源代码。系统不应简单地把每个下划线字符串替换掉，而应当：

1. 将题目模板展示给学生；
2. 学生提交补全后的完整代码；
3. 将代码保存为 `student_solution.py`；
4. 自动调用指定函数，例如 `fact("the cat")`；
5. 比较函数返回值。

配置示例：

```json
{
  "execution_mode": "function_template",
  "function_name": "fact",
  "args": ["the cat"],
  "kwargs": {},
  "return_type": "mixed_list",
  "expected_value": [
    "THE CAT",
    ["the", "cat"],
    "the/cat",
    0,
    "a cat"
  ],
  "weight": 1
}
```

这种模式仍然不要求教师编写独立的加工脚本，测试入口由后端统一生成。

### 2.5 结构化返回值模式

有些函数返回的不是单个数字或字符串，而是列表、字典、嵌套对象或 DataFrame。例如：

```python
def fact():
    return ["result", [1, 2], {"ok": True}]
```

这类结果不能可靠地通过普通字符串比较处理，需要先进行标准化：

```text
数字 → 数字比较
字符串 → 文本比较
列表/字典 → JSON 结构比较
DataFrame → 列名、索引、数据内容结构比较
```

对于题目返回多个 pandas DataFrame 的情况，比较器应当将每个 DataFrame 转换为稳定结构，例如：

```json
{
  "columns": ["year", "state", "pop"],
  "index": ["one", "two"],
  "records": [
    {"year": 2000, "state": "Ohio", "pop": 1.5}
  ]
}
```

不能直接比较 DataFrame 的字符串打印结果，因为列宽、空格、索引显示格式和浮点格式可能导致误判。

## 3. 测试用例的统一结构

无论采用哪种模式，一个测试用例都应当包含以下信息：

| 字段 | 作用 |
|---|---|
| `case_no` | 测试用例序号 |
| `weight` | 测试用例权重 |
| `is_hidden` | 是否对学生隐藏 |
| `stdin` | 标准输入模式使用 |
| `args` | 函数调用模式的位置参数 |
| `kwargs` | 函数调用模式的关键字参数 |
| `expected_output` | 标准输入/输出模式的期望文本 |
| `expected_value` | 函数模式的期望返回值 |
| `comparison_mode` | 比较规则 |
| `timeout_ms` | 执行超时时间 |

实际配置应根据执行模式使用不同字段，不应要求每道题填写所有字段。

## 4. 测试用例的执行流程

### 4.1 学生进入答题页面

系统读取：

- 作业题目关系 `assignment_items.question_id`；
- 题目配置 `graph_questions.programming_config_json`；
- 学生已有草稿和代码答案。

学生看到题干、代码编辑器和当前代码。题目配置中的标准答案、隐藏测试用例和内部判卷逻辑不会发送给学生。

### 4.2 学生点击“运行代码”

这是交互式预览，不代表正式提交。

当前流程为：

```text
StudentAssignmentView.vue
        ↓
POST /api/v1/code/runs
        ↓
GlotClient
        ↓
根目录 glotio.py
        ↓
PISTON_URL
        ↓
Piston 远程执行
```

运行结果返回 stdout、stderr、错误信息、退出码和执行耗时，不写入正式成绩。

### 4.3 学生点击“提交作业”

提交后由后端同步执行当前已实现的判卷流程：

```text
创建 submissions 记录
        ↓
读取题目和编程题配置
        ↓
逐题调用 ScoringService
        ↓
逐测试用例调用 Piston
        ↓
比较运行结果
        ↓
写入 submission_grades
        ↓
写入逐测试用例详情 JSON
        ↓
返回提交状态
```

### 4.4 每个测试用例如何运行

对于标准输入/输出模式：

```text
同一份学生代码
        + 当前测试用例 stdin
        → Piston
        → stdout
        → 与 expected_output 比较
```

对于函数模式：

```text
学生代码
        + 后端自动生成的通用调用入口
        + 当前测试用例 args/kwargs
        → Piston
        → 函数返回值
        → 结构化比较
```

每个测试用例都单独执行，互相之间不共享运行时状态。学生代码不会与测试用例文本拼接，测试用例只是输入数据或函数参数。

## 5. 结果类型处理

### 5.1 文本结果

适合标准输入/输出题。当前默认比较模式为忽略行尾空格和末尾换行，避免 `print()` 自动产生换行导致误判。

可以提供以下比较方式：

- 完全一致；
- 忽略末尾换行；
- 忽略每行末尾空格；
- 忽略行尾空格并忽略末尾换行。

### 5.2 数字结果

应当使用数值比较，而不是直接比较字符串。对于浮点数，需要配置允许误差，例如：

```json
{
  "result_type": "number",
  "tolerance": 0.000001
}
```

当前系统尚未接入独立的浮点误差配置。

### 5.3 列表、字典和嵌套 JSON

系统应当保持：

- 列表顺序敏感；
- 字典键顺序不敏感；
- 数字类型一致或按规则转换；
- 字符串和数字不能隐式混淆。

例如：

```python
["a", [1, 2], {"ok": True}]
```

应转换成稳定 JSON 后进行深度比较。

### 5.4 DataFrame 和 pandas 结果

DataFrame 比较至少需要考虑：

- 行数；
- 列名及列顺序；
- 索引值及索引顺序；
- 单元格值；
- 缺失值 `NaN`；
- 浮点数误差；
- 是否允许排序后相同。

对于题目2中的多个 DataFrame，建议使用 `dataframe_list` 结果类型，逐个转换后比较，而不是依赖 `repr()` 或打印文本。

### 5.5 异常结果

部分题目可能要求学生正确抛出异常。未来可以支持：

```json
{
  "expected_exception": "ValueError",
  "expected_message_contains": "invalid"
}
```

当前系统不会把“预期异常”作为独立正确结果处理，运行异常仍会进入运行错误状态。

## 6. 教师端需要配置什么

### 6.1 当前教师端已经提供的配置

在教师端题库管理中，选择“编程题”或“程序填空题”后，可以配置：

| 配置项 | 说明 |
|---|---|
| 语言 | 当前默认 `python` |
| 版本 | Piston 运行时版本，`latest` 表示使用可用的最高版本 |
| 文件名 | 默认 `main.py` |
| 超时 | 单个测试用例的最大执行时间 |
| 输出比较 | 完全比较、忽略末尾换行、忽略行尾空格等 |
| 标准输入 | 传给程序的输入文本 |
| 期望输出 | 用于和 stdout 比较的文本 |
| 权重 | 当前测试用例在本题中的分值比例 |
| 隐藏测试用例 | 运行结果可保存，但不向学生暴露标准答案 |

这些配置保存在：

```text
graph_questions.programming_config_json
```

教师不需要填写 `submission_grades`，判卷结果由系统自动写入。

### 6.2 函数题未来需要增加的配置

为了支持题目1和题目3这类题，还需要在题库表单中增加：

- 执行模式：标准输入/输出、函数调用、程序填空；
- 函数名称，例如 `fact`、`square_sum`；
- 位置参数 `args`；
- 关键字参数 `kwargs`；
- 返回值类型，例如数字、字符串、JSON、DataFrame；
- 标准返回值；
- 浮点误差或结构化比较规则；
- 题目模板/起始代码；
- 依赖包，例如 `pandas`。

## 7. 是否需要教师创建测试脚本

### 7.1 普通标准输入/输出题：不需要

教师只需填写：

- 输入数据；
- 期望输出；
- 测试权重。

系统直接把学生代码作为 `main.py` 发送给 Piston。

### 7.2 普通函数题：不需要单独脚本

后端可以根据 `function_name`、`args` 和 `kwargs` 自动生成统一的调用入口。教师配置的是数据，不是 Python 测试程序。

这样可以避免：

- 每道题创建一个额外的 `.py` 文件；
- 教师维护测试脚本版本；
- 测试脚本与学生代码文件名冲突；
- 自定义脚本中出现不安全操作。

### 7.3 复杂题：可以支持可选测试适配器

如果题目需要复杂对象构造、特殊导入、多个函数协作或 DataFrame 专用标准化，可以增加“系统内置适配器”，但不建议允许教师直接上传任意脚本。

推荐的安全顺序是：

1. 优先使用系统内置的通用函数调用器；
2. 使用系统内置的 JSON、DataFrame、浮点数比较器；
3. 只有通用适配器无法覆盖时，才增加经过审核的适配器类型；
4. 不允许教师上传可以任意执行系统命令的判卷脚本。

## 8. 是否需要使用 `assert`

### 8.1 标准输入/输出模式：不需要

系统直接比较 stdout 和期望输出即可。

### 8.2 函数调用模式：可以使用，但不建议让教师手写

测试入口内部可以使用断言：

```python
assert square_sum(1, 2, 3) == 14
```

但更推荐系统统一捕获返回值后比较：

```python
actual = square_sum(1, 2, 3)
compare(actual, expected)
```

原因是统一比较器可以处理：

- 列表和字典深度比较；
- DataFrame 结构比较；
- 浮点误差；
- 缺失值；
- 失败原因和差异信息。

### 8.3 `assert` 的适用范围

`assert` 适合简单的布尔判断，但不适合作为整个判卷系统的唯一机制。它存在以下问题：

- 默认错误信息不够详细；
- 复杂对象差异不容易展示；
- DataFrame 的断言需要专用方法；
- Python 以优化模式运行时，`assert` 可能被禁用；
- 不同语言需要不同断言语法；
- 教师编写任意断言脚本会扩大执行风险。

因此建议：测试用例使用 JSON 数据表达，比较逻辑由后端统一实现；必要时在内部适配器中使用断言，但不暴露给教师作为必填脚本。

## 9. 当前系统的实际实现

### 9.1 数据库结构

本次基础版没有增加测试用例表，只增加两个 JSON 字段：

| 表 | 字段 | 作用 |
|---|---|---|
| `graph_questions` | `programming_config_json` | 保存题目的运行配置和测试用例 |
| `submission_grades` | `grading_details_json` | 保存每个测试用例的运行结果 |

这样可以保持现有题目、作业和提交关系不变。

### 9.2 后端判卷

核心文件：

- `backend/domain/programming.py`：规范化编程题配置、输出比较；
- `backend/domain/scoring.py`：客观题和编程题统一判卷；
- `backend/apps/code_runner/services.py`：Piston 远程调用；
- `backend/repositories/mysql_question_repository.py`：读写题目配置；
- `backend/repositories/learning_repository.py`：写入逐题成绩和测试结果。

当前编程题判卷流程：

1. 从 `assignment_items.question_id` 读取题目；
2. 从 MySQL 读取 `programming_config_json`；
3. 对每个测试用例调用一次 Piston；
4. 比较 stdout 与 `expected_output`；
5. 根据权重计算编程题 0–100 分；
6. 将测试用例结果写入 `grading_details_json`；
7. 所有题目完成判卷后，查看结果时汇总逐题分数。

### 9.3 运行文件

`main.py` 是默认的远程运行文件名，不是系统中长期保存的公用文件。

系统每次运行都会临时组装：

```json
{
  "name": "main.py",
  "content": "学生提交的代码"
}
```

不同题目使用各自的学生代码，不共享代码内容。教师可以在题目配置中修改文件名，但普通 Python 题保持 `main.py` 即可。

### 9.4 判卷状态

| 状态 | 含义 |
|---|---|
| `graded` | 已完成判卷并得到分数 |
| `pending_test_cases` | 题目没有配置测试用例，不判 0 分 |
| `grading_unavailable` | Piston 服务不可用，不判为答错 |
| `grading` | 作业整体仍处于判卷中/待处理 |

`submission_grades.grading_details_json` 记录测试用例状态、实际输出、运行错误和耗时，但不会把隐藏测试用例的标准答案返回给学生。

## 10. 当前尚未实现的能力

### 10.1 函数调用判卷

尚未支持：

- `function_name` 配置；
- 自动生成函数调用入口；
- `args`/`kwargs` 测试参数；
- 学生代码导入和函数调用隔离。

因此题目1目前还不能直接按函数返回值自动判卷。

### 10.2 代码片段自动包装判卷

尚未支持：

- `wrapped_body` 执行模式；
- 自动为学生代码添加函数定义和调用入口；
- `parameter_names`、`return_variable` 等包装配置；
- 将测试用例参数注入包装函数；
- 包装阶段的语法、缩进和作用域校验。

当前系统不能可靠判断一段不含函数、也不使用 `input()` 的代码应该如何调用。后续应由教师明确选择“代码片段自动包装模式”，由后端生成通用 runner，而不是为每道题手工创建加工脚本。

### 10.3 程序填空判卷

尚未支持：

- `starter_code` 模板字段；
- 程序填空题的模板展示和草稿初始化；
- 指定函数调用；
- 多个空位的完整提交校验。

题目2和题目3目前只能作为普通编程代码提交，不能按原系统的函数返回结果自动判卷。

### 10.4 结构化结果比较

尚未支持：

- 列表/字典深度比较器；
- DataFrame 标准化比较器；
- `NaN` 和浮点误差策略；
- 排序不敏感比较；
- 预期异常比较。

### 10.5 运行环境依赖管理

虽然题目可以在配置中说明依赖包，但当前 Piston 运行环境不会根据题目自动安装 `pandas` 等依赖。题目2要稳定判卷，必须先确认 Piston Python runtime 已安装 pandas，或建立固定的带 pandas 运行镜像。

### 10.6 异步判卷和人工处理

当前提交请求会同步等待 Piston 返回。尚未实现：

- 异步判卷队列；
- 重试机制；
- 教师人工修改编程题分数；
- 判卷失败后的人工重判；
- 判卷结果修正审计。

## 11. 推荐的后续实现顺序

1. 扩展 `programming_config_json`，增加 `execution_mode`；
2. 先实现 Python 函数调用模式；
3. 增加 `function_name`、`args`、`kwargs` 和 `expected_value`；
4. 实现 `wrapped_body` 代码片段自动包装模式；
5. 后端生成通用 runner，不允许教师上传任意脚本；
6. 增加列表、字典和混合结构比较；
7. 增加程序填空模板和起始代码；
8. 增加 DataFrame 专用比较器和 pandas 运行环境；
9. 再实现异步判卷、重试和人工判卷。

在函数判卷模式正式完成前，教师应将编程题明确设计为“完整程序 + 标准输入/输出”，否则学生只实现函数的题目会因为没有自动调用入口而无法得到正确结果。
