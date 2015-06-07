# P3: Item Catalog

## Overview

Python server-side application that manages a list of restaurants and its menus.

This program is the third project of the Full Stack Developer Nanodegree from [Udacity](https://www.udacity.com/)

## Requirements

Python (version 2.7)

flask  
Flask-login  
sqlalchemy  
oauth2client  
requests  
httplib2


## Configuration

You can either set up your environment or use a provisioned virtual environment:

#### Setting up the environment

Install the following software requirements:

```
apt-get install python-sqlalchemy
apt-get install python-pip

pip install flask
pip install Flask-Login
pip install oauth2client
pip install requests
pip install httplib2
```

#### Setting up a virtual environment with Vagrant

Set up a virtual environment with a provisioned VM with [vagrant](https://www.vagrantup.com/):

1. Start up a VM as configured by the default Vagrantfile
``` vagrant up ```

2. Ssh into it
``` vagrant ssh ```


## OAuth Configuration

#### Setting up Google authentification:

1. In order to connect with google, you will need to create a project in https://console.developers.google.com/

2. Once a project is created you need to generate OAuth ClientId in credentials

3. Click on ``` download json ``` to download the json file, call it client_secrets.json and store it in your project

4. In login.html give the client id to
``` data-clientid = "YOU_CLIENT_ID" ```


#### Setting up Facebook authentification:

1. In order to connect with facebook, you will need to create an app in https://developers.facebook.com/

2. Create a file and call it fb_client_secrets.json:
```
{
  "web": {
    "app_id": "YOUR_APP_ID",
    "app_secret": "YOUR_APP_SECRET"
  }
}
```

3. In login.html give the appId to
``` appId = "YOUR_APP_ID ```


## Running info

run python dabase_setup.py for setting up the database

run python finalproject.py