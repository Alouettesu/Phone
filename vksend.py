import requests
import vk_api
import config
import random

__vk_session = vk_api.VkApi(token=config.vk_token)
__vk = __vk_session.get_api()

def send_sms(smsList):
    try:
        for sms in smsList.smsList:
            if sms.Stat == 'REC UNREAD':
                __vk.messages.send(
                    user_id = config.vk_user_id,
                    message = 'Новое сообщение от ' + sms.Sender,
                    random_id = random.randint(1, 2**31)
                )
                __vk.messages.send(
                    user_id = config.vk_user_id,
                    message = sms.Text,
                    random_id = random.randint(1, 2**31)
                )
    except:
        return False
    return True