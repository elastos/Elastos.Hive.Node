from . import view, view_db, view_file


def init_app(app):
    view.init_app(app)
    view_db.init_app(app)
    view_file.init_app(app)
