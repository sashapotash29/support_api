# Importing datetime all together rather than "from datetime import datetime" 
# more readable in code, i.e. datetime.timezone rather than timezone
import os, sqlite3, logging, os, datetime

from .CustomExceptions import InvalidInputError


# This is the DatabaseHandler. All database querying/interactions shoudl go through this Class
# it can do some post processing though the output sent from the API should be handled by the ResponseHandler()

logger = logging.getLogger(__name__)

class DBHandler:


    def __init__(self, db_url:str="", db_file_path:str=""):
        self.db_url = os.environ["DB_URL"] if db_url == "" else db_url
        logger.info(f"Initiated DBHandler with '{self.db_url}'")
        self.db_type = self.db_url.split(":")[0] 
        self.db_path = self.db_url.split("/")[-1] if db_file_path == "" else db_file_path
        # Before instatiating a DB Object, verify it can connect
        self.connection = self._test_connection()
        self.client = self.connection.cursor()

    def _retrieve_decrypted_password(p:str):
        # This is not needed for Sqlite3 example. If you were to store DB password in file, you will likely encrypt it. 
        # This is where you would implement logic on how to decrypt it
        pass

    def _test_connection(self) -> None:
        match self.db_type:
            case "sqlite3":
                if os.path.exists(self.db_path):
                    try:
                        return sqlite3.connect(self.db_path)
                    except:
                        raise InvalidInputError(f"Connection to '{self.db_type}' failed. Unable to connect to database at '{self.db_path}'")
                else:
                    raise InvalidInputError(f"Sqlite Database not found at: '{self.db_path}'")
            case _:
                raise InvalidInputError(f"Unimplemented database type: '{self.db_type}'")
        pass
    
    def _execute_select(self, select_statement:str, include_headers:bool=False) -> dict:
        self.client.execute(select_statement)
        rows = self.client.fetchall()
        if len(rows) > 0:
            # Add headers if the flag is present, otherwise give them rows as produced by sqlite3 module
            if include_headers:
                column_names = [column_description[0] for column_description in self.client.description]
                rows = [column_names] + rows
            return {"STATUS": True, "ROWS": rows, "STATEMENT": select_statement}
        else:
            return {"STATUS": False, "ROWS": [], "STATEMENT": select_statement}
    
    def _execute_crud(self, crud_sql_statement:str, commit_flag:bool=False) -> dict:
        self.client.execute(crud_sql_statement)
        impacted_rows = self.client.rowcount
        if impacted_rows > 0:
            if commit_flag:
                self.connection.commit()
                logging.warning(f"Transaction has been committed '{crud_sql_statement}'")
            return {"STATUS": True, "ROWS": [impacted_rows], "STATEMENT": crud_sql_statement}
        else:
            return {"STATUS": False, "ROWS": [impacted_rows], "STATEMENT": crud_sql_statement}

    def execute_query(self, sql_statement:str, statement_type:str="select", include_headers:bool=False, commit_flag:bool=False) -> str:
        match statement_type.lower():
            case "select":
                response = self._execute_select(sql_statement, include_headers)
            case "update" | "delete" | "insert":
                # C.R.U.D. => Create / Replace / Update / Delete
                response =  self._execute_crud(sql_statement, commit_flag)
            case "create":
                try:
                    self.client.execute(sql_statement)
                    response = {"STATUS":True}
                except sqlite3.OperationalError as err:
                    logging.error(f"Unable to run CREATE statement. '{sql_statement}'. Exception below: '{err}'")
                    {"STATUS":False}
            case _:
                logger.error(f"execute_query() - Failed to execute '{sql_statement}'")
                raise InvalidInputError(f"Unable to action based on statement type: '{statement_type}'")
        
        return response

    def retrieve_user_details(self, username:str) -> dict:
        query_result = self.execute_query(f"Select * from api_users;")
        return query_result

    def _is_valid_token(self, token_str:str) -> bool:
        token_exists_sql = f"SELECT 1 FROM user_token_journal WHERE token = '{token_str}';"
        token_exists_response = self.execute_query(token_exists_sql, "select")
        return token_exists_response["STATUS"]

    def _token_expiry_check(self, token_str:str) -> (bool, str):
        # Get the token's expiry from database
        get_token_expiry_sql = f"SELECT expiry FROM user_token_journal WHERE token = '{token_str}';"
        get_token_expiry_result = self.execute_query(get_token_expiry_sql, "select")
        expiry_str = get_token_expiry_result["ROWS"][0][0]
        expiry_time_dt = self._convert_expiry_to_datetime(expiry_str)
        # Get Current time
        current_time_dt = self._get_current_datetime()
        # Check it against current time and return result
        return expiry_time_dt < current_time_dt, expiry_str


    def check_token_is_valid(self, token_str:str) -> bool:
        checks_failed = 0
        msg = ""
        # 1 Token is not a valid token. REJECT
        if not self._is_valid_token(token_str):
            logging.warning(f"Token '{token_str}' was not found in database")
            checks_failed += 1
            msg = "Not a valid token"
        else:
            # 2 Token has expired and no longer valid. REJECT
            # If the token was valid, we need to check if it has expired
            expired, expiry_date = self._token_expiry_check(token_str)
            if expired:
                logging.warning(f"Token '{token_str}' has expired. Expiry Date: {expiry_date}")
                msg = f"Expired on: {expiry_date}"
                checks_failed +=1
        result = True if checks_failed == 0 else False
        return result, msg

    def _get_current_datetime(self, tz:datetime.timezone=datetime.timezone.utc,
                               forward_offset:int=0) -> datetime:
        # This might get more complicated if there are other timezones to consider
        return datetime.datetime.now(tz) + datetime.timedelta(hours=forward_offset)

    def _convert_expiry_to_datetime(self, datetime_str:str, datetime_str_format:str="%Y-%m-%d %H:%M:%S.%f %z") -> datetime.datetime:
        return datetime.datetime.strptime(datetime_str, datetime_str_format)

    def register_new_token(self, token_str:str, user_id:int) -> dict:
        # Check if User already has a token. If so, update the record
        user_has_token_flag = self.get_user_for_token(user_id)
        if user_has_token_flag:
            # NOTE: these 3 lines could be broken into a separate function in case there are other situations that require updating a token (more reusable)
            new_expiry_datetime_str = self._get_current_datetime(forward_offset=int(os.environ["API_TOKEN_HOURS_LIFETIME"])
                                                                 ).strftime("%Y-%m-%d %H:%M:%S.%f %z")
            update_users_token_entry_sql = f"UPDATE user_token_journal SET token='{token_str}', expiry='{new_expiry_datetime_str}' WHERE user_id = {user_id};"
            response =  self.execute_query(update_users_token_entry_sql, "update", commit_flag=True)
            logging.info(f"Updated token for User #{user_id} - Expiry Time (UTC): {new_expiry_datetime_str}")
        # If user does not have token, then insert the token into user_token_journal table
        elif not user_has_token_flag:
            new_expiry_datetime_str = self._get_current_datetime(forward_offset=int(os.environ["API_TOKEN_HOURS_LIFETIME"])
                                                                 ).strftime("%Y-%m-%d %H:%M:%S.%f %z")
            insert_new_user_token_sql = f"INSERT INTO user_token_journal (user_id, token, expiry) VALUES ({user_id}, '{token_str}', '{new_expiry_datetime_str}');"
            response =  self.execute_query(insert_new_user_token_sql, "insert", commit_flag=True)
            logging.info(f"First User Token Generated for User #{user_id}. - Expiry Time (UTC): {new_expiry_datetime_str}")
        else:
            logger.error("Unable to register new token . Token_string: '{}' and User ID: '{}' received")
            response =  {"STATUS": False}
        
        return response

    def get_user_for_token(self, user_id:int) -> int | bool:
        check_user_id_sql = f"SELECT user_id FROM user_token_journal WHERE user_id = {user_id};"
        result = self.execute_query(check_user_id_sql, "select")
        if result["STATUS"]:
            # expected "result" object is  {...., "ROWS": [[<user_id/int>],....}
            return result["ROWS"][0][0]
        elif not result["STATUS"]:
            return False

    def get_all_jobs(self) -> dict:
        get_all_jobs_sql = "SELECT * FROM  job_status;"
        return self.execute_query(get_all_jobs_sql, include_headers=True)
    
    def get_job_by_id(self, job_id:str) -> dict:
        get_all_jobs_sql = f"SELECT * FROM  job_status WHERE job_id = {job_id}"
        return self.execute_query(get_all_jobs_sql, include_headers=True)