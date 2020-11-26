from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField

from wtforms.validators import DataRequired, Length, ValidationError
from models import Participant


class NonValidatingSelectField(SelectField):
    def pre_validate(self, form):
        pass


def email_exists(form, field):
    email = field.data.lower()
    if Participant.select().where(Participant.Email == email).exists():
        raise ValidationError('Participant with that email already exists, check the name you have entered matches '
                              'previously, or contact aldrichhouse75@gmail.com for help.')


class NewChallenge(FlaskForm):
    """Form for creating a challenge"""
    Name = StringField(
        'Name',
        validators=[
            DataRequired(),
            Length(min=1, max=50, message="Name must be max 50 characters")
        ]
    )

    Email = StringField(
        'Email',
        validators=[]
    )

    Title = StringField(
        'Challenge Title',
        validators=[
            DataRequired(),
            Length(min=1, max=50, message="Title must be max 50 characters")
        ]
    )

    Description = StringField(
        'Challenge Description',
        validators=[
            Length(max=250, message="Description must be max 250 characters")
        ]
    )

    # MoneyRaised = DecimalField(
    #     'Money Raised So Far',
    #     validators=[],
    #     default=0.00
    # )


class EditChallenge(FlaskForm):
    """Form for editing a challenge"""

    Title = StringField(
        'Title',
        validators=[
            DataRequired(),
            Length(min=1, max=50, message="Title must be max 50 characters")
        ]
    )

    Description = StringField(
        'Description',
        validators=[
            Length(max=250, message="Description must be max 250 characters")
        ]
    )

    MoneyRaised = DecimalField(
        'Money Raised So Far',
        validators=[]
    )

    URL = StringField(
        'URL',
        validators=[]
    )


class NewUser(FlaskForm):
    Name = StringField(
        'Name',
        validators=[DataRequired()]
    )

    Email = StringField(
        'Email',
        validators=[DataRequired()]
    )
