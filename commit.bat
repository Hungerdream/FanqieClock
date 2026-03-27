@echo off
chcp 65001 >nul
cd /d e:\编程语言\trae
git add conftest.py
git commit -m "fix(test): mock QuoteWorker in conftest to prevent network hang on Linux CI"
git push
