# How to generate TLS Certificates for HyperCode
# Run these commands in a terminal with OpenSSL (e.g., Git Bash, WSL, or Linux)

# 1. Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt \
  -subj "/CN=hypercode.local/O=HyperFocus"

# 2. Create the Kubernetes Secret
kubectl create secret tls hypercode-tls \
  --key tls.key --cert tls.crt -n hypercode

# 3. Verify
kubectl get secret hypercode-tls -n hypercode
