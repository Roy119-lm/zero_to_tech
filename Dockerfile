# Use official Apache Spark image as base
FROM apache/spark:3.5.7-scala2.12-java11-python3-ubuntu

# Maintainer information
LABEL maintainer="YaQia"
LABEL description="Apache Spark with Iceberg and S3 MinIO support"

USER root

# 创建必要的目录
RUN mkdir -p /tmp/spark-events && \
    chmod 777 /tmp/spark-events

# Set environment variables
ENV ICEBERG_VERSION=1.9.0
ENV HADOOP_VERSION=3.3.4
ENV SPARK_MAJOR_VERSION=3.5
ENV SPARK_VERSION=3.5.7
ENV SPARK_HOME=${SPARK_HOME:-"/opt/spark"}

# Download and install Iceberg runtime JAR
RUN curl -L -o ${SPARK_HOME}/jars/iceberg-spark-runtime-${SPARK_MAJOR_VERSION}_2.12-${ICEBERG_VERSION}.jar \
    https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-${SPARK_MAJOR_VERSION}_2.12/${ICEBERG_VERSION}/iceberg-spark-runtime-${SPARK_MAJOR_VERSION}_2.12-${ICEBERG_VERSION}.jar

# Download AWS bundle
RUN curl -L -o ${SPARK_HOME}/jars/iceberg-aws-bundle-${ICEBERG_VERSION}.jar \
    https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/${ICEBERG_VERSION}/iceberg-aws-bundle-${ICEBERG_VERSION}.jar

# Download and install Hadoop AWS
RUN curl -L -o ${SPARK_HOME}/jars/hadoop-aws-${HADOOP_VERSION}.jar \
   https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_VERSION}/hadoop-aws-${HADOOP_VERSION}.jar

# Download and install PostgreSQL JDBC driver for JDBC Catalog
RUN curl -L -o ${SPARK_HOME}/jars/postgresql-42.7.9.jar \
    https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.9/postgresql-42.7.9.jar

# Install python dependencies
RUN pip install pandas pypinyin openpyxl zhon china-division -i https://mirrors.aliyun.com/pypi/simple

# Set work directory
WORKDIR /opt/spark/work-dir

# Switch back to spark user
USER spark

# Add spark executables to PATH
ENV PATH=$PATH:/opt/spark/bin

# Expose Spark ports
EXPOSE 4040 7077 8080 8081

# Default command
CMD ["/opt/spark/bin/spark-shell"]
