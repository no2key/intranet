# -*- coding: utf-8 -*-
import logging
import datetime
from google.appengine.api import memcache

import models

def get(key, clear=False):
    if clear:
        memcache.delete(key)
        return

    data = memcache.get(key)
    if data:
        logging.info("return " + key)
        return data

    data = []
    if key == "all_persons":
        query = models.Person.all().filter("suspended", False)
    elif key == "all_projects":
        query = models.Project.all().order('order')
    elif key == "all_entries":
        query = models.Entry.all().order('due_on')
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

    memcache.set(key, data)
    logging.info("cached " + key)
    return data
