from django.core.management.base import BaseCommand

from django.contrib.auth.models import User

import pandas as pd

class Command(BaseCommand):
  help = 'users management command'

  def add_arguments(self, parser):
    parser.add_argument('-l', '--list', action='store_true', help='list profiles and users')
    parser.add_argument('-u', '--usr', default=None, help='user')
    parser.add_argument('-p', '--pwd', default=None, help='password')
    parser.add_argument('-s', '--staff', action='store_true', help='is_staff')
    parser.add_argument('-r', '--res', action='store_true', help='reset user db')

  def handle(self, *args, **kwargs):

    if kwargs.get('res'):
      try:
        User.objects.exclude(is_superuser=True).delete()
        print(f'Resetting user/profiles OK')
      except Exception as e:
        print(f'Resetting user/profiles error : {e}')

    usr = kwargs.get('usr')
    pwd = kwargs.get('pwd')
    if usr and pwd:
      try:
        if kwargs.get('staff'):
          staff = True
        else:
          staff = False
        user = User.objects.create_user(
          username=usr,
          password=pwd,
          is_staff=staff,
        )
        print(f'Created user {user} staff {staff}')
      except Exception as e:
        print(f'Error : {e}')

    if kwargs.get('list'):
      qs = User.objects.all()
      df = pd.DataFrame(qs.values())
      print(df.columns)
      print(df[['username', 'id', 'is_staff', 'is_superuser', 'last_login']])