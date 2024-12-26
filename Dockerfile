FROM python:3.9

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Install ffmpeg for pydub
RUN apt-get update && apt-get install -y ffmpeg

COPY . /code

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"] 