import jwt

payload = {
    "sub": "airflow"  # 'sub' is required, acts like user_id
}

secret = "my-super-secret"  # must match AIRFLOW__API__AUTH__JWT_SECRET
token = jwt.encode(payload, secret, algorithm="HS256")
print(token)