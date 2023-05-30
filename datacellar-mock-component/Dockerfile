FROM python:3.10-bullseye
WORKDIR /root
COPY . .
RUN pip install -r requirements.txt
EXPOSE 9090
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9090"]