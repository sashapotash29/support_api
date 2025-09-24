# Basic Fast API

## Description:
- Fastapi example
- Connects to a database that contains job statuses
- Requires user to authenticate (get a token and provide in header on protected requests)

## Environment Setup:
1. Install poetry
2. Clone the repo
3. Navigate to repo's root directory
4. Run command: **poetry install**
    - Documentation: https://python-poetry.org/docs/basic-usage
5. Create database
```
in root directory:
poetry run python create_table_and_add_user.py -c config/app-config-dev.json
```


## Usage:
### Start the app
```
Navigate to root directory
To start the app:
poetry run fastapi dev app.py
```
### create_table_and_add_user.py
```
usage: create_table_and_add_user.py [-h] [-c CONFIG] [-d]

options:
  -h, --help           show this help message and exit
  -c, --config CONFIG  Path to the config file
  -d, --drop           Flag to drop table
```


## API Instructions
### Endpoints
#### /login
- This is the authentication endpoint
- Expects a POST request containing JSON with keys "username" and "password" and associated values to verify your credentials
- In the JSON response, your token is in the "TOKEN" key.
```
Curl Example:
curl -X POST -H 'application/json' -d '{"username":"jsmith", "password":"verySecure123"}'
```
```
Response Example:
{"STATUS":"SUCCESS","TOKEN":"91e31607ba44db916261c0e84231582dc1486484b9071db62320651e8a1580e9","MESSAGE":"Login Successful"}
```
### /jobs
- This endpoint returns all the jobs
- Each job is listed in the job_status table
- NOTE: This is a protected resource and requires a TOKEN. See /login for more info
```
Curl Example
 curl http://localhost:8000/jobs -H 'Authorization: Bearer 91e31607ba44db916261c0e84231582dc1486484b9071db62320651e8a1580e9'
```
```
Response Example
{
  "jobs": [
    {
      "job_id": 1,
      "program": "EQModelCalculator.sh",
      "start_time": "2025-09-23 23:32:17.128410 +0000",
      "end_time": null,
      "params": "-asofdate 20250920 -model VOL"
    },
    {
      "job_id": 2,
      "program": "LogArchiveAndReset.sh",
      "start_time": "2025-09-23 23:32:17.128410 +0000",
      "end_time": "2025-09-24 01:32:17.128415 +0000",
      "params": "-e PRD"
    }
  ]
}
```

### /job/<job_id>
- This endpoint is to get the status of a specific job (based on the id)
- This queries the job_status table
- NOTE: This is a protected resource and requires a TOKEN. See /login for more info
```
Curl Example
 curl http://localhost:8000/job/1 -H 'Authorization: Bearer 91e31607ba44db916261c0e84231582dc1486484b9071db62320651e8a1580e9'
```
```
Response Example:
{"jobs":[{"job_id":1,"program":"EQModelCalculator.sh","start_time":"2025-09-23 23:32:17.128410 +0000","end_time":null,"params":"-asofdate 20250920 -model VOL"}]}

If not found, you will receive an empty array
{"jobs":[]}
```
