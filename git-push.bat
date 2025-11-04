@echo off
chcp 65001 >nul
echo ==========================================
echo    Git 快速推送脚本
echo ==========================================
echo.

REM 提示用户输入提交信息
set /p commit_msg=请输入本次修改内容描述: 

REM 检查是否输入了提交信息
if "%commit_msg%"=="" (
    echo [错误] 提交信息不能为空！
    pause
    exit /b 1
)

echo.
echo ==========================================
echo 开始执行推送操作...
echo ==========================================
echo.

REM 添加所有修改
echo [1/3] 添加文件到暂存区...
git add .
if errorlevel 1 (
    echo [错误] git add 失败！
    pause
    exit /b 1
)
echo [完成] 文件已添加
echo.

REM 提交修改
echo [2/3] 提交修改...
git commit -m "%commit_msg%"
if errorlevel 1 (
    echo [错误] git commit 失败！可能没有新的修改内容
    pause
    exit /b 1
)
echo [完成] 修改已提交
echo.

REM 推送到远程仓库
echo [3/3] 推送到远程仓库...
git push
if errorlevel 1 (
    echo [错误] git push 失败！请检查网络连接和权限
    pause
    exit /b 1
)
echo [完成] 推送成功！
echo.

echo ==========================================
echo    所有操作完成！
echo ==========================================
pause

