FROM python:3.11-slim

WORKDIR /app

COPY . /app/

RUN pip install --no-cache-dir -r requirements.txt

ENV FLASK_APP=main.py
ENV SECRET_KEY=jakomp123467
ENV EVOLUTION_API_URL=http://host.docker.internal:8080
ENV EVOLUTION_API_KEY=sXarFms2vtu6zfD19UYsRs4VCto0YbeYV
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--reuse-port", "--reload", "main:app"]