# -*- coding: utf-8 -*-
import os
import logging
import webapp2
import time

from django.template.loader import render_to_string
from google.appengine.api import users

import models
import tools.common
import settings
from mc import cache

class BaseRequestHandler(webapp2.RequestHandler):
    """Extension of the normal RequestHandler
    """
    
    def __init__(self, request, response):
      self.initialize(request, response)

      logging.getLogger().setLevel(logging.DEBUG)
      self.init_time = time.time()
      self.user = users.get_current_user()
      self.person = models.Person.from_user(self.user)
      os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

    def __del__(self):
      logging.debug("Handler for %s took %.2f seconds" %
                    (self.request.url, time.time() - self.init_time))
                          
    def check_user(self):
        if not self.person or not self.person.is_setup:
          self.redirect('/signup/step1')
        
    def render(self, template_name, template_values={}, to_string=False):
        # Detect Chrome
        chrome = False
        uastring = self.request.headers.get('user_agent')
        if "Chrome" in uastring:
          chrome = True
        # Preset values for the template
        values = {
          'request': self.request,
          'chrome': chrome,
          'person': self.person,
          'impacts': settings.IMPACTS,
          'project_statuses': settings.PROJECT_STATUSES,
          'product_reviewer': settings.PRODUCT_REVIEWER,
          'engineering_reviewer': settings.ENGINEERING_REVIEWER,
          'domain': settings.DOMAIN,
          'logout_url': users.create_logout_url(self.request.uri),
          'all_persons': cache.get_all_persons(),
          'all_projects': cache.get_all_projects(),
          'all_releases': cache.get_all_releases(),
          'all_active_releases': cache.get_all_active_releases(),
          'all_entries': cache.get_all_entries(),
          'all_active_entries': cache.get_all_active_entries(),
          'all_launched_entries': cache.get_all_launched_entries(),
          'all_cancelled_entries': cache.get_all_cancelled_entries(),
          'calendar': settings.CALENDAR,
          'ga': settings.GA
        }

        # Add manually supplied template values
        values.update(template_values)

        # Render template
        if to_string:
          return render_to_string(template_name, values)
        else:
          self.response.out.write(render_to_string(template_name, values))