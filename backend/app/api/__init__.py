from flask import Blueprint

career_bp = Blueprint("career", __name__)

from . import career  # noqa: E402,F401
