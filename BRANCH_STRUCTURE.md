# 项目分支结构说明

## 分支概览

本项目现已分为三个分支，各自管理项目的不同版本：

### 1. main 分支（文档主分支）
**用途**：仅保留项目文档和说明信息  
**包含文件**：
- README.md - 项目说明
- Ans.docx - 开发对话记录
- Sum.md - 总结文档
- answer.md - 答案文档
- .gitignore - Git忽略配置（所有分支一致）

**不包含**：HTML 版本、React 版本和相关资源文件

### 2. html-version 分支
**用途**：保留原始的 HTML 静态版本  
**包含文件**：
- 所有静态 HTML 页面（pages/ 文件夹）
- CSS 样式文件（css/ 文件夹）
- 资源文件（assets/ 文件夹）
- 项目文档文件
- .gitignore（与其他分支一致）

**不包含**：React 版本（react-ebook/ 文件夹）

### 3. react-version 分支
**用途**：保留 React 版本的实现  
**包含文件**：
- React 项目文件（react-ebook/ 文件夹）
- 资源文件（assets/ 文件夹）
- 项目文档文件
- .gitignore（与其他分支一致）

**不包含**：HTML 版本（pages/、css/ 文件夹等）

## .gitignore 配置
所有分支使用统一的 .gitignore 配置：
- Sum.md
- Ans.docx
- .DS_Store
- .idea
- react-ebook/node_modules

## 分支切换说明

```bash
# 查看 HTML 版本
git checkout html-version

# 查看 React 版本
git checkout react-version

# 回到文档主分支
git checkout main
```

## 各版本使用方式

### HTML 版本
直接用浏览器打开 pages/login.html 即可运行

### React 版本
```bash
cd react-ebook
npm install
npm run dev
```

