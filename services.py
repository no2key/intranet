# -*- coding: utf-8 -*-
import os
import re
import logging
import email
import webapp2
import datetime
import time

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings' # TODO: Move to app.yaml

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
          html = render_to_string("mail/entry.html", values),
          reference = "entry-%s" % entry.key()
        )
        generate_email(email)
        entry.mailed = True
        entry.put()
        for story in entry.unmailed_stories:
          story.mailed = True
          story.put()
      else:
        logging.info("No project members for entry %s." % entry.name)

class Email(webapp2.RequestHandler):
  def post(self, key):
      """Worker that runs in the 'background'"""
      if settings.DEBUG is not True:
      # If not in debug mode, then really send emails
      # Get the object from the database
        email = models.Email.get(key)

        # Construct a appengine.api.mail object
        message = mail.EmailMessage()
        message.sender = email.sender
        message.to = email.to
        if email.cc:
          message.cc = email.cc
        message.bcc = settings.ADMINS
        message.subject = email.subject
        # message.reply_to = email.sender
        if email.reference:
          message.headers = {
              "References": email.reference # Make threading works in Gmail
          } 
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
      if not to_m:
        logging.info("No valid email address in 'to'. Try search 'cc'.")
        to_m = to_p.search(message.cc)
      if to_m:
        key = to_m.group()
        entry = models.Entry.get(key)
        if entry:
          plaintext_bodies = message.bodies('text/plain')
          text = ""
          for content_type, body in plaintext_bodies:
            text = text + body.decode()
          # So we get texts.
          logging.info("Original texts: \n" + text)
          text= remove_quotes(text) # Remove quotes.
          logging.info("Clean texts: \n" + text)          
          from_p = re.compile(r'(?<=(\<))(.*?)(?=@' + settings.DOMAIN + ')') # TODO: Bug: pure email address can't match.
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
        logging.error("Email delivery failed: No valid email address found.")

class SyncCalendar(webapp2.RequestHandler):
  def get(self):
    entries = models.Entry.all().filter("calendar_synced", False)
    for entry in entries:
      taskqueue.add(queue_name='calendar', url="/services/sync/calendar/%s" % entry.key())
      self.response.out.write("Entry %s waiting to be synced to calenadr.<br>" % entry.name)
      entry.calendar_synced = True
      entry.put()
      # TODO: Sync event followers to Google Calendar
        
class SyncCalendarEvent(webapp2.RequestHandler):
  def post(self, key):
      """Worker that runs in the 'background'"""
      # Get the object from the database
      client = gdata.calendar.client.CalendarClient(domain=settings.DOMAIN)
      client.ssl = True
      client.debug = True
      access_token_key = 'access_token_%s' % settings.ADMINS[0]
      client.auth_token = gdata.gauth.ae_load(access_token_key)
      calendar_id = settings.CALENDAR
      feed_uri = client.GetCalendarEventFeedUri(
          calendar=calendar_id, visibility='private', projection='full')

      entry = models.Entry.get(key)
      if entry.status == "cancelled":
        # Remove entry from Calendar
        if entry.calendar_edit_uri:
          event = client.GetEventEntry(uri = entry.calendar_edit_uri)
          client.Delete(event)
          logging.info("Event Deleted: " + event.id.text)
          self.response.out.write("Event Deleted: %s<br>" % event.id.text)
      else:
        # Create / update entry
        if entry.calendar_edit_uri: # Update existed entry
          event = client.GetEventEntry(uri = entry.calendar_edit_uri)
          event.when = []
        else: # Create new entry
          event = gdata.calendar.data.CalendarEventEntry()
        event.title = atom.data.Title(text="[%s] %s (%s) - %s" % (entry.project.name, entry.name, entry.impact, entry.status.upper()))
        event.content = atom.data.Content(text=entry.notes)
        due_on = entry.due_on.isoformat()
        event.when.append(gdata.calendar.data.When(start=due_on))
        if entry.calendar_edit_uri:
          client.Update(event)
          logging.info("Event Updated: " + event.id.text)
        else:
          new_event = client.InsertEvent(event, insert_uri=feed_uri)
          entry.calendar_edit_uri = new_event.GetEditLink().href
          entry.calendar_view_uri = new_event.GetHtmlLink().href
          logging.info("Event Created: " + new_event.id.text)

class SyncCalendarReset(webapp2.RequestHandler):
  def get(self):
    # Reset sync status.
    entries = models.Entry.all()
    for entry in entries:
      entry.calendar_synced = False
      entry.calendar_edit_uri = None
      entry.calendar_view_uri = None
      entry.put()
      self.response.out.write("Entry %s reset.<br>" % entry.name)
    self.response.out.write("All entries reset.<br>")

class SyncCalendarClean(webapp2.RequestHandler):
  def get(self):
    # Clean calendar
    client = gdata.calendar.client.CalendarClient(domain=settings.DOMAIN)
    client.ssl = True
    client.debug = True
    access_token_key = 'access_token_%s' % settings.ADMINS[0]
    client.auth_token = gdata.gauth.ae_load(access_token_key)
    calendar_id = settings.CALENDAR
    feed_uri = client.GetCalendarEventFeedUri(
        calendar=calendar_id, visibility='private', projection='full')
    feed = client.GetCalendarEventFeed(uri = feed_uri)
    for i, an_event in enumerate(feed.entry):
      client.Delete(an_event)

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

class FixReviewStatus(webapp2.RequestHandler):
  def get(self):
      entries = models.Entry.all().filter("prod_design_review", "missing")
      for entry in entries:
        entry.prod_design_review = "new"
        self.response.out.write("Fix prod review status for %s.<br>" % entry.name)
        entry.put()
      entries = models.Entry.all().filter("eng_design_review", "missing")
      for entry in entries:
        entry.eng_design_review = "new"
        self.response.out.write("Fix eng review status for %s.<br>" % entry.name)
        entry.put()

class FixEmailStatus(webapp2.RequestHandler):
  def get(self):
      emails = models.Email.all()
      for email in emails:
        taskqueue.add(url="/services/email/%s" % email.key())
        self.response.out.write("Fix email status for %s.<br>" % email.subject)
    
def generate_email(email):
  email.put()
  logging.info("Created email #%s." % email.key())
  taskqueue.add(url="/services/email/%s" % email.key())

def remove_quotes(text):
  # http://stackoverflow.com/questions/2385347/how-to-remove-the-quoted-text-from-an-email-and-only-show-the-new-text
  # general spacers for time and date
  spacers = "[\\s,/\\.\\-]"
  # matches times
  timePattern = "(?:[0-2])?[0-9]:[0-5][0-9](?::[0-5][0-9])?(?:(?:\\s)?[AP]M)?"
  # matches day of the week
  dayPattern = "(?:(?:Mon(?:day)?)|(?:Tue(?:sday)?)|(?:Wed(?:nesday)?)|(?:Thu(?:rsday)?)|(?:Fri(?:day)?)|(?:Sat(?:urday)?)|(?:Sun(?:day)?))"
  # matches day of the month (number and st, nd, rd, th)
  dayOfMonthPattern = "[0-3]?[0-9]" + spacers + "*(?:(?:th)|(?:st)|(?:nd)|(?:rd))?"
  # matches months (numeric and text)
  monthPattern = ("(?:(?:Jan(?:uary)?)|(?:Feb(?:uary)?)|(?:Mar(?:ch)?)|(?:Apr(?:il)?)|(?:May)|(?:Jun(?:e)?)|(?:Jul(?:y)?)" +
                  "|(?:Aug(?:ust)?)|(?:Sep(?:tember)?)|(?:Oct(?:ober)?)|(?:Nov(?:ember)?)|(?:Dec(?:ember)?)|(?:[0-1]?[0-9]))")
  # matches years (only 1000's and 2000's, because we are matching emails)
  yearPattern = "(?:[1-2]?[0-9])[0-9][0-9]";
  # matches a full date
  datePattern = ("(?:" + dayPattern + spacers + "+)?(?:(?:" + dayOfMonthPattern + spacers + "+" + monthPattern + ")|" +
                 "(?:" + monthPattern + spacers + "+" + dayOfMonthPattern + "))" +
                 spacers + "+" + yearPattern)

  # matches a date and time combo (in either order)
  dateTimePattern = ("(?:" + datePattern + "[\\s,]*(?:(?:at)|(?:@))?\\s*" + timePattern + ")|" +
                     "(?:" + timePattern + "[\\s,]*(?:on)?\\s*"+ datePattern + ")")

  # matches a leading line such as
  # ----Original Message----
  # or simply
  # ------------------------
  leadInLine = "-+\\s*(?:Original(?:\\sMessage)?)?\\s*-+\n"
  # matches a header line indicating the date
  dateLine = "(?:(?:date)|(?:sent)|(?:time)):\\s*"+ dateTimePattern + ".*\n"
  # matches a subject or address line
  subjectOrAddressLine = "((?:from)|(?:subject)|(?:b?cc)|(?:to))|:.*\n"
  # matches gmail style quoted text beginning, i.e.
  # On Mon Jun 7, 2010 at 8:50 PM, Simon wrote:
  gmailQuotedTextBeginning = "(On\\s+" + dateTimePattern + ".*wrote:\n)"

  # matches the start of a quoted section of an email
  rule1 = re.compile(r"(?i)(?:(?:" + leadInLine + ")?" +
                                    "(?:(?:" +subjectOrAddressLine + ")|(?:" + dateLine + ")){2,6})|(?:" +
                                    gmailQuotedTextBeginning + ")"
                                    );
  rule2 = re.compile(r"^\>.*", re.MULTILINE)
  rule3 = re.compile(r"^Sent from", re.MULTILINE)
  match = rule1.search(text)
  if match:
    text = text[:match.start()]
    logging.info("Rule 1 matched.")
  match = rule2.search(text)
  if match:
    text = text[:match.start()]
    logging.info("Rule 2 matched.")
  match = rule3.search(text)
  if match:
    text = text[:match.start()]
    logging.info("Rule 3 matched.")
  return text

urls = [
    (r'/services/notification', Notifications),
    (r'/services/email/(.*)', Email),
    (r'/services/sync/calendar/clean', SyncCalendarClean),
    (r'/services/sync/calendar/reset', SyncCalendarReset),
    (r'/services/sync/calendar/(.*)', SyncCalendarEvent),
    (r'/services/sync/calendar', SyncCalendar),
    (r'/services/sync/users', SyncUsers),
    (r'/services/sync/profiles', SyncProfiles),
    (r'/services/check/delays', CheckDelays),
    (r'/services/fix/review-status', FixReviewStatus),
    (r'/services/fix/email-status', FixEmailStatus),
    IncomingMail.mapping()
]

# TODO: Send weekly summaries

app = webapp2.WSGIApplication(urls, debug=settings.DEBUG)