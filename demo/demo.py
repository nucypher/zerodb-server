import zerodb
from zerodb.query import *
from models import Employee

PASSPHRASE = "very insecure passphrase - never use it"
SOCKET = ("localhost", 8001)

db = zerodb.DB(
    ("localhost", 8001),
    cert_file='client.pem', key_file='client_key.pem', server_cert='server.pem',
    password=PASSPHRASE)

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
