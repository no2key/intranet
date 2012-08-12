# -*- coding: utf-8 -*-
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app, login_required
from google.appengine.api import users
import gdata.gauth
import gdata.apps.client

import settings
import models
        
class ImportUsers(webapp.RequestHandler):
    def get(self):
        client = gdata.apps.client.AppsClient(domain=settings.DOMAIN)
        client.ssl = True
        current_user = users.get_current_user()
        access_token_key = 'access_token_%s' % current_user.user_id()
        client.auth_token = gdata.gauth.ae_load(access_token_key)
        feed = client.RetrieveAllUsers()
        for entry in feed.entry:
          person = models.Person.get_by_key_name(entry.login.user_name)
          if not person:
            person = models.Person(
              key_name = entry.login.user_name
            )
          email = entry.login.user_name + '@' + settings.DOMAIN
          person.gaia = users.User(email)
          person.email = email
          person.id = entry.login.user_name
          person.given_name = entry.name.given_name
          person.family_name = entry.name.family_name
          if entry.login.suspended == "true":
            person.suspended = True
          else:
            person.suspended = False
          person.put()
          self.response.out.write('User ' + entry.login.user_name + ' created. <br>')
          
def main():
    application = webapp.WSGIApplication([('/admin/import/users', ImportUsers)],
                                         debug=True)
    run_wsgi_app(application)