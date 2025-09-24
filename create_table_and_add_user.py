import argparse, json, os, logging, sys, sqlite3, datetime
from libs.DBHandler import DBHandler



def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Path to the config file", default="../config/app-config.dev.json")
    parser.add_argument("-d", "--drop", help="Flag to drop table ", default=False, action="store_true")

    return parser.parse_args()

def get_config(path_cfg_file:str) -> json:
    if os.path.exists(path_cfg_file):
        with open(path_cfg_file) as cfg_file_f:
            return json.load(cfg_file_f)


def create_table(dbh:DBHandler, sql_statement:str, table_name:str, drop_table:bool=False) -> bool:
    if drop_table:
        try:
            dbh.client.execute(f"DROP TABLE {table_name};")
            logging.info(f"Table has been dropped '{table_name}'")
        except sqlite3.OperationalError as err:
            logging.warning(f"Table does not exist '{err}'")
    logging.info(f"Attempting Create Table: {CREATE_API_USERS_TABLE_QUERY}")
    table_create_response = dbh.execute_query(sql_statement, "create")
    if table_create_response["STATUS"]:
        logging.info("Table created")
        dbh.connection.commit()
        return True
    else:
        logging.error('Failed to create table')
        return False


def insert_row(dbh:DBHandler, sql_statement:str)-> bool:
    logging.info(f"Attempting Insert Row: {sql_statement}")
    insert_row_response = dbh.execute_query(sql_statement, "insert")
    if insert_row_response["STATUS"]:
        logging.info(f"Insert was sucessful. Impacted rows: {insert_row_response['ROWS'][0]}")
        dbh.connection.commit()
        return True
    else:
        logging.error(f"Unable to run insert statement: '{sql_statement}'")
        return False



if __name__ == '__main__':

    CREATE_API_USERS_TABLE_QUERY='''CREATE TABLE api_users(
    user_id INTEGER PRIMARY KEY ,
    username TEXT UNIQUE,
    email TEXT UNIQUE,
    password TEXT
    );'''

    # Sqlite does not support Date Type Columns - Will use an ISO String representation
    CREATE_TOKEN_JOURNAL_TABLE_QUERY='''CREATE TABLE user_token_journal(
    user_id INTEGER,
    token TEXT UNIQUE,
    expiry TEXT,
    FOREIGN KEY (user_id) REFERENCES api_users(user_id)
    );'''

    CREATE_JOB_STATUS_TABLE_QUERY='''CREATE TABLE job_status(
    job_id INTEGER PRIMARY KEY,
    program TEXT UNIQUE,
    start_time TEXT,
    end_time TEXT,
    params TEXT
    );'''

    "%Y-%m-%d %H:%M:%S.%f %z"

    DUMMY_USER_INSERT = "INSERT INTO api_users(username, email, password) VALUES('{}','{}','{}')".format("jsmith", "john.smith@gmail.com", "verySecure123")
    DUMMY_JOB_STARTIME = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(hours=2)
    DUMMY_JOB_ENDIME = datetime.datetime.now(tz=datetime.timezone.utc)
    DUMMY_JOB_INSERT = "INSERT INTO job_status(program, start_time,  params) VALUES('{}','{}','{}')".format(
        "EQModelCalculator.sh", DUMMY_JOB_STARTIME.strftime("%Y-%m-%d %H:%M:%S.%f %z"), "-asofdate 20250920 -model VOL")
    DUMMY_JOB_INSERT_2 = "INSERT INTO job_status(program, start_time, end_time,  params) VALUES('{}','{}','{}','{}')".format(
        "LogArchiveAndReset.sh", DUMMY_JOB_STARTIME.strftime("%Y-%m-%d %H:%M:%S.%f %z"), DUMMY_JOB_ENDIME.strftime("%Y-%m-%d %H:%M:%S.%f %z"), "-e PRD")

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(funcName)s:%(lineno)d - %(levelname)s - %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout)]
    )
    args = get_args()
    logging.info(f"Arguments: {args}")
    cfg = get_config(args.config)
    logging.info(f"Config: {cfg}")
    # As DB HOST is the path to SQL Lite DB, need to create a relative path rather than hardcode the path into config file
    database_name = cfg["DB_URL"].split("//")[1]
    database_fullpath = os.path.join(os.path.dirname(__file__), database_name)
    dbh = DBHandler(cfg["DB_URL"], db_file_path=database_fullpath)

    create_table(dbh, CREATE_API_USERS_TABLE_QUERY, "api_users", args.drop)
    create_table(dbh, CREATE_TOKEN_JOURNAL_TABLE_QUERY, "user_token_journal", args.drop)
    create_table(dbh, CREATE_JOB_STATUS_TABLE_QUERY, "job_status", args.drop)
        
    insert_row(dbh, DUMMY_USER_INSERT)
    insert_row(dbh, DUMMY_JOB_INSERT)
    insert_row(dbh, DUMMY_JOB_INSERT_2)