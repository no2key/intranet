# -*- coding: utf-8 -*-
import os
import logging
import datetime
import webapp2
from django.template.loader import render_to_string
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.api import mail
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import urlfetch
from hashlib import md5

# Import libraries
import gdata.gauth
import gdata.apps.client

# Import packages from the project
import settings
import models
import services
from baserequesthandler import BaseRequestHandler

# LogOut redirects the user to the GAE logout url, and then redirects to /
class LogOut(webapp2.RequestHandler):
    def get(self):
        url = users.create_logout_url("/")
        self.redirect(url)

class Main(BaseRequestHandler):
    def get(self):
        self.check_user()
        #for entry in self.person.entries:
        #  logging.info(entry.name)
        #self.render("index.html")
        self.redirect('/entries')

class Projects(BaseRequestHandler):
    def get(self): # TODO: show all projects
        self.check_user()
        self.render("projects.html")
        return
    def post(self): # Create a new project.
        self.check_user()
        project = get_project_from_request(self.request)
        project.put()
        memcache.flush_all()
        new_story(self, "created the project", project=project)
        self.redirect("/projects/" + str(project.key()))

class Project(BaseRequestHandler):
    def get(self, key): # Show a project.
        self.check_user()
        # Display project information
        project = models.Project.get(key)
        template_values = {
          "project": project,
          "active_entries": models.Entry.gql("WHERE project = :1 AND status IN ('new', 'in progress', 'ready') ORDER BY due_on", project.key()),
          "launched_entries": models.Entry.gql("WHERE project = :1 AND status = 'launched' ORDER BY due_on", project.key()),
          "cancelled_entries": models.Entry.gql("WHERE project = :1 AND status = 'cancelled' ORDER BY due_on", project.key()),
        }
        self.render("project.html", template_values)

    def post(self, key): # Update a project.
        self.check_user()
        project_updated = get_project_from_request(self.request)
        project = models.Project.get(key)
        if project.name != project_updated.name:
          project.name = project_updated.name
          new_story(self, "changed the name to <em>%s</em>" % project.name, project=project)
        if project.notes != project_updated.notes:
          project.notes = project_updated.notes
          new_story(self, "changed the notes to <em>%s</em>" % project.notes, project=project)
        if project.status != project_updated.status:
          project.status = project_updated.status
          new_story(self, "changed the status to <em>%s</em>" % project.status, project=project)
        project.put()
        memcache.flush_all()
        self.redirect("/projects/" + key)
        
class ProjectMembers(BaseRequestHandler):
    def post(self, key): # Add a member to a project.
        self.check_user()
        role = decode(self.request.get("role"))
        person = string_to_user(decode(self.request.get("user_id")))
        project = models.Project.get(key)
        update_role(self, person, project, role)

class Entries(BaseRequestHandler):
    def get(self): # Show all entries
        self.check_user()
        template_values = {
          "launched_entries": models.Entry.all().order('due_on')
        }
        self.render("entries.html")
        
    def post(self): # Create a new entry
        self.check_user()
        entry = get_entry_from_request(self.request)
        if entry.impact in ["experiment", "dogfood", "beta"]:
          entry.prod_design_review = "waived"
          entry.eng_design_review = "waived"
        else:
          if not entry.prod_design_doc:
            entry.prod_design_review = "missing"
          if not entry.eng_design_doc:
            entry.eng_design_review = "missing"
        entry.created_by = self.person
        entry.put()
        memcache.flush_all()
        new_story(self, "created the entry", entry=entry)
        self.redirect('/entries/' + str(entry.key()))
            
class Entry(BaseRequestHandler):
    def get(self, key): # Show an entry.
        self.check_user()
        # Render the template
        entry = models.Entry.get(key)
        template_values = {
          "entry": entry
        }
        self.render("entry.html", template_values)

    def post(self, key): # Update an entry.
        self.check_user()
        entry_updated = get_entry_from_request(self.request)
        entry = models.Entry.get(key)
        # Check diffs and log changes
        if entry.name != entry_updated.name:
          entry.name = entry_updated.name
          new_story(self, "changed the name to <em>%s</em>" % entry.name, entry=entry)
        if entry.notes != entry_updated.notes:
          entry.notes = entry_updated.notes
          new_story(self, "changed the note to <em>%s</em>" % entry.notes, entry=entry)
        if entry.impact != entry_updated.impact:
          entry.impact = entry_updated.impact
          if entry.impact in ["experiment", "dogfood", "beta"]:
            entry.prod_design_review = "waived"
            entry.eng_design_review = "waived"
          else: 
            if not entry.prod_design_doc:
              entry.prod_design_review = "missing"
            if not entry.eng_design_doc:
              entry.eng_design_review = "missing"
          new_story(self, "changed the impact to <em>%s</em>" % entry.impact, entry=entry)
        if entry.project.key() != entry_updated.project.key():
          entry.project = entry_updated.project
          new_story(self, "moved to <em>%s</em>" % entry.project.name, entry=entry)
        if entry.prod_design_doc != entry_updated.prod_design_doc:
          entry.prod_design_doc = entry_updated.prod_design_doc
          new_story(self, "changed the product design doc to <em>%s</em>" % entry.prod_design_doc, entry=entry)
        if entry.eng_design_doc != entry_updated.eng_design_doc:
          entry.eng_design_doc = entry_updated.eng_design_doc
          new_story(self, "changed the engineering design doc to <em>%s</em>" % entry.eng_design_doc, entry=entry)

        if entry.type != entry_updated.type:
          entry.type = entry_updated.type
          if entry.type == "platform":
            new_story(self, "marked as ship independently", entry=entry)
          elif entry.type == "product":
            new_story(self, "marked as rely on others", entry=entry)
        if entry.type == "platform":
          # For platform, due_on will be filled in. And reliers will get the same due_on.
          if entry.due_on != entry_updated.due_on:
            entry.due_on = entry_updated.due_on
            new_story(self, "changed the due day to <em>%s</em>" % entry.due_on.isoformat(), entry=entry)
            if entry.reliers:
              for relier in entry.reliers:
                relier.due_on = entry.due_on
                new_story(self, "changed the due day of <em>%s</em> to <em>%s</em>" % (entry.name, entry.due_on.isoformat()), entry=relier)
                relier.put()
          entry.dependency = None
        elif entry.type == "product":
          # For products
          if not compare_models(entry_updated.dependency, entry.dependency):
            entry.dependency = entry_updated.dependency
            entry.due_on = entry.dependency.due_on
            new_story(self, "will rely on <em>%s</em> to ship on <em>%s</em>" % (entry.dependency.name, entry.due_on), entry=entry)

        entry.put()
        memcache.flush_all()
        self.redirect('/entries/' + key)

class EntryFollowers(BaseRequestHandler):
    def post(self, key): # TODO: Add a user to entry followers
        self.check_user()

class EntryFollower(BaseRequestHandler):
    def post(self, key, user_id): # TODO: Update a user to entry followers
        self.check_user()

class EntryStories(BaseRequestHandler):
    def post(self, key): # Create a story to an entry.
        self.check_user()
        text = decode(self.request.get("text"))
        entry = models.Entry.get(key)
        new_story(self, text, entry=entry, type="comment")
        self.redirect("/entries/" + key)

class EntryReview(BaseRequestHandler):
    def post(self, key, type):
        self.check_user()
        entry = models.Entry.get(key)
        status = decode(self.request.get("status"))
        text = decode(self.request.get("text"))
        if type == "prod":
          if entry.prod_design_review != status:
            entry.prod_design_review = status
            new_story(self, "changed product design review status to <em>%s</em>" % status, entry=entry)
            entry.put()
        elif type == "eng":
          if entry.eng_design_review != status:
            entry.eng_design_review = status
            new_story(self, "changed engineering design review status to <em>%s</em>" % status, entry=entry)
            entry.put()
        if text:
          new_story(self, text, entry=entry, type="comment")
        memcache.flush_all()
        self.redirect("/entries/" + key)

class EntryStatus(BaseRequestHandler):
    def post(self, key):
        self.check_user()
        entry = models.Entry.get(key)
        status = decode(self.request.get("status"))
        text = decode(self.request.get("text"))
        if entry.status != status:
          entry.status = status
          if entry.status == "ready":
            new_story(self, "declared <em>%s</em> is ready to launch" % entry.name, entry=entry)
            for relier in entry.reliers: # Reliers' launch statuses are in sync with dependent.
              relier.status = entry.status
              new_story(self, "declared <em>%s</em> is ready to launch" % entry.name, entry=relier)
              relier.put()
            
            # Send launch notifications
            values = {"entry": entry, "base_url": settings.BASE_URL, "text": text}
            cc = []
            for notifier in entry.notifiers:
              cc.append(notifier.email)
            email = models.Email(
              sender = "Launch Notifier <entry-%s@%s.appspotmail.com>" % (entry.key(), settings.APP_ID),
              subject = unicode(render_to_string("mail/ready_notification_subject.txt", values)),
              to = [db.Email("launch@wandoujia.com")],
              cc = list(set(cc)),
              html = render_to_string("mail/ready_notification.html", values)
            )
            services.generate_email(email)

          elif entry.status == "launched": # Reliers' launch statuses are in sync with dependent.
            entry.launched_at = datetime.datetime.now()
            new_story(self, "launched <em>%s</em>" % entry.name, entry=entry)
            for relier in entry.reliers:
              relier.status = entry.status
              relier.launched_at = entry.launched_at
              new_story(self, "launched <em>%s</em>" % entry.name, entry=relier)
              relier.put()
            # TODO: Send out anouncement email.
          else:
            new_story(self, "changed status to <em>%s</em>" % status, entry=entry)
          entry.put()
        if text:
          new_story(self, text, entry=entry, type="comment")
        # TODO: Make texts more funny and useful
        memcache.flush_all()
        self.redirect("/entries/" + key)
        
class Stories(BaseRequestHandler):
    def get(self, key): # Show all stories.
        self.check_user()
        stories = models.Story.all().order('-created_at')
        template_values = {
          'stories': stories
        }
        self.render("stories.html", template_values)
        return

class Reviews(BaseRequestHandler):
    def get(self, type):
        if type not in ('prod', 'eng'):
          self.error(404)
        else:
          required_entries = models.Entry.gql("WHERE %s_design_review IN ('new', 'missing', 'rejected', 'ack') AND status IN ('new', 'in progress') ORDER BY due_on" % type)
          approved_entries = models.Entry.gql("WHERE %s_design_review = 'approved' ORDER BY due_on" % type)
          waived_entries = models.Entry.gql("WHERE %s_design_review = 'waived' ORDER BY due_on" % type)

          template_values = {
            "type": type,
            "required_entries": required_entries,
            "approved_entries": approved_entries,
            "waived_entries": waived_entries 
          }
          self.render("reviews.html", template_values)

class SignupStep1(webapp2.RequestHandler):
    # Generate and redirect users to GData APIs
    def get(self):
        """This handler is responsible for fetching an initial OAuth
        request token and redirecting the user to the approval page."""

        client = gdata.apps.client.AppsClient(domain="wandoujia.com")
        client.ssl = True
        
        current_user = users.get_current_user()
        
        scopes = settings.SCOPES
        oauth_callback = 'http://%s/signup/step2' % self.request.host
        consumer_key = settings.CONSUMER_KEY
        consumer_secret = settings.CONSUMER_SECRET
        request_token = client.get_oauth_token(scopes, oauth_callback,
                                               consumer_key, consumer_secret)

        # Persist this token in the datastore.
        request_token_key = 'request_token_%s' % current_user.email()
        gdata.gauth.ae_save(request_token, request_token_key)

        # Generate the authorization URL.
        approval_page_url = request_token.generate_authorization_url()

        self.redirect(str(approval_page_url))

class SignupStep2(webapp2.RequestHandler):
  def get(self):
      """When the user grants access, they are redirected back to this
      handler where their authorized request token is exchanged for a
      long-lived access token."""
      
      client = gdata.apps.client.AppsClient(domain="wandoujia.com")
      client.ssl = True
      
      current_user = users.get_current_user()
      
      # Remember the token that we stashed? Let's get it back from
      # datastore now and adds information to allow it to become an
      # access token.
      request_token_key = 'request_token_%s' % current_user.email()
      request_token = gdata.gauth.ae_load(request_token_key)
      gdata.gauth.authorize_request_token(request_token, self.request.uri)

      # We can now upgrade our authorized token to a long-lived
      # access token by associating it with gdocs client, and
      # calling the get_access_token method.
      client.auth_token = client.get_access_token(request_token)

      # Note that we want to keep the access token around, as it
      # will be valid for all API calls in the future until a user
      # revokes our access. For example, it could be populated later
      # from reading from the datastore or some other persistence
      # mechanism.
      access_token_key = 'access_token_%s' % current_user.email()
      gdata.gauth.ae_save(request_token, access_token_key)
            
      # Write user info into database
      
      user_name = current_user.email().split('@')[0]
      logging.info(user_name)
      person = models.Person().get_by_key_name(user_name)
      if not person:
        person = models.Person(
          gaia = current_user,
          email = current_user.email(),
          key_name = user_name
        )
      person.is_setup = True
      person.put()
      memcache.flush_all()
      self.redirect('/')

def get_entry_from_request(request):
  if decode(request.get("type")) == "product":
    dependency = models.Entry.get(decode(request.get("dependency")))
    due_on = dependency.due_on
  else:
    due_on = iso_to_date(decode(request.get("due_on")))
  entry = models.Entry(
    name = decode(request.get("name")),
    notes = decode(request.get("notes")),
    impact = decode(request.get("impact")),
    project = models.Project.get(decode(request.get("project"))),
    due_on = due_on,
    type = decode(request.get("type")),
    prod_design_doc = decode(request.get("prod_design_doc")),
    eng_design_doc = decode(request.get("eng_design_doc"))
  )
  if entry.type == "product":
    entry.dependency = models.Entry.get(decode(request.get("dependency")))
  return entry

def get_project_from_request(request):
  project = models.Project(
    name = decode(request.get("name")),
    notes = decode(request.get("notes", None)),
    status = decode(request.get("status")),
  )
  return project

def iso_to_date(iso):
  if iso:
    strlist = iso.split('-')
    return datetime.date(int(strlist[0]), int(strlist[1]), int(strlist[2]))
  else:
    return iso

def get_dates():
  dates = {}
  dates['today'] = datetime.date.today()
  dates['this_monday'] = dates['today'] + datetime.timedelta(days=-dates['today'].weekday())
  dates['this_sunday'] = dates['this_monday'] + datetime.timedelta(days=-1)
  dates['next_monday'] = dates['this_monday'] + datetime.timedelta(weeks=1)
  dates['next_sunday'] = dates['next_monday'] + datetime.timedelta(days=-1)
  dates['the_monday_after_next_monday'] = dates['next_monday'] + datetime.timedelta(weeks=1)
  dates['the_sunday_after_next_sunday'] = dates['the_monday_after_next_monday'] + datetime.timedelta(days=-1)
  dates['30_days_later'] = dates['today'] + datetime.timedelta(days=30)
  dates['31_days_later'] = dates['today'] + datetime.timedelta(days=31)
  return dates

def decode(var):
  """Safely decode form input. Return None if empty"""
  if not var:
    return None
  return unicode(var, 'utf-8') if isinstance(var, str) else unicode(var)

def decode_list(var):
    """Use decode to decode a list of form inputs"""
    if not var:
        return var
    new = []
    for i in var:
        new.append(decode(i))
    return new

def string_list_to_users(string_list):
    """Transcode a list of strings to a list of user objects (domain name added)"""
    user_list = []
    for string in string_list:
      if string:
        user_list.append(string_to_user(string))
    return user_list

def compare_models(a, b):
    """Compare two reference to models. Return false if different, true if same."""
    if (a and not b) or (not a and b):
      return False
    if a and b:
      return a.key() == b.key
    if not a and not b:
      return True
    
def string_to_user(string):
    if string:
      return models.Person.get_by_key_name(string)
    else:
      return None

def update_role(request, person, project, role):
  if person:
    if role == "owner":
      # One project could only have one owner, remove other owners
      for owner in project.owner:
        owner.owns = None
        owner.put()
      # Remove other roles.
      person.fulltime = None
      if project.key() in person.plusones:
        person.plusones.remove(project.key())
      # Create new role
      person.owns = project
      new_story(request, "added <strong>%s</strong> as <em>owner</em>" % person.id, project=project, person=person)
      
    elif role == "fulltimer":
      # Remove other roles.
      # One could only be owner or fulltimer in one project.
      person.owns = None
      if project.key() in person.plusones:
        person.plusones.remove(project.key())
      # Create new role
      person.fulltime = project
      new_story(request, "added <strong>%s</strong> as <em>fulltimer</em>" % person.id, project=project, person=person)

    elif role == "plusoner":
      # If already has other roles, remove that.
      if person.fulltime and (person.fulltime.key() == project.key()):
        person.fulltime = None
      if person.owns and (person.owns.key() == project.key()):
        person.owns = None
      # Create new role
      person.plusones.append(project.key())
      new_story(request, "added <strong>%s</strong> as <em>\"+1\"er</em>" % person.id, project=project, person=person)
    else:
      # Remove all roles from this project.
      if person.fulltime and (person.fulltime.key() == project.key()):
        person.fulltime = None
      if person.owns and (person.owns.key() == project.key()):
        person.owns = None
      if project.key() in person.plusones:
        person.plusones.remove(project.key())
      new_story(request, "removed <strong>%s</strong> from this project" % person.id, project=project, person=person)
    person.put()
    memcache.flush_all()
    request.redirect('/projects/' + str(project.key()))
  else:
    request.error(500)
  
def new_story(request, text, type = "system", entry = None, project = None, person = None):
  if not project:
    project = entry.project
  if not person:
    person = request.person
  story = models.Story(
    text = text,
    entry = entry,
    project = project,
    person = person,
    type = type
  )
  if hasattr(request, "person"): # Sometimes stories are generated by system.
    story.created_by = request.person
  elif person:
    story.created_by = person
  story.put()
  if story.entry:
    story.entry.mailed = False
    story.entry.calendar_synced = False
    story.entry.put()
  if story.project:
    story.project.mailed = False
    story.project.put()
  # TODO: Same for person
  