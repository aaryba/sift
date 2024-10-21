from PIL import Image, ImageDraw, ImageFont
from flask import send_file
import requests
import tempfile
from datetime import timedelta
from sqlalchemy import desc, asc  # for ordering in chart
from matplotlib.dates import date2num
from sift_models import User, Role, VoteSummary, Vote, VoteSummaryHistory, Points, Config, ContactRequest, AllowedStudentsAndStaff, roles_users, db
from sift_config import *
from sift_utils import *
from sift_model_views import register_admin_views
import datetime as dtm
import io
import os
import uuid
from flask import Flask, render_template, request, session, redirect, jsonify, url_for, Response, flash, send_from_directory
from flask_security import Security, SQLAlchemyUserDatastore, current_user, login_required, roles_required, roles_accepted, user_registered
from flask_admin import Admin, AdminIndexView, expose, BaseView
from flask_admin import helpers as admin_helpers  # needed for better login pages
from io import StringIO  # for uploading csv
import csv  # for parsing csv
import numpy as np


# imports needed for charting
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import matplotlib.ticker as mticker
# Use the 'Agg' backend for non-GUI rendering, fixes matplotlib warning related to threads
matplotlib.use('Agg')
# for date plotting on history chart on x axis


# This function does : "Overrides the default Flask Admin behavior"
class MyAdminIndexView(AdminIndexView):
    """
    Customized AdminIndexView for Flask Admin.

    Attributes:
    - index: Renders custom_base.html as the index page.
    - is_visible: Returns False to hide the default home link.
    """
    @expose('/')
    def index(self):
        return self.render('custom_base.html')

    def is_visible(self):
        return False

    @expose('/')
    def index(self):
        return self.render('custom_base.html')
    # set default Home Flask Admin to false to hide the default home link

    def is_visible(self):
        return False  # Hide default home link


@log_function_call
def create_app():
    """
    Create and configure the Flask application along with the user datastore.

    Returns:
        tuple: A tuple containing the Flask application and the user datastore.
    """
    SALT = 'my_precious_two'
    app = Flask(__name__)

    import os
    # db_path = os.path.join(os.path.dirname(__file__),'instance', 'sift.db')
    db_path = os.path.join(os.path.dirname(__file__), 'sift.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

    # to see all SQL Queries created by SQLAlchemy
    app.config['SQLALCHEMY_ECHO'] = SQLALCHEMY_ECHO
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flash-sift.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['SECRET_KEY'] = 'you-will-never-guess'
    app.config['SECURITY_PASSWORD_SALT'] = SALT
    # app.config['SECURITY_PASSWORD_HASH']  = 'bcrypt'
    app.config['SECURITY_PASSWORD_HASH'] = 'argon2'

    app.config['SECURITY_REGISTERABLE'] = True
    # flask-sec can auto redirect user to this page on login
    app.config['SECURITY_POST_LOGIN_VIEW'] = 'dashboard'
    app.config['SECURITY_POST_LOGOUT_VIEW'] = 'dashboard'
    # app.config['SECURITY_POST_REGISTER_VIEW'] = 'welcome'
    # app.config['SECURITY_RECOVERABLE'] = False

    # Setup relaxed security rules for demo
    app.config['SECURITY_SEND_REGISTER_EMAIL'] = False
    app.config['SECURITY_CHANGEABLE'] = True
    app.config['SECURITY_SEND_PASSWORD_CHANGE_EMAIL'] = False
    app.config['SECURITY_PASSWORD_COMPLEXITY_CHECKER'] = None
    app.config['SECURITY_PASSWORD_LENGTH_MIN'] = 1
    app.config['SECURITY_PASSWORD_CHECK_BREACHED'] = False

    # Specify the templates folder or specific HTML files to watch
    # Automatically reload templates
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    # Initialize SQLAlchemy with the app
    db.init_app(app)

    admin = Admin(app, name='SIFT', index_view=MyAdminIndexView(
        url=DASH_ROOT_URL), template_mode='bootstrap4')

    # Register admin views
    register_admin_views(admin)

    # set up Flask-Security Userdatastore
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security = Security(app, user_datastore)

    @security.context_processor
    def security_context_processor():
        return dict(
            admin_base_template=admin.base_template,
            admin_view=admin.index_view,
            h=admin_helpers,
            get_url=url_for
        )

    @app.context_processor
    def inject_theme():
        theme = {
            'swatch': 'default',  # Define your theme swatch here
            'fluid': True  # to make it full screen
        }
        return dict(theme=theme)
    # This will allow us to use datetime.now() in all templates via datetime.datetime.now() to get the current date and time.
    # I need this to ensure that my JS scripts always reload

    @app.context_processor
    def inject_datetime():
        # import datetime
        return dict(datetime=dtm)

    @app.context_processor
    def inject_config():
        # import datetime
        return dict(conf=Config.query.first())


# config_instance = Config.query.first()


    @app.context_processor
    def inject_points():
        # return
        local_awarded_points = 0
        # old_points = Points.query.filter_by(awarded_to_id = vote.voter_id).first()
        if current_user.is_authenticated:
            db_points_obj = Points.query.filter_by(
                awarded_to_id=current_user.id).first()
            if db_points_obj:
                logger.info(
                    f"DB Points: {db_points_obj}, {db_points_obj.awarded_points}")
                local_awarded_points = db_points_obj.awarded_points
        logger.info(f"Points: {local_awarded_points}")
        return dict(awarded_points=local_awarded_points)

    @ app.route('/')
    def index():
        try:
            return redirect(DASH_ROOT_URL)
            # return f'You r at home, User {current_user.email} <form action="/logout" method="GET"><input type="submit" value="Logout"></form></br><form action="{ DASH_ROOT_URL }" method="GET"><input type="submit" value="Go Admin"></form>'
        except Exception as e:
            logger.info(f"An error occurred: {e}")

            return f'You r at home as anonymous user<form action="/login" method="GET"><input type="submit" value="Login"></form></br><form action="{ DASH_ROOT_URL }" method="GET"><input type="submit" value="Go Admin"></form>'
            # sys.ext()
        # else:
        #     return f'You r at home as anyms user'

    # During registration, check if pre-approved users - with email - are allowed to register

    @ log_function_call
    @ app.before_request
    def before_request():
        if request.endpoint == 'security.register' and request.method == 'POST':
            email = request.form.get('email')

            found_user = AllowedStudentsAndStaff.query.filter_by(
                email=email).first()

            if found_user:
                logger.info(f'User with email {email} allowed to register')
            else:
                logger.info(f'User with email {email} not allowed to register')
                flash(
                    'Your email is not allowed to register. Please use your school email to register.', 'error')
                return redirect(url_for('security.register'))

    # after user is registered, lets assign them a role per the uploaded csv file
    @ log_function_call
    @ user_registered.connect_via(app)
    def user_registered_sighandler(app, user, **extra):

        found_user = AllowedStudentsAndStaff.query.filter_by(
            email=user.email).first()
        logger.info(
            f'Found user (user_registered_sighandler): {found_user}, will assign role: {found_user.role}')
        default_role = user_datastore.find_or_create_role(
            found_user.role)  # Or your desired role
        user_datastore.add_role_to_user(user, default_role)
        db.session.commit()

    @ app.route('/search')
    @ roles_accepted('admin', 'teacher', 'student')
    def search():
        search_query = request.args.get('query', '')


        # do a join to get users that have role students
        users = (
            User.query
            .join(roles_users, User.id == roles_users.c.user_id)
            .join(Role, roles_users.c.role_id == Role.id)
            .filter(User.email.contains(search_query))
            .filter(Role.name == 'student')
            .all()
        )

        return jsonify([{'id': user.id, 'email': user.email} for user in users])

    @ log_function_call
    @ app.route('/upload_students_and_staff', methods=['POST'])
    @ roles_accepted('admin')
    def upload_students_and_staff():
        file = request.files.get('file')
        if not file:
            return jsonify({'status': 'error', 'message': 'You need to Select a file before clicking upload'})

        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'You need to Select a file before clicking upload'})

        try:
            stream = StringIO(file.stream.read().decode('UTF8'), newline=None)
            csv_input = csv.reader(stream)
            # Delete all rows
            db.session.query(AllowedStudentsAndStaff).delete()
            logger.info(
                f'Doing soft delete of allowed students and staff before importing new data')

            for row in csv_input:
                logger.info(f'row[0]: "{row[0]}" - row[1]: "{row[1]}"')
                found_role = Role.query.filter_by(name=row[1]).first()

                if found_role:
                    logger.info(f'Role ID: {found_role.id}')

                    # logger.info(f'row[0]: "{row[0]}" - found_role: "{found_role }"')
                    logger.info(
                        f'row[0]: "{row[0]}" - found_role: {found_role } - found_role.id: {found_role.id }')

                    new_row = AllowedStudentsAndStaff(
                        email=row[0],
                        role=row[1],
                        role_id=found_role.id
                    )
                    db.session.add(new_row)

                else:
                    logger.info(f'Role not found : {row[1]}, skipping row')

            # return "Successfully uploaded Students and Staff Allowed List!"
            db.session.commit()

            return jsonify({'status': 'success', 'message': 'File uploaded successfully!'})

        except:
            return jsonify({'status': 'error', 'message': 'Uploaded File is not a CSV or its corrupt!'})

    @ log_function_call
    @ app.route('/student_history_combined.png')
    @ roles_accepted('admin', 'teacher')
    def student_history_combined():

        student_id_to_lookup = int(request.args.get(
            'student_id', default="1"))  # integer
        vote_type_pos_or_neg = request.args.get(
            'vote_type_pos_or_neg', default="pos")

        logger.info(f"student_id_to_lookup: {student_id_to_lookup}")
        logger.info(f"vote_type_pos_or_neg: {vote_type_pos_or_neg}")

        # real data
        dates = []
        scores_pos = []
        scores_neg = []
        scores_ns = []
        scores_sibs = []

        summaries = (
            VoteSummaryHistory.query
            # Filter by specific voted_for_id
            .filter_by(voted_for_id=student_id_to_lookup)
            .limit(36)
            .all()
        )

        if len(summaries) > 0:
            # create the X,Y data needed for the plot
            logger.info(
                f"Summaries Results Length from DB: {len(summaries)} for student email: {summaries[0].voted_for.email}")
        else:
            logger.warning(
                f"No summaries found for student email: {student_id_to_lookup}")

        for summary in summaries:
            # dates.append(summary.voted_for_snap_date)
            dates.append(
                summary.voted_for_snap_date.strftime("%Y-%m-%d %H:%M"))

            # all scores for the three category
            scores_pos.append(summary.vote_positive_count)
            scores_neg.append(summary.vote_negative_count)
            scores_ns.append(summary.vote_needs_support_count)
            scores_sibs.append(summary.vote_pos_negative_sum)

        # Create a figure and axis object
        fig, ax = plt.subplots()

        if len(summaries) > 0:

            # Marker styles
            # https://matplotlib.org/stable/api/markers_api.html#module-matplotlib.markers
            # https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.plot.html#matplotlib.axes.Axes.plot

            # Plot SIBS scores in Purple
            ax.plot(dates, scores_sibs, label='SIBS',
                    marker=',',  color='purple', lw=3)

            # Plot Needs Support scores in Blue
            ax.plot(dates, scores_ns, label='Needs Support',
                    marker='.',  color='blue')

            # Plot positive scores in green
            ax.plot(dates, scores_pos, label='Positive Scores',
                    linestyle=':', color='green', lw=1)

            # Plot negative scores in red
            ax.plot(dates, scores_neg, label='Negative Scores',
                    linestyle=':', color='red', lw=1)

            # Customize the plot with labels, title, and legend
            ax.set_xlabel('Date')
            ax.set_ylabel('Score')
            ax.set_title(f'{summaries[0].voted_for.email} : Scores Over Time')

            # Format x-axis for dates
            # Rotate dates on x-axis for better readability
            fig.autofmt_xdate(rotation=45)

            # Add a legend
            ax.legend()

            # Add grid for better visualization
            ax.grid(True)

            # Adjust layout for better spacing
            fig.tight_layout()

        # Save it to a temporary buffer.
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        # matplotlib.pyplot.close()
        buf.seek(0)
        plt.close(fig)
        return Response(buf.getvalue(), mimetype='image/png')
        # return send_file(buf, mimetype='image/png')

    @ log_function_call
    @ app.route('/student_history.png')
    @ roles_accepted('admin', 'teacher')
    def student_history():

        student_id_to_lookup = int(request.args.get(
            'student_id', default="1"))  # integer
        vote_type_pos_or_neg = request.args.get(
            'vote_type_pos_or_neg', default="pos")

        logger.info(f"student_id_to_lookup: {student_id_to_lookup}")
        logger.info(f"vote_type_pos_or_neg: {vote_type_pos_or_neg}")

        # real data
        dates = []
        scores = []

        summaries = (
            VoteSummaryHistory.query
            # Filter by specific voted_for_id
            .filter_by(voted_for_id=student_id_to_lookup)
            .limit(36)
            .all()
        )

        if len(summaries) > 0:
            # create the X,Y data needed for the plot
            logger.info(
                f"Summaries Results Length from DB: {len(summaries)} for student email: {summaries[0].voted_for.email}")
        else:
            logger.warning(
                f"No summaries found for student email: {student_id_to_lookup}")

        for summary in summaries:
            logger.info(summary)
            dates.append(
                (summary.voted_for_snap_date).strftime("%Y-%m-%d %H:%M"))
            if vote_type_pos_or_neg == 'pos':
                scores.append(summary.vote_positive_count)
            elif vote_type_pos_or_neg == 'neg':
                scores.append(summary.vote_negative_count)
            elif vote_type_pos_or_neg == 'ns':
                scores.append(summary.vote_needs_support_count)

        logger.info(f" {vote_type_pos_or_neg} : {scores}")
        # Create a figure and axis object
        # fig, ax = plt.subplots(figsize=(10, 6))
        fig, ax = plt.subplots()

        if len(summaries) > 0:

            # Convert dates to numerical format for plotting
            dates_num = date2num(dates)

            # Scatter plot of the original data
            ax.scatter(dates, scores, color='blue', label='Scores')

            # Calculate the trendline (polynomial fitting of degree 1, i.e., linear trend)
            z = np.polyfit(dates_num, scores, 1)
            p = np.poly1d(z)

            # Plot the trendline on the same axis
            if vote_type_pos_or_neg == 'pos':
                ax.plot(dates, p(dates_num), color='green',
                        linestyle='--', label='Trendline')
            elif vote_type_pos_or_neg == 'neg':
                ax.plot(dates, p(dates_num), color='red',
                        linestyle='--', label='Trendline')
            elif vote_type_pos_or_neg == 'ns':
                ax.plot(dates, p(dates_num), color='blue',
                        linestyle='--', label='Trendline')

            # Customize the plot with labels, title, and legend
            ax.set_xlabel('Date')
            ax.set_ylabel('Score')
            ax.set_title(f'{summaries[0].voted_for.email} : Scores Over Time')

            # Format x-axis for dates
            # Rotate dates on x-axis for better readability
            fig.autofmt_xdate(rotation=45)

            # Add a legend
            ax.legend()

            # Add grid for better visualization
            ax.grid(True)

            # Adjust layout for better spacing
            fig.tight_layout()

        # Save it to a temporary buffer.
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        # matplotlib.pyplot.close()
        buf.seek(0)
        plt.close(fig)
        return Response(buf.getvalue(), mimetype='image/png')
        # return send_file(buf, mimetype='image/png')

    @ log_function_call
    @ app.route('/school_history.png')
    @ roles_accepted('admin', 'teacher')
    def school_history():

        # student_id_to_lookup = int(request.args.get('student_id', default="1")) #integer
        vote_type_pos_or_neg = request.args.get(
            'vote_type_pos_or_neg', default="pos")

        # logger.info(f"student_id_to_lookup: {student_id_to_lookup}")
        logger.info(f"vote_type_pos_or_neg: {vote_type_pos_or_neg}")

        # real data
        dates = []
        scores = []

        is_positive = False

        if vote_type_pos_or_neg == 'pos':
            is_positive = True
        else:
            is_positive = False

        # Calculate the date 1 year ago from today
        one_year_ago = dtm.datetime.utcnow() - timedelta(days=365)

        # Query to find all unique snapshot_id values
        unique_snapshot_ids = db.session.query(
            VoteSummaryHistory.snapshot_id
        ).filter(
            # only look at data from last year
            VoteSummaryHistory.voted_for_snap_date >= one_year_ago
        ).distinct().all()

        logger.info("unique_snapshot_ids: " +
                    " -- ".join([str(item) for item in unique_snapshot_ids]))

        # Process the results
        dict_date_to_score = {}
        for snapshot_id in unique_snapshot_ids:
            logger.info(f"Processing snapshot_id: {snapshot_id[0]}")
            if (is_positive):
                # Query specific columns and filter by voted_for_snap_date
                list_of_vote_summaries_for_snapshot = db.session.query(
                    VoteSummaryHistory.snapshot_id,
                    VoteSummaryHistory.voted_for_snap_date,
                    VoteSummaryHistory.vote_positive_count
                ).filter(
                    # only look at data from last year
                    VoteSummaryHistory.snapshot_id == snapshot_id[0]
                ).all()

                logger.info(
                    f"list_of_vote_summaries_for_snapshot +v: {list_of_vote_summaries_for_snapshot}")

                # no need to loop, we take first record from the results as x axis
                x_date = list_of_vote_summaries_for_snapshot[0].voted_for_snap_date
                y_score = 0  # set to 0
                for summary in list_of_vote_summaries_for_snapshot:
                    logger.info(summary)
                    y_score += summary.vote_positive_count

                # for a unique snapshot id, we only have one date and one score ( we summed the score)
                # dates.append(x_date.strftime("%Y-%m-%d %H:%M" ))
                dates.append(x_date)

                scores.append(y_score)

            else:
                # Query specific columns and filter by voted_for_snap_date
                list_of_vote_summaries_for_snapshot = db.session.query(
                    VoteSummaryHistory.snapshot_id,
                    VoteSummaryHistory.voted_for_snap_date,
                    VoteSummaryHistory.vote_negative_count,
                ).filter(
                    # only look at data from last year
                    VoteSummaryHistory.snapshot_id == snapshot_id[0]
                ).all()

                if not list_of_vote_summaries_for_snapshot is None:
                    logger.info(
                        f"list_of_vote_summaries_for_snapshot -v: {list_of_vote_summaries_for_snapshot}")

                    # no need to loop, we take first record from the results as x axis
                    x_date = list_of_vote_summaries_for_snapshot[0].voted_for_snap_date
                    y_score = 0  # set to 0
                    for summary in list_of_vote_summaries_for_snapshot:
                        logger.info(summary)
                        y_score += summary.vote_negative_count

                    # for a unique snapshot id, we only have one date and one score ( we summed the score)
                    dates.append(x_date.strftime("%Y-%m-%d %H:%M"))
                    scores.append(y_score)

                else:
                    logger.info(
                        "list_of_vote_summaries_for_snapshot -v is None")

        logger.info(f"School  : Dates : {len(dates)} Scores : {len(scores)}")
        logger.info("Dates: " + " -- ".join([str(item) for item in dates]))
        logger.info("Scores: " + " -- ".join([str(item) for item in scores]))

        # Create a figure and axis object
        fig, ax = plt.subplots()

        if len(dates) > 0:

            # Convert dates to numerical format for plotting
            dates_num = date2num(dates)

            # Scatter plot of the original data
            ax.scatter(dates, scores, color='blue', label='Scores')

            # Calculate the trendline (polynomial fitting of degree 1, i.e., linear trend)
            z = np.polyfit(dates_num, scores, 1)
            p = np.poly1d(z)

            # Plot the trendline on the same axis
            ax.plot(dates, p(dates_num), color='red',
                    linestyle='--', label='Trendline')

            # Customize the plot with labels, title, and legend
            ax.set_xlabel('Date')
            ax.set_ylabel('Score')
            # ax.set_title(f'{summaries[0].voted_for.email} : Scores Over Time')
            ax.set_title(f'School Scores Over Time')

            # Format x-axis for dates
            # Rotate dates on x-axis for better readability
            fig.autofmt_xdate(rotation=45)

            # Add a legend
            ax.legend()

            # Add grid for better visualization
            ax.grid(True)

            # Adjust layout for better spacing
            fig.tight_layout()

        # Save it to a temporary buffer.
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        # matplotlib.pyplot.close()
        buf.seek(0)
        plt.close(fig)
        return Response(buf.getvalue(), mimetype='image/png')
        # return send_file(buf, mimetype='image/png')

    @ log_function_call
    @ app.route('/school_history_combined.png')
    @ roles_accepted('admin', 'teacher')
    def school_history_combined():

        # student_id_to_lookup = int(request.args.get('student_id', default="1")) #integer
        vote_type_pos_or_neg = request.args.get(
            'vote_type_pos_or_neg', default="pos")

        # logger.info(f"student_id_to_lookup: {student_id_to_lookup}")
        logger.info(f"vote_type_pos_or_neg: {vote_type_pos_or_neg}")

        # real data
        dates = []
        scores_pos = []
        scores_negv = []
        scores_need_support = []

        # Calculate the date 1 year ago from today
        one_year_ago = dtm.datetime.utcnow() - timedelta(days=365)

        # Query to find all unique snapshot_id values
        unique_snapshot_ids = db.session.query(
            VoteSummaryHistory.snapshot_id
        ).filter(
            # only look at data from last year
            VoteSummaryHistory.voted_for_snap_date >= one_year_ago
        ).distinct().all()

        logger.info("unique_snapshot_ids: " +
                    " -- ".join([str(item) for item in unique_snapshot_ids]))

        # Process the results
        dict_date_to_score = {}
        for snapshot_id in unique_snapshot_ids:
            logger.info(f"Processing snapshot_id: {snapshot_id[0]}")
            # if(is_positive) :
            # Query specific columns and filter by voted_for_snap_date
            list_of_vote_summaries_for_snapshot = db.session.query(
                VoteSummaryHistory.snapshot_id,
                VoteSummaryHistory.voted_for_snap_date,
                VoteSummaryHistory.vote_positive_count,
                VoteSummaryHistory.vote_negative_count,
                # VoteSummaryHistory.vote_pos_negative_sum,
                VoteSummaryHistory.vote_needs_support_count
            ).filter(
                # only look at data from last year
                VoteSummaryHistory.snapshot_id == snapshot_id[0]
            ).all()

            logger.info(
                f"list_of_vote_summaries_for_snapshot +v: {list_of_vote_summaries_for_snapshot}")

            # no need to loop, we take first record from the results as x axis
            x_date = list_of_vote_summaries_for_snapshot[0].voted_for_snap_date
            y_score_pos = 0  # set to 0
            y_score_neg = 0
            y_score_need_support = 0

            for summary in list_of_vote_summaries_for_snapshot:
                logger.info(summary)
                y_score_pos += summary.vote_positive_count
                y_score_neg += summary.vote_negative_count
                y_score_need_support += summary.vote_needs_support_count

            # for a unique snapshot id, we only have one date and one score ( we summed the score)
            dates.append(x_date.strftime("%Y-%m-%d %H:%M"))
            scores_pos.append(y_score_pos)
            scores_negv.append(y_score_neg)
            scores_need_support.append(y_score_need_support)

        logger.info(f"School Combo : Dates: " +
                    " -- ".join([str(item) for item in dates]))

        logger.info(
            f"School Combo :  +V : Dates : {len(dates)} Scores : {len(scores_pos)}")
        logger.info(
            f"School Combo :  -V : Dates : {len(dates)} Scores : {len(scores_negv)}")
        logger.info(
            f"School Combo :  -S : Dates : {len(dates)} Scores : {len(scores_need_support)}")

        logger.info("School Combo Scores +V: " +
                    " -- ".join([str(item) for item in scores_pos]))
        logger.info("School Combo Scores -v: " +
                    " -- ".join([str(item) for item in scores_negv]))
        logger.info("School Combo Scores ns: " +
                    " -- ".join([str(item) for item in scores_need_support]))

        year = dates
        vote_category_names = {
            'Positive Influencers': scores_pos,
            'Negative Influencers': scores_negv,
            'Need Social Support': scores_need_support,
        }

        # Create a figure and axis object
        fig, ax = plt.subplots()

        if len(dates) > 0:

            # Convert dates to numerical format for plotting
            # dates_num = date2num(dates)

            # fig, ax = plt.subplots()
            colors = ['#2ca02c', '#ff7f0e', '#1f77b4']
            ax.stackplot(year, vote_category_names.values(),
                         labels=vote_category_names.keys(), colors=colors, alpha=0.8)
            ax.legend(loc='upper left', reverse=True)
            # ax.set_title('Combined School Scores Over Time')
            ax.set_xlabel('Snapshot Datetime')
            ax.set_ylabel('Total Votes')
            # add tick at every 200 million people
            ax.yaxis.set_minor_locator(mticker.MultipleLocator(.2))

            # # Format x-axis for dates
            # Rotate dates on x-axis for better readability
            fig.autofmt_xdate(rotation=45)

            # Add a legend
            ax.legend()

            # Add grid for better visualization
            ax.grid(True)

            # Adjust layout for better spacing
            fig.tight_layout()

        # Save it to a temporary buffer.
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        # matplotlib.pyplot.close()
        buf.seek(0)
        plt.close(fig)
        return Response(buf.getvalue(), mimetype='image/png')
        # return send_file(buf, mimetype='image/png')

    @ log_function_call
    @ app.route('/school_trend_sabs.png')
    @ roles_accepted('admin', 'teacher')
    def school_trend_sabs():

        # real data
        dates = []
        scores_pos = []
        scores_negv = []
        scores_need_support = []

        # Calculate the date 1 year ago from today
        one_year_ago = dtm.datetime.utcnow() - timedelta(days=365)

        # Query to find all unique snapshot_id values
        unique_snapshot_ids = db.session.query(
            VoteSummaryHistory.snapshot_id
        ).filter(
            # only look at data from last year
            VoteSummaryHistory.voted_for_snap_date >= one_year_ago
        ).distinct().all()

        logger.info("unique_snapshot_ids: " +
                    " -- ".join([str(item) for item in unique_snapshot_ids]))

        # this is where I append snapshot dates and average school scores
        list_of_x_dates = []
        list_of_y_sabs = []
        # Get
        for snapshot_id in unique_snapshot_ids:
            # 0 index has id and #1 has snap date
            logger.info(f"Processing snapshot_id: {snapshot_id[0]}")
            # if(is_positive) :
            # Query specific columns and filter by voted_for_snap_date
            list_of_vote_summaries_for_snapshot = db.session.query(
                VoteSummaryHistory.snapshot_id,
                VoteSummaryHistory.voted_for_id,
                VoteSummaryHistory.voted_for_snap_date,

                # VoteSummaryHistory.vote_positive_count,
                # VoteSummaryHistory.vote_negative_count,
                # get the SIBS for every student in this cycle
                VoteSummaryHistory.vote_pos_negative_sum
                # VoteSummaryHistory.vote_needs_support_count
            ).filter(
                # only look at data from last year
                VoteSummaryHistory.snapshot_id == snapshot_id[0]
            ).all()

            logger.info(
                f"list_of_vote_summaries_for_snapshot : Len : {len(list_of_vote_summaries_for_snapshot)}: {list_of_vote_summaries_for_snapshot}")

            # Lets now loop through all Student SIBS scores in this cycle and calculate average
            sum_of_all_sibs_in_snapshot = 0
            sabs_for_snapshot = 0
            for span_student_row_in_cycle in list_of_vote_summaries_for_snapshot:
                logger.info(
                    f"Snap {span_student_row_in_cycle[0]}  : SIBS for User ID '{span_student_row_in_cycle[1]} : {span_student_row_in_cycle[3]}")
                sum_of_all_sibs_in_snapshot += span_student_row_in_cycle[3]

            # calculate average of all SIBS in a Cycle
            if sum_of_all_sibs_in_snapshot != 0:
                sabs_for_snapshot = sum_of_all_sibs_in_snapshot / \
                    len(list_of_vote_summaries_for_snapshot)

            logger.info(
                f"Snap {span_student_row_in_cycle[0]}  : SABS : {sabs_for_snapshot} , WHY : {sum_of_all_sibs_in_snapshot}/{len(list_of_vote_summaries_for_snapshot)}")

            # no need to loop, we take first record from the results as x axis
            x_date = list_of_vote_summaries_for_snapshot[0].voted_for_snap_date

            # for a unique snapshot id, we only have one date and one score ( we summed the score)
            list_of_x_dates.append(x_date.strftime("%Y-%m-%d %H:%M"))
            list_of_y_sabs.append(sabs_for_snapshot)

        logger.info(f"School SABS : list_of_x_dates: " +
                    " -- ".join([str(item) for item in list_of_x_dates]))

        logger.info(
            f"School Length of list_of_y_sabs: {len(dates)} Scores : {len(list_of_y_sabs)}")

        logger.info("School list_of_y_sabs SABS Scores :  " +
                    " -- ".join([str(item) for item in list_of_y_sabs]))

        year = list_of_x_dates
        vote_category_names = {
            'SABS Scores': list_of_y_sabs,
        }

        # Create a figure and axis object
        fig, ax = plt.subplots()

        if len(list_of_x_dates) > 0:

            # Convert dates to numerical format for plotting
            # dates_num = date2num(dates)

            # fig, ax = plt.subplots()
            # colors = ['#2ca02c', '#ff7f0e', '#1f77b4']
            colors = ['#2ca02c']
            ax.stackplot(year, vote_category_names.values(),
                         labels=vote_category_names.keys(), colors=colors, alpha=0.8)
            ax.legend(loc='upper left', reverse=True)
            # ax.set_title('Combined School Scores Over Time')
            ax.set_xlabel('Snapshot Datetime')
            ax.set_ylabel('Total Votes')
            # add tick at every 200 million people
            ax.yaxis.set_minor_locator(mticker.MultipleLocator(.2))

            # # Format x-axis for dates
            # Rotate dates on x-axis for better readability
            fig.autofmt_xdate(rotation=45)

            # Add a legend
            ax.legend()

            # Add grid for better visualization
            ax.grid(True)

            # Adjust layout for better spacing
            fig.tight_layout()

        # Save it to a temporary buffer.
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        # matplotlib.pyplot.close()
        buf.seek(0)
        plt.close(fig)
        return Response(buf.getvalue(), mimetype='image/png')
        # return send_file(buf, mimetype='image/png')

    @ app.route('/plot.png')
    @ roles_accepted('admin', 'teacher')
    def plot_png():
        # real data
        students = []
        scores = []

        isDecending = request.args.get('desc', default=True)

        if isDecending == 'true':
            # no longer using net totals
            # changed approach to show students with most +ve votes
            # summaries = VoteSummary.query.order_by(desc(VoteSummary.vote_pos_negative_sum)).limit(10).all()
            summaries = VoteSummary.query.order_by(
                desc(VoteSummary.vote_positive_count)).limit(MAX_STUDENTS_FOR_REALTIME_CHART).all()
        else:
            # changed approach to show students with most negative votes
            # summaries = VoteSummary.query.order_by(asc(VoteSummary.vote_pos_negative_sum)).limit(10).all()
            summaries = VoteSummary.query.order_by(
                desc(VoteSummary.vote_negative_count)).limit(MAX_STUDENTS_FOR_REALTIME_CHART).all()

        for summary in summaries:
            students.append(summary.voted_for.email.split('@')[0])
            if isDecending == 'true':
                # scores.append(summary.vote_pos_negative_sum)
                scores.append(summary.vote_positive_count)
            else:
                scores.append(summary.vote_negative_count)

        fig, ax = plt.subplots()
        y_pos = range(len(students))
        ax.barh(y_pos, scores, align='center')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(students)
        ax.invert_yaxis()  # labels read top-to-bottom
        ax.set_xlabel('Scores')
        ax.set_title('Student Scores')

        # Set x-axis to use integer ticks
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))

        # Save it to a temporary buffer.
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        # matplotlib.pyplot.close()
        buf.seek(0)
        plt.close(fig)
        return Response(buf.getvalue(), mimetype='image/png')
        # return send_file(buf, mimetype='image/png')

    @ app.route('/plot_need_support.png')
    @ roles_accepted('admin', 'teacher')
    def plot_need_support_png():

        # real data
        students = []
        scores = []
        summaries = VoteSummary.query.order_by(
            desc(VoteSummary.vote_needs_support_count)).limit(MAX_STUDENTS_FOR_REALTIME_CHART).all()

        for summary in summaries:
            students.append(summary.voted_for.email.split('@')[0])
            scores.append(summary.vote_needs_support_count)

        fig, ax = plt.subplots()
        y_pos = range(len(students))
        # ax.barh(y_pos, scores, align='center')
        ax.barh(y_pos, scores, align='center', color='orange')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(students)
        ax.invert_yaxis()  # labels read top-to-bottom
        ax.set_xlabel('Votes')
        ax.set_title('Student\'s Needing Support')

        # Set x-axis to use integer ticks
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))

        # Save it to a temporary buffer.
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        # matplotlib.pyplot.close()
        plt.close(fig)
        return Response(buf.getvalue(), mimetype='image/png')
        # return send_file(buf, mimetype='image/png')

    @ app.route('/top_n_students_in_last_snapshot.png')
    @ roles_accepted('admin', 'teacher')
    def top_n_students_in_last_snapshot():

        # real data
        students = []
        scores = []

        pos_neg_ns_or_sibs = request.args.get('pos_neg_ns_or_sibs')

        # Calculate the date 1 year ago from today
        one_year_ago = dtm.datetime.utcnow() - timedelta(days=365)
        logger.info(f"one_year_ago  : ${one_year_ago}")

        # Query to find all unique snapshot_id values
        unique_snapshot_ids = db.session.query(
            VoteSummaryHistory.snapshot_id
        ).filter(
            # only look at data from last year
            VoteSummaryHistory.voted_for_snap_date >= one_year_ago
        ).distinct().all()

        fig, ax = plt.subplots()

        if len(unique_snapshot_ids) > 0:
            logger.info("unique_snapshot_ids: " +
                        " -- ".join([str(item) for item in unique_snapshot_ids]))
            logger.info(
                f"Using the first one in the list, : {unique_snapshot_ids[0]}")

            which_column_to_sort_by = None

            if pos_neg_ns_or_sibs == 'pos':
                which_column_to_sort_by = VoteSummaryHistory.vote_positive_count
            elif pos_neg_ns_or_sibs == 'neg':
                which_column_to_sort_by = VoteSummaryHistory.vote_negative_count
            elif pos_neg_ns_or_sibs == 'ns':
                which_column_to_sort_by = VoteSummaryHistory.vote_needs_support_count

            if which_column_to_sort_by is not None:
                list_of_vote_summaries_for_snapshot = VoteSummaryHistory.query.filter(
                    # only look at data from last year
                    VoteSummaryHistory.snapshot_id == unique_snapshot_ids[0][0]
                ).order_by(
                    # desc(VoteSummaryHistory.vote_positive_count)
                    desc(which_column_to_sort_by)
                ).limit(MAX_STUDENTS_FOR_REALTIME_CHART).all()

            if pos_neg_ns_or_sibs == 'sibs':
                which_column_to_sort_by = VoteSummaryHistory.vote_pos_negative_sum

                if which_column_to_sort_by is not None:
                    list_of_vote_summaries_for_snapshot = VoteSummaryHistory.query.filter(
                        # only look at data from last year
                        VoteSummaryHistory.snapshot_id == unique_snapshot_ids[0][0]
                    ).order_by(
                        asc(which_column_to_sort_by)
                    ).limit(MAX_STUDENTS_FOR_REALTIME_CHART).all()

            logger.info(
                f"list_of_vote_summaries_for_snapshot : {list_of_vote_summaries_for_snapshot}")

            label = None
            for summary_hist_record in list_of_vote_summaries_for_snapshot:
                logger.info(f"summary_hist_record  :{summary_hist_record}")

                students.append(
                    summary_hist_record.voted_for.email.split('@')[0])

                if pos_neg_ns_or_sibs == 'pos':
                    scores.append(summary_hist_record.vote_positive_count)
                    label = "Most Positive"
                elif pos_neg_ns_or_sibs == 'neg':
                    scores.append(summary_hist_record.vote_negative_count)
                    label = "Most Negative"
                elif pos_neg_ns_or_sibs == 'ns':
                    scores.append(summary_hist_record.vote_needs_support_count)
                    label = "Highest Needs Support"
                elif pos_neg_ns_or_sibs == 'sibs':
                    scores.append(
                        summary_hist_record.vote_pos_negative_sum)  # aka SIBS
                    label = "Lowest Student Individual Behavior Score"

            if len(scores) > 0:

                y_pos = range(len(students))
                ax.barh(y_pos, scores, align='center')
                ax.set_yticks(y_pos)
                ax.set_yticklabels(students)
                ax.invert_yaxis()  # labels read top-to-bottom
                ax.set_xlabel('Scores')
                # ax.set_xlabel('Date')
                ax.set_ylabel('Name')
                # ax.set_ylabel('Students')
                # ax.set_title('Last Snapshot Scores : ' + label) #Will use HTML Label

                # Set x-axis to use integer ticks
                ax.xaxis.set_major_locator(MaxNLocator(integer=True))

        # Save it to a temporary buffer.
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        # matplotlib.pyplot.close()
        buf.seek(0)
        plt.close(fig)
        return Response(buf.getvalue(), mimetype='image/png')
        # return send_file(buf, mimetype='image/png')

    @ app.route('/funny_chart.png')
    def funny_chart():
        # Sample data
        x = ['aary', 'dad', 'mom']
        y = [5, 6, 10]

        # Create a plot
        plt.figure()
        plt.bar(x, y, color='#3954a4')
        plt.title('Sample Chart')
        plt.xlabel('X-axis')
        plt.ylabel('Y-axis')

        # Save the plot to a BytesIO object
        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)

        return send_file(img, mimetype='image/png')

    @ app.route('/resetvotes', methods=['GET'])
    @ roles_accepted('admin')
    def resetvotes():
        # ORM method to delete all records
        db.session.query(VoteSummary).delete()
        db.session.query(VoteSummaryHistory).delete()
        db.session.query(Vote).delete()
        db.session.query(Points).delete()
        db.session.commit()  # Commit the change

        return "Success! Votes, Summary, Summary History, and Points have been Deleted."

    @ log_function_call
    @ app.route('/createsnapshot', methods=['GET'])
    @ roles_accepted('admin')
    def createsnapshot():
        # Step1: We copy Summary to SummaryHistory
        # Step2: If user has even voted ones, we reward them the credit points as defined in config
        # Step3: And delete all records from Summary and Votes Table

        # S1 : ORM method to copy all records
        list_of_vote_summaries = VoteSummary.query.all()
        list_of_vote_summaries_history_rows = []
        # all records in a snapshot will have same id
        snapshot_id = str(uuid.uuid4())

        for summary in list_of_vote_summaries:

            # logger.info(summary)
            logger.info(
                f'Will Add {summary.voted_for_id} to VoteSummaryHistory')
            vsh_object = VoteSummaryHistory(
                voted_for_id=summary.voted_for_id,
                snapshot_id=snapshot_id,
                vote_positive_count=summary.vote_positive_count,
                vote_negative_count=summary.vote_negative_count,
                vote_pos_negative_sum=summary.vote_pos_negative_sum,
                vote_needs_support_count=summary.vote_needs_support_count
            )

            list_of_vote_summaries_history_rows.append(vsh_object)

        # Add them to the session
        db.session.add_all(list_of_vote_summaries_history_rows)
        db.session.commit()  # Commit the change

        # S2: If user has even voted ones, we reward them the credit points as defined in config
        i_points_to_award = Config.query.get(1).points_awarded_for_vote
        list_of_all_votes = Vote.query.all()
        list_of_point_records = []
        dict_of_already_seen_voter_ids = {}
        for vote in list_of_all_votes:

            if not vote.voter_id in dict_of_already_seen_voter_ids:
                logger.info(
                    f'Will awared points  -- {i_points_to_award} --  to -- {vote.voter.email}')

                # get old points so we can add new points to old ones
                # there can be only one entry per voter
                old_points = Points.query.filter_by(
                    awarded_to_id=vote.voter_id).first()
                if old_points:
                    old_points.awarded_points = old_points.awarded_points + i_points_to_award
                    # i_points_to_award = i_points_to_award + old_points.awarded_points
                else:
                    point_rec = Points(
                        awarded_to_id=vote.voter_id,
                        awarded_points=i_points_to_award
                    )
                    list_of_point_records.append(point_rec)

                # add in dict to ensure if this persone voted twice, we dont award them points again
                dict_of_already_seen_voter_ids[vote.voter_id] = None
            else:
                logger.info(
                    f'Will NOT awared points, seen already  -- {i_points_to_award} --  to -- {vote.voter.email}')

        # this only adds the new points
        db.session.add_all(list_of_point_records)
        db.session.commit()  # Commit the change, and will also update the old points

        # S3 : ORM method to delete all records
        db.session.query(VoteSummary).delete()
        db.session.query(Vote).delete()  # temporarily comment out to test
        db.session.commit()  # Commit the change

        return "Success: Current Votes Snapshot has been taken and the system is ready for a new Voting Cycle."

    @ app.route('/contact', methods=['GET'])
    def contact():
        name = request.args.get('name')
        email = request.args.get('email')
        message = request.args.get('message')

        cr = ContactRequest(
            name=name[:255],  # to save length allowed in db
            email=email[:255],
            message=message[:5000]
        )
        db.session.add(cr)
        db.session.commit()
        return "Thanks for contacting us. We will get back to you shortly."

    @ app.route('/vote', methods=['POST'])
    @ roles_accepted('admin', 'teacher', 'student')
    def vote():
        user_selected_id = int(request.form.get('user_selected_id'))
        vote_selected_cat_type = int(request.form.get('vote_type'))
        user_selected_email = request.form.get('user_selected_email')
        # Process the vote (e.g., save to the database)
        # flash(f'Your vote for user {user_id} with vote type {vote_type} was recorded.')

        # add the vote to DB
        # do additional logic to ensure we avoide duplicate votes

        # can be change, saved or failed, ignored
        changed_saved_failed_ignored = 'Failed'

        # Find if the user has voted for this kid before for +ve or -ve
        #   if yes, was it the same +ve or -ve
        #           Yes: then tell user his vote was :  remove as its same
        #           No :
        #               then remove old vote and add new
        #               tell user it was :  changed

        # if no, add vote and tell user it was :  saved
        # any error, tell user it was :  failed

        # check if I have voted for this kid before

        logger.info(
            f'Query Curr UID {current_user.id}, voted_for_id {user_selected_id}, vote_category_id={vote_selected_cat_type}')
        # vote_obj_before = Vote.query.filter_by(voter_id=current_user.id, voted_for_id=user_selected_id, vote_category_id=vote_selected_cat_type).first()

        # List of vote_category_id values to filter by
        pos_neg_category_ids = [1, 2]
        needs_supp_cat_ids = [3]

        vote_obj_before_pos_neg = Vote.query.filter(
            # Filter by vote_category_id +ve or -ve
            Vote.vote_category_id.in_(pos_neg_category_ids),
            # Filter by user_id
            Vote.voter_id.in_([current_user.id]),
            # Filter by voted_for_id
            Vote.voted_for_id.in_([user_selected_id])
        ).first()

        # vote_obj_before = Vote.query.filter_by(voter_id=current_user.id, voted_for_id=user_selected_id).first()

        vote_obj_before_needs_supp = Vote.query.filter(
            # Filter by needs support only
            Vote.vote_category_id.in_(needs_supp_cat_ids),
            # Filter by user_id
            Vote.voter_id.in_([current_user.id]),
            # Filter by voted_for_id
            Vote.voted_for_id.in_([user_selected_id])
        ).first()

        logger.info(
            f'vote_obj_before_needs_supp " : {vote_obj_before_needs_supp}')

        logger.info(f'vote_obj_before_pos_neg : {vote_obj_before_pos_neg}')

        # retrv totals from DB VoteSummary

        vote_summary_obj_before = db.session.query(
            VoteSummary).filter_by(voted_for_id=user_selected_id).first()
        if vote_summary_obj_before is None:
            vote_summary_obj_before = VoteSummary(voted_for_id=user_selected_id,
                                                  vote_positive_count=0,
                                                  vote_negative_count=0,
                                                  vote_needs_support_count=0,
                                                  vote_pos_negative_sum=0)
            db.session.add(vote_summary_obj_before)
            logger.info(
                'Added VoteSummary obj to DB for first time, as it was not found in db')
            db.session.commit()
        else:
            logger.info('VoteSummary obj was found in db')
        logger.info(vote_summary_obj_before)

        # if current_user.id == user_selected_id :
        #     logger.info ('Cant let you vote for your self')

        # I have two special condition checks
        # First one is for only +ve and -ve votes
        # second one is only for needs support
        if vote_selected_cat_type == 1 or vote_selected_cat_type == 2:

            if vote_obj_before_pos_neg is None:
                logger.info('User has not voted already, will submit vote')
                vote = Vote(voter_id=current_user.id, voted_for_id=user_selected_id,
                            vote_category_id=vote_selected_cat_type)
                db.session.add(vote)

                changed_saved_failed_ignored = 'Saved.'  # can be change, saved or failed
                # update VoteSummary
                # delete_vote=...
                updateVoteSummaryObject(
                    vote_summary_obj_before, vote_selected_cat_type)

                db.session.commit()

                logger.info(changed_saved_failed_ignored)
            else:
                logger.info(
                    f'vote_obj_before.vote_category_id : {vote_obj_before_pos_neg.vote_category_id} == vote_selected_cat_type : {vote_selected_cat_type}')
                # special handling for +ve and -ve votes
                # if vote_obj_before_pos_neg.vote_category_id == 1 or vote_obj_before_pos_neg.vote_category_id == 2 :

                if vote_obj_before_pos_neg.vote_category_id == vote_selected_cat_type:
                    changed_saved_failed_ignored = 'Deleted, as you clicked the same vote twice.'
                    logger.info(changed_saved_failed_ignored)
                    db.session.delete(vote_obj_before_pos_neg)
                    # update summary to remove selected vote
                    updateVoteSummaryObject(
                        vote_summary_obj_before, vote_selected_cat_type,  b_is_deleted=True)
                    db.session.commit()
                else:
                    db.session.delete(vote_obj_before_pos_neg)
                    vote = Vote(voter_id=current_user.id, voted_for_id=user_selected_id,
                                vote_category_id=vote_selected_cat_type)
                    db.session.add(vote)

                    changed_saved_failed_ignored = 'Changed.'
                    # update VoteSummary
                    updateVoteSummaryObject(
                        vote_summary_obj_before, vote_selected_cat_type, True)

                    db.session.commit()  # will also update VoteSummary automatically, sqla tracks changes

                    logger.info(changed_saved_failed_ignored)

        elif vote_selected_cat_type == 3:  # needs support
            # second one is only for needs support
            if vote_obj_before_needs_supp is None:
                logger.info(
                    'User has not voted already for support, will submit vote')
                vote = Vote(voter_id=current_user.id, voted_for_id=user_selected_id,
                            vote_category_id=vote_selected_cat_type)
                db.session.add(vote)

                changed_saved_failed_ignored = 'Saved.'  # can be change, saved or failed
                # update VoteSummary
                updateVoteSummaryObject(
                    vote_summary_obj_before, vote_selected_cat_type)

                db.session.commit()

                logger.info(changed_saved_failed_ignored)
            else:
                logger.info(
                    f'vote_obj_before_needs_supp.vote_category_id : {vote_obj_before_needs_supp.vote_category_id} == vote_selected_cat_type : {vote_selected_cat_type}')
                # special handling for +ve and -ve votes
                # if vote_obj_before_pos_neg.vote_category_id == 1 or vote_obj_before_pos_neg.vote_category_id == 2 :

                if vote_obj_before_needs_supp.vote_category_id == vote_selected_cat_type:
                    changed_saved_failed_ignored = 'Deleted, as you have already nominated this person for support.'
                    logger.info(changed_saved_failed_ignored)
                    db.session.delete(vote_obj_before_needs_supp)
                    updateVoteSummaryObject(
                        vote_summary_obj_before, vote_selected_cat_type,  b_is_deleted=True)
                    db.session.commit()

        return f'Your vote for "{user_selected_email}" was {changed_saved_failed_ignored}'

    @ log_function_call
    @ app.route('/cursive/<text>')
    def generate_cursive_text_image(text):

        # google_fonts_url = "https://fonts.googleapis.com/css2?family=Great+Vibes&display=swap"
        # font_name = "GreatVibes-Regular.ttf"
        font_url = "https://github.com/google/fonts/raw/main/ofl/greatvibes/GreatVibes-Regular.ttf"

        global CURSIVE_FONT_PATH_TMP  # ensure this is form config
        print("Database URI:", CURSIVE_FONT_PATH_TMP)

        if CURSIVE_FONT_PATH_TMP == "":
            # Download the font
            response = requests.get(font_url)
            with tempfile.NamedTemporaryFile(delete=False, prefix="font_sift_", suffix=".ttf") as tmp_font:
                tmp_font.write(response.content)
                # font_path = tmp_font.name
                CURSIVE_FONT_PATH_TMP = tmp_font.name
                logger.info(
                    f"Downloaded font from {font_url} to {CURSIVE_FONT_PATH_TMP}")
        else:
            logger.info(
                f"DIDNT Downloaded font , already existed {CURSIVE_FONT_PATH_TMP}")

        # Create an image with a white background
        width, height = 800, 60
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)

        # Load the font
        font = ImageFont.truetype(CURSIVE_FONT_PATH_TMP, 50)

        # Draw the text onto the image

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((width - text_width) // 2, (height - text_height) // 2)
        draw.text(position, text, fill='black', font=font)

        # Save the image to a bytes buffer
        buffer = io.BytesIO()
        image.save(buffer, 'PNG')
        buffer.seek(0)

        return send_file(buffer, mimetype='image/png')

    return app, user_datastore


@ log_function_call
def updateVoteSummaryObject(vote_summary_obj_before, i_vote_category_id, b_is_changed_sides=False, b_is_deleted=False):
    '''
    Update the vote summary object based on the user's vote category and actions taken.
    Parameters:
        vote_summary_obj_before (object): The vote summary object before the update.
        i_vote_category_id (int): The ID of the vote category.
        b_is_changed_sides (bool, optional): Flag indicating if the user changed sides. Defaults to False.
        b_is_deleted (bool, optional): Flag indicating if the vote is deleted. Defaults to False.
    '''

    # work with local vars
    i_vote_value_ps = 0
    i_vote_value_neg = 0
    i_vote_value_needs_supp = 0
    i_vote_pos_negative_sum = 0

    # fill local vars with DB vars
    if vote_summary_obj_before is not None:
        i_vote_value_ps = vote_summary_obj_before.vote_positive_count
        i_vote_value_neg = vote_summary_obj_before.vote_negative_count
        i_vote_value_needs_supp = vote_summary_obj_before.vote_needs_support_count
        i_vote_pos_negative_sum = vote_summary_obj_before.vote_pos_negative_sum
    else:
        logger.info('No Vote summary found for user {user_selected_id}')

    logger.info(
        f'Vote summary : FromDB :  i_vote_value_ps : {i_vote_value_ps}, i_vote_value_neg : {i_vote_value_neg} , i_vote_value_needs_supp : {i_vote_value_needs_supp}, i_vote_pos_negative_sum : {i_vote_pos_negative_sum}')

    # handle increasting totals if user voted +ve
    if i_vote_category_id == 1:
        if b_is_deleted:
            i_vote_value_ps -= 1
        else:
            i_vote_value_ps += 1
        if b_is_changed_sides:
            i_vote_value_neg -= 1

    # handle increasting totals if user voted -ve
    elif i_vote_category_id == 2:
        if b_is_deleted:
            i_vote_value_neg -= 1
        else:
            i_vote_value_neg += 1
        if b_is_changed_sides:
            i_vote_value_ps -= 1

    # handle increasting totals if user voted +-ve
    elif i_vote_category_id == 3:
        if b_is_deleted:
            i_vote_value_needs_supp -= 1
        else:
            i_vote_value_needs_supp += 1

    vote_summary_obj_before.vote_positive_count = i_vote_value_ps
    vote_summary_obj_before.vote_negative_count = i_vote_value_neg
    vote_summary_obj_before.vote_needs_support_count = i_vote_value_needs_supp
    vote_summary_obj_before.vote_pos_negative_sum = i_vote_value_ps - i_vote_value_neg
    # nothing to return becuase I am motifying the mutable VoteSummary Object here
    # I will have to call commit in the caller function


# added for pythonanywhere
if os.getenv('PYTHONANYWHERE_SITE'):
    logger.info(
        "Running on PythonAnywhere, will expport app to pythonanywhere.com")
    app, user_datastore = create_app()


if __name__ == '__main__':
    app, user_datastore = create_app()

    app.run(debug=True)

    # added for flask to watch all files in this project, including this HTML and JS files
    # need to run this command : pip install livereload, not needed for actual deployment
    # from livereload import Server
    # server = Server(app.wsgi_app)
    # server.serve(host = '127.0.0.1',port=5000)
