comando para não dar problema no requirements
`pip freeze | findstr /V "@" > requirements.txt`
adicionar psycopg2-binary==2.9.10 no lugar de psycopg2==2.9.10
