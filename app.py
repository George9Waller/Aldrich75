import os
import atexit
import datetime
import time
from decimal import Decimal
import webbrowser
import peewee
import jinja2
from apscheduler.schedulers.background import BackgroundScheduler
from flask_mail import Mail, Message
from flask import Flask, render_template, request, make_response, flash, url_for, redirect
import models
import forms
# import users

app = Flask(__name__)

try:
    import environment
    environment.create_app_environment_variables()
except ModuleNotFoundError:
    pass


app.secret_key = os.environ.get('SECRET_KEY')

app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get("EMAIL_USER")
app.config['MAIL_PASSWORD'] = os.environ.get("EMAIL_PASS")
mail = Mail(app)


def bulk_email_checker():
    print('checking mail tasks')
    try:
        for task in models.BulkEmailTask.select():
            if not task.Done:
                if task.DateTime <= datetime.datetime.now():
                    print(task.DateTime, datetime.datetime.now())
                    print('doing email task: {}'.format(task.Task_Name))
                    do_bulk_task(task)
    except peewee.InternalError:
        print('Peewee Internal Error')
        pass


def do_bulk_task(task):

    total = 0.00
    for challenge in models.Challenge.select():
        total += float(challenge.MoneyRaised)

    attempted = []

    for participant in models.Participant.select():
        if participant.bulkemail:
            if str(participant.Email) in attempted:
                pass
            else:
                attempted.append(participant.Email)
                # try:
                msg = Message(task.Task_Name, sender='"Aldrich 75 <aldrichhouse75@gmail.com>"',
                              recipients=[participant.Email])

                with app.app_context():
                    context = ()
                    template = jinja2.Template(str(task.Template))
                    msg.html = render_template(str(task.Template), participant=participant, total=total, title=task.Task_Name, message=task.Task_Message, bulk=True)

                with app.test_request_context('/'):
                    mail.send(msg)
                    time.sleep(30)
                # except:
                #     pass

    models.BulkEmailTask.update({models.BulkEmailTask.Done: True}).where(models.BulkEmailTask.id == task.id).execute()
    print(attempted)


def check_authenticated():
    if request.cookies.get('authenticated') == os.environ.get('LOGIN_KEY'):
        return True
    return False

def check_authenticated_admin():
    if request.cookies.get('admin') == os.environ.get('ADMIN_KEY'):
        return True
    else:
        return False


@app.route('/')
def index():
    authenticated = check_authenticated()

    challenges = models.Challenge.get_challenges()

    total = 0
    met_challenges = 0
    for challenge in challenges:
        money = round(float(challenge.MoneyRaised), 3)
        total += money
        if money >= 75:
            met_challenges += 1

    startdate = datetime.date(2021, 1, 5)
    enddate = datetime.date(2021, 3, 19)

    today = datetime.date.today()
    if today < startdate:
        days_text = 'Days until start'
        future = startdate
        days = future - today
        colour = '#FFBF00'
    else:
        days_text = 'Days left'
        future = enddate
        days = future - today
        colour = '##659D32'

    progress = int((total / 7500) * 100)

    ordered_challenges = models.Challenge.select().order_by(models.Challenge.MoneyRaised.asc())
    challenge1 = None
    challenge2 = None
    challenge3 = None

    try:
        challenge1 = ordered_challenges[0]
        challenge2 = ordered_challenges[1]
        challenge3 = ordered_challenges[2]
    except:
        pass

    my_challenges = []
    try:
        try:
            participant = models.Participant.get(models.Participant.id == int(request.cookies.get('ParticipantID')))
            for inspect_challenge in challenges:
                if inspect_challenge.Participant == participant:
                    my_challenges.append(inspect_challenge.id)
        except:
            pass

    except models.DoesNotExist:
        pass

    default_participant = models.Participant.get(models.Participant.Email == 'aldrichhouse75@gmail.com')
    support_challenge = models.Challenge.get(models.Challenge.Participant == default_participant)

    popup = request.cookies.get('first')
    if popup is None:
        popup = False

    resp = make_response(render_template('index.html', total=total, met_challenges=met_challenges, days=days.days,
                                         days_colour=colour, days_text=days_text, authenticated=authenticated,
                                         challenges=challenges, progress=progress, challenge1=challenge1,
                                         challenge2=challenge2, challenge3=challenge3, my_challenges=my_challenges,
                                         support_challenge_id=support_challenge.id, popup=popup))

    if not popup:
        resp.set_cookie('first', 'True', max_age=15552000)

    return resp


@app.route('/login', methods=['GET', 'POST'])
def login():
    # redirect if already authenticated
    if check_authenticated():
        return redirect(url_for('index'))

    if request.method == 'POST':
        password = request.form.get('password')
        if password == os.environ.get('ACCESS_PASS'):
            # TODO get stats
            resp = make_response(redirect(url_for('index')))
            resp.set_cookie('authenticated', os.environ.get('LOGIN_KEY'), max_age=7200)
            flash('You will be logged in for 2h', 'success')
            return resp
        elif password == '':
            flash('A password is required', 'error')
        elif password == os.environ.get('ADMIN_PASS'):
            resp = make_response(redirect(url_for('admin')))
            resp.set_cookie('admin', os.environ.get('ADMIN_KEY'), max_age=7200)
            return resp
        else:
            flash('Password incorrect', 'error')

    return render_template('login.html')


@app.route('/newchallenge', methods=['GET', 'POST'])
def create_challenge():
    form = forms.NewChallenge()

    if not check_authenticated():
        flash('You must be logged in to perform this action', 'error')
        return redirect(url_for('index'))

    if form.validate_on_submit():
        flash('Challenge created', 'success')
        try:
            participant = models.Participant.get(models.Participant.Name == form.Name.data.strip()
                                                 and models.Participant.Email == form.Email.data.lower().strip())
        except models.DoesNotExist:
            creating = True
            while creating:
                name = form.Name.data.strip()
                email = form.Email.data.lower().strip()
                try:
                    participant = models.Participant.create(Name=name, Email=email)
                    creating = False
                    msg = Message('New User', sender='"Aldrich 75 <aldrichhouse75@gmail.com>"',
                                  recipients=[participant.Email])
                    message = "It's great to see you're contributing to the campaign and make sure to share the news to your friends and family so they can donate. Your details have now been saved so if you want to make another challenge using this email you must use the name: " + participant.Name
                    msg.html = render_template('emails/default_bulk.html', participant=participant, title='Congratulations on making a challenge!', message=message, bulk=False)
                    mail.send(msg)
                except:
                    name = name + '_'

        models.Challenge.create_challenge(participant, form.Title.data, form.Description.data)

        resp = make_response(redirect(url_for('index')))
        resp.set_cookie('ParticipantID', str(participant.id), max_age=15552000)
        return resp

    else:
        try:
            participant = models.Participant.get_participant_by_id(int(request.cookies.get('ParticipantID')))
            form.Name.data = participant.Name
            form.Email.data = participant.Email
        except:
            pass
        return render_template('create_challenge.html', form=form, function='Create')


@app.route('/donate/<int:challengeid>', methods=['GET', 'POST'])
def donate(challengeid):
    challenge = models.Challenge.get_challenge_by_id(challengeid)

    if request.method == 'POST':
        money = round(float(request.form.get('Donation')), 3)
        if money == 0:
            flash('You cannot pledge to donate £0', 'error')
        else:
            flash('Thank you for pledging to donate £{}'.format(money), 'success')
            challenge.update_money_raised_by(money)
            if request.form.get('paybycard'):
                print(request.form.get('paybycard'))
                money = round((money * 1.029), 2)
            return redirect('https://www.paypal.com/paypalme/BrightonCollege/{}'.format(money))

    return render_template('donate.html', challenge=challenge)


@app.route('/admin')
def admin():
    if check_authenticated_admin():
        users = models.Participant.get_participants().order_by(models.Participant.Email)
        challenges = models.Challenge.get_challenges().order_by(models.Challenge.Participant)
        return render_template('admin.html', users=users, challenges=challenges)
    else:
        return redirect(url_for('index'))


@app.route('/admin/delete/user/<int:userid>')
def delete_user(userid):
    if check_authenticated_admin():
        user = models.Participant.get_participant_by_id(userid)
        models.Challenge.delete().where(models.Challenge.Participant == user).execute()
        models.Participant.delete().where(models.Participant.id == user.id).execute()
        return redirect(url_for('admin'))
    else:
        flash('unauthorised action', 'error')
        return redirect(url_for('index'))


@app.route('/admin/delete/challenge/<int:challengeid>')
def delete_challenge(challengeid):
    if check_authenticated_admin():
        models.Challenge.delete().where(models.Challenge.id == challengeid).execute()
        return redirect(url_for('admin'))
    else:
        flash('unauthorised action', 'error')
        return redirect(url_for('index'))


@app.route('/admin/edit/challenge/<int:challengeid>', methods=['GET', 'POST'])
def edit_challenge(challengeid):
    try:
        participant = models.Participant.get(models.Participant.id == request.cookies.get('ParticipantID'))
    except models.DoesNotExist:
        participant = None

    challenge = models.Challenge.get_challenge_by_id(challengeid)

    if check_authenticated_admin() or challenge.Participant == participant:
        form = forms.EditChallenge()

        if form.validate_on_submit():
            if check_authenticated_admin():
                models.Challenge.update({models.Challenge.Title: form.Title.data,
                                         models.Challenge.Description: form.Description.data,
                                         models.Challenge.URL: form.URL.data,
                                         models.Challenge.MoneyRaised: form.MoneyRaised.data})\
                    .where(models.Challenge.id == challengeid).execute()
            else:
                models.Challenge.update({models.Challenge.Title: form.Title.data,
                                         models.Challenge.Description: form.Description.data})\
                    .where(models.Challenge.id == challengeid).execute()
            return redirect(url_for('admin'))
        else:
            form.Title.data = challenge.Title
            form.Description.data = challenge.Description
            form.MoneyRaised.data = challenge.MoneyRaised
            form.URL.data = challenge.URL
            return render_template('create_challenge.html', form=form, function='Update', challenge=challenge,
                                   admin=check_authenticated_admin())

    else:
        flash('unauthorised action', 'error')
        return redirect(url_for('index'))


@app.route('/admin/create/user', methods=['GET', 'POST'])
def create_user():
    if request.cookies.get('admin') == os.environ.get('ADMIN_KEY'):
        form = forms.NewUser()

        if form.validate_on_submit():
            try:
                models.Participant.create_participant(form.Name.data, form.Email.data)
                return redirect(url_for('admin'))
            except:
                flash('error creating user', 'error')
                return redirect(url_for('admin'))
        else:
            return render_template('create_user.html', form=form)
    else:
        flash('unauthorised action', 'error')
        return redirect(url_for('index'))


@app.route('/unsubscribe/<int:ParticipantID>')
def unsubscribe(ParticipantID):
    try:
        participant = models.Participant.get_participant_by_id(ParticipantID)
    except:
        flash('Error unsubscribing from bulk emails, please email aldrichhouse75@gmail.com', 'error')
        return redirect(url_for('index'))

    try:
        models.Participant.update({models.Participant.bulkemail: False}).where(models.Participant.id == ParticipantID).execute()
        message = participant.Name + ' has been successfully unsubscribed from bulk emails'
        flash(message, 'success')
        return redirect(url_for('index'))
    except:
        flash('Error unsubscribing from bulk emails, please email aldrichhouse75@gmail.com', 'error')
        return redirect(url_for('index'))


if __name__:
    # different host for web server
    if os.uname().nodename == 'Georges-MacBook-Pro-2.local':
        app.run(port=int(os.environ.get('PORT', 5000)), use_reloader=True, host='127.0.0.1')
    else:
        app.run(port=int(os.environ.get('PORT', 5000)), use_reloader=True, host='0.0.0.0')
    models.initialise()

    try:
        participant = models.Participant.create(Name='Aldrich 75', Email='aldrichhouse75@gmail.com', bulkemail=True)
        models.Challenge.create(Participant=participant, Title='Raise Money For Charity', Description='Donate to this challenge if you just want to support this campaign and not a specific challenge')
    except:
        pass

    try:
        task_time = datetime.datetime(2020, 11, 27, 8, 40, 0, 0)
        print(task_time)
        task = models.BulkEmailTask.create(Task_Name='Welcome Aldrich', Task_Message='message', DateTime=task_time, Template='emails/welcome_email.html', Done=False)
        print('created email task')
    except:
        pass

    # try:
    #     for user in users.get_users():
    #         try:
    #             name = user[2] + ' ' + user[0]
    #             print(name)
    #             models.Participant.create_participant(name, user[4])
    #         except:
    #             pass
    # except:
    #     pass

    # models.BulkEmailTask.update({models.BulkEmailTask.Done: False}).execute()

    # Bulk Email scheduler
    # scheduler = BackgroundScheduler()
    # scheduler.add_job(func=bulk_email_checker, trigger="interval", seconds=60)
    # scheduler.start()
    # print('started scheduler')

    """check emails on program start"""
    bulk_email_checker()
    #
    # atexit.register(lambda: scheduler.shutdown())
