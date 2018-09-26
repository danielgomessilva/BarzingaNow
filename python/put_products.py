import csv, json
import requests

X = []
Y = []
with open('products.csv', 'rb') as data:
    reader = csv.reader(data, delimiter=',')
    headers = {'content-type' : 'application/x-www-form-urlencoded', 'Bearer' : 'Token Diego'}
    params = {'sessionKey': '9ebbd0b25760557393a43064a92bae539d962103', 'format': 'xml', 'platformId': 1}
    for line in reader:
        # = "https://v6-dot-barzinganow.appspot.com/api/product/"
        url = "http://localhost:8080/api/product/"
        data = {"description":line[1],"price":line[2], "quantity": int(line[4]), "category": ""}
        print data
        print requests.post(url, data=data, headers=headers, params=params)