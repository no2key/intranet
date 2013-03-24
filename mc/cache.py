# -*- coding: utf-8 -*-
import logging
import sys
import datetime
import pickle
from google.appengine.api import memcache

import models

def mem_set(key, value, chunksize=900000):
  serialized = pickle.dumps(value, 2)
  values = {}
  for i in xrange(0, len(serialized), chunksize):
    values['%s.%s' % (key, i//chunksize)] = serialized[i : i+chunksize]
    logging.info("cached: " + ('%s.%s' % (key, i//chunksize))+ str(values['%s.%s' % (key, i//chunksize)]));
  memcache.set_multi(values)
  memcache.set(key, len(values))

def mem_get(key):
  n = memcache.get(key)
  logging.info("#key_size:" + str(n))
  if not n:
    return None
  
  results = memcache.get_multi(['%s.%s' % (key, i) for i in xrange(n)])
  logging.info("#results:" + str(results))
  serialized = ''
  chunks = []
  for v in results.values():
    chunks.append(v)
  
  serialized = ''.join(chunks)
  try:
    logging.info("cached hitted !!!!")
    return pickle.loads(serialized)
  except Exception:
    logging.info("cache missed ")
    return None

def mem_delete(key):
  n = memcache.get(key)
  if n:
    memcache.delete_multi(['%s.%s' % (key, i) for i in xrange(n)])
  
  memcache.delete(key)

def get(key, clear=False):
    if clear:
        mem_delete(key)
        return

    data = mem_get(key)
    if data:
        logging.info("return " + key)
        return data

    data = []
    if key == "all_persons":
        query = models.Person.all().filter("suspended", False)
    elif key == "all_projects":
        query = models.Project.all().order('order')
    elif key == "all_entries":
        query = models.Entry.gql(
            "ORDER BY due_on DESC LIMIT 100")
    elif key == "all_active_entries":
        query = models.Entry.gql(
            "WHERE status IN ('new', 'in progress', 'ready', 'completed') "
            "ORDER BY due_on")
    elif key == "all_launched_entries":
        query = models.Entry.gql("WHERE status = 'launched' ORDER BY due_on")
    elif key == "all_cancelled_entries":
        query = models.Entry.gql("WHERE status = 'cancelled' ORDER BY due_on")
    elif key == "all_releases":
        query = models.Entry.gql("WHERE type = 'platform' ORDER BY due_on")
    elif key == "all_active_releases":
        query = models.Entry.gql(
            "WHERE type = 'platform' AND "
            "status IN ('new', 'in progress', 'ready', 'completed') "
            "ORDER BY due_on")
    elif key == "all_active_beta_releases":
        query = models.Entry.gql(
            "WHERE type = 'platform' AND "
            "status IN ('new', 'in progress', 'ready', 'completed') "
            "AND impact = 'beta' ORDER BY due_on")
    elif key == "all_active_major_releases":
        query = models.Entry.gql(
            "WHERE type = 'platform' AND "
            "status IN ('new', 'in progress', 'ready', 'completed') "
            "AND impact = 'major' ORDER BY due_on")
    elif key == "all_active_full_releases":
        query = models.Entry.gql(
            "WHERE type = 'platform' AND "
            "status IN ('new', 'in progress', 'ready', 'completed') AND "
            "impact IN ('major', 'minor') ORDER BY due_on")
    elif key == "all_active_nonexperimental_releases":
        query = models.Entry.gql(
            "WHERE type = 'platform' AND "
            "status IN ('new', 'in progress', 'ready', 'completed') AND "
            "impact IN ('major', 'minor', 'beta') ORDER BY due_on")
    elif key == "all_active_external_releases":
        query = models.Entry.gql(
            "WHERE type = 'platform' AND "
            "status IN ('new', 'in progress', 'ready', 'completed') AND "
            "impact IN ('major', 'minor', 'beta', 'experimental') "
            "ORDER BY due_on")
    elif key == "recent_launched_releases":
        query = models.Entry.gql(
            "WHERE type = 'platform' AND "
            "status = 'launched' AND launched_at > DATE('%s') "
            "ORDER BY launched_at" %
            ((datetime.date.today() + datetime.timedelta(days=-7)).isoformat()))
    elif key == "all_launched_releases":
        query = models.Entry.gql(
            "WHERE type = 'platform' AND status = 'launched' "
            "ORDER BY launched_at")
    else:
      return

    for item in query:
      data.append(item)

    mem_set(key, data)
	
    logging.info("cached " + key)
    return data
