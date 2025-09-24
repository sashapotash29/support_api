import logging, re

logger = logging.getLogger(__name__)

# Base class
class MessageHandler:

    # Simple function to verify if the necessary keys are present.
    # As there is lots of JSON going in and out of the API, this give a quick check that requirements are met
    def _required_keys(self, request_obj:dict, *key_names:str|int) -> bool:
        result = 0
        for key_name in key_names:
            if key_name not in request_obj:
                result += 1
        if result == 0:
            return True
        else:
            return False


class RequestHandler(MessageHandler):
    # Class for handling requests that come in
    # Verify the keys are there, do some processing/extraction of data

    def verify_login_request(self, request_json:dict) -> bool:
        logger.info(f"Received a request string '{request_json}'")
        return self._required_keys(request_json, "username", "password")

    def check_token_is_present(self, request:dict) -> tuple[bool,str]:
        if self._required_keys(request.headers, "authorization"):
            return self.parse_token(request.headers["authorization"])
        else:   
            return (False, "Authorization not in headers")
    
    def parse_token(self, auth_str:str) -> tuple[bool,str]:
        if "Bearer " in auth_str:
            token_match_re_str = r"^Bearer\s*(.+?)$"
            search_result = re.match(token_match_re_str, auth_str)
            if search_result:
                return (True, search_result.group(1))
            else:
                logging.warning(f"Unable to parse token from Authorization value: '{auth_str}'")
                return (False, "Token not found")
        else:
            logging.warning(f"Not a valid Authorization Value: '{auth_str}'")
            return False,"Not a valid Authorization Value (missing 'Bearer ')"


class ResponseHandler(MessageHandler):
    # Class for handling Responses that are fed to client
    # Convert DBHandler Objects and other Python objects into Dictionaries/JSONs

    def generate_jobs_response(self, job_list:list[list]) -> str:
        # This function will receive the database results and convert rows to dicts with columns as keys
        response = {"jobs" : []}
        if len(job_list) >= 1:
            headers = job_list[0]
            for row in job_list[1:]:
                row_dict = {}
                for idx in range(len(row)):
                    row_dict[headers[idx]] = row[idx]
                response["jobs"].append(row_dict)

        return response
    
