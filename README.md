
## INSTALL
```sh
    pip install "langchain>=0.2.0" --break-system-packages # Core LangChain package
    pip install langchain-community --break-system-packages # Contains Chroma and other community integrations
    pip install langchain-openai --break-system-packages # Contains OpenAI models and embeddings
    pip install chromadb --break-system-packages # The underlying database library
    pip install pypdf fastapi uvicorn sqlalchemy httpx python-jose langchain-text-splitters --break-system-packages
```
or
```sh
  pip install -r requirements.txt

```

## DEV

- windows
  -> python -m venv env
  -> .\env\Scripts\activate
- macos
  -> python3 -m venv venv
  -> source ./venv/bin/activate

- uvicorn main-single:app --reload

- Эхлээд доорх кодыг ажиллуулж text-г vector болгон хувиргаж байгаа
```sh
  curl -X 'POST' 'http://127.0.0.1:8000/upload-pdf'
```


## QUERY TEXT - Жишээ асуултууд
```sh

    Topic	Effective Query Text
    Houses & Hotels:	"What is the rule for building houses evenly across a complete color-group?"
    Speed Die:	"When playing with the Speed Die, what are the effects of rolling the Mr. Monopoly symbol?"
    Mortgages:	"If I buy mortgaged property from another player, what must I pay the Bank to lift the mortgage later?"

```
```sh
    Basic Rules	"What happens if I land on an unowned property?"
    Rent & Mortgage	"Can I collect rent on a mortgaged property?"
    Houses & Hotels	"What is the rule for building houses evenly?"
    Jail	"How do I get out of Jail in Monopoly?"
    Money & Bank	"What happens if the Bank runs out of money?"
    Taxes	"How is Income Tax calculated?"
    Speed Die (Specific)	"When do I start using the Speed Die?"
    Speed Die (Action)	"What are the actions when I roll a Mr. Monopoly on the Speed Die?"
```


## LOGIN CURL
```sh

curl -X 'POST' \
  'http://127.0.0.1:8000/login' \
  -H 'Content-Type: application/json' \
  -d '{"username": "user1", "password": "1234"}'

```

## Query CURL
```sh
curl -X 'POST' \
  'http://127.0.0.1:8000/query' \
  -H 'Content-Type: application/json' \
  -d '{"query": "What happens if I land on an unowned property?"}'

curl -X 'POST' \
  'http://127.0.0.1:8000/query-auth' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer user1' \
  -d '{"query": "What happens if I land on an unowned property?"}'

curl -X 'POST' \
  'http://127.0.0.1:8000/query-auth' \
  -H 'Content-Type: application/json' \
  -d '{"query": "What happens if I land on an unowned property?"}'


curl -X 'GET' \
  'http://127.0.0.1:8000/get-user-info' \
  -H 'Content-Type: application/json'
curl -X 'GET' \
  'http://127.0.0.1:8000/get-user-info' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMSIsImV4cCI6MTc2NDgxOTI3N30.R8N-Q_45JbECr55RAoHNTUFy6K5EdDDHCFsmQxYhEtE' \
  -H 'Content-Type: application/json'
```
