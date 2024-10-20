# SQLITE CLould admin/p8KKKwwdG8
# Flask Admin Code
# pip install WTForms wtforms-sqlalchemy
# from flask import redirect,url_for, Flask
from flask import Flask, render_template, request, session, redirect, jsonify, url_for, Response, flash
from flask_admin import Admin, AdminIndexView, expose, BaseView
from flask_admin.contrib.sqla import ModelView

from flask_admin.form import Select2Widget
from flask_security import current_user
from wtforms_sqlalchemy.fields import QuerySelectMultipleField
from wtforms_sqlalchemy.fields import QuerySelectField


from flask_security.utils import verify_password
from flask_security.utils import hash_password


from sift_models import User, Role, VoteCategory, VoteSummary, VoteSummaryHistory, Vote, Config, Points, ContactRequest, AllowedStudentsAndStaff, db
from sift_config import *




###############################
# Flask Admin Code - START
###############################

class AdminAccessOnlyView(ModelView):

    # to hide fs_uniquifier from list view for all views
    column_exclude_list = ['fs_uniquifier']

    #  Ensure only authenticated and admin are allwed to access

    def is_accessible(self):

        # Ensure the user is authenticated
        if not current_user.is_authenticated:
            return False

        # Check if the user has any of the required roles
        # required_roles = {'admin'}
        # required_roles = {'admin','teacher'}
        required_roles = {'admin'}
        # Assuming current_user.roles returns a list or set of roles
        user_roles = set(current_user.roles)

        return bool(required_roles & user_roles)


class TeacherAccessOnlyView(ModelView):

    # to hide fs_uniquifier from list view for all views
    column_exclude_list = ['fs_uniquifier']

    #  Ensure only authenticated and admin are allwed to access

    def is_accessible(self):

        # Ensure the user is authenticated
        if not current_user.is_authenticated:
            return False

        # Check if the user has any of the required roles
        # required_roles = {'admin'}
        required_roles = {'admin', 'teacher'}
        # Assuming current_user.roles returns a list or set of roles
        user_roles = set(current_user.roles)

        return bool(required_roles & user_roles)


class RoleView(AdminAccessOnlyView):
    can_export = True
    can_create = True
    can_edit = True
    can_delete = True


class UserAdmin(AdminAccessOnlyView):
    can_export = True
    can_create = True
    can_edit = True
    can_delete = True
    # Display a dropdown for roles in the form
    form_columns = ['email', 'password', 'roles', 'active',]

    # to
    column_exclude_list = ['password', 'fs_uniquifier']

    # Additional configurations for the User view
    column_searchable_list = ['email']
    column_filters = ['email']

    # Use QuerySelectMultipleField for roles
    form_overrides = {
        'roles': QuerySelectMultipleField
    }

    # Define how the dropdown should populate its choices
    form_args = {
        'roles': {
            'query_factory': lambda: Role.query.all(),
            'widget': Select2Widget(multiple=True),
            'get_label': 'name'
        },
        # 'password': {
        #     # 'get_label': 'password',
        #     'allow_blank': False,
        # },

    }

    def on_model_change(self, form, model, is_created):
        ...
        # Ensure the correct hashed password is used when saving
        # getting forms ID and saving it in the model
        if is_created or form.password.data:

            pass_from_form = form.password.data

            # neded if we use bcrypt
            # if not (pass_from_form.lower().startswith('$2b$12$'.lower()) and len(pass_from_form) == 60):
            # neded if we use argon
            if not pass_from_form.lower().startswith('$argon2id$'):
                print(f'*********************************************')
                print(f'User enteres plain pass, so lets hash it')
                print(f'form.password : {form.password.data}')
                model.password = hash_password(form.password.data)
                print(verify_password(form.password.data, model.password))
                print(f'model.password : {model.password}')
                print(f'Doing Debug Exit')

            print(f'form.password.data : {form.password.data}')
            print(f'model.password : {model.password}')
            print(f'*********************************************')
            # model.voted_for_id = form.voted_for.data.id
            # model.vote_category_id = form.vote_category.data.id


class VoteAdmin(TeacherAccessOnlyView):
    can_export = True
    can_create = True
    can_edit = True
    can_delete = True

    form_columns = ['vote_date', 'voter', 'voted_for', 'vote_category']

    # Use QuerySelectMultipleField for roles
    form_overrides = {
        # these have to point to relationships in the Vote Class
        'voter': QuerySelectField,  # Not QuerySelectMultipleField,
        'voted_for': QuerySelectField,
        'vote_category': QuerySelectField
    }

    # Define how the dropdown should populate its choices
    form_args = {
        'voter': {
            'query_factory': lambda: User.query.all(),
            'get_label': 'email',
            'widget': Select2Widget(multiple=False),
            'allow_blank': False,
            'get_pk': lambda x: x.id  # Explicitly specify the primary key
        },
        'voted_for': {
            'query_factory': lambda: User.query.all(),
            'get_label': 'email',
            'widget': Select2Widget(multiple=False),
            'allow_blank': False,
            'get_pk': lambda x: x.id  # Explicitly specify the primary key
        },
        'vote_category': {
            'query_factory': lambda: VoteCategory.query.all(),
            'get_label': 'name',
            'widget': Select2Widget(multiple=False),
            'allow_blank': False,
            'get_pk': lambda x: x.id  # Explicitly specify the primary key
        },

    }

    def on_model_change(self, form, model, is_created):
        # Ensure the correct IDs are used when saving
        # getting forms ID and saving it in the model
        model.voter_id = form.voter.data.id
        model.voted_for_id = form.voted_for.data.id
        model.vote_category_id = form.vote_category.data.id


class VoteSummaryAdmin(TeacherAccessOnlyView):
    can_export = True
    can_create = True
    can_edit = True
    can_delete = True

    # which columns to display
    form_columns = ['voted_for', 'vote_positive_count',
                    'vote_negative_count', 'vote_needs_support_count']

    # No overrides needed
    form_overrides = {
    }

    # Define how the dropdown should populate its choices
    form_args = {
        'voted_for': {
            'query_factory': lambda: User.query.all(),
            'get_label': 'email',
            'widget': Select2Widget(multiple=False),
            'allow_blank': False,
            'get_pk': lambda x: x.id  # Explicitly specify the primary key
        }
    }

    column_searchable_list = ['voted_for_id']
    column_filters = ['voted_for_id']

    def on_model_change(self, form, model, is_created):
        # Ensure the correct IDs are used when saving
        model.voted_for_id = form.voted_for.data.id


class VoteSummaryHistoryAdmin(TeacherAccessOnlyView):
    can_export = True
    can_create = True
    can_edit = True
    can_delete = True

    # which columns to display
    form_columns = ['voted_for', 'voted_for_snap_date', 'vote_positive_count',
                    'vote_negative_count', 'vote_needs_support_count']

    # No overrides needed
    form_overrides = {
    }

    # Define how the dropdown should populate its choices
    form_args = {
        'voted_for': {
            'query_factory': lambda: User.query.all(),
            'get_label': 'email',
            'widget': Select2Widget(multiple=False),
            'allow_blank': False,
            'get_pk': lambda x: x.id  # Explicitly specify the primary key
        }
    }

    column_searchable_list = ['voted_for_id']
    column_filters = ['voted_for_id']

    def on_model_change(self, form, model, is_created):
        # Ensure the correct IDs are used when saving
        model.voted_for_id = form.voted_for.data.id


class VoteCategoryAdmin(AdminAccessOnlyView):
    can_export = False
    can_create = True
    can_edit = True
    can_delete = True
    # Display a dropdown for roles in the form
    form_columns = ['name', 'description']


class ConfigAdminView(AdminAccessOnlyView):
    can_export = False
    can_create = False
    can_edit = True
    can_delete = False
    # Display a dropdown for roles in the form
    # form_columns = ['name', 'description']


class PointTeacherView(TeacherAccessOnlyView):
    can_export = True
    can_create = False
    can_edit = True
    can_delete = False

    column_searchable_list = ['awarded_to_id']
    column_filters = ['awarded_to_id']
    # Display a dropdown for roles in the form
    # form_columns = ['name', 'description']

    form_columns = ['awarded_to', 'awarded_date']

    form_args = {
        'awarded_to_id': {
            'query_factory': lambda: User.query.all(),
            'get_label': 'email',
            'widget': Select2Widget(multiple=False),
            'allow_blank': False,
            'get_pk': lambda x: x.id  # Explicitly specify the primary key
        }
    }


class ContactAdminView(AdminAccessOnlyView):
    can_export = True
    can_create = True
    can_edit = True
    can_delete = True

    column_searchable_list = ['email']
    column_filters = ['email']
    # Display a dropdown for roles in the form
    # form_columns = ['name', 'description']

    form_columns = ['name', 'email', 'message', 'date_of_contact']


class AllowedStudentsAndStaffAdminView(AdminAccessOnlyView):
    can_export = True
    can_create = True
    can_edit = True
    can_delete = True

    column_searchable_list = ['email']
    column_filters = ['email']
    # Display a dropdown for roles in the form
    # form_columns = ['name', 'description']

    form_columns = ['email', 'role', 'role_id']


####################
# FLASK ADMIN Custom Home Page
####################

# added to show charts
class MyCustomView_Charts(BaseView):
    @expose('/')  # default view is needed
    def index(self):
        # return self.render('charts.html', chart_refresh_in_ms=2000)

        return self.render('charts.html', chart_refresh_in_ms=CHART_AUTO_REFRESH_MS)

    def is_accessible(self):
        # return current_user.is_authenticated

        # Ensure the user is authenticated
        if not current_user.is_authenticated:
            return False

        # Check if the user has any of the required roles
        required_roles = {'admin', 'teacher'}  # Add other roles if needed
        # Assuming current_user.roles returns a list or set of roles
        user_roles = set(current_user.roles)

        return bool(required_roles & user_roles)

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('security.login'))

    # @expose('/custom-link')
    # def custom_link(self):
    #     return redirect(url_for('chartpage')) # this is the function name, will get URL for it


class MyCustomView_About(BaseView):
    @expose('/')  # default view is needed
    def index(self):

        return self.render('about.html')


class MyCustomView_Sources(BaseView):
    @expose('/')  # default view is needed
    def index(self):

        return self.render('sources.html')


class ContactView(BaseView):
    @expose('/')  # default view is needed
    def index(self):
        # return self.render('charts.html', chart_refresh_in_ms=2000)

        return self.render('contact.html')


class AaryDemoView(BaseView):
    @expose('/')  # default view is needed
    def index(self):
        # return self.render('charts.html', chart_refresh_in_ms=2000)

        return self.render('demo.html', chart_refresh_in_ms=CHART_AUTO_REFRESH_MS)

    def is_accessible(self):
        # return current_user.is_authenticated

        # Ensure the user is authenticated
        if not current_user.is_authenticated:
            return False

        # Check if the user has any of the required roles
        required_roles = {'admin', 'teacher'}  # Add other roles if needed
        # Assuming current_user.roles returns a list or set of roles
        user_roles = set(current_user.roles)

        return bool(required_roles & user_roles)

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('security.login'))
# def register_admin_views(flask_app : Flask):


def register_admin_views(admin: Admin):

    # Add Custom Pages

    admin.add_view(MyCustomView_Charts(name='Charts', endpoint='chart-ep',
                   menu_icon_type='fa', menu_icon_value='fa-bar-chart'))

    admin.add_view(MyCustomView_About(name='About SIFT', endpoint='about-ep',
                   menu_icon_type='fa', menu_icon_value='fa-info-circle'))

    admin.add_view(MyCustomView_Sources(name='Sources', endpoint='sources-ep',
                   menu_icon_type='fa', menu_icon_value='fa-link'))

    # Table views
    admin.add_view(VoteAdmin(Vote, db.session, category='Vote',
                   menu_icon_type='fa', menu_icon_value='fa-sticky-note'))
    admin.add_view(VoteSummaryAdmin(
        VoteSummary, db.session, category='Vote',
                   menu_icon_type='fa', menu_icon_value='fa-folder-open'))
    admin.add_view(VoteSummaryHistoryAdmin(
        VoteSummaryHistory, db.session, category='Vote',
                   menu_icon_type='fa', menu_icon_value='fa-folder'))
    admin.add_view(VoteCategoryAdmin(
        VoteCategory, db.session, category='Vote',
                   menu_icon_type='fa', menu_icon_value='fa-bars'))

    admin.add_view(ConfigAdminView(Config, db.session, category='Settings',
                   menu_icon_type='fa', menu_icon_value='fa-cogs'))
    admin.add_view(PointTeacherView(Points, db.session, category='Settings',
                   menu_icon_type='fa', menu_icon_value='fa-dot-circle-o'))
    admin.add_view(ContactAdminView(
        ContactRequest, db.session, category='Settings',
                   menu_icon_type='fa', menu_icon_value='fa-comments-o'))
    admin.add_view(RoleView(Role, db.session, category='Registration Info',
                   menu_icon_type='fa', menu_icon_value='fa-id-badge'))

    admin.add_view(UserAdmin(User, db.session,
                   category='Registration Info', menu_icon_type='fa', menu_icon_value='fa-user-circle-o'))

    admin.add_view(AllowedStudentsAndStaffAdminView(
        AllowedStudentsAndStaff, db.session, category='Registration Info', menu_icon_type='fa', menu_icon_value='fa-shield'))

    admin.add_view(ContactView(name='Contact', endpoint='contact-ep',
                   menu_icon_type='fa', menu_icon_value='fa-envelope'))

    # admin.add_view(AaryDemoView(name='Demo', endpoint='demo-ep',
    #                menu_icon_type='fa', menu_icon_value='fa-bar-chart'))

    # Icon classes in FontAwesome : Taken from https://fontawesome.com/v4/icons/
    # admin.add_view(VoteAdmin(Vote, db.session,category='Vote Management', menu_icon_type='fa', menu_icon_value='fa-tag'))
    # admin.add_view(VoteSummaryAdmin(VoteSummary, db.session,category='Vote Management', menu_icon_type='fa', menu_icon_value='fa-tags'))
    # admin.add_view(VoteSummaryHistoryAdmin(VoteSummaryHistory, db.session,category='Vote Management', menu_icon_type='fa', menu_icon_value='fa-history'))

    # admin.add_view(ConfigAdminView(Config, db.session,category='Config Management', menu_icon_type='fa', menu_icon_value='fa-cogs'))
    # admin.add_view(PointTeacherView(Points, db.session,category='Config Management', menu_icon_type='fa', menu_icon_value='fa-star-half-o'))
    # admin.add_view(ContactAdminView(ContactRequest, db.session,category='Config Management', menu_icon_type='fa', menu_icon_value='fa-envelope-open-o'))
    # admin.add_view(VoteCategoryAdmin(VoteCategory, db.session,category='Config Management', menu_icon_type='fa', menu_icon_value='fa-leaf'))

    # admin.add_view(UserAdmin(User, db.session,category='User Management', menu_icon_type='fa', menu_icon_value='fa-user'))
    # admin.add_view(RoleView(Role, db.session,category='User Management', menu_icon_type='fa', menu_icon_value='fa-users'))
    # admin.add_view(AllowedStudentsAndStaffAdminView(AllowedStudentsAndStaff, db.session,category='User Management', menu_icon_type='fa', menu_icon_value='fa-shield'))


###############################
# Flask Admin Code - END
###############################
