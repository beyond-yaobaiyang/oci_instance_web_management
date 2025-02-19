import logging
from app import create_app

# 配置基本日志

logger = logging.getLogger(__name__)

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
