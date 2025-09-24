import secrets, logging

logger = logging.getLogger(__name__)

# This module will handle creation of Auth related details as well as Eencryption requirements
# i.e. encryption/decryption of passwords. 

class AuthHandler:

    def __init__(self):
        pass

    def encrypt_string(input_string:str):
        pass

    def decypt_string(input_string:str):
        pass

    def get_token(self, token_size:int=16):
        return secrets.token_hex(token_size)