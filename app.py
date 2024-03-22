from flask import Flask, render_template, redirect, url_for, request, session
from database import get_db
from flask_recaptcha import ReCaptcha
import os
import hashlib
import cred

def hashpass(pwd):
    return hashlib.md5(pwd.encode()).hexdigest()

'''
Quick note on this version of RecaptCha:
Go to: <virtualenv>/lib/python-<version>/site-packages
open flask_recaptcha.py
change:
    from jinja2 import Markup
to:
    from markupsafe import Markup
'''

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['RECAPTCHA_SITE_KEY'] = cred.recaptcha_site_key
app.config['RECAPTCHA_SECRET_KEY'] = cred.recaptcha_secret_key

recaptcha = ReCaptcha(app)

@app.template_filter('nl2br')
def nl2br(item):
    if isinstance(item, str):
        return item.replace('\n','<br>')
    return item

@app.route('/', methods=['GET','POST'])
def home():
    if 'user' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cur = db.cursor()
    sql = 'select id, author, category, quote, rating from quotes'
    cur.execute(sql)
    data = cur.fetchall()
    headers = data[0].keys()
    datalist = []
    for row in data:
        datalist.append(list(row))

    return render_template('index.html', headers=headers, data=datalist)

@app.route('/login', methods=['GET','POST'])
def login():
    if 'user' in session:
        session.pop('user')
    if 'email' in session:
        session.pop('email')
    if 'admin' in session:
        session.pop('admin')

    if request.method == 'POST':
        if recaptcha.verify():
            email = request.form['email']
            password = hashpass(request.form['password'])
            db = get_db()
            cur = db.cursor()
            sql = 'select id, username, email, password, admin from users where email = ? and password = ?'
            cur.execute(sql, [email, password])
            data = cur.fetchone()
            if data == None:
                return render_template('login.html', url=url_for('login'), msg='invalid user or password')
            user = data['username']
            email = data['email']
            admin = int(data['admin'])
            session['user'] = user
            session['email'] = email
            session['admin'] = admin
            return redirect(url_for('home'))


    return render_template('login.html', url=url_for('login'), msg=None)

@app.route('/query', methods=['GET','POST'])
def query():
    if 'user' not in session:
        return redirect(url_for('login'))

    sql = None
    data = None
    headers = None
    if request.method == 'POST':
        sql = request.form['query']
        # only select queries are allowed, so check.
        if len(sql) < 10:
            pass
        elif sql[:6].lower() != 'select':
            pass
        else:
            db = get_db()
            cur = db.cursor()
            try:
                cur.execute(sql)
                results = cur.fetchall()
                if len(results) > 0:
                    headers = results[0].keys()
                    data = list(results)
            except:
                pass
    
    return render_template('query.html', query=sql, headers=headers, data=data)

@app.route('/packaged', methods=['GET','POST'])
def packaged():
    if 'user' not in session:
        return redirect(url_for('login'))

    options = None
    headers = None
    data = None
    if request.method == 'POST':
        query = request.form['query']
        # 1 = everything
        # 2 = all authors
        # 3 = all categories
        # 4 = all inspirational quotes
        # 5 = all humorous quotes
        # 6 = all philosophical quotes
        # 7 = all songs
        # 8 = combo
        if int(query) == 1:
            sql = 'select * from quotes'
        elif int(query) == 2:
            sql = 'select row_number() over(order by author) as No, author from (select distinct(author) from quotes)'
        elif int(query) == 3:
            sql = 'select row_number() over(order by category) as No, category from (select distinct(category) from quotes)'
        elif int(query) == 4:
            sql = "SELECT ROW_NUMBER() over(ORDER BY id) AS NO, author, quote FROM (SELECT id, author, quote FROM quotes WHERE category = 'Inspirational');"
        elif int(query) == 5:
            sql = "SELECT ROW_NUMBER() over(ORDER BY id) AS NO, author, quote FROM (SELECT id, author, quote FROM quotes WHERE category = 'Humorous');"
        elif int(query) == 6:
            sql = "SELECT ROW_NUMBER() over(ORDER BY id) AS NO, author, quote FROM (SELECT id, author, quote FROM quotes WHERE category = 'Philosophical');"
        elif int(query) == 7:
            sql = "SELECT ROW_NUMBER() over(ORDER BY id) AS NO, author, quote FROM (SELECT id, author, quote FROM quotes WHERE category = 'Song');"
        elif int(query) == 8:
            return redirect(url_for('combo'))
        else:
            sql = 'INVALID'

        if sql != 'INVALID':
            db = get_db()
            cur = db.cursor()
            cur.execute(sql)
            data = cur.fetchall()
            headers = data[0].keys()


    options = []
    options.append({'value': 1, 'label': 'All Quotes'})
    options.append({'value': 2, 'label': 'All Authors'})
    options.append({'value': 3, 'label': 'All Categories'})
    options.append({'value': 4, 'label': 'All Inspirational Quotes'})
    options.append({'value': 5, 'label': 'All Humorous Quotes'})
    options.append({'value': 6, 'label': 'All Philosophical Quotes'})
    options.append({'value': 7, 'label': 'All Songs'})
    options.append({'value': 8, 'label': 'combo'})

    return render_template('packaged.html', headers=headers, data=data, options=options)

@app.route('/combo', methods=['GET','POST'])
def combo():
    if 'user' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cur = db.cursor()
    cur.execute('select distinct author from quotes')
    authors = cur.fetchall()
    cur.execute('select distinct category from quotes')
    categories = cur.fetchall()
    quotes = None
    if request.method == 'POST':
        author = request.form['author']
        category = request.form['category']
        rating = request.form['rating']

        params = []
        if author == 'ANY' and category == 'ANY' and rating == 'ANY':
            sql = 'select id, author, category, quote, rating from quotes order by rating desc'
        elif author == 'ANY' and category == 'ANY':
            sql = 'select id, author, category, quote, rating from quotes where rating = ?'
            params.append(int(rating))
        elif author == 'ANY' and rating == 'ANY':
            sql = 'select id, author, category, quote, rating from quotes where category = ?'
            params.append(category)
        elif category == 'ANY' and rating == 'ANY':
            sql = 'select id, author, category, quote, rating from quotes where author = ?'
            params.append(author)
        elif author == 'ANY':
            sql = 'select id, author, category, quote, rating from quotes where category = ? or rating = ?'
            params.append(category)
            params.append(int(rating))
        elif category == 'ANY':
            sql = 'select author, category, quote, rating from quotes where author = ? or rating = ?'
            params.append(author)
            params.append(int(rating))
        elif rating == 'ANY':
            sql = 'select author, category, quote, rating from quotes where category = ? or author = ?'
            params.append(category)
            params.append(author)
        else:
            sql = 'select author, category, quote, rating from quotes where author = ? or category = ? or rating = ?'
            params.append(author)
            params.append(category)
            params.append(int(rating))

        cur.execute(sql, params)
        quotes = cur.fetchall()


    return render_template('combo.html', quotes=quotes, authors=authors, categories=categories)

@app.route('/authors', methods=['GET','POST'])
def authors():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    sql = 'select row_number() over(order by author) as No, author from (select distinct(author) from quotes)'
    cur = db.cursor()
    cur.execute(sql)
    data = cur.fetchall()
    headers = data[0].keys()
    return render_template('authors.html', headers=headers, data=list(data))

@app.route('/categories', methods=['GET','POST'])
def categories():
    if 'user' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cur = db.cursor()
    sql = 'select row_number() over(order by category) as No, category from (select distinct(category) from quotes)'
    cur.execute(sql)
    data = cur.fetchall()
    headers = data[0].keys()

    return render_template('categories.html', headers=headers, data=list(data))

@app.route('/logout', methods=['GET','POST'])
def logout():
    if 'user' in session:
        session.pop('user')
    if 'email' in session:
        session.pop('email')
    if 'admin' in session:
        session.pop('admin')

    return render_template('logout.html')
