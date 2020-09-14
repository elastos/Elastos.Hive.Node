from . import view, view_db, view_file, view_scripting, interceptor


def init_app(app):
    view.init_app(app)
    view_db.init_app(app)
    view_file.init_app(app)
    view_scripting.init_app(app)
    interceptor.init_app(app)
