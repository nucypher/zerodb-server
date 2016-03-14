import zerodb  # ZeroDB itself
import transaction  # Transaction manager
import models  # ..and our data model

# Also we need to generate some random data
import names
import loremipsum
import random

# Setup logging
import logging
logging.basicConfig()

# Start client end of TLS tunnel
from pystunnel import Stunnel
stunnel = Stunnel("conf/stunnel-client.conf")
rc = stunnel.start()
print("stunnel started with rc %d" % rc)
import atexit
atexit.register(stunnel.stop)

# Open ZeroDB connection
USERNAME = "root"
PASSPHRASE = "123"
SOCKET = ("localhost", 8002)

db = zerodb.DB(SOCKET, username=USERNAME, password=PASSPHRASE)
print("Connected")

# Create objects
NUMOBJECTS = 1000
REPORTFREQ = 100

# Everything we record should be within a transaction manager
# or be ended with transaction.commit()
print("Creating %d objects" % NUMOBJECTS)
with transaction.manager:
    for i in range(NUMOBJECTS):
        if i % REPORTFREQ == 0 and i != 0:
            # Random text generation is slow, so we report
            # about progress here
            print(i)
        e = models.Employee(name=names.get_first_name(),
                            surname=names.get_last_name(),
                            salary=random.randrange(200000),
                            description=loremipsum.get_paragraph(),
                            extra=loremipsum.get_sentence())
        db.add(e)  # Don't forget to add created object to the db

    # One special record
    desc = """A theoretical physicist, cosmologist,
author and Director of Research at the Centre for
Theoretical Cosmology within the University of Cambridge,
Stephen William Hawking resides in the United Kingdom."""
    e = models.Employee(name="Stephen", surname="Hawking",
                        salary=400000,
                        description=desc)
    db.add(e)  # Don't forget to add created object to the db
    print("Committing")

# This is not really necessary
db.disconnect()
