from flask import Blueprint

from hive.main.hive_scripting import HiveScripting

h_scripting = HiveScripting()


hive_scripting = Blueprint('hive_scripting', __name__)


def init_app(app):
    h_scripting.init_app(app)
    app.register_blueprint(hive_scripting)


@hive_scripting.route('/api/v1/scripting/set_script', methods=['POST'])
def set_script():
    return h_scripting.set_script()


@hive_scripting.route('/api/v1/scripting/run_script', methods=['POST'])
def run_script():
    return h_scripting.run_script()
