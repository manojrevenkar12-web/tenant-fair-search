# The service image. CI builds the fat jar with sbt first (sbt "service/assembly"), then this image.
FROM eclipse-temurin:21-jre-noble
RUN useradd --system --uid 10001 tfs
WORKDIR /app
COPY service/target/scala-3.3.4/tenant-fair-search.jar /app/tenant-fair-search.jar
COPY config/platform.json config/index.json /app/config/
USER 10001
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s CMD ["sh", "-c", "exec 3<>/dev/tcp/127.0.0.1/8080 || exit 1"]
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=70", "-jar", "/app/tenant-fair-search.jar"]
