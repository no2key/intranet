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
    """Extension of the normal RequestHandler"""
    
    def __init__(self, request, response):
        self.initialize(request, response)
        logging.getLogger().setLevel(logging.DEBUG)
        self.init_time = time.time()
        self.user = users.get_current_user()
        self.person = models.Person.from_user(self.user)
        self.__class__.values = {
            'request': self.request,
            'person': self.person,
            'impacts': settings.IMPACTS,
            'project_statuses': settings.PROJECT_STATUSES,
            'product_reviewer': settings.PRODUCT_REVIEWER,
            'engineering_reviewer': settings.ENGINEERING_REVIEWER,
            'domain': settings.DOMAIN,
            'logout_url': users.create_logout_url(self.request.uri),
            'all_persons': cache.get('all_persons'),
            'all_projects': cache.get('all_projects'),
            'all_releases': cache.get('all_releases'),
            'all_active_releases': cache.get('all_active_releases'),
            'all_active_beta_releases': cache.get('all_active_beta_releases'),
            'all_active_major_releases': cache.get(
                'all_active_major_releases'),
            'all_active_full_releases': cache.get('all_active_full_releases'),
            'all_active_external_releases': cache.get(
                'all_active_external_releases'),
            'all_active_nonexperimental_releases': cache.get(
                'all_active_nonexperimental_releases'),
            'all_launched_releases': cache.get('all_launched_releases'),
            'recent_launched_releases': cache.get('recent_launched_releases'),
            'all_entries': cache.get('all_entries'),
            'all_active_entries': cache.get('all_active_entries'),
            'all_launched_entries': cache.get('all_launched_entries'),
            'all_cancelled_entries': cache.get('all_cancelled_entries'),
            'calendar': settings.CALENDAR,
            'ga': settings.GA
        }
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

        # Add manually supplied template values
        self.__class__.values['chrome'] = chrome
        self.__class__.values.update(template_values)
        
        logging.info('begin to render:' + time.strftime('%H-%M-%S',time.localtime(time.time())))
        # Render template
        if to_string:
            return render_to_string(template_name, self.__class__.values)
        else:
            self.response.out.write(render_to_string(template_name, self.__class__.values))
        logging.info('render ended:' + time.strftime('%H-%M-%S',time.localtime(time.time())))

