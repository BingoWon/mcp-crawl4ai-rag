"""
Global Logger Configuration
全局日志配置

Provides unified logging configuration for the entire project.
为整个项目提供统一的日志配置。
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class LoggerConfig:
    """全局日志配置类"""
    
    # 日志格式
    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # 日志级别
    DEFAULT_LEVEL = logging.INFO
    
    # 日志文件配置
    LOG_DIR = Path("logs")
    MAX_BYTES = 10 * 1024 * 1024  # 10MB
    BACKUP_COUNT = 5
    
    @classmethod
    def ensure_log_dir(cls):
        """确保日志目录存在"""
        cls.LOG_DIR.mkdir(exist_ok=True)


def setup_logger(name: str, level: Optional[str] = None, file_logging: bool = True) -> logging.Logger:
    """
    设置并返回logger实例
    
    Args:
        name: logger名称，通常使用__name__
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        file_logging: 是否启用文件日志
        
    Returns:
        配置好的logger实例
    """
    logger = logging.getLogger(name)
    
    # 避免重复配置
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = getattr(logging, level.upper()) if level else LoggerConfig.DEFAULT_LEVEL
    logger.setLevel(log_level)
    
    # 创建格式化器
    formatter = logging.Formatter(
        fmt=LoggerConfig.FORMAT,
        datefmt=LoggerConfig.DATE_FORMAT
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（使用轮转日志）
    if file_logging:
        LoggerConfig.ensure_log_dir()

        # 按模块名创建日志文件
        module_name = name.split('.')[-1] if '.' in name else name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = LoggerConfig.LOG_DIR / f"{module_name}_{timestamp}.log"

        # 使用RotatingFileHandler进行日志轮转
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=LoggerConfig.MAX_BYTES,
            backupCount=LoggerConfig.BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取已配置的logger实例
    
    Args:
        name: logger名称
        
    Returns:
        logger实例
    """
    return logging.getLogger(name)


# 为向后兼容提供的便捷函数
def create_logger(name: str, level: str = "INFO") -> logging.Logger:
    """创建logger的便捷函数"""
    return setup_logger(name, level)
