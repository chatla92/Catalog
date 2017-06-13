from flask import Flask, render_template, request, redirect, jsonify, url_for
from flask import make_response, flash
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Products, Reviews, Categories, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json

import requests
from flask.ext.httpauth import HTTPBasicAuth

app = Flask(__name__)
auth = HTTPBasicAuth()

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog Application"

# Connect to Database and create database session
engine = create_engine('sqlite:///1_electronics_catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Login Page


@app.route('/login', methods=['GET', 'POST'])
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    if request.method == 'POST':
        username = request.form['name']
        password = request.form['password']
        if username is None or password is None:
            flash('Username or password cannot be empty')
            return redirect('/login')

        try:
            user = session.query(User).filter_by(name=username).one()
        except:
            flash('User does not exist')
            return redirect('/login')

        if verify_password(username, password):
            login_session['username'] = username
            login_session['user_id'] = user.id
            flash('Logged in succesfully')
            return redirect('/catalog')
        flash('Entered Credentials are wrong')
        return redirect('/catalog')
    return render_template('login.html', STATE=state)


@auth.verify_password
def verify_password(username, password):
    user = session.query(User).filter_by(name=username).first()
    if not user or not user.verify_password(password):
        return False
    return True

# Add a new user


@app.route('/users/add', methods=['GET', 'POST'])
def new_user():
    if request.method == 'GET':
        return render_template('user_add.html')
    if request.method == 'POST':
        username = request.form['name']
        password = request.form['password']
        email = request.form['email']
        if username is None or password is None or email is None:
            flash('Username or password cannot be empty')
            return redirect('/login')

        if session.query(User).filter_by(name=username).first() is not None:
            flash('user already exists')
            return redirect('/login')

        user = User(name=username, email=email)
        user.hash_password(password)
        session.add(user)
        session.commit()
        user = session.query(User).filter_by(name=username).first()
        login_session['username'] = username
        login_session['user_id'] = user.id
        flash('User created succesfully')
        return redirect('/catalog')

# Google login


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is'
                                            'already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id
    login_session['credentials'] = credentials
    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;' \
              '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# Google disconnect


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['credentials']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCatalog'))
    else:
        del login_session['username']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCatalog'))


# Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
        'email'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# JSON APIs
@app.route('/catalog/<int:cat>/JSON')
@auth.login_required
def ProductsInCatalogJSON(cat):
    products = session.query(Products).filter_by(cat_id=cat).all()
    return jsonify(Products=[p.serialize for p in products])


@app.route('/catalog/<int:cat>/products/<int:product_id>/JSON')
@auth.login_required
def productJSON(cat, product_id):
    product = session.query(Products).filter_by(id=product_id).one()
    return jsonify(Menu_Item=product.serialize)


@app.route('/catalog/JSON')
@auth.login_required
def CatalogJSON():
    categories = session.query(Products.category).group_by(
        Products.category).all()
    return jsonify(categories=[c.category for c in categories])

# Home Page


@app.route('/')
@app.route('/catalog/')
def showCatalog():
    prods = session.query(Products).order_by(desc(Products.id)).limit(10).all()
    categories = session.query(Products).group_by(Products.category).all()
    if 'username' not in login_session:
        return render_template('public_catalog.html', products=prods,
                               categories=categories)
    else:
        return render_template('catalog.html', products=prods,
                               categories=categories,
                               user=login_session['username'])

# List all the products in a category


@app.route('/catalog/<int:categ_id>/')
def showProductsinCategory(categ_id):
    products = session.query(Products).filter_by(cat_id=categ_id).all()
    category = session.query(Categories).filter_by(id=categ_id).one()
    if 'username' not in login_session:
        return render_template('public_category.html',
                               cat=category.name, products=products)
    else:
        return render_template('category.html', cat=category.name,
                               products=products,
                               user=login_session['username'])

# Display Information of a product


@app.route('/catalog/<int:categ_id>/products/<int:product_id>')
def showProduct(categ_id, product_id):
    product = session.query(Products).filter_by(id=product_id).one()
    reviews = session.query(Reviews).filter_by(id=product_id).all()
    creator = getUserInfo(product.user_id)
    name = {}
    for r in reviews:
        name[r.id] = session.query(User).filter_by(id=r.user_id).one().name
    if 'username' not in login_session:
        flash("You are not logged in to edit the item")
        return render_template('product_show_public.html',
                               item=product, reviews=reviews, names=name)
    if creator.id != login_session['user_id']:
        flash("You don't have permission to edit the item")
        return render_template('product_show_public.html',
                               item=product, reviews=reviews, names=name)
    else:
        return render_template('product_show.html',
                               item=product, reviews=reviews, names=name,
                               user=login_session['username'])

# Add a new product


@app.route('/catalog/new', methods=['GET', 'POST'])
def newProduct():
    if 'username' not in login_session:
        flash('Please Login to create new item')
        return redirect('/login')
    if request.method == 'POST':
        new_product = Products(
            name=request.form['name'], category=request.form['category'],
            desc=request.form['decsription'],
            url=request.form['url'],
            img=request.form['img'], user_id=login_session['user_id'])
        session.add(new_product)
        flash('New Item %s Successfully Created' % new_product.name)
        session.commit()
        return redirect(url_for('showCatalog'))
    else:
        return render_template('new_product.html')

# Edit a product


@app.route('/catalog/<int:categ_id>/products/<int:product_id>/edit',
           methods=['GET', 'POST'])
def editProduct(categ_id, product_id):
    if 'username' not in login_session:
        flash('Please Login to edit item')
        return redirect('/login')
    editedItem = session.query(Products).filter_by(id=product_id).one()

    if login_session['user_id'] != editedItem.user_id:
        return ("<script>function myFunction() {alert('You are not authorized"
                " to edit this product. '); window.location = '/catalog/" +
                str(categ_id) + "/products/" + str(product_id) +
                "';}</script><body onload='myFunction()''>")
    if request.method == 'POST':
        if request.form['name']:
            session.query(Products).filter_by(id=product_id).update(
                {Products.name: request.form['name']})
        if request.form['description']:
            session.query(Products).filter_by(id=product_id).update(
                {Products.desc: request.form['description']})
        if request.form['category']:
            session.query(Products).filter_by(id=product_id).update(
                {Products.category: request.form['category']})
        if request.form['url']:
            session.query(Products).filter_by(id=product_id).update(
                {Products.url: request.form['url']})
        if request.form['img']:
            session.query(Products).filter_by(id=product_id).update(
                {Products.url: request.form['img']})
        session.add(editedItem)
        session.commit()
        flash('Menu Item Successfully Edited')
        return redirect('/catalog/' + str(categ_id) + '/products/' +
                        str(product_id))
    else:
        return render_template('edit_product.html',
                               product_id=product_id, item=editedItem)


# Delete a product


@app.route('/catalog/<int:categ_id>/products/<int:product_id>/delete',
           methods=['GET', 'POST'])
def deleteProduct(categ_id, product_id):
    if 'username' not in login_session:
        flash('Please Login to delete item')
        return redirect('/login')

    ItemToDelete = session.query(Products).filter_by(id=product_id).one()
    if login_session['user_id'] != ItemToDelete.user_id:
        return ("<script>function myFunction() {alert('You are not authorized "
                "to delete this product. '); window.location = '/catalog/" +
                str(categ_id) + "/products/" + str(product_id) +
                "';}</script><body onload='myFunction()''>")

    if request.method == 'POST':
        session.delete(ItemToDelete)
        session.commit()
        flash('Menu Item Successfully Deleted')
        return redirect(url_for('showProductsinCategory', categ_id=categ_id))
    else:
        return render_template('delete_product.html', item=ItemToDelete)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
