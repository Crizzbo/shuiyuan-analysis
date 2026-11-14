# 水源分析终端前端工程 (WaterSource Terminal Frontend)

本项目为水源分析终端的 React + TypeScript + Vite 前端客户端工程。

## 技术栈与设计规范

- React 19 + TypeScript 5
- Vite 构建与开发热重载服务器
- Tailwind CSS 与浅色工作台
- 原生 EventSource (SSE) 实时推流通信
- 使用 Python REST 接口与 `/api/stream`

## 构建与运行命令

1. 安装依赖：`npm install`
2. 开发运行：`npm run dev`（内置代理将 `/api` 转至本地 `127.0.0.1:8765`）
3. 生产打包：`npm run build`（打包产物自动输出至 `web/dist`，由 Python 网关托管）

从项目根目录运行 `python scripts/build_web.py` 和 `python scripts/serve_watersource_terminal.py`，打开 `http://127.0.0.1:8765`。定时任务在服务进程运行期间生效，使用 `--manual-only` 可只保留手动触发。

原工作区继续提供市场总览、雷达、采集概览、个股分析、日志及设置。金融计算器位于「计算分析」，定时任务和日线归档位于「采集中心」，官方 RSS 归档位于「事件情报」。计算器调用项目登记的金融计算服务，以输入假设计算并返回结果底稿。
