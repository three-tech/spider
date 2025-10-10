from base.config import config
from x.x_auth_client import create_x_auth_client
from x.x_spider import XSpider

token ='780fc99a00ec1fbe83e59df7415ddf1919dbda16'
x_client = create_x_auth_client(token)

if __name__ == "__main__":
    print(x_client.get_my_following())
