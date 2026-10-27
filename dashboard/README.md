# mover

### Django

#### Local
First setup (only once)
```
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

Launch django server
```
python manage.py runserver
```
and visit [http://127.0.0.1:8000](http://127.0.0.1:8000)

Launch command module (see [`management`](mtsdata/management) folder content in `mtsdata` app)
```
python manage.py test -a foo
python manage.py test2 -a bar
```

#### Docker
From within `dashboard` folder, edit `docker-compose.yml` and run
```
docker compose up gui
```


### Fastapi

#### Self-Hosted
From any folder, create your own `config.json` and run
```
python path/to/dashboarrd/fastapi/sim_ws.py
```

#### Hosted
From within `dashboard/fastapi` folder, create your own `config.json` and run
```
uvicorn sim-ws:app --reload --port 9000
```

#### Docker
From within `dashboard` folder, edit `docker-compose.yml` and run
```
docker compose up sim_ws
```


docker-compose -f docker-compose.figaro.yml --project-name "mover" up --build -d
