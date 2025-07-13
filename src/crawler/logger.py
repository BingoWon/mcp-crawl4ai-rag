"""精简的爬虫日志配置"""

import logging
import os
from datetime import datetime

# 创建logs目录
logs_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
os.makedirs(logs_dir, exist_ok=True)

# 生成日志文件名
log_filename = f"crawler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_filepath = os.path.join(logs_dir, log_filename)

# 配置基础日志 - 同时输出到控制台和文件
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.StreamHandler(),  # 控制台输出
        logging.FileHandler(log_filepath, encoding='utf-8')  # 文件输出
    ]
)

# 创建爬虫专用logger
logger = logging.getLogger('crawler')
