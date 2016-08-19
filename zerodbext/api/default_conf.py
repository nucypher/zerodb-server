from ZEO.tests import testssl

api_sock = ('localhost', 17234)
zerodb_sock = ('localhost', 8001)
models = 'models.py'
# username =
# password =
client_key = testssl.client_key         # If set, use cert-based auth
client_cert = testssl.client_cert       # If set, use cert-based auth
server_cert = testssl.server_cert       # If absent, we rely on CA
debug = True
