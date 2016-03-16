import zerodb
from zerodb.query import *
from models import Employee

# Setup logging
import logging
logging.basicConfig()

# Open ZeroDB connection
USERNAME = "root"
PASSPHRASE = "123"
SOCKET = ("localhost", 8002)
STUNNEL_CONFIG = "conf/stunnel-client.conf"

db = zerodb.DB(SOCKET, username=USERNAME, password=PASSPHRASE, stunnel_config=STUNNEL_CONFIG)
print("Connected")

print(len(db[Employee]))

johns = db[Employee].query(name="John", limit=10)
print(len(johns))
print(johns)

rich_johns = db[Employee].query(InRange("salary", 195000, 200000), name="John")
print(len(rich_johns))
print(rich_johns)

uk = db[Employee].query(Contains("description", "United Kingdom"))
print(len(uk))
if uk:
    print(uk[0])
    print(uk[0].description)
