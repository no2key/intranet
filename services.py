# -*- coding: utf-8 -*-
import os
import re
import logging
import email
import webapp2
import datetime
import time

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

"""
Services that are accessible to admin only (eg. cron).
"""

from django.template.loader import render_to_string
from google.appengine.api import mail
from google.appengine.api import taskqueue
from google.appengine.api import users
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.ext.webapp.util import run_wsgi_app, login_required

# Import gdata
import atom.data
import gdata.data
import gdata.gauth
import gdata.acl.data
import gdata.apps.client
import gdata.calendar.data
import gdata.calendar.client
import gdata.contacts.data
import gdata.contacts.client

import models
import settings
import handlers

# Keep in mind that these are run by system instead of users.
class Notifications(webapp2.RequestHandler):
  def get(self):
    # Generate emails for all entries
    entries = models.Entry.all().filter("mailed", False)
    for entry in entries:
      to = []      
      for notifier in entry.notifiers:
        to.append(notifier.email)
      if to:
        values = {"entry": entry, "base_url": settings.BASE_URL}
        email = models.Email(
          sender = "Launch Notifier <entry-%s@%s.appspotmail.com>" % (entry.key(), settings.APP_ID),
          subject = "[%s] %s (%s) - %s" % (entry.project.name, entry.name, entry.impact, entry.status.upper()),
          to = list(set(to)),
          html = render_to_string("mail_entry.html", values),
          headers = {"References": "entry-%s" % entry.key()} # Make threading works in Gmail
        )
        generate_email(email)
        entry.mailed = True
        entry.put()
        for story in entry.unmailed_stories:
          story.mailed = True
          story.put()
    '''# Generate emails for remaining entries which might be tight to a project.
    projects = models.Project.all().filter("mailed", False)
    for project in projects:
      if project.unmailed_stories:
        to = []      
        for notifier in project.notifiers:
          to.append(notifier.email)
        if to:
          values = {"project": project}
          email = models.Email(
            sender = "Launch Notifier <project-%s@%s.appspotmail.com>" % (project.key(), settings.APP_ID),
            subject = "Updates to [%s]" % project.name,
            to = list(set(to)),
            html = render_to_string("mail_project.html", values),
            headers = {"References": "project-%s" % project.key()} # Make threading works in Gmail
          )
          generate_email(email)
          project.mailed = True
          project.put()
          for story in project.unmailed_stories:
            story.mailed = True
            story.put()'''


class Email(webapp2.RequestHandler):
  def post(self, key):
      """Worker that runs in the 'background'"""
      # Get the object from the database
      email = models.Email.get(key)

      # Construct a appengine.api.mail object
      message = mail.EmailMessage()
      message.sender = email.sender
      if settings.DEBUG is not True:
        # If not in debug mode, then really send emails
        message.to = email.to
      message.bcc = settings.ADMINS
      message.subject = email.subject
      logging.info("Message sent to: %s" % message.to)

      # Set text and html body
      message.html = email.html

      # Send. Important: Sometimes emails fail to send, which will throw an
      # exception and end the function there. Next round tries again.
      message.send()

      # Now the message was sent and we can safely delete it.
      email.delete()

class IncomingMail(InboundMailHandler):
  def receive(self, message):
      # TODO: Add supports for project-(.*) and person-(.*)
      logging.info("Received a message to: " + message.to)
      logging.info("Received a message from: " + message.sender)
      to_p = re.compile(r'(?<=entry-)(.*?)(?=@)') # TODO: And post-fixs
      to_m = to_p.search(message.to)
      if to_m:
        key = to_m.group()
        entry = models.Entry.get(key)
        if entry:
          plaintext_bodies = message.bodies('text/plain')
          text = ""
          for content_type, body in plaintext_bodies:
            text = text + body.decode()
          # So we get texts.
          # TODO: Get rid of quotes
          from_p = re.compile(r'(?<=\<)(.*?)(?=@)')
          from_m = from_p.search(message.sender)
          if from_m:
            id = from_m.group()
            logging.info("Sender identified: %s" % id)
            person = models.Person.get_by_key_name(id)
            handlers.new_story(self, text, entry=entry, type="comment", person=person)
            logging.info("Delivered an update to entry-%s" % key)
          else:
            logging.error("Email delivery failed: Invalid sender.")
        else:
          logging.error("Email delivery failed: Can't find the entry")
      else:
        logging.error("Email delivery failed: No valid email address.")

class SyncCalendar(webapp2.RequestHandler):
    def get(self):
        client = gdata.calendar.client.CalendarClient(domain=settings.DOMAIN)
        client.ssl = True
        client.debug = True
        access_token_key = 'access_token_%s' % settings.ADMINS[0]
        client.auth_token = gdata.gauth.ae_load(access_token_key)
        calendar_id = settings.CALENDAR
        visibility = 'private'
        projection = 'full'
        feed_uri = client.GetCalendarEventFeedUri(calendar=calendar_id, visibility=visibility, projection=projection)
        logging.info("Google Calendar Feed URI: " + str(feed_uri))
        feed = client.GetCalendarEventFeed(uri = feed_uri)
        self.response.out.write('Events on Primary Calendar: %s' % feed.title.text)
        for i, an_event in enumerate(feed.entry):
          self.response.out.write('\t%s. %s' % (i, an_event.title.text))
        
        all_entries = models.Entry.all()
        for entry in all_entries:
          if entry.status == "cancelled":
            # Remove entry from Calendar
            if entry.calendar_edit_uri:
              event = client.GetEventEntry(uri = entry.calendar_edit_uri)
              client.Delete(event)
              logging.info("Event Deleted: " + event.id.text)
              self.response.out.write("Event Deleted: %s<br>" % event.id.text)
          else:
            # Create / update entry
            if entry.calendar_edit_uri:
              event = client.GetEventEntry(uri = entry.calendar_edit_uri)
              event.when = []
            else:
              event = gdata.calendar.data.CalendarEventEntry()
            event.title = atom.data.Title(text="[%s] %s (%s) - %s" % (entry.project.name, entry.name, entry.impact, entry.status.upper()))
            event.content = atom.data.Content(text=entry.notes)
            due_on = entry.due_on.isoformat()
            event.when.append(gdata.calendar.data.When(start=due_on))
            if entry.calendar_edit_uri:
              client.Update(event)
              logging.info("Event Updated: " + event.id.text)
              self.response.out.write("Event Updated: %s<br>" % event.id.text)
            else:
              new_event = client.InsertEvent(event, insert_uri=feed_uri)
              entry.calendar_edit_uri = new_event.GetEditLink().href
              entry.calendar_view_uri = new_event.GetHtmlLink().href
              entry.put()
              logging.info("Event Created: " + new_event.id.text)
              self.response.out.write("Event created: %s<br>" % new_event.id.text)
          # TODO: Sync event followers to Google Calendar

class SyncUsers(webapp2.RequestHandler):
    def get(self):
        client = gdata.apps.client.AppsClient(domain=settings.DOMAIN)
        client.ssl = True
        access_token_key = 'access_token_%s' % settings.ADMINS[0]
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
          self.response.out.write('User ' + entry.login.user_name + ' created / updated. <br>')
          
class SyncProfiles(webapp2.RequestHandler):
    def get(self):
        client = gdata.contacts.client.ContactsClient(source=settings.APP_NAME, domain=settings.DOMAIN)
        feed = client.GetProfilesFeed()

        for i, entry in enumerate(feed.entry):
          self.response.out.write('\n%s %s' % (i+1, entry.name.full_name.text))
          if entry.content:
            self.response.out.write('    %s' % (entry.content.text))
          # Display the primary email address for the contact.
          for email in entry.email:
            if email.primary and email.primary == 'true':
              self.response.out.write('    %s' % (email.address))
          # Display extended properties.
          for extended_property in entry.extended_property:
            if extended_property.value:
              value = extended_property.value
            else:
              value = extended_property.GetXmlBlob()
            self.response.out.write('    Extended Property - %s: %s' % (extended_property.name, value))

class CheckDelays(webapp2.RequestHandler):
    def get(self):
        entries = models.Entry.all()
        for entry in entries:
          if entry.delayed:
            handlers.new_story(self, "This is delayed", entry=entry)

def generate_email(email):
  email.put()
  logging.info("Created an email.")
  taskqueue.add(url="/services/email/%s" % email.key())
  
urls = [
    (r'/services/notification', Notifications),
    (r'/services/email/(.*)', Email),
    (r'/services/sync/calendar', SyncCalendar),
    (r'/services/sync/users', SyncUsers),
    (r'/services/sync/profiles', SyncProfiles),
    (r'/services/check/delays', CheckDelays),
    IncomingMail.mapping()
]

# TODO: Send weekly summaries

app = webapp2.WSGIApplication(urls, debug=settings.DEBUG)