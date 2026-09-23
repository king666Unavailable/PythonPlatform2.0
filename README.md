# Python 教学平台 2.0

Python 教学平台 2.0 是面向教师、学生和管理员的前后端分离教学系统。系统围绕教学班、题库、作业、提交记录、成绩和知识图谱组织功能，用于支持 Python 课程的日常教学、练习、测试和学情管理。

本项目是原 Python 教学平台的重构版本。重构过程中保留了必要的历史数据兼容能力，并逐步将业务数据统一迁移到 MySQL。账号、教学班、题库、作业、提交和成绩等业务数据均从 MySQL 读取；知识图谱的结构和图谱管理功能仍从 Neo4j 读取或写入。

## 系统架构

项目采用前后端分离架构：

- 前端：Vue 3 + TypeScript + Vite，按用户身份和业务模块组织页面。
- 后端：Django + Django REST Framework，提供 `/api/v1/` 版本化接口。
- 业务数据库：MySQL，保存账号、教学班、题库、作业、提交、逐题成绩和系统配置。
- 知识图谱数据库：Neo4j，仅用于知识图谱结构、节点管理和图谱展示；不同机器可以使用各自的 Neo4j 实例。
- 编程题运行服务：通过 `.env` 中的 `PISTON_URL` 调用外部或自建的 Piston 兼容服务；代码运行与自动判卷是两个独立功能，目前只实现代码运行。

```text
浏览器
   │
   ├── Vue 前端（127.0.0.1:5173）
   │       │
   │       └── REST API（127.0.0.1:<后端端口>/api/v1）
   │                    │
   │                    └── MySQL：主要业务数据
   │
   ├── Neo4j：知识图谱结构和节点关系
   └── Piston 兼容运行服务：编程题代码运行
```

## 主要角色与功能

### 学生端

- 首页：教学概况、最近成绩和当前教学班信息。
- 我的作业：按照截止时间查看作业，支持进行中、判卷中、已完成和已逾期等状态。
- 作业答题：选择题、填空题和编程题作答，支持草稿保存、逐题用时记录和提交。
- 补交：教师开放补交后，学生在原作业入口按照规则进入补交。
- 个人中心：基本资料、测试完成情况、成绩曲线和学情画像占位入口。
- 知识图谱：读取 Neo4j 图谱，并展示个人知识点掌握度。
- 题目练习：从题库中进行题目练习。
- 编程题：使用 CodeMirror 编辑代码，并调用 Piston 兼容服务运行代码。

### 教师端

- 教学概况：当前教学班的教学数据概览。
- 作业管理：创建作业、选择题目、设置截止时间、答题时长和开放范围。
- 补交设置：为指定作业创建、开放、关闭和修改补交规则。
- 作业统计：查看成绩榜、提交情况、平均分趋势和导出内容。
- 班级学情：查看班级提醒、作业完成情况、学生详情及成绩趋势。
- 题库管理：从 MySQL 题库中检索、创建、编辑和删除题目。
- 知识图谱管理：从 Neo4j 维护课程、主题、知识和知识点结构。
- AI 出题：提供 AI 生成题目的审核入口，审核通过后写入 MySQL 题库。

### 管理员端

- 账号管理：管理管理员、教师和学生账号，支持单个创建、批量导入、状态管理和教学班成员关系。
- 教学班管理：创建和维护教学班，管理教师及学生成员。
- 功能显示配置：按角色配置前端导航栏中的功能显示与隐藏。
- 操作记录：查看账号登录、作业提交等系统操作记录。

## 目录结构

```text
PythonPlatform2.0/
├── backend/                         # Django 后端
│   ├── manage.py                     # Django 管理和开发入口
│   ├── api/                          # API 公共配置、认证和权限
│   │   └── v1/                       # /api/v1 路由入口
│   ├── apps/                         # 按业务领域拆分的后端模块
│   │   ├── admin/                    # 管理员、账号、教学班和审计
│   │   ├── assignments/              # 作业、作业题目和补交
│   │   ├── auth/                     # 登录、退出、密码修改、会话
│   │   ├── code_runner/              # 编程题代码运行
│   │   ├── context/                  # 当前教学班上下文
│   │   ├── grading/                  # 成绩和判卷相关服务
│   │   ├── knowledge/                # Neo4j 知识图谱接口
│   │   ├── questions/                # MySQL 题库接口
│   │   ├── student/                  # 学生资料、首页和学生功能
│   │   ├── submissions/              # 草稿、提交和作答详情
│   │   ├── teacher/                  # 教师作业统计和班级学情
│   │   ├── analytics/                # 学习分析接口
│   │   ├── mastery/                  # 掌握度接口
│   │   └── ai/                       # AI 对话、出题和审核
│   ├── repositories/                 # MySQL、Neo4j 及外部服务数据访问层
│   ├── domain/                       # 跨模块领域规则和数据结构
│   ├── config/settings/              # development、production、testing 配置
│   └── workers/                      # 后台任务相关代码
├── frontend/                         # Vue 前端
│   ├── src/
│   │   ├── views/auth/               # 登录和认证页面
│   │   ├── views/student/            # 学生端页面
│   │   ├── views/teacher/            # 教师端页面
│   │   ├── views/admin/              # 管理员端页面
│   │   ├── modules/                  # 按功能拆分的 API、类型和业务逻辑
│   │   ├── components/               # 通用组件
│   │   ├── layouts/                  # 不同身份的整体布局
│   │   ├── navigation/               # 导航配置和功能可见性
│   │   ├── router/                   # 路由和身份权限控制
│   │   ├── stores/                   # 会话、当前教学班等状态
│   │   └── styles/                   # 全局和模块样式
│   └── package.json                  # 前端依赖和脚本
├── database/
│   └── python_platform_schema.sql   # MySQL 最终表结构脚本
├── data/                             # 题库、快照和导入数据
├── requirements.txt                  # Python 依赖
└── README.md                         # 项目说明
```

## MySQL 数据分组

当前业务表按功能前缀组织，字段和表关系以 `database/python_platform_schema.sql` 为准。

| 数据分组 | 主要表 | 用途 |
| :--- | :--- | :--- |
| 用户 | `user_admins`、`user_teachers`、`user_students` | 三类账号及登录信息 |
| 教学班 | `classes`、`classes_teacher`、`classes_student`、`classes_preferences` | 教学班和成员关系、最近使用班级 |
| 知识图谱题库 | `graph_themes`、`graph_knowledge`、`graph_points`、`graph_questions` | MySQL 中的知识分类和题库 |
| 作业 | `assignments`、`assignment_items`、`assignment_makeup` | 作业、作业题目和补交规则 |
| 学习记录 | `submissions`、`submission_details`、`submission_grades` | 提交记录、学生逐题答案和逐题成绩 |
| 系统与扩展 | `audit_logs`、`feature_visibility_settings`、`code_runs`、AI 相关表 | 操作记录、功能显示、代码运行和 AI 扩展 |

需要注意：账号、教学班、题库、作业、提交和成绩等业务数据使用 MySQL。`graph_*` 表保存已经迁移到 MySQL 的知识分类、题库及掌握度计算所需的关系数据；知识图谱页面和教师知识图谱管理仍需要 Neo4j。Neo4j 节点对外使用稳定 `uid`，不应依赖会随数据库实例变化的 `elementId`。

## 技术栈

### 后端

- Language: Python 3.11
- Framework: Django 5.2 + Django REST Framework
- Database: MySQL + PyMySQL
- Knowledge Graph: Neo4j（知识图谱功能必需）
- File Processing: OpenPyXL

### 前端

- Framework: Vue 3 + TypeScript + Vite
- Code Editor: CodeMirror
- Knowledge Graph: vis-network
- Package Manager: npm

## 快速开始

### 1. 环境准备

确保本地已安装以下环境：

- Python 3.11（建议使用 Miniconda 或 Anaconda）
- Node.js LTS
- MySQL 5.7/8.0

创建并激活项目自己的 Python 环境。环境名称可以自行决定，以下以 `PythonClass` 为例：

```powershell
conda create -n PythonClass python=3.11
conda activate PythonClass
```

Linux 服务器也可以使用项目虚拟环境：

```bash
python3 -m venv .venv
source ./.venv/bin/activate
```

### 2. 数据库配置

1. 在 MySQL 中创建数据库：

   ```sql
   CREATE DATABASE python_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

2. 初始化数据库表结构：

   ```powershell
   mysql -u root -p python_platform < database/python_platform_schema.sql
   ```

3. 在项目根目录创建本地 `.env` 文件，填写 MySQL 和代码运行服务配置。该文件只用于本地配置，不要提交真实密码和 Token：

   ```env
   DJANGO_SECRET_KEY=your-development-secret
   DJANGO_DEBUG=true
   DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

   PYTHONPLATFORM_MYSQL_HOST=localhost
   PYTHONPLATFORM_MYSQL_PORT=3306
   PYTHONPLATFORM_MYSQL_USER=root
   PYTHONPLATFORM_MYSQL_PASSWORD=your_mysql_password
   PYTHONPLATFORM_MYSQL_DATABASE=python_platform

   NEO4J_URI=bolt://127.0.0.1:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your_neo4j_password
   NEO4J_DATABASE=

   PYTHONPLATFORM_BACKEND_PORT=8000
   DJANGO_CSRF_TRUSTED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173

   PISTON_URL=http://127.0.0.1:2000
   ```

如果不使用知识图谱功能，可以暂不启动 Neo4j；访问知识图谱相关页面时必须配置并启动 Neo4j。

如果数据库中已经存在业务数据，不要重复初始化或删除数据库，应先核对当前结构和数据，再进行迁移。

### 3. 后端部署

1. 在项目根目录打开终端并激活环境。

   Windows Anaconda：

   ```powershell
   conda activate PythonClass
   ```

   Linux 虚拟环境：

   ```bash
   source ./.venv/bin/activate
   ```

2. 安装 Python 依赖：

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

3. 初始化 Django 自带的数据表：

   ```bash
   cd backend
   python manage.py migrate
   ```

   该命令只管理 Django 自身的会话等表，不会创建项目业务表；业务表仍需执行 `database/python_platform_schema.sql`。

4. 启动 Django 后端：

   ```bash
   python manage.py runserver --noreload
   ```

   后端端口从项目根目录 `.env` 的 `PYTHONPLATFORM_BACKEND_PORT` 读取，默认是 `8000`。如果端口被占用，只修改 `.env`：

   ```env
   PYTHONPLATFORM_BACKEND_PORT=8001
   ```

   然后重新启动后端和前端。前端 Vite 配置会读取同一个端口，并将 `/api` 请求代理到后端。

后端健康检查地址为：

```text
http://127.0.0.1:<PYTHONPLATFORM_BACKEND_PORT>/api/v1/health
```

### 4. 前端部署

打开新的终端窗口，进入前端目录：

```powershell
cd frontend
```

第一次运行项目时，先安装前端依赖：

```powershell
npm install
```

`npm install` 只需要首次安装，或者 `package.json` 发生变化后重新执行。以后每次启动项目不需要重复安装依赖。

启动前端开发服务器（仅本机访问）：

```powershell
npm run dev
```

如果需要让同一局域网内的其他设备访问，使用：

```bash
npm run dev -- --host 0.0.0.0
```

浏览器访问地址为：

```text
http://127.0.0.1:5173/
```

远程访问时使用`http://服务器 IP:5173/`

若使用服务器 IP 或其他来源访问，需要在根目录 `.env` 中加入完整来源，协议、IP 和端口必须一致，末尾不要加 `/`：

```env
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,服务器IP
DJANGO_CSRF_TRUSTED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173,http://服务器IP:5173
```

多个来源使用英文逗号分隔。修改 `.env` 后需要重启后端。

## API 组织方式

所有接口以 `/api/v1/` 开头，并按领域拆分。例如：

| 领域 | 路径示例 | 说明 |
| :--- | :--- | :--- |
| 认证 | `/api/v1/auth/login` | 登录、退出、当前用户和密码修改 |
| 学生 | `/api/v1/student/...` | 学生首页、个人资料、作业和学习功能 |
| 作业 | `/api/v1/assignments/...` | 作业列表、详情、创建和补交 |
| 提交 | `/api/v1/submissions/...` | 草稿、提交、结果和成绩 |
| 题库 | `/api/v1/questions/...` | MySQL 题库检索和维护 |
| 教师 | `/api/v1/classes/...`、`/api/v1/teacher/...` | 教学班、学情和统计 |
| 管理员 | `/api/v1/admin/...` | 账号、教学班、审计和功能配置 |
| 知识图谱 | `/api/v1/knowledge-graph/...` | 知识图谱展示和管理，读取 Neo4j |
| 代码运行 | `/api/v1/code/...` | 编程题代码运行 |

登录采用 Django Session 和 CSRF 机制。前端通过当前会话获取用户身份，后端根据管理员、教师、学生角色及当前教学班执行权限校验。

## 当前实现边界

已具备主要前后端链路的功能包括：

- 三类账号登录、停用账号拦截和密码修改入口。
- 教学班切换及教师、学生、管理员的成员关系管理。
- MySQL 题库检索、作业创建、题目关联、作答、草稿保存和提交。
- 作业补交规则、开放对象和学生端补交入口。
- 教师端作业统计、班级学情、成绩趋势和导出入口。
- 学生端个人中心、测试完成情况和成绩曲线。
- 学生端知识图谱和教师端知识图谱管理，需要 Neo4j 配置。
- 编程题代码编辑和远程运行；自动判卷尚未实现。

仍保留的待实现或待优化方向包括：

- 学习路径相关功能
- 学情画像及部分学习分析功能。
- 管理员和教师操作记录的进一步完善。
- 历史学生数据迁移、导出格式优化和账号/作业删除等涉及多表的数据操作。

## 开发约定

- 新功能按角色和业务模块放入对应的 `backend/apps/`、`backend/repositories/`、`frontend/src/modules/` 和 `frontend/src/views/`。
- 页面标题、导航项和用户可见文案不展示内部功能编号或开发说明。
- 账号、教学班、题库、作业、提交和成绩通过 Repository 访问 MySQL；知识图谱结构通过 Neo4j 访问。
- 涉及多表的数据迁移、删除或结构调整，先核对数据库结构和关联关系，再执行变更并验证数据数量。
- 修改后至少执行后端测试、前端构建和 Django 系统检查。
