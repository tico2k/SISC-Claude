import datetime
from datetime import timezone
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import socket

def generate_self_signed_cert(cert_file="cert.pem", key_file="key.pem"):
    # Generate our key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    # Generate a self-signed cert
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"KR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Seoul"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Seoul"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Fleit Lab"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
    ])
    
    import ipaddress
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.now(timezone.utc)
    ).not_valid_after(
        # Our certificate will be valid for 10 years
        datetime.datetime.now(timezone.utc) + datetime.timedelta(days=3650)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(u"localhost"),
            x509.DNSName(hostname),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            x509.IPAddress(ipaddress.IPv4Address(local_ip)),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())

    # Write our certificate out to disk.
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    # Write our private key out to disk.
    with open(key_file, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    
    print(f"✅ Generated {cert_file} and {key_file} successfully.")
    print(f"Subject Alternative Names: localhost, {hostname}, {local_ip}")

if __name__ == "__main__":
    generate_self_signed_cert()
