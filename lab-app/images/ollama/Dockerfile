FROM ollama/ollama

ENV OLLAMA_KEEP_ALIVE=-1
ENV OLLAMA_MODEL=qwen2.5:3b

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 11434

ENTRYPOINT ["/entrypoint.sh"]
