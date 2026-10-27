FROM python:3.8

#set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE 1

RUN pip install geopandas==0.10.2
RUN pip install shapely==1.7.1
RUN pip install matplotlib
RUN pip install Django
RUN pip install requests
RUN pip install coloredlogs
RUN pip install gunicorn
RUN pip install folium==0.12.1.post1

WORKDIR /code
COPY ./gui /code

COPY ./entrypoint.sh /entrypoint.sh
RUN sed -i.bak 's/\r$//' /entrypoint.sh
RUN ["chmod", "+x", "/entrypoint.sh"]
ENTRYPOINT [ "/entrypoint.sh" ]