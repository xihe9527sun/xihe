@echo off
REM 曦和四站启动脚本 — 开机或断线后运行
TITLE 曦和四站启动

echo.
echo ====================================
echo   曦和四站 · Cloudflare隧道 + 后端
echo ====================================
echo.

REM Step 1: Start Cloudflare tunnel
echo [1/2] 启动Cloudflare隧道...
START /B "" "C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2\cloudflared.exe" tunnel --config "C:\Users\Administrator\.cloudflared\config.yml" run > "C:\Users\Administrator\.cloudflared\tunnel.log" 2>&1
if %ERRORLEVEL% EQU 0 (echo   ✅ 隧道已启动) else (echo   ❌ 隧道启动失败)
echo.

REM Step 2: Start all 4 backend servers
echo [2/2] 启动后端服务...
set NODE="C:\Users\Administrator\.workbuddy\binaries\node\versions\22.12.0\node.exe"
set DASH=F:\SmartLegend\Xihe\XiheDashboard

START /B "" %NODE% %DASH%\main-site.js      > %DASH%\logs\main-site.log  2>&1
echo   ✅ xihe-pg.xyz → 4326

START /B "" %NODE% %DASH%\home-site.js      > %DASH%\logs\home-site.log  2>&1
echo   ✅ home.xihe-pg.xyz → 4324

START /B "" %NODE% %DASH%\aibounty-site.js   > %DASH%\logs\aibounty.log   2>&1
echo   ✅ www.aibounty.cn → 4321

START /B "" %NODE% %DASH%\node-site.js       > %DASH%\logs\node-site.log  2>&1
echo   ✅ node.xihe-pg.xyz → 4325

START /B "" %NODE% %DASH%\server.js          > %DASH%\logs\dashboard.log  2>&1
echo   ✅ 本地仪表盘 → 4328

echo.
echo ====================================
echo   全部启动完成
echo   🌐 xihe-pg.xyz        → seed-journey
echo   🌐 home.xihe-pg.xyz   → 实时XCRN
echo   🌐 www.aibounty.cn    → 工具导航
echo   🌐 node.xihe-pg.xyz   → 通信节点
echo   🌐 localhost:4328     → 完整仪表盘
echo ====================================
