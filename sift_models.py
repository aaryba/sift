from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin, RoleMixin
from datetime import datetime  # to auto insert default dates
import uuid


db = SQLAlchemy()

# Define Models
roles_users = db.Table('roles_users',
                       db.Column('user_id', db.Integer(),
                                 db.ForeignKey('user.id')),
                       db.Column('role_id', db.Integer(),
                                 db.ForeignKey('role.id'))
                       )


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __repr__(self): return f'Role : {self.name}'
    # def __str__(self):
    #     # Using a list comprehension to create a string of attributes
    #     attributes = [f"{key}={value}" for key, value in vars(self).items() if not key.startswith('_')]
    #     return f"__str__ {self.__class__.__name__}({', '.join(attributes)})"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean(), default=True)
    confirmed_at = db.Column(db.DateTime(), default=datetime.utcnow)
    fs_uniquifier = db.Column(
        db.String(255), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    # added to check authorization in home page

    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)

    def __repr__(self): return f'User ID {self.id} : {self.email}'

    # def __str__(self):
    #     # Using a list comprehension to create a string of attributes
    #     attributes = [f"{key}={value}" for key, value in vars(self).items() if not key.startswith('_')]
    #     return f"__str__ {self.__class__.__name__}({', '.join(attributes)})"


class VoteCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))
    fs_uniquifier = db.Column(
        db.String(255), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    # votes = db.relationship('Vote', backref='vote_category', lazy='dynamic')

    def __repr__(self): return f'VoteCategory : {self.name}'

    # def __str__(self):
    #     # Using a list comprehension to create a string of attributes
    #     attributes = [f"{key}={value}" for key, value in vars(self).items() if not key.startswith('_')]
    #     return f"__str__ {self.__class__.__name__}({', '.join(attributes)})"


class Vote(db.Model):
    # PKeys
    id = db.Column(db.Integer, primary_key=True)
    # FKeys
    voter_id = db.Column(
        db.Integer(), db.ForeignKey('user.id'), nullable=False)
    voted_for_id = db.Column(
        db.Integer(), db.ForeignKey('user.id'), nullable=False)
    vote_category_id = db.Column(db.Integer(), db.ForeignKey(
        'vote_category.id'), nullable=False)
    # Other Data
    vote_date = db.Column(db.DateTime(), nullable=False,
                          default=datetime.utcnow)

    # Purpose: Establishes a relationship from the Votes model to the User model, indicating which user received the vote.
    # backref='votes_received': Automatically adds a votes_received attribute to the User model, allowing you to access all votes a user has received.
    # lazy='dynamic': Indicates that the votes_received attribute should be loaded dynamically when the User model is accessed.
    #  backref=backref('votes_cast', lazy='dynamic')
    # lazy='dynamic': This makes the votes_cast attribute return a query object instead of a list, allowing for further filtering or ordering.

    voter = db.relationship('User', foreign_keys=[
                            voter_id], backref='votes_cast')
    voted_for = db.relationship(
        'User', foreign_keys=[voted_for_id], backref='votes_received')
    vote_category = db.relationship('VoteCategory', foreign_keys=[
                                    vote_category_id], backref='votes')

    def __repr__(self):
        return f'Vote ID : {self.id}'


class VoteSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    voted_for_id = db.Column(
        db.Integer(), db.ForeignKey('user.id'), nullable=False)
    vote_positive_count = db.Column(db.Integer(), nullable=False)
    vote_negative_count = db.Column(db.Integer(), nullable=False)
    # add totals too so that we can order in chart, this is the SIBS Score
    vote_pos_negative_sum = db.Column(db.Integer(), nullable=False)
    vote_needs_support_count = db.Column(db.Integer(), nullable=False)
    voted_for = db.relationship(
        'User', foreign_keys=[voted_for_id], backref='votes_total')

    def __str__(self):
        # Using a list comprehension to create a string of attributes
        attributes = [f"{key}={value}" for key, value in vars(
            self).items() if not key.startswith('_')]
        return f"__str__ {self.__class__.__name__}({', '.join(attributes)})"


# Admin can take a snapshot of the votes on demand.
# Datamodel of this table is same as Vote Summary
class VoteSummaryHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # only different column from VoteSummary
    voted_for_snap_date = db.Column(
        db.DateTime(), default=datetime.utcnow, nullable=False)
    # unique id for snapshot to help us summarize results for school history
    snapshot_id = db.Column(db.String(255), nullable=False)

    voted_for_id = db.Column(
        db.Integer(), db.ForeignKey('user.id'), nullable=False)
    vote_positive_count = db.Column(db.Integer(), nullable=False)
    vote_negative_count = db.Column(db.Integer(), nullable=False)
    # add totals too so that we can order in chart
    vote_pos_negative_sum = db.Column(db.Integer(), nullable=False)
    vote_needs_support_count = db.Column(db.Integer(), nullable=False)
    voted_for = db.relationship(
        'User', foreign_keys=[voted_for_id], backref='votes_total_trend')

    def __str__(self):
        # Using a list comprehension to create a string of attributes
        attributes = [f"{key}={value}" for key, value in vars(
            self).items() if not key.startswith('_')]
        return f"__str__ {self.__class__.__name__}({', '.join(attributes)})"


class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    points_awarded_for_vote = db.Column(
        db.Integer(), nullable=False, default=1)
    school_name = db.Column(
        db.String(1000), nullable=False, default="Student Interaction Feedback Tool")

    def __repr__(self):
        return f'Vote ID : {self.id}'

# Keep record of all points awarded to a Student for voting


class Points(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    awarded_date = db.Column(
        db.DateTime(), default=datetime.utcnow, nullable=False)
    awarded_to_id = db.Column(
        db.Integer(), db.ForeignKey('user.id'), nullable=False)
    awarded_points = db.Column(db.Integer(), nullable=False)
    awarded_to = db.relationship(
        'User', foreign_keys=[awarded_to_id], backref='points_total')

    def __repr__(self):
        return f'Vote ID : {self.id}'


class ContactRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), default='', nullable=False)
    email = db.Column(db.String(255), nullable=False)
    message = db.Column(db.String(5000), nullable=False)
    date_of_contact = db.Column(
        db.DateTime(), default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'Contact ID : {self.id}'


class AllowedStudentsAndStaff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer(), db.ForeignKey('role.id'), nullable=False)

    def __repr__(self):
        return f'CSV Record ID : {self.id}'
