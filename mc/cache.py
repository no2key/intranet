# -*- coding: utf-8 -*-
import logging
from google.appengine.api import memcache

import models

def get_all_persons(clear=False):
    if clear:
        memcache.delete("all_persons")
        return

    all_persons = memcache.get("all_persons")
    if all_persons:
        logging.info("return cached all_persons")
        return all_persons

    all_persons = []
    for person in models.Person.all().filter("suspended", False):
        all_persons.append(person)

    memcache.set("all_persons", all_persons)
    logging.info("cached all_persons")
    return all_persons

def get_all_projects(clear=False):
    if clear:
        memcache.delete("all_projects")
        return

    all_projects = memcache.get("all_projects")
    if all_projects:
        logging.info("return cached all_projects")
        return all_projects

    all_projects = []
    for project in models.Project.all().order('order'):
        all_projects.append(project)

    memcache.set("all_projects", all_projects)
    logging.info("cached all_projects")
    return all_projects

def get_all_entries(clear=False):
  if clear:
      memcache.delete("all_entries")
      return

  all_entries = memcache.get("all_entries")
  if all_entries:
      logging.info("return cached all_entries")
      return all_entries

  all_entries = []
  for entry in models.Entry.all().order('due_on'):
      all_entries.append(entry)

  memcache.set("all_entries", all_entries)
  logging.info("cached all_entries")
  return all_entries

def get_all_active_entries(clear=False):
  if clear:
      memcache.delete("all_active_entries")
      return

  all_active_entries = memcache.get("all_active_entries")
  if all_active_entries:
      logging.info("return cached all_active_entries")
      return all_active_entries

  all_active_entries = []
  for entry in models.Entry.all().filter("status IN", ["new", "in progress", "ready"]).order('due_on'):
      all_active_entries.append(entry)

  memcache.set("all_active_entries", all_active_entries)
  logging.info("cached all_active_entries")
  return all_active_entries

def get_all_launched_entries(clear=False):
  if clear:
      memcache.delete("all_launched_entries")
      return

  all_launched_entries = memcache.get("all_launched_entries")
  if all_launched_entries:
      logging.info("return cached all_launched_entries")
      return all_launched_entries

  all_launched_entries = []
  for entry in models.Entry.all().filter("status", "launched").order('due_on'):
      all_launched_entries.append(entry)

  memcache.set("all_launched_entries", all_launched_entries)
  logging.info("cached all_launched_entries")
  return all_launched_entries

def get_all_cancelled_entries(clear=False):
  if clear:
      memcache.delete("all_cancelled_entries")
      return

  all_cancelled_entries = memcache.get("all_cancelled_entries")
  if all_cancelled_entries:
      logging.info("return cached all_cancelled_entries")
      return all_cancelled_entries

  all_cancelled_entries = []
  for entry in models.Entry.all().filter("status", "cancelled").order('due_on'):
      all_cancelled_entries.append(entry)

  memcache.set("all_cancelled_entries", all_cancelled_entries)
  logging.info("cached all_cancelled_entries")
  return all_cancelled_entries

def get_all_releases(clear=False):
  if clear:
      memcache.delete("all_releases")
      return

  all_releases = memcache.get("all_releases")
  if all_releases:
      logging.info("return cached all_releases")
      return all_releases

  all_releases = []
  for release in models.Entry.all().filter("type", "platform").order('due_on'):
      all_releases.append(release)

  memcache.set("all_releases", all_releases)
  logging.info("cached all_releases")
  return all_releases

def get_all_active_releases(clear=False):
  if clear:
      memcache.delete("all_active)releases")
      return

  all_active_releases = memcache.get("all_active_releases")
  if all_active_releases:
      logging.info("return cached all_active_releases")
      return all_active_releases

  all_active_releases = []
  for release in models.Entry.all().filter("type", "platform").filter("status IN", ["new", "in progress", "ready"]).order('due_on'):
      all_active_releases.append(release)

  memcache.set("all_active_releases", all_active_releases)
  logging.info("cached all_active_releases")
  return all_active_releases