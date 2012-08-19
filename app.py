# -*- coding: utf-8 -*-
import os
import webapp2
import handlers
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings' # TODO: Move to app.yaml
sys.path.append(os.path.join(os.path.dirname(__file__), ''))

urls = [
    (r'/', handlers.Main),
    (r'/projects', handlers.Projects),
    (r'/projects/(.*)/members', handlers.ProjectMembers),
    (r'/projects/(.*)', handlers.Project),
    (r'/entries', handlers.Entries),
    (r'/entries/(.*)/followers/(.*)', handlers.EntryFollower),
    (r'/entries/(.*)/followers', handlers.EntryFollowers),
    (r'/entries/(.*)/stories', handlers.EntryStories),
    (r'/entries/(.*)/review/(.*)', handlers.EntryReview),
    (r'/entries/(.*)/status', handlers.EntryStatus),
    (r'/entries/(.*)', handlers.Entry),
    (r'/reviews/(.*)', handlers.Reviews),
    (r'/stories', handlers.Stories),
    (r'/logout', handlers.LogOut),
    (r'/signup/step1', handlers.SignupStep1),
    (r'/signup/step2', handlers.SignupStep2)
]
app = webapp2.WSGIApplication(urls, debug=True)