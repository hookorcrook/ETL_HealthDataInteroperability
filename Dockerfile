FROM ${AIRFLOW_IMAGE_NAME:-apache/airflow:2.8.1}-python3.9
USER root

# Install OpenJDK-17
RUN apt update && \
    apt-get install -y openjdk-17-jdk && \
    apt-get install -y ant && \
    apt-get clean;

# Set JAVA_HOME
ENV JAVA_HOME /usr/lib/jvm/java-17-openjdk-amd64/
RUN export JAVA_HOME

USER airflow
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt