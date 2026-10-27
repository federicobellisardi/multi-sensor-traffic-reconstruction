#! /usr/bin/env python3

from requests import post, get
import time
import json

baseurl = 'localhost:9000'
sim_url = f'http://{baseurl}/sim'
status_url = f'http://{baseurl}/status'

payload = {
  'start_date'  : '2021-05-12 05:00:00',
  'stop_date'   : '2021-05-12 05:59:00',
  'sampling_dt' : 900
}
headers={
  'accept': 'application/json',
  'Content-Type': 'application/json',
}
response = post(sim_url, data=json.dumps(payload), headers=headers)
rjson = response.json()
print(rjson)
sim_uid = rjson['sim_uid']
print(sim_uid)

#exit()

while True:
  response = get(f'{status_url}/{sim_uid}')
  rjson = response.json()
  #print(rjson)
  status = rjson['status']
  completion = rjson['completion']
  elapsed = rjson['elapsed']

  barlen = 20
  bar = '|' + '*' * int(completion*barlen) + ' ' * (barlen - int(barlen*completion)) + '|'
  print(f'{bar} status {status: >10} {100*completion: 3.2f}% elapsed {elapsed: 5.3f} s', end='\r')

  if status == 'complete':
    response = get(f'{status_url}/{sim_uid}?download=True')
    with open('response.json', 'w') as rout:
      json.dump(response.json(), rout, indent=2)
    print('\nsim status : ', rjson['status'])
    break
  time.sleep(1)
