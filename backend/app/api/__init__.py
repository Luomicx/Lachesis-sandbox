"""
api/ 目录：Flask Blueprint 层。
本文件定义职业 career 蓝图，承载路由注册的入口。
"""
from flask import Blueprint

career_bp = Blueprint("career", __name__)

from . import career  # noqa: E402,F401
