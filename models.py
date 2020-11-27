import datetime
from peewee import *
from decimal import Decimal
import os


testing = False

if testing:
    """For testing use SQLite database"""
    DATABASE = SqliteDatabase('moodboard.db')
else:
    """For deployment use Postgres database"""
    try:
        try:
            import environment
            environment.create_database_environment_variables()
        except ModuleNotFoundError:
            pass
        DATABASE = PostgresqlDatabase(os.environ.get('DATABASE_URL').split('/')[-1],
                                      user=os.environ.get('DATABASE_URL').split('/')[2].split(':')[0],
                                      password=os.environ.get('DATABASE_URL').split(':')[2].split('@')[0],
                                      host=os.environ.get('DATABASE_URL').split('@')[1].split(':')[0],
                                      port=os.environ.get('DATABASE_URL').split(':')[3].split('/')[0],
                                      autorollback=True)
        print('Databse connected')
    except OperationalError:
        print('database not connected')
        DATABASE = SqliteDatabase('database.db')


class Participant(Model):
    """Class for people to assign challenges to"""
    # TODO add validation if participant creation is exposed to web users
    id = PrimaryKeyField()
    Name = CharField()
    Email = CharField(unique=True)
    bulkemail = BooleanField(default=True)

    class Meta:
        database = DATABASE
        order_by = ('Name',)

    @staticmethod
    def get_participants():
        return Participant.select()

    @staticmethod
    def get_participant_by_id(id):
        return Participant.get(Participant.id == id)

    @classmethod
    def create_participant(cls, name, email):
        try:
            cls.create(Name=name, Email=email)
        except ValueError:
            print('error creating Participant')


class Challenge(Model):
    """Challenges to be displayed as cards"""
    id = PrimaryKeyField()
    Participant = ForeignKeyField(Participant, related_name='Participant')
    Title = CharField(max_length=50)
    Description = CharField(max_length=250)
    MoneyRaised = DecimalField(default=0)
    URL = CharField(default='')

    class Meta:
        database = DATABASE
        order_by = ('Participant',)

    @classmethod
    def create_challenge(cls, participant, title, description='', moneyraised=0):
        try:
            cls.create(Participant=participant, Title=title, Description=description, MoneyRaised=moneyraised)
        except ValueError:
            print('error creating challenge')

    def update_money_raised_by(self, amount):
        current_money = Challenge.get(Challenge.id == self).MoneyRaised
        new_money = current_money + Decimal(amount)
        Challenge.update({Challenge.MoneyRaised: Decimal(new_money)}).where(Challenge.id == self).execute()
        return

    @staticmethod
    def get_challenges():
        return Challenge.select()

    @staticmethod
    def get_challenge_by_id(id):
        return Challenge.get(Challenge.id == id)


class BulkEmailTask(Model):
    id = PrimaryKeyField()
    Task_Name = CharField(unique=True)
    Task_Message = CharField()
    DateTime = DateTimeField(default=datetime.datetime.now)
    Template = CharField(default='emails/default_bulk.html')
    Done = BooleanField(default=False)

    class Meta:
        database = DATABASE
        order_by = ('id',)


def initialise():
    print('Database initialising')
    DATABASE.connect()
    # DATABASE.drop_tables([Participant, Challenge])
    DATABASE.create_tables([Participant, Challenge, BulkEmailTask], safe=True)
    # DATABASE.execute_sql('ALTER TABLE participant ADD COLUMN "bulkemail" BOOLEAN DEFAULT TRUE')
    DATABASE.close()
