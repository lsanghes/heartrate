from ant.easy.node import Node
from ant.easy.channel import Channel
from twilio.rest import Client
from collections import deque
from datetime import datetime
import time, logging

class Alert:
    def __init__(self, account_sid, auth_token, twilio_number, twilio_call_url, alert_numbers):
        self.client = Client(account_sid, auth_token)
        self.twilio_number = twilio_number
        self.twilio_call_url = twilio_call_url
        self.alert_numbers = alert_numbers
        self.logger = logging.getLogger("Alert")

    def send_sms(self, body):
        msg = ""
        for number in self.alert_numbers:
            try:
                message = self.client.messages.create(to=number, from_=self.twilio_number, body=body)
                msg += "SMS:{} SENT\n".format(number)
            except Exception as ex:
                self.logger.error('{}: {}'.format(type(ex), ex))
                msg += "SMS:{} FAILED\n".format(number)
        return msg

    def make_call(self):
        msg = ""
        for number in self.alert_numbers:
            try:
                call = client.api.account.calls.create(to=number, from_=self.twilio_number, url=self.twilio_call_url)
                msg += "Call:{} SENT\n".format(number)
            except Exception as ex:
                self.logger.error('{}: {}'.format(type(ex), ex))
                msg += "Call:{} FAILED\n".format(number)
        return msg


class HRM:
    def __init__(self, netkey, alert, sampling_interval, moving_avg_size, max_hr_threshold, enable_sms_alert, enable_call_alert):
        self.alert = alert
        self.prev_ts = time.time()
        self.prev_avg_hr = 0
        self.netkey = netkey
        self.antnode = None
        self.channel = None
        self.sms_enabled = True
        self.call_enabled = False
        self.past_heartrates = deque([], moving_avg_size)
        self.curr_heartrate = None
        self.sampling_interval = sampling_interval
        self.max_hr_threshold = max_hr_threshold
        self.enable_call_alert = enable_call_alert
        self.enable_sms_alert = enable_sms_alert
        self.logger = logging.getLogger("HRM")

    def stop(self):
        if self.antnode:
            self.antnode.stop()

    def start(self):
        self.setup_node_channel()
        self.channel.open()
        self.antnode.start()

    def setup_node_channel(self):
        self.antnode = Node()
        self.antnode.set_network_key(0x00, self.netkey)
        self.channel = self.antnode.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE)
        self.channel.on_broadcast_data = self.process
        self.channel.on_burst_data = self.process
        self.channel.set_period(8070)
        self.channel.set_search_timeout(12)
        self.channel.set_rf_freq(57)
        self.channel.set_id(0, 120, 0)

    def process(self, data):
        curr_ts = time.time()
        if curr_ts - self.prev_ts < self.sampling_interval:
            return

        hr = data[7]
        self.past_heartrates.append(hr)
        curr_avg_hr = sum(self.past_heartrates) // len(self.past_heartrates)

        self.logger.info("hr={}, avg_hr={}".format(hr, curr_avg_hr))

        # log hr for analysis
        hr_log = "{},{},{}".format(datetime.fromtimestamp(curr_ts).strftime("%Y%m%d_%H:%M:%S"), hr, curr_avg_hr)
        with open("hr_log_{}.csv".format(datetime.fromtimestamp(time.time()).strftime("%Y%m%d")), "a") as f:
            f.write(hr_log + "\n")

        # detect abnormal hr
        if self.prev_avg_hr < self.max_hr_threshold and curr_avg_hr > self.max_hr_threshold:
            ts = datetime.fromtimestamp(curr_ts).strftime("%I:%M%p")
            msg =  "Unusual HR {} BPM was detected at {}.".format(hr, ts)
            self.logger.info(msg)
            if self.enable_sms_alert:
                self.logger.info(self.alert.send_sms(msg))
            if self.enable_call_alert:
                self.logger.info(self.alert.make_call())

        # update prev_* values
        self.prev_ts = curr_ts
        self.prev_avg_hr = curr_avg_hr


netkey = [0xb9, 0xa5, 0x21, 0xfb, 0xbd, 0x72, 0xc3, 0x45]
twilio_call_url = "http://twimlets.com/holdmusic?Bucket=com.twilio.music.ambient"
account_sid = "AC36f913e555e5e0760cf5edfe1fd528f2"
auth_token  = "5c9aa78c852e24fd239ce1bfe3f5b918"
twilio_number = "+13124710394"
alert_numbers = ["+13123162187"]
sampling_interval = 5
moving_avg_size = 6
enable_sms_alert = 1
enable_call_alert = 0
max_hr_threshold = 100

def main():
    logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level = logging.INFO)
    alert = Alert(account_sid, auth_token, twilio_number, twilio_call_url, alert_numbers)
    hrm = HRM(netkey, alert, sampling_interval, moving_avg_size, max_hr_threshold, enable_sms_alert, enable_call_alert)
    try:
        print("starting HRM...")
        hrm.start()
    finally:
        print("stopping HRM...")
        hrm.stop()

if __name__ == "__main__":
    main()