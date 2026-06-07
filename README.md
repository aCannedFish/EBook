## 电子书城（HTML + React）

本仓库是课程《互联网应用开发技术》的课程项目，包含两套前端实现：

- `html-version`：原生 HTML + CSS 静态页面版本
- `react-version`：React + React Router 版本
- `main`：文档主分支（仅保留说明文档）

### 仓库结构

```text
main
  README.md                  统一项目说明
  （其他说明文档）

html-version
  pages/                     静态页面
  css/                       样式文件
  assets/                    图片与图标资源
  HTML_DESIGN.md             HTML 设计说明

react-version
  react-ebook/               React 项目目录
    src/
      pages/                 各业务页面（按模块下沉 loader/action）
      routes/                Root 路由、鉴权处理、错误边界
      data/                  Data.json 与前端内存仓库 appStore
      components/            可复用组件（含 BookCard、DashboardLayout、ResourceTable 等）
    public/assets/           静态资源
  REACT_DESIGN.md            React 设计说明（随 react-version 架构同步维护）
  DATA.md                    数据交互与状态流转说明
  ACTION.md                  Data Router action 机制说明
  SEARCH.md                  顶栏搜索在共享布局下的数据流说明
  ANT_DESIGN.md              Ant Design 组件使用与 props 说明
```

### 运行方法

#### 1) 运行 HTML 版本

```bash
git checkout html-version
open pages/login.html
```

#### 2) 运行 React 版本

```bash
git checkout react-version
cd react-ebook
npm install
npm run dev
```

启动后按终端提示访问本地地址（通常为 `http://localhost:5173`）。

React 版本当前采用：

- Root + children 嵌套路由
- Data Router（loader/action/redirect）
- `App.jsx` 仅做路由装配（业务 loader/action 下沉到模块文件）
- `DashboardLayout` 在受保护父路由中统一共享（子页面只渲染内容区）
- UI 组件层使用 Ant Design（保留原数据路由与 `appStore` 读写链路）

#### 2.1) 运行 Spring Boot 后端（推荐一键脚本）

```bash
cd springboot-ebook
chmod +x run-local.sh stop-local.sh
./run-local.sh
```

后端默认地址：`http://localhost:8080`，可用以下接口验证：

- `GET /api/v1/books`
- `GET /api/v1/book/1`
- `POST /api/v1/users/register`

停止临时 MySQL 容器：

```bash
cd springboot-ebook
./stop-local.sh
```

#### 3) 查看文档主分支

```bash
git checkout main
```

### 说明

- `README.md` 在三个分支中内容保持一致。
- React 版本已接入 Spring Boot 后端 API；书籍、用户、购物车、订单均通过 `/api/v1/**` 与 MySQL 持久化联调（详见 `ANSWER_HW5.md`、`ANSWER_IT2.md`）。
