# Django settings
# Rename this to "settings.py"
import os
TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), 'templates/'))
TEMPLATE_DEBUG = True
DEBUG = True
INSTALLED_APPS = ('customtags')

# Customized settings
ADMINS = ["admin@yourdomain.com"] # TODO: Move into datastore
DOMAIN = "yourdomain.com"
APP_ID = "your-app-id"
CALENDAR = "your-calendar-address@group.calendar.google.com"

IMPACTS = ["major", "minor", "beta", "experimental", "dogfood"]
PROJECT_STATUSES = ["active", "pilot", "maintenence", "sunset"]
APPROVAL_STATUSES = ["missing", "new", "ack", "approved", "rejected", "waived", "pending"]

# Google API settings
APP_NAME = 'your-app-name'
CONSUMER_KEY = 'your-consumer-key'
CONSUMER_SECRET = 'your-consumer-secret'
SCOPES = ['https://docs.google.com/feeds/',
          'https://apps-apis.google.com/a/feeds/user/',
          'https://www.googleapis.com/auth/userinfo.email',
          'https://www.google.com/calendar/feeds/',
          'https://www.google.com/m8/feeds/profiles']
          
