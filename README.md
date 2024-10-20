- [Overview](#overview)
- [Install and Dependencies](#install-and-dependencies)
    - [#1: Operation System : Windows 11](#1-operation-system--windows-11)
    - [#2: Clone this repo](#2-clone-this-repo)
    - [#3: Python Version : 3.10](#3-python-version--310)
    - [#4: Install Dependencies](#4-install-dependencies)
    - [#5: Setup database](#5-setup-database)
  - [#1. Starting the App](#1-starting-the-app)
  - [#2. Logging In](#2-logging-in)
      - [Open the link presented in flask console to login to the application](#open-the-link-presented-in-flask-console-to-login-to-the-application)
      - [Default Logins](#default-logins)
      - [Default Password](#default-password)

# Overview
Welcom to SIFT. 
A Web Application designed using Python and Flask libraries. 

# Install and Dependencies


### #1: Operation System : Windows 11

### #2: Clone this repo

### #3: Python Version : 3.10
```
python --version
Python 3.10.14
```
Suggestion : To avoid conflict with other python versions and packages, it is recommended to use anaconda environment manager.

If the user is using anacoda, then this one line command can be run on the conda termnial and from inside the project folder.

- This will create a new python 3.10 environment named "sift"
- Then activate that environemnt
- Then install all the application dependencies in the requirements.txt
```
conda create --name sift python=3.10 -y && conda activate sift && pip install -r requirements.txt
```


### #4: Install Dependencies 
Dependencies can be instaled with the following command.

Install Steps : 

```
pip install -r requirements.txt
```

Please refer to requirement.txt for complete list.

| Package Name  |Usage   |
|---|---|
|Flask   |  Core web package |
|Flask_Admin |To provide CURDL views for the main SQLite tables. |
|Flask-Security-Too |To allow for Role based access for admins, teachers and students |
|flask_sqlalchemy |ORM layer for SQL Lite |
|matplotlib |To enable charting capabilities |
|numpy | Date manipulation for charts|
|SQLAlchemy |SQL Lite Database access for Flask |
|WTForms_SQLAlchemy |Enahnced handling of model views  |
|argon2_cffi |Password Hashing algorithim |
|Pillow |To show Cursive School Logo |
|Requests |To dowload webfont from Google |


### #5: Setup database

Run the **setup_sift.py** file at the root to setup database.

```
python setup_sift.py
Database initialization started...
Database Initialized, Please launch sift App by launching sift_app.py
```

Confirm that sift.db SQLite databse file is auto-created

We are now ready to run the app.


## #1. Starting the App
Start the app by issuing the following command : **python sift_app.py**

The terminal will show an output similar to the following.
```
python sift_app.py
2024-10-20 11:57:43,514 - sift_utils - INFO - Entering: create_app
2024-10-20 11:57:43,708 - sift_utils - INFO - Exiting: create_app
 * Serving Flask app 'sift_app'
 * Debug mode: on
2024-10-20 11:57:43,816 - werkzeug - INFO - WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
2024-10-20 11:57:43,816 - werkzeug - INFO - Press CTRL+C to quit
Exiting: create_app
```

## #2. Logging In 

#### Open the link presented in flask console to login to the application
Example : http://127.0.0.1:5000

#### Default Logins
| User  |Role   
|---|---|
|admin@test.com|admin|
|teacher@test.com|teacher|
|adam@test.com|student|
|braden@test.com|student|

#### Default Password

Default password for all accounts is : **123**