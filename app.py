import logging, sys, json, os
from fastapi import FastAPI , HTTPException, Request
import uvicorn

# Custom Libraries
from libs.MessageHandler import RequestHandler, ResponseHandler
from libs.AuthHandler import AuthHandler
from libs.DBHandler import DBHandler


def get_config(path_to_config:str) -> json:
    if os.path.exists(path_to_config):
        with open(path_to_config) as app_cfg_f:
            return json.load(app_cfg_f)
    else:
        logging.error(f"Unable to find config file at '{path_to_config}'. App Exiting..")
        sys.exit()


# Init instance of FastAPI() to attach endpoints to
app = FastAPI()

### ENDPOINTS
@app.get("/")
def base_url():
    return {"Welcome to the API. Please get a token at /login"}


@app.post("/login")
async def verify_login(logon_request:Request) -> dict:
    response = {"STATUS": "FAILED", "MESSAGE": "Login failed"}
    additonal_info = ""
    body = await logon_request.json()
    logging.info(f"Received a logon request '{body}'")
    if RequestHandler().verify_login_request(body):
        user_details = DBHandler(os.environ["DB_URL"]).retrieve_user_details(body["username"])
        if user_details["STATUS"] and user_details["ROWS"][0][3] == body["password"]:
            user_session_token = AuthHandler().get_token(32)
            logging.info(f"Token Granted to {body['username']}: '{user_session_token}'")
            register_token_result = DBHandler(os.environ["DB_URL"]).register_new_token(user_session_token, user_details["ROWS"][0][0])
            if register_token_result["STATUS"]:
                logging.info("Token successfully recorded in database")
                response = {"STATUS": "SUCCESS", "TOKEN" : user_session_token, "MESSAGE": "Login Successful"}
            else:
                logging.error("Failed to register token. Received '{body}' Token: '{user_session_token}'")
        else:
            additonal_info = "Password did not match and/or not a valid user"
            logging.warning(additonal_info)
    else:
        additonal_info =  "Not a valid logon_request"
        logging.info(additonal_info)

    response["MESSAGE"] = response["MESSAGE"] if additonal_info == "" else f"{response['MESSAGE']} - {additonal_info}" 
    return response

@app.get("/jobs")
async def get_list_of_jobs(get_jobs_request:Request):
    http_request = get_jobs_request
    token_success, token_msg = RequestHandler().check_token_is_present(http_request)
    if token_success:
        dbh = DBHandler(os.environ["DB_URL"])
        token_valid, token_check_message = dbh.check_token_is_valid(token_msg)
        if token_valid:
            all_jobs_query_result = dbh.get_all_jobs()
            return ResponseHandler().generate_jobs_response(all_jobs_query_result['ROWS'])
        else:
            return {"STATUS": "FAILED", "MESSAGE": f"Token is Invalid. Reason: '{token_check_message}'"}
    else:
        logging.warning(f"/jobs/all request failed. No token present. Headers: '{http_request.headers}'")
        return {"STATUS": "FAILED", "MESSAGE": f"Unable to retrieve token from Headers. Reason: '{token_msg}'"}


@app.get("/job/{job_id}")
async def get_job_info(job_id:str, http_request:Request):
    token_success, token_msg = RequestHandler().check_token_is_present(http_request)
    if token_success:
        dbh = DBHandler(os.environ["DB_URL"])
        token_valid, token_check_message = dbh.check_token_is_valid(token_msg)
        if token_valid:
            job_query_result = dbh.get_job_by_id(job_id)
            return ResponseHandler().generate_jobs_response(job_query_result['ROWS'])
        else:
            return {"STATUS": "FAILED", "MESSAGE": f"Token is Invalid. Reason: '{token_check_message}'"}
    else:
        logging.warning(f"/jobs/all request failed. No token present. Headers: '{http_request.headers}'")
        return {"STATUS": "FAILED", "MESSAGE": f"Unable to retrieve token from Headers. Reason: '{token_msg}'"}
    

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s",
                    # handlers=[logging.StreamHandler(sys.stdout)]
                    filename="app.log"
)


## Load configuration file
app_cfg = get_config("config/app-config-dev.json")
# Add system config variables to environment.
# This setup allows us to be flexible in a kubernetes-like environment where we can open a shell and modify on the fly
os.environ["DB_URL"] = app_cfg["DB_URL"]
os.environ["API_TOKEN_HOURS_LIFETIME"] = str(app_cfg["API_TOKEN_HOURS_LIFETIME"])

logging.info(f"API will run on host {app_cfg['API_HOST']} and port {app_cfg['API_PORT']}")

uvicorn.run(app, host=app_cfg['API_HOST'], port=app_cfg['API_PORT'])
logging.info("API is now available")