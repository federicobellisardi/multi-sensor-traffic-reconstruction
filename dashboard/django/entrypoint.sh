#! /usr/bin/env sh

echo "$(date) - Init sqlite db"
rm -rf *.sqlite3
python manage.py makemigrations
python manage.py migrate

echo "$(date) - Collecting staticfiles"
mkdir -p ${STATICFILES_DIR}
python manage.py collectstatic --noinput

if [ "${MOVER_INSECURE}" != "" ]
then
  echo "$(date) - DEV MODE"
  python manage.py super
  python manage.py runserver 0.0.0.0:8000
else
  echo "$(date) - PROD MODE"
  gunicorn gui.wsgi:application --bind 0.0.0.0:8000 --workers 3 --capture-output
fi
