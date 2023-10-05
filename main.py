from gevent import monkey
monkey.patch_all()

import scrapetube
import os
import math
import random
import requests

from flask import Flask, redirect, url_for, render_template, flash, request, jsonify
from gevent.pywsgi import WSGIServer
from flask_compress import Compress
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc, func, or_, and_
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from datetime import datetime, date

base_url = 'http://localhost'
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///studyclique.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SECRET_KEY'] = 'WRYTG^&W*R'
app.config['SQLALCHEMY_SILENCE_UBER_WARNING'] = 1
app.static_folder = 'static'

app.config['MAIL_SERVER'] = 'mail.privateemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'mailer@maxtan.co'
app.config['MAIL_PASSWORD'] = 'pbkpbk2004'

mail = Mail(app)
login_manager = LoginManager(app)
db = SQLAlchemy(app)

def gen_password(length: int):
  chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@#$%^&*()[]'
  pw = ''
  for i in range(length):
    pw += random.choice(list(chars))

  return pw


class User(UserMixin, db.Model):
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(20), unique=True, nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    first = db.Column(db.String(20), nullable=False)
    last = db.Column(db.String(20), nullable=False)
    groups = db.Column(db.String(20))
    avatar = db.Column(db.String)
    bio = db.Column(db.String, nullable=True)
    website = db.Column(db.String, nullable=True)

class ChatMessage(UserMixin, db.Model):
  __tablename__ = 'ChatMessage'
  id = db.Column(db.Integer, primary_key=True)
  sender = db.Column(db.String, nullable=False)
  recipient = db.Column(db.String,  nullable=True)
  group = db.Column(db.String,  nullable=True)
  timestamp = db.Column(db.String, nullable=False)
  message = db.Column(db.String, nullable=False)

class GroupMembers(UserMixin, db.Model):
  __tablename__ = 'GroupMembers'
  username = db.Column(db.String, primary_key=True, nullable=False)
  group = db.Column(db.String,  nullable=False)

class Blog(UserMixin, db.Model):
  __tablename__ = 'Blog'
  name = db.Column(db.String, primary_key=True, unique=True, nullable=False) 
  filename = db.Column(db.String, unique=True, nullable=False) 
  category = db.Column(db.String, nullable=False) 
  author = db.Column(db.String, nullable=False) 
  timestamp = db.Column(db.String, nullable=False) 

class Author(UserMixin, db.Model):
  __tablename__ = 'Author'
  name = db.Column(db.String, primary_key=True, unique=True, nullable=False) 
  avatar = db.Column(db.String, nullable=False) 
  desc = db.Column(db.String, nullable=False) 

class Newsletter(UserMixin, db.Model):
    __tablename__ = 'Newsletter'
    timestamp = db.Column(db.String, primary_key=True, unique=True)
    news = db.Column(db.String, nullable=False)
    tips = db.Column(db.String, nullable=False)

class Email(UserMixin, db.Model):
    __tablename__ = 'Email'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(20), unique=True, nullable=False)

class Group(UserMixin, db.Model):
    __tablename__ = 'Group'
    id = db.Column(db.Integer, unique=True, primary_key=True)
    creator = db.Column(db.String, nullable=False)
    name = db.Column(db.String, unique=True, nullable=False)
    desc = db.Column(db.String, nullable=False) 
    field = db.Column(db.String, nullable=False) 
    approved = db.Column(db.Boolean, default=False, nullable=False)
    members = db.Column(db.Integer, default=1)

with app.app_context():
    db.create_all()

def generate_timestamp():
    now = datetime.now()
    timestamp = now.strftime("%d %b, %Y")
    return timestamp
  
@login_manager.user_loader
def load_user(user_id):
  return User.query.get(int(user_id))

@app.route('/')
def home():
    groups = Group.query.order_by(Group.members.desc()).limit(5).all()
    avatars = {}
    for group in groups:
      avatars[group.creator] = User.query.filter_by(username=group.creator.lower()).first().avatar
    return render_template('index.html', groups=groups, avatars=avatars)

@app.route('/register/')
def register():
  if not current_user.is_authenticated:
    return render_template('register.html')
  else:
    return redirect(url_for('admin', manage='users'))

@app.route('/register/', methods=['POST'])
def register_request():
  name = request.form.get('fname')
  email = request.form.get('email')
  username = request.form.get('username')
  password = gen_password(15)

  invalid = ' !@#$%^&*()`-=_+[]{}\|;:,./<>?'
  if len(list(username)) < 7:
    flash('Username is too short, must be at least 8 characters')
    return redirect(url_for('register'))
  for char in list(invalid):
    if char in username:
      flash('Invalid username')
      return redirect(url_for('register'))
  if '"' in username:
    flash('Invalid username')
    return redirect(url_for('register'))
  if "'" in username:
    flash('Invalid username')
    return redirect(url_for('register'))
  test = User.query.filter_by(username=username.lower()).first()

  for email_ in Email.query.all():
    if email == email_.email:
      flash('That email is already used')
      return redirect(url_for('register'))

  if '.' not in email:
    flash('Invalid email')
    return redirect(url_for('register'))
  if '@' not in email:
    flash('Invalid email')
    return redirect(url_for('register'))

  if test is None:
    user = User(first=name.split()[0], last=name.split()[1], email=email, username=username.lower(), password=password, avatar='https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png')
    db.session.add(user)
    db.session.commit()

    recipient = email
    subject = 'StudyClique - Account Creation'
    body = f'Username: {username}\nPassword: {password}'

    msg = Message(subject=subject, sender=app.config['MAIL_USERNAME'], recipients=[recipient], body=body)

    mail.send(msg)
    flash('Account created! You\'re password has been emailed to you.')
    return redirect(url_for('login'))
  else:
    flash('Username is taken.')
    return redirect(url_for('register'))
  

@app.route('/login/')
def login():
  if not current_user.is_authenticated:
    return render_template('login.html')
  else:
    return redirect(url_for('admin', manage='users'))

@app.route('/login/', methods=['POST'])
def login_request():
  username = request.form.get('fname')
  password = request.form.get('pwd')
  try:
    user = User.query.filter_by(username=username).first()
    if (user.username == username) and (user.password == password):
      user = User(id=user.id, username=username, password=password, first=user.first, last=user.last, groups=user.groups)
      login_user(user)
      return redirect(url_for('admin', manage='users'))
    else:
      flash('Invalid credentials')
      return redirect(url_for('login'))
  except Exception as e:
    print(e)
    flash('Invalid credentials')
    return redirect(url_for('login'))

@app.route('/panel/<manage>')
@login_required
def admin(manage):
  if current_user.username == 'max':
    if manage == 'users':
      users = User.query.all()
      for user in users:
        user.realpw = user.password
        pw = ''
        for i in list(user.password):
          pw += '*'
        user.password = pw
      return render_template('admin.html', users=users)

    if manage == 'newsletter':
      emails = Email.query.all()
      return render_template('admin2.html', emails=emails)

    if manage == 'blog':
      return render_template('admin3.html', authors=Author.query.all(), posts=Blog.query.all())

    if manage == 'groups':
      return render_template('admin4.html', groups=Group.query.all())
  else:
    return redirect(url_for('dashboard'))

@app.route('/dashboard/')
@login_required
def dashboard():
    chats = ChatMessage.query.filter_by(sender=current_user.username.lower()).all()
    chats_ = ChatMessage.query.filter_by(recipient=current_user.username.lower()).all()
    recipients = []

    for chat in chats:
        user = User.query.filter_by(username=chat.recipient.lower()).first()
        if [user.username, user.avatar] not in recipients:
            recipients.append([user.username, user.avatar])

    for chat in chats_:
        user = User.query.filter_by(username=chat.sender.lower()).first()
        if [user.username, user.avatar] not in recipients:
            recipients.append([user.username, user.avatar])

    return render_template('dashboard.html', recipients=recipients, User=User)

@app.route('/dashboard/editprofile/')
@login_required
def editprofile():
  return render_template('editprofile.html')

def is_today(date_string):
    # Convert the date string to a datetime object
    date_format = "%m/%d/%Y"
    date_object = datetime.strptime(date_string, date_format).date()

    # Get the current date
    current_date = date.today()

    # Compare if the date part of the datetime object is the same as the current date
    return date_object == current_date

@app.route('/dashboard/chat/')
@login_required
def chatbox():
    # Common Table Expression (CTE) to get the latest messages for each sender
    latest_messages_cte = db.session.query(ChatMessage.sender,
                                           ChatMessage.recipient,
                                           func.max(ChatMessage.id).label('max_id')) \
      .filter(or_(ChatMessage.sender == current_user.username.lower(),
                  ChatMessage.recipient == current_user.username.lower())) \
      .group_by(ChatMessage.sender, ChatMessage.recipient) \
      .subquery()

    # Join the ChatMessage table with the CTE to get the latest messages
    latest_messages = db.session.query(ChatMessage).join(latest_messages_cte,
                                                         ChatMessage.id == latest_messages_cte.c.max_id) \
                                                  .all()

    # Collect the recipient information and the last message from each sender
    recipients = []
    for chat in latest_messages:
        print(chat.sender, chat.recipient, chat.message)
        user = User.query.filter_by(username=chat.sender.lower()).first()
        i = 0
        if user.username != current_user.username:

            for recipient in recipients:
                if recipient[0] == user.username:
                    recipients.pop(i)
                i += 1

            recipients.append([user.username, user.avatar, chat.message, user.email])
        elif user.username == current_user.username and chat.recipient != current_user.username:
            user = User.query.filter_by(username=chat.recipient.lower()).first()

            for recipient in recipients:
                if recipient[0] == user.username:
                    recipients.pop(i)
                i += 1

            recipients.append([user.username, user.avatar, chat.message, user.email])

    print(recipients)
    messages = ChatMessage.query.filter(
        or_(
            and_(ChatMessage.sender == current_user.username, ChatMessage.recipient == recipients[0][0]),
            and_(ChatMessage.sender == recipients[0][0], ChatMessage.recipient == current_user.username)
        )
    ).all()
    def_messages = []

    for message in messages:
        if message.sender == current_user.username:
            if is_today(message.timestamp.split()[0]):
                def_messages.append(['right', message.message, message.timestamp.split()[1] + ' ' + message.timestamp.split()[2]])
            else:
                def_messages.append(['right', message.message, message.timestamp])
        else:
            if is_today(message.timestamp.split()[0]):
                def_messages.append(['left', message.message, message.timestamp.split()[1] + ' ' + message.timestamp.split()[2]])
            else:
                def_messages.append(['left', message.message, message.timestamp])

    groups = User.query.filter_by(username=current_user.username).first().groups
    print(groups)
    if str(groups) != 'None':
        groups = groups.split(',')
    else:
        groups = ''

    return render_template('chat.html', recipients=recipients, def_messages=def_messages, groups=groups)

@app.route('/check_username/', methods=['POST'])
@login_required
def check_username():
  username = request.form.get('username')
  user = User.query.filter_by(username=username).first()
  exists = user is not None
  if username.lower() == current_user.username.lower():
    exists = False
  response = {'exists': exists, 'avatar': user.avatar}
  return jsonify(response)

@app.route('/retrieve_user/', methods=['POST'])
def retrieve_user():
    username = request.form.get('username')
    user = User.query.filter_by(username=username).first()
    response = {'username': user.username, 'avatar': user.avatar}
    return jsonify(response)


@app.route('/retrieve_messages/', methods=['POST'])
@login_required
def retrieve_messages():
    sender = request.form.get('sender')
    recipient = request.form.get('recipient')

    # Query the database using sender and recipient
    messages = ChatMessage.query.filter(
        (ChatMessage.sender == sender) | (ChatMessage.recipient == sender)
    ).filter(
        (ChatMessage.sender == recipient) | (ChatMessage.recipient == recipient)
    ).all()

    # Convert messages to a serializable format
    serialized_messages = []
    for message in messages:
        if is_today(message.timestamp.split()[0]):
            message.timestamp = message.timestamp.split()[1] + ' ' + message.timestamp.split()[2]
        if message.sender == current_user.username:
            alignment = 'right'
        else:
            alignment = 'left'
        serialized_message = {
            'sender': message.sender,
            'recipient': message.recipient,
            'timestamp': message.timestamp,
            'message': message.message,
            'alignment': alignment,
            'avatar': User.query.filter_by(username=message.sender).first().avatar
        }
        serialized_messages.append(serialized_message)

    return jsonify(messages=serialized_messages)  # Return the serialized messages as JSON response


@app.route('/fetch_user/<username>', methods=['GET'])
def fetch_user(username):
    user = User.query.filter_by(username=username.lower()).first()

    user_data = {
        "username": user.username,
        "avatar": user.avatar,
        "email": user.email
    }

    return jsonify(user_data)

@app.route('/send_message/', methods=['POST'])
@login_required
def send_message():
    sender = request.form.get('sender')
    recipient = request.form.get('recipient')
    message = request.form.get('message')

    timestamp = datetime.now().strftime("%m/%d/%Y %I:%M %p")
    chatmsg = ChatMessage(sender=sender, recipient=recipient, timestamp=timestamp, message=message)
    db.session.add(chatmsg)
    db.session.commit()
    return {'sender': sender, 'recipient': recipient, 'timestamp': timestamp, 'message': message, 'success': True}


@app.route('/panel/blog/group/delete/', methods=['POST'])
@login_required
def admin_group_delete():
  data = request.get_json()
  name = data['name']

  post = Group.query.filter_by(name=name).first()
  db.session.delete(post)
  db.session.commit()
  return redirect(url_for('admin', manage='groups'))

@app.route('/panel/blog/group/approve/', methods=['POST'])
@login_required
def admin_group_approve():
  data = request.get_json()
  name = data['name']
  group = Group.query.filter_by(name=name).first()
  group.approved = True
  db.session.commit()
  return redirect(url_for('admin', manage='groups'))

@app.route('/panel/blog/group/decline/', methods=['POST'])
@login_required
def admin_group_decline():
  data = request.get_json()
  name = data['name']
  group = Group.query.filter_by(name=name).first()
  db.session.delete(group)
  db.session.commit()
  return redirect(url_for('admin', manage='groups'))

@app.route('/panel/blog/post/create/', methods=['POST'])
@login_required
def admin_blog_create():
  name = request.form.get('name')
  file = request.files['file']
  filename = secure_filename(file.filename)
  file.save(os.path.join(app.root_path, 'templates', filename))
  category = request.form.get('category')
  author = request.form.get('author')

  blog = Blog(name=name.replace(' ','-'), filename=filename, category=category, author=author, timestamp=generate_timestamp())
  db.session.add(blog)
  db.session.commit()

@app.route('/panel/blog/post/delete/', methods=['POST'])
def admin_blog_delete():
  data = request.get_json()
  name = data['name']

  post = Blog.query.filter_by(name=name).first()
  db.session.delete(post)
  db.session.commit()
  return redirect(url_for('admin', manage='blog'))

@app.route('/panel/blog/author/create/', methods=['POST'])
def admin_author_create():
  return ''

@app.route('/blog/')
def collection():
  avatars = []
  posts = Blog.query.all()
  for post in posts:
    author = Author.query.filter_by(name=post.author).first()
    avatars.append(author.avatar)
  
  return render_template('blog.html', posts=Blog.query.all(), avatars=avatars)

@app.route('/blog/search/', methods=['POST'])
def blog_search():
  query = request.form.get('query')
  posts = Blog.query.filter(Blog.name.like(f'%{query}%')).all()

  avatars = []
  for post in posts:
    author = Author.query.filter_by(name=post.author).first()
    avatars.append(author.avatar)

  return render_template('blog.html', posts=posts, avatars=avatars)

@app.route('/blog/filter/', methods=['POST'])
def blog_filter():
  filter = request.form.get('filter')
  posts = Blog.query.filter_by(category=filter).all()

  avatars = []
  for post in posts:
    author = Author.query.filter_by(name=post.author).first()
    avatars.append(author.avatar)
  
  return render_template('blog.html', posts=posts, avatars=avatars)

@app.route('/blog/filtered/<filter>/')
def blog_filtered(filter):
  posts = Blog.query.filter_by(category=filter).all()

  avatars = []
  for post in posts:
    author = Author.query.filter_by(name=post.author).first()
    avatars.append(author.avatar)
  
  return render_template('blog.html', posts=posts, avatars=avatars)

@app.route('/blog/<name>/')
def blog(name):
  try:
    blog = Blog.query.filter_by(name=name).first()
    author = blog.author
    author = Author.query.filter_by(name=author).first()
  
    blogs = Blog.query.order_by(Blog.timestamp.desc()).limit(3).all()
    
    return render_template(blog.filename, author=author.name, avatar=author.avatar, desc=author.desc, blogs=blogs, base=base_url)
  except:
    return redirect(url_for('home'))

@app.route('/blog/preview/')
@login_required
def blogpreview():
  if current_user.username == 'max':
    blogs = Blog.query.order_by(Blog.timestamp.desc()).limit(3).all()
    return render_template('blogpreview.html', blogs=blogs, base=base_url)
  return redirect(url_for('home'))


@app.route('/panel/newsletter/', methods=['POST'])
@login_required
def admin_email_search():
  filter = request.form.get('filter')
  emails = Email.query.filter(Email.email.startswith(filter)).all()
  for email in emails:
    print(email.email)
  return render_template('admin2.html', emails=emails)

@app.route('/dashboard/user/update/', methods=['POST'])
@login_required
def update_user():
    data = request.get_json()
    print(data)

    try:
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if current_password and new_password and confirm_password:
            if current_password != new_password:
                if new_password == confirm_password and len(new_password) >= 10:
                    # Update the user's password (replace this with your actual password update logic)
                    # Example: user.set_password(new_password)
                    user = User.query.filter_by(username=current_user.username).first()
                    user.password = new_password
                    db.session.commit()
                    flash('Password has been updated successfully.', 'success')
                else:
                    if len(new_password) < 10:
                        flash('Password must be at least 10 characters.', 'error')
                    else:
                        flash('New password and confirmation do not match.', 'error')
            else:
                flash('You\'re using your old password.', 'error')
        else:
            flash('Please fill in all password fields.', 'error')
    except Exception as e:
        flash('An error occurred while updating the password. Please try again later.', 'error')
        print(e)

    try:
        firstName = data.get('firstName')
        lastName = data.get('lastName')
        bio = data.get('bio')
        website = data.get('website')

        user = User.query.filter_by(username=current_user.username).first()
        user.first = firstName
        user.last = lastName
        user.bio = bio
        user.website = website

        db.session.commit()
    except:
        pass

    return redirect(url_for('editprofile'))





@app.route('/panel/users/update/', methods=['POST'])
@login_required
def admin_user_update():
  form = request.form.get('form')

  if form == 'admin_user_update':
    id = int(request.form.get('id'))
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')
    first = request.form.get('first')
    last = request.form.get('last')
    groups = request.form.get('groups')
    user = User.query.filter_by(username=username).first()
    if user:
      user.email = email
      user.username = username
      if password != '':
        user.password = password
      user.first = first
      user.last = last
      user.groups = groups
      db.session.commit()
      flash('User has been updated')
    else:
      flash('Error')
    
    return redirect(url_for('admin', manage='users'))
  elif form == 'admin_user_add':
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')
    first = request.form.get('first')
    last = request.form.get('last')

    try:
      test = User.query.filter_by(username=username).first()
      if test is None:
        newUser = User(email=email, username=username, password=password, first=firstName, last=lastName, avatar='https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png')
        db.session.add(newUser)
        db.session.commit()
        return redirect(url_for('admin', manage='users'))
      else:
        return redirect(url_for('admin', manage='users'))
    except Exception as e:
      return redirect(url_for('admin', manage='users'))
    
@app.route('/panel/users/search/', methods=['POST'])
@login_required
def admin_user_search():
  username = request.form.get('username')
  print(username)

  users = User.query.filter(User.username.like(username)).all()
  print(users)
  return render_template('admin.html', users=users)

@app.route('/panel/users/add', methods=['POST'])
@login_required
def admin_user_add():
  data = request.get_json()
  email = data['email']
  username = data['username']
  password = data['password']
  firstName = data['first']
  lastName = data['last']

  test = User.query.filter_by(username=username).first()
  if test is None:
    newUser = User(email=email, username=username, password=password, first=firstName, last=lastName, avatar='https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png')
    db.session.add(newUser)
    db.session.commit()
    return redirect(url_for('admin', manage='users'))
  else:
    return redirect(url_for('admin', manage='users'))

  
@app.route('/panel/users/delete/', methods=['POST'])
@login_required
def admin_user_delete():
  data = request.get_json()
  id = int(data['id'])

  user = User.query.filter_by(id=id).first()
  db.session.delete(user)
  db.session.commit()

  return redirect(url_for('admin', manage='users'))
  
@app.route('/panel/newsletter/add/', methods=['POST'])
@login_required
def admin_newsletter_add():
  data = request.get_json()
  email = data['email']
  
  if (email != '') and ('@' in email):
    newEmail = Email(email=email)
    db.session.add(newEmail)
    db.session.commit()
    return redirect(url_for('admin', manage='newsletter'))
  else:
    flash('Invalid email')
    return redirect(url_for('admin', manage='newsletter'))

@app.route('/panel/newsletter/delete/', methods=['POST'])
@login_required
def admin_newsletter_delete():
  data = request.get_json()
  id = int(data['id'])

  email = Email.query.filter_by(id=id).first()
  db.session.delete(email)
  db.session.commit()
  return redirect(url_for('admin', manage='newsletter'))

@app.route('/panel/newsletter/send/', methods=['POST'])
@login_required
def admin_newsletter_send():
  data = request.get_json()
  print(data)
  news = data['news']
  tips = data['tips']

  emails = Email.query.all()
  subject = 'StudyClique - Weekly Newsletter'
  template = 'newsletter.html'

  timestamp = generate_timestamp()
  for email in emails:
    recipient = email.email
    html_content = render_template(template, news=news, tips=tips, base=base_url, timestamp=timestamp)

    msg = Message(subject=subject, sender=app.config['MAIL_USERNAME'], recipients=[recipient])
    msg.html = html_content
    mail.send(msg)

  print(timestamp)
  newsletter = Newsletter(timestamp=timestamp, news=news, tips=tips)
  db.session.add(newsletter)
  db.session.commit()

  flash('Newsletter has been sent')
  return redirect(url_for('admin', manage='newsletter'))


@app.route('/newsletter/<timestamp>/')
def newsletter(timestamp):
  newsletter = Newsletter.query.filter_by(timestamp=timestamp).first()
  return render_template('newsletter.html', news=newsletter.news, tips=newsletter.tips, timestamp=timestamp)

@app.route('/newsletter/unsubscribe/<email>/')
def newsletter_unsubscribe(email):
  email_ = Email.query.filter_by(email=email).first()
  email = email_

  db.session.delete(email)
  db.session.commit()
  flash('You\'ve unsubscribed from the newsletter')
  return redirect(url_for('home'))

@app.route('/logout/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/protected/')
@login_required
def protected():
    return 'Protected page. User ID: ' + current_user.id

@app.route('/tos/')
def terms_of_service():
  return render_template('tos.html')

@app.route('/privacy/')
def privacy_policy():
  return render_template('policy.html')

@app.errorhandler(404)
@app.route('/error/')
def error_404(url):
  return render_template('404.html')

@app.route('/subscribe/', methods=['POST'])
def subscribe_to_newsletter():
  email_ = request.form.get('email')
  email = db.session.add(Email(email=email_))

  try:
    db.session.commit()
    flash('Thanks for subscribing!')
    return redirect(f"{url_for('home')}#newsletter")
  except:
    flash('You\'ve already subscribed!')
    return redirect(f"{url_for('home')}#newsletter")


@app.route('/')
def explore_auction():
  return ''


@app.route('/')
def contact():
  return 'wr'

@app.route('/')
def live_auction():
  return 'wr'


@app.route('/')
def item_details():
  return 'wr'


@app.route('/')
def activity():
  return 'wr'


@app.route('/')
def about():
  return 'wr'


@app.route('/')
def blog_left_sidebar():
  return 'wr'




@app.route('/')
def author_profile():
  return 'wr'


@app.route('/')
def authors():
  return ''


@app.route('/')
def index():
  return ''


@app.route('/')
def index2():
  return ''


@app.route('/')
def index3():
  return ''



@app.route('/')
def item_ranking():
  return ''

@app.route('/'
           '')
def add_wallet():
  return ''


@app.route('/')
def create_collection():
  return ''


@app.route('/')
def team():
  return ''


@app.route('/')
def testimonials():
  return ''


@app.route('/')
def recover_password():
  return ''


@app.route('/')
def blog_no_sidebar():
  return ''


@app.route('/')
def blog_right_sidebar():
  return ''


@app.route('/')
def blog_details_no_sidebar():
  return ''


@app.route('/')
def blog_details_left_sidebar():
  return ''


@app.route('/')
def blog_details_right_sidebar():
  return ''


@app.route('/study_groups/')
def study_groups():
  groups = Group.query.all()

  return render_template('studygroups.html', groups=groups)


@app.route('/')
def create_study_group():
  return ''

if __name__ == "__main__":
    print('StudyClique is successfully online')
    http_server = WSGIServer(('0.0.0.0', 80), app)
    http_server.serve_forever()
    compress = Compress()
    compress.init_app(app)
    db.create_all()
