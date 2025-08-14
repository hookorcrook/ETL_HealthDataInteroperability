FROM apache/airflow:2.8.1-python3.9
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

# Copy project files
COPY --chown=airflow:root requirements.txt .
COPY --chown=airflow:root scripts/ /opt/airflow/scripts/
COPY --chown=airflow:root include/ /opt/airflow/include/
COPY --chown=airflow:root config/ /opt/airflow/config/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create directories
RUN mkdir -p /opt/airflow/include/temp_data

# Create an entrypoint script
COPY --chown=airflow:root scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]