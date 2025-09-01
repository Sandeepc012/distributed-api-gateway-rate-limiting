FROM envoyproxy/envoy:v1.30-latest
COPY envoy.yaml /etc/envoy/envoy.yaml
CMD ["/usr/local/bin/envoy","-c","/etc/envoy/envoy.yaml","-l","info","--service-cluster","api-gateway"]