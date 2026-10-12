# -*- coding: utf-8 -*-
"""统一日志配置：模块级 logger，控制台输出，带时间戳和模块名。

用法：
    from api.log import get_logger
    logger = get_logger(__name__)
    logger.warning("语义路失败，降级关键词路: %s", e)
"""
import logging
import sys

_CONFIGURED = False


def _configure():
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )
    _CONFIGURED = True


def get_logger(name):
    """获取模块级 logger，自动完成全局配置。"""
    _configure()
    return logging.getLogger(name)
