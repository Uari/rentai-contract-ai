
FROM python:3.11-slim
WORKDIR /app
RUN pip install streamlit requests
COPY frontend /app
EXPOSE 8501
ENV BACKEND_URL=http://rentai-backend:8000/api
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
