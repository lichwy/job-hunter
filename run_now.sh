#!/bin/bash
# 立即执行一次职位抓取（忽略去重，强制发送所有当前职位）
cd "$(dirname "$0")"
/opt/homebrew/bin/python3 job_hunter.py "$@"
