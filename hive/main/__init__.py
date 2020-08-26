from . import view, view_db


def init_app(app):
    view.init_app(app)
    view_db.init_app(app)
