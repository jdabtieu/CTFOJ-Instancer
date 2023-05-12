# CTFOJ-Instancer
Instancer for secure CTF challenges hosted with CTFOJ

## Sample API Usage
```
To create an instance:

curl -H "Authorization: Bearer bob" -H "Content-Type: application/json" -X POST --data '{"name": "typop", "player": 1, "duration": 600, "flag": "ctf{flag}"}' http://localhost:5000/api/v1/create

To query an instance:

curl -H "Authorization: Bearer bob" -H "Content-Type: application/json" -X POST --data '{"name": "typop", "player": 1}' http://localhost:5000/api/v1/query

To destroy an instance:

curl -H "Authorization: Bearer bob" -H "Content-Type: application/json" -X POST --data '{"name": "typop", "player": 1}' http://localhost:5000/api/v1/destroy
```
