# -*- coding: utf-8 -*-
"""
    finalproject
    ~~~~~~~~~~~~

    Server-side application that manages a list of restaurants and its menus.

"""
from flask import Flask, render_template, request, redirect, url_for, flash
from flask import jsonify, make_response
from flask import session as login_session
app = Flask(__name__)
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from database_setup import Base, Restaurant, MenuItem, User
import httplib2
import json
import requests
import random
import string

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu Application"

#: Create session and connect db
engine = create_engine('sqlite:///restaurantMenu.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/disconnect')
def disconnect():
    """ Calls unlog functions depending provider and redirects home """
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['credentials']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash ('Succesfully disconnected')
        return redirect(url_for('showrestaurants'))

@app.route('/fbdisconnect')
def fbdisconnect():
    """ Unlog facebook login function """
    facebook_id = login_session['facebook_id']
    url = 'https://graph.facebook.com/%s/permissions' % facebook_id
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]

@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    """ Login with facebook function """
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token' \
        '&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    userinfo_url = "https://graph.facebook.com/v2.2/me"
    token = result.split("&")[0]
    url = 'https://graph.facebook.com/v2.2/me?%s' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token
    url = 'https://graph.facebook.com/v2.2/me/picture?%s&redirect=0' \
        '&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    login_session['picture'] = data["data"]["url"]
    user_id = getuserid(login_session['email'])
    if not user_id:
        user_id = createuser(login_session)
    login_session['user_id'] = user_id
    output = ''
    output += 'Welcome, '
    output += login_session['username']
    output += '!<br/><br/>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 64px; height: 64px;border-radius: 32px;' \
        ' -webkit-border-radius: 32px;-moz-border-radius: 32px;"> '
    flash("Now logged in as %s" % login_session['username'])
    return output

@app.route('/gdisconnect')
def gdisconnect():
    """ Unlog google login function """
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    cred = json.loads(credentials)
    access_token = cred["access_token"]
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Succesfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response('Failed to revoke token for given user', 400)
        response.headers['Content-Type'] = 'application/json'
        return response

@app.route('/gconnect', methods=['POST'])
def gconnect():
    """ Login with google function """
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps(
            'Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data
    try:
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(json.dumps(
            'Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' 
        % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps(
            "Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps(
            "Token's client ID doesn't match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
            'Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
    login_session['provider'] = 'google'
    login_session['credentials'] = credentials.to_json()
    login_session['gplus_id'] = gplus_id
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = json.loads(answer.text)
    login_session['username'] = data["name"]
    login_session['picture'] = data["picture"]
    login_session['email'] = data["email"]
    user_id = getuserid(login_session['email'])
    if not user_id:
        user_id = createuser(login_session)
    login_session['user_id'] = user_id
    output = ''
    output += 'Welcome, '
    output += login_session['username']
    output += '!<br/><br/>'
    output += '<img src="'
    output += login_session['picture']
    output += '" style = "width: 64px; height: 64px; border-radius: 32px;' \
        ' -webkit-border-radius: 32px; -moz-border-radius: 32px;">'
    flash ("you are now logged in as %s" % login_session['username'])
    return output 

@app.route('/login/')
def showlogin():
    """ Create random state and load login """
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) 
        for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

@app.route('/restaurants/JSON/')
def restaurantsjson():
    """ Creates json of restaraurants """
    restaurants = session.query(Restaurant).all()
    return jsonify(Restaurants=[restaurant.serialize for restaurant in restaurants])


@app.route('/restaurants/<int:restaurant_id>/menu/JSON/')
def restaurantmenujson(restaurant_id):
    """ Creates json of restaurant menu items given restaurant_id """
    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()
    return jsonify(MenuItems=[item.serialize for item in items])


@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/JSON/')
def menuitemjson(restaurant_id, menu_id):
    """ Creates json of restaurant menu item given restaurant_id and menu_id """
    item = session.query(MenuItem).filter_by(id=menu_id).one()
    return jsonify(MenuItem=item.serialize)


@app.route('/')
@app.route('/restaurants/')
def showrestaurants():
    """ Show all restaurants """
    restaurants = session.query(Restaurant).order_by(asc(Restaurant.name)).all()
    if 'username' not in login_session:
        return render_template('publicRestaurants.html', restaurants=restaurants)
    else:
        return render_template('restaurants.html', restaurants=restaurants, 
        login_session=login_session['user_id'])


@app.route('/restaurant/new', methods=['GET', 'POST'])
def newrestaurant():
    """ Create a new restaurant """
    if request.method == 'POST':
        newRestaurant = Restaurant(name=request.form["name"],
            user_id=login_session['user_id'])
        session.add(newRestaurant)
        session.commit()
        flash("%s restaurant succesfully created" % request.form["name"])
        return redirect(url_for('showrestaurants'))
    else:
        return render_template('newRestaurant.html')


@app.route('/restaurant/<int:restaurant_id>/edit/', methods=['GET', 'POST'])
def editrestaurant(restaurant_id):
    """ Edit restaurant """
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if restaurant.user_id != login_session['user_id']:
        return "<script>function myFunction() {" \
            "alert('You are not authorized to perform this action');" \
            "window.location = '/'}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form["name"]:
            restaurant.name = request.form["name"]
        session.add(restaurant)
        session.commit()
        flash("%s restaurant succesfully edited" % restaurant.name)
        return redirect(url_for('showrestaurants'))
    else:
        return render_template('editRestaurant.html', restaurant=restaurant)


@app.route('/restaurant/<int:restaurant_id>/delete/', methods=['GET', 'POST'])
def deleterestaurant(restaurant_id):
    """ Delete restaurant """
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    menuItems = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()
    if 'username' not in login_session:
        return redirect('/login')
    if restaurant.user_id != login_session['user_id']:
        return "<script>function myFunction() {" \
            "alert('You are not authorized to perform this action');" \
            "window.location = '/'}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        for item in menuItems:
            session.delete(item)
        session.delete(restaurant)
        session.commit()
        flash("%s restaurant succesfully deleted" % restaurant.name)
        return redirect(url_for('showrestaurants'))
    else:
        return render_template('deleteRestaurant.html', restaurant=restaurant)


@app.route('/restaurant/<int:restaurant_id>/')
def showmenu(restaurant_id):
    """ Show restaurant menu restaurant_id given """
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    creator = getuserinfo(restaurant.user_id)
    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('publicmenu.html', restaurant=restaurant, 
            items=items, creator=creator)
    else:       
        return render_template('menu.html', restaurant=restaurant, 
            items=items, creator=creator)


@app.route('/restaurants/<int:restaurant_id>/new/', methods=['GET', 'POST'])
def newmenuitem(restaurant_id):
    """ Create a new menu in a restaurant restaurant_id given """
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if restaurant.user_id != login_session['user_id']:
        return "<script>function myFunction() {" \
            "alert('You are not authorized to perform this action');" \
            "window.location = '/'}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        newItem = MenuItem(
            name=request.form["name"], 
            restaurant_id=restaurant_id,
            user_id=restaurant.user_id,
            description = request.form["description"],
            course = request.form["course"],
            price = request.form["price"])
        session.add(newItem)
        session.commit()
        flash("%s menu item sucessfully created" % request.form["name"])
        return redirect(url_for('showmenu', restaurant_id=restaurant_id))
    else:
        return render_template('newMenuItem.html', restaurant=restaurant)


@app.route('/restaurants/<int:restaurant_id>/<int:menu_id>/edit/', 
    methods=['GET', 'POST'])
def editmenuitem(restaurant_id, menu_id):
    """ Edit menu item from a restaurant menu restaurant_id and menu_id given """
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    item = session.query(MenuItem).filter_by(id=menu_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if restaurant.user_id != login_session['user_id']:
        return "<script>function myFunction() {" \
            "alert('You are not authorized to perform this action');" \
            "window.location = '/'}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            item.name = request.form["name"]
        if request.form['description']:
            item.description = request.form["description"]
        if request.form['price']:
            item.price = request.form["price"]
        if request.form['course']:
            item.course = request.form["course"]
        session.add(item)
        session.commit()
        flash("%s menu item succesfully edited" % item.name)
        return redirect(url_for('showmenu', restaurant_id=restaurant_id))
    else:
        return render_template('editMenuItem.html', restaurant=restaurant, item=item)


@app.route('/restaurants/<int:restaurant_id>/<int:menu_id>/delete/', 
    methods=['GET', 'POST'])
def deletemenuitem(restaurant_id, menu_id):
    """ Delete menu item from a restaurant menu restaurant_id and menu_id given """
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    item = session.query(MenuItem).filter_by(id=menu_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if restaurant.user_id != login_session['user_id']:
        return "<script>function myFunction() {" \
            "alert('You are not authorized to perform this action');" \
            "window.location = '/'}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(item)
        session.commit()
        flash("%s menu item succesfully deleted" % item.name)
        return redirect(url_for('showmenu', restaurant_id=restaurant_id))
    else:
        return render_template('deleteMenuItem.html', restaurant=restaurant, item=item)
    return "page to delete item from menu"


def getuserid(email):
    """ Returns user.id for a given email """
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


def getuserinfo(user_id):
    """ Returns user of a given user_id """
    user = session.query(User).filter_by(id=user_id).one()
    return user

def createuser(login_session):
    """ Create new user given login_session """
    newUser = User(name = login_session['username'], 
        email = login_session['email'],
        picture = login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email = login_session['email']).one()
    return user.id


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
