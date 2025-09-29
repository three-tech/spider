from base.config import config
from x.x_spider import XSpider

API_TOKEN = config.get('x', {}).get('auth_token', "")
client = XSpider()


def sync_my_following():
    """
    同步我的关注
    """
    client.sync_following_to_member_x()


if __name__ == '__main__':
    # client.process_user_tweets('deyerzamora')
    client.run()
