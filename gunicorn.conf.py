import multiprocessing
import os

# Azure App Service では PORT 環境変数が動的に設定される
port = os.environ.get('PORT', '8000')
bind = f"0.0.0.0:{port}"

max_requests = 1000
max_requests_jitter = 50
log_file = "-"

timeout = 230
# https://learn.microsoft.com/en-us/troubleshoot/azure/app-service/web-apps-performance-faqs#why-does-my-request-time-out-after-230-seconds

num_cpus = multiprocessing.cpu_count()
workers = (num_cpus * 2) + 1
worker_class = "uvicorn.workers.UvicornWorker"

# 追加の最適化設定
keepalive = 5
accesslog = '-'
errorlog = '-'
loglevel = 'info'
proc_name = 'app-backend-gunicorn'
preload_app = True
