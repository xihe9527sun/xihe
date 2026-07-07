@echo off
REM 曦和·Deep Code 启动器
REM 同时启动进化管道和Deep Code CLI

title 曦和 · Deep Code 桌面版

cd /d F:\SmartLegend\Xihe\deepcode-clone\packages\cli

REM 设置环境
set DEEPSEEK_API_KEY=%DEEPSEEK_API_KEY%

REM 启动home-server（提供面板数据）
start /B "" "C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe" -X utf8 F:\SmartLegend\Xihe\bin\home-server.py

REM 启动代谢心跳
start /B "" "C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe" -X utf8 F:\SmartLegend\Xihe\bridge\metabolic_actor.py

echo.
echo ╔══════════════════════════════════════════╗
echo ║    曦和 · Deep Code 桌面版已启动       ║
echo ║    模型: DeepSeek-V4 Flash              ║
echo ║    面板: home.xihe-pg.xyz/xihe-desktop  ║
echo ║    载体: Deep Code CLI v0.1.33          ║
echo ╚══════════════════════════════════════════╝
echo.

REM 启动Deep Code
node dist/cli.js

REM 退出时清理
taskkill /F /IM python.exe >nul 2>&1
