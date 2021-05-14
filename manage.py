from flask_script import Manager, Server

from src import create_app

manager = Manager(create_app)
manager.add_command("runserver", Server(host="0.0.0.0", port=5000))
manager.add_option('-c', '--config', dest='mode', required=False)

if __name__ == "__main__":
    # manager.run(debug=False)
    manager.run()
