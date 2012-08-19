# -*- coding: utf-8 -*-
import logging
import datetime

from hashlib import md5
from google.appengine.ext import db
from google.appengine.api import users

import settings

class Project(db.Model):
    name = db.StringProperty(required=True)
    notes = db.TextProperty()
    order = db.IntegerProperty()
    status = db.StringProperty(
        required=True,
        default="active",
        choices=set(settings.PROJECT_STATUSES))
    created_at = db.DateTimeProperty(auto_now_add=True)
    modified_at = db.DateTimeProperty(auto_now=True)
    mailed = db.BooleanProperty(default=False)

    @property
    def plusoners(self):
      return Person.gql("WHERE plusones = :1", self.key())
    
    @property
    def stories(self):
      return self.project_stories.order("created_at")

    @property
    def unmailed_stories(self):
      return self.project_stories.order("created_at").filter("mailed", False)

    @property
    def notifiers(self):
        notifiers = []
        notifiers.extend(self.owner)
        notifiers.extend(self.fulltimers)
        notifiers.extend(self.plusoners)
        return list(set(notifiers))

class Person(db.Model):
    email = db.EmailProperty()
    id = db.StringProperty()
    gaia = db.UserProperty()
    given_name = db.StringProperty()
    family_name = db.StringProperty()
    owns = db.ReferenceProperty(Project, collection_name="owner")
    fulltime = db.ReferenceProperty(Project, collection_name = "fulltimers")
    # Could only fulltime on ONE project
    plusones = db.ListProperty(db.Key) # +1 a project
    date_joined = db.DateTimeProperty(auto_now_add=True)
    date_lastlogin = db.DateTimeProperty(auto_now_add=True)  # TODO
    date_lastactivity = db.DateTimeProperty(auto_now_add=True)  # TODO
    is_setup = db.BooleanProperty(default=False)
    suspended = db.BooleanProperty(default=False)
    
    @property
    def projects(self):
      projects = []
      projects.extend(self.owns)
      projects.extend(self.fulltime)
      projects.extend(db.get(self.plusones))
      return list(set(projects))
      
    @property
    def entries(self):
      return Entry.gql("WHERE notifiers = :1", self)
    
    @property
    def plusone_projects(self):
      return db.get(self.plusones)
      
    @staticmethod
    def from_user(user):
        user_name = user.email().split('@')[0]
        person = Person().get_by_key_name(user_name)
        return person
        
    @staticmethod
    def from_email(email):
        user_id = email.split('@')[0]
        return Person().get_by_key_name(user_id)

class Entry(db.Model):
    # User fill-in properties
    name = db.StringProperty(required=True)
    notes = db.TextProperty()
    impact = db.StringProperty(
        required=True,
        choices=set(settings.IMPACTS))
    project = db.ReferenceProperty(Project, collection_name="entries")
    prod_design_doc = db.LinkProperty()
    eng_design_doc = db.LinkProperty()

    status = db.StringProperty(
        required=True,
        default="new",
        choices=set(settings.LAUNCH_STATUSES)
    )
    prod_design_review = db.StringProperty(
        required=True,
        default="new",
        choices=set(settings.APPROVAL_STATUSES))
    eng_design_review = db.StringProperty(
        required=True,
        default="new",
        choices=set(settings.APPROVAL_STATUSES))

    # For "product"
    dependency = db.SelfReferenceProperty(collection_name="reliers")
    # For "platform", this will be filled in
    due_on = db.DateProperty(required=True)
    type = db.StringProperty(choices=set(["platform", "product"]))
    
    # Automatic properties
    launched_at = db.DateTimeProperty()
    created_at = db.DateTimeProperty(auto_now_add=True)
    created_by = db.ReferenceProperty(Person, collection_name="creates")
    modified_at = db.DateTimeProperty(auto_now=True)
    mailed = db.BooleanProperty(default=False)
    calendar_synced = db.BooleanProperty(default=False)
    calendar_edit_uri = db.LinkProperty()
    calendar_view_uri = db.LinkProperty()
    
    @property
    def notifiers(self):
        notifiers = []
        notifiers.extend(self.project.owner)
        notifiers.extend(self.project.fulltimers)
        notifiers.extend(self.project.plusoners)
        return list(set(notifiers))
    
    @property
    def stories(self):
      return self.entry_stories.order("created_at")
    
    @property
    def unmailed_stories(self):
      return self.entry_stories.order("created_at").filter("mailed", False)
      
    @property
    def ready(self):
      for relier in self.reliers:
        if not ((relier.prod_design_review == "approved" or
                 relier.prod_design_review == "waived") and
                (relier.eng_design_review == "approved" or
                 relier.eng_design_review == "waived")):
          return False
      if not ((self.prod_design_review == "approved" or
               self.prod_design_review == "waived") and
              (self.eng_design_review == "approved" or
               self.eng_design_review == "waived")):
        return False
      return True
    
    @property
    def active(self):
      if (self.status == "launched" or self.status == "cancelled"):
        return False
      else:
        return True
        
    @property
    def delayed(self):
      if datetime.date.today() > self.due_on and self.status in ["in progress", "new", "completed", "ready"]:
        return True
      else:
        return False

class Story(db.Model):
    type = db.StringProperty(choices=set(["system", "comment"]))
    text = db.TextProperty(required=True)
    created_by = db.ReferenceProperty(Person)
    created_at = db.DateTimeProperty(auto_now_add=True)
    entry = db.ReferenceProperty(Entry, collection_name="entry_stories")
    project = db.ReferenceProperty(Project, collection_name="project_stories")
    person = db.ReferenceProperty(Person, collection_name="person_stories")
    
    # Flag to indicate whether this is mailed or not.
    mailed = db.BooleanProperty(default=False)

class Email(db.Model):
    sender = db.EmailProperty(required=True)
    to = db.ListProperty(db.Email, required=True)
    cc = db.ListProperty(db.Email)
    reference = db.StringProperty()
    subject = db.StringProperty(required=True)
    html = db.TextProperty(required=True)
    