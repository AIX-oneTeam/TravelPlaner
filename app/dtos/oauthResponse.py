class oauthResponse :
    def __init__(self, access_token, refresh_token):
        self.access_token = access_token
        self.refresh_token = refresh_token

    def __str__(self):
        return f'access_token: {self.access_token}, token_type: {self.token_type}, expires_in: {self.expires_in}, refresh_token: {self.refresh_token}, scope: {self.scope}'
    
    
