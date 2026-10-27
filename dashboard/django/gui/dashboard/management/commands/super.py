from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User

import os

class Command(BaseCommand):
  help = 'create default superuser'

  def handle(self, *args, **kwargs):
    # create superuser if missing
    try:
      super_username = 'physycom'
      super_email    = ''
      super_password = os.environ['MOVER_PWD']
      User = get_user_model()
      User.objects.create_superuser(super_username, super_email, super_password)
      print(f'Superuser created')
    except Exception as e:
      print(e)
