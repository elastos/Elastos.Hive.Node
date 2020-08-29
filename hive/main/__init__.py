from . import view, view_db, view_file, view_scripting


def init_app(app):
    view.init_app(app)
    view_db.init_app(app)
    view_file.init_app(app)
    view_scripting.init_app(app)
