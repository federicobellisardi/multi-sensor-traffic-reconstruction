from fastapi import FastAPI, Request
from pydantic import BaseModel

app = FastAPI(
)

class body_sim(BaseModel):
  start_date : str
  stop_date : str
  sampling_dt : int

class response_sim(BaseModel):
  message : str = 'simulation OK'
  sim_uid  : int = 0
  real_score : float = 0
  user_start : str = ''

@app.post('/sim', response_model=response_sim)
async def sim_post(body: body_sim, request: Request):
  return response_sim()
