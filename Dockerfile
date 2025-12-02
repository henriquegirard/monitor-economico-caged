FROM python:3.9-slim

WORKDIR /app

# Instala bibliotecas do sistema (necessário para o py7zr funcionar bem)
RUN apt-get update && apt-get install -y libgomp1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]