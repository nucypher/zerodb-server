# Tools to generate certificates from keys
from OpenSSL import crypto
import ecdsa

from zerodb.crypto import rand

DEFAULT_CURVE = ecdsa.curves.NIST384p


def generate_cert(curve=DEFAULT_CURVE, CN="zerodb.com"):
    serial = int.from_bytes(rand(8), byteorder='little')

    ecdsa_key = ecdsa.SigningKey.generate(curve)
    k = crypto.load_privatekey(crypto.FILETYPE_PEM, ecdsa_key.to_pem())

    # k = crypto.PKey()
    # k.generate_key(crypto.TYPE_RSA, 4096)

    # create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().CN = CN
    cert.set_serial_number(serial)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10 * 365 * 86400)  # 10 years
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')

    priv_pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode()
    pub_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode()

    return priv_pem, pub_pem
