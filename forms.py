from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField

from wtforms.validators import DataRequired, Length


class NonValidatingSelectField(SelectField):
    def pre_validate(self, form):
        pass


class NewChallenge(FlaskForm):
    """Form for creating a challenge"""
    Participant = NonValidatingSelectField(
        'Participant',
        validators=[
            DataRequired()
        ]
    )

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
        validators=[],
        default=0.00
    )


class EditChallenge(FlaskForm):
    """Form for editing a challenge"""
    Participant = NonValidatingSelectField(
        'Participant',
        validators=[
            DataRequired()
        ]
    )

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
