from django.conf import settings
from django.db import models
from django.templatetags.static import static
from django.core.validators import MaxValueValidator, MinValueValidator

import os

# Create your models here.
class Simulation(models.Model):
  SIM_PENDING = 'pending'
  SIM_COMPLETE = 'complete'
  SIM_STATUS = [
    (SIM_PENDING, 'pending'),
    (SIM_COMPLETE, 'complete'),
  ]

  sim_id = models.CharField(max_length=300, help_text='simulation id')
  submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, help_text='simulation submission user')
  submitted_time = models.DateTimeField(auto_now_add=True, help_text='simulation submission time')
  runtime = models.PositiveIntegerField(null=True, help_text='simulation runtime in seconds')
  completion = models.FloatField(default=0, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
  status = models.CharField(max_length=30, choices=SIM_STATUS, default=SIM_PENDING, help_text='simulation status')
  start_date = models.DateTimeField(help_text='simulation start time')
  stop_date = models.DateTimeField(help_text='simulation stop time')
  results_path = models.CharField(max_length=300, help_text='simulation result csv file', null=True)

  def __str__(self):
    return f'Simulation {self.id}, sim_id {self.sim_id}, status {self.status}, runtime {self.runtime}'

  def get_csv_absolute_url(self):
    filen = os.path.join(settings.SIM_RESULT_FOLDER, os.path.split(self.results_path)[-1])
    url = static(f'{filen}')
    return url

  def get_json_absolute_url(self):
    # create json file
    filen = os.path.join(settings.SIM_RESULT_FOLDER, os.path.split(self.results_path)[-1])
    url = static(f'{filen}')
    return url

