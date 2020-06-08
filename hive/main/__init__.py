from . import view, scheduler


def init_app(app):
    view.init_app(app)
    scheduler.init_app(app)
