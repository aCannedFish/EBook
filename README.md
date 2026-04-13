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
	src/                     页面、组件、样式、数据
	public/assets/           静态资源
  REACT_DESIGN.md            React 设计说明（保持不变）
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

#### 3) 查看文档主分支

```bash
git checkout main
```

### 说明

- `README.md` 在三个分支中内容保持一致。
- 业务数据目前为前端演示数据，不包含真实后端接口。

