# gunicorn.conf.py

# Network
bind = "0.0.0.0:8000"   # nginx will reverse-proxy to this
proxy_protocol = False
forwarded_allow_ips = "*"

# Workers (start simple; tune later)
# rule of thumb: workers = 2 * CPU cores
workers = 3
threads = 2
worker_class = "gthread"
timeout = 60
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"          # stdout (docker-friendly)
errorlog  = "-"          # stderr
loglevel  = "info"

# App
wsgi_app = "rum_marketplace_project.wsgi:application"
