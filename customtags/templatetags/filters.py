# -*- coding: utf-8 -*-
from django import template
import datetime

register = template.Library()

def cst(value):
    if value:
      return datetime.timedelta(hours=+8) + value
    else:
      return value
    
register.filter("cst", cst)