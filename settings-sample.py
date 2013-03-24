# Django settings
import os
TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), 'templates/'))
INSTALLED_APPS = ('customtags', 'django.contrib.markup')

TEMPLATE_DEBUG = False # When deployed to production, this should be set FALSE
DEBUG = False # When deployed to production, this should be set FALSE
APP_ID = "your-app-id"
CALENDAR = "your-calendar-address@group.calendar.google.com"

# Customized settings
ADMINS = ["admin@yourdomain.com"] # TODO: Move into datastore
DOMAIN = "yourdomain.com"
BASE_URL = "http://www.yourdomain.com/"

PRODUCT_REVIEWER = "your-reviewer"
ENGINEERING_REVIEWER = "your-reviewer"

# Variables
IMPACTS = ["major", "minor", "beta", "experimental", "dogfood"]
PROJECT_STATUSES = ["active", "pilot", "maintenence", "sunset"]
APPROVAL_STATUSES = ["missing", "new", "ack", "approved", "rejected", "waived", "pending"]
LAUNCH_STATUSES = ["new", "in progress", "completed", "ready", "launched", "cancelled"]

# Google API settings
APP_NAME = 'your-app-name'
CONSUMER_KEY = 'your-consumer-key'
CONSUMER_SECRET = 'your-consumer-secret'
SCOPES = ['https://docs.google.com/feeds/',
          'https://apps-apis.google.com/a/feeds/user/',
          'https://www.googleapis.com/auth/userinfo.email',
          'https://www.google.com/calendar/feeds/',
          'https://www.google.com/m8/feeds/profiles']

# Google Analytics settings
GA = 'UA-########-##'