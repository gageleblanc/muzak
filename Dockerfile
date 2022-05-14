FROM python:3.8

COPY requirements.txt /
RUN apt-get update && apt-get install -y libtag1-dev
RUN pip3 install -r /requirements.txt
RUN mkdir /tmp/wheels
COPY dist/*.whl /tmp/wheels
RUN pip3 install /tmp/wheels/*.whl
ENTRYPOINT ["muzak"]
