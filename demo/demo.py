import zerodb
from zerodb.query import *
from models import Employee

SOCKET = ("localhost", 8001)

db = zerodb.DB(
    ("localhost", 8001), username='root', password='root-password',
    server_cert='server.pem')

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
