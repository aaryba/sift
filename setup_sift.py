from functools import wraps
import os
from flask import Flask
from flask_security import Security, SQLAlchemyUserDatastore
from flask_security.utils import hash_password, verify_password
# Import my DBModels
from sift_models import User, Role, VoteCategory, Config, db
import tempfile
import shutil

import logging
# logging.basicConfig()
logging.basicConfig(level=logging.WARN,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set the logging level for sqlalchemy
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)
# Set the logging level for Werkzeug
logging.getLogger('werkzeug').setLevel(logging.WARNING)


def log_function_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Entering: {func.__name__}")
        result = func(*args, **kwargs)
        logger.info(f"Exiting: {func.__name__}")
        return result
    return wrapper


# Default Constants
if os.getenv('PYTHONANYWHERE_SITE'):
    # need complex password to deploy to internet
    DEFAULT_ADMIN_PASS = '67d694dd-4093-49fb-a115-4c001865b740'
else:
    DEFAULT_ADMIN_PASS = '123'

SQLALCHEMY_ECHO = False
DASH_ROOT_URL = '/dashboard'
######


@log_function_call
def create_app():
    SALT = 'my_precious_two'

    app = Flask(__name__)

    db_path = os.path.join(os.path.dirname(__file__), 'sift.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    # to see all SQL Queries crated by SQLAlchemy
    app.config['SQLALCHEMY_ECHO'] = SQLALCHEMY_ECHO
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['SECRET_KEY'] = 'you-will-never-guess'
    app.config['SECURITY_PASSWORD_SALT'] = SALT
    # app.config['SECURITY_PASSWORD_HASH']  = 'bcrypt' #removed as library has issues with python 3.10
    app.config['SECURITY_PASSWORD_HASH'] = 'argon2'
    app.config['SECURITY_REGISTERABLE'] = True
    # flask-sec can auto redirec user to this page on login
    app.config['SECURITY_POST_LOGIN_VIEW'] = 'dashboard'
    app.config['SECURITY_POST_LOGOUT_VIEW'] = 'dashboard'

    # for development
    app.config['SECURITY_SEND_REGISTER_EMAIL'] = False
    app.config['SECURITY_CHANGEABLE'] = True
    app.config['SECURITY_SEND_PASSWORD_CHANGE_EMAIL'] = False
    app.config['SECURITY_PASSWORD_COMPLEXITY_CHECKER'] = None
    app.config['SECURITY_PASSWORD_LENGTH_MIN'] = 1
    app.config['SECURITY_PASSWORD_CHECK_BREACHED'] = False

    # Initialize SQLAlchemy with the app
    db.init_app(app)

    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security = Security(app, user_datastore)
    return app, user_datastore


@log_function_call
def init_db_and_first_user(user_datastore):


    # will throw an exception if it already exists, which is fine
    db.create_all()

    admin_role = user_datastore.find_or_create_role('admin')
    teacher_role = user_datastore.find_or_create_role('teacher')
    student_role = user_datastore.find_or_create_role('student')

    # password is automatically hashed
    user_datastore.create_user(
        email='admin@test.com', password=DEFAULT_ADMIN_PASS, roles=['admin'])
    user_datastore.create_user(
        email='teacher@test.com', password=DEFAULT_ADMIN_PASS, roles=['teacher'])
    user_datastore.create_user(
        email=f'adam@test.com', password=DEFAULT_ADMIN_PASS, roles=['student'])
    user_datastore.create_user(
        email=f'braden@test.com', password=DEFAULT_ADMIN_PASS, roles=['student'])
    user_datastore.create_user(
        email=f'charlie@test.com', password=DEFAULT_ADMIN_PASS, roles=['student'])
    user_datastore.create_user(
        email=f'daniel@test.com', password=DEFAULT_ADMIN_PASS, roles=['student'])
    user_datastore.create_user(
        email=f'ethon@test.com', password=DEFAULT_ADMIN_PASS, roles=['student'])
    user_datastore.create_user(
        email=f'fredrick@test.com', password=DEFAULT_ADMIN_PASS, roles=['student'])
    user_datastore.create_user(
        email=f'greg@test.com', password=DEFAULT_ADMIN_PASS, roles=['student'])

    # for i in range(10):
    #     user_datastore.create_user(
    #         email=f'student_{i}@test.com', password=hashed_password, roles=['student'])

    vote_category_1 = VoteCategory(
        name='Positive', description='Positive Vote')
    vote_category_2 = VoteCategory(
        name='Negative', description='Negative Vote')
    vote_category_3 = VoteCategory(
        name='Need Support', description='Need Support')

    # Add Three types of Vote Categories to the App
    db.session.add(vote_category_1)
    db.session.add(vote_category_2)
    db.session.add(vote_category_3)

    cfg = Config(points_awarded_for_vote=1)
    db.session.add(cfg)

    db.session.commit()

    # if deploying to pythonanywhere, the temp directory needs to be deleted
    # not needed when running locally
    if os.getenv('PYTHONANYWHERE_SITE'):

        # # Get the temporary directory path
        temp_dir = tempfile.gettempdir()

        # Clear all temp files and folders
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                    logger.info(f'Deleted temp file {file_path}')
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    logger.info(f'Deleted temp folder {file_path}')
            except Exception as e:
                logger.error(f'Error deleting {file_path}: {e}')


# if __name__ == '__main__':
app, user_datastore = create_app()

with app.app_context():
    try:
        print('Database initialization started...')
        init_db_and_first_user(user_datastore)
        print('Database Initialized, Please launch sift App by launching sift_app.py')
    except Exception as e:
        print(f"Sorry, Setup Failed : Please make sure sift.db is deleted and try again.")
        # print(e)
