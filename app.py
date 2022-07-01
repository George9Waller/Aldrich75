import os
import atexit
import datetime
import time
from decimal import Decimal
import webbrowser
import hashlib
import peewee
from peewee import fn
import jinja2
from apscheduler.schedulers.background import BackgroundScheduler
from flask_mail import Mail, Message
from flask import Flask, render_template, request, make_response, flash, url_for, redirect
from urllib.parse import quote
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


def check_authenticated_make_challenge():
    if request.cookies.get('make_challenge') == os.environ.get('CHALLENGE_KEY'):
        return True
    else:
        return False


def get_participant_from_hash():
    for iter_participant in models.Participant.select():
        if hashlib.sha224(str(iter_participant.id).encode('utf-8')).hexdigest() == request.cookies.get('ParticipantID'):
            return iter_participant
    return None


@app.route('/robots.txt')
def robots():
    return make_response(render_template('robots.txt'))


@app.route('/')
def index():
    # if request.cookies.get('first') is None:
    #     resp = make_response(render_template('about.html', popup=True))
    #     resp.set_cookie('first', 'True', max_age=15552000)
    #     # return resp

    authenticated = check_authenticated()
    make_challenge = check_authenticated_make_challenge()

    challenges_content = models.Challenge.select().where(models.Challenge.URL != '').order_by(fn.Random())
    challenges_empty = models.Challenge.select().where(models.Challenge.URL == '').order_by(fn.Random())
    challenges = challenges_content + challenges_empty

    total = 0
    total_weekly = 0
    met_challenges = 0
    challenges_raising = 0
    for challenge in challenges:
        money = challenge.MoneyRaised
        if challenge.id != 1:
            if money > 0:
                challenges_raising += 1
            if money >= 75:
                met_challenges += 1

    week_ago = datetime.date.today() - datetime.timedelta(days=7)
    for donation in models.Donation.select():
        total += donation.Amount
        if donation.Timestamp > datetime.datetime.combine(week_ago, datetime.time(0, 0)):
            total_weekly += donation.Amount

    startdate = datetime.date(2021, 1, 4)
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

    ordered_challenges = models.Challenge.select().where(models.Challenge.id != 1)\
        .order_by(models.Challenge.MoneyRaised.desc())
    topChallenges = []

    try:
        topChallenges = ordered_challenges[:6]
    except:
        pass

    my_challenges = []

    try:
        try:
            for iter_participant in models.Participant.select():
                participant = get_participant_from_hash()

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

    print(make_challenge)

    donations = models.Donation.select().order_by(models.Donation.Timestamp.desc())

    # Assuming 75% of donations have gift aid
    total = float(total) + ((0.85 * float(total)) * 0.25)
    total_weekly = float(total_weekly) + ((0.85 * float(total_weekly)) * 0.25)
    progress = int((total / 7500) * 100)

    resp = make_response(render_template('index.html', total=total, met_challenges=met_challenges, days=days.days,
                                         days_colour=colour, days_text=days_text, authenticated=authenticated,
                                         challenges=challenges, progress=progress, topChallenges=topChallenges,
                                         my_challenges=my_challenges, support_challenge_id=support_challenge.id,
                                         popup=popup, make_challenge=make_challenge, donations=donations,
                                         total_weekly=total_weekly, challenges_raising=challenges_raising))

    if not popup:
        resp.set_cookie('first', 'True', max_age=15552000)

    return resp


@app.route('/login', methods=['GET', 'POST'])
def login():
    # redirect if already authenticated
    if check_authenticated() and check_authenticated_make_challenge():
        return redirect(url_for('index'))

    if request.method == 'POST':
        password = request.form.get('password')
        if password == os.environ.get('ACCESS_PASS'):
            resp = make_response(redirect(url_for('index')))
            resp.set_cookie('authenticated', os.environ.get('LOGIN_KEY'), max_age=7200)
            resp.set_cookie('make_challenge', os.environ.get('CHALLENGE_KEY'), max_age=7200)
            try:
                if 0 < len(request.cookies.get('ParticipantID')) <= 3:
                    old_value = request.cookies.get('ParticipantID')
                    resp.set_cookie('ParticipantID', hashlib.sha224(str(old_value).encode('utf-8')).hexdigest())
                resp.delete_cookie('email')
                resp.delete_cookie('name')
            except:
                pass
            flash('You will be logged in to view restricted data and make challenges for 2h', 'success')
            return resp
        elif password == '':
            flash('A password is required', 'error')
        elif password == os.environ.get('ADMIN_PASS'):
            resp = make_response(redirect(url_for('admin')))
            resp.set_cookie('admin', os.environ.get('ADMIN_KEY'), max_age=7200)
            resp.set_cookie('authenticated', os.environ.get('LOGIN_KEY'), max_age=7200)
            resp.set_cookie('make_challenge', os.environ.get('CHALLENGE_KEY'), max_age=7200)
            flash('You will be logged in as admin', 'success')
            return resp
        elif password == os.environ.get('CHALLENGE_PASS'):
            resp = make_response(redirect(url_for('index')))
            resp.set_cookie('make_challenge', os.environ.get('CHALLENGE_KEY'), max_age=7200)
            flash('You will be logged in to make challenges for 2h', 'success')
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
        hash_id = str(participant.id).encode('utf-8')
        resp.set_cookie('ParticipantID', hashlib.sha224(hash_id).hexdigest(), max_age=15552000)
        print(hashlib.sha224(hash_id).hexdigest())
        return resp

    else:
        try:
            participant = get_participant_from_hash()
            form.Name.data = participant.Name
            form.Email.data = participant.Email
        except:
            pass
        return render_template('create_challenge.html', form=form, function='Create')


@app.route('/donate', methods=['GET'])
def donate_general():
    flash('This is a general donation, not linked to a specific challenge.', 'error')
    return redirect('/donate/1')


@app.route('/donate/<int:challengeid>', methods=['GET', 'POST'])
def donate(challengeid):
    if not challengeid:
        flash('This is a general donation, not linked to a specific challenge.', 'error')
        challenge = models.Challenge.get_challenge_by_id(1)
    else:
        challenge = models.Challenge.get_challenge_by_id(challengeid)
    charity_message = request.args.get('charity')
    print(charity_message)

    if request.method == 'POST':
        money = round(float(request.form.get('Donation')), 3)
        if money == 0:
            flash('You cannot pledge to donate £0', 'error')
        else:
            if charity_message is None:
                print('calculating least donated challenge')
                charity = models.Donation.get_lowest_charity()
            else:
                charity = charity_message
            if charity == 'Grassroots':
                charityid = 249633
            elif charity == 'Buglife':
                charityid = 187874
            else:
                charityid = 129035
            print('redirecting to link')
            message = request.form.get('Message')[:200]
            temp_message = models.TempMessage.create(Message=message)
            message = temp_message.id
            print(message)
            return redirect('http://link.justgiving.com/v1/charity/donate/charityId/{}?amount={}&currency='
                            'GBP&reference=BC&exitUrl=https%3A%2F%2Fwww.aldrich75.co.uk%2Fdonated%3Famount%3D{}'
                            '%26charity%3D{}%26challengeid%3D{}%26message%3D{}%26jgDonationId%3DJUSTGIVING-DONATION-ID'
                            .format(charityid, money, money, charity, challengeid, message))

    return render_template('donate.html', challenge=challenge, charity=charity_message)


@app.route('/donated')
def donated():
    try:
        amount = request.args.get('amount')
        charity = request.args.get('charity')
        challengeid = request.args.get('challengeid')
        challenge = models.Challenge.get(models.Challenge.id == challengeid)
        message = request.args.get('message')
        print(message)

        message_string = models.TempMessage.select(models.TempMessage.Message).where(models.TempMessage.id == int(message))

        try:
            donation = models.Donation.create(Challenge=challenge, Amount=amount, Charity=charity, message=message_string)
        except:
            flash('There was an error recording your donation, please email aldrichhouse75@gmail.com', 'error')
            return redirect(url_for('index'))

        challenge.update_money_raised_by(amount)

        flash('Your donation of £{} to {} has been successfully recorded'.format(amount, charity), 'success')

        try:
            participant = models.Participant.get().where(models.Participant.id == 1)
            msg = Message('New Donations', sender='"Aldrich 75 <aldrichhouse75@gmail.com>"',
                          recipients=['george.waller3@gmail.com'])
            message = "A donation of {} has been given to {}. Message: {}".format(donation.Amount, donation.Charity, donation.message)
            msg.html = render_template('emails/default_bulk.html', participant=participant,
                                       title='New Donation', message=message, bulk=False)
            mail.send(msg)
        except:
            pass

        return redirect(url_for('index'))

    except:
        flash('There was an error recording your donation, please email aldrichhouse75@gmail.com', 'error')
        return redirect(url_for('index'))


@app.route('/admin')
def admin():
    if check_authenticated_admin():
        users = models.Participant.get_participants().order_by(models.Participant.id)
        challenges = models.Challenge.get_challenges().order_by(models.Challenge.Participant)

        grassrootstotal = 0
        amazetotal = 0
        buglifetotal = 0
        for donation in models.Donation.select():
            if donation.Charity == 'Grassroots':
                grassrootstotal += float(donation.Amount)
            elif donation.Charity == 'Amaze':
                amazetotal += float(donation.Amount)
            elif donation.Charity == 'Buglife':
                buglifetotal += float(donation.Amount)

        return render_template('admin.html', users=users, challenges=challenges,
                               donations=models.Donation.select().order_by(models.Donation.Timestamp),
                               grassrootstotal=grassrootstotal, amazetotal=amazetotal, buglifetotal=buglifetotal)
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
        participandid = get_participant_from_hash()
        participant = models.Participant.get(models.Participant.id == participandid)
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


@app.route('/logout')
def logout():
    resp = make_response(redirect(url_for('index')))
    resp.delete_cookie('make_challenge')
    resp.delete_cookie('authenticated')
    resp.delete_cookie('admin')
    return resp


@app.route('/donation-options')
def donation_options():
    return redirect(url_for('about'))


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


@app.route('/about')
def about():
    return render_template('about.html', popup=False, support_challenge_id=1)


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

    # models.Donation.delete().where(models.Donation.message == 'Test Message').execute()

    """Email Task"""
    # try:
    #     task_time = datetime.datetime(2020, 11, 27, 8, 40, 0, 0)
    #     print(task_time)
    #     task = models.BulkEmailTask.create(Task_Name='Welcome Aldrich', Task_Message='message', DateTime=task_time, Template='emails/welcome_email.html', Done=False)
    #     print('created email task')
    # except:
    #     pass

    # models.Participant.update({models.Participant.Name: 'Mr\tTomlin'}).where(models.Participant.id == 1236).execute()

    # Bulk Email scheduler
    # scheduler = BackgroundScheduler()
    # scheduler.add_job(func=bulk_email_checker, trigger="interval", seconds=60)
    # scheduler.start()
    # print('started scheduler')

    """check emails on program start"""
    # bulk_email_checker()
    #
    # atexit.register(lambda: scheduler.shutdown())
